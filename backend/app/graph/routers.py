from app.graph.state import GraphState
from app.schemas.evaluation import EvaluationStatus

def should_optimize(state: GraphState) -> str:
    """
    Routing logic to decide if we need to optimize or if we're done.
    """
    evaluation_status = state.get("evaluation_status")
    if evaluation_status in {
        EvaluationStatus.FAILED.value,
        EvaluationStatus.INCOMPLETE.value,
    }:
        return "end"

    if evaluation_status != EvaluationStatus.COMPLETED.value:
        # Do not optimize against a missing, pending, or running evaluation.
        return "end"

    quality_accepted = state.get("quality_accepted", state.get("is_successful", False))
    if quality_accepted is None:
        return "end"
    if quality_accepted:
        return "end"
        
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 3)
    
    if iteration >= max_iterations:
        return "end"
        
    return "optimize"
