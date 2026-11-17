import os
import tempfile
import time
import platform
import sys
from datetime import datetime, timezone

from app.graph.state import GraphState
from app.agents.generation_planner_agent import GenerationPlannerAgent
from app.agents.requirement_schema_agent import RequirementSchemaAgent
from app.agents.optimization_agent import OptimizationAgent
from app.tools.synthetic_generator import (
    GaussianCopulaGenerator, CTGANGenerator, TVAEGenerator,
    parse_row_count_from_prompt,
)
from app.tools.statistical_evaluator import evaluate_statistical_quality
from app.tools.schema_evaluator import evaluate_schema_fidelity
from app.tools.privacy_checker import evaluate_privacy_risk
from app.tools.ml_utility_evaluator import evaluate_ml_utility
from app.schemas.evaluation import EvaluationReport, EvaluationStatus
from app.core.logging import logger


def _create_generator(requested_model, parameters, allow_slow_models=None):
    """Resolve requested versus actually executable synthesizer explicitly."""
    actual_model = requested_model
    effective_input = parameters or {}
    fallback_reason = None
    if allow_slow_models is None:
        allow_slow_models = os.getenv("ALLOW_SLOW_MODELS", "false").lower() == "true"
    if actual_model in ("CTGAN", "TVAE") and not allow_slow_models:
        fallback_reason = "Slow model execution is disabled by ALLOW_SLOW_MODELS."
        actual_model = "GaussianCopula"
        effective_input = {}
    if actual_model == "GaussianCopula":
        generator = GaussianCopulaGenerator(parameters=effective_input)
    elif actual_model == "CTGAN":
        generator = CTGANGenerator(parameters=effective_input)
    elif actual_model == "TVAE":
        generator = TVAEGenerator(parameters=effective_input)
    else:
        fallback_reason = f"Unknown requested model: {actual_model}."
        actual_model = "GaussianCopula"
        generator = GaussianCopulaGenerator(parameters={})
    return generator, actual_model, fallback_reason


def plan_generation_node(state: GraphState) -> GraphState:
    logger.info("Executing plan_generation_node...")

    if state.get("generation_plan"):
        return state  # already planned
        
    req = state.get("requirement")
    if req and req.strip() and not state.get("requirement_analysis"):
        logger.info("Extracting NLP constraints from requirement prompt...")
        try:
            req_agent = RequirementSchemaAgent()
            analysis = req_agent.analyze_requirement(req)
            state["requirement_analysis"] = analysis.model_dump()
        except Exception as e:
            logger.warning(f"Failed to extract NLP requirements: {e}. Proceeding without structured requirements.")
    
    # Try to get cached profile/relationships if not in state
    dataset_id = state.get("dataset_id")
    if dataset_id:
        from app.cache.cache_service import CacheService
        
        if not state.get("profile_json"):
            cached_profile = CacheService.get_dataset_profile(dataset_id)
            if cached_profile:
                logger.info(f"Using cached profile for dataset {dataset_id}")
                state["profile_json"] = cached_profile
        
        if not state.get("relationships_json"):
            cached_relationships = CacheService.get_dataset_relationships(dataset_id)
            if cached_relationships:
                logger.info(f"Using cached relationships for dataset {dataset_id}")
                state["relationships_json"] = cached_relationships

    planner = GenerationPlannerAgent()
    plan = planner.plan(
        schema_json=state.get("schema_json") or {},
        profile_json=state.get("profile_json") or {},
        relationships_json=state.get("relationships_json") or {},
        requirement=state.get("requirement"),  # Pass user's custom prompt
        requirement_analysis=state.get("requirement_analysis"), # Pass extracted NLP constraints
    )

    state["generation_plan"] = plan.model_dump()
    state["status_message"] = "Initial generation plan created."
    return state


def generate_data_node(state: GraphState) -> GraphState:
    logger.info("Executing generate_data_node...")
    try:
        return _generate_data_node_impl(state)
    except Exception as e:
        logger.error(f"generate_data_node failed: {e}", exc_info=True)
        state["is_successful"] = False
        state["iteration"] = state.get("max_iterations", 1)
        state["status_message"] = f"Data generation failed: {str(e)[:300]}"
        return state


