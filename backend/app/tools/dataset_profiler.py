import pandas as pd
import numpy as np
from typing import Dict, Any

def profile_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Deterministically profiles a pandas DataFrame.
    Calculates statistics for numerical, categorical, and datetime columns.
    """
    total_rows = len(df)
    
    profile = {
        "summary": {
            "row_count": total_rows,
            "column_count": len(df.columns),
            "duplicate_rows": int(df.duplicated().sum()) if total_rows > 0 else 0,
            "duplicate_percentage": float(df.duplicated().mean()) if total_rows > 0 else 0.0,
            "missing_cells": int(df.isna().sum().sum()),
            "missing_percentage": float(df.isna().mean().mean()) if total_rows > 0 else 0.0
        },
        "columns": {}
    }
    
    for col in df.columns:
        col_data = df[col]
        missing_count = int(col_data.isna().sum())
        
        col_profile = {
            "type": str(col_data.dtype),
            "missing_count": missing_count,
            "missing_percentage": missing_count / total_rows if total_rows > 0 else 0,
            "unique_count": int(col_data.nunique())
        }
        
        if pd.api.types.is_numeric_dtype(col_data):
            # Numerical stats
            valid_data = col_data.dropna()
            if not valid_data.empty:
                col_profile.update({
                    "mean": float(valid_data.mean()),
                    "median": float(valid_data.median()),
                    "std": float(valid_data.std()) if len(valid_data) > 1 else 0.0,
                    "min": float(valid_data.min()),
                    "max": float(valid_data.max()),
                    "skewness": float(valid_data.skew()) if len(valid_data) > 2 else 0.0,
                    "q25": float(valid_data.quantile(0.25)),
                    "q75": float(valid_data.quantile(0.75))
                })
        elif pd.api.types.is_datetime64_any_dtype(col_data):
            # Datetime stats
            valid_data = col_data.dropna()
            if not valid_data.empty:
                col_profile.update({
                    "min_date": str(valid_data.min()),
                    "max_date": str(valid_data.max())
                })
        else:
            # Categorical / Text stats
            valid_data = col_data.dropna()
            if not valid_data.empty:
                value_counts = valid_data.value_counts(normalize=True).head(10)
                col_profile.update({
                    "top_categories": {str(k): float(v) for k, v in value_counts.items()}
                })
                
        profile["columns"][str(col)] = col_profile
        
    return profile
