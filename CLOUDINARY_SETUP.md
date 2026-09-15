# Cloudinary Setup Guide

## Critical Issue: Missing Cloudinary Credentials

Your application is currently failing with 500 errors because **Cloudinary credentials are not configured in Railway**.

The error occurs when trying to:
- Upload datasets via file upload
- Generate datasets from prompts
- Store synthetic data outputs

## Why Cloudinary?

Synthetix uses Cloudinary as cloud storage for:
- Uploaded dataset files (CSV, Excel, JSON, Parquet)
- AI-generated seed datasets
- Final synthetic data outputs
- Temporary file storage during processing

Railway's ephemeral filesystem doesn't persist files across deployments, so cloud storage is essential.

## How to Get Cloudinary Credentials

### 1. Create a Free Cloudinary Account

1. Go to [https://cloudinary.com/users/register_free](https://cloudinary.com/users/register_free)
2. Sign up with your email (free tier includes 25GB storage and 25GB bandwidth/month)
3. Verify your email

### 2. Get Your Credentials

1. Log into [Cloudinary Console](https://cloudinary.com/console)
2. On the Dashboard, you'll see:
   - **Cloud Name**: (e.g., `agenticai`)
   - **API Key**: (e.g., `123456789012345`)
   - **API Secret**: (click "Reveal" to see it)

### 3. Configure Railway Environment Variables

1. Go to your Railway project: [https://railway.app/project/your-project](https://railway.app/project/your-project)
2. Select your **backend service**
3. Go to **Variables** tab
4. Add these three environment variables:

```bash
CLOUDINARY_CLOUD_NAME=your_cloud_name_here
CLOUDINARY_API_KEY=your_api_key_here
CLOUDINARY_API_SECRET=your_api_secret_here
```

**Example:**
```bash
CLOUDINARY_CLOUD_NAME=agenticai
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=AbCdEfGhIjKlMnOpQrStUvWxYz
```

### 4. Restart the Service

After adding the variables:
1. Railway will automatically redeploy
2. Wait for deployment to complete
3. Test the application

## Current Configuration Status

Your `.env` file has:
```bash
CLOUDINARY_CLOUD_NAME=agenticai  ✅ (looks valid)
CLOUDINARY_API_KEY=placeholder_cloudinary_api_key  ❌ (placeholder)
CLOUDINARY_API_SECRET=placeholder_cloudinary_api_secret  ❌ (placeholder)
```

**Action Required:** Replace the placeholder values with real credentials from Cloudinary Console.

## Testing After Setup

Once configured, test these features:
1. **File Upload**: Upload a CSV/Excel file on the Datasets page
2. **Prompt Generation**: Use "Generate from Prompt" feature
3. **Check Logs**: Verify no "Cloudinary configuration error" messages

## Error Messages Explained

### Before Fix
```
POST /api/datasets/generate-from-prompt 500 (Internal Server Error)
```

### After Fix (with better error handling)
```
File storage service is not configured. Please contact support or check CLOUDINARY credentials in environment variables.
```

## Alternative: Local File Storage (Not Recommended)

If you cannot use Cloudinary, you would need to:
1. Switch to persistent volume storage (Railway's volume service)
2. Modify all storage.py functions to use local filesystem
3. Handle file cleanup and quota management manually

**Not recommended** because:
- Railway volumes cost extra
- More complex to manage
- Less scalable
- No CDN benefits

## Security Notes

- **Never commit** Cloudinary credentials to git
- Store them only in Railway environment variables
- Cloudinary credentials in `.env` are for **local development only**
- Use different Cloudinary accounts for dev/staging/production

## Support

If you need help:
- Cloudinary support: [https://support.cloudinary.com/](https://support.cloudinary.com/)
- Cloudinary docs: [https://cloudinary.com/documentation](https://cloudinary.com/documentation)

## Quick Fix Summary

**What to do right now:**

1. ✅ Code is already fixed with better error handling
2. 🔄 Get Cloudinary credentials from [cloudinary.com/console](https://cloudinary.com/console)
3. 🔄 Add them to Railway environment variables
4. ✅ Restart Railway service (automatic)
5. ✅ Test the application

**Estimated time:** 5-10 minutes
