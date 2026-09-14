from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.dataset import Dataset
from app.models.job import Job

router = APIRouter()

@router.get("/")
def get_usage(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dataset_count = db.query(func.count(Dataset.id)).filter(Dataset.user_id == current_user.id).scalar()
    job_count = db.query(func.count(Job.id)).filter(Job.user_id == current_user.id).scalar()
    total_rows = db.query(func.sum(Dataset.row_count)).filter(Dataset.user_id == current_user.id).scalar() or 0
    
    return {
        "datasets_created": dataset_count,
        "api_requests": job_count,
        "rows_generated": total_rows,
        "storage_used_mb": dataset_count * 2.5 # Mock storage
    }
