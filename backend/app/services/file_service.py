import os
from fastapi import UploadFile
from typing import Tuple
from app.core.config import settings
import shutil
from datetime import datetime
from docling.document_converter import DocumentConverter


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


converter = DocumentConverter()

def extract_text_from_file(file_path: str, file_type: str) -> str:
    """
    Extracts text using Docling for better structural preservation.
    """
    try:
        ext = os.path.splitext(file_path)[1].lower()
        
        # Supported By Docling (PDF, DOCX, images, etc.)
        if ext in [".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".html", ".pptx", ".md"]:
             print(f"DEBUG: Converting {file_path} with Docling...")
             result = converter.convert(file_path)
             document = result.document
             return document.export_to_markdown() # Using markdown export as it's cleaner for LLMs
            
        elif ext in [".txt", ".json", ".csv", ".py", ".js", ".css", ".sql"]:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
                
        return ""
    except Exception as e:
        print(f"Extraction error: {e}")
        return ""
