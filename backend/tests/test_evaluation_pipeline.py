import json

import pandas as pd
import pytest
from pydantic import ValidationError

from app.graph.nodes import evaluate_data_node
from app.schemas.evaluation import EvaluationReport
from app.api.routes.datasets import PromptGenerationRequest


def test_complete_pipeline_persists_component_results_without_an_aggregate_score(tmp_path):
    real = pd.DataFrame({
        "signal": list(range(120)),
        "group": [f"g{i % 3}" for i in range(120)],
        "label": [i % 2 for i in range(120)],
    })
    synthetic = real.sample(frac=1, random_state=7).reset_index(drop=True)
    real_path = tmp_path / "real.csv"
    synthetic_path = tmp_path / "synthetic.csv"
    real.to_csv(real_path, index=False)
    synthetic.to_csv(synthetic_path, index=False)
    state = {
        "real_data_path": str(real_path),
        "synthetic_data_path": str(synthetic_path),
        "evaluation_config": {
            "target_column": "label",
            "task_type": "classification",
            "random_seed": 17,
        },
        "generator_metadata": {
            "requested_generator": "GaussianCopula",
            "actual_generator": "GaussianCopula",
            "fallback_reason": None,
        },
        "iteration": 0,
        "max_iterations": 1,
        "best_evaluation_report": None,
    }

    result = evaluate_data_node(state)
    report = result["evaluation_report"]

    assert result["evaluation_status"] == "COMPLETED"
    assert result["quality_accepted"] is None
    assert set(report["component_statuses"]) == {
        "schema_fidelity", "statistical_fidelity", "privacy_risk", "ml_utility"
    }
    assert report["schema_details"]["valid"] is True
    assert "wasserstein_distance" in report["statistical_details"]["columns"]["signal"]
    assert "exact_match" in report["privacy_details"]["metrics"]
    assert "TRTR" in report["ml_utility_details"]["metrics"]
    assert report["overall_score"] is None
    json.dumps(report, allow_nan=False)
    validated = EvaluationReport.model_validate(report)
    assert validated.evaluation_status.value == "COMPLETED"


def test_generation_api_accepts_explicit_ml_task_and_rejects_unknown_task():
    request = PromptGenerationRequest(
        prompt="make records",
        evaluation_target=" churned ",
        evaluation_task="classification",
    )
    assert request.evaluation_target == "churned"
    with pytest.raises(ValidationError, match="evaluation_task"):
        PromptGenerationRequest(prompt="make records", evaluation_task="guess")
