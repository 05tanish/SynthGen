from app.graph.state import GraphState

def should_optimize(state: GraphState) -> str:
    """
    Routing logic to decide if we need to optimize or if we're done.
    """
    if state.get("is_successful", False):
        return "end"
        
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 3)
    
    if iteration >= max_iterations:
        return "end"
        
    return "optimize"
