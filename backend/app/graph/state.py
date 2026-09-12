from typing import TypedDict, Dict, Any, Optional


class GraphState(TypedDict):
    """
    Represents the state of our synthetic data generation pipeline graph.
    All fields must be JSON-serializable (no raw DataFrames).
    DataFrames are stored on disk and referenced by path.
    """
    # Inputs
    dataset_id: int
    requirement: Optional[str]

    # File paths (serializable)
    real_data_path: str  # Absolute path to the source CSV/file on disk

    # Metadata
    schema_json: Optional[Dict[str, Any]]
    profile_json: Optional[Dict[str, Any]]
    relationships_json: Optional[Dict[str, Any]]

    # Plans
    generation_plan: Optional[Dict[str, Any]]

    # Outputs (paths, not DataFrames)
    synthetic_data_path: Optional[str]  # Absolute path to temp synthetic CSV

    # Evaluation
    evaluation_report: Optional[Dict[str, Any]]
    evaluation_summary: Optional[str]

    # Best Tracking (for fallback if iterations exhausted)
    best_synthetic_data_path: Optional[str]
    best_evaluation_report: Optional[Dict[str, Any]]
    best_evaluation_summary: Optional[str]

    # Control Flow
    iteration: int
    max_iterations: int
    is_successful: bool
    status_message: str
