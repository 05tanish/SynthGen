import os
import shutil
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.job import Job
from app.models.dataset import Dataset
from app.graph.workflow import build_workflow
from app.graph.state import GraphState
from app.core.logging import logger
from app.core.config import settings


def _update_job(db: Session, job: Job, **kwargs):
    """Helper to update job fields and commit, including updated_at."""
    for key, value in kwargs.items():
        setattr(job, key, value)
    job.updated_at = datetime.now(timezone.utc)
    db.commit()


def run_generation_job(job_id: int):
    logger.info(f"Starting background job: {job_id}")
    db: Session = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found.")
            return

        dataset = db.query(Dataset).filter(Dataset.id == job.dataset_id).first()
        if not dataset:
            _update_job(db, job, status="failed", error_message="Dataset not found.")
            return

        _update_job(db, job, status="running", current_step="loading_data")

        # 1. Resolve the absolute path to the source file
        source_path = os.path.abspath(dataset.source_filename)
        if not os.path.exists(source_path):
            _update_job(db, job, status="failed", error_message=f"Source file not found: {source_path}")
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
            synth_tmp_path = final_state.get("best_synthetic_data_path")
            report = final_state.get("best_evaluation_report")
            
            # Since we are returning the best, we mark it as successful in the DB 
            # so the user can download it, but the report will show it didn't pass strict thresholds.
            is_success = True

        if is_success and synth_tmp_path:
            # Combine original + synthetic data into one file
            storage_dir = os.path.abspath(
                os.path.join(settings.FILE_STORAGE_PATH, "synthetic")
            )
            os.makedirs(storage_dir, exist_ok=True)

            import uuid
            import pandas as pd

            real_df = pd.read_csv(source_path)
            synth_df = pd.read_csv(synth_tmp_path)

            # Tag each row so the consumer knows its origin
            real_df["is_synthetic"] = False
            synth_df["is_synthetic"] = True

            # Concatenate real + synthetic, reset index
            combined_df = pd.concat([real_df, synth_df], ignore_index=True)

            filename = f"combined_{dataset.id}_{uuid.uuid4().hex[:8]}.csv"
            final_path = os.path.join(storage_dir, filename)
            combined_df.to_csv(final_path, index=False)

            # Clean up temp synthetic file
            if os.path.exists(synth_tmp_path):
                os.remove(synth_tmp_path)

            logger.info(
                f"Saved combined dataset: {len(real_df)} real + {len(synth_df)} synthetic "
                f"= {len(combined_df)} total rows → {final_path}"
            )

            _update_job(
                db, job,
                status="completed",
                current_step="finished",
                synthetic_file_path=final_path,
                evaluation_report_json=report,
            )
        else:
            _update_job(
                db, job,
                status="failed",
                current_step="failed",
                error_message=final_state.get("status_message", "Workflow failed to produce valid data."),
                evaluation_report_json=report,
            )

        logger.info(f"Job {job_id} finished with status: {job.status}")

    except Exception as e:
        logger.error(f"Job {job_id} failed with exception: {str(e)}", exc_info=True)
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                _update_job(db, job, status="failed", error_message=str(e))
        except Exception as inner_e:
            logger.error(f"Failed to update job status after error: {inner_e}")
    finally:
        db.close()
