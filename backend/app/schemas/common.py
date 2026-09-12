from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class ColumnConstraint(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    categories: Optional[List[str]] = None
    regex: Optional[str] = None
    min_date: Optional[str] = None
    max_date: Optional[str] = None

class ColumnSchema(BaseModel):
    name: str
    semantic_type: str = Field(description="e.g., integer, float, categorical, datetime, text, boolean")
    description: str
    nullable: bool = False
    unique: bool = False
    constraints: Optional[ColumnConstraint] = None

class RelationshipSchema(BaseModel):
    source_column: str
    target_column: str
    relationship_type: str = Field(description="e.g., positive_dependency, negative_dependency, mathematical, categorical_association")
    description: str

class RequirementAnalysis(BaseModel):
    dataset_name: str
    row_count: int
    columns: List[ColumnSchema]
    relationships: List[RelationshipSchema]
    business_rules: List[str]
    assumptions: List[str]
