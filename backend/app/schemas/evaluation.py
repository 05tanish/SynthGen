from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EvaluationStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    INCOMPLETE = "INCOMPLETE"

class EvaluationReport(BaseModel):
    """Current evaluation result, while accepting older persisted report shapes."""

    model_config = ConfigDict(extra="allow")

    evaluation_status: EvaluationStatus = EvaluationStatus.UNKNOWN
    quality_accepted: Optional[bool] = None
    statistical_score: Optional[float] = None
    privacy_score: Optional[float] = None
    ml_utility_score: Optional[float] = None
    overall_score: Optional[float] = None
    passed: Optional[bool] = None
    failed_component: Optional[str] = None
    error_message: Optional[str] = None
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    component_statuses: Dict[str, str] = Field(default_factory=dict)
    execution_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    statistical_details: Dict[str, Any] = Field(default_factory=dict)
    schema_details: Dict[str, Any] = Field(default_factory=dict)
    privacy_details: Dict[str, Any] = Field(default_factory=dict)
    ml_utility_details: Dict[str, Any] = Field(default_factory=dict)
