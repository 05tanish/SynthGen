import os
import tempfile

from app.graph.state import GraphState
from app.agents.generation_planner_agent import GenerationPlannerAgent
from app.agents.requirement_schema_agent import RequirementSchemaAgent
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

    plan = state["generation_plan"]
    model_name = plan["selected_model"]
    params = plan.get("parameters") or {}

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
    import os as _os
    if model_name in ("CTGAN", "TVAE") and _os.getenv("ALLOW_SLOW_MODELS", "false").lower() != "true":
        logger.warning(
            f"Model '{model_name}' selected by planner but overridden to GaussianCopula. "
            f"Set ALLOW_SLOW_MODELS=true to enable CTGAN/TVAE (requires high-memory server)."
        )
        model_name = "GaussianCopula"
        params = {}

    if model_name == "GaussianCopula":
        generator = GaussianCopulaGenerator(parameters=params)
    elif model_name == "CTGAN":
        generator = CTGANGenerator(parameters=params)
    elif model_name == "TVAE":
        generator = TVAEGenerator(parameters=params)
    else:
        logger.warning(f"Unknown model '{model_name}', falling back to GaussianCopula.")
        generator = GaussianCopulaGenerator(parameters={})

    logger.info(f"Fitting {model_name} on {len(fit_df)} rows...")
    # Run the fit in a thread with a hard timeout.
    # CTGAN/TVAE training is CPU-bound and can run 15+ minutes on large datasets.
    # Without a timeout the worker thread blocks forever and Railway kills the container.
    import concurrent.futures
    FIT_TIMEOUT_SECONDS = 600  # 10 minutes max per fit attempt
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(generator.fit, fit_df)
        try:
            future.result(timeout=FIT_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            raise RuntimeError(
                f"{model_name} model fitting exceeded {FIT_TIMEOUT_SECONDS}s timeout. "
                f"Try reducing MAX_ITERATIONS or dataset size."
            )

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
    synthetic_df = generator.generate(num_rows=row_count)

    # Store synthetic data to a temp file to avoid non-serializable DataFrame in state
    tmp_file = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    synthetic_df.to_csv(tmp_file.name, index=False)
    tmp_file.close()

    state["synthetic_data_path"] = tmp_file.name
    state["status_message"] = f"Generated {row_count} rows using {model_name} (fitted on {len(fit_df)} rows)."
    return state


def evaluate_data_node(state: GraphState) -> GraphState:
    logger.info("Executing evaluate_data_node...")

    real_data_path = state.get("real_data_path")
    synth_data_path = state.get("synthetic_data_path")

    if not real_data_path or not os.path.exists(real_data_path):
        raise ValueError(f"real_data_path is invalid: {real_data_path}")
    if not synth_data_path or not os.path.exists(synth_data_path):
        raise ValueError(f"synthetic_data_path is invalid: {synth_data_path}")

    import pandas as pd
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
