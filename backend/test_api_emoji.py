
import requests
import json
from app.core.config import settings

BASE_URL = "http://localhost:8000/api"

def test_chat_emoji_retrieval():
    # 1. Create a chat
    print("Creating chat...")
    resp = requests.post(f"{BASE_URL}/chats/", json={"title": "Emoji API Test"})
    if resp.status_code != 200:
        print(f"Failed to create chat: {resp.text}")
        return
    chat_id = resp.json()["id"]
    print(f"Chat ID: {chat_id}")

    # 2. Add a message with emoji manually via DB (or simulate it if we had an endpoint, but we can just use the one created by test_emoji.py if we knew the ID, but let's just insert one via API if possible, or assume the previous test left one).
    # Actually, we can use the 'send message' endpoint but that triggers LLM.
    # Let's rely on the fact that we can just read the chat created in `test_emoji.py` if we knew its ID.
    # But `test_emoji.py` created a chat. Let's list chats and find it.
    
    print("Listing chats...")
    resp = requests.get(f"{BASE_URL}/chats/")
    chats = resp.json()
    target_chat = None
    for c in chats:
        if c["title"] == "Emoji Test Chat":
            target_chat = c
            break
            
    if not target_chat:
        print("Could not find 'Emoji Test Chat' created by previous test script. Using the new one.")
        # If we can't find it, we can't easily insert a message with emojis without triggering LLM or using direct DB.
        # Let's direct DB insert a message into this new chat.
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.models.sql_models import Message
        
        engine = create_engine(settings.DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        msg = Message(chat_id=chat_id, role="user", content="Testing API Emojis: 🚀")
        session.add(msg)
        session.commit()
        session.close()
        target_chat = {"id": chat_id}

    # 3. Retrieve the chat via API
    print(f"Retrieving chat {target_chat['id']}...")
    resp = requests.get(f"{BASE_URL}/chats/{target_chat['id']}")
    if resp.status_code != 200:
        print(f"Failed to get chat: {resp.text}")
        return
        
    data = resp.json()
    messages = data.get("messages", [])
    
    found = False
    for m in messages:
        print(f"Message content: {m['content']}")
        if "🚀" in m['content'] or "😊" in m['content'] or "🌍" in m['content']:
            found = True
            
    if found:
        print("SUCCESS: Emojis returned correctly by API.")
    else:
        print("FAILURE: Emojis NOT found in API response (likely ?? returned).")

if __name__ == "__main__":
    test_chat_emoji_retrieval()
