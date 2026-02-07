
import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services import ingestion

def test_docling():
    file_path = "storage/uploads/2026-02-07/AA CAR Presentation - September 25.pdf.pdf"
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        # Try to find any pdf
        import glob
        pdfs = glob.glob("storage/uploads/**/*.pdf", recursive=True)
        if pdfs:
            file_path = pdfs[0]
            print(f"Using found PDF: {file_path}")
        else:
            print("No PDF found to test.")
            return

    print(f"Testing ingestion on: {file_path}")
    try:
        # We need a dummy doc_id
        doc_id = "test_doc_id_123"
        result = ingestion.process_and_index_document(file_path, doc_id)
        
        print(f"\nIgnestion call returned text length: {len(result)}")
        
        # Verify Persistence
        from app.core.database import VectorSessionLocal, get_db
        from app.models.vector_models import DocumentChunk
        from app.core.config import settings
        
        print(f"Vector DB URL: {settings.VECTOR_DB_URL.split('@')[1] if '@' in settings.VECTOR_DB_URL else settings.VECTOR_DB_URL}")
        
        vdb = VectorSessionLocal()
        chunks = vdb.query(DocumentChunk).filter(DocumentChunk.doc_id == doc_id).all()
        print(f"Verify chunks for {doc_id}: {len(chunks)}")
        vdb.close()
        
    except Exception as e:
        print(f"Caught Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_docling()
