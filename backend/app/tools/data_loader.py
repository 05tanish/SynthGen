import pandas as pd
from typing import Dict, Any, Tuple
from sqlalchemy import create_engine
from pydantic import BaseModel
import os

class LoadedDataset(BaseModel):
    dataframe: Any  # Cannot easily type check Pandas DataFrame in Pydantic V2 without extra config, so Any is used
    source_type: str
    source_name: str
    row_count: int
    column_count: int
    metadata: Dict[str, Any]

    model_config = {"arbitrary_types_allowed": True}

def load_from_file(file_path: str) -> LoadedDataset:
    """Load dataset from a file (CSV, Excel, JSON, Parquet)"""
    ext = os.path.splitext(file_path)[1].lower()
    filename = os.path.basename(file_path)
    
    if ext == '.csv':
        try:
            df = pd.read_csv(file_path, on_bad_lines='skip')
        except pd.errors.EmptyDataError:
            df = pd.DataFrame()
    elif ext in ['.xls', '.xlsx']:
        df = pd.read_excel(file_path)
    elif ext == '.json':
        df = pd.read_json(file_path)
    elif ext == '.parquet':
        df = pd.read_parquet(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")
        
    return LoadedDataset(
        dataframe=df,
        source_type="file",
        source_name=filename,
        row_count=len(df),
        column_count=len(df.columns),
        metadata={"extension": ext}
    )

def load_from_database(db_url: str, table_name: str, query: str = None) -> LoadedDataset:
    """Load dataset from SQLite, PostgreSQL, or MySQL"""
    engine = create_engine(db_url)
    
    if query:
        df = pd.read_sql_query(query, engine)
    else:
        df = pd.read_sql_table(table_name, engine)
        
    source_type = "sqlite" if db_url.startswith("sqlite") else "postgresql" if db_url.startswith("postgresql") else "mysql"
    
    return LoadedDataset(
        dataframe=df,
        source_type=source_type,
        source_name=table_name or "Custom Query",
        row_count=len(df),
        column_count=len(df.columns),
        metadata={"table": table_name, "has_custom_query": bool(query)}
    )
