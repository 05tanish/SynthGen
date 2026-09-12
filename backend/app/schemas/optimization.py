from pydantic import BaseModel, Field
from typing import Dict, Any

class OptimizationPlan(BaseModel):
    action: str = Field(description="Must be one of: 'retry_same', 'tune_parameters', 'switch_model', 'fail'")
    reasoning: str = Field(description="Why this action was chosen based on the evaluation report")
    new_model: str = Field(description="If switch_model, the new model to use (GaussianCopula, CTGAN, TVAE). Otherwise echo current model.")
    new_parameters: Dict[str, Any] = Field(description="The new parameters to use.")
