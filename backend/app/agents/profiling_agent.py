from langchain_core.messages import SystemMessage, HumanMessage
from app.core.llm_provider import LLMProvider
from app.prompts.profiling import PROFILING_SYSTEM_PROMPT, PROFILING_USER_PROMPT
from app.core.logging import logger
import json

# Context size limits (chars) - standardized across all agents
PROFILE_CONTEXT_LIMIT = 1000
RELATIONSHIPS_CONTEXT_LIMIT = 1000

class ProfilingAgent:
    def __init__(self):
        # Profiling agent just needs standard text output, no strict Pydantic parsing needed for summary
        self.llm = LLMProvider.get_llm(temperature=0.2)

    def analyze_profile(self, profile_json: dict, relationships_json: dict) -> str:
        logger.info("ProfilingAgent analyzing deterministic profiles...")
        
        # Serialize dicts to string for prompt with consistent limits
        p_str = json.dumps(profile_json, indent=2)
        if len(p_str) > PROFILE_CONTEXT_LIMIT:
            logger.warning(f"Profile context ({len(p_str)} chars) exceeds {PROFILE_CONTEXT_LIMIT} limit. Truncating.")
            p_str = p_str[:PROFILE_CONTEXT_LIMIT]
        
        r_str = json.dumps(relationships_json, indent=2)
        if len(r_str) > RELATIONSHIPS_CONTEXT_LIMIT:
            logger.warning(f"Relationships context ({len(r_str)} chars) exceeds {RELATIONSHIPS_CONTEXT_LIMIT} limit. Truncating.")
            r_str = r_str[:RELATIONSHIPS_CONTEXT_LIMIT]
        
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
