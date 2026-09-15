# Cloudinary 500 Error - Root Cause Analysis & Fix

## Issue Summary

**Problem:** POST to `/api/datasets/generate-from-prompt` and `/api/datasets/upload` returning 500 Internal Server Error in production.

**Root Cause:** Cloudinary credentials not configured in Railway environment. The application was using placeholder values from the `.env` file instead of real credentials.

**Impact:** Users unable to:
- Upload dataset files
- Generate datasets from prompts
- Complete any workflow requiring file storage

## Root Cause Analysis

### 1. Missing Credentials in Railway

The Railway deployment was using these placeholder values:
```bash
CLOUDINARY_API_KEY=placeholder_cloudinary_api_key
CLOUDINARY_API_SECRET=placeholder_cloudinary_api_secret
```

These placeholders caused Cloudinary API calls to fail with authentication errors, which were being caught as generic 500 errors without clear messaging.

### 2. Poor Error Reporting

The original code didn't validate credentials before attempting uploads, leading to:
- Generic 500 errors with no actionable information
- No way to distinguish between config errors vs. upload failures
- Difficult debugging in production

### 3. Architecture Context

Synthetix requires cloud storage because:
- Railway uses ephemeral filesystem (files don't persist across deploys)
- Datasets can be large (up to 30,000 rows, 100MB files)
- Synthetic outputs need permanent storage
- Multiple background workers need access to the same files

## Changes Implemented

### 1. Credential Validation (`backend/app/core/storage.py`)

**Before:**
```python
def _configure():
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )
```

**After:**
```python
def _configure():
    """Configure Cloudinary with credentials from environment variables."""
    # Validate credentials are set
    if (settings.CLOUDINARY_API_KEY == "placeholder_cloudinary_api_key" or 
        settings.CLOUDINARY_API_SECRET == "placeholder_cloudinary_api_secret" or
        not settings.CLOUDINARY_CLOUD_NAME or
        settings.CLOUDINARY_CLOUD_NAME == "placeholder_cloud_name"):
        raise ValueError(
            "Cloudinary credentials not configured. Please set CLOUDINARY_CLOUD_NAME, "
            "CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET environment variables. "
            "Get these from https://cloudinary.com/console"
        )
    
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )
```

**Benefits:**
- Detects placeholder values before attempting API calls
- Provides clear, actionable error message
- Prevents cryptic authentication errors

### 2. Enhanced Upload Error Handling (`backend/app/core/storage.py`)

**Before:**
```python
def upload_file(file_bytes: bytes, public_id: str, folder: str = "synthetix") -> str:
    _configure()
    result = cloudinary.uploader.upload(
        file_bytes,
        public_id=public_id,
        folder=folder,
        resource_type="raw",
        overwrite=True,
    )
    url: str = result["secure_url"]
    logger.info(f"Uploaded to Cloudinary: {url}")
    return url
```

**After:**
```python
def upload_file(file_bytes: bytes, public_id: str, folder: str = "synthetix") -> str:
    """
    Upload raw bytes to Cloudinary.
    
    Raises:
        ValueError: If Cloudinary credentials are not configured.
        Exception: If upload fails (network, quota, authentication, etc.)
    """
    try:
        _configure()
        result = cloudinary.uploader.upload(
            file_bytes,
            public_id=public_id,
            folder=folder,
            resource_type="raw",
            overwrite=True,
        )
        url: str = result["secure_url"]
        logger.info(f"Uploaded to Cloudinary: {url}")
        return url
    except ValueError as ve:
        # Credentials not configured
        logger.error(f"Cloudinary configuration error: {ve}")
        raise
    except Exception as e:
        logger.error(f"Cloudinary upload failed for {public_id}: {e}", exc_info=True)
        raise Exception(f"File upload failed: {str(e)}") from e
```

**Benefits:**
- Distinguishes config errors from upload failures
- Logs full stack traces for debugging
- Propagates clear error messages to API layer

### 3. API Endpoint Error Handling (`backend/app/api/routes/datasets.py`)

Added specific error handling in both `upload_dataset()` and `generate_from_prompt()`:

```python
# Upload to Cloudinary with error handling
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
```

**Benefits:**
- User-friendly error messages in API responses
- Distinguishes between config issues and transient failures
- Helps users understand what action to take

### 4. Comprehensive Documentation (`CLOUDINARY_SETUP.md`)

Created step-by-step guide covering:
- Why Cloudinary is needed
- How to get credentials (with links)
- How to configure Railway environment variables
- Testing procedures
- Troubleshooting tips
- Security best practices

## Testing Checklist

After deploying the fix and configuring Cloudinary credentials:

- [ ] **Upload CSV File**: Go to Datasets → Upload → Select a CSV → Verify success
- [ ] **Upload Excel File**: Upload an .xlsx file → Verify success
- [ ] **Generate from Prompt**: Use "Generate from Prompt" → Enter a prompt → Verify seed generation
- [ ] **Check Cloudinary Console**: Verify files appear in `synthetix/uploads/` folder
- [ ] **Check Railway Logs**: No "Cloudinary configuration error" messages
- [ ] **Download Dataset**: Generate synthetic data → Download → Verify CSV downloads correctly

## Error Messages (Before vs After)

### Before Fix
```
POST /api/datasets/generate-from-prompt 500 (Internal Server Error)
```
- Generic error
- No indication of root cause
- Impossible to debug without server access

### After Fix (Missing Credentials)
```json
{
  "detail": "File storage service is not configured. Please contact support or check CLOUDINARY credentials in environment variables."
}
```
- Clear indication of the issue
- Actionable next step
- Points to environment configuration

### After Fix (Upload Failure)
```json
{
  "detail": "File upload failed: [specific error]. The storage service may be unavailable or over quota. Please try again later."
}
```
- Includes specific error details
- Suggests it might be transient
- Encourages retry

## Deployment Steps

### 1. Code Deployment (✅ Complete)

```bash
# Already pushed to GitHub
git log --oneline -1
# 48a7d81c fix(storage): add Cloudinary credential validation and better error handling
```

### 2. Railway Configuration (🔄 Action Required)

1. Go to [Railway Dashboard](https://railway.app/)
2. Select your Synthetix backend service
3. Navigate to **Variables** tab
4. Add/Update these three variables:

```bash
CLOUDINARY_CLOUD_NAME=<your_cloud_name>
CLOUDINARY_API_KEY=<your_api_key>
CLOUDINARY_API_SECRET=<your_api_secret>
```

5. Save changes (Railway will auto-redeploy)

### 3. Get Cloudinary Credentials

If you don't have a Cloudinary account yet:

1. Sign up at [https://cloudinary.com/users/register_free](https://cloudinary.com/users/register_free)
2. Free tier includes:
   - 25GB storage
   - 25GB bandwidth/month
   - No credit card required
3. Get credentials from [Dashboard](https://cloudinary.com/console)

### 4. Verify Fix

```bash
# Test endpoint health
curl https://synthetix-backend-production-43d0.up.railway.app/api/health

# Test generate-from-prompt (should get clear error if not configured)
curl -X POST https://synthetix-backend-production-43d0.up.railway.app/api/datasets/generate-from-prompt \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_token>" \
  -d '{"prompt": "Generate customer data", "row_count": 100}'
```

## Files Changed

| File | Changes | Purpose |
|------|---------|---------|
| `backend/app/core/storage.py` | Added credential validation, enhanced error handling | Detect config issues early, provide clear errors |
| `backend/app/api/routes/datasets.py` | Added try-catch blocks for uploads | User-friendly API error messages |
| `CLOUDINARY_SETUP.md` | New comprehensive guide | Help users set up credentials correctly |

## Git Commits

```bash
48a7d81c fix(storage): add Cloudinary credential validation and better error handling
a0e82c21 Fix: Enhanced error handling and LLM validation for generate-from-prompt endpoint
3ba73c8c feat(monitoring): enhance health check endpoints
bb75b45b fix(frontend): improve API configuration and auth handling
c95e63f1 feat(errors): enhance error handling with better user messages
b87c8c72 fix(api): resolve 405 Method Not Allowed error on datasets endpoint
```

## Next Steps

1. **Immediate (Required for app to work):**
   - [ ] Get Cloudinary credentials from [cloudinary.com/console](https://cloudinary.com/console)
   - [ ] Add credentials to Railway environment variables
   - [ ] Wait for Railway auto-redeploy (~2-3 minutes)
   - [ ] Test dataset upload and prompt generation

2. **Verification:**
   - [ ] Run through testing checklist above
   - [ ] Check Railway logs for any errors
   - [ ] Verify files appear in Cloudinary dashboard

3. **Optional Improvements:**
   - Consider adding Cloudinary quota monitoring
   - Set up alerts for upload failures
   - Add retry logic for transient network failures
   - Consider backup storage provider

## Support

If issues persist after configuration:
1. Check Railway logs for detailed error messages
2. Verify Cloudinary credentials are correct (try them in Cloudinary console)
3. Check Cloudinary quota hasn't been exceeded
4. Verify network connectivity from Railway to Cloudinary

## Summary

**Root Cause:** Missing Cloudinary credentials in Railway environment

**Fix:** Added credential validation and better error handling to detect and report configuration issues clearly

**Action Required:** Configure Cloudinary credentials in Railway (5-10 minute task)

**ETA to Working:** Once credentials are added, app will work immediately after Railway redeploys (~2-3 minutes)
