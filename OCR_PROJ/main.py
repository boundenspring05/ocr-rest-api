import hashlib
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

    response = {}
    s = time.time()
    tasks = []
    cache_hits = 0
    image_hashes = {}
    
    for img in Images:
        print("Images Uploaded: ", img.filename)
        
        content = await img.read()
        img_hash = hashlib.md5(content).hexdigest()
        
        if img_hash in image_hashes:
            cache_hits += 1
            response[img.filename] = image_hashes[img_hash]
            continue
        if await redis.get(f"ocr:cache:{img_hash}"):
            cache_hits += 1
            text = (await redis.get(f"ocr:cache:{img_hash}"))
            response[img.filename] = text
            continue
            
        await img.seek(0)
        
        file_counter = await redis.incr("ocr:global_file_counter")
        counter = [file_counter]
        
        tasks.append(asyncio.create_task(
            utils.process_with_cleanup(img, ocr.read_image, counter)
        ))
        tasks[-1].img_hash = img_hash
    
    if tasks:
        texts = await asyncio.gather(*tasks, return_exceptions=True)
        for i, task in enumerate(tasks):
            if isinstance(texts[i], Exception):
                response[Images[len(response)].filename] = f"[OCR ERROR] {str(texts[i])}"
            else:
                text = str(texts[i]).strip()

                await redis.setex(f"ocr:cache:{task.img_hash}", 300, text)
                response[Images[len(response)].filename] = text
    
    response["Time Taken"] = round((time.time() - s), 2)
    response["image_count"] = len(Images)
    response["cache_hits"] = cache_hits
    response["cache_misses"] = len(Images) - cache_hits
    
    return response