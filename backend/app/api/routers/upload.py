from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import sql_models as models
from app import schemas
from app.services import file_service
from datetime import datetime

router = APIRouter()

@router.post("/", response_model=schemas.Attachment)
async def upload_file(
    file: UploadFile = File(...),
    overwrite: bool = Form(False), # Using Form to receive boolean
    db: Session = Depends(get_db)
):
    import os
    try:
        # Check for existing file
        existing_attachment = db.query(models.Attachment).filter(models.Attachment.file_name == file.filename).first()

        if existing_attachment:
            if not overwrite:
                raise HTTPException(
                    status_code=400, 
                    detail=f"The file '{file.filename}' already exists. Enable 'Overwrite File' to update it."
                )
            
            # --- OVERWRITE LOGIC ---
            print(f"DEBUG: Overwriting file {file.filename} (ID: {existing_attachment.id})")
            
            # 1. Delete from Vector DB
            from app.services import ingestion
            doc_id = str(existing_attachment.id)
            ingestion.delete_document_chunks(doc_id)
            
            # 2. Delete existing file from disk
            if existing_attachment.file_path and os.path.exists(existing_attachment.file_path):
                try:
                    os.remove(existing_attachment.file_path)
                    print(f"DEBUG: Deleted old file: {existing_attachment.file_path}")
                except Exception as e:
                    print(f"Warning: Could not delete old file: {e}")
            
            # 3. Save New File (Disk)
            # This creates a new file, potentially in a new date-folder
            file_path, file_size = await file_service.save_upload_file(file)
            
            # 4. Update SQL Record
            existing_attachment.file_path = file_path
            existing_attachment.file_size = file_size
            existing_attachment.created_at = datetime.utcnow() # Update timestamp
            existing_attachment.extracted_text = "" # Reset
            
            db.commit()
            db.refresh(existing_attachment)
            
            # 5. Process & Re-Index
            markdown_text = ingestion.process_and_index_document(file_path, doc_id)
            
            existing_attachment.extracted_text = markdown_text
            db.commit()
            db.refresh(existing_attachment)
            
            return existing_attachment

        else:
            # --- NEW FILE LOGIC ---
            file_path, file_size = await file_service.save_upload_file(file)
            
            # Create Attachment
            db_attachment = models.Attachment(
                file_name=file.filename,
                file_type=file.content_type or "application/octet-stream",
                file_size=file_size,
                file_path=file_path,
                extracted_text="" 
            )
            db.add(db_attachment)
            db.commit()
            db.refresh(db_attachment)
            
            # Process
            from app.services import ingestion
            doc_id = str(db_attachment.id)
            markdown_text = ingestion.process_and_index_document(file_path, doc_id)
            
            db_attachment.extracted_text = markdown_text
            db.commit()
            db.refresh(db_attachment)
            
            return db_attachment

    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        with open("backend_error.log", "a") as f:
            f.write(f"Error processing upload: {str(e)}\n")
            f.write(traceback.format_exc())
            f.write("\n" + "-"*50 + "\n")
        raise HTTPException(status_code=500, detail=str(e))
