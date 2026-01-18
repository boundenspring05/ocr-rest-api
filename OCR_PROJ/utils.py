import shutil
import os
from contextlib import contextmanager
import asyncio

@contextmanager
def save_file_context(uploaded_file, counter, path="."):
    
    extension = os.path.splitext(uploaded_file.filename)[-1]
    
    unique_name = f"file{counter[0]}{extension}"
    temp_file = os.path.join(path, unique_name)
    
    try:
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(uploaded_file.file, buffer)
        yield temp_file
    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)

async def process_with_cleanup(uploaded_file, ocr_func, counter, path="./"):
    def sync_process():
        with save_file_context(uploaded_file, counter, path=path) as temp_file:
            return ocr_func(temp_file)
    
    return await asyncio.to_thread(sync_process)
