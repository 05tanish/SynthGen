from langchain_core.messages import SystemMessage, HumanMessage
from app.core.llm_provider import LLMProvider
from app.prompts.optimization import OPTIMIZATION_SYSTEM_PROMPT, OPTIMIZATION_USER_PROMPT
from app.schemas.optimization import OptimizationPlan
from app.core.logging import logger
import json

class OptimizationAgent:
    def __init__(self):
        self.llm = LLMProvider.get_structured_llm(schema=OptimizationPlan, temperature=0.2)

    def optimize(self, current_plan: dict, evaluation_report: dict, iteration: int, max_iterations: int = 3) -> OptimizationPlan:
        logger.info(f"OptimizationAgent analyzing failure on iteration {iteration}...")
        
        messages = [
            SystemMessage(content=OPTIMIZATION_SYSTEM_PROMPT),
            HumanMessage(content=OPTIMIZATION_USER_PROMPT.format(
                current_plan=json.dumps(current_plan),
                evaluation_report=json.dumps(evaluation_report)[:3000],
                iteration=iteration,
                max_iterations=max_iterations
            ))
        ]
        
        try:
            result = self.llm.invoke(messages)
            return result
        except Exception as e:
            logger.error(f"Failed to optimize plan: {e}")
            raise
