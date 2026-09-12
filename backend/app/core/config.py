from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Agentic AI Synthetic Data Generator"
    
    # DB
    DATABASE_URL: str
    
    # Redis
    UPSTASH_REDIS_URL: str
    UPSTASH_REDIS_TOKEN: str
    
    # LLM
    LLM_PROVIDER: str = "groq"
    LLM_API_KEY: str
    LLM_MODEL: str = "openai/gpt-oss-20b"
    
    # Generator Settings
    MAX_ITERATIONS: int = 5
    QUALITY_THRESHOLD: float = 0.65
    
    # Other settings
    FILE_STORAGE_PATH: str = "./storage"
    MAX_UPLOAD_SIZE_MB: int = 50
    RESEND_API_KEY: Optional[str] = None
    
    # Auth
    SECRET_KEY: str = "agentic-ai-super-secret-key-change-in-prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days

    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
