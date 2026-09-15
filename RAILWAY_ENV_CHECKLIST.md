# Railway Environment Variables Checklist

## Quick Setup Guide

Copy this checklist when configuring your Railway backend service.

## Required Environment Variables

### ✅ Database (Already Configured)
```bash
DATABASE_URL=postgresql://user:password@host.neon.tech/database?sslmode=require
```
**Note:** Your actual DATABASE_URL is already set in Railway

### ✅ Redis (Already Configured)
```bash
UPSTASH_REDIS_URL=https://your-redis-instance.upstash.io
UPSTASH_REDIS_TOKEN=your_upstash_token_here
```
**Note:** Your actual Redis credentials are already set in Railway

### ✅ LLM Provider (Already Configured)
```bash
LLM_PROVIDER=groq
LLM_API_KEY=gsk_your_groq_api_key_here
LLM_MODEL=openai/gpt-oss-20b
```
**Note:** Your actual LLM credentials are already set in Railway

### ✅ Google OAuth (Already Configured)
```bash
GOOGLE_CLIENT_ID=your_google_client_id_here
```
**Note:** Your actual Google Client ID is already set in Railway

### ✅ Email Service (Already Configured)
```bash
RESEND_API_KEY=re_your_resend_api_key_here
```
**Note:** Your actual Resend API key is already set in Railway

### ❌ Cloudinary (ACTION REQUIRED - Currently Using Placeholders)
```bash
# Get these from https://cloudinary.com/console
CLOUDINARY_CLOUD_NAME=<your_cloud_name_here>
CLOUDINARY_API_KEY=<your_api_key_here>
CLOUDINARY_API_SECRET=<your_api_secret_here>
```

**Current Status:** Using placeholder values, causing 500 errors
**Action:** Replace with real credentials from Cloudinary dashboard

### ✅ CORS Configuration (Already Configured)
```bash
FRONTEND_URL=https://synthetic-data-generator-mu.vercel.app
```

### ✅ Application Settings (Already Configured)
```bash
MAX_ITERATIONS=5
QUALITY_THRESHOLD=0.65
MAX_UPLOAD_SIZE_MB=100
```

## Step-by-Step: Add Cloudinary Credentials

### 1. Get Credentials from Cloudinary

1. Go to [https://cloudinary.com/console](https://cloudinary.com/console)
2. Sign up for free account (if you don't have one)
3. On the Dashboard, find:
   - **Cloud Name** (e.g., `agenticai`)
   - **API Key** (e.g., `123456789012345`)
   - **API Secret** (click "Reveal" to see it)

### 2. Add to Railway

1. Open [Railway Dashboard](https://railway.app/)
2. Select your **Synthetix Backend** service
3. Click **Variables** tab
4. Click **+ Add Variable** (or edit existing ones)
5. Add these three variables:

```bash
CLOUDINARY_CLOUD_NAME=your_actual_cloud_name
CLOUDINARY_API_KEY=your_actual_api_key
CLOUDINARY_API_SECRET=your_actual_api_secret
```

6. Click **Save** or **Deploy** (Railway auto-redeploys)

### 3. Verify

Wait 2-3 minutes for deployment, then test:
```bash
# Should return 200 OK
curl https://synthetix-backend-production-43d0.up.railway.app/api/health
```

Try uploading a file or generating from prompt in the web UI.

## Common Issues

### Issue: "File storage service is not configured"
**Cause:** Cloudinary credentials not set or still using placeholders
**Fix:** Add real credentials from Cloudinary console

### Issue: "File upload failed: Invalid credentials"
**Cause:** Incorrect API key or secret
**Fix:** Double-check credentials in Cloudinary console, copy them again

### Issue: "File upload failed: Quota exceeded"
**Cause:** Free tier limit reached (25GB/month)
**Fix:** Upgrade Cloudinary plan or wait for quota reset

### Issue: Still getting 500 errors after adding credentials
**Cause:** Railway hasn't redeployed yet
**Fix:** Wait 2-3 minutes, or manually redeploy from Railway dashboard

## Verification Commands

```bash
# Test health endpoint
curl https://synthetix-backend-production-43d0.up.railway.app/api/health

# Check Railway logs
# Go to Railway Dashboard → Select Service → Deployments → Click latest deployment → View logs

# Look for these log messages:
# ✅ "Cloudinary upload successful: https://..."
# ❌ "Cloudinary configuration error: ..."
# ❌ "Cloudinary upload failed: ..."
```

## Security Notes

- **Never commit** Cloudinary credentials to git
- Store them **only** in Railway environment variables
- Your `.env` file is for **local development only**
- Use **different Cloudinary accounts** for dev/staging/production if possible

## Need Help?

1. **Setup Guide:** See `CLOUDINARY_SETUP.md` for detailed instructions
2. **Fix Summary:** See `CLOUDINARY_FIX_SUMMARY.md` for technical details
3. **Cloudinary Support:** [https://support.cloudinary.com/](https://support.cloudinary.com/)

## Quick Links

- [Railway Dashboard](https://railway.app/)
- [Cloudinary Console](https://cloudinary.com/console)
- [Cloudinary Free Signup](https://cloudinary.com/users/register_free)
- [Backend URL](https://synthetix-backend-production-43d0.up.railway.app)
- [Frontend URL](https://synthetic-data-generator-mu.vercel.app)
