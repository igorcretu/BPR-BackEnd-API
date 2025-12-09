# Phase 2: Scraper Modifications - COMPLETED ✅

## Overview
Phase 2 focused on creating upload tooling, auto-scraper with incremental scraping, and image API endpoints.

## Files Created

### 1. **upload_new_scraper.ipynb** (CREATED)
Complete Jupyter notebook for initial data upload from bilbasen_scraper_pi.py output.

**Features:**
- Maps 55+ CSV columns (Danish) to database columns (English)
- Handles external_id as primary deduplication key
- Parses price strings ("38.900 kr." → 38900.0)
- Stores image_path (relative), sets image_downloaded=False
- Extracts horsepower, torque from combined strings
- Converts mileage, numeric specs with proper handling
- UPSERT logic: INSERT new or UPDATE existing based on external_id
- Batch uploads (1000 records per batch)
- Comprehensive data quality reporting
- Verification queries post-upload

**Column Mappings:**
```
CSV (Scraper) → Database
├── external_id → external_id (NEW)
├── price → price (cleaned)
├── details_model_year → model_year, year
├── details_first_registration → first_registration
├── details_mileage_km / mileage_km_numeric → mileage
├── details_fuel_type → fuel_type
├── details_geartype / attr_gear_type → transmission
├── details_power_hp_nm → horsepower, torque_nm (extracted)
├── details_range_km → range_km (EV)
├── details_battery_capacity_kwh → battery_capacity (EV)
├── model_body_type → body_type
├── model_weight_kg / attr_weight_kg → weight
├── details_periodic_tax → periodic_tax, tax (NEW)
├── image_filename → image_path (NEW)
└── ... 40+ more fields
```

**Helper Functions:**
- `clean_price()`: Remove "kr.", dots, convert to float
- `extract_horsepower()`: Parse "150 HK / 110 kW" → 150
- `extract_torque()`: Parse "... / 250 Nm" → 250
- `extract_mileage()`: "150.000 km" → 150000
- `parse_date()`: ISO format parsing
- `parse_boolean()`: Danish yes/no conversion
- `extract_co2()`: "120 g/km" formatting

**Usage:**
```python
# Run all cells in order
# Adjust DB credentials in cell 1
# CSV file: bilbasen_scrape/car_details.csv
# Output: UPSERT to cars table
```

### 2. **auto_scraper.py** (CREATED)
Production-ready incremental scraper script.

**Features:**
- **Incremental Mode**: Query max(external_id), scrape newest-first, stop at known ID
- **Full Mode**: Complete scrape (for initial setup or periodic refresh)
- Database integration: UPSERT cars, log scraping runs
- Image downloads: Checks for existing, saves to bilbasen_scrape_auto/images/
- Statistics tracking: cars_new, cars_updated, images_downloaded, highest_external_id
- Error handling: Retry logic, graceful failures, comprehensive logging
- Scraping logs: Records to scraping_logs table with detailed stats
- Rate limiting: 1.5-3.5s delays between requests

**Architecture:**
```
AutoScraper
├── connect_db() → PostgreSQL connection
├── get_max_external_id() → Query highest external_id from database
├── scrape_listing_page(page) → Extract listings from search results
├── scrape_listing_details(url, external_id) → Full car details
├── download_image(image_url, external_id) → Save image locally
├── check_car_exists(external_id) → Check for duplicates
├── upsert_car(car_data) → INSERT or UPDATE car
└── log_scraping_run() → Record stats to scraping_logs
```

**Incremental Scraping Logic:**
```python
# 1. Get max external_id from database
max_id = SELECT MAX(external_id::bigint) FROM cars  # e.g., 6093980

# 2. Scrape Bilbasen sorted by date descending
url = "https://www.bilbasen.dk/brugt/bil?sortby=date&sortorder=desc"

# 3. For each listing:
if int(listing_external_id) <= int(max_id):
    break  # Stop, we've reached known listings

# 4. Process new listings
scrape_details(listing_url)
download_image(image_url)
upsert_car(data)

# 5. Log results
INSERT INTO scraping_logs (
    scraping_mode='incremental',
    highest_external_id=...,
    cars_new=...,
    cars_updated=...,
    images_downloaded=...
)
```

