"""
graph_worker.py — generation job executor

Runs in a daemon thread started by main.py (run_worker_thread).
All DB writes use fresh sessions to avoid Neon idle-connection drops.
"""
import os
import time
import tempfile
import concurrent.futures
from datetime import datetime, timezone

from app.db.database import SessionLocal
from app.models.job import Job, JobStatus
from app.models.dataset import Dataset
from app.models.user import User  # noqa: F401 — needed for FK resolution
from app.graph.workflow import build_workflow
from app.graph.state import GraphState
from app.core.logging import logger
from app.core.config import settings
from app.core import storage as cloud_storage

# Hard cap on entire workflow execution (LLM + fit + evaluate)
WORKFLOW_TIMEOUT_SECONDS = 900  # 15 minutes


# ─────────────────────────────────────────────────────────────────────────────
# DB helpers — always open a fresh session, never reuse long-lived ones
# ─────────────────────────────────────────────────────────────────────────────

def _db_update_job_status(job_id: int, **kwargs) -> bool:
    """
    Write job fields using a brand-new DB session.
    Returns True on success, False on failure. Never raises.
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"[DB] Job {job_id} not found when updating {list(kwargs.keys())}")
            return False
        for key, value in kwargs.items():
            if key == 'progress_percent':
                continue  # column not in schema yet
            setattr(job, key, value)
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"[DB] Job {job_id} updated: {list(kwargs.keys())}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"[DB] Failed to update job {job_id} ({list(kwargs.keys())}): {e}", exc_info=True)
        return False
    finally:
        db.close()


def _cleanup_temp_file(file_path: str):
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"[CLEANUP] Could not delete {file_path}: {e}")


def _reset_stale_running_jobs():
    """Reset jobs left RUNNING by a previous crash/deploy."""
    db = SessionLocal()
    try:
        stale = db.query(Job).filter(Job.status == JobStatus.RUNNING).all()
        if stale:
            ids = [j.id for j in stale]
            logger.warning(f"[STARTUP] Resetting {len(stale)} stale RUNNING jobs to FAILED: {ids}")
            for job in stale:
                job.status = JobStatus.FAILED
                job.current_step = "failed"
                job.error_message = "Interrupted by server restart — please retry."
                job.updated_at = datetime.now(timezone.utc)
            db.commit()
        else:
            logger.info("[STARTUP] No stale RUNNING jobs found.")

        pending = db.query(Job).filter(Job.status == JobStatus.PENDING).all()
        if pending:
            logger.info(f"[STARTUP] {len(pending)} PENDING jobs waiting: {[j.id for j in pending]}")
    except Exception as e:
        db.rollback()
        logger.error(f"[STARTUP] Failed to reset stale jobs: {e}", exc_info=True)
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Main job runner
# ─────────────────────────────────────────────────────────────────────────────

def run_generation_job(job_id: int):
    logger.info("=" * 72)
    logger.info(f"🚀 JOB {job_id} — STARTING")
    logger.info("=" * 72)

    local_source_path = None
    synth_tmp_path = None

    # ── 1. Load job + dataset, mark RUNNING ──────────────────────────────────
    try:
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).with_for_update().first()
            if not job:
                logger.error(f"[JOB {job_id}] Not found in DB.")
                return
            if job.status == JobStatus.RUNNING:
                logger.warning(f"[JOB {job_id}] Already RUNNING — skipping duplicate.")
                return
            if job.status == JobStatus.CANCELLED:
                logger.info(f"[JOB {job_id}] Cancelled before start.")
                return
            if job.status not in (JobStatus.PENDING,):
                logger.warning(f"[JOB {job_id}] Unexpected status {job.status} — skipping.")
                return

            dataset = db.query(Dataset).filter(Dataset.id == job.dataset_id).first()
            if not dataset:
                db.rollback()
                db.close()
                _db_update_job_status(job_id, status=JobStatus.FAILED,
                                      error_message="Dataset not found.")
                return

            # Snapshot all fields we need — then close session immediately
            ds = {
                "id": dataset.id,
                "name": dataset.name,
                "row_count": dataset.row_count,
                "source_filename": dataset.source_filename,
                "prompt": dataset.prompt,
                "profile_json": dataset.profile_json,
                "relationships_json": dataset.relationships_json or {},
            }

            job.status = JobStatus.RUNNING
            job.current_step = "loading_data"
            job.updated_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"[JOB {job_id}] Marked RUNNING — dataset '{ds['name']}' ({ds['row_count']} rows)")
        finally:
            db.close()

    except Exception as e:
        logger.error(f"[JOB {job_id}] Failed during DB load: {e}", exc_info=True)
        _db_update_job_status(job_id, status=JobStatus.FAILED,
                              error_message=f"Startup error: {str(e)[:200]}")
        return

    # ── 2. Download source file ───────────────────────────────────────────────
    try:
        source_ref = ds["source_filename"]
        logger.info(f"[JOB {job_id}] Source ref: {source_ref[:80] if source_ref else 'None'}")

        if source_ref and source_ref.startswith("http"):
            t = time.time()
            ext = os.path.splitext(source_ref.split("?")[0])[-1] or ".csv"
            local_source_path = cloud_storage.download_to_temp(source_ref, suffix=ext)
            source_path = local_source_path
            logger.info(f"[JOB {job_id}] Downloaded source in {time.time()-t:.1f}s → {source_path}")
        else:
            source_path = os.path.abspath(source_ref) if source_ref else None
            logger.info(f"[JOB {job_id}] Using local source: {source_path}")

        if not source_path or not os.path.exists(source_path):
            logger.error(f"[JOB {job_id}] Source file missing: {source_path}")
            _db_update_job_status(job_id, status=JobStatus.FAILED,
                                  error_message="Source file not found.")
            return

    except Exception as e:
        logger.error(f"[JOB {job_id}] File download failed: {e}", exc_info=True)
        _db_update_job_status(job_id, status=JobStatus.FAILED,
                              error_message=f"Download error: {str(e)[:200]}")
        return

    # ── 3. Run LangGraph workflow ─────────────────────────────────────────────
    try:
        _db_update_job_status(job_id, current_step="running_graph")

        initial_state: GraphState = {
            "dataset_id": ds["id"],
            "requirement": ds["prompt"],
            "requirement_analysis": None,
            "real_data_path": source_path,
            "schema_json": ds["profile_json"],
            "profile_json": ds["profile_json"],
            "relationships_json": ds["relationships_json"],
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

        logger.info(f"[JOB {job_id}] Building workflow (MAX_ITERATIONS={settings.MAX_ITERATIONS})...")
        workflow = build_workflow()

        logger.info(f"[JOB {job_id}] Invoking workflow (timeout={WORKFLOW_TIMEOUT_SECONDS}s)...")
        t_wf = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(workflow.invoke, initial_state)
            try:
                final_state = future.result(timeout=WORKFLOW_TIMEOUT_SECONDS)
            except concurrent.futures.TimeoutError:
                raise RuntimeError(
                    f"Workflow timed out after {WORKFLOW_TIMEOUT_SECONDS}s."
                )
        logger.info(f"[JOB {job_id}] Workflow done in {time.time()-t_wf:.1f}s. "
                    f"is_successful={final_state.get('is_successful')} "
                    f"synth_path={final_state.get('synthetic_data_path')} "
                    f"best_path={final_state.get('best_synthetic_data_path')}")

    except Exception as e:
        logger.error(f"[JOB {job_id}] Workflow FAILED: {e}", exc_info=True)
        _cleanup_temp_file(local_source_path)
        _db_update_job_status(job_id, status=JobStatus.FAILED,
                              current_step="failed",
                              error_message=str(e)[:500])
        return

    # ── 4. Process results and upload ────────────────────────────────────────
    try:
        is_success = final_state.get("is_successful", False)
        synth_tmp_path = final_state.get("synthetic_data_path")
        report = final_state.get("evaluation_report")

        # Prefer best result if threshold wasn't met but data exists
        if not is_success and final_state.get("best_synthetic_data_path"):
            logger.info(f"[JOB {job_id}] Using best result (threshold not met).")
            _cleanup_temp_file(synth_tmp_path)
            synth_tmp_path = final_state.get("best_synthetic_data_path")
            report = final_state.get("best_evaluation_report")
            is_success = True

        # If any data exists at all, treat as success — never discard generated data
        if not is_success and synth_tmp_path and os.path.exists(synth_tmp_path):
            logger.warning(f"[JOB {job_id}] is_successful=False but data exists — treating as success.")
            is_success = True

        logger.info(f"[JOB {job_id}] Final: is_success={is_success} path={synth_tmp_path}")

        if is_success and synth_tmp_path and os.path.exists(synth_tmp_path):
            import uuid
            import pandas as pd

            # Update step so the frontend's "Finalizing dataset" step becomes active
            _db_update_job_status(job_id, current_step="saving_results")

            # 4a — read
            logger.info(f"[JOB {job_id}] [4a] Reading CSV...")
            t = time.time()
            synth_df = pd.read_csv(synth_tmp_path)
            logger.info(f"[JOB {job_id}] [4a] {len(synth_df)} rows read in {time.time()-t:.1f}s")

            # 4b — adjust row count
            logger.info(f"[JOB {job_id}] [4b] Adjusting to {ds['row_count']} rows...")
            t = time.time()
            requested_rows = min(ds["row_count"] or len(synth_df), 30000)
            if len(synth_df) > requested_rows:
                synth_df = synth_df.sample(n=requested_rows, random_state=42).reset_index(drop=True)
            elif len(synth_df) < requested_rows:
                shortfall = requested_rows - len(synth_df)
                extra = synth_df.sample(n=shortfall, replace=True, random_state=99).reset_index(drop=True)
                synth_df = pd.concat([synth_df, extra], ignore_index=True)
            synth_df = synth_df.drop_duplicates()
            if len(synth_df) < requested_rows:
                extra = synth_df.sample(n=requested_rows - len(synth_df), replace=True, random_state=77).reset_index(drop=True)
                synth_df = pd.concat([synth_df, extra], ignore_index=True)
            synth_df = synth_df.head(requested_rows).reset_index(drop=True)
            logger.info(f"[JOB {job_id}] [4b] Final {len(synth_df)} rows in {time.time()-t:.1f}s")

            # 4c — write temp CSV
            logger.info(f"[JOB {job_id}] [4c] Writing temp CSV...")
            t = time.time()
            filename = f"synthetic_{ds['id']}_{uuid.uuid4().hex[:8]}.csv"
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as f:
                synth_df.to_csv(f, index=False)
                final_tmp = f.name
            size_kb = os.path.getsize(final_tmp) / 1024
            logger.info(f"[JOB {job_id}] [4c] Written {size_kb:.0f} KB in {time.time()-t:.1f}s")

            # 4d — upload to Cloudinary
            logger.info(f"[JOB {job_id}] [4d] Uploading {filename} ({size_kb:.0f} KB) to Cloudinary...")
            t = time.time()
            cloudinary_url = None
            try:
                with open(final_tmp, "rb") as f:
                    csv_bytes = f.read()
                # We're already in a background thread, so call directly (no nested executor)
                cloudinary_url = cloud_storage.upload_file(
                    csv_bytes,
                    f"synthetic/{filename.replace('.csv', '')}",
                    "synthetix",
                )
                logger.info(f"[JOB {job_id}] [4d] Uploaded in {time.time()-t:.1f}s → {cloudinary_url}")
            except Exception as upload_err:
                logger.error(f"[JOB {job_id}] [4d] Upload FAILED in {time.time()-t:.1f}s: {upload_err}", exc_info=True)
            finally:
                _cleanup_temp_file(final_tmp)

            _cleanup_temp_file(synth_tmp_path)
            synth_tmp_path = None

            # 4e — write COMPLETED to DB
            if cloudinary_url:
                logger.info(f"[JOB {job_id}] [4e] Writing COMPLETED to DB...")
                t = time.time()
                ok = _db_update_job_status(
                    job_id,
                    status=JobStatus.COMPLETED,
                    current_step="finished",
                    synthetic_file_path=cloudinary_url,
                )
                logger.info(f"[JOB {job_id}] [4e] DB write {'OK' if ok else 'FAILED'} in {time.time()-t:.1f}s")
                logger.info("=" * 72)
                logger.info(f"✅ JOB {job_id} COMPLETED SUCCESSFULLY")
                logger.info("=" * 72)
                # Write report separately (large JSON — non-critical)
                if report:
                    _db_update_job_status(job_id, evaluation_report_json=report)
            else:
                logger.error(f"[JOB {job_id}] [4e] Cloudinary upload failed — marking FAILED")
                _db_update_job_status(job_id, status=JobStatus.FAILED,
                                      current_step="failed",
                                      error_message="File upload failed. Please retry.")

        else:
            _cleanup_temp_file(synth_tmp_path)
            error_msg = final_state.get("status_message", "No synthetic data was produced.")
            logger.error(f"[JOB {job_id}] No data produced. Reason: {error_msg}")
            _db_update_job_status(job_id, status=JobStatus.FAILED,
                                  current_step="failed", error_message=error_msg)
            if report:
                _db_update_job_status(job_id, evaluation_report_json=report)

    except Exception as e:
        logger.error(f"[JOB {job_id}] Result processing CRASHED: {e}", exc_info=True)
        _cleanup_temp_file(synth_tmp_path)
        _db_update_job_status(job_id, status=JobStatus.FAILED,
                              current_step="failed",
                              error_message=f"Internal error: {str(e)[:300]}")
    finally:
        _cleanup_temp_file(local_source_path)
