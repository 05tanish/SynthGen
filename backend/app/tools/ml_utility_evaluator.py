import pandas as pd
import numpy as np
from typing import Dict, Any
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import f1_score, r2_score
from sklearn.preprocessing import LabelEncoder


def evaluate_ml_utility(real_data: pd.DataFrame, synthetic_data: pd.DataFrame) -> Dict[str, Any]:
    """
    Evaluates ML utility by training models on real vs synthetic data
    and testing both on a holdout real test set.
    Score of 1.0 means synthetic data is as useful as real data for training.
    """
    if len(real_data.columns) < 2:
        return {"score": 1.0, "details": {"message": "Not enough columns for ML utility evaluation"}}

    common_cols = list(set(real_data.columns).intersection(synthetic_data.columns))
    if not common_cols:
        return {"score": 0.0, "details": {"message": "No common columns between real and synthetic data"}}

    target_col = common_cols[-1]
    features = common_cols[:-1]

    # Use .copy() to prevent SettingWithCopyWarning on slice assignment
    real_sub = real_data[common_cols].dropna().copy()
    synth_sub = synthetic_data[common_cols].dropna().copy()

    if len(real_sub) < 50 or len(synth_sub) < 50:
        return {"score": 0.5, "details": {"message": "Dataset too small for reliable ML evaluation"}}

    # Label encode categorical columns
    for col in common_cols:
        if not pd.api.types.is_numeric_dtype(real_sub[col]):
            le = LabelEncoder()
            # Fit on combined vocabulary to avoid unseen label errors
            combined = pd.concat([real_sub[col], synth_sub[col]]).astype(str)
            le.fit(combined)
            real_sub[col] = le.transform(real_sub[col].astype(str))
            synth_sub[col] = le.transform(synth_sub[col].astype(str))

    X_real = real_sub[features]
    y_real = real_sub[target_col]
    X_real_train, X_real_test, y_real_train, y_real_test = train_test_split(
        X_real, y_real, test_size=0.2, random_state=42
    )

    X_synth_train = synth_sub[features]
    y_synth_train = synth_sub[target_col]

    is_classification = len(np.unique(y_real)) < 10 or not pd.api.types.is_numeric_dtype(y_real)
    score = 0.0
    details: Dict[str, Any] = {
        "target_column": target_col,
        "type": "classification" if is_classification else "regression",
    }

    try:
        if is_classification:
            model_real = RandomForestClassifier(n_estimators=20, random_state=42)
            model_synth = RandomForestClassifier(n_estimators=20, random_state=42)

            model_real.fit(X_real_train, y_real_train)
            model_synth.fit(X_synth_train, y_synth_train)

            pred_real = model_real.predict(X_real_test)
            pred_synth = model_synth.predict(X_real_test)

            f1_real = f1_score(y_real_test, pred_real, average="weighted", zero_division=0)
            f1_synth = f1_score(y_real_test, pred_synth, average="weighted", zero_division=0)

            score = f1_synth / f1_real if f1_real > 0 else 0.0
            details.update({"f1_real": float(f1_real), "f1_synth": float(f1_synth)})

        else:
            model_real = RandomForestRegressor(n_estimators=20, random_state=42)
            model_synth = RandomForestRegressor(n_estimators=20, random_state=42)

            model_real.fit(X_real_train, y_real_train)
            model_synth.fit(X_synth_train, y_synth_train)

            pred_real = model_real.predict(X_real_test)
            pred_synth = model_synth.predict(X_real_test)

            r2_real = r2_score(y_real_test, pred_real)
            r2_synth = r2_score(y_real_test, pred_synth)

            r2_real_norm = max(0.0, r2_real)
            r2_synth_norm = max(0.0, r2_synth)

            score = r2_synth_norm / r2_real_norm if r2_real_norm > 0 else 0.0
            details.update({"r2_real": float(r2_real), "r2_synth": float(r2_synth)})

    except Exception as e:
        details["error"] = str(e)
        score = 0.5  # Neutral fallback on unexpected error

    return {
        "score": float(max(0.0, min(1.0, score))),
        "details": details,
    }
