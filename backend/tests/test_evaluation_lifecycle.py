from types import SimpleNamespace

import pytest

from app.graph import nodes
from app.graph.routers import should_optimize
from app.schemas.evaluation import EvaluationStatus
from app.workers.graph_worker import _select_generated_artifact
from app.api.routes.jobs import _evaluation_response_fields
from app.tools.ml_utility_evaluator import evaluate_ml_utility


@pytest.mark.parametrize(
    ("component", "evaluator_name"),
    [
        ("statistical", "evaluate_statistical_quality"),
        ("privacy", "evaluate_privacy_risk"),
        ("ml_utility", "evaluate_ml_utility"),
    ],
)
def test_evaluator_failure_is_not_quality_acceptance(
    tmp_path, monkeypatch, component, evaluator_name
):
    real_path = tmp_path / "real.csv"
    synth_path = tmp_path / "synth.csv"
    real_path.write_text("feature,target\n1,a\n2,b\n")
    synth_path.write_text("feature,target\n1,a\n2,b\n")

    def fail(*_args, **_kwargs):
        raise RuntimeError(f"{component} evaluator unavailable")

    monkeypatch.setattr(nodes, evaluator_name, fail)
    state = {
        "real_data_path": str(real_path),
        "synthetic_data_path": str(synth_path),
        "iteration": 0,
        "max_iterations": 3,
    }

    result = nodes.evaluate_data_node(state)

    assert result["evaluation_status"] == EvaluationStatus.FAILED.value
    assert result["quality_accepted"] is None
    assert result["is_successful"] is False
    assert result["evaluation_report"]["failed_component"] == component
    assert component in result["evaluation_report"]["error_message"]
    assert should_optimize(result) == "end"


def test_complete_evaluation_failure_has_explicit_report_and_keeps_artifact(tmp_path):
    artifact = tmp_path / "synthetic.csv"
    artifact.write_text("x\n1\n")
    result = nodes.evaluate_data_node(
        {
            "real_data_path": str(tmp_path / "missing-real.csv"),
            "synthetic_data_path": str(artifact),
            "iteration": 0,
            "max_iterations": 3,
        }
    )

    assert result["evaluation_status"] == EvaluationStatus.FAILED.value
    assert result["evaluation_report"]["failed_component"] == "evaluation_pipeline"
    assert result["quality_accepted"] is None
    selected_path, report, available = _select_generated_artifact(result)
    assert selected_path == str(artifact)
    assert available is True
    assert report["evaluation_status"] == EvaluationStatus.FAILED.value


def test_worker_keeps_generated_file_but_does_not_infer_evaluation_success(tmp_path):
    artifact = tmp_path / "synthetic.csv"
    artifact.write_text("x\n1\n")
    path, report, available = _select_generated_artifact(
        {"synthetic_data_path": str(artifact), "is_successful": False}
    )

    assert path == str(artifact)
    assert available is True
    assert report["evaluation_status"] == EvaluationStatus.INCOMPLETE.value
    assert report["quality_accepted"] is None


def test_api_exposes_generation_and_evaluation_states_separately():
    failed_job = SimpleNamespace(
        status=SimpleNamespace(value="COMPLETED"),
        synthetic_file_path="https://files.example/generated.csv",
        evaluation_report_json={
            "evaluation_status": "FAILED",
            "quality_accepted": None,
        },
    )
    fields = _evaluation_response_fields(failed_job)
    assert fields == {
        "generation_status": "completed",
        "artifact_available": True,
        "evaluation_status": "FAILED",
        "quality_accepted": None,
    }


def test_legacy_report_is_not_assumed_to_have_completed_evaluation():
    legacy_job = SimpleNamespace(
        status="COMPLETED",
        synthetic_file_path="legacy.csv",
        evaluation_report_json={"passed": True, "overall_score": 0.9},
    )
    fields = _evaluation_response_fields(legacy_job)
    assert fields["evaluation_status"] == "UNKNOWN"
    assert fields["quality_accepted"] is None


@pytest.mark.parametrize(
    ("generation_status", "expected_evaluation_status"),
    [("RUNNING", "PENDING"), ("COMPLETED", "INCOMPLETE")],
)
def test_api_reports_missing_evaluation_state(generation_status, expected_evaluation_status):
    job = SimpleNamespace(
        status=SimpleNamespace(value=generation_status),
        synthetic_file_path="generated.csv" if generation_status == "COMPLETED" else None,
        evaluation_report_json=None,
    )
    fields = _evaluation_response_fields(job)
    assert fields["evaluation_status"] == expected_evaluation_status
    assert fields["quality_accepted"] is None


def test_ml_utility_unavailable_cases_return_incomplete_without_fallback_scores():
    frame = __import__("pandas").DataFrame({"only_column": [1, 2]})
    result = evaluate_ml_utility(
        frame, frame, target_column="only_column", task_type="classification"
    )
    assert result["status"] == "INCOMPLETE"
    assert result["metrics"] == {}

