from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Depends
from typing import List
import time
import asyncio
import ocr
import utils
import redis.asyncio as aioredis
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = await aioredis.from_url("redis://localhost:6379", 
                                            encoding="utf-8", decode_responses=True)
    print("Redis connected for OCR API")
    yield  
    await app.state.redis.close()
    print("Redis disconnected")

app = FastAPI(lifespan=lifespan)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

def get_redis():
    return app.state.redis

@app.post("/api/v1/extract_text")
@limiter.limit("10/minute")
@limiter.limit("100/hour")
async def extract_text(request: Request, Images: List[UploadFile] = File(...), redis=Depends(get_redis)):
    if not Images:
        raise HTTPException(status_code=400, detail="No images provided")
    
    if len(Images) > 50:
        raise HTTPException(status_code=413, detail="Max 50 images per request")

    for img in Images:
        if not img.content_type or not img.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail=f"Invalid file type: {img.content_type or 'unknown'}")
        if img.size and img.size > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"File too large: {img.filename}")

    response = {}
    s = time.time()
    tasks = []
    
    for img in Images:
        print("Images Uploaded: ", img.filename)
        file_counter = await redis.incr("ocr:global_file_counter")
        counter = [file_counter]
        
        tasks.append(asyncio.create_task(
            utils.process_with_cleanup(img, ocr.read_image, counter)
        ))
    
    texts = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, text in enumerate(texts):
        if isinstance(text, Exception):
            response[Images[i].filename] = f"[OCR ERROR] {str(text)}"
        else:
            response[Images[i].filename] = str(text).strip()
    
    response["Time Taken"] = round((time.time() - s), 2)
    response["image_count"] = len(Images)
    return response
