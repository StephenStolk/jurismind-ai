from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "Indian Legal Document Intelligence"
    DEBUG: bool = False
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000", 
        "http://localhost:5173",
        "https://*.vercel.app",
        ]
    
    # LLM
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str
    LLM_MODEL: str = "openai/gpt-oss-120b:free"
    
    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "legal_docs"
    
    # Embeddings model — multilingual, supports Hindi + English
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # Uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 20

    # MLflow
    MLFLOW_TRACKING_URI: str
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
settings = Settings()