from langchain_groq import ChatGroq
from langchain_core.language_models import BaseChatModel
from app.core.config import settings
from typing import Type
from pydantic import BaseModel

class LLMProvider:
    @staticmethod
    def get_llm(temperature: float = 0.0) -> BaseChatModel:
        """Get the configured LLM instance"""
        if settings.LLM_PROVIDER.lower() == "groq":
            return ChatGroq(
                temperature=temperature,
                model_name=settings.LLM_MODEL,
                api_key=settings.LLM_API_KEY
            )
        # Fallback to a placeholder or raise error if unsupported
        raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")
        
    @staticmethod
    def get_structured_llm(schema: Type[BaseModel], temperature: float = 0.0):
        """Get an LLM bound to output a specific Pydantic schema"""
        llm = LLMProvider.get_llm(temperature)
        return llm.with_structured_output(schema).with_retry(
            stop_after_attempt=3, 
            wait_exponential_jitter=True
        )
