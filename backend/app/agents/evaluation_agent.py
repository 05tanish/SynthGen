from langchain_core.messages import SystemMessage, HumanMessage
from app.core.llm_provider import LLMProvider
from app.prompts.evaluation import EVALUATION_SYSTEM_PROMPT, EVALUATION_USER_PROMPT
from app.schemas.evaluation import EvaluationReport
from app.core.logging import logger
import json

class EvaluationAgent:
    def __init__(self):
        self.llm = LLMProvider.get_llm(temperature=0.2)

    def summarize_evaluation(self, report: EvaluationReport) -> str:
        logger.info("EvaluationAgent summarizing deterministic report...")
        
        # Serialize dicts
        s_details = json.dumps(report.statistical_details, indent=2)[:2000]
        p_details = json.dumps(report.privacy_details, indent=2)[:2000]
        m_details = json.dumps(report.ml_utility_details, indent=2)[:2000]
        
        messages = [
            SystemMessage(content=EVALUATION_SYSTEM_PROMPT),
            HumanMessage(content=EVALUATION_USER_PROMPT.format(
                overall_score=report.overall_score,
                passed=report.passed,
                statistical_score=report.statistical_score,
                privacy_score=report.privacy_score,
                ml_utility_score=report.ml_utility_score,
                statistical_details=s_details,
                privacy_details=p_details,
                ml_utility_details=m_details
            ))
        ]
        
        try:
            result = self.llm.invoke(messages)
            return result.content
        except Exception as e:
            logger.error(f"Failed to summarize evaluation with LLM: {e}")
            raise
