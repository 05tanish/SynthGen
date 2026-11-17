import json

import numpy as np
import pandas as pd
import pytest

from app.tools.schema_evaluator import evaluate_schema_fidelity
from app.tools.statistical_evaluator import evaluate_statistical_quality


def test_zero_mean_numeric_column_uses_raw_unit_differences():
    real = pd.DataFrame({"x": [-1.0, 1.0, -1.0, 1.0]})
    synthetic = pd.DataFrame({"x": [-2.0, 2.0, -2.0, 2.0]})
    result = evaluate_statistical_quality(real, synthetic)
    metric = result["columns"]["x"]

    assert "score" not in result
    assert metric["real_mean"] == 0.0
    assert metric["mean_difference"] == 0.0
    assert metric["standard_deviation_difference"] == pytest.approx(
        np.std([-2, 2, -2, 2], ddof=1) - np.std([-1, 1, -1, 1], ddof=1)
    )
    assert metric["wasserstein_distance"] == pytest.approx(1.0)


def test_constant_and_single_observation_columns_are_handled():
    result = evaluate_statistical_quality(
        pd.DataFrame({"constant": [4, 4]}),
        pd.DataFrame({"constant": [4, 4]}),
    )
    assert result["columns"]["constant"]["wasserstein_distance"] == 0.0
    assert result["columns"]["constant"]["standard_deviation_difference"] == 0.0
    assert result["relationships"] == []

    one_observation = evaluate_statistical_quality(
        pd.DataFrame({"single": [3]}), pd.DataFrame({"single": [3]})
    )
    assert one_observation["columns"]["single"]["standard_deviation_difference"] is None


@pytest.mark.parametrize("values", [[0, 1, 2, 1, 0], [0.1, 0.4, 2.2, 3.5, 8.0]])
def test_discrete_and_continuous_numeric_metrics(values):
    result = evaluate_statistical_quality(
        pd.DataFrame({"x": values}), pd.DataFrame({"x": values})
    )
    assert result["columns"]["x"]["status"] == "COMPLETED"
    assert result["columns"]["x"]["wasserstein_distance"] == 0.0
    assert all(q["difference"] == 0.0 for q in result["columns"]["x"]["quantiles"].values())


def test_missingness_is_reported_for_numeric_and_categorical_columns():
    real = pd.DataFrame({"n": [1.0, np.nan, 3.0], "c": ["a", None, "b"]})
    synthetic = pd.DataFrame({"n": [1.0, 2.0, 3.0], "c": ["a", "a", "b"]})
    result = evaluate_statistical_quality(real, synthetic)
    assert result["columns"]["n"]["real_missing_rate"] == pytest.approx(1 / 3)
    assert result["columns"]["n"]["missing_rate_difference"] == pytest.approx(-1 / 3)
    assert result["columns"]["c"]["real_missing_rate"] == pytest.approx(1 / 3)
    assert result["columns"]["c"]["total_variation_distance"] > 0
    assert "nullability_mismatch" in evaluate_schema_fidelity(real, synthetic)["issues"]


def test_schema_marks_all_null_columns_and_nullability():
    result = evaluate_schema_fidelity(
        pd.DataFrame({"x": [None, None]}), pd.DataFrame({"x": ["a", None]})
    )
    column = result["columns"][0]
    assert column["real_all_null"] is True
    assert column["synthetic_all_null"] is False
    assert column["real_nullable"] is True
    assert column["synthetic_nullable"] is True


def test_unseen_and_high_cardinality_categories_are_reported():
    real = pd.DataFrame({"c": [f"v{i}" for i in range(500)]})
    synthetic = pd.DataFrame({"c": [f"v{i}" for i in range(499)] + ["new"]})
    metric = evaluate_statistical_quality(real, synthetic)["columns"]["c"]
    assert metric["unseen_synthetic_category_count"] == 1
    assert metric["unseen_synthetic_categories"] == ["'new'"]
    assert metric["total_variation_distance"] > 0


