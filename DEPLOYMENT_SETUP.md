# Deployment Setup Guide - Script Execution Configuration

## Overview
This guide explains the Docker configuration changes made to enable the Flask API to trigger scraper and training scripts from the frontend.

## What Was Changed

### 1. Docker Volume Mounts

Both `docker-compose.yml` (development) and `docker-compose.prod.yml` (production) have been updated with the following volume mounts:

#### Backend Service:
```yaml
volumes:
  # ML models directory
  - ./app/models:/app/app/models
  
  # API logs
  - ./logs:/app/logs
  
  # Car images from scraper
  - ../BPR-BackEnd-ML-Model/bilbasen_scrape/images:/app/images
  
  # CSV data and scraper logs (READ/WRITE)
  - ../BPR-BackEnd-ML-Model/bilbasen_scrape:/app/data
  
  # ML scripts directory for execution (READ/WRITE)
  - ../BPR-BackEnd-ML-Model:/app/ML_Model
```

#### Prediction Worker Service:
```yaml
volumes:
  # ML models directory
  - ./app/models:/app/app/models
  
  # API logs
  - ./logs:/app/logs
  
  # ML scripts directory
  - ../BPR-BackEnd-ML-Model:/app/ML_Model
```

## How Script Execution Works

### Frontend Trigger Flow:
1. User clicks "Trigger Scraping" or "Trigger Training" button in `BackendHealth.tsx`
2. Frontend calls Flask API endpoint:
   - `POST /api/trigger-scraping` (with optional `mode: incremental|full`)
   - `POST /api/trigger-training`
3. Flask API (in `app/main.py`) uses subprocess to execute Python scripts:
   - Scraper: `/app/ML_Model/auto_scraper.py`
   - Training: `/app/ML_Model/train_models.py`

### Script Paths in Container:
- `/app/ML_Model/auto_scraper.py` → Scraper script
- `/app/ML_Model/train_models.py` → Training script
- `/app/ML_Model/import_csv_to_db.py` → CSV import script
- `/app/data/car_details.csv` → Scraped car data
- `/app/data/images/` → Car images
- `/app/data/*.log` → Scraper logs (written by auto_scraper.py)

## Raspberry Pi Directory Structure

```
/home/igor/BachelorApi/
├── BPR-BackEnd-API/              # API + Docker setup
│   ├── app/
│   │   ├── main.py               # Flask endpoints
│   │   ├── models/               # ML model files (.pkl)
│   │   │   ├── best_model_catboost.pkl
│   │   │   ├── feature_scaler.pkl
│   │   │   ├── label_encoders.pkl
│   │   │   └── model_metadata.json
│   │   └── ml/predictor.py
│   ├── docker-compose.yml        # Development config
│   ├── docker-compose.prod.yml   # Production config (UPDATED)
│   └── logs/                     # API logs
│
└── BPR-BackEnd-ML-Model/         # Scripts + Data
    ├── auto_scraper.py           # Web scraper
    ├── train_models.py           # Model training
    ├── import_csv_to_db.py       # CSV import
    └── bilbasen_scrape/          # Data directory
        ├── car_details.csv       # 14,200 cars
        ├── details_checkpoint.json
        ├── images/               # 14,784+ images
        └── *.log                 # Scraper logs (WRITABLE)
```

## Important Notes

### 1. File Permissions
The scraper writes log files to `bilbasen_scrape/`. Ensure the directory has write permissions:

```bash
# On Raspberry Pi:
chmod -R 777 /home/igor/BachelorApi/BPR-BackEnd-ML-Model/bilbasen_scrape/
```

### 2. Python Dependencies
The auto_scraper.py script uses these packages (all in API requirements.txt):
- ✅ requests
- ✅ beautifulsoup4
- ✅ pandas
- ✅ psycopg2-binary
- ✅ python-dotenv

The train_models.py script uses:
- ✅ pandas, numpy, scikit-learn, joblib
- ✅ catboost
- ✅ psycopg2-binary
- ❌ **xgboost** (NOT in API requirements.txt)

**ACTION REQUIRED:** Add xgboost to `requirements.txt`:
```
xgboost==2.0.3
```

### 3. Database Connection
Scripts use environment variables for database connection. Ensure `.env` file exists in ML_Model directory OR Docker environment variables are set:

