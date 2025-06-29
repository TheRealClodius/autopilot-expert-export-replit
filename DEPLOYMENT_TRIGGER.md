# CRITICAL DEPLOYMENT ENVIRONMENT VARIABLES

## Redis Connection Error Fix

**Problem:** Deployment showing `error dial tcp 127.0.0.1:6379: connect: connection refused`

**Root Cause:** When these environment variables are EMPTY in deployment, something defaults to `redis://localhost:6379`

## REQUIRED DEPLOYMENT ENVIRONMENT VARIABLES

Set these explicitly in your deployment environment:

```bash
# Disable Redis connections completely (RECOMMENDED)
export CELERY_BROKER_URL=''
export CELERY_RESULT_BACKEND=''
export REDIS_URL=''
```

**Alternative option:**
```bash
# Use memory transport explicitly  
export CELERY_BROKER_URL='memory://'
export CELERY_RESULT_BACKEND='cache+memory://'
export REDIS_URL=''
```

## Deployment Status

- ✅ Application code updated to handle empty Redis configurations
- ✅ Celery fallback to memory transport implemented
- ✅ Health checks skip Redis when not configured
- ✅ All localhost Redis URLs blocked and replaced with memory transport
- 🔄 **DEPLOYMENT NEEDED:** Environment variables must be set explicitly

## Verification

After setting environment variables, check logs for:
```
- celery_app - INFO - Using memory transport (broker_url='')
- celery_app - INFO - Using cache+memory backend (backend_url='')
```

This will eliminate ALL Redis connection attempts in deployment.