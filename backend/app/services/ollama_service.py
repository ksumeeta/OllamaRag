import httpx
import json
from typing import List, Dict, AsyncGenerator
from app.core.config import settings
import logging

# Configure Logging
logger = logging.getLogger(__name__)

OLLAMA_URL = settings.OLLAMA_BASE_URL

async def check_ollama_connection():
    global OLLAMA_URL
    primary_url = settings.OLLAMA_BASE_URL
    local_url = settings.OLLAMA_BASE_URL_LOCAL
    
    logger.info(f"Checking primary Ollama connection at: {primary_url}...")
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{primary_url}/api/tags")
            if response.status_code == 200:
                OLLAMA_URL = primary_url
                logger.info(f"✅ Primary Ollama ({primary_url}) is ONLINE. Using primary.")
                return
    except Exception as e:
        logger.warning(f"⚠️ Primary Ollama unavailable ({str(e)}).")

    logger.info(f"🔄 Switching to Local Ollama at: {local_url}...")
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
            logger.error(f"Error fetching models: {e}")
            return []


# Reworking generator for robustness using line iteration
async def stream_chat(model: str, messages: List[Dict], enable_think: bool = False) -> AsyncGenerator[Dict[str, str], None]:
    url = f"{OLLAMA_URL}/api/chat"
    
    # 1. Prepare initial payload
    payload = {
        "model": model,
        "messages": messages,
        "stream": True
    }
    # If user explicitly requested thinking, or if we default to trying it (e.g. for reasoning models)
    # The previous fix set enable_think=False by default to be safe.
    # But if the user WANTS to support reasoning models automatically, we should defaults to True *but fallback*.
    # If user explicitly requested thinking, enable it.
    
    use_thinking = enable_think
    if enable_think:
         payload["think"] = True

    # Debug: Log payload preview (User Request)
    logger.info("--- Stream Chat Payload Debug ---")
    for key, value in payload.items():
        if key == "messages" and isinstance(value, list):
            logger.info(f"Key: {key} (List with {len(value)} items):")
            for i, msg in enumerate(value):
                role = msg.get('role', 'unknown')
                content = str(msg.get('content', ''))
                logger.info(f"  [{i}] Role: {role}, Content Preview: {content[:50]}...")
        else:
            val_str = str(value)
            logger.info(f"Key: {key}, Value Preview: {val_str[:50]}...")
    logger.info("---------------------------------")

    async with httpx.AsyncClient(timeout=120.0) as client:
        should_retry_without_think = False
        
        # Attempt 1
        try:
            async with client.stream('POST', url, json=payload) as response:
                if response.status_code == 400:
                    # check error
                    content = await response.aread()
                    try:
                        err_json = json.loads(content)
                        err_msg = err_json.get("error", "")
                    except:
                        err_msg = content.decode('utf-8')
                        
                    if "does not support thinking" in err_msg:
                        logger.info(f"Model '{model}' does not support thinking. Retrying without 'think' param.")
                        should_retry_without_think = True
                    else:
                        raise Exception(f"Ollama Error ({response.status_code}): {err_msg}")
                elif response.status_code != 200:
                     # Other errors
                    content = await response.aread()
                    raise Exception(f"Ollama Error ({response.status_code}): {content.decode('utf-8')}")
                else:
                    # Success - yield stream
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if 'error' in data:
                                     raise Exception(f"Ollama Stream Error: {data['error']}")
                                     
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
        except httpx.ConnectError as e:
             raise Exception(f"Could not connect to Ollama: {e}")

        # Attempt 2 (Fallback)
        if should_retry_without_think:
            del payload["think"]
            async with client.stream('POST', url, json=payload) as response:
                if response.status_code != 200:
                     content = await response.aread()
                     raise Exception(f"Ollama Error ({response.status_code}) on retry: {content.decode('utf-8')}")
                     
                async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if 'error' in data:
                                     raise Exception(f"Ollama Stream Error: {data['error']}")

                                if 'message' in data:
                                    msg = data['message']
                                    # No thinking here obviously
                                    val_content = msg.get('content', '')
                                    if val_content:
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
