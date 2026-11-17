"""Deterministic Train-on-Synthetic/Test-on-Real utility evaluation."""

from decimal import Decimal
from typing import Any, Dict, Optional


def _incomplete(reason: str, **details) -> Dict[str, Any]:
    return {
        "status": "INCOMPLETE",
        "task": None,
        "target_column": details.pop("target_column", None),
        "metrics": {},
        "errors": [{"component": "ml_utility", "message": reason}],
        "configuration": details,
        "limitations": ["No utility metric is emitted when task definition or data is unsuitable."],
    }


def _class_token(value) -> str:
    import numbers
    import numpy as np

    if isinstance(value, (bool, np.bool_)):
        return f"boolean:{bool(value)}"
    if isinstance(value, numbers.Number):
        return f"numeric:{Decimal(str(value)).normalize()}"
    return f"{type(value).__module__}.{type(value).__qualname__}:{value!r}"


def evaluate_ml_utility(
    real_data,
    synthetic_data,
    *,
    target_column: Optional[str] = None,
    task_type: Optional[str] = None,
    random_seed: int = 42,
    test_size: float = 0.2,
    n_estimators: int = 100,
) -> Dict[str, Any]:
    """Evaluate TRTR and TSTR on one fixed holdout from real data.

    Target and task must be explicit. Separate preprocessing/model pipelines
    are fit on each training set, never on the shared real test partition.
    """
    import numpy as np
    import pandas as pd
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
        mean_absolute_error,
        mean_squared_error,
        precision_score,
        recall_score,
        r2_score,
    )
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import LabelEncoder, OneHotEncoder
    from app.tools.schema_evaluator import evaluate_schema_fidelity

    if target_column is None:
        return _incomplete(
            "Target column is required; no target was selected automatically.",
            candidate_columns=[str(column) for column in real_data.columns],
            random_seed=random_seed,
            test_size=test_size,
        )
    if task_type not in {"classification", "regression"}:
        return _incomplete(
            "Task type must be explicitly set to 'classification' or 'regression'.",
            target_column=target_column,
            candidate_task_types=["classification", "regression"],
            random_seed=random_seed,
            test_size=test_size,
        )
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between zero and one")
    if target_column not in real_data.columns or target_column not in synthetic_data.columns:
        return _incomplete(
            "Configured target column must exist in both datasets.",
            target_column=target_column,
            random_seed=random_seed,
            test_size=test_size,
        )
    if real_data.columns.duplicated().any() or synthetic_data.columns.duplicated().any():
        return _incomplete(
            "Duplicate column labels prevent unambiguous target and feature selection.",
            target_column=target_column,
            random_seed=random_seed,
            test_size=test_size,
        )

    feature_columns = [
        column for column in real_data.columns
        if column != target_column and column in synthetic_data.columns
    ]
    missing_features = [
        column for column in real_data.columns
        if column != target_column and column not in synthetic_data.columns
    ]
    if missing_features or not feature_columns:
        return _incomplete(
            "Synthetic data must contain all real feature columns and at least one feature is required.",
            target_column=target_column,
            missing_features=[str(column) for column in missing_features],
            random_seed=random_seed,
            test_size=test_size,
        )
    schema_result = evaluate_schema_fidelity(real_data, synthetic_data)
    incompatible = [
        check["column"] for check in schema_result["columns"]
        if check.get("type_compatible") is False
    ]
    if incompatible:
        return _incomplete(
            "Configured target/features contain incompatible real and synthetic type families.",
            target_column=target_column,
            incompatible_columns=incompatible,
            random_seed=random_seed,
            test_size=test_size,
        )

    real_target = real_data[target_column]
    synthetic_target = synthetic_data[target_column]
    real_valid_target = real_target.notna().to_numpy()
    synthetic_valid_target = synthetic_target.notna().to_numpy()
    real_indices = np.flatnonzero(real_valid_target)
    synthetic_indices = np.flatnonzero(synthetic_valid_target)
    if len(real_indices) < 5 or len(synthetic_indices) < 2:
        return _incomplete(
            "At least five real target rows and two synthetic target rows are required for this holdout protocol.",
            target_column=target_column,
            real_target_rows=int(len(real_indices)),
            synthetic_target_rows=int(len(synthetic_indices)),
            random_seed=random_seed,
            test_size=test_size,
        )

    stratification = None
    split_note = ""
    if task_type == "classification":
        target_tokens = real_target.iloc[real_indices].map(_class_token)
        counts = target_tokens.value_counts()
        proposed_test_count = max(1, int(np.ceil(len(real_indices) * test_size)))
        if len(counts) > 1 and counts.min() >= 2 and proposed_test_count >= len(counts):
            stratification = target_tokens
        else:
            split_note = "Stratification was not feasible; deterministic unstratified split used."
    try:
        train_positions, test_positions = train_test_split(
            real_indices,
            test_size=test_size,
            random_state=random_seed,
            stratify=stratification,
        )
    except ValueError as exc:
        return _incomplete(
            f"Unable to create the real holdout split: {exc}",
            target_column=target_column,
            task_type=task_type,
            random_seed=random_seed,
            test_size=test_size,
        )
    if len(train_positions) < 2 or len(test_positions) < 1:
        return _incomplete(
            "The resulting real train/test split is too small to fit and evaluate a model.",
            target_column=target_column,
            task_type=task_type,
            real_train_rows=int(len(train_positions)),
            real_test_rows=int(len(test_positions)),
            random_seed=random_seed,
            test_size=test_size,
        )

    numeric_features = []
    categorical_features = []
    for column in feature_columns:
        dtype = real_data[column].dtype
        if pd.api.types.is_numeric_dtype(dtype) and not pd.api.types.is_bool_dtype(dtype):
            numeric_features.append(column)
        else:
            categorical_features.append(column)

    def prepare_features(frame):
        prepared = frame[feature_columns].copy()
        for column in numeric_features:
            prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
            prepared[column] = prepared[column].replace([np.inf, -np.inf], np.nan)
        for column in categorical_features:
            prepared[column] = prepared[column].map(
                lambda value: np.nan if pd.isna(value) else f"{type(value).__module__}.{type(value).__qualname__}:{value!r}"
            )
        return prepared

    real_x = prepare_features(real_data)
    synthetic_x = prepare_features(synthetic_data)
    transformers = []
    if numeric_features:
        transformers.append((
            "numeric",
            SimpleImputer(strategy="median", keep_empty_features=True),
            numeric_features,
        ))
    if categorical_features:
        transformers.append((
            "categorical",
            Pipeline([
                ("imputer", SimpleImputer(strategy="constant", fill_value="<MISSING>", keep_empty_features=True)),
                ("onehot", OneHotEncoder(handle_unknown="ignore")),
            ]),
            categorical_features,
        ))
    model_parameters = {
        "n_estimators": int(n_estimators),
        "random_state": int(random_seed),
        "n_jobs": 1,
    }
    model_class = RandomForestClassifier if task_type == "classification" else RandomForestRegressor

    y_real_all = real_target.iloc[real_indices]
    y_synthetic_all = synthetic_target.iloc[synthetic_indices]
    target_encoder = None
    unseen_synthetic_target_rows = 0
    if task_type == "classification":
        target_encoder = LabelEncoder()
        real_tokens = y_real_all.map(_class_token)
        target_encoder.fit(real_tokens.iloc[np.isin(real_indices, train_positions)])
        train_classes = set(target_encoder.classes_)
        synth_tokens = y_synthetic_all.map(_class_token)
        known = synth_tokens.isin(train_classes)
        unseen_synthetic_target_rows = int((~known).sum())
        synthetic_indices = synthetic_indices[known.to_numpy()]
        synth_tokens = synth_tokens.loc[known]
        if len(synthetic_indices) < 2:
            return _incomplete(
                "Fewer than two synthetic target rows have classes present in the real training partition.",
                target_column=target_column,
                task_type=task_type,
                unseen_synthetic_target_rows=unseen_synthetic_target_rows,
                random_seed=random_seed,
                test_size=test_size,
            )
        y_real_train = target_encoder.transform(
            real_target.iloc[train_positions].map(_class_token)
        )
        y_real_test_tokens = real_target.iloc[test_positions].map(_class_token)
        test_known = y_real_test_tokens.isin(train_classes)
        if not bool(test_known.all()):
            return _incomplete(
                "The real test split contains a class absent from the real training partition.",
                target_column=target_column,
                task_type=task_type,
                unseen_test_classes=sorted(set(y_real_test_tokens[~test_known])),
                random_seed=random_seed,
                test_size=test_size,
            )
        y_real_test = target_encoder.transform(y_real_test_tokens)
        y_synthetic_train = target_encoder.transform(synth_tokens)
        class_display = [str(value) for value in target_encoder.classes_]
    else:
        y_real_numeric = pd.to_numeric(real_target.iloc[real_indices], errors="coerce")
        y_synthetic_numeric = pd.to_numeric(synthetic_target.iloc[synthetic_indices], errors="coerce")
        valid_real = np.isfinite(y_real_numeric.to_numpy(dtype=float, na_value=np.nan))
        valid_synthetic = np.isfinite(y_synthetic_numeric.to_numpy(dtype=float, na_value=np.nan))
        if not bool(valid_real.all()) or not bool(valid_synthetic.all()):
            return _incomplete(
                "Regression targets must be finite numeric values; invalid targets were not silently dropped.",
                target_column=target_column,
                task_type=task_type,
                random_seed=random_seed,
                test_size=test_size,
            )
        real_target_by_index = pd.Series(y_real_numeric.to_numpy(dtype=float), index=real_indices)
        synthetic_target_by_index = pd.Series(y_synthetic_numeric.to_numpy(dtype=float), index=synthetic_indices)
        y_real_train = real_target_by_index.loc[train_positions].to_numpy()
        y_real_test = real_target_by_index.loc[test_positions].to_numpy()
        y_synthetic_train = synthetic_target_by_index.to_numpy()
        class_display = None

    real_train_x = real_x.iloc[train_positions]
    real_test_x = real_x.iloc[test_positions]
    synth_train_x = synthetic_x.iloc[synthetic_indices]

    def fit_predict(train_x, train_y):
        pipeline = Pipeline([
            ("preprocess", ColumnTransformer([
                (name, transformer, columns)
                for name, transformer, columns in transformers
            ], remainder="drop")),
            ("model", model_class(**model_parameters)),
        ])
        pipeline.fit(train_x, train_y)
        prediction = pipeline.predict(real_test_x)
        probabilities = pipeline.predict_proba(real_test_x) if task_type == "classification" else None
        return pipeline, prediction, probabilities

    try:
        real_model, real_prediction, real_probabilities = fit_predict(real_train_x, y_real_train)
        synthetic_model, synthetic_prediction, synthetic_probabilities = fit_predict(synth_train_x, y_synthetic_train)
    except Exception as exc:
        return _incomplete(
            f"Model fitting or prediction failed: {type(exc).__name__}: {exc}",
            target_column=target_column,
            task_type=task_type,
            model="RandomForest",
            model_parameters=model_parameters,
            random_seed=random_seed,
            test_size=test_size,
        )

    if task_type == "classification":
        labels = np.arange(len(target_encoder.classes_))

        def classification_metrics(prediction):
            matrix = np.zeros((len(labels), len(labels)), dtype=int)
            for actual, predicted in zip(y_real_test, prediction):
                matrix[int(actual), int(predicted)] += 1
            return {
                "accuracy": float(accuracy_score(y_real_test, prediction)),
                "precision_weighted": float(precision_score(y_real_test, prediction, average="weighted", labels=labels, zero_division=0)),
                "recall_weighted": float(recall_score(y_real_test, prediction, average="weighted", labels=labels, zero_division=0)),
                "f1_weighted": float(f1_score(y_real_test, prediction, average="weighted", labels=labels, zero_division=0)),
                "confusion_matrix": matrix.tolist(),
            }

        def auc_metric(model, probabilities):
            if len(np.unique(y_real_test)) < 2:
                return {"value": None, "status": "UNAVAILABLE", "reason": "The real test partition contains fewer than two classes."}
            if len(model.classes_) != len(labels) or not np.array_equal(model.classes_, labels):
                return {"value": None, "status": "UNAVAILABLE", "reason": "The training partition did not contain the full real class set needed for comparable probabilities."}
            try:
                from sklearn.metrics import roc_auc_score
                if len(labels) == 2:
                    value = roc_auc_score(y_real_test, probabilities[:, 1])
                else:
                    value = roc_auc_score(y_real_test, probabilities, labels=labels, multi_class="ovr", average="weighted")
                return {"value": float(value), "status": "COMPLETED", "reason": None}
            except ValueError as exc:
                return {"value": None, "status": "UNAVAILABLE", "reason": str(exc)}

        metrics = {
            "TRTR": classification_metrics(real_prediction),
            "TSTR": classification_metrics(synthetic_prediction),
            "roc_auc": {
                "TRTR": auc_metric(real_model, real_probabilities),
                "TSTR": auc_metric(synthetic_model, synthetic_probabilities),
            },
        }
        class_distribution = {
            "real_training": {str(value): int(count) for value, count in y_real_all.iloc[np.isin(real_indices, train_positions)].map(str).value_counts().items()},
            "synthetic_training": {str(value): int(count) for value, count in y_synthetic_all.map(str).value_counts().items()},
            "test": {str(value): int(count) for value, count in real_target.iloc[test_positions].map(str).value_counts().items()},
            "class_labels_fit_from_real_training_only": class_display,
        }
    else:
        def regression_metrics(prediction):
            target_variance = float(np.var(y_real_test))
            r2 = float(r2_score(y_real_test, prediction, force_finite=False)) if target_variance > 0 else None
            return {
                "mae": float(mean_absolute_error(y_real_test, prediction)),
                "rmse": float(np.sqrt(mean_squared_error(y_real_test, prediction))),
                "r2": r2,
                "r2_status": "COMPLETED" if r2 is not None and np.isfinite(r2) else "UNAVAILABLE",
                "r2_reason": None if r2 is not None and np.isfinite(r2) else "R² is undefined for a constant real test target.",
            }
        metrics = {
            "TRTR": regression_metrics(real_prediction),
            "TSTR": regression_metrics(synthetic_prediction),
        }
        class_distribution = None

    return {
        "status": "COMPLETED",
        "task": task_type,
        "target_column": target_column,
        "feature_columns": [str(column) for column in feature_columns],
        "ignored_synthetic_columns": [
            str(column) for column in synthetic_data.columns if column not in real_data.columns
        ],
        "metrics": metrics,
        "dataset_sizes": {
            "real_rows": int(len(real_data)),
            "real_training_rows": int(len(train_positions)),
            "real_test_rows": int(len(test_positions)),
            "synthetic_rows": int(len(synthetic_data)),
            "synthetic_training_rows": int(len(synthetic_indices)),
            "synthetic_rows_with_unseen_target_class": unseen_synthetic_target_rows,
        },
        "class_distribution": class_distribution,
        "configuration": {
            "model": "RandomForestClassifier" if task_type == "classification" else "RandomForestRegressor",
            "model_parameters": model_parameters,
            "test_size": float(test_size),
            "random_seed": int(random_seed),
            "split_stratified": stratification is not None,
            "split_note": split_note,
            "preprocessing": {
                "numeric": "median imputation fit within each training pipeline; all-empty columns retained",
                "categorical": "typed string tokens, constant missing imputation, one-hot encoding with unknown categories ignored",
                "fit_policy": "TRTR preprocessing fits only on real training rows; TSTR preprocessing fits only on synthetic training rows",
            },
        },
        "limitations": [
            "TSTR measures utility for this selected target, model family, split, and dataset; it is not a privacy guarantee.",
            "Random forests are a baseline and may not represent utility for other model families.",
            "TRTR is a reference baseline, not a theoretical upper bound.",
            "ROC-AUC is reported unavailable in this implementation because probability calibration and single-class handling are outside this baseline protocol.",
            "Synthetic training rows whose target class is absent from the real training partition are excluded and counted.",
        ],
    }
