import pandas as pd

from scripts import run_evaluation_benchmarks as benchmark


def test_benchmark_fixtures_cover_requested_data_shapes():
    fixtures = benchmark.make_fixtures(42)
    assert set(fixtures) == {
        "numerical_only", "categorical_only", "mixed", "missing_values",
        "imbalanced_classification", "regression", "high_cardinality",
        "duplicate_records", "small_dataset", "large_dataset",
    }
    assert fixtures["small_dataset"][0].shape[0] < fixtures["mixed"][0].shape[0]
    assert fixtures["large_dataset"][0].shape[0] > fixtures["mixed"][0].shape[0]


def test_failed_requested_generator_is_not_reported_as_fallback(monkeypatch):
    class FailingGenerator:
        def __init__(self, parameters):
            self.effective_parameters = parameters

        def fit(self, _frame):
            raise RuntimeError("fixture failure")

    monkeypatch.setitem(benchmark.GENERATORS, "GaussianCopula", FailingGenerator)
    frame = pd.DataFrame({"x": [1, 2], "target": [0, 1]})
    result = benchmark.benchmark_run(
        "tiny", frame, "target", "classification", "GaussianCopula", 42, 1, 2
    )
    assert result["generator"]["status"] == "FAILED"
    assert result["generator"]["actual_model"] is None
    assert result["generator"]["fallback_reason"] is None
    assert result["errors"][0]["component"] == "generation"


def test_successful_generator_name_is_the_actual_generator(monkeypatch):
    class CopyGenerator:
        def __init__(self, parameters):
            self.effective_parameters = parameters

        def fit(self, _frame):
            return None

        def generate(self, num_rows, random_seed):
            return source.iloc[:num_rows].copy().reset_index(drop=True)

    source = pd.DataFrame({"x": list(range(100)), "target": [i % 2 for i in range(100)]})
    monkeypatch.setitem(benchmark.GENERATORS, "GaussianCopula", CopyGenerator)
    result = benchmark.benchmark_run(
        "fixture", source, "target", "classification", "GaussianCopula", 42, 1, 100
    )
    assert result["generator"]["status"] == "COMPLETED"
    assert result["generator"]["actual_model"] == "GaussianCopula"
    assert result["metrics"]["ml_utility"]["status"] == "COMPLETED"
