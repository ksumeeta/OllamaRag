import httpx
import json

API_URL = "http://localhost:8000/api/chats"
ATTACHMENT_ID = 24

def test_qa():
    with httpx.Client(timeout=60.0) as client:
        # 1. Create Chat
        print("Creating Chat for Q&A...")
        resp = client.post(f"{API_URL}/", json={"title": "Test Chat Q&A"})
        chat_id = resp.json()["id"]
        print(f"Chat created. ID: {chat_id}")
        
        # 2. Ask Question
        question = "Who should I contact in case of emergency?"
        print(f"Asking: '{question}'")
        msg_payload = {
            "chat_id": chat_id,
            "content": question,
            "attachments": [ATTACHMENT_ID],
            "use_llm_data": False,
            "use_documents": True,
            "model_used": "llama3.1:8b" 
        }
        
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
                     except:
                         pass
        print("\n\nQ&A Complete.")
        
        if "555-0100" in full_response:
             print("PASS: Correct answer found.")
        else:
             print("FAIL: Answer might be incorrect.")

if __name__ == "__main__":
    test_qa()
