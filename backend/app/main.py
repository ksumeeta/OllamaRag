from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.routers import chats, models, tags, upload
from app.core.database import engine, Base, vector_engine
from app.models.vector_models import BaseVector
from app.core.config import settings
from app.services.ollama_service import check_ollama_connection
import logging

# Configure Logging
# Using force=True to override default handlers and ensure consistent formatting
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-9s %(name)-40s %(message)s",
    force=True
)
logger = logging.getLogger(__name__)

# Create Tables (MS SQL)
Base.metadata.create_all(bind=engine)

# Create Tables (Vector DB)
if vector_engine:
    from sqlalchemy import text
    try:
        with vector_engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    except Exception as e:
        logger.error(f"Warning: Could not enable vector extension: {e}")
    
    BaseVector.metadata.create_all(bind=vector_engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI application.
    Handles startup and shutdown events.
    """
    # Check Ollama Connection on Startup
    await check_ollama_connection()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS
origins = [
    "http://localhost",
    "http://localhost:3000", # React default
    "http://localhost:5173", # Vite default
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(models.router, prefix=f"{settings.API_V1_STR}/models", tags=["models"])
app.include_router(chats.router, prefix=f"{settings.API_V1_STR}/chats", tags=["chats"]) # Includes /message
app.include_router(tags.router, prefix=f"{settings.API_V1_STR}/tags", tags=["tags"])
app.include_router(upload.router, prefix=f"{settings.API_V1_STR}/upload", tags=["upload"])

@app.get("/")
def read_root():
    """
    Root endpoint to verify backend status.
    """
    return {"message": "Local LLM Chat Backend Running"}
