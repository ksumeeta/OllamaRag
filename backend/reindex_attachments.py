
import sys
import os
import logging

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, VectorSessionLocal
from app.models import sql_models as models
from app.services import ingestion

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reindex_all():
    db = SessionLocal()
    try:
        attachments = db.query(models.Attachment).all()
        logger.info(f"Found {len(attachments)} attachments to re-index.")
        
        for att in attachments:
            if not att.file_path or not os.path.exists(att.file_path):
                logger.warning(f"File not found: {att.file_path}. Skipping.")
                continue
                
            logger.info(f"Re-indexing: {att.file_name} (ID: {att.id})")
            try:
                # We reuse process_and_index_document
                # Note: This will re-run OCR/Docling which is expensive but safe.
                # It updates extracted_text too.
                doc_id = str(att.id)
                ingestion.process_and_index_document(att.file_path, doc_id)
                logger.info("Success.")
            except Exception as e:
                logger.error(f"Failed to re-index {att.id}: {e}")

    except Exception as e:
        logger.error(f"Global error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reindex_all()
