from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Agentic AI Synthetic Data Generator"
    
    # DB
    DATABASE_URL: str = "sqlite:///./app.db"
    
    # Redis
    UPSTASH_REDIS_URL: str = ""
    UPSTASH_REDIS_TOKEN: Optional[str] = None  # Not needed for local Redis
    
    # LLM
    LLM_PROVIDER: str = "groq"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    
    # Langfuse Observability (optional)
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"  # or self-hosted URL
    LANGFUSE_ENABLED: bool = True  # Set to False to disable
    
    # Generator Settings
    MAX_ITERATIONS: int = 5
    QUALITY_THRESHOLD: float = 0.65
    MAX_CONCURRENT_JOBS: int = 2  # Limit simultaneous SDV model training
    
    # Other settings
    FILE_STORAGE_PATH: str = "./storage"
    MAX_UPLOAD_SIZE_MB: int = 50
    RESEND_API_KEY: Optional[str] = None
    
    # Cloudinary (file storage)
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    
    # Auth
    SECRET_KEY: str = "changeme-insecure-default-please-set-in-env"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    GOOGLE_CLIENT_ID: str = ""  # No default - must be set in .env
    
    # Frontend URL for CORS
    FRONTEND_URL: Optional[str] = None

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore")

settings = Settings()