def test_schema_reports_missing_extra_incompatible_duplicate_and_dimensions():
    real = pd.DataFrame([[1, "a", 2]], columns=["numeric", "category", "duplicate"])
    synthetic = pd.DataFrame([["bad", "a", 2, 3]], columns=["numeric", "category", "duplicate", "extra"])
    synthetic.columns = ["numeric", "category", "duplicate", "extra"]
    real.columns = ["numeric", "category", "duplicate"]
    # Include repeated labels explicitly; ordinary dict construction would discard them.
    real = pd.DataFrame([[1, 1, "a"]], columns=["numeric", "numeric", "category"])
    result = evaluate_schema_fidelity(real, synthetic)

    assert result["real_row_count"] == 1
    assert result["synthetic_row_count"] == 1
    assert result["real_column_count"] == 3
    assert result["synthetic_column_count"] == 4
    assert result["duplicate_real_columns"] == ["numeric"]
    assert result["unexpected_columns"] == ["duplicate", "extra"]
    assert "duplicate_columns" in result["issues"]
    assert "unexpected_columns" in result["issues"]


def test_incompatible_shared_column_is_explicit_and_has_no_statistic():
    result = evaluate_statistical_quality(
        pd.DataFrame({"value": [1, 2]}), pd.DataFrame({"value": ["one", "two"]})
    )
    assert result["columns"]["value"]["status"] == "UNAVAILABLE"
    assert "incompatible" in result["columns"]["value"]["reason"]


def test_missing_and_extra_columns_are_not_silently_compared():
    real = pd.DataFrame({"present": [1, 2], "missing": [3, 4]})
    synthetic = pd.DataFrame({"present": [1, 2], "extra": [5, 6]})
    result = evaluate_statistical_quality(real, synthetic)
    assert result["columns"]["missing"]["status"] == "UNAVAILABLE"
    schema = evaluate_schema_fidelity(real, synthetic)
    assert schema["missing_columns"] == ["missing"]
    assert schema["unexpected_columns"] == ["extra"]


def test_empty_data_returns_incomplete_metrics_without_nan_values():
    result = evaluate_statistical_quality(
        pd.DataFrame({"x": pd.Series(dtype=float)}),
        pd.DataFrame({"x": pd.Series(dtype=float)}),
    )
    assert result["status"] == "INCOMPLETE"
    assert result["columns"]["x"]["status"] == "INCOMPLETE"
    assert result["columns"]["x"]["wasserstein_distance"] is None
    assert evaluate_schema_fidelity(
        pd.DataFrame({"x": pd.Series(dtype=float)}),
        pd.DataFrame({"x": pd.Series(dtype=float)}),
    )["issues"] == ["empty_dataset"]
    json.dumps(result, allow_nan=False)


def test_numeric_categorical_and_categorical_relationships_are_reported():
    real = pd.DataFrame({
        "x": [0, 0, 1, 1, 2, 2],
        "y": [0, 1, 2, 3, 4, 5],
        "group": ["a", "a", "b", "b", "c", "c"],
        "flag": ["yes", "no", "yes", "no", "yes", "no"],
    })
    synthetic = real.copy()
    result = evaluate_statistical_quality(real, synthetic)
    methods = {relationship["method"] for relationship in result["relationships"]}
    assert {"pearson_correlation", "cramers_v", "correlation_ratio_eta_squared"} <= methods
    assert all(
        relationship["absolute_difference"] == pytest.approx(0.0)
        for relationship in result["relationships"]
        if relationship["status"] == "COMPLETED"
    )


def test_relationship_association_limit_is_reported_not_silently_dropped():
    data = pd.DataFrame({
        "a": [f"a{i}" for i in range(400)],
        "b": [f"b{i}" for i in range(400)],
    })
    result = evaluate_statistical_quality(data, data.copy())
    relation = next(r for r in result["relationships"] if r["method"] == "cramers_v")
    assert relation["status"] == "UNAVAILABLE"
    assert "cell limit" in relation["reason"]
