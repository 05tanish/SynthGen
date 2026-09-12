from app.schemas.common import RequirementAnalysis
from typing import Dict, Any

def schema_generator(analysis: RequirementAnalysis) -> Dict[str, Any]:
    """
    Transforms the validated Pydantic RequirementAnalysis model into the
    internal JSON schema representation used by downstream generation.
    """
    schema_dict = {
        "dataset_name": analysis.dataset_name,
        "row_count": analysis.row_count,
        "columns": [col.model_dump() for col in analysis.columns],
        "relationships": [rel.model_dump() for rel in analysis.relationships],
        "business_rules": analysis.business_rules,
        "assumptions": analysis.assumptions
    }
    return schema_dict
