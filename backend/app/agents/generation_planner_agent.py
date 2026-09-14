from langchain_core.messages import SystemMessage, HumanMessage
from app.core.llm_provider import LLMProvider
from app.prompts.planner import PLANNER_SYSTEM_PROMPT, PLANNER_USER_PROMPT
from app.schemas.planner import GenerationPlan
from app.core.logging import logger
import json

# Context size limits (chars)
SCHEMA_CONTEXT_LIMIT = 1500
PROFILE_CONTEXT_LIMIT = 1000
RELATIONSHIPS_CONTEXT_LIMIT = 1000
REQUIREMENT_ANALYSIS_LIMIT = 500

class GenerationPlannerAgent:
    def __init__(self):
        self.llm = LLMProvider.get_structured_llm(schema=GenerationPlan, temperature=0.1)

    def plan(
        self,
        schema_json: dict,
        profile_json: dict,
        relationships_json: dict,
        requirement: str = None,
        requirement_analysis: dict = None,
    ) -> GenerationPlan:
        logger.info("GenerationPlannerAgent generating plan...")

        # Validate and truncate contexts to limits
        s_str = json.dumps(schema_json)
        if len(s_str) > SCHEMA_CONTEXT_LIMIT:
            logger.warning(f"Schema context ({len(s_str)} chars) exceeds {SCHEMA_CONTEXT_LIMIT} limit. Truncating.")
            s_str = s_str[:SCHEMA_CONTEXT_LIMIT]
        
        p_str = json.dumps(profile_json)
        if len(p_str) > PROFILE_CONTEXT_LIMIT:
            logger.warning(f"Profile context ({len(p_str)} chars) exceeds {PROFILE_CONTEXT_LIMIT} limit. Truncating.")
            p_str = p_str[:PROFILE_CONTEXT_LIMIT]
        
        r_str = json.dumps(relationships_json)
        if len(r_str) > RELATIONSHIPS_CONTEXT_LIMIT:
            logger.warning(f"Relationships context ({len(r_str)} chars) exceeds {RELATIONSHIPS_CONTEXT_LIMIT} limit. Truncating.")
            r_str = r_str[:RELATIONSHIPS_CONTEXT_LIMIT]
        
        user_prompt_str = requirement or "No specific requirements provided. Use best judgment."
        if len(user_prompt_str) > 2000:
            logger.warning(f"User prompt ({len(user_prompt_str)} chars) exceeds 2000 limit. Truncating.")
            user_prompt_str = user_prompt_str[:2000]
        
        req_analysis_str = json.dumps(requirement_analysis)[:REQUIREMENT_ANALYSIS_LIMIT] if requirement_analysis else "None"

        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=PLANNER_USER_PROMPT.format(
                schema_json=s_str,
                profile_json=p_str,
                relationships_json=r_str,
                user_prompt=user_prompt_str,
                requirement_analysis=req_analysis_str,
            ))
        ]

        try:
            result = self.llm.invoke(messages)
            return result
        except Exception as e:
            logger.error(f"Failed to generate plan: {e}. Falling back to default plan.")
            return GenerationPlan(
                selected_model="CTGAN",
                reasoning="Fallback plan due to API rate limit or error.",
                parameters={"epochs": 50, "batch_size": 100}
            )
