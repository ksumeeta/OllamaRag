
import os
import shutil
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.core.database import engine, Base, vector_engine
from app.models.sql_models import Chat, Message, Tag, Attachment, MessageContext, chat_tags  # Import all models to register with Base
from app.models.vector_models import BaseVector, DocumentChunk

def reset_mssql():
    print("Resetting MSSQL Database...")
    try:
        # Drop all tables
        print("  Dropping all MSSQL tables...")
        Base.metadata.drop_all(bind=engine)
        print("  MSSQL tables dropped.")
        
        # Recreate all tables
        print("  Recreating MSSQL tables...")
        Base.metadata.create_all(bind=engine)
        print("  MSSQL tables recreated successfully.")
    except Exception as e:
        print(f"Error resetting MSSQL: {e}")

def reset_postgres():
    print("\nResetting PostgreSQL Vector Database...")
    if not vector_engine:
        print("Vector DB URL not set, skipping.")
        return

    try:
        # Drop all tables
        print("  Dropping all Vector DB tables...")
        BaseVector.metadata.drop_all(bind=vector_engine)
        print("  Vector DB tables dropped.")

        # Recreate extensions and tables
        print("  Recreating Vector DB tables...")
        with vector_engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        
        BaseVector.metadata.create_all(bind=vector_engine)
        print("  Vector DB tables recreated successfully.")
    except Exception as e:
        print(f"Error resetting PostgreSQL: {e}")

def reset_storage():
    print("\nCleaning File Storage...")
    # Determine upload directory based on current working directory
    current_dir = os.getcwd()
    if current_dir.endswith("backend"):
        upload_dir = os.path.join(current_dir, "storage", "uploads")
    else:
        upload_dir = os.path.join(current_dir, "backend", "storage", "uploads")

    print(f"  Target upload directory: {upload_dir}")

    if os.path.exists(upload_dir):
        try:
            files = os.listdir(upload_dir)
            count = 0
            for f in files:
                file_path = os.path.join(upload_dir, f)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    count += 1
            print(f"  Deleted {count} files from storage.")
        except Exception as e:
            print(f"Error cleaning file storage: {e}")
    else:
        print(f"  Upload directory not found, creating it.")
        os.makedirs(upload_dir, exist_ok=True)
        print("  Upload directory created.")

if __name__ == "__main__":
    print("Starting Phase ZERO Full Reset & Recreate...")
    reset_mssql()
    reset_postgres()
    reset_storage()
    print("\nFull Reset & Recreate Complete.")
