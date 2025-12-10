# 🚀 IMMEDIATE DEPLOYMENT INSTRUCTIONS

## Problem Summary
The scraper starts (PID 201, 261) but dies immediately. The old code doesn't have the comprehensive logging we just added, so we can't see WHY it's failing.

## What Was Fixed
1. ✅ Added comprehensive step-by-step logging (12 steps tracked)
2. ✅ Fixed `RuntimeError: Working outside of application context` in thread
3. ✅ Added `procps` package to Dockerfile (provides `pgrep` command)
4. ✅ Enhanced error detection (imports, syntax, permissions, DB connection)
5. ✅ All 155 tests passing, 70.28% coverage

## Deploy to Raspberry Pi NOW

### Step 1: SSH to Pi
```bash
ssh igor@your-pi-address
```

### Step 2: Pull Latest Code
```bash
cd /home/igor/BachelorApi/BPR-BackEnd-API
git pull origin main
```

### Step 3: Rebuild and Restart Container
```bash
# Stop and remove old container
docker-compose down

# Rebuild with new Dockerfile (installs procps)
docker-compose build --no-cache bpr-flask

# Start services
docker-compose up -d

# Verify containers are running
docker ps
```

### Step 4: Monitor Startup Logs
```bash
docker logs -f bpr-flask
```

**Look for:**
- `INITIALIZING BPR BACKEND API`
- `Database initialized`
- `ML Predictor initialized`
- `Serving on http://...`

### Step 5: Test Scraper Trigger

**From your browser:** https://carpredict.online → Backend Health → Click "Trigger Scraping"

**Watch Docker logs immediately after clicking:**
```bash
docker logs -f bpr-flask
```

### Step 6: What You'll See in New Logs

**If working correctly:**
```
[request_id] ========== SCRAPER TRIGGER START ==========
[request_id] Step 1: Checking for running scraper processes...
[request_id] Checking for pattern: bilbasen_incremental
[request_id] pgrep result for bilbasen_incremental: returncode=1, stdout=
[request_id] No running scraper found - proceeding
[request_id] Step 2: Parsed scraping mode: incremental
[request_id] Step 11: Creating background thread...
[request_id] Step 12: Starting background thread...
[request_id][thread_id] ===== BACKGROUND THREAD STARTED =====
[request_id][thread_id] Step 3a: Checking Docker script path: /app/ML_Model/bilbasen_incremental.py
[request_id][thread_id] Script validation: exists=True, readable=True, executable=False
[request_id][thread_id] Step 4: Script validated
[request_id][thread_id] Step 5: Using Python command: python3
[request_id][thread_id] Python location: /usr/bin/python3
[request_id][thread_id] Step 6: Preparing environment variables...
[request_id][thread_id] Database URL present: True
[request_id][thread_id] Parsed DB credentials from URI
[request_id][thread_id] Final env vars: DB=car_prediction, USER=bpr_user, HOST=db, PORT=5432
[request_id][thread_id] Step 7: Building command...
[request_id][thread_id] Step 8: Executing command: python3 /app/ML_Model/bilbasen_incremental.py
[request_id][thread_id] Working directory: /app
[request_id][thread_id] Step 9: Starting subprocess.Popen...
[request_id][thread_id] [SUCCESS] Process spawned with PID: 12345
[request_id][thread_id] Step 10: Waiting 0.5s to check process health...
[request_id][thread_id] Process poll result: None (None=still running)
[request_id][thread_id] [SUCCESS] Process still running after 0.5s - scraper appears healthy
[request_id][thread_id] Scraper will continue running in background
```

**If it fails, you'll see:**
```
[request_id][thread_id] [FAILED] Scraper died immediately!
[request_id][thread_id] Exit code: 1
[request_id][thread_id] STDOUT (xxx chars): <output here>
[request_id][thread_id] STDERR (xxx chars): <error here>
[request_id][thread_id] ERROR TYPE: Missing Python dependency
```

### Step 7: Check Scraper Process

**Inside container:**
```bash
# Check if scraper is running
docker exec bpr-flask pgrep -f bilbasen_incremental

# If running, you'll see a PID number
# If not running, no output
```

### Step 8: Check Scraper Logs

**Via API:**
```bash
curl "https://carpredict.online/api/scraper-logs?lines=100"
```

**Or from inside container:**
```bash
docker exec bpr-flask tail -f /app/ML_Model/logs/incremental_20251210.log
```

## Common Issues and Solutions

### Issue 1: "pgrep: command not found" (FIXED)
**Solution:** Rebuild container - we added `procps` package

### Issue 2: "ModuleNotFoundError" in scraper
**Check:** Does bilbasen_incremental.py need extra dependencies?
```bash
docker exec bpr-flask python3 -c "import psycopg2, requests, bs4"
```

### Issue 3: "Permission denied"
**Fix:**
```bash
docker exec bpr-flask chmod +x /app/ML_Model/bilbasen_incremental.py
```

### Issue 4: "Connection refused" (database)
**Check:**
```bash
# Is PostgreSQL container running?
docker ps | grep postgres

# Can Flask connect to DB?
docker exec bpr-flask python3 -c "import psycopg2; psycopg2.connect(host='db', database='car_prediction', user='bpr_user', password='your_password')"
```

## Expected Timeline

1. **Rebuild container:** 2-3 minutes
2. **Container startup:** 30-40 seconds
3. **Trigger scraper:** Immediate
4. **See detailed logs:** Immediate
5. **Identify root cause:** Within 1 minute

## After Deployment

Once you trigger the scraper and see the logs, **send me the new log output** and I can tell you exactly what's wrong!

The new logging will show:
- ✅ Whether script file exists and is readable
- ✅ Whether Python is found
- ✅ What environment variables are set
- ✅ The exact command being executed
- ✅ The PID of the spawned process
- ✅ If it dies, the STDOUT/STDERR output
- ✅ Specific error type classification

## Quick Deploy Commands (Copy-Paste)

```bash
ssh igor@your-pi-address
cd /home/igor/BachelorApi/BPR-BackEnd-API
git pull origin main
docker-compose down
docker-compose build --no-cache bpr-flask
docker-compose up -d
docker logs -f bpr-flask
```

Then trigger from browser and watch the logs! 🎯
