import httpx
import json

API_URL = "http://localhost:8000/api/chats"
ATTACHMENT_ID = 24 # From previous step. Ideally should fetch dynamically but hardcoding for test

def test_summary():
    with httpx.Client(timeout=60.0) as client:
        # 1. Create Chat
        print("Creating Chat...")
        resp = client.post(f"{API_URL}/", json={"title": "Test Chat"})
        if resp.status_code != 200:
            print(f"Failed to create chat: {resp.text}")
            return
        chat_id = resp.json()["id"]
        print(f"Chat created. ID: {chat_id}")

        # 2. Update Chat with attachment (Wait, logic says we pass attachment ID in message)
        # MessageCreate schema: chat_id, content, attachments=[id]
        
        # 3. Send Message for Summary
        print("Requesting Summary...")
        msg_payload = {
            "chat_id": chat_id,
            "content": "Please summarize the uploaded document.",
            "attachments": [ATTACHMENT_ID],
            "use_llm_data": False, # Strict RAG
            "use_documents": True,
            "use_web_search": False,
            "model_used": "llama3.1:8b" 
        }
        
        # The endpoint returns a StreamingResponse (SSE)
        # We need to handle that.
        full_response = ""
        with client.stream("POST", f"{API_URL}/message", json=msg_payload) as response:
             for line in response.iter_lines():
                 if line.startswith("data: "):
                     data_str = line[6:]
                     if data_str == "[DONE]":
                         break
                     try:
                         data = json.loads(data_str)
                         if "chunk" in data:
                             full_response += data["chunk"]
                             print(data["chunk"], end="", flush=True)
                         if "error" in data:
                             print(f"\nError: {data['error']}")
                     except:
                         pass
        print("\n\nSummary Received.")
        return full_response

if __name__ == "__main__":
    test_summary()
