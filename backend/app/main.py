from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import health
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Agentic AI Synthetic Data Generator API",
    version="1.0.0"
)

from app.db.database import Base, engine
from app.models.dataset import Dataset
from app.models.job import Job
Base.metadata.create_all(bind=engine)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
from app.api.routes import datasets
app.include_router(datasets.router, prefix="/api/datasets", tags=["datasets"])
from app.api.routes import jobs
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
