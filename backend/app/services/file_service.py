import os
from app.services.ingestion import extract_text_content
from fastapi import UploadFile
from typing import Tuple
from app.core.config import settings
import shutil
from datetime import datetime
import logging

logger = logging.getLogger(__name__)



UPLOAD_DIR = settings.UPLOAD_DIR

os.makedirs(UPLOAD_DIR, exist_ok=True)

async def save_upload_file(upload_file: UploadFile) -> Tuple[str, int]:
    """
    Saves file to disk and returns (file_path, file_size).
    """
    try:
        # Create date-based subdirectory
        today = datetime.now().strftime("%Y-%m-%d")
        target_dir = os.path.join(UPLOAD_DIR, today)
        os.makedirs(target_dir, exist_ok=True)
        
        file_path = os.path.join(target_dir, upload_file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
            
        file_size = os.path.getsize(file_path)
        return file_path, file_size
    finally:
        upload_file.file.close()




def extract_text_from_file(file_path: str, file_type: str) -> str:
    """
    Extracts text using centralized ingestion logic (Docling + Fallback).
    Delegates to app.services.ingestion.extract_text_content.
    """
    try:
        return extract_text_content(file_path)
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        return ""
