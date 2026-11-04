"""
Langfuse Integration for LLM Observability

Provides comprehensive tracking of:
- LLM requests and responses
- Token usage and costs
- Latency measurements
- LangGraph workflow execution
- Agent performance metrics
- Error tracking

Usage:
    from app.core.langfuse_tracer import get_langfuse_handler, trace_generation_job
    
    # For LangChain/LangGraph
    handler = get_langfuse_handler(trace_name="generation_job_123")
    llm.invoke(messages, config={"callbacks": [handler]})
    
    # For custom operations
    with trace_generation_job(job_id=123) as trace:
        # Your code here
        trace.update(output={"status": "completed"})
"""

from typing import Optional, Dict, Any
from contextlib import contextmanager
from app.core.config import settings
from app.core.logging import logger

# Lazy initialization - only import if Langfuse is enabled
_langfuse_client = None
_langfuse_available = False


# No-op classes for when Langfuse is unavailable
class NoOpTrace:
    """Dummy trace object when Langfuse is unavailable"""
    def update(self, **kwargs):
        pass
    def span(self, *args, **kwargs):
        return NoOpSpan()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass


class NoOpSpan:
    """Dummy span object when Langfuse is unavailable"""
    def update(self, **kwargs):
        pass
    def end(self, **kwargs):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass


def _init_langfuse():
    """Initialize Langfuse client (lazy loading)"""
    global _langfuse_client, _langfuse_available
    
    if _langfuse_client is not None:
        return _langfuse_client
    
    if not settings.LANGFUSE_ENABLED:
        logger.info("Langfuse observability is disabled via LANGFUSE_ENABLED=False")
        _langfuse_available = False
        return None
    
    if not settings.LANGFUSE_SECRET_KEY or not settings.LANGFUSE_PUBLIC_KEY:
        logger.warning(
            "Langfuse keys not configured. Set LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY "
            "to enable LLM observability. Continuing without Langfuse."
        )
        _langfuse_available = False
        return None
    
    try:
        from langfuse import Langfuse
        
        _langfuse_client = Langfuse(
            secret_key=settings.LANGFUSE_SECRET_KEY,
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            host=settings.LANGFUSE_HOST,
        )
        _langfuse_available = True
        logger.info(f"Langfuse observability initialized successfully (host: {settings.LANGFUSE_HOST})")
        return _langfuse_client
        
    except ImportError:
        logger.warning(
            "Langfuse package not installed. Run 'pip install langfuse' to enable LLM observability. "
            "Continuing without Langfuse."
        )
        _langfuse_available = False
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Langfuse: {e}. Continuing without observability.")
        _langfuse_available = False
        return None


def is_langfuse_available() -> bool:
    """Check if Langfuse is available and configured"""
    if _langfuse_client is None:
        _init_langfuse()
    return _langfuse_available


def get_langfuse_handler(
    trace_name: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[list] = None
):
    """
    Get a Langfuse callback handler for LangChain/LangGraph.
    
    Args:
        trace_name: Name of the trace (e.g., "generation_job_123")
        user_id: User ID for tracking
        session_id: Session ID for grouping related traces
        metadata: Additional metadata to attach
        tags: Tags for filtering (e.g., ["production", "ctgan"])
    
    Returns:
        CallbackHandler instance or None if Langfuse unavailable
    """
    client = _init_langfuse()
    if not client:
        return None
    
    try:
        from langfuse.callback import CallbackHandler
        
        handler = CallbackHandler(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
            trace_name=trace_name,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {},
            tags=tags or [],
        )
        return handler
    except Exception as e:
        logger.error(f"Failed to create Langfuse callback handler: {e}")
        return None


@contextmanager
def trace_generation_job(
    job_id: int,
    dataset_id: int,
    user_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Context manager for tracing a complete generation job.
    
    Usage:
        with trace_generation_job(job_id=123, dataset_id=456, user_id=789) as trace:
            # Your generation code here
            trace.update(output={"status": "completed", "rows": 1000})
    
    Args:
        job_id: Job ID
        dataset_id: Dataset ID
        user_id: User ID
        metadata: Additional metadata (e.g., model, parameters)
    """
    client = _init_langfuse()
    if not client:
        # Return a no-op context manager if Langfuse unavailable
        yield NoOpTrace()
        return
    
    try:
        trace = client.trace(
            name=f"generation_job_{job_id}",
            user_id=str(user_id) if user_id else None,
            session_id=f"dataset_{dataset_id}",
            metadata={
                "job_id": job_id,
                "dataset_id": dataset_id,
                **(metadata or {})
            },
            tags=["generation", "production"]
        )
        
        yield trace
        
        # Flush at the end of the trace
        client.flush()
        
    except Exception as e:
        logger.error(f"Error in Langfuse trace: {e}")
        yield NoOpTrace()


def trace_agent_execution(
    agent_name: str,
    input_data: Dict[str, Any],
    parent_trace = None
):
    """
    Create a span for individual agent execution.
    
    Args:
        agent_name: Name of the agent (e.g., "GenerationPlannerAgent")
        input_data: Input to the agent
        parent_trace: Parent trace to attach this span to
    
    Returns:
        Span object or NoOpSpan if Langfuse unavailable
    """
    if not parent_trace or not is_langfuse_available():
        return NoOpSpan()
    
    try:
        span = parent_trace.span(
            name=agent_name,
            input=input_data,
            metadata={"agent": agent_name}
        )
        return span
    except Exception as e:
        logger.error(f"Error creating agent span: {e}")
        return NoOpSpan()


def log_llm_generation(
    trace_name: str,
    model: str,
    input_text: str,
    output_text: str,
    metadata: Optional[Dict[str, Any]] = None,
    usage: Optional[Dict[str, int]] = None,
    latency_ms: Optional[float] = None
):
    """
    Log a single LLM generation event.
    
    Args:
        trace_name: Name for this generation
        model: Model name (e.g., "llama-3.3-70b-versatile")
        input_text: Input prompt
        output_text: Generated output
        metadata: Additional metadata
        usage: Token usage {"prompt_tokens": X, "completion_tokens": Y, "total_tokens": Z}
        latency_ms: Latency in milliseconds
    """
    client = _init_langfuse()
    if not client:
        return
    
    try:
        generation = client.generation(
            name=trace_name,
            model=model,
            input=input_text,
            output=output_text,
            metadata=metadata or {},
            usage=usage,
            start_time=None,  # Will be set automatically
            end_time=None,
        )
        
        if latency_ms:
            generation.update(latency_ms=latency_ms)
        
        client.flush()
        
    except Exception as e:
        logger.error(f"Error logging LLM generation to Langfuse: {e}")


def flush_langfuse():
    """
    Flush all pending Langfuse events.
    Call this at the end of critical operations to ensure data is sent.
    """
    if _langfuse_client:
        try:
            _langfuse_client.flush()
        except Exception as e:
            logger.error(f"Error flushing Langfuse: {e}")
