from sqlalchemy import create_engine, text
from app.core.config import settings
import os

def verify():
    print("Verifying Ingestion...")
    
    # 1. Check File Storage
    upload_dir = os.path.join(os.getcwd(), "storage", "uploads")
    # Need to handle date dir
    found_file = False
    for root, dirs, files in os.walk(upload_dir):
        for file in files:
            if "test_ingestion.txt" in file:
                print(f"PASS: File found at {os.path.join(root, file)}")
                found_file = True
                break
    if not found_file:
        print("FAIL: File not found in storage.")

    # 2. Check MSSQL
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, file_name, extracted_text FROM Attachments WHERE file_name='test_ingestion.txt' ORDER BY id DESC")).fetchone()
            if result:
                print(f"PASS: MSSQL Attachment found. ID: {result[0]}, Name: {result[1]}")
                if result[2] and "Project Alpha" in result[2]:
                    print("PASS: Extracted text verified.")
                else:
                    print("FAIL: Extracted text missing or incorrect.")
            else:
                print("FAIL: Attachment not found in MSSQL.")
    except Exception as e:
        print(f"Error checking MSSQL: {e}")

    # 3. Check Vector DB
    try:
        if settings.VECTOR_DB_URL:
            pg_engine = create_engine(settings.VECTOR_DB_URL)
            with pg_engine.connect() as conn:
                # We need the doc_id. From MSSQL result above, but let's just query by text content if unique
                # Or query all and see if any match our content
                result = conn.execute(text("SELECT COUNT(*) FROM document_chunks")).fetchone()
                count = result[0]
                print(f"Vector DB Chunk Count: {count}")
                if count > 0:
                    print("PASS: Vector DB has chunks.")
                    # Check content
                    row = conn.execute(text("SELECT text FROM document_chunks LIMIT 1")).fetchone()
                    print(f"Sample Chunk Text: {row[0][:50]}...")
                else:
                    print("FAIL: Vector DB is empty.")
    except Exception as e:
        print(f"Error checking Vector DB: {e}")

if __name__ == "__main__":
    verify()
