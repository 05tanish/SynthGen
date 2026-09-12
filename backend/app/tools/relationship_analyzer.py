import pandas as pd
from typing import Dict, Any, List

def analyze_relationships(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyzes relationships between columns in the dataset.
    Primarily calculates Pearson correlation for numerical columns.
    """
    relationships = {
        "correlations": [],
        "matrix": {}
    }
    
    # Select only numeric columns for correlation
    numeric_df = df.select_dtypes(include=['number'])
    
    if len(numeric_df.columns) > 1:
        corr_matrix = numeric_df.corr(method='pearson')
        
        # Save full matrix
        relationships["matrix"] = corr_matrix.fillna(0).to_dict()
        
        # Extract strong relationships (absolute correlation > 0.5)
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                col1 = corr_matrix.columns[i]
                col2 = corr_matrix.columns[j]
                corr_value = corr_matrix.iloc[i, j]
                
                if pd.notna(corr_value) and abs(corr_value) > 0.5:
                    rel_type = "positive_dependency" if corr_value > 0 else "negative_dependency"
                    relationships["correlations"].append({
                        "source": str(col1),
                        "target": str(col2),
                        "relationship_type": rel_type,
                        "strength": float(abs(corr_value)),
                        "raw_score": float(corr_value)
                    })
                    
    # Sort by strength descending
    relationships["correlations"] = sorted(
        relationships["correlations"], 
        key=lambda x: x["strength"], 
        reverse=True
    )
    
    return relationships
