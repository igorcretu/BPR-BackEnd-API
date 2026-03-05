#!/bin/bash

# Bachelor Project - Nightly Update Script
# Runs scraping followed by model training at 2 AM daily

# Configuration
PROJECT_DIR="/home/igor/BachelorApi"
SCRAPER_DIR="/home/igor/BachelorApi/BPR-BackEnd-API/app/scraping"
API_DIR="/home/igor/BachelorApi/BPR-BackEnd-API"
LOG_DIR="$PROJECT_DIR/BPR-BackEnd-API/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/nightly_update_$TIMESTAMP.log"
SECONDS=0

# Parse command line arguments
DRY_RUN=false
SKIP_SCRAPING=false
SKIP_TRAINING=false
SKIP_RESTART=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true ;;
        --skip-scraping) SKIP_SCRAPING=true ;;
        --skip-training) SKIP_TRAINING=true ;;
        --skip-restart) SKIP_RESTART=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Start logging
echo "========================================" | tee -a "$LOG_FILE"
echo "🌙 Nightly Update Started: $(date)" | tee -a "$LOG_FILE"
if [ "$DRY_RUN" = true ]; then
    echo "🔍 DRY RUN MODE - No actual changes will be made" | tee -a "$LOG_FILE"
fi
echo "========================================" | tee -a "$LOG_FILE"

# Function to log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to handle errors
handle_error() {
    log "❌ ERROR: $1"
    log "⚠️  Nightly update failed. Check logs: $LOG_FILE"
    exit 1
}

# ============================================================================
# STEP 1: WEB SCRAPING
# ============================================================================

if [ "$SKIP_SCRAPING" = true ]; then
    log "⏭️  Skipping scraping step (--skip-scraping flag)"
else
    log "📊 Step 1: Starting web scraping..."
    cd "$SCRAPER_DIR" || handle_error "Cannot access scraper directory: $SCRAPER_DIR"

    # Check if scraper is already running
    if pgrep -f "bilbasen_incremental.py" > /dev/null; then
        log "⚠️  Scraper is already running. Skipping scraping step."
    else
        # Install missing dependencies if needed
        MISSING_DEPS=()
        for pkg in psycopg2 pandas requests bs4 playwright; do
            if ! python3 -c "import $pkg" 2>/dev/null; then
                case $pkg in
                    psycopg2) MISSING_DEPS+=("psycopg2-binary") ;;
                    bs4) MISSING_DEPS+=("beautifulsoup4") ;;
                    *) MISSING_DEPS+=("$pkg") ;;
                esac
            fi
        done
        
        if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
            log "Installing missing dependencies: ${MISSING_DEPS[*]}"
            if [ "$DRY_RUN" = false ]; then
                pip3 install --break-system-packages "${MISSING_DEPS[@]}" 2>&1 | tee -a "$LOG_FILE"
                
                # Install Playwright browsers if playwright was just installed
                if [[ " ${MISSING_DEPS[@]} " =~ " playwright " ]]; then
                    log "Installing Playwright browsers..."
                    python3 -m playwright install chromium 2>&1 | tee -a "$LOG_FILE"
                fi
            else
                log "🔍 DRY RUN: Would install ${MISSING_DEPS[*]}"
                if [[ " ${MISSING_DEPS[@]} " =~ " playwright " ]]; then
                    log "🔍 DRY RUN: Would install Playwright browsers"
                fi
            fi
        fi
        
        # Run the scraper
        log "Running incremental scraper..."
        if [ "$DRY_RUN" = false ]; then
            # Set environment variables for database connection
            export POSTGRES_HOST="localhost"
            export POSTGRES_PORT="5432"
            export POSTGRES_DB="car_prediction"
            export POSTGRES_USER="bpr_user"
            export POSTGRES_PASSWORD="postgres"
            
            python3 "$SCRAPER_DIR/bilbasen_incremental.py" 2>&1 | tee -a "$LOG_FILE"
            SCRAPER_EXIT_CODE=${PIPESTATUS[0]}

            if [ $SCRAPER_EXIT_CODE -ne 0 ]; then
                log "⚠️  Scraper exited with code $SCRAPER_EXIT_CODE (may be normal if no new listings)"
            else
                log "✅ Scraping completed successfully"
            fi

            # Get scraping statistics
            NEW_LISTINGS=$(grep -oP "(\d+) new (listings|cars)" "$LOG_FILE" | tail -1 || echo "0 new listings")
            log "📈 Scraping results: $NEW_LISTINGS"
        else
            log "🔍 DRY RUN: Would run scraper"
        fi
    fi
fi

# ============================================================================
# STEP 2: MODEL TRAINING
# ============================================================================

if [ "$SKIP_TRAINING" = true ]; then
    log "⏭️  Skipping training step (--skip-training flag)"
