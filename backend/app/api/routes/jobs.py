from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.job import Job, JobStatus
from app.models.user import User
from app.api.deps import get_current_user
import os
import httpx

router = APIRouter()

@router.get("/{job_id}")
def get_job_status(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # progress_percent column temporarily removed for backward compatibility
    # Will return 0 until database migration is run
    progress = 0
        
    return {
        "id": job.id,
        "dataset_id": job.dataset_id,
        "status": job.status.value.lower() if hasattr(job.status, 'value') else str(job.status).lower(),
        "current_step": job.current_step,
        "progress_percent": progress,
        "error_message": job.error_message,
        "evaluation_report": job.evaluation_report_json,
        "created_at": job.created_at,
        "updated_at": job.updated_at
    }

@router.get("/{job_id}/download")
async def download_synthetic_data(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.status != JobStatus.COMPLETED or not job.synthetic_file_path:
        raise HTTPException(status_code=400, detail="Data is not ready or failed to generate")
    
    # Use a friendly download filename
    from app.models.dataset import Dataset
    dataset = db.query(Dataset).filter(Dataset.id == job.dataset_id).first()
    friendly_name = (dataset.name or "dataset").replace(" ", "_")[:40] if dataset else "dataset"
    from datetime import date
    download_name = f"{friendly_name}_{date.today().isoformat()}.csv"
    
    # Check if synthetic_file_path is a URL (Cloudinary) or local path
    if job.synthetic_file_path.startswith("http://") or job.synthetic_file_path.startswith("https://"):
        # It's a Cloudinary URL - fetch and stream it
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(job.synthetic_file_path, timeout=30.0)
                response.raise_for_status()
                
                # Stream the content
                async def stream_content():
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        yield chunk
                
                return StreamingResponse(
                    stream_content(),
                    media_type='text/csv',
                    headers={
                        'Content-Disposition': f'attachment; filename="{download_name}"'
                    }
                )
            except httpx.HTTPError as e:
                raise HTTPException(status_code=500, detail="Failed to download file. Please try again later.")
    else:
        # It's a local file path (legacy support)
        if not os.path.exists(job.synthetic_file_path):
            raise HTTPException(status_code=404, detail="Generated file is not available. Please generate again.")
        
        return FileResponse(
            path=job.synthetic_file_path,
            filename=download_name,
            media_type='text/csv'
        )


@router.get("/by-dataset/{dataset_id}")
def get_job_by_dataset(dataset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get the latest job for a given dataset. Used by History and Dataset detail pages."""
    from sqlalchemy import desc
    job = (
        db.query(Job)
        .filter(Job.dataset_id == dataset_id, Job.user_id == current_user.id)
        .order_by(desc(Job.created_at))
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Generation job not found for this dataset")
    return {
        "id": job.id,
        "dataset_id": job.dataset_id,
        "status": job.status.value.lower() if hasattr(job.status, 'value') else str(job.status).lower(),
        "current_step": job.current_step,
        "error_message": job.error_message,
        "evaluation_report": job.evaluation_report_json,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


@router.post("/{job_id}/cancel")
def cancel_job(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Cancel a running or pending generation job.
    The job status will be set to CANCELLED, and the worker will detect this and stop processing.
    """
    from app.core.logging import logger
    
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Can only cancel pending or running jobs
    if job.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status '{job.status}'. Only pending or running jobs can be cancelled."
        )
    
    # Update job status to cancelled
    job.status = JobStatus.CANCELLED
    job.current_step = "cancelled_by_user"
    job.error_message = "Cancelled by user"
    from datetime import datetime, timezone
    job.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(job)
    
    logger.info(f"Job {job_id} cancelled by user {current_user.id}")
    
    return {
        "status": "cancelled",
        "message": "Job cancellation requested. The job will stop processing.",
        "job_id": job.id
    }
