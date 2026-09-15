from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import health
from app.core.config import settings
import uuid
import time

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Agentic AI Synthetic Data Generator API",
    version="1.0.1"  # Incremented to force Railway redeploy
)

# ─── Request ID Middleware for debugging ─────────────────────────────────────
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to each request for debugging"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log request details
    from app.core.logging import logger
    logger.info(
        f"Request: {request.method} {request.url.path} | "
        f"Status: {response.status_code} | "
        f"Time: {process_time:.3f}s | "
        f"Request-ID: {request_id}"
    )
    
    return response

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

# ─── Explicit OPTIONS handler — belt-and-suspenders CORS preflight ─────────────
# Some hosting platforms (Railway, Render) return their own 502/503 error pages
# before the CORS middleware can add headers. This handler guarantees preflight
# OPTIONS requests always get a proper 200 with CORS headers.
from fastapi import Response as FastAPIResponse
from fastapi.routing import APIRoute

@app.options("/{full_path:path}")
async def handle_preflight(request: Request, full_path: str):
    origin = request.headers.get("origin", "*")
    return FastAPIResponse(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type, Accept, Origin, X-Requested-With",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "86400",
        },
    )

from app.db.database import Base, engine
from app.models.dataset import Dataset
from app.models.job import Job
from app.models.user import User
from app.models.api_key import ApiKey
from app.models.template import Template

@app.on_event("startup")
def startup_db():
    try:
        from sqlalchemy import text
        Base.metadata.create_all(bind=engine)
        # Ensure hashed_password is nullable for Google OAuth in PostgreSQL
        try:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL;"))
                conn.commit()
        except Exception:
            pass
    except Exception as e:
        import logging
        logging.getLogger("uvicorn.error").warning(f"Database table initialization warning: {e}")

# ─── COOP Middleware ──────────────────────────────────────────────────────────
# Google Sign-In popup uses postMessage to communicate with the opener window.
# The default COOP value "same-origin" blocks that. We must use
# "same-origin-allow-popups" so the OAuth popup can call postMessage.
from starlette.middleware.base import BaseHTTPMiddleware

class COOPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
        return response

app.add_middleware(COOPMiddleware)

# CORS configuration - Allow all origins in production for Railway deployment
_cors_origins = [
    # Local dev
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:80",
    "http://localhost",
    # Production — Vercel frontend
    "https://synthetic-data-generator-mu.vercel.app",
    # Railway backend (for internal health checks)
    "https://synthetix-backend-production-43d0.up.railway.app",
]

# Also add any extra URL from env (e.g. custom domain / preview deployments)
if hasattr(settings, 'FRONTEND_URL') and settings.FRONTEND_URL:
    _cors_origins.append(settings.FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    # Covers localhost variants + all Vercel/Railway preview URLs
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$|^https://[a-z0-9-]+\.(vercel\.app|railway\.app)$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["*"],
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
