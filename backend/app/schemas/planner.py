from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class GenerationPlan(BaseModel):
    selected_model: str = Field(description="Must be one of: GaussianCopula, CTGAN, TVAE")
    reasoning: str = Field(description="Why this model was chosen based on data profile")
    parameters: Dict[str, Any] = Field(description="Parameters for the model (e.g. epochs, batch_size)")
