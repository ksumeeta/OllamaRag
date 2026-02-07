from sqlalchemy import create_engine, text
from app.core.config import settings

def run_migration():
    print("Running Helper Migration...")
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        # 1. Add augmented_content to Messages
        try:
            print("Attempting to add augmented_content to Messages...")
            conn.execute(text("ALTER TABLE Messages ADD augmented_content NVARCHAR(MAX) NULL;"))
            conn.commit()
            print("Success: augmented_content added.")
        except Exception as e:
            print(f"Info: augmented_content might already exist or error: {e}")

        # 2. Create MessageContext Table (if not exists via SQLAlchemy logic usually, but here we enforce if needed or let main.py do it)
        # Main.py uses create_all, which works for new tables. MessageContext is new.
        # So we just need to ensure Messages table is updated.
        
        # However, we also need to make sure MessageContext table is created if create_all doesn't run again or if we want to force it.
        # Base.metadata.create_all(bind=engine) will be called in main.py.
        # But if the app is already running (reloading), it might have missed it?
        # Let's let main.py handle new table creation. This script is just for ALTER.

if __name__ == "__main__":
    run_migration()
