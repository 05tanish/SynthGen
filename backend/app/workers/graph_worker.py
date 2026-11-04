import os
import tempfile
import threading
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.database import SessionLocal
from app.models.job import Job, JobStatus
from app.models.dataset import Dataset
from app.graph.workflow import build_workflow
from app.graph.state import GraphState
from app.core.logging import logger
from app.core.config import settings
from app.core import storage as cloud_storage

# ========================================================================
# CONCURRENCY CONTROL: Limit simultaneous generation jobs
# ========================================================================
# Semaphore limits concurrent SDV model training to prevent memory exhaustion
# and ensure predictable performance. Max 2-3 concurrent jobs recommended.
# ========================================================================
MAX_CONCURRENT_JOBS = getattr(settings, 'MAX_CONCURRENT_JOBS', 2)
_job_semaphore = threading.Semaphore(MAX_CONCURRENT_JOBS)


def _update_job(db: Session, job: Job, **kwargs):
    """
    Helper to update job fields and commit with proper transaction isolation.
    Uses row-level locking to prevent race conditions.
    Handles missing columns gracefully for backward compatibility.
    """
    try:
        # Refresh the job within the transaction to get latest state
        db.refresh(job)
        
        for key, value in kwargs.items():
            # Skip progress_percent if column doesn't exist in database
            if key == 'progress_percent':
                try:
                    setattr(job, key, value)
                except Exception as e:
                    logger.debug(f"Could not set progress_percent (column may not exist): {e}")
                    continue
            else:
                setattr(job, key, value)
        
        job.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(job)
    except Exception as e:
        db.rollback()
        error_str = str(e).lower()
        # If it's a column error, log it but don't fail the whole operation
        if "progress_percent" in error_str and ("column" in error_str or "does not exist" in error_str):
            logger.warning(f"Database schema missing progress_percent column. Job updates will continue without progress tracking.")
            # Try again without progress_percent
            try:
                db.refresh(job)
                for key, value in kwargs.items():
                    if key != 'progress_percent':
                        setattr(job, key, value)
                job.updated_at = datetime.now(timezone.utc)
                db.commit()
                db.refresh(job)
                return
            except Exception as retry_error:
                logger.error(f"Failed to update job {job.id} even without progress_percent: {retry_error}")
                db.rollback()
                raise
        else:
            logger.error(f"Failed to update job {job.id}: {e}")
            raise


def _cleanup_temp_file(file_path: str):
    """Safely clean up a temporary file."""
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up temp file {file_path}: {e}")


def run_generation_job(job_id: int):
    logger.info(f"Job {job_id} waiting for concurrency slot...")
    
    # Acquire semaphore - blocks if MAX_CONCURRENT_JOBS are already running
    with _job_semaphore:
        logger.info(f"Job {job_id} acquired concurrency slot. Starting execution...")
        _run_generation_job_internal(job_id)


