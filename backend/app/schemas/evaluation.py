from pydantic import BaseModel
from typing import Dict, Any, List

class EvaluationReport(BaseModel):
    statistical_score: float
    privacy_score: float
    ml_utility_score: float
    overall_score: float
    passed: bool
    
    statistical_details: Dict[str, Any]
    privacy_details: Dict[str, Any]
    ml_utility_details: Dict[str, Any]
