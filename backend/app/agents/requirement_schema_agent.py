from langchain_core.messages import SystemMessage, HumanMessage
from app.core.llm_provider import LLMProvider
from app.prompts.requirement import REQUIREMENT_SYSTEM_PROMPT, REQUIREMENT_USER_PROMPT
from app.schemas.common import RequirementAnalysis
from app.core.logging import logger

# User requirement limit
USER_REQUIREMENT_LIMIT = 2000

class RequirementSchemaAgent:
    def __init__(self):
        self.llm = LLMProvider.get_structured_llm(schema=RequirementAnalysis, temperature=0.1)

    def analyze_requirement(self, requirement: str) -> RequirementAnalysis:
        logger.info(f"RequirementSchemaAgent analyzing: {requirement[:50]}...")
        
        # Validate requirement length
        if len(requirement) > USER_REQUIREMENT_LIMIT:
            logger.warning(f"Requirement ({len(requirement)} chars) exceeds {USER_REQUIREMENT_LIMIT} limit. Truncating.")
            requirement = requirement[:USER_REQUIREMENT_LIMIT]
        
        messages = [
            SystemMessage(content=REQUIREMENT_SYSTEM_PROMPT),
            HumanMessage(content=REQUIREMENT_USER_PROMPT.format(requirement=requirement))
        ]
        
        try:
            result = self.llm.invoke(messages)
            return result
        except Exception as e:
            logger.error(f"Failed to analyze requirement: {e}")
            raise