def _generate_data_node_impl(state: GraphState) -> GraphState:

    plan = state["generation_plan"]
    requested_model = str(plan["selected_model"])
    model_name = requested_model
    params = plan.get("parameters") or {}
    fallback_reason = None
    random_seed = int(plan.get("random_seed", 42))

    # Load real_data from file path (avoids keeping DataFrame in state)
    real_data_path = state.get("real_data_path")
    if not real_data_path or not os.path.exists(real_data_path):
        raise ValueError(f"real_data_path is missing or invalid: {real_data_path}")
    import pandas as pd
    real_df = pd.read_csv(real_data_path)
    
    # ========================================================================
    # PERFORMANCE OPTIMIZATION: Sampling-Based Fit
    # ========================================================================
    # For large datasets, fit on a stratified sample to reduce training time.
    # Target: Max 5000 rows for fitting, regardless of dataset size.
    # This reduces CTGAN fit time from 25min → 3min for 25K row datasets.
    # ========================================================================
    
    original_row_count = len(real_df)
    fit_df = real_df  # Default: fit on full dataset
    
    # Use sampling for datasets larger than 5000 rows
    SAMPLE_THRESHOLD = 5000
    MAX_SAMPLE_SIZE = 5000
    
    if original_row_count > SAMPLE_THRESHOLD:
        sample_size = min(MAX_SAMPLE_SIZE, original_row_count)
        logger.info(f"Dataset has {original_row_count} rows. Using stratified sample of {sample_size} rows for model fitting.")
        
        # Try stratified sampling by categorical columns to preserve distribution
        try:
            # Identify categorical columns
            categorical_cols = [col for col in real_df.columns if real_df[col].dtype == 'object' or real_df[col].nunique() < 50]
            
            if categorical_cols:
                # Use first categorical column for stratification
                stratify_col = categorical_cols[0]
                logger.info(f"Stratifying sample by column: {stratify_col}")
                
                from sklearn.model_selection import train_test_split
                fit_df, _ = train_test_split(
                    real_df,
                    train_size=sample_size,
                    stratify=real_df[stratify_col],
                    random_state=42
                )
            else:
                # No categorical columns, use random sampling
                logger.info("No categorical columns found. Using random sampling.")
                fit_df = real_df.sample(n=sample_size, random_state=42)
        
        except Exception as e:
            # Fallback to random sampling if stratification fails
            logger.warning(f"Stratified sampling failed: {e}. Using random sampling.")
            fit_df = real_df.sample(n=sample_size, random_state=42)
        
        logger.info(f"Sample created: {len(fit_df)} rows (original: {original_row_count} rows)")
        logger.info(f"Expected speedup: ~{original_row_count / sample_size:.1f}x faster model fitting")

    # ── Production safety override ───────────────────────────────────────────
    # CTGAN/TVAE require 10-25 min of CPU-bound PyTorch training.
    # On Railway (shared CPU, ~512MB-1GB RAM) this causes OOM kills or timeouts.
    # Force GaussianCopula unless ALLOW_SLOW_MODELS=true is explicitly set.
    generator, actual_model, fallback_reason = _create_generator(
        requested_model, params
    )
    if fallback_reason:
        logger.warning(
            f"Requested model '{requested_model}' resolved to '{actual_model}': {fallback_reason}"
        )
    model_name = actual_model

    logger.info(f"Fitting {model_name} on {len(fit_df)} rows...")
    # Run the fit in a thread with a hard timeout.
    # CTGAN/TVAE training is CPU-bound and can run 15+ minutes on large datasets.
    # Without a timeout the worker thread blocks forever and Railway kills the container.
    import concurrent.futures
    FIT_TIMEOUT_SECONDS = 600  # 10 minutes max per fit attempt
    fit_started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(generator.fit, fit_df)
        try:
            future.result(timeout=FIT_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            raise RuntimeError(
                f"{model_name} model fitting exceeded {FIT_TIMEOUT_SECONDS}s timeout. "
                f"Try reducing MAX_ITERATIONS or dataset size."
            )
    fit_runtime_seconds = time.perf_counter() - fit_started

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
        row_count = original_row_count
        logger.info(f"Using row count from real data length: {row_count}")

    logger.info(f"Generating {row_count} rows...")
    sample_started = time.perf_counter()
    synthetic_df = generator.generate(num_rows=row_count, random_seed=random_seed)
    sample_runtime_seconds = time.perf_counter() - sample_started

    # Store synthetic data to a temp file to avoid non-serializable DataFrame in state
    tmp_file = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    synthetic_df.to_csv(tmp_file.name, index=False)
    tmp_file.close()

    state["synthetic_data_path"] = tmp_file.name
    try:
        from importlib.metadata import version
        sdv_version = version("sdv")
    except Exception:
        sdv_version = None
    state["generator_metadata"] = {
        "requested_generator": requested_model,
        "actual_generator": model_name,
        "fallback_reason": fallback_reason,
        "effective_parameters": generator.effective_parameters,
        "random_seed": random_seed,
        "sampling_seed_applied": bool(getattr(generator, "random_seed_applied", False)),
        "seed_scope": "SDV sampling state; model fitting may use library/framework randomness",
        "sdv_version": sdv_version,
        "fit_row_count": int(len(fit_df)),
        "source_row_count": int(original_row_count),
        "generated_row_count": int(len(synthetic_df)),
        "generated_column_count": int(len(synthetic_df.columns)),
        "fit_runtime_seconds": fit_runtime_seconds,
        "sampling_runtime_seconds": sample_runtime_seconds,
    }
    state["status_message"] = f"Generated {row_count} rows using {model_name} (fitted on {len(fit_df)} rows)."
    return state


def evaluate_data_node(state: GraphState) -> GraphState:
    logger.info("Executing evaluate_data_node...")
    evaluation_started = time.perf_counter()
    state["evaluation_status"] = EvaluationStatus.RUNNING.value
    try:
        return _evaluate_data_node_impl(state)
    except Exception as e:
        logger.error(f"evaluate_data_node failed: {e}", exc_info=True)
        failed_component = state.get("evaluation_component", "evaluation_pipeline")
        component_statuses = {
            "schema_fidelity": "NOT_RUN",
            "statistical_fidelity": "NOT_RUN",
            "privacy_risk": "NOT_RUN",
            "ml_utility": "NOT_RUN",
        }
        component_key = {
            "schema": "schema_fidelity",
            "statistical": "statistical_fidelity",
            "privacy": "privacy_risk",
            "ml_utility": "ml_utility",
        }.get(failed_component)
        if component_key:
            component_statuses[component_key] = "FAILED"
        report = EvaluationReport(
            evaluation_status=EvaluationStatus.FAILED,
            quality_accepted=None,
            failed_component=failed_component,
            error_message=str(e)[:500],
            errors=[{
                "component": state.get("evaluation_component", "evaluation_pipeline"),
                "message": str(e)[:500],
                "exception_type": type(e).__name__,
            }],
            component_statuses=component_statuses,
            execution_metadata={
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "runtime_seconds": time.perf_counter() - evaluation_started,
                "generator": state.get("generator_metadata") or {},
            },
            limitations=["Quality was not evaluated successfully; no quality acceptance decision was made."],
        )
        state["evaluation_status"] = EvaluationStatus.FAILED.value
        state["quality_accepted"] = None
        state["is_successful"] = False
        state["evaluation_report"] = report.model_dump(mode="json")
        state["evaluation_summary"] = "Evaluation failed; generated data was not quality-evaluated."
        state["status_message"] = f"Evaluation failed: {str(e)[:200]}"
        return state


def _evaluate_data_node_impl(state: GraphState) -> GraphState:
    evaluation_started = time.perf_counter()

    real_data_path = state.get("real_data_path")
    synth_data_path = state.get("synthetic_data_path")

    if not real_data_path or not os.path.exists(real_data_path):
        raise ValueError(f"real_data_path is invalid: {real_data_path}")
    if not synth_data_path or not os.path.exists(synth_data_path):
        raise ValueError(f"synthetic_data_path is invalid: {synth_data_path}")

    import pandas as pd
    real_df = pd.read_csv(real_data_path)
    synth_df = pd.read_csv(synth_data_path)

    state["evaluation_component"] = "ml_utility"
    evaluation_config = state.get("evaluation_config") or {}
    component_errors = []

    def evaluate_component(name, evaluator):
        state["evaluation_component"] = name
        try:
            return evaluator()
        except Exception as exc:
            error = {
                "component": name,
                "message": str(exc)[:500],
                "exception_type": type(exc).__name__,
            }
            component_errors.append(error)
            logger.error(f"{name} evaluation failed: {exc}", exc_info=True)
            return {
                "status": "FAILED",
                "errors": [error],
                "limitations": [f"{name} metrics were not produced because evaluation raised an exception."],
            }

    schema_result = evaluate_component(
        "schema", lambda: evaluate_schema_fidelity(real_df, synth_df)
    )
    stat_result = evaluate_component(
        "statistical",
        lambda: evaluate_statistical_quality(
            real_df,
            synth_df,
            schema_result=schema_result if schema_result.get("status") != "FAILED" else None,
        ),
    )
    priv_result = evaluate_component(
        "privacy", lambda: evaluate_privacy_risk(real_df, synth_df)
    )
    ml_result = evaluate_component(
        "ml_utility",
        lambda: evaluate_ml_utility(
            real_df,
            synth_df,
            target_column=evaluation_config.get("target_column"),
            task_type=evaluation_config.get("task_type"),
            random_seed=int(evaluation_config.get("random_seed", 42)),
        ),
    )
    state.pop("evaluation_component", None)

    # Components remain independent. No weighted aggregate is calculated from
    # metrics with different meanings or units.
    is_successful = False
    component_statuses = {
        "schema_fidelity": schema_result.get("status", "UNKNOWN"),
        "statistical_fidelity": stat_result.get("status", "UNKNOWN"),
        "privacy_risk": priv_result.get("status", "UNKNOWN"),
        "ml_utility": ml_result.get("status", "UNKNOWN"),
    }
    evaluation_status = (
        EvaluationStatus.FAILED.value
        if component_errors
        else EvaluationStatus.INCOMPLETE.value
        if any(status in {"INCOMPLETE", "FAILED"} for status in component_statuses.values())
        else EvaluationStatus.COMPLETED.value
    )
    for result in (schema_result, stat_result, priv_result, ml_result):
        for error in result.get("errors", []):
            if error not in component_errors:
                component_errors.append(error)
    dependency_versions = {}
    try:
        from importlib.metadata import version
        for package in ("pandas", "numpy", "scipy", "scikit-learn", "sdv"):
            try:
                dependency_versions[package] = version(package)
            except Exception:
                dependency_versions[package] = None
    except Exception:
        dependency_versions = {}
    execution_metadata = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": time.perf_counter() - evaluation_started,
        "real_dimensions": {"rows": int(len(real_df)), "columns": int(len(real_df.columns))},
        "synthetic_dimensions": {"rows": int(len(synth_df)), "columns": int(len(synth_df.columns))},
        "evaluation_configuration": {
            "target_column": evaluation_config.get("target_column"),
            "task_type": evaluation_config.get("task_type"),
            "random_seed": int(evaluation_config.get("random_seed", 42)),
        },
        "generator": state.get("generator_metadata") or {},
        "dependency_versions": dependency_versions,
        "runtime_environment": {
            "platform": platform.platform(),
            "python_version": sys.version.split()[0],
            "logical_cpu_count": os.cpu_count(),
        },
    }

    report = EvaluationReport(
        evaluation_status=evaluation_status,
        quality_accepted=None,
        failed_component=component_errors[0]["component"] if component_errors else None,
        error_message=component_errors[0]["message"] if component_errors else None,
        statistical_details=stat_result,
        schema_details=schema_result,
        privacy_details=priv_result,
        ml_utility_details=ml_result,
        component_statuses=component_statuses,
        errors=component_errors,
        execution_metadata=execution_metadata,
        limitations=[
            "Component completion does not imply quality acceptance.",
            "Privacy indicators are empirical and do not provide formal privacy guarantees.",
        ],
    )

    summary = (
        "Schema and statistical fidelity metrics completed. "
        "No combined quality acceptance decision was made."
    )

    # Preserve a usable generated artifact/report without ranking incomparable
    # metric families by a made-up aggregate.
    if not state.get("best_evaluation_report"):
        state["best_synthetic_data_path"] = state.get("synthetic_data_path")
        state["best_evaluation_report"] = report.model_dump(mode="json")
        state["best_evaluation_summary"] = summary

    state["evaluation_report"] = report.model_dump(mode="json")
    state["evaluation_status"] = evaluation_status
    state["quality_accepted"] = None
    state["evaluation_summary"] = summary
    state["is_successful"] = is_successful
    state["iteration"] = state.get("iteration", 0) + 1

    state["status_message"] = (
        f"Evaluation {evaluation_status.lower()}. Quality acceptance is undecided; see component-level metrics."
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
