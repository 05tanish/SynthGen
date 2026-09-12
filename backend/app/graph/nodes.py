import os
import tempfile
import pandas as pd
from app.graph.state import GraphState
from app.agents.generation_planner_agent import GenerationPlannerAgent
from app.agents.optimization_agent import OptimizationAgent
from app.agents.evaluation_agent import EvaluationAgent
from app.tools.synthetic_generator import (
    GaussianCopulaGenerator, CTGANGenerator, TVAEGenerator,
    parse_row_count_from_prompt,
)
from app.tools.statistical_evaluator import evaluate_statistical_quality
from app.tools.privacy_checker import evaluate_privacy_risk
from app.tools.ml_utility_evaluator import evaluate_ml_utility
from app.schemas.evaluation import EvaluationReport
from app.core.logging import logger
from app.core.config import settings


def plan_generation_node(state: GraphState) -> GraphState:
    logger.info("Executing plan_generation_node...")

    if state.get("generation_plan"):
        return state  # already planned

    planner = GenerationPlannerAgent()
    plan = planner.plan(
        schema_json=state.get("schema_json") or {},
        profile_json=state.get("profile_json") or {},
        relationships_json=state.get("relationships_json") or {},
        requirement=state.get("requirement"),  # Pass user's custom prompt
    )

    state["generation_plan"] = plan.model_dump()
    state["status_message"] = "Initial generation plan created."
    return state


def generate_data_node(state: GraphState) -> GraphState:
    logger.info("Executing generate_data_node...")

    plan = state["generation_plan"]
    model_name = plan["selected_model"]
    params = plan.get("parameters") or {}

    # Load real_data from file path (avoids keeping DataFrame in state)
    real_data_path = state.get("real_data_path")
    if not real_data_path or not os.path.exists(real_data_path):
        raise ValueError(f"real_data_path is missing or invalid: {real_data_path}")
    real_df = pd.read_csv(real_data_path)

    if model_name == "GaussianCopula":
        generator = GaussianCopulaGenerator(parameters=params)
    elif model_name == "CTGAN":
        generator = CTGANGenerator(parameters=params)
    elif model_name == "TVAE":
        generator = TVAEGenerator(parameters=params)
    else:
        logger.warning(f"Unknown model '{model_name}', falling back to GaussianCopula.")
        generator = GaussianCopulaGenerator(parameters={})

    logger.info(f"Fitting {model_name}...")
    generator.fit(real_df)

    # Priority order for row count:
    # 1. User's natural-language prompt (e.g. "generate 500 rows")
    # 2. Profile summary row_count (mirrors original dataset size)
    # 3. Actual length of the real dataframe
    prompt_row_count = parse_row_count_from_prompt(state.get("requirement"))
    profile_summary = (state.get("profile_json") or {}).get("summary", {})
    profile_row_count = profile_summary.get("row_count")

    if prompt_row_count:
        row_count = prompt_row_count
        logger.info(f"Using row count from user prompt: {row_count}")
    elif profile_row_count:
        row_count = profile_row_count
        logger.info(f"Using row count from profile: {row_count}")
    else:
        row_count = len(real_df)
        logger.info(f"Using row count from real data length: {row_count}")

    logger.info(f"Generating {row_count} rows...")
    synthetic_df = generator.generate(num_rows=row_count)

    # Store synthetic data to a temp file to avoid non-serializable DataFrame in state
    tmp_file = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    synthetic_df.to_csv(tmp_file.name, index=False)
    tmp_file.close()

    state["synthetic_data_path"] = tmp_file.name
    state["status_message"] = f"Generated {row_count} rows using {model_name}."
    return state


def evaluate_data_node(state: GraphState) -> GraphState:
    logger.info("Executing evaluate_data_node...")

    real_data_path = state.get("real_data_path")
    synth_data_path = state.get("synthetic_data_path")

    if not real_data_path or not os.path.exists(real_data_path):
        raise ValueError(f"real_data_path is invalid: {real_data_path}")
    if not synth_data_path or not os.path.exists(synth_data_path):
        raise ValueError(f"synthetic_data_path is invalid: {synth_data_path}")

    real_df = pd.read_csv(real_data_path)
    synth_df = pd.read_csv(synth_data_path)

    stat_result = evaluate_statistical_quality(real_df, synth_df)
    priv_result = evaluate_privacy_risk(real_df, synth_df)
    ml_result = evaluate_ml_utility(real_df, synth_df)

    # Calculate overall weighted score
    overall_score = (
        stat_result["score"] * 0.4
        + priv_result["score"] * 0.4
        + ml_result["score"] * 0.2
    )

    # Use configurable thresholds from settings
    quality_threshold = settings.QUALITY_THRESHOLD
    privacy_threshold = max(0.5, quality_threshold - 0.15)  # privacy floor scales with quality
    is_successful = overall_score >= quality_threshold and priv_result["score"] >= privacy_threshold

    logger.info(
        f"Evaluation: overall={overall_score:.3f} (threshold={quality_threshold}), "
        f"privacy={priv_result['score']:.3f} (threshold={privacy_threshold:.2f}), "
        f"passed={is_successful}"
    )

    report = EvaluationReport(
        statistical_score=stat_result["score"],
        privacy_score=priv_result["score"],
        ml_utility_score=ml_result["score"],
        overall_score=overall_score,
        passed=is_successful,
        statistical_details=stat_result["details"],
        privacy_details=priv_result["details"],
        ml_utility_details=ml_result["details"],
    )

    eval_agent = EvaluationAgent()
    try:
        summary = eval_agent.summarize_evaluation(report)
    except Exception as e:
        logger.error(f"EvaluationAgent failed to summarize, using fallback: {e}")
        summary = f"Overall score: {overall_score:.2f}. Passed: {is_successful}."

    # Track the best result seen so far (by overall_score) so we can save it
    # even if we never reach the threshold after all iterations.
    best_score = (state.get("best_evaluation_report") or {}).get("overall_score", 0.0)
    if overall_score >= best_score:
        state["best_synthetic_data_path"] = state.get("synthetic_data_path")
        state["best_evaluation_report"] = report.model_dump()
        state["best_evaluation_summary"] = summary

    state["evaluation_report"] = report.model_dump()
    state["evaluation_summary"] = summary
    state["is_successful"] = is_successful
    state["iteration"] = state.get("iteration", 0) + 1

    status = "SUCCESS" if is_successful else "FAILED"
    state["status_message"] = (
        f"Evaluation {status}. Overall Score: {overall_score:.2f} / threshold {quality_threshold}."
    )

    return state


def optimize_plan_node(state: GraphState) -> GraphState:
    logger.info("Executing optimize_plan_node...")

    optimizer = OptimizationAgent()
    try:
        opt_plan = optimizer.optimize(
            current_plan=state["generation_plan"],
            evaluation_report=state["evaluation_report"],
            iteration=state["iteration"],
            max_iterations=state["max_iterations"],
        )
    except Exception as e:
        logger.error(f"OptimizationAgent failed: {e}. Ending workflow.")
        state["is_successful"] = False
        state["iteration"] = state["max_iterations"]
        state["status_message"] = f"Optimization agent failed with error: {e}"
        return state

    if opt_plan.action == "fail":
        state["is_successful"] = False
        state["iteration"] = state["max_iterations"]
        state["status_message"] = "Optimization agent gave up. End of line."
    else:
        state["generation_plan"]["selected_model"] = opt_plan.new_model
        state["generation_plan"]["parameters"] = opt_plan.new_parameters
        state["status_message"] = (
            f"Optimized plan: switching to {opt_plan.new_model} or tuning parameters."
        )

    return state
