from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Local LLM Chat"
    API_V1_STR: str = "/api"
    
    # MS SQL Database Connection
    # Ensure ODBC Driver 17 for SQL Server is installed
    DATABASE_URL: str = "mssql+pyodbc://@localhost/LocalLLMChatDB?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
    
    # Vector Database (PostgreSQL)
    VECTOR_DB_URL: str = "postgresql://postgres:password@localhost:5432/rag_vector_db"
    
    # Ollama Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_WEB_SEARCH_KEY: str = ""

    # Uploads
    UPLOAD_DIR: str = "storage/uploads"

    class Config:
        env_file = ".env"

settings = Settings()
