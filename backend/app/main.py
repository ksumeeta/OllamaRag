from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import chats, models, tags, upload
from app.core.database import engine, Base, vector_engine
from app.models.vector_models import BaseVector
from app.core.config import settings

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
        print(f"Warning: Could not enable vector extension: {e}")
    
    BaseVector.metadata.create_all(bind=vector_engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
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
    return {"message": "Local LLM Chat Backend Running"}