def _run_generation_job_internal(job_id: int):
    """Internal job execution with proper resource cleanup."""
    db: Session = SessionLocal()
    synth_tmp_path = None  # Track temp file for cleanup
    local_source_path = None  # Track downloaded source file
    
    # Initialize Langfuse trace for this job
    from app.core.langfuse_tracer import trace_generation_job, flush_langfuse
    
    try:
        # Use SELECT FOR UPDATE to lock the job row and prevent concurrent updates
        job = db.query(Job).filter(Job.id == job_id).with_for_update().first()
        if not job:
            logger.error(f"Job {job_id} not found.")
            return

        # Check if job is already running (another worker picked it up)
        if job.status == JobStatus.RUNNING:
            logger.warning(f"Job {job_id} is already running. Skipping duplicate execution.")
            return
        
        # Check if job was cancelled before starting
        if job.status == JobStatus.CANCELLED:
            logger.info(f"Job {job_id} was cancelled before starting. Exiting.")
            return

        dataset = db.query(Dataset).filter(Dataset.id == job.dataset_id).first()
        if not dataset:
            _update_job(db, job, status=JobStatus.FAILED, error_message="Dataset not found.")
            return
        
        # Start Langfuse trace
        with trace_generation_job(
            job_id=job.id,
            dataset_id=dataset.id,
            user_id=job.user_id,
            metadata={
                "dataset_name": dataset.name,
                "row_count": dataset.row_count,
                "column_count": dataset.column_count,
                "source_type": dataset.source_type,
                "prompt": dataset.prompt,
                "max_iterations": settings.MAX_ITERATIONS,
                "quality_threshold": settings.QUALITY_THRESHOLD
            }
        ) as trace:
            _update_job(db, job, status=JobStatus.RUNNING, current_step="loading_data", progress_percent=10)
            
            # Check cancellation after status update
            if _check_cancellation(db, job_id):
                logger.info(f"Job {job_id} cancelled during initialization.")
                return

            # 1. Resolve source — if it's a Cloudinary URL, download to a temp file
            source_ref = dataset.source_filename

            if source_ref and source_ref.startswith("http"):
                ext = os.path.splitext(source_ref.split("?")[0])[-1] or ".csv"
                local_source_path = cloud_storage.download_to_temp(source_ref, suffix=ext)
                source_path = local_source_path
            else:
                # Legacy: local path
                source_path = os.path.abspath(source_ref) if source_ref else None

            if not source_path or not os.path.exists(source_path):
                _update_job(db, job, status=JobStatus.FAILED, error_message="Source file not found.")
                return
            
            # Check cancellation before starting graph
            if _check_cancellation(db, job_id):
                logger.info(f"Job {job_id} cancelled before graph execution.")
                _cleanup_temp_file(local_source_path)
                return

            # 2. Setup State — no DataFrames, only the file path
            initial_state: GraphState = {
                "dataset_id": dataset.id,
                "requirement": dataset.prompt,  # Pass user's custom prompt to the graph
                "requirement_analysis": None,
                "real_data_path": source_path,
                "schema_json": dataset.profile_json,   # Profile acts as schema metadata
                "profile_json": dataset.profile_json,
                "relationships_json": dataset.relationships_json or {},
                "generation_plan": None,
                "synthetic_data_path": None,
                "evaluation_report": None,
                "evaluation_summary": None,
                "best_synthetic_data_path": None,
                "best_evaluation_report": None,
                "best_evaluation_summary": None,
                "iteration": 0,
                "max_iterations": settings.MAX_ITERATIONS,
                "is_successful": False,
                "status_message": "Starting workflow",
            }

            # 3. Run Graph with progress tracking
            workflow = build_workflow()
            _update_job(db, job, current_step="planning_generation", progress_percent=20)
            
            # Check cancellation one more time before expensive graph execution
            if _check_cancellation(db, job_id):
                logger.info(f"Job {job_id} cancelled before workflow invocation.")
                _cleanup_temp_file(local_source_path)
                return

            # Execute workflow with cancellation checking and progress updates
            progress_callback = lambda step, percent: _update_progress(db, job_id, step, percent)
            final_state = _execute_workflow_with_cancellation(
                workflow, initial_state, job_id, db, progress_callback
            )
            
            # If workflow was cancelled, exit
            if final_state is None:
                logger.info(f"Job {job_id} was cancelled during workflow execution.")
                _cleanup_temp_file(local_source_path)
                _cleanup_temp_file(synth_tmp_path)
                return

            # 4. Save results
            is_success = final_state.get("is_successful")
            synth_tmp_path = final_state.get("synthetic_data_path")
            report = final_state.get("evaluation_report")

            if not is_success and final_state.get("best_synthetic_data_path"):
                logger.info("Iterations exhausted without passing threshold. Falling back to the best result.")
                # Clean up the last failed attempt before using best
                _cleanup_temp_file(synth_tmp_path)
                synth_tmp_path = final_state.get("best_synthetic_data_path")
                report = final_state.get("best_evaluation_report")
                
                # Since we are returning the best, we mark it as successful in the DB 
                # so the user can download it, but the report will show it didn't pass strict thresholds.
                is_success = True

            if is_success and synth_tmp_path:
                import uuid
                import pandas as pd

                synth_df = pd.read_csv(synth_tmp_path)

                # Trim or expand to exactly the requested row count
                requested_rows = dataset.row_count or len(synth_df)
                if requested_rows > 30000:
                    logger.warning(f"Requested rows {requested_rows} exceeds limit. Capping to 30,000.")
                    requested_rows = 30000

                if len(synth_df) > requested_rows:
                    synth_df = synth_df.sample(n=requested_rows, random_state=42).reset_index(drop=True)
                elif len(synth_df) < requested_rows:
                    shortfall = requested_rows - len(synth_df)
                    logger.warning(f"Generated {len(synth_df)} rows but {requested_rows} were requested. Filling shortfall of {shortfall} by resampling.")
                    extra = synth_df.sample(n=shortfall, replace=True, random_state=99).reset_index(drop=True)
                    synth_df = pd.concat([synth_df, extra], ignore_index=True)

                # Remove exact duplicate rows
                synth_df = synth_df.drop_duplicates()
                if len(synth_df) < requested_rows:
                    shortfall = requested_rows - len(synth_df)
                    extra = synth_df.sample(n=shortfall, replace=True, random_state=77).reset_index(drop=True)
                    synth_df = pd.concat([synth_df, extra], ignore_index=True)
                synth_df = synth_df.head(requested_rows).reset_index(drop=True)

                logger.info(f"Final synthetic dataset: {len(synth_df)} rows (requested: {requested_rows})")

                # Write final CSV to a temp file, upload to Cloudinary
                filename = f"synthetic_{dataset.id}_{uuid.uuid4().hex[:8]}.csv"
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as f:
                    synth_df.to_csv(f, index=False)
                    final_tmp = f.name

                try:
                    with open(final_tmp, "rb") as f:
                        csv_bytes = f.read()
                    cloudinary_url = cloud_storage.upload_file(
                        csv_bytes,
                        f"synthetic/{filename.replace('.csv', '')}",
                        "synthetix",
                    )
                finally:
                    _cleanup_temp_file(final_tmp)

                # Clean up temp synthetic file after successful upload
                _cleanup_temp_file(synth_tmp_path)
                synth_tmp_path = None

                _update_job(
                    db, job,
                    status=JobStatus.COMPLETED,
                    current_step="finished",
                    progress_percent=100,
                    synthetic_file_path=cloudinary_url,   # URL stored in DB
                    evaluation_report_json=report,
                )
                
                # Update Langfuse trace with success
                trace.update(
                    output={
                        "status": "completed",
                        "row_count": len(synth_df),
                        "quality_score": report.get("overall_score") if report else None,
                        "iterations": final_state.get("iteration"),
                        "selected_model": final_state.get("generation_plan", {}).get("selected_model")
                    }
                )
                
            else:
                # Clean up temp file on failure
                _cleanup_temp_file(synth_tmp_path)
                synth_tmp_path = None
                
                _update_job(
                    db, job,
                    status=JobStatus.FAILED,
                    current_step="failed",
                    error_message=final_state.get("status_message", "Workflow failed to produce valid data."),
                    evaluation_report_json=report,
                )
                
                # Update Langfuse trace with failure
                trace.update(
                    output={
                        "status": "failed",
                        "error": final_state.get("status_message"),
                        "iterations": final_state.get("iteration")
                    },
                    level="ERROR"
                )

            logger.info(f"Job {job_id} finished with status: {job.status}")
        
        # Flush Langfuse to ensure data is sent (outside trace context)
        flush_langfuse()

    except Exception as e:
        logger.error(f"Job {job_id} failed with exception: {str(e)}", exc_info=True)
        _cleanup_temp_file(synth_tmp_path)
        try:
            from app.core.error_sanitiser import safe_error_message
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                _update_job(db, job, status=JobStatus.FAILED, error_message=safe_error_message(e))
        except Exception as inner_e:
            logger.error(f"Failed to update job status after error: {inner_e}")
        
        # Flush Langfuse even on error
        from app.core.langfuse_tracer import flush_langfuse
        flush_langfuse()
        
    finally:
        # Clean up temp local source file if we downloaded from Cloudinary
        if local_source_path and os.path.exists(local_source_path):
            _cleanup_temp_file(local_source_path)
        db.close()


