import pandas as pd
from scipy.stats import ks_2samp
import numpy as np
from typing import Dict, Any

def evaluate_statistical_quality(real_data: pd.DataFrame, synthetic_data: pd.DataFrame) -> Dict[str, Any]:
    """
    Evaluates statistical similarity between real and synthetic data.
    Returns a score between 0 and 1, plus column-level metrics.
    """
    score_components = []
    details = {}
    
    for col in real_data.columns:
        if col not in synthetic_data.columns:
            continue
            
        real_col = real_data[col].dropna()
        synth_col = synthetic_data[col].dropna()
        
        if len(real_col) == 0 or len(synth_col) == 0:
            continue
            
        if pd.api.types.is_numeric_dtype(real_data[col]):
            # Kolmogorov-Smirnov test for distribution similarity
            # Returns D-statistic (0 to 1, where 0 is identical) and p-value
            statistic, pvalue = ks_2samp(real_col, synth_col)
            similarity = 1.0 - statistic  # 1 is perfect similarity
            
            # Compare means
            mean_diff = abs(real_col.mean() - synth_col.mean()) / (abs(real_col.mean()) + 1e-9)
            
            col_score = max(0, min(1, similarity - (mean_diff * 0.1)))
            score_components.append(col_score)
            
            details[col] = {
                "similarity": similarity,
                "mean_diff_ratio": mean_diff,
                "score": col_score
            }
        else:
            # Categorical distribution similarity
            real_dist = real_col.value_counts(normalize=True)
            synth_dist = synth_col.value_counts(normalize=True)
            
            # Total Variation Distance
            common_idx = real_dist.index.union(synth_dist.index)
            tvd = 0.5 * np.sum(np.abs(
                real_dist.reindex(common_idx, fill_value=0) - 
                synth_dist.reindex(common_idx, fill_value=0)
            ))
            
            similarity = 1.0 - tvd
            score_components.append(similarity)
            
            details[col] = {
                "similarity": similarity,
                "tvd": tvd,
                "score": similarity
            }
            
    # Calculate overall statistical score
    overall_score = np.mean(score_components) if score_components else 0.0
    
    return {
        "score": float(overall_score),
        "details": details
    }
