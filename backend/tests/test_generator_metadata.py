import pandas as pd

from app.graph import nodes


def test_slow_model_override_records_requested_and_actual_models(monkeypatch, tmp_path):
    class FakeGaussian:
        def __init__(self, parameters):
            self.parameters = parameters
            self.effective_parameters = {"effective": True}

        def fit(self, frame):
            self.fit_rows = len(frame)

        def generate(self, num_rows, random_seed):
            return pd.DataFrame({"x": list(range(num_rows))})

    monkeypatch.setattr(nodes, "GaussianCopulaGenerator", FakeGaussian)
    monkeypatch.setenv("ALLOW_SLOW_MODELS", "false")
    real_path = tmp_path / "real.csv"
    pd.DataFrame({"x": range(12)}).to_csv(real_path, index=False)
    state = {
        "generation_plan": {"selected_model": "CTGAN", "parameters": {"epochs": 50}},
        "real_data_path": str(real_path),
        "requirement": None,
        "profile_json": {"summary": {"row_count": 12}},
    }

    result = nodes._generate_data_node_impl(state)
    metadata = result["generator_metadata"]

    assert metadata["requested_generator"] == "CTGAN"
    assert metadata["actual_generator"] == "GaussianCopula"
    assert "disabled" in metadata["fallback_reason"]
    assert metadata["effective_parameters"] == {"effective": True}
    assert metadata["random_seed"] == 42
    assert metadata["generated_row_count"] == 12
    import os
    os.remove(result["synthetic_data_path"])


def test_unknown_generator_fallback_is_explicit(monkeypatch):
    class FakeGaussian:
        def __init__(self, parameters):
            self.parameters = parameters

    monkeypatch.setattr(nodes, "GaussianCopulaGenerator", FakeGaussian)
    generator, actual_model, fallback_reason = nodes._create_generator(
        "made-up-model", {"learning_rate": 0.2}, allow_slow_models=True
    )
    assert isinstance(generator, FakeGaussian)
    assert actual_model == "GaussianCopula"
    assert "Unknown requested model" in fallback_reason
    assert generator.parameters == {}