**Usage:**
```bash
# Incremental scrape (default)
python auto_scraper.py --mode incremental

# Full scrape
python auto_scraper.py --mode full

# Skip images
python auto_scraper.py --no-images
```

**Logging:**
- Console: INFO level
- File: auto_scraper.log (all levels)
- Database: scraping_logs table

### 3. **Image API Endpoints** (ADDED to app/main.py)

**Endpoint 1: GET /api/cars/{car_id}/image**
```python
# Get image by car database ID
# Returns: JPEG image file
# Error 404: If image not available or file not found
```

**Endpoint 2: GET /api/images/{external_id}**
```python
# Get image by Bilbasen listing ID (external_id)
# Returns: JPEG image file
# Error 404: If image not available or file not found
```

**Implementation:**
```python
@app.route('/api/cars/<car_id>/image', methods=['GET'])
def get_car_image(car_id):
    car = Car.query.get_or_404(car_id)
    if not car.image_path or not car.image_downloaded:
        abort(404, description="Image not available")
    
    image_full_path = os.path.join(os.path.dirname(__file__), '..', car.image_path)
    if not os.path.exists(image_full_path):
        abort(404, description="Image file not found")
    
    return send_file(image_full_path, mimetype='image/jpeg')
```

**Frontend Integration:**
```typescript
// Try real car image first, fallback to Wikimedia
const imageUrl = `${API_BASE_URL}/api/cars/${car.id}/image`;
<img src={imageUrl} onError={(e) => { 
  e.currentTarget.src = wikimediaFallback; 
}} />
```

### 4. **Cron/Scheduler Setup Scripts** (CREATED)

**For Linux/Raspberry Pi: setup_auto_scraper_cron.sh**
```bash
# Sets up cron job: Every 2 days at 2:00 AM
0 2 */2 * * cd /path/to/project && python3 auto_scraper.py --mode incremental

# Install:
chmod +x setup_auto_scraper_cron.sh
./setup_auto_scraper_cron.sh

# View cron jobs:
crontab -l

# Manual test:
python3 auto_scraper.py --mode incremental
```

**For Windows: setup_auto_scraper_task.ps1**
```powershell
# Sets up Windows Task Scheduler: Every 2 days at 2:00 AM
# Run as Administrator:
.\setup_auto_scraper_task.ps1

# View task:
Get-ScheduledTask -TaskName BPR_AutoScraper

# Run now:
Start-ScheduledTask -TaskName BPR_AutoScraper
```

## Image Storage Architecture

### Raspberry Pi Production Setup
```
/home/pi/car_images/          # Physical storage (large capacity drive)
    ├── 6093980.jpg
    ├── 6093981.jpg
    └── ...

/app/static/car_images/       # Symlink for Flask to serve
    → /home/pi/car_images/

Database:
    image_path: "bilbasen_scrape/images/6093980.jpg"  # Relative path
    image_downloaded: true
```

**Create symlink on Raspberry Pi:**
```bash
ln -s /home/pi/car_images /app/static/car_images
```

### Development Setup
```
BackEnd/ML_Model/
    ├── bilbasen_scrape/images/       # From original scraper
    └── bilbasen_scrape_auto/images/  # From auto_scraper
```

## Incremental Scraping Workflow

### First Run (No data in database)
```
1. max_external_id = None (database empty)
2. Scrape all pages (behaves like full mode)
3. Download all images
4. Insert all cars
5. Log: scraping_mode='incremental', cars_new=102000, highest_external_id=6100000
```

### Subsequent Runs (Every 2 days)
```
1. max_external_id = 6100000 (from database)
2. Scrape page 1 (newest listings)
   - Listing 6100150: New, scrape details
   - Listing 6100120: New, scrape details
   - Listing 6100050: New, scrape details
   - Listing 6099990: ≤ max_id, STOP
3. Total: 3 new cars, 0 updated
4. Download 3 images
5. Log: scraping_mode='incremental', cars_new=3, highest_external_id=6100150
```

