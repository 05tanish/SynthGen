from app.schemas.common import RequirementAnalysis, ColumnSchema
from typing import Dict, Any, List

class SchemaValidationError(Exception):
    def __init__(self, message: str, errors: List[str]):
        super().__init__(message)
        self.errors = errors

def schema_validator(analysis: RequirementAnalysis) -> bool:
    """Validates the schema deterministically"""
    errors = []
    
    if analysis.row_count <= 0:
        errors.append(f"Invalid row count: {analysis.row_count}")
        
    seen_columns = set()
    for col in analysis.columns:
        # Check duplicates
        if col.name.lower() in seen_columns:
            errors.append(f"Duplicate column name: {col.name}")
        seen_columns.add(col.name.lower())
        
        # Check types
        allowed_types = ["integer", "float", "categorical", "datetime", "text", "boolean"]
        if col.semantic_type not in allowed_types:
            errors.append(f"Unsupported semantic type for column '{col.name}': {col.semantic_type}")
            
        # Check constraints
        if col.constraints:
            if col.constraints.min is not None and col.constraints.max is not None:
                if col.constraints.min > col.constraints.max:
                    errors.append(f"Constraint error in '{col.name}': min ({col.constraints.min}) > max ({col.constraints.max})")
                    
    if errors:
        raise SchemaValidationError("Schema validation failed", errors)
        
    return True