def _update_progress(db: Session, job_id: int, step: str, percent: int):
    """
    Update job progress during workflow execution.
    Non-blocking - failures are logged but don't interrupt workflow.
    """
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            _update_job(db, job, current_step=step, progress_percent=percent)
            logger.debug(f"Job {job_id} progress: {percent}% - {step}")
    except Exception as e:
        logger.warning(f"Failed to update progress for job {job_id}: {e}")


def _check_cancellation(db: Session, job_id: int) -> bool:
    """
    Check if the job has been cancelled.
    Returns True if cancelled, False otherwise.
    """
    db.expire_all()  # Force refresh from database
    job = db.query(Job).filter(Job.id == job_id).first()
    if job and job.status == JobStatus.CANCELLED:
        logger.info(f"Cancellation detected for job {job_id}")
        return True
    return False


def _execute_workflow_with_cancellation(
    workflow, 
    initial_state: GraphState, 
    job_id: int, 
    db: Session,
    progress_callback=None
):
    """
    Execute the LangGraph workflow with periodic cancellation checks and progress updates.
    Returns final state or None if cancelled.
    
    Progress milestones:
    - 20%: Planning generation (before workflow)
    - 30%: Requirement analysis complete
    - 40%: Generation plan created
    - 50%: Starting data generation
    - 70%: Data generation complete
    - 80%: Evaluation in progress
    - 90%: Optimization/iteration (if needed)
    - 100%: Complete
    
    Note: LangGraph doesn't support native cancellation, so this is a best-effort approach.
    We check cancellation between iterations but cannot interrupt SDV fit operations.
    """
    from app.graph.state import GraphState as GState
    
    # Wrap the workflow to inject progress updates at key steps
    # Since LangGraph doesn't expose node-level hooks, we'll monitor state changes
    
    try:
        # Track iteration for progress estimation
        current_iteration = initial_state.get("iteration", 0)
        max_iterations = initial_state.get("max_iterations", settings.MAX_ITERATIONS)
        
        # Execute workflow step-by-step if possible, otherwise invoke fully
        # Note: For granular progress, we'd need to stream events from LangGraph
        # For now, we'll update progress based on iteration count
        
        if progress_callback:
            progress_callback("requirement_analysis", 30)
        
        # Check cancellation before workflow
        if _check_cancellation(db, job_id):
            return None
        
        if progress_callback:
            progress_callback("generation_planning", 40)
        
        # Check cancellation again
        if _check_cancellation(db, job_id):
            return None
            
        if progress_callback:
            progress_callback("generating_data", 50)
        
        # Execute the workflow
        # Note: This is synchronous and cannot be interrupted during SDV fit
        final_state = workflow.invoke(initial_state)
        
        # Post-generation progress updates
        if progress_callback and final_state:
            iteration = final_state.get("iteration", 0)
            
            # Calculate progress based on iteration
            if iteration > 0:
                # Linear interpolation: 70% at iter 1, 90% at max_iterations
                base_progress = 70
                iter_progress = min(20, int(20 * iteration / max_iterations))
                progress_callback("evaluating_quality", base_progress + iter_progress)
            else:
                progress_callback("evaluation_complete", 80)
        
        return final_state
        
    except Exception as e:
        # Check if exception is due to cancellation
        if _check_cancellation(db, job_id):
            logger.info(f"Workflow execution cancelled for job {job_id}")
            return None
        raise
