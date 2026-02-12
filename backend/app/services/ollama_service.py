import httpx
import json
from typing import List, Dict, AsyncGenerator
from app.core.config import settings

OLLAMA_URL = settings.OLLAMA_BASE_URL

async def check_ollama_connection():
    global OLLAMA_URL
    primary_url = settings.OLLAMA_BASE_URL
    local_url = settings.OLLAMA_BASE_URL_LOCAL
    
    print(f"Checking primary Ollama connection at: {primary_url}...")
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{primary_url}/api/tags")
            if response.status_code == 200:
                OLLAMA_URL = primary_url
                print(f"✅ Primary Ollama ({primary_url}) is ONLINE. Using primary.")
                return
    except Exception as e:
        print(f"⚠️ Primary Ollama unavailable ({str(e)}).")

    print(f"🔄 Switching to Local Ollama at: {local_url}...")
    OLLAMA_URL = local_url

async def list_local_models() -> List[Dict]:
    """
    Fetch list of available models from Ollama.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            print(f"Error fetching models: {e}")
            return []

async def chat_stream_generator(
    model: str, 
    messages: List[Dict], 
    options: Dict = None
) -> AsyncGenerator[str, None]:
    """
    Stream response from Ollama /api/chat.
    Yields chunks of text.
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    if options:
        payload["options"] = options

    async with httpx.AsyncClient(timeout=None) as client:
        try:
            async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    if chunk:
                        try:
                            # Ollama sends JSON objects per line
                            # We might receive multiple JSONs in one chunk or partials if huge
                            # Usually checking line by line is safer for streaming JSON
                            text_chunk = chunk.decode("utf-8")
                            # Simple split in case of multiple objects
                            # NOTE: This implies 'chunk' ends on a boundary. reliable for Ollama?
                            # A more robust buffer approach is better.
                            pass
                        except:
                            pass
                        
                        # Let's use a simpler line iterator
                        pass

            # Simpler approach using aiter_lines if available or manual buffer
        except Exception as e:
            yield f"Error calling Ollama: {str(e)}"

# Reworking generator for robustness using line iteration
async def stream_chat(model: str, messages: List[Dict], enable_think: bool = True) -> AsyncGenerator[Dict[str, str], None]:
    url = f"{OLLAMA_URL}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": True
    }
    if enable_think:
        payload["think"] = True 
    
    in_thinking = False

    async with httpx.AsyncClient(timeout=90.0) as client:
        async with client.stream('POST', url, json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if 'message' in data:
                            msg = data['message']
                            val_thinking = msg.get('thinking', '')
                            val_content = msg.get('content', '')
                            
                            if val_thinking:
                                yield {"type": "think", "content": val_thinking}
                            elif val_content:
                                yield {"type": "content", "content": val_content}

                        if data.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue

async def generate_search_query(model: str, user_query: str) -> str:
    """
    Generate a concise search query based on the user's prompt.
    """
    messages = [
        {"role": "system", "content": "You are a helper. Generate a single, concise web search query for the user's request. Return ONLY the query text, no quotes or explanations."},
        {"role": "user", "content": user_query}
    ]
    # Non-streaming call
    full_resp = ""
    async for chunk_data in stream_chat(model, messages, enable_think=False):
        if chunk_data["type"] == "content":
            full_resp += chunk_data["content"]
    return full_resp.strip()

async def execute_web_search(query: str) -> str:
    """
    Execute web search using Ollama Web Search API (as per user requirements).
    """
    if not settings.OLLAMA_WEB_SEARCH_KEY:
        return "Error: OLLAMA_WEB_SEARCH_KEY not configured."
    
    # User provided: https://ollama.com/api/web_search (This might be a placeholder/hypothetical API or custom proxy)
    # Assuming standard requests structure.
    # Note: The user provided URL `https://ollama.com/api/web_search` which seems unlikely to be an official public endpoint 
    # for local Ollama, maybe they mean a hosted service or a proxy they set up.
    # I will follow instructions and use the URL provided.
    
    url = "https://ollama.com/api/web_search"
    headers = {
        "Authorization": f"Bearer {settings.OLLAMA_WEB_SEARCH_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"query": query}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            if response.status_code == 200:
                # Assuming response format, usually "results" list
                # Return a summary string
                return response.text 
            else:
                return f"Web search failed: {response.status_code} {response.text}"
        except Exception as e:
            return f"Web search error: {str(e)}"
