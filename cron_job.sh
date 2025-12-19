#!/bin/bash

# Bachelor Project - Nightly Update Script
# Runs scraping followed by model training at 2 AM daily

# Configuration
PROJECT_DIR="/home/igor/BachelorApi"
SCRAPER_DIR="/home/igor/BachelorScraper"  # Adjust to your scraper location
LOG_DIR="$PROJECT_DIR/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/nightly_update_$TIMESTAMP.log"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Start logging
echo "========================================" | tee -a "$LOG_FILE"
echo "🌙 Nightly Update Started: $(date)" | tee -a "$LOG_FILE"
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

log "📊 Step 1: Starting web scraping..."
cd "$SCRAPER_DIR" || handle_error "Cannot access scraper directory: $SCRAPER_DIR"

# Activate virtual environment if you have one
if [ -d "venv" ]; then
    log "Activating Python virtual environment..."
    source venv/bin/activate || handle_error "Cannot activate virtual environment"
fi

# Run the scraper (adjust the command to match your scraper script)
log "Running incremental scraper..."
python3 scraper.py --incremental 2>&1 | tee -a "$LOG_FILE"
SCRAPER_EXIT_CODE=${PIPESTATUS[0]}

if [ $SCRAPER_EXIT_CODE -ne 0 ]; then
    handle_error "Scraper failed with exit code $SCRAPER_EXIT_CODE"
fi

log "✅ Scraping completed successfully"

# Get scraping statistics
NEW_LISTINGS=$(grep -o "new listings" "$LOG_FILE" | wc -l || echo "0")
log "📈 New listings collected: $NEW_LISTINGS"

# ============================================================================
# STEP 2: MODEL TRAINING
# ============================================================================

log "🤖 Step 2: Starting model training..."
cd "$PROJECT_DIR" || handle_error "Cannot access project directory: $PROJECT_DIR"

# Activate virtual environment if different from scraper
if [ -d "venv" ]; then
    log "Activating Python virtual environment..."
    source venv/bin/activate || handle_error "Cannot activate virtual environment"
fi

# Run model training (adjust the command to match your training script)
log "Training models with updated dataset..."
python3 train_models.py 2>&1 | tee -a "$LOG_FILE"
TRAINING_EXIT_CODE=${PIPESTATUS[0]}

if [ $TRAINING_EXIT_CODE -ne 0 ]; then
    handle_error "Model training failed with exit code $TRAINING_EXIT_CODE"
fi

log "✅ Model training completed successfully"

# ============================================================================
# STEP 3: RESTART API (Optional - if models need to be reloaded)
# ============================================================================

log "🔄 Step 3: Restarting Flask API..."

# Option A: If using systemd
# sudo systemctl restart bpr-api.service

# Option B: If using Docker
# cd "$PROJECT_DIR" && docker-compose restart backend

# Option C: If using PM2 or similar
# pm2 restart bpr-api

# Option D: Simple restart (adjust to your setup)
if pgrep -f "flask run" > /dev/null; then
    log "Stopping existing Flask process..."
    pkill -f "flask run"
    sleep 2
fi

# Uncomment and adjust based on your deployment method
# log "Starting Flask API..."
# cd "$PROJECT_DIR" && nohup python3 app.py >> "$LOG_DIR/flask.log" 2>&1 &

log "✅ API restart completed"

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

# Final summary
log "========================================="
log "🎉 Nightly Update Completed Successfully!"
log "📊 New listings: $NEW_LISTINGS"
log "📁 Full log: $LOG_FILE"
log "========================================="

exit 0