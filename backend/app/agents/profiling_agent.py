from langchain_core.messages import SystemMessage, HumanMessage
from app.core.llm_provider import LLMProvider
from app.prompts.profiling import PROFILING_SYSTEM_PROMPT, PROFILING_USER_PROMPT
from app.core.logging import logger
import json

class ProfilingAgent:
    def __init__(self):
        # Profiling agent just needs standard text output, no strict Pydantic parsing needed for summary
        self.llm = LLMProvider.get_llm(temperature=0.2)

    def analyze_profile(self, profile_json: dict, relationships_json: dict) -> str:
        logger.info("ProfilingAgent analyzing deterministic profiles...")
        
        # Serialize dicts to string for prompt
        p_str = json.dumps(profile_json, indent=2)[:4000] # truncate to avoid token limits if massive
        r_str = json.dumps(relationships_json, indent=2)[:2000]
        
        messages = [
            SystemMessage(content=PROFILING_SYSTEM_PROMPT),
            HumanMessage(content=PROFILING_USER_PROMPT.format(
                profile_json=p_str, 
                relationships_json=r_str
            ))
        ]
        
        try:
            result = self.llm.invoke(messages)
            return result.content
        except Exception as e:
            logger.error(f"Failed to analyze profile with LLM: {e}")
            raise
