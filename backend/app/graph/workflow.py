from langgraph.graph import StateGraph, END
from app.graph.state import GraphState
from app.graph.nodes import (
    plan_generation_node,
    generate_data_node,
    evaluate_data_node,
    optimize_plan_node
)
from app.graph.routers import should_optimize

def build_workflow() -> StateGraph:
    """
    Builds the LangGraph workflow for synthetic data generation.
    """
    workflow = StateGraph(GraphState)
    
    # Add Nodes
    workflow.add_node("planner", plan_generation_node)
    workflow.add_node("generator", generate_data_node)
    workflow.add_node("evaluator", evaluate_data_node)
    workflow.add_node("optimizer", optimize_plan_node)
    
    # Add Edges
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "generator")
    workflow.add_edge("generator", "evaluator")
    
    # Conditional Routing after Evaluation
    workflow.add_conditional_edges(
        "evaluator",
        should_optimize,
        {
            "end": END,
            "optimize": "optimizer"
        }
    )
    
    # Optimizer loops back to generator
    workflow.add_edge("optimizer", "generator")
    
    return workflow.compile()