```env
POSTGRES_DB=car_prediction
POSTGRES_USER=bpr_user
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

### 4. Script Execution
The Flask API executes scripts using subprocess with detached mode:

```python
script_path = '/app/ML_Model/auto_scraper.py'
subprocess.Popen(
    ['python3', script_path, '--mode', mode],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    start_new_session=True
)
```

This means:
- Scripts run in background
- API returns immediately (202 Accepted)
- Progress tracked via database (`scraping_logs`, `model_training_run` tables)

## Deployment Steps on Raspberry Pi

### 1. Pull Latest Code
```bash
cd /home/igor/BachelorApi/BPR-BackEnd-API
git pull origin main
```

### 2. Update Requirements (if needed)
Add xgboost to `requirements.txt`:
```bash
echo "xgboost==2.0.3" >> requirements.txt
```

### 3. Rebuild Docker Images
```bash
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
```

### 4. Set Permissions
```bash
chmod -R 777 /home/igor/BachelorApi/BPR-BackEnd-ML-Model/bilbasen_scrape/
chmod -R 777 /home/igor/BachelorApi/BPR-BackEnd-API/logs/
```

### 5. Start Services
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 6. Verify Mounts
```bash
# Check backend container
docker exec bpr-flask ls -la /app/ML_Model/
# Should see: auto_scraper.py, train_models.py, etc.

docker exec bpr-flask ls -la /app/data/
# Should see: car_details.csv, images/, *.log

docker exec bpr-flask ls -la /app/app/models/
# Should see: best_model_catboost.pkl, etc.
```

### 7. Test Triggers
```bash
# Test scraper trigger
curl -X POST http://localhost:5000/api/trigger-scraping \
  -H "Content-Type: application/json" \
  -d '{"mode": "incremental"}'

# Test training trigger
curl -X POST http://localhost:5000/api/trigger-training
```

### 8. Monitor Logs
```bash
# API logs
docker logs -f bpr-flask

# Check scraper logs (inside container)
docker exec bpr-flask ls -la /app/data/*.log
docker exec bpr-flask tail -f /app/data/scraper.log
```

## Troubleshooting

### Issue: "Script not found"
**Symptom:** API returns error when triggering scripts
**Solution:** 
```bash
# Verify mount
docker exec bpr-flask ls -la /app/ML_Model/
# If empty, check docker-compose volume paths
```

### Issue: "Permission denied writing logs"
**Symptom:** Scraper can't write log files
**Solution:**
```bash
chmod -R 777 /home/igor/BachelorApi/BPR-BackEnd-ML-Model/bilbasen_scrape/
```

### Issue: "Module xgboost not found"
**Symptom:** Training script fails with import error
**Solution:**
```bash
# Add to requirements.txt and rebuild
echo "xgboost==2.0.3" >> requirements.txt
docker-compose -f docker-compose.prod.yml build --no-cache backend
docker-compose -f docker-compose.prod.yml up -d
```

### Issue: "Can't connect to database"
**Symptom:** Scripts can't access PostgreSQL
**Solution:**
- Ensure DATABASE_URL environment variable is set in docker-compose
- Use hostname `db` (Docker service name), not `localhost`
- Verify database is healthy: `docker exec bpr-postgres pg_isready`

## Next Steps

1. **Re-import Database with Complete Data:**
   ```bash
   cd /home/igor/BachelorApi/BPR-BackEnd-ML-Model
   python3 import_csv_to_db.py bilbasen_scrape/car_details.csv
   ```
   This will populate all 60+ fields with Danish format data correctly parsed.

2. **Test Frontend Triggers:**
   - Open frontend in browser
   - Navigate to Backend Health page
   - Click "Trigger Scraping" button
   - Verify scraping starts (check logs)
   - Wait for completion (several hours)
   - Check `scraping_logs` table for results

3. **Train Models:**
   - After scraping completes
   - Click "Trigger Training" button
   - Wait for training (30-60 minutes)
   - Check `model_training_run` table for results
   - Verify new model files in `app/models/`

## Summary

✅ **Completed:**
- Docker volume mounts configured for script access
- ML_Model directory mounted as `/app/ML_Model`
- Scraper data directory mounted as `/app/data` (writable)
- Both development and production docker-compose files updated

⏳ **Remaining:**
- Add xgboost to requirements.txt
- Set file permissions on Raspberry Pi
- Rebuild Docker images on Raspberry Pi
- Test script triggers from frontend
- Re-import database with complete data

🎯 **Result:**
Frontend buttons will now successfully trigger scraper and training scripts running inside Docker containers with full access to data and logs.