else
    log "🤖 Step 2: Starting model training..."

    # Check if training is already running
    if pgrep -f "train_models.py" > /dev/null; then
        log "⚠️  Training is already running. Skipping training step."
    else
        # Install missing training dependencies if needed
        log "Checking training dependencies..."
        MISSING_TRAIN_DEPS=()
        for pkg in numpy pandas scikit-learn xgboost catboost lightgbm psycopg2 joblib dotenv; do
            if ! python3 -c "import ${pkg/scikit-learn/sklearn}" 2>/dev/null; then
                case $pkg in
                    psycopg2) MISSING_TRAIN_DEPS+=("psycopg2-binary") ;;
                    dotenv) MISSING_TRAIN_DEPS+=("python-dotenv") ;;
                    *) MISSING_TRAIN_DEPS+=("$pkg") ;;
                esac
            fi
        done
        
        if [ ${#MISSING_TRAIN_DEPS[@]} -gt 0 ]; then
            log "Installing missing training dependencies: ${MISSING_TRAIN_DEPS[*]}"
            if [ "$DRY_RUN" = false ]; then
                pip3 install --break-system-packages "${MISSING_TRAIN_DEPS[@]}" 2>&1 | tee -a "$LOG_FILE"
            else
                log "🔍 DRY RUN: Would install ${MISSING_TRAIN_DEPS[*]}"
            fi
        fi
        
        # Trigger training via API endpoint
        log "Triggering model training via API..."
        if [ "$DRY_RUN" = false ]; then
            TRAINING_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST http://localhost:5000/api/trigger-training)
            HTTP_STATUS=$(echo "$TRAINING_RESPONSE" | grep -oP 'HTTP_STATUS:\K\d+')
            
            if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "202" ]; then
                log "✅ Training triggered successfully (HTTP $HTTP_STATUS)"
                log "Response: $(echo "$TRAINING_RESPONSE" | sed '/HTTP_STATUS/d')"
                
                # Wait for training to complete (check every 30 seconds, max 2 hours)
                TRAINING_TIMEOUT=240  # 2 hours in 30-second intervals
                TRAINING_COUNTER=0
                
                while [ $TRAINING_COUNTER -lt $TRAINING_TIMEOUT ]; do
                    sleep 30
                    if ! pgrep -f "train_models.py" > /dev/null; then
                        log "✅ Model training completed"
                        break
                    fi
                    TRAINING_COUNTER=$((TRAINING_COUNTER + 1))
                    if [ $((TRAINING_COUNTER % 10)) -eq 0 ]; then
                        log "Training still in progress... ($((TRAINING_COUNTER / 2)) minutes elapsed)"
                    fi
                done
                
                if [ $TRAINING_COUNTER -ge $TRAINING_TIMEOUT ]; then
                    log "⚠️  Training timeout reached (2 hours). Training may still be running."
                fi
            else
                log "⚠️  Failed to trigger training (HTTP $HTTP_STATUS)"
                log "Response: $(echo "$TRAINING_RESPONSE" | sed '/HTTP_STATUS/d')"
            fi
        else
            log "🔍 DRY RUN: Would trigger training"
        fi
    fi
fi

# ============================================================================
# STEP 3: RESTART API (to reload new models)
# ============================================================================

if [ "$SKIP_RESTART" = true ]; then
    log "⏭️  Skipping API restart (--skip-restart flag)"
else
    log "🔄 Step 3: Restarting Flask API to reload models..."
    cd "$API_DIR" || handle_error "Cannot access API directory: $API_DIR"

    if [ "$DRY_RUN" = false ]; then
        # Restart the Docker container
        log "Restarting bpr-flask container..."
        docker restart bpr-flask 2>&1 | tee -a "$LOG_FILE"

        # Wait for container to be healthy
        log "Waiting for API to become healthy..."
        HEALTH_TIMEOUT=60
        HEALTH_COUNTER=0

        while [ $HEALTH_COUNTER -lt $HEALTH_TIMEOUT ]; do
            sleep 2
            CONTAINER_STATUS=$(docker inspect --format='{{.State.Health.Status}}' bpr-flask 2>/dev/null || echo "unknown")
            
            if [ "$CONTAINER_STATUS" = "healthy" ]; then
                log "✅ API is healthy and ready"
                break
            fi
            
            HEALTH_COUNTER=$((HEALTH_COUNTER + 1))
            
            if [ $((HEALTH_COUNTER % 15)) -eq 0 ]; then
                log "Waiting for health check... ($HEALTH_COUNTER seconds elapsed, status: $CONTAINER_STATUS)"
            fi
        done

        if [ $HEALTH_COUNTER -ge $HEALTH_TIMEOUT ]; then
            log "⚠️  Health check timeout. API may not be ready."
        else
            # Verify API is actually responding
            API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health)
            if [ "$API_RESPONSE" = "200" ]; then
                log "✅ API health endpoint responding (HTTP 200)"
            else
                log "⚠️  API health check returned HTTP $API_RESPONSE"
            fi
        fi
    else
        log "🔍 DRY RUN: Would restart bpr-flask container"
    fi
fi

# ============================================================================
# STEP 4: CLEANUP AND SUMMARY
# ============================================================================

log "🧹 Step 4: Cleanup old logs..."

# Keep only last 30 days of logs
find "$LOG_DIR" -name "nightly_update_*.log" -mtime +30 -delete
log "Old logs cleaned up (kept last 30 days)"

# Calculate duration
DURATION=$SECONDS
log "⏱️  Total duration: $((DURATION / 60)) minutes and $((DURATION % 60)) seconds"

# Get final model status
log "📊 Checking final model status..."
MODEL_STATUS=$(curl -s http://localhost:5000/api/ml/health 2>/dev/null | grep -oP '"active_models":\K\d+' || echo "unknown")

# Final summary
log "========================================="
log "🎉 Nightly Update Completed Successfully!"
log "📊 Active ML models: $MODEL_STATUS"
log "📁 Full log: $LOG_FILE"
log "========================================="

exit 0
