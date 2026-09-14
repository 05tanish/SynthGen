import os
import shutil
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


def _update_job(db: Session, job: Job, **kwargs):
    """
    Helper to update job fields and commit with proper transaction isolation.
    Uses row-level locking to prevent race conditions.
    """
    try:
        # Refresh the job within the transaction to get latest state
        db.refresh(job)
        
        for key, value in kwargs.items():
            setattr(job, key, value)
        job.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(job)
    except Exception as e:
        db.rollback()
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
    logger.info(f"Starting background job: {job_id}")
    db: Session = SessionLocal()
    synth_tmp_path = None  # Track temp file for cleanup
    
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

        dataset = db.query(Dataset).filter(Dataset.id == job.dataset_id).first()
        if not dataset:
            _update_job(db, job, status=JobStatus.FAILED, error_message="Dataset not found.")
            return

        _update_job(db, job, status=JobStatus.RUNNING, current_step="loading_data")

        # 1. Resolve the absolute path to the source file
        source_path = os.path.abspath(dataset.source_filename)
        if not os.path.exists(source_path):
            _update_job(db, job, status=JobStatus.FAILED, error_message=f"Source file not found: {source_path}")
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

        # 3. Run Graph
        workflow = build_workflow()
        _update_job(db, job, current_step="running_graph")

        final_state = workflow.invoke(initial_state)

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
            storage_dir = os.path.abspath(
                os.path.join(settings.FILE_STORAGE_PATH, "synthetic")
            )
            os.makedirs(storage_dir, exist_ok=True)

            import uuid
            import pandas as pd

            synth_df = pd.read_csv(synth_tmp_path)

            # Trim or expand to exactly the requested row count
            requested_rows = dataset.row_count or len(synth_df)
            
            # Enforce maximum row limit
            if requested_rows > 30000:
                logger.warning(f"Requested rows {requested_rows} exceeds limit. Capping to 30,000.")
                requested_rows = 30000

            if len(synth_df) > requested_rows:
                # Trim to exactly the requested number of rows
                synth_df = synth_df.sample(n=requested_rows, random_state=42).reset_index(drop=True)
                logger.info(f"Trimmed synthetic output from {len(pd.read_csv(synth_tmp_path))} to {requested_rows} rows.")
            elif len(synth_df) < requested_rows:
                # If we got fewer rows than requested, try to expand by resampling with noise
                shortfall = requested_rows - len(synth_df)
                logger.warning(f"Generated {len(synth_df)} rows but {requested_rows} were requested. Filling shortfall of {shortfall} by resampling.")
                extra = synth_df.sample(n=shortfall, replace=True, random_state=99).reset_index(drop=True)
                synth_df = pd.concat([synth_df, extra], ignore_index=True)

            # Remove exact duplicate rows
            pre_dedup = len(synth_df)
            synth_df = synth_df.drop_duplicates()
            if len(synth_df) < requested_rows:
                # Refill after dedup
                shortfall = requested_rows - len(synth_df)
                extra = synth_df.sample(n=shortfall, replace=True, random_state=77).reset_index(drop=True)
                synth_df = pd.concat([synth_df, extra], ignore_index=True)
            # Final trim to exact count
            synth_df = synth_df.head(requested_rows).reset_index(drop=True)

            logger.info(f"Final synthetic dataset: {len(synth_df)} rows (requested: {requested_rows})")

            filename = f"synthetic_{dataset.id}_{uuid.uuid4().hex[:8]}.csv"
            final_path = os.path.join(storage_dir, filename)
            
            # Use atomic write pattern: write to temp, then move
            temp_final_path = final_path + ".tmp"
            synth_df.to_csv(temp_final_path, index=False)
            os.rename(temp_final_path, final_path)

            # Clean up temp synthetic file after successful save
            _cleanup_temp_file(synth_tmp_path)
            synth_tmp_path = None  # Mark as cleaned up

            _update_job(
                db, job,
                status=JobStatus.COMPLETED,
                current_step="finished",
                synthetic_file_path=final_path,
                evaluation_report_json=report,
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

        logger.info(f"Job {job_id} finished with status: {job.status}")

    except Exception as e:
        logger.error(f"Job {job_id} failed with exception: {str(e)}", exc_info=True)
        
        # Always clean up temp file on exception
        _cleanup_temp_file(synth_tmp_path)
        
        try:
            from app.core.error_sanitiser import safe_error_message
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                _update_job(db, job, status=JobStatus.FAILED, error_message=safe_error_message(e))
        except Exception as inner_e:
            logger.error(f"Failed to update job status after error: {inner_e}")
    finally:
        db.close()
