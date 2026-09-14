from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
import json

def truncate_json_data(data: Optional[Dict[str, Any]], max_chars: int, name: str = "data") -> Optional[Dict[str, Any]]:
    """
    Truncate JSON data if it exceeds the character limit.
    Keeps the structure but removes less important fields.
    Returns None if data is None.
    """
    if data is None:
        return None
    
    json_str = json.dumps(data)
    if len(json_str) <= max_chars:
        return data
    
    # Data exceeds limit - try to truncate intelligently
    from app.core.logging import logger
    logger.warning(f"{name} exceeds {max_chars} char limit ({len(json_str)} chars). Truncating intelligently.")
    
    # For profile data, keep only essential statistics
    if 'columns' in data and 'summary' in data:
        truncated = {
            'summary': data['summary'],
            'columns': {}
        }
        # Keep only basic stats for each column
        for col_name, col_data in list(data['columns'].items())[:10]:  # Max 10 columns
            if isinstance(col_data, dict):
                truncated['columns'][col_name] = {
                    'type': col_data.get('type'),
                    'unique_count': col_data.get('unique_count'),
                    'mean': col_data.get('mean'),
                    'std': col_data.get('std'),
                }
        return truncated
    
    # For relationships, keep only top correlations
    if 'correlations' in data:
        truncated = {
            'correlations': data['correlations'][:5]  # Keep top 5
        }
        return truncated
    
    # Generic truncation - convert to string and cut
    return json.loads(json_str[:max_chars - 3] + '...')


class DatasetBase(BaseModel):
    name: str
    source_type: str
    source_filename: Optional[str] = None
    row_count: int = Field(ge=1, le=30000, description="Number of rows (max 30,000)")
    column_count: int = Field(ge=1, le=100, description="Number of columns (max 100)")
    prompt: Optional[str] = Field(None, max_length=2000, description="User prompt (max 2,000 chars)")
    schema_json: Optional[Dict[str, Any]] = None
    profile_json: Optional[Dict[str, Any]] = None
    relationships_json: Optional[Dict[str, Any]] = None

    # Note: JSON size validation removed from here.
    # The generated profile/relationship data can exceed limits,
    # so we truncate in the API route instead of rejecting.
    # Agents will handle truncation when using this data.

class DatasetCreate(DatasetBase):
    pass

class DatasetResponse(DatasetBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
