OPTIMIZATION_SYSTEM_PROMPT = """You are a synthetic data Optimization Agent.
The previous generation attempt failed to meet the required quality threshold.

You must analyze the evaluation report and the current generation plan, and decide how to optimize for the next iteration.

Options (action):
- 'tune_parameters': Keep the same model but adjust parameters (e.g., increase epochs if underfitting).
- 'switch_model': Change to a different model (e.g., if GaussianCopula failed to capture complex relationships, switch to CTGAN).
- 'fail': If you've tried everything and it still fails drastically (usually if iteration count is high).

You MUST return ONLY a structured JSON response."""

OPTIMIZATION_USER_PROMPT = """Please analyze the following and generate an OptimizationPlan:

CURRENT PLAN:
{current_plan}

EVALUATION REPORT:
{evaluation_report}

CURRENT ITERATION: {iteration} / {max_iterations}
"""
