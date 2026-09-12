from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime

class DatasetBase(BaseModel):
    name: str
    source_type: str
    source_filename: Optional[str] = None
    row_count: int
    column_count: int
    prompt: Optional[str] = None
    schema_data: Optional[Dict[str, Any]] = None  # renamed from schema_json to avoid Pydantic BaseModel collision
    profile_json: Optional[Dict[str, Any]] = None
    relationships_json: Optional[Dict[str, Any]] = None

class DatasetCreate(DatasetBase):
    pass

class DatasetResponse(DatasetBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
