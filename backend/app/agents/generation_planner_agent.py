from langchain_core.messages import SystemMessage, HumanMessage
from app.core.llm_provider import LLMProvider
from app.prompts.planner import PLANNER_SYSTEM_PROMPT, PLANNER_USER_PROMPT
from app.schemas.planner import GenerationPlan
from app.core.logging import logger
import json

class GenerationPlannerAgent:
    def __init__(self):
        self.llm = LLMProvider.get_structured_llm(schema=GenerationPlan, temperature=0.1)

    def plan(
        self,
        schema_json: dict,
        profile_json: dict,
        relationships_json: dict,
        requirement: str = None,
    ) -> GenerationPlan:
        logger.info("GenerationPlannerAgent generating plan...")

        s_str = json.dumps(schema_json)[:3000]
        p_str = json.dumps(profile_json)[:2000]
        r_str = json.dumps(relationships_json)[:2000]
        user_prompt_str = requirement or "No specific requirements provided. Use best judgment."

        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=PLANNER_USER_PROMPT.format(
                schema_json=s_str,
                profile_json=p_str,
                relationships_json=r_str,
                user_prompt=user_prompt_str,
            ))
        ]

        try:
            result = self.llm.invoke(messages)
            return result
        except Exception as e:
            logger.error(f"Failed to generate plan: {e}")
            raise
