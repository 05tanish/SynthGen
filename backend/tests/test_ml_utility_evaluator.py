import numpy as np
import pandas as pd

from app.tools.ml_utility_evaluator import evaluate_ml_utility


def test_target_and_task_must_be_explicit():
    frame = pd.DataFrame({"feature": [1, 2, 3, 4, 5], "target": [0, 1, 0, 1, 0]})
    result = evaluate_ml_utility(frame, frame)
    assert result["status"] == "INCOMPLETE"
    assert "required" in result["errors"][0]["message"]
    assert result["metrics"] == {}

    missing_task = evaluate_ml_utility(frame, frame, target_column="target")
    assert missing_task["status"] == "INCOMPLETE"
    assert "explicitly set" in missing_task["errors"][0]["message"]

    invalid_target = evaluate_ml_utility(
        frame, frame, target_column="does_not_exist", task_type="classification"
    )
    assert invalid_target["status"] == "INCOMPLETE"
    assert "must exist" in invalid_target["errors"][0]["message"]


def test_small_real_dataset_returns_incomplete_with_reason():
    frame = pd.DataFrame({"feature": range(4), "target": [0, 1, 0, 1]})
    result = evaluate_ml_utility(
        frame, frame, target_column="target", task_type="classification"
    )
    assert result["status"] == "INCOMPLETE"
    assert "five real target rows" in result["errors"][0]["message"]


def test_binary_classification_reports_trtr_tstr_metrics_and_auc():
    x = np.arange(120)
    frame = pd.DataFrame({"feature": x, "category": [f"g{i % 3}" for i in x], "target": (x % 2).astype(str)})
    result = evaluate_ml_utility(
        frame, frame.copy(), target_column="target", task_type="classification", random_seed=13
    )
    assert result["status"] == "COMPLETED"
    assert result["task"] == "classification"
    for task in ("TRTR", "TSTR"):
        assert set(result["metrics"][task]) >= {
            "accuracy", "precision_weighted", "recall_weighted", "f1_weighted", "confusion_matrix"
        }
        assert result["metrics"][task]["confusion_matrix"]
    assert result["metrics"]["roc_auc"]["TRTR"]["status"] == "COMPLETED"
    assert result["metrics"]["roc_auc"]["TSTR"]["status"] == "COMPLETED"


def test_multiclass_high_cardinality_is_not_misclassified_as_regression():
    frame = pd.DataFrame({
        "feature": np.arange(240),
        "target": [f"class_{i % 12}" for i in range(240)],
    })
    result = evaluate_ml_utility(
        frame, frame.copy(), target_column="target", task_type="classification", random_seed=2
    )
    assert result["task"] == "classification"
    assert len(result["class_distribution"]["class_labels_fit_from_real_training_only"]) == 12
    assert result["metrics"]["roc_auc"]["TRTR"]["status"] == "COMPLETED"


def test_imbalanced_classification_uses_deterministic_stratification_when_feasible():
    frame = pd.DataFrame({
        "feature": np.arange(200),
        "target": ["rare"] * 10 + ["common"] * 190,
    })
    result = evaluate_ml_utility(
        frame, frame.copy(), target_column="target", task_type="classification", random_seed=8
    )
    assert result["status"] == "COMPLETED"
    assert result["configuration"]["split_stratified"] is True
    assert result["class_distribution"]["test"]["rare"] == 2
    assert len(result["metrics"]["TSTR"]["confusion_matrix"]) == 2


def test_low_cardinality_regression_remains_regression_and_reports_raw_metrics():
    frame = pd.DataFrame({
        "feature": np.arange(100, dtype=float),
        "target": np.where(np.arange(100) % 2, 1.0, 0.0),
    })
    result = evaluate_ml_utility(
        frame, frame.copy(), target_column="target", task_type="regression"
    )
    assert result["task"] == "regression"
    assert set(result["metrics"]["TSTR"]) >= {"mae", "rmse", "r2"}


def test_single_class_classification_reports_auc_unavailable_without_faking_value():
    frame = pd.DataFrame({"feature": np.arange(20), "target": ["one"] * 20})
    result = evaluate_ml_utility(
        frame, frame.copy(), target_column="target", task_type="classification"
    )
    assert result["status"] == "COMPLETED"
    assert result["metrics"]["roc_auc"]["TRTR"]["status"] == "UNAVAILABLE"
    assert result["metrics"]["roc_auc"]["TRTR"]["value"] is None


def test_missing_values_and_unseen_synthetic_feature_categories_are_handled():
    real = pd.DataFrame({
        "numeric": [float(i) if i % 7 else np.nan for i in range(100)],
        "category": [f"c{i % 3}" if i % 9 else None for i in range(100)],
        "target": [i % 2 for i in range(100)],
    })
    synthetic = real.copy()
    synthetic.loc[0, "category"] = "unseen"
    result = evaluate_ml_utility(
        real, synthetic, target_column="target", task_type="classification"
    )
    assert result["status"] == "COMPLETED"
    assert "unknown categories ignored" in result["configuration"]["preprocessing"]["categorical"]


def test_synthetic_only_classes_are_counted_and_excluded():
    real = pd.DataFrame({"feature": np.arange(100), "target": ["a", "b"] * 50})
    synthetic = real.copy()
    synthetic.loc[0, "target"] = "synthetic_only"
    result = evaluate_ml_utility(
        real, synthetic, target_column="target", task_type="classification"
    )
    assert result["dataset_sizes"]["synthetic_rows_with_unseen_target_class"] == 1
    assert result["dataset_sizes"]["synthetic_training_rows"] == 99


def test_numeric_class_values_match_across_compatible_integer_and_float_dtypes():
    real = pd.DataFrame({"feature": np.arange(100), "target": np.arange(100) % 2})
    synthetic = real.copy()
    synthetic["target"] = synthetic["target"].astype(float)
    result = evaluate_ml_utility(
        real, synthetic, target_column="target", task_type="classification"
    )
    assert result["status"] == "COMPLETED"
    assert result["dataset_sizes"]["synthetic_rows_with_unseen_target_class"] == 0


def test_constant_regression_test_target_has_unavailable_r2():
    frame = pd.DataFrame({"feature": np.arange(30), "target": np.ones(30)})
    result = evaluate_ml_utility(frame, frame.copy(), target_column="target", task_type="regression")
    assert result["metrics"]["TSTR"]["r2"] is None
    assert result["metrics"]["TSTR"]["r2_status"] == "UNAVAILABLE"


def test_negative_r2_is_preserved_for_synthetic_training():
    real = pd.DataFrame({"feature": np.arange(100, dtype=float), "target": np.arange(100, dtype=float)})
    synthetic = real.copy()
    synthetic["target"] = 50.0
    result = evaluate_ml_utility(real, synthetic, target_column="target", task_type="regression")
    assert result["metrics"]["TSTR"]["r2"] < 0
    assert result["metrics"]["TSTR"]["mae"] > 0


def test_fixed_seed_reproduces_split_and_model_metrics():
    frame = pd.DataFrame({"feature": np.arange(80), "target": np.arange(80) % 3})
    first = evaluate_ml_utility(
        frame, frame.copy(), target_column="target", task_type="classification", random_seed=31
    )
    second = evaluate_ml_utility(
        frame, frame.copy(), target_column="target", task_type="classification", random_seed=31
    )
    assert first["metrics"] == second["metrics"]
    assert first["dataset_sizes"] == second["dataset_sizes"]
