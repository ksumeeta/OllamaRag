
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, UnicodeText
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Setup
db_url = settings.DATABASE_URL
engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_emoji_persistence():
    session = SessionLocal()
    try:
        # Create a test message
        test_content = "Hello 🌍! This is a test with emojis: 😊 🎉 🔥"
        
        # We need to insert into the Messages table. Since we don't want to import full models if we can avoid it, 
        # let's assume the table exists as defined in the models.
        # However, to be safe, let's use the ORM models if available or raw SQL.
        
        # Raw SQL might be safer to verify exactly what's sent.
        # But let's try ORM first as that's what the app uses.
        from app.models.sql_models import Message, Chat
        
        # Create a dummy chat first
        chat = Chat(title="Emoji Test Chat")
        session.add(chat)
        session.commit()
        session.refresh(chat)
        
        msg = Message(chat_id=chat.id, role="user", content=test_content)
        session.add(msg)
        session.commit()
        session.refresh(msg)
        
        print(f"Original content: {test_content}")
        print(f"Saved content:    {msg.content}")
        
        if msg.content == test_content:
            print("SUCCESS: Emojis preserved correctly!")
        else:
            print("FAILURE: Emojis were corrupted.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    test_emoji_persistence()
