from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from typing import List
import time
import asyncio
import hashlib
import ocr
import utils
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get('/')
def home():
    return {'message': "OCR API - POST to /api/v1/extract_text"}

@app.post("/api/v1/extract_text")
@limiter.limit("10/minute")
@limiter.limit("100/hour")
async def extract_text(request: Request, Images: List[UploadFile] = File(...)):
    if not Images:
        raise HTTPException(status_code=400, detail="No images provided")
    
    if len(Images) > 50:
        raise HTTPException(status_code=413, detail="Max 10 images per request")
    
    for img in Images:
        if not img.content_type or not img.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type: {img.content_type or 'unknown'}"
            )
        
        if img.size and img.size > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large: {img.filename} ({img.size} bytes)"
            )
    
    counter = [0]
    response = {}
    s = time.time()
    tasks = []
    
    for img in Images:
        print("Images Uploaded: ", img.filename)
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

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "rate_limiting": "active",
        "max_images_per_request": 10,
        "limits": {"minute": 10, "hour": 100}
    }
