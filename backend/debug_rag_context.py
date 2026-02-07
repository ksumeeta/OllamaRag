
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_db, SessionLocal
from app.models import sql_models as models
from app.services import ingestion

def debug_rag():
    db = SessionLocal()
    try:
        # Get latest chat
        latest_chat = db.query(models.Chat).order_by(models.Chat.updated_at.desc()).first()
        if not latest_chat:
            print("No chats found.")
            return

        print(f"Latest Chat ID: {latest_chat.id}, Title: {latest_chat.title}")
        
        # Get attachments
        attachments = db.query(models.Attachment).filter(models.Attachment.chat_id == latest_chat.id).all()
        print(f"Attachments found: {len(attachments)}")
        
        doc_ids = []
        for att in attachments:
            print(f" - Attachment ID: {att.id}, Name: {att.file_name}, Text Len: {len(att.extracted_text) if att.extracted_text else 0}, File Path: {att.file_path}")
            if att.extracted_text:
                doc_ids.append(str(att.id))
        
        if not doc_ids:
            print("No attachments with extracted text found.")
            return

        query = "summarise this document"
        print(f"\nRunning retrieval for query: '{query}' with doc_ids: {doc_ids}")
        
        chunks = ingestion.retrieve_relevant_chunks(query, doc_ids, top_k=5)
        print(f"Chunks retrieved: {len(chunks)}")
        
        for i, chunk in enumerate(chunks):
            print(f"--- Chunk {i+1} ---")
            print(f"Score: {chunk.get('score')}")
            print(f"Text preview: {chunk.get('text')[:200]}...")
            print(f"Metadata: {chunk.get('meta')}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def list_all_chunks():
    print("\n--- Listing ALL Chunks in Vector DB ---")
    from app.core.database import VectorSessionLocal
    from app.models.vector_models import DocumentChunk
    
    if not VectorSessionLocal:
        print("Vector DB not configured.")
        return

    vdb = VectorSessionLocal()
    try:
        chunks = vdb.query(DocumentChunk).limit(20).all()
        print(f"Total chunks found (limit 20): {len(chunks)}")
        for i, chunk in enumerate(chunks):
            print(f"Chunk {i+1}: ID={chunk.id}, DocID={chunk.doc_id}, TextLen={len(chunk.text)}")
    except Exception as e:
        print(f"Error listing chunks: {e}")
    finally:
        vdb.close()

if __name__ == "__main__":
    list_all_chunks()
    debug_rag()
