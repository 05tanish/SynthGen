from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import health
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Agentic AI Synthetic Data Generator API",
    version="1.0.0"
)

# ─── Global exception handler — hides internal details from all API responses ─
def _get_cors_headers(request: Request) -> dict:
    origin = request.headers.get("origin")
    headers = {
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    }
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
    else:
        headers["Access-Control-Allow-Origin"] = "*"
    return headers

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    from app.core.error_sanitiser import safe_error_message
    from app.core.logging import logger
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": safe_error_message(exc)},
        headers=_get_cors_headers(request),
    )

from app.db.database import Base, engine
from app.models.dataset import Dataset
from app.models.job import Job
from app.models.user import User
from app.models.api_key import ApiKey
from app.models.template import Template
Base.metadata.create_all(bind=engine)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8000",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
from app.api.routes import auth
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
from app.api.routes import datasets
app.include_router(datasets.router, prefix="/api/datasets", tags=["datasets"])
from app.api.routes import jobs
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(jobs.router, prefix="/api/generations", tags=["generations"])
from app.api.routes import api_keys
app.include_router(api_keys.router, prefix="/api/api-keys", tags=["api_keys"])
from app.api.routes import templates
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])
from app.api.routes import usage
app.include_router(usage.router, prefix="/api/usage", tags=["usage"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
