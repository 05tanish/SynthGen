import numpy as np
import pandas as pd
import pytest

from app.tools import privacy_checker
from app.tools.privacy_checker import evaluate_privacy_risk


def test_duplicate_rows_count_matched_synthetic_unique_values_and_pairs_separately():
    real = pd.DataFrame({"n": [1, 1, 2], "c": ["a", "a", "b"]})
    synthetic = pd.DataFrame({"n": [1, 1, 1], "c": ["a", "a", "a"]})
    metric = evaluate_privacy_risk(real, synthetic)["metrics"]["exact_match"]
    assert metric["synthetic_rows_with_real_match"] == 3
    assert metric["synthetic_row_match_rate"] == 1.0
    assert metric["unique_matching_record_values"] == 1
    assert metric["total_matching_pairs"] == 6


def test_null_values_participate_in_exact_matching_and_mixed_distances():
    real = pd.DataFrame({"numeric": [1.0, np.nan, 4.0], "category": ["a", None, "b"]})
    synthetic = pd.DataFrame({"numeric": [np.nan, 2.0, 4.0], "category": [None, "new", "b"]})
    result = evaluate_privacy_risk(real, synthetic)
    assert result["status"] == "COMPLETED"
    assert result["metrics"]["exact_match"]["synthetic_rows_with_real_match"] == 2
    assert 0 <= result["metrics"]["nearest_neighbor_distance"]["distance_quantiles"]["0.5"] <= 1


def test_column_reordering_is_aligned_by_source_order_and_deterministic():
    real = pd.DataFrame({"n": [0, 1, 2], "c": ["a", "b", "c"]})
    synth = pd.DataFrame({"c": ["a", "b", "c"], "n": [0, 1, 2]})
    first = evaluate_privacy_risk(real, synth, sample_size=2, random_seed=9)
    second = evaluate_privacy_risk(real, synth, sample_size=2, random_seed=9)
    assert first["metrics"] == second["metrics"]
    assert first["configuration"]["column_order"] == ["n", "c"]
    assert first["metrics"]["exact_match"]["synthetic_rows_with_real_match"] == 3


def test_constant_numeric_column_has_defined_gower_distance():
    real = pd.DataFrame({"n": [5, 5], "c": ["a", "b"]})
    synthetic = pd.DataFrame({"n": [5, 6], "c": ["a", "b"]})
    result = evaluate_privacy_risk(real, synthetic)
    assert result["metrics"]["nearest_neighbor_distance"]["distance_quantiles"]["0.0"] == 0.0


def test_large_inputs_use_configured_deterministic_sampling():
    real = pd.DataFrame({"n": np.arange(1500), "category": [f"c{i % 9}" for i in range(1500)]})
    synthetic = real.sample(frac=1, random_state=12).reset_index(drop=True)
    result = evaluate_privacy_risk(real, synthetic, sample_size=100, random_seed=22, batch_size=8)
    nn = result["metrics"]["nearest_neighbor_distance"]
    assert nn["sampled_real_rows"] == 100
    assert nn["sampled_synthetic_rows"] == 100
    assert nn["sample_seed"] == 22
    assert result["status"] == "COMPLETED"


def test_schema_mismatch_is_incomplete_and_does_not_compare_partial_rows():
    result = evaluate_privacy_risk(
        pd.DataFrame({"n": [1], "c": ["a"]}),
        pd.DataFrame({"n": [1], "other": ["a"]}),
    )
    assert result["status"] == "INCOMPLETE"
    assert result["metrics"] == {}
    assert "missing_columns" in result["errors"][0]


def test_duplicate_columns_are_incomplete():
    real = pd.DataFrame([[1, 2]], columns=["x", "x"])
    synth = pd.DataFrame([[1, 2]], columns=["x", "x"])
    assert evaluate_privacy_risk(real, synth)["status"] == "INCOMPLETE"


def test_invalid_sampling_configuration_raises():
    frame = pd.DataFrame({"x": [1]})
    with pytest.raises(ValueError, match="positive"):
        evaluate_privacy_risk(frame, frame, sample_size=0)


def test_nearest_neighbor_failure_is_not_replaced_with_a_default(monkeypatch):
    frame = pd.DataFrame({"n": [1, 2], "c": ["a", "b"]})

    def fail(*_args, **_kwargs):
        raise RuntimeError("distance calculation failed")

    monkeypatch.setattr(privacy_checker, "_gower_nearest_distances", fail)
    with pytest.raises(RuntimeError, match="distance calculation failed"):
        evaluate_privacy_risk(frame, frame.copy())