### Edge Cases Handled
- **Duplicate external_ids in scrape**: UPSERT updates existing
- **Missing images**: Skips download, image_downloaded=False
- **Network failures**: Logged, continue with next listing
- **Database errors**: Rollback transaction, log error
- **Empty pages**: Stops gracefully

## Data Quality Features

### Upload Notebook Validation
```python
# Check required fields
required = ['external_id', 'brand', 'model', 'price']
missing_count = df[required].isna().sum()

# Drop rows with missing required fields
clean_df = clean_df.dropna(subset=required)

# Report
print(f"Dropped {before - after} rows with missing required fields")
```

### Auto-Scraper Validation
```python
# External ID validation
external_id = extract_external_id(listing_url)
if not external_id:
    continue  # Skip invalid listing

# Unique constraint enforcement
ON CONFLICT (external_id) DO UPDATE SET ...
```

## Performance Considerations

### Batch Processing
- Upload notebook: 1000 records per batch using `execute_values()`
- Auto-scraper: Single car UPSERT (real-time processing)

### Rate Limiting
```python
# Between page requests: 2-4 seconds
time.sleep(random.uniform(2, 4))

# Between car details: 1.5-3.5 seconds
time.sleep(random.uniform(1.5, 3.5))
```

### Image Handling
- Check if file exists before downloading
- Skip already downloaded images
- Parallel-friendly: Can run multiple scrapers with different filters

### Database Optimization
```sql
-- Indexes for fast lookups
CREATE UNIQUE INDEX ON cars(external_id);
CREATE INDEX ON cars(brand);
CREATE INDEX ON cars(fuel_type);
CREATE INDEX ON scraping_logs(scraping_mode);
```

## Testing Checklist

### Upload Notebook
- ⬜ Load CSV successfully
- ⬜ Clean price strings correctly
- ⬜ Parse horsepower/torque from combined field
- ⬜ Handle missing values gracefully
- ⬜ UPSERT without duplicates
- ⬜ Verify row counts before/after
- ⬜ Check external_id uniqueness

### Auto-Scraper
- ⬜ Connect to database successfully
- ⬜ Query max external_id correctly
- ⬜ Scrape listing pages without errors
- ⬜ Stop at known external_id (incremental)
- ⬜ Download images successfully
- ⬜ UPSERT cars without duplicates
- ⬜ Log scraping run with correct stats
- ⬜ Handle network failures gracefully

### Image API
- ⬜ GET /api/cars/{car_id}/image returns image
- ⬜ GET /api/images/{external_id} returns image
- ⬜ Return 404 for missing images
- ⬜ Return 404 for invalid IDs
- ⬜ Serve correct MIME type (image/jpeg)

### Cron/Scheduler
- ⬜ Cron job installs successfully
- ⬜ Task runs at scheduled time
- ⬜ Logs written to correct file
- ⬜ Manual run works correctly

## Next Steps (Phase 3: Multi-Model ML)

1. **Create train_models.py orchestration script**
   - Train multiple models: XGBoost, CatBoost, Ridge, Lasso, ElasticNet, LSTM, GRU
   - Extract real confidence scores from each model
   - Calculate comparison metrics (MAE by price/fuel/year, inference time)
   - Save models to files, register in ml_models table
   - Insert training_run and comparison_metrics records

2. **Implement linear_models.py**
   - Ridge Regression
   - Lasso Regression
   - ElasticNet
   - Extract prediction intervals for confidence

3. **Implement rnn_models.py**
   - LSTM model
   - GRU model
   - Time-series features for price trends
   - Confidence estimation from prediction variance

4. **Add post-scrape trigger**
   - Auto-scraper calls train_models.py after successful scrape
   - Retrain only if significant new data (e.g., >100 new cars)

## Notes
- Auto-scraper runs independently of original bilbasen_scraper_pi.py
- Both scrapers can coexist (different output directories)
- Image paths are relative, easily portable
- Database uses external_id as primary deduplication mechanism
- All timestamps in UTC for consistency
