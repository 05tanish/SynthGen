from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.job import Job
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/{job_id}")
def get_job_status(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return {
        "id": job.id,
        "dataset_id": job.dataset_id,
        "status": job.status,
        "current_step": job.current_step,
        "error_message": job.error_message,
        "evaluation_report": job.evaluation_report_json,
        "created_at": job.created_at,
        "updated_at": job.updated_at
    }

from fastapi.responses import FileResponse
import os

@router.get("/{job_id}/download")
def download_synthetic_data(job_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.status != "completed" or not job.synthetic_file_path:
        raise HTTPException(status_code=400, detail="Data is not ready or failed to generate")
        
    if not os.path.exists(job.synthetic_file_path):
        raise HTTPException(status_code=404, detail="Synthetic file not found on disk")
        
    filename = os.path.basename(job.synthetic_file_path)
    return FileResponse(
        path=job.synthetic_file_path, 
        filename=filename,
        media_type='text/csv'
    )
