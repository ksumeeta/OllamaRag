from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.services.ollama_service import list_local_models

router = APIRouter()

@router.get("/", response_model=List[Dict[str, Any]])
async def get_models():
    """
    List all available local Ollama models.
    """
    models = await list_local_models()
    return models
