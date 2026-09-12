from pydantic_settings import BaseSettings, SettingsConfigDict

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
    
    # Storage
    FILE_STORAGE_PATH: str = "./storage"
    MAX_UPLOAD_SIZE_MB: int = 100

    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
