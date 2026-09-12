from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.concurrency import run_in_threadpool
from typing import Optional
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.dataset import Dataset
from app.models.job import Job
from app.schemas.dataset import DatasetResponse, DatasetCreate
from app.tools.data_loader import load_from_file
from app.tools.dataset_profiler import profile_dataset
from app.tools.relationship_analyzer import analyze_relationships
from app.core.config import settings
from app.workers.graph_worker import run_generation_job
import shutil
import os
import uuid
from pydantic import BaseModel
from app.agents.seed_generator_agent import SeedGeneratorAgent

router = APIRouter()

os.makedirs(os.path.join(settings.FILE_STORAGE_PATH, "uploads"), exist_ok=True)


@router.post("/upload", response_model=DatasetResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    # Validate extension
    allowed_extensions = [".csv", ".xlsx", ".xls", ".json", ".parquet"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file extension: {ext}")

    # Save uploaded file
    file_id = str(uuid.uuid4())
    upload_dir = os.path.abspath(os.path.join(settings.FILE_STORAGE_PATH, "uploads"))
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{file_id}{ext}")

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Check size
        if os.path.getsize(file_path) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            os.remove(file_path)
            raise HTTPException(status_code=413, detail="File too large")

        # Run heavy CPU-bound profiling in a thread pool to avoid blocking the event loop
        loaded_data = await run_in_threadpool(load_from_file, file_path)
        profile = await run_in_threadpool(profile_dataset, loaded_data.dataframe)
        relationships = await run_in_threadpool(analyze_relationships, loaded_data.dataframe)

        db_dataset = Dataset(
            name=file.filename,
            source_type="upload",
            source_filename=file_path,
            row_count=loaded_data.row_count,
            column_count=loaded_data.column_count,
            prompt=prompt,
            profile_json=profile,
            relationships_json=relationships,
        )
        db.add(db_dataset)
        db.commit()
        db.refresh(db_dataset)

        return db_dataset

    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))


class PromptGenerationRequest(BaseModel):
    prompt: str


@router.post("/generate-from-prompt")
async def generate_from_prompt(
    request: PromptGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    try:
        # 1. Ask LLM to generate a seed CSV
        agent = SeedGeneratorAgent()
        seed_csv_str = await run_in_threadpool(agent.generate_seed_csv, request.prompt)
        
        # 2. Save it to a temporary file in uploads
        file_id = str(uuid.uuid4())
        upload_dir = os.path.abspath(os.path.join(settings.FILE_STORAGE_PATH, "uploads"))
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{file_id}.csv")
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(seed_csv_str)
            
        # 3. Process it just like a normal upload
        loaded_data = await run_in_threadpool(load_from_file, file_path)
        
        if loaded_data.row_count == 0:
            raise HTTPException(
                status_code=400, 
                detail="The AI failed to generate a valid seed dataset (often caused by safety refusals or overly complex prompts). Please rephrase your prompt and try again."
            )
            
        profile = await run_in_threadpool(profile_dataset, loaded_data.dataframe)
        relationships = await run_in_threadpool(analyze_relationships, loaded_data.dataframe)
        
        # 4. Save to DB
        db_dataset = Dataset(
            name=f"Generated: {request.prompt[:20]}...",
            source_type="prompt",
            source_filename=file_path,
            row_count=loaded_data.row_count,
            column_count=loaded_data.column_count,
            prompt=request.prompt,
            profile_json=profile,
            relationships_json=relationships,
        )
        db.add(db_dataset)
        db.commit()
        db.refresh(db_dataset)
        
        # 5. Automatically enqueue the Generation Job to expand the seed dataset
        job = Job(dataset_id=db_dataset.id, status="pending", current_step="queued")
        db.add(job)
        db.commit()
        db.refresh(job)
        
        background_tasks.add_task(run_generation_job, job.id)
        
        return {"message": "Generation job started", "job_id": job.id, "dataset": db_dataset}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate seed data: {e}")


@router.get("/", response_model=list[DatasetResponse])
def get_datasets(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    datasets = db.query(Dataset).order_by(Dataset.created_at.desc()).offset(skip).limit(limit).all()
    return datasets


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.get("/{dataset_id}/profile")
def get_dataset_profile(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if not dataset.profile_json:
        raise HTTPException(status_code=404, detail="Profile not generated yet")
    return dataset.profile_json


@router.get("/{dataset_id}/relationships")
def get_dataset_relationships(dataset_id: int, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if not dataset.relationships_json:
        raise HTTPException(status_code=404, detail="Relationships not analyzed yet")
    return dataset.relationships_json


@router.post("/{dataset_id}/generate")
def generate_synthetic_data(
    dataset_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if not dataset.source_filename or not os.path.exists(os.path.abspath(dataset.source_filename)):
        raise HTTPException(
            status_code=422,
            detail="Source file is missing from disk. Please re-upload the dataset.",
        )

    # Create Job
    job = Job(dataset_id=dataset.id, status="pending", current_step="queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    # Enqueue background task
    background_tasks.add_task(run_generation_job, job.id)

    return {"message": "Generation job started", "job_id": job.id}
