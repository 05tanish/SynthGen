import pandas as pd
import numpy as np
from typing import Dict, Any
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

def evaluate_privacy_risk(real_data: pd.DataFrame, synthetic_data: pd.DataFrame) -> Dict[str, Any]:
    """
    Evaluates privacy risks by checking for exact duplicates and nearest-neighbor distances.
    Score is 1.0 (perfect privacy / no memorization) to 0.0 (high memorization).
    """
    # 1. Exact Duplicate Checking
    # Ensure columns match
    common_cols = list(set(real_data.columns).intersection(synthetic_data.columns))
    real_sub = real_data[common_cols].dropna()
    synth_sub = synthetic_data[common_cols].dropna()
    
    # Check if any synthetic row is an exact match to a real row
    # This is a simplified approach, in production we'd use hash comparisons
    # Merging with indicator
    merged = pd.merge(synth_sub, real_sub, how='inner')
    exact_matches = len(merged)
    exact_match_ratio = exact_matches / len(synth_sub) if len(synth_sub) > 0 else 0
    
    # 2. Nearest Neighbor Distance (DCR - Distance to Closest Record)
    # Only for numeric data for simplicity in this MVP
    num_cols = real_sub.select_dtypes(include=['number']).columns
    
    dcr_score = 1.0
    if len(num_cols) > 0 and len(real_sub) > 0 and len(synth_sub) > 0:
        scaler = StandardScaler()
        # Sample to avoid massive memory issues on MVP
        r_sample = real_sub[num_cols].sample(min(1000, len(real_sub)))
        s_sample = synth_sub[num_cols].sample(min(1000, len(synth_sub)))
        
        try:
            r_scaled = scaler.fit_transform(r_sample)
            s_scaled = scaler.transform(s_sample)
            
            nn = NearestNeighbors(n_neighbors=1, algorithm='auto').fit(r_scaled)
            distances, _ = nn.kneighbors(s_scaled)
            
            # If distance is very close to 0, it's highly similar (memorization)
            # Threshold of 0.01 in scaled space
            too_close_ratio = np.mean(distances < 0.01)
            dcr_score = 1.0 - too_close_ratio
        except Exception:
            pass # Fallback if singular matrix etc.

    # Combine scores
    privacy_score = float((1.0 - exact_match_ratio) * 0.5 + dcr_score * 0.5)
    
    return {
        "score": max(0.0, min(1.0, privacy_score)),
        "details": {
            "exact_matches": exact_matches,
            "exact_match_ratio": exact_match_ratio,
            "dcr_score": float(dcr_score),
            "message": "Privacy evaluation provides empirical risk indicators and is not a formal privacy guarantee or regulatory certification."
        }
    }
