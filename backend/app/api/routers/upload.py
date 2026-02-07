from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import sql_models as models
from app import schemas
from app.services import file_service

router = APIRouter()

@router.post("/", response_model=schemas.Attachment)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        file_path, file_size = await file_service.save_upload_file(file)
        
        # New Ingestion Logic
        # Create temp record to get ID (or use filename/timestamp as doc_id)
        # Here we use a temporary ID logic or just commit first? 
        # Better: Create attachment first, get ID, then process.
        
        db_attachment = models.Attachment(
            file_name=file.filename,
            file_type=file.content_type or "application/octet-stream",
            file_size=file_size,
            file_path=file_path,
            extracted_text="" # Placeholder
        )
        db.add(db_attachment)
        db.commit()
        db.refresh(db_attachment)
        
        # Process in background? For now, synchronous to ensure availability immediately
        from app.services import ingestion
        doc_id = str(db_attachment.id)
        markdown_text = ingestion.process_and_index_document(file_path, doc_id)
        
        db_attachment.extracted_text = markdown_text
        db.commit()
        db.refresh(db_attachment)
        
        return db_attachment
    except Exception as e:
        import traceback
        with open("backend_error.log", "a") as f:
            f.write(f"Error processing upload: {str(e)}\n")
            f.write(traceback.format_exc())
            f.write("\n" + "-"*50 + "\n")
        raise HTTPException(status_code=500, detail=str(e))
