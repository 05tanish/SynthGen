import os
import tempfile
import concurrent.futures
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.job import Job, JobStatus
from app.models.dataset import Dataset
from app.models.user import User  # Import to resolve foreign key FK
from app.graph.workflow import build_workflow
from app.graph.state import GraphState
from app.core.logging import logger
from app.core.config import settings
from app.core import storage as cloud_storage

# Maximum time the entire workflow (LLM + fit + evaluate) is allowed to run
WORKFLOW_TIMEOUT_SECONDS = 900  # 15 minutes hard cap


def _db_update_job_status(job_id: int, **kwargs):
    """
    Open a FRESH DB session and update job fields.
    Always uses a new connection — never reuses a long-lived session —
    so Neon's idle-connection drops never cause a hang here.
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"_db_update_job_status: job {job_id} not found")
            return
        for key, value in kwargs.items():
            if key == 'progress_percent':
                continue  # column not in schema yet
            setattr(job, key, value)
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.debug(f"Job {job_id} updated: {list(kwargs.keys())}")
    except Exception as e:
        db.rollback()
        logger.error(f"_db_update_job_status failed for job {job_id}: {e}", exc_info=True)
        raise
    finally:
        db.close()


def _cleanup_temp_file(file_path: str):
    """Safely clean up a temporary file."""
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up temp file {file_path}: {e}")


def _reset_stale_running_jobs():
    """
    On worker startup, reset any jobs stuck in RUNNING from a previous crash.
    These will never complete on their own — mark them FAILED so users can retry.
    """
    db = SessionLocal()
    try:
        stale = db.query(Job).filter(Job.status == JobStatus.RUNNING).all()
        if stale:
            logger.warning(f"Found {len(stale)} stale RUNNING jobs from previous crash — marking FAILED")
            for job in stale:
                job.status = JobStatus.FAILED
                job.current_step = "failed"
                job.error_message = "Job interrupted by server restart. Please retry."
                job.updated_at = datetime.now(timezone.utc)
            db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to reset stale jobs: {e}")
    finally:
        db.close()


def run_generation_job(job_id: int):
    """
    Main entry point for background job execution.
    Runs in the polling worker thread started by main.py.
    """
    logger.info("=" * 80)
    logger.info(f"🚀 STARTING GENERATION JOB {job_id}")
    logger.info("=" * 80)

    synth_tmp_path = None
    local_source_path = None

    # ── 1. Load job and dataset using a short-lived session ──────────────────
    try:
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).with_for_update().first()
            if not job:
                logger.error(f"Job {job_id} not found.")
                return
            if job.status == JobStatus.RUNNING:
                logger.warning(f"Job {job_id} already RUNNING — skipping duplicate.")
                return
            if job.status == JobStatus.CANCELLED:
                logger.info(f"Job {job_id} cancelled before start.")
                return

            dataset = db.query(Dataset).filter(Dataset.id == job.dataset_id).first()
            if not dataset:
                db.rollback()
                db.close()
                _db_update_job_status(job_id, status=JobStatus.FAILED, error_message="Dataset not found.")
                return

            # Snapshot everything we need — then close the session
            dataset_id = dataset.id
            dataset_name = dataset.name
            dataset_row_count = dataset.row_count
            dataset_column_count = dataset.column_count
            dataset_source_filename = dataset.source_filename
            dataset_prompt = dataset.prompt
            dataset_profile_json = dataset.profile_json
            dataset_relationships_json = dataset.relationships_json or {}

            # Mark RUNNING while session is fresh
            job.status = JobStatus.RUNNING
            job.current_step = "loading_data"
            job.updated_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Job {job_id} failed during initial DB load: {e}", exc_info=True)
        try:
            _db_update_job_status(job_id, status=JobStatus.FAILED, error_message=f"Startup error: {str(e)[:200]}")
        except Exception:
            pass
        return

    # ── 2. Download source file ──────────────────────────────────────────────
    try:
        source_ref = dataset_source_filename
        if source_ref and source_ref.startswith("http"):
            logger.info(f"Downloading source from Cloudinary: {source_ref[:60]}...")
            ext = os.path.splitext(source_ref.split("?")[0])[-1] or ".csv"
            local_source_path = cloud_storage.download_to_temp(source_ref, suffix=ext)
            source_path = local_source_path
        else:
            source_path = os.path.abspath(source_ref) if source_ref else None

        if not source_path or not os.path.exists(source_path):
            _db_update_job_status(job_id, status=JobStatus.FAILED, error_message="Source file not found.")
            return
    except Exception as e:
        logger.error(f"Job {job_id} failed during file download: {e}", exc_info=True)
        _db_update_job_status(job_id, status=JobStatus.FAILED, error_message=f"Failed to load source file: {str(e)[:200]}")
        return

    # ── 3. Build and run the LangGraph workflow ──────────────────────────────
    try:
        _db_update_job_status(job_id, current_step="running_graph")

        initial_state: GraphState = {
            "dataset_id": dataset_id,
            "requirement": dataset_prompt,
            "requirement_analysis": None,
            "real_data_path": source_path,
            "schema_json": dataset_profile_json,
            "profile_json": dataset_profile_json,
            "relationships_json": dataset_relationships_json,
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

        logger.info(f"Building workflow (max_iterations={settings.MAX_ITERATIONS})...")
        workflow = build_workflow()

        # Run workflow in a thread with a hard global timeout so the worker
        # thread is never blocked forever if an LLM call or fit() hangs.
        logger.info(f"🔄 Invoking workflow (timeout={WORKFLOW_TIMEOUT_SECONDS}s)...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(workflow.invoke, initial_state)
            try:
                final_state = future.result(timeout=WORKFLOW_TIMEOUT_SECONDS)
            except concurrent.futures.TimeoutError:
                raise RuntimeError(
                    f"Workflow exceeded {WORKFLOW_TIMEOUT_SECONDS}s timeout. "
                    "Generation cancelled to prevent server resource exhaustion."
                )
        logger.info("✓ Workflow completed")

    except Exception as e:
        logger.error(f"Job {job_id} workflow failed: {e}", exc_info=True)
        _cleanup_temp_file(local_source_path)
        try:
            from app.core.error_sanitiser import safe_error_message
            _db_update_job_status(job_id, status=JobStatus.FAILED,
                                  current_step="failed",
                                  error_message=safe_error_message(e))
        except Exception as inner_e:
            logger.error(f"Could not mark job {job_id} FAILED: {inner_e}")
        return

    # ── 4. Process and upload results ────────────────────────────────────────
    try:
        is_success = final_state.get("is_successful")
        synth_tmp_path = final_state.get("synthetic_data_path")
        report = final_state.get("evaluation_report")

        # Use best result if threshold wasn't met
        if not is_success and final_state.get("best_synthetic_data_path"):
            logger.info("Using best result (threshold not met).")
            _cleanup_temp_file(synth_tmp_path)
            synth_tmp_path = final_state.get("best_synthetic_data_path")
            report = final_state.get("best_evaluation_report")
            is_success = True

        if is_success and synth_tmp_path and os.path.exists(synth_tmp_path):
            import uuid
            import pandas as pd

            synth_df = pd.read_csv(synth_tmp_path)
            logger.info(f"Generated {len(synth_df)} rows")

            requested_rows = min(dataset_row_count or len(synth_df), 30000)
            if len(synth_df) > requested_rows:
                synth_df = synth_df.sample(n=requested_rows, random_state=42).reset_index(drop=True)
            elif len(synth_df) < requested_rows:
                shortfall = requested_rows - len(synth_df)
                extra = synth_df.sample(n=shortfall, replace=True, random_state=99).reset_index(drop=True)
                synth_df = pd.concat([synth_df, extra], ignore_index=True)

            synth_df = synth_df.drop_duplicates()
            if len(synth_df) < requested_rows:
                shortfall = requested_rows - len(synth_df)
                extra = synth_df.sample(n=shortfall, replace=True, random_state=77).reset_index(drop=True)
                synth_df = pd.concat([synth_df, extra], ignore_index=True)
            synth_df = synth_df.head(requested_rows).reset_index(drop=True)

            filename = f"synthetic_{dataset_id}_{uuid.uuid4().hex[:8]}.csv"
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as f:
                synth_df.to_csv(f, index=False)
                final_tmp = f.name

            logger.info(f"☁️  Uploading {filename} to Cloudinary...")
            try:
                with open(final_tmp, "rb") as f:
                    csv_bytes = f.read()
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    fut = ex.submit(cloud_storage.upload_file, csv_bytes,
                                    f"synthetic/{filename.replace('.csv', '')}", "synthetix")
                    cloudinary_url = fut.result(timeout=120)
                logger.info(f"✓ Uploaded: {cloudinary_url[:60]}...")
            finally:
                _cleanup_temp_file(final_tmp)

            _cleanup_temp_file(synth_tmp_path)
            synth_tmp_path = None

            # Fresh session — never reuse a session that was open for minutes
            _db_update_job_status(
                job_id,
                status=JobStatus.COMPLETED,
                current_step="finished",
                synthetic_file_path=cloudinary_url,
                evaluation_report_json=report,
            )
            logger.info("=" * 80)
            logger.info(f"✅ JOB {job_id} COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)

        else:
            _cleanup_temp_file(synth_tmp_path)
            synth_tmp_path = None
            error_msg = final_state.get("status_message", "Workflow failed to produce valid data.")
            logger.error(f"Job {job_id} failed: {error_msg}")
            _db_update_job_status(
                job_id,
                status=JobStatus.FAILED,
                current_step="failed",
                error_message=error_msg,
                evaluation_report_json=report,
            )
            logger.info(f"❌ JOB {job_id} FAILED")

    except Exception as e:
        logger.error(f"Job {job_id} failed during result processing: {e}", exc_info=True)
        _cleanup_temp_file(synth_tmp_path)
        try:
            from app.core.error_sanitiser import safe_error_message
            _db_update_job_status(job_id, status=JobStatus.FAILED,
                                  current_step="failed",
                                  error_message=safe_error_message(e))
        except Exception as inner_e:
            logger.error(f"Could not mark job {job_id} FAILED after result error: {inner_e}")
    finally:
        _cleanup_temp_file(local_source_path)
