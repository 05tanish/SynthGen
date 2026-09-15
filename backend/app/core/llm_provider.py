from langchain_groq import ChatGroq
from langchain_core.language_models import BaseChatModel
from app.core.config import settings
from typing import Type
from pydantic import BaseModel

class LLMProvider:
    @staticmethod
    def get_llm(temperature: float = 0.0) -> BaseChatModel:
        """Get the configured LLM instance"""
        if not settings.LLM_API_KEY:
            raise ValueError("LLM_API_KEY environment variable is not set. Please configure it in Railway.")
        
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
        """Get an LLM bound to output a specific Pydantic schema using PydanticOutputParser to bypass Groq tool bugs."""
        from langchain_core.output_parsers import PydanticOutputParser
        from langchain_core.messages import SystemMessage, HumanMessage
        
        llm = LLMProvider.get_llm(temperature)
        parser = PydanticOutputParser(pydantic_object=schema)
        
        def inject_instructions(input_data):
            instructions = "You MUST output valid JSON matching the following schema:\\n" + parser.get_format_instructions()
            sys_msg = SystemMessage(content=instructions)
            
            if isinstance(input_data, str):
                return [sys_msg, HumanMessage(content=input_data)]
            elif isinstance(input_data, list):
                return [sys_msg] + input_data
            return input_data

        chain = inject_instructions | llm | parser
        return chain.with_retry(
            stop_after_attempt=3, 
            wait_exponential_jitter=True
        )
