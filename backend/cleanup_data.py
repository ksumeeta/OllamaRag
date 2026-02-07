import os
import shutil
from sqlalchemy import create_engine, text
from app.core.config import settings

# 1. Clear MSSQL Database
print("Cleaning MSSQL Database...")
try:
    mssql_engine = create_engine(settings.DATABASE_URL)
    with mssql_engine.connect() as conn:
        # Order matters due to foreign keys
        tables_to_clear = [
            "MessageContext",
            "Attachments",
            "Messages",
            "ChatTags",
            "Tags",
            "Chats"
        ]
        for table in tables_to_clear:
            print(f"  Deleting from {table}...")
            conn.execute(text(f"DELETE FROM {table}"))
        conn.commit()
    print("MSSQL Database cleared.")
except Exception as e:
    print(f"Error cleaning MSSQL: {e}")

# 2. Clear PostgreSQL Vector Database
print("\nCleaning PostgreSQL Vector Database...")
try:
    # Use the vector db url from settings
    if settings.VECTOR_DB_URL:
        pg_engine = create_engine(settings.VECTOR_DB_URL)
        with pg_engine.connect() as conn:
            print("  Truncating document_chunks...")
            conn.execute(text("TRUNCATE TABLE document_chunks"))
            conn.commit()
        print("PostgreSQL Vector Database cleared.")
    else:
        print("Vector DB URL not set, skipping.")
except Exception as e:
    print(f"Error cleaning PostgreSQL: {e}")

# 3. Clear File Storage
print("\nCleaning File Storage...")
upload_dir = os.path.join(os.getcwd(), "storage", "uploads")
# The script might be run from root, so we check path
if not os.path.exists(upload_dir):
    # Try relative to backend
    upload_dir = os.path.join(os.getcwd(), "backend", "storage", "uploads")

if os.path.exists(upload_dir):
    try:
        files = os.listdir(upload_dir)
        for f in files:
            file_path = os.path.join(upload_dir, f)
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"  Deleted {f}")
        print("File storage cleared.")
    except Exception as e:
        print(f"Error cleaning file storage: {e}")
else:
    print(f"Upload directory not found at {upload_dir}")

print("\nPhase ZERO Cleanup Complete.")
