# Railway Deployment Guide

## Services Required

This application needs **TWO services** running on Railway:

### 1. API Service (Web)
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Root Directory**: `/backend`
- Handles HTTP requests from frontend

### 2. Worker Service (Background)
- **Start Command**: `python run_worker.py`
- **Root Directory**: `/backend`  
- Processes generation jobs from database

## Setup Instructions

### Option A: Using railway.toml (Automatic)
The `railway.toml` file configures both services automatically.

1. Push code to GitHub
2. Railway detects `railway.toml`
3. Creates both API and Worker services
4. Done!

### Option B: Manual Setup (If railway.toml doesn't work)

1. **Keep existing API service** running

2. **Add Worker Service**:
   - Click "New Service" in Railway dashboard
   - Select "GitHub Repo" 
   - Choose your repository
   - Configure:
     - Name: `worker`
     - Root Directory: `/backend`
     - Start Command: `python run_worker.py`
   
3. **Copy Environment Variables**:
   - Go to API service settings
   - Copy ALL environment variables
   - Paste into Worker service settings
   
4. **Deploy Worker**

## Environment Variables Needed

Both services need these variables (copy from .env or existing service):

```
DATABASE_URL=postgresql://...
UPSTASH_REDIS_URL=...
UPSTASH_REDIS_TOKEN=...
LLM_PROVIDER=groq
LLM_API_KEY=...
LLM_MODEL=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_HOST=...
SECRET_KEY=...
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
GOOGLE_CLIENT_ID=...
```

## How It Works

1. User creates job via frontend → API service
2. API saves job as PENDING in database
3. Worker polls database every 5 seconds
4. Worker finds PENDING jobs and processes them
5. Worker updates job status to COMPLETED
6. Frontend shows completed job with download

## Troubleshooting

### Worker Not Processing Jobs
- Check worker service logs in Railway dashboard
- Verify all environment variables are set
- Run health check: `python check_worker.py`

### Build Fails
- Check Railway build logs
- Verify `requirements.txt` has all dependencies
- Ensure Python version is compatible (3.12+)

### Jobs Stuck in "Generating..."
- Worker service is probably not running
- Check worker logs for errors
- Verify DATABASE_URL is correct

## Testing

After deployment, create a test job:
1. Upload a small CSV
2. Click Generate
3. Job should complete in 30-60 seconds
4. Check worker logs to see processing

## Logs

View logs in Railway dashboard:
- **API logs**: HTTP requests, errors
- **Worker logs**: Job processing, generation progress
