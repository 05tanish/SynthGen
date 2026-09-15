from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.concurrency import run_in_threadpool
from typing import Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.db.database import get_db
from app.models.dataset import Dataset
from app.models.job import Job, JobStatus
from app.schemas.dataset import DatasetResponse, DatasetCreate
from app.tools.data_loader import load_from_file
from app.tools.dataset_profiler import profile_dataset
from app.tools.relationship_analyzer import analyze_relationships
from app.core.config import settings
from app.workers.graph_worker import run_generation_job
from app.core import storage as cloud_storage
import os
import uuid
import tempfile
from app.agents.seed_generator_agent import SeedGeneratorAgent
from app.api.deps import get_current_user
from app.models.user import User
from app.core.logging import logger

router = APIRouter()


@router.post("/upload", response_model=DatasetResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None, max_length=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate prompt length if provided
    if prompt and len(prompt) > 2000:
        raise HTTPException(status_code=400, detail="Prompt exceeds 2,000 character limit")
    
    # Validate extension
    allowed_extensions = [".csv", ".xlsx", ".xls", ".json", ".parquet"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file extension: {ext}")

    # Read file bytes into memory
    file_bytes = await file.read()

    # Check size before doing anything expensive
    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    # Write to a temp file so existing loaders (pandas/pyarrow) can read by path
    file_id = str(uuid.uuid4())
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        # Run heavy CPU-bound profiling in a thread pool to avoid blocking the event loop
        loaded_data = await run_in_threadpool(load_from_file, tmp_path)

        # Validate row count (must be between 8 and 30,000)
        if loaded_data.row_count < 8:
            raise HTTPException(
                status_code=400,
                detail=f"Dataset has only {loaded_data.row_count} rows. Minimum 8 rows required for reliable synthetic generation."
            )

        if loaded_data.row_count > 30000:
            raise HTTPException(
                status_code=400,
                detail=f"Dataset has {loaded_data.row_count} rows. Maximum 30,000 rows allowed."
            )

        # Validate column count (max 100 columns)
        if loaded_data.column_count > 100:
            raise HTTPException(
                status_code=400,
                detail=f"Dataset has {loaded_data.column_count} columns. Maximum 100 columns allowed."
            )

        profile = await run_in_threadpool(profile_dataset, loaded_data.dataframe)
        relationships = await run_in_threadpool(analyze_relationships, loaded_data.dataframe)

        # Truncate JSON data to fit within limits (agents will re-truncate as needed)
        from app.schemas.dataset import truncate_json_data
        profile = truncate_json_data(profile, 1000, "Profile")
        relationships = truncate_json_data(relationships, 1000, "Relationships")

        # Parse desired row count from prompt, or default to uploaded file's row count
        from app.tools.synthetic_generator import parse_row_count_from_prompt
        desired_row_count = parse_row_count_from_prompt(prompt) if prompt else None
        final_row_count = desired_row_count if desired_row_count else loaded_data.row_count
        if final_row_count > 30000:
            logger.warning(f"Requested row count {final_row_count} exceeds limit. Capping to 30,000.")
            final_row_count = 30000

        # Upload to Cloudinary — store the returned URL as source_filename
        cloudinary_url = await run_in_threadpool(
            cloud_storage.upload_file,
            file_bytes,
            f"uploads/{file_id}",
            "synthetix",
        )

        db_dataset = Dataset(
            name=file.filename,
            source_type="upload",
            source_filename=cloudinary_url,   # URL instead of local path
            row_count=final_row_count,
            column_count=loaded_data.column_count,
            prompt=prompt,
            profile_json=profile,
            relationships_json=relationships,
            user_id=current_user.id,
        )
        db.add(db_dataset)
        db.commit()
        db.refresh(db_dataset)
        return db_dataset

    except HTTPException:
        raise
    except Exception as e:
        from app.core.error_sanitiser import raise_safe_http_error
        raise_safe_http_error(e, status_code=500, context="upload_dataset")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


class PromptGenerationRequest(BaseModel):
    prompt: str = Field(max_length=2000, description="User prompt (max 2,000 chars)")
    row_count: int = Field(default=1000, ge=1, le=30000, description="Number of rows to generate (max 30,000)")
    format: str = "CSV"    # Output format (future use)


@router.post("/generate-from-prompt")
async def generate_from_prompt(
    request: PromptGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Validate request (Pydantic will auto-validate, but we add extra checks)
        if request.row_count > 30000:
            raise HTTPException(
                status_code=400,
                detail="Row count exceeds maximum limit of 30,000 rows"
            )
        
        # 1. Ask LLM to generate a seed CSV
        agent = SeedGeneratorAgent()
        seed_csv_str = await run_in_threadpool(agent.generate_seed_csv, request.prompt)
        
        # 2. Write seed CSV to a temp file then upload to Cloudinary
        file_id = str(uuid.uuid4())
        seed_bytes = seed_csv_str.encode("utf-8")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(seed_bytes)
            file_path = tmp.name

        cloudinary_url = await run_in_threadpool(
            cloud_storage.upload_file,
            seed_bytes,
            f"uploads/{file_id}",
            "synthetix",
        )
            
        # 3. Process it just like a normal upload
        loaded_data = await run_in_threadpool(load_from_file, file_path)
        
        # Validate seed dataset has minimum viable rows
        if loaded_data.row_count < 8:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=400, 
                detail=f"The AI generated only {loaded_data.row_count} seed rows. Minimum 8 rows required. This often happens with overly complex or safety-sensitive prompts. Please simplify your prompt and try again."
            )
        
        # Validate column count
        if loaded_data.column_count > 100:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=400,
                detail=f"Generated dataset has {loaded_data.column_count} columns. Maximum 100 columns allowed. Please simplify your prompt."
            )
            
        profile = await run_in_threadpool(profile_dataset, loaded_data.dataframe)
        relationships = await run_in_threadpool(analyze_relationships, loaded_data.dataframe)
        
        # Truncate JSON data to fit within limits
        from app.schemas.dataset import truncate_json_data
        profile = truncate_json_data(profile, 1000, "Profile")
        relationships = truncate_json_data(relationships, 1000, "Relationships")
        
        # 4. Save to DB — embed row_count in prompt so graph_worker can parse it
        # We prefix the prompt with the row count instruction for reliable parsing
        enriched_prompt = f"Generate exactly {request.row_count} rows. {request.prompt}"
        
        # Ensure enriched prompt doesn't exceed limit
        if len(enriched_prompt) > 2000:
            enriched_prompt = enriched_prompt[:2000]
        
        db_dataset = Dataset(
            name=f"Generated: {request.prompt[:40]}...",
            source_type="prompt",
            source_filename=cloudinary_url,   # URL instead of local path
            row_count=request.row_count,
            column_count=loaded_data.column_count,
            prompt=enriched_prompt,
            profile_json=profile,
            relationships_json=relationships,
            user_id=current_user.id,
        )
        db.add(db_dataset)
        db.commit()
        db.refresh(db_dataset)
        
        # 5. Automatically enqueue the Generation Job to expand the seed dataset
        job = Job(dataset_id=db_dataset.id, status=JobStatus.PENDING, current_step="queued", user_id=current_user.id)
        db.add(job)
        db.commit()
        db.refresh(job)
        
        background_tasks.add_task(run_generation_job, job.id)
        
        return {"message": "Generation job started", "job_id": job.id, "dataset_id": db_dataset.id}

        
    except HTTPException:
        raise
    except ValueError as e:
        # ValueError from seed generator carries a safe user-facing message
        logger.error(f"Seed generation ValueError: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        from app.core.error_sanitiser import raise_safe_http_error
        raise_safe_http_error(e, status_code=500, context="generate_from_prompt")


@router.get("/", response_model=list[DatasetResponse])
def get_datasets(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        logger.info(f"Fetching datasets for user {current_user.id}")
        datasets = db.query(Dataset).filter(Dataset.user_id == current_user.id).order_by(Dataset.created_at.desc()).offset(skip).limit(limit).all()
        logger.info(f"Found {len(datasets)} datasets for user {current_user.id}")
        
        # Convert to response format explicitly to catch any serialization issues
        result = []
        for dataset in datasets:
            try:
                result.append(DatasetResponse.model_validate(dataset))
            except Exception as e:
                logger.error(f"Failed to serialize dataset {dataset.id}: {e}")
                # Skip this dataset but continue with others
                continue
        
        return result
    except Exception as e:
        logger.error(f"Error fetching datasets for user {current_user.id}: {e}", exc_info=True)
        # Return empty list instead of raising error if it's just a query issue
        if "no such table" in str(e).lower() or "database" in str(e).lower():
            logger.warning("Database table not found or not initialized. Returning empty list.")
            return []
        from app.core.error_sanitiser import raise_safe_http_error
        raise_safe_http_error(e, status_code=500, context="get_datasets")


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.get("/{dataset_id}/profile")
def get_dataset_profile(dataset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if not dataset.profile_json:
        raise HTTPException(status_code=404, detail="Profile not generated yet")
    return dataset.profile_json


@router.get("/{dataset_id}/relationships")
def get_dataset_relationships(dataset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
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
    current_user: User = Depends(get_current_user),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if not dataset.source_filename:
        raise HTTPException(
            status_code=422,
            detail="Source file is missing. Please re-upload the dataset.",
        )

    # Create Job
    job = Job(dataset_id=dataset.id, status=JobStatus.PENDING, current_step="queued", user_id=current_user.id)
    db.add(job)
    db.commit()
    db.refresh(job)

    # Enqueue background task
    background_tasks.add_task(run_generation_job, job.id)

    return {"message": "Generation job started", "job_id": job.id}

@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Check if there are any running jobs for this dataset
    running_jobs = db.query(Job).filter(
        Job.dataset_id == dataset.id,
        Job.status.in_([JobStatus.PENDING, JobStatus.RUNNING])
    ).count()
    
    if running_jobs > 0:
        raise HTTPException(
            status_code=409, 
            detail="Cannot delete dataset with active jobs. Please wait for jobs to complete or cancel them first."
        )
    
    # Delete all associated jobs first
    db.query(Job).filter(Job.dataset_id == dataset.id).delete()
    
    # Delete source file from Cloudinary if it's a URL
    if dataset.source_filename and dataset.source_filename.startswith("http"):
        # public_id is embedded in the URL as "synthetix/uploads/<uuid>"
        try:
            parts = dataset.source_filename.split("/upload/")
            if len(parts) == 2:
                public_id = parts[1].split(".")[0]  # strip version/extension
                cloud_storage.delete_file(public_id)
        except Exception as e:
            logger.warning(f"Failed to delete Cloudinary asset for dataset {dataset.id}: {e}")
    
    db.delete(dataset)
    db.commit()
    
    return {"status": "deleted"}
