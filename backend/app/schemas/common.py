from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Any

class ColumnConstraint(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    categories: Optional[List[str]] = None
    regex: Optional[str] = None
    min_date: Optional[str] = None
    max_date: Optional[str] = None

    @field_validator('min', 'max')
    @classmethod
    def validate_min_max(cls, v, info):
        """Validate that min/max constraints are logical"""
        return v

    @field_validator('categories')
    @classmethod
    def validate_categories(cls, v):
        """Limit number of categories to prevent bloat"""
        if v is not None and len(v) > 100:
            raise ValueError(f"Too many categories ({len(v)}). Maximum 100 allowed.")
        return v

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
    row_count: int = Field(ge=1, le=30000, description="Requested row count (max 30,000)")
    columns: List[ColumnSchema] = Field(max_length=100, description="Column definitions (max 100)")
    relationships: List[RelationshipSchema] = Field(max_length=50, description="Relationships (max 50)")
    business_rules: List[str]
    assumptions: List[str]
