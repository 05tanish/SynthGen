from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.concurrency import run_in_threadpool
from typing import Optional, List
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
        try:
            cloudinary_url = await run_in_threadpool(
                cloud_storage.upload_file,
                file_bytes,
                f"uploads/{file_id}",
                "synthetix",
            )
        except ValueError as ve:
            # Cloudinary credentials not configured
            logger.error(f"Cloudinary configuration error: {ve}")
            raise HTTPException(
                status_code=500,
                detail="File storage service is not configured. Please contact support or check CLOUDINARY credentials in environment variables."
            )
        except Exception as e:
            # Cloudinary upload failed (network, quota, auth, etc.)
            logger.error(f"Cloudinary upload failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"File upload failed: {str(e)}. The storage service may be unavailable or over quota. Please try again later."
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
        
        # Cache profile and relationships for faster access
        from app.cache.cache_service import CacheService
        CacheService.set_dataset_profile(db_dataset.id, profile)
        CacheService.set_dataset_relationships(db_dataset.id, relationships)
        
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
        logger.info(f"Generate-from-prompt called with prompt: {request.prompt[:100]}... | row_count: {request.row_count}")
        
        # Validate request (Pydantic will auto-validate, but we add extra checks)
        if request.row_count > 30000:
            raise HTTPException(
                status_code=400,
                detail="Row count exceeds maximum limit of 30,000 rows"
            )
        
        # 1. Ask LLM to generate a seed CSV
        logger.info("Initializing SeedGeneratorAgent...")
        try:
            agent = SeedGeneratorAgent()
        except Exception as e:
            logger.error(f"Failed to initialize SeedGeneratorAgent: {e}")
            raise HTTPException(
                status_code=500,
                detail="AI service is not properly configured. Please check LLM_API_KEY environment variable."
            )
        
        logger.info("Generating seed CSV from prompt...")
        try:
            seed_csv_str = await run_in_threadpool(agent.generate_seed_csv, request.prompt)
            logger.info(f"Seed CSV generated successfully. Length: {len(seed_csv_str)} chars")
        except ValueError as ve:
            # ValueError from seed generator carries a safe user-facing message
            logger.error(f"Seed generation ValueError: {ve}")
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            logger.error(f"Seed generation failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Failed to generate seed data. The AI service may be rate-limited or unavailable. Please try again in a moment."
            )
        
        # 2. Write seed CSV to a temp file then upload to Cloudinary
        file_id = str(uuid.uuid4())
        seed_bytes = seed_csv_str.encode("utf-8")
        file_path = None
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                tmp.write(seed_bytes)
                file_path = tmp.name

            logger.info(f"Uploading seed CSV to Cloudinary...")
            try:
                cloudinary_url = await run_in_threadpool(
                    cloud_storage.upload_file,
                    seed_bytes,
                    f"uploads/{file_id}",
                    "synthetix",
                )
                logger.info(f"Cloudinary upload successful: {cloudinary_url}")
            except ValueError as ve:
                # Cloudinary credentials not configured
                logger.error(f"Cloudinary configuration error: {ve}")
                raise HTTPException(
                    status_code=500,
                    detail="File storage service is not configured. Please contact support or check CLOUDINARY credentials in environment variables."
                )
            except Exception as e:
                # Cloudinary upload failed (network, quota, auth, etc.)
                logger.error(f"Cloudinary upload failed: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"File upload failed: {str(e)}. The storage service may be unavailable or over quota. Please try again later."
                )
                
            # 3. Process it just like a normal upload
            logger.info("Loading and profiling seed data...")
            loaded_data = await run_in_threadpool(load_from_file, file_path)
            
            # Validate seed dataset has minimum viable rows
            if loaded_data.row_count < 8:
                raise HTTPException(
                    status_code=400, 
                    detail=f"The AI generated only {loaded_data.row_count} seed rows. Minimum 8 rows required. This often happens with overly complex or safety-sensitive prompts. Please simplify your prompt and try again."
                )
            
            # Validate column count
            if loaded_data.column_count > 100:
                raise HTTPException(
                    status_code=400,
                    detail=f"Generated dataset has {loaded_data.column_count} columns. Maximum 100 columns allowed. Please simplify your prompt."
                )
            
            logger.info(f"Seed data loaded: {loaded_data.row_count} rows, {loaded_data.column_count} columns")
                
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
            
            logger.info("Creating dataset record in database...")
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
            logger.info("Creating generation job...")
            job = Job(dataset_id=db_dataset.id, status=JobStatus.PENDING, current_step="queued", user_id=current_user.id)
            db.add(job)
            db.commit()
            db.refresh(job)
            
            background_tasks.add_task(run_generation_job, job.id)
            
            logger.info(f"Generation job started successfully. Job ID: {job.id}, Dataset ID: {db_dataset.id}")
            return {"message": "Generation job started", "job_id": job.id, "dataset_id": db_dataset.id}
        
        finally:
            # Clean up temp file
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file {file_path}: {e}")

        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        # ValueError from seed generator carries a safe user-facing message
        logger.error(f"Seed generation ValueError: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log full error for debugging
        logger.error(f"Unexpected error in generate_from_prompt: {e}", exc_info=True)
        from app.core.error_sanitiser import raise_safe_http_error
        raise_safe_http_error(e, status_code=500, context="generate_from_prompt")


@router.get("/", response_model=List[DatasetResponse])
async def get_datasets(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Get all datasets for the authenticated user.
    Supports pagination with skip and limit parameters.
    """
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
    """
    Delete a dataset and all associated resources.
    
    Safety checks:
    1. Cannot delete if there are running or pending jobs
    2. Deletes all associated jobs (completed/failed)
    3. Cleans up Cloudinary files
    4. Transaction-safe deletion
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Check if there are any running or pending jobs for this dataset
    active_jobs = db.query(Job).filter(
        Job.dataset_id == dataset.id,
        Job.status.in_([JobStatus.PENDING, JobStatus.RUNNING])
    ).all()
    
    if active_jobs:
        job_ids = [job.id for job in active_jobs]
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete dataset with active jobs (IDs: {job_ids}). Please cancel or wait for jobs to complete first."
        )
    
    # Get all jobs for cleanup
    all_jobs = db.query(Job).filter(Job.dataset_id == dataset.id).all()
    
    # Clean up Cloudinary files for all jobs (synthetic data)
    for job in all_jobs:
        if job.synthetic_file_path and job.synthetic_file_path.startswith("http"):
            try:
                # Extract public_id from Cloudinary URL
                # Format: https://res.cloudinary.com/{cloud}/upload/{version}/{public_id}.{format}
                parts = job.synthetic_file_path.split("/upload/")
                if len(parts) >= 2:
                    # Get everything after /upload/, then split by first dot to remove version and extension
                    path_after_upload = parts[1]
                    # Remove version number (v1234567890) if present
                    if path_after_upload.startswith("v"):
                        path_parts = path_after_upload.split("/", 1)
                        if len(path_parts) == 2:
                            path_after_upload = path_parts[1]
                    # Remove extension
                    public_id = path_after_upload.rsplit(".", 1)[0]
                    cloud_storage.delete_file(public_id)
                    logger.info(f"Deleted Cloudinary file for job {job.id}: {public_id}")
            except Exception as e:
                logger.warning(f"Failed to delete Cloudinary file for job {job.id}: {e}")
    
    # Delete source file from Cloudinary if it's a URL
    if dataset.source_filename and dataset.source_filename.startswith("http"):
        try:
            parts = dataset.source_filename.split("/upload/")
            if len(parts) >= 2:
                path_after_upload = parts[1]
                if path_after_upload.startswith("v"):
                    path_parts = path_after_upload.split("/", 1)
                    if len(path_parts) == 2:
                        path_after_upload = path_parts[1]
                public_id = path_after_upload.rsplit(".", 1)[0]
                cloud_storage.delete_file(public_id)
                logger.info(f"Deleted Cloudinary source file for dataset {dataset.id}: {public_id}")
        except Exception as e:
            logger.warning(f"Failed to delete Cloudinary source file for dataset {dataset.id}: {e}")
    
    # Delete all associated jobs (CASCADE should handle this, but we're explicit for logging)
    deleted_job_count = db.query(Job).filter(Job.dataset_id == dataset.id).delete()
    logger.info(f"Deleted {deleted_job_count} jobs for dataset {dataset.id}")
    
    # Delete the dataset
    db.delete(dataset)
    db.commit()
    
    # Invalidate cache for this dataset
    from app.cache.cache_service import CacheService
    CacheService.invalidate_dataset(dataset.id)
    
    logger.info(f"Successfully deleted dataset {dataset.id} and all associated resources")
    
    return {
        "status": "deleted",
        "dataset_id": dataset_id,
        "jobs_deleted": deleted_job_count
    }
