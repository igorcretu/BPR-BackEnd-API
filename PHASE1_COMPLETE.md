# Phase 1: Database Schema - COMPLETED ✅

## Overview
Phase 1 focused on updating the database schema and ORM models to support multi-model ML infrastructure, incremental scraping, real car images, and comprehensive model comparison metrics.

## Files Modified

### 1. **migrations/add_ml_models_schema.sql** (CREATED)
Complete database migration script with:
- **ALTER cars**: Added `external_id` (unique, indexed), `image_path`, `image_downloaded`, `tax`
- **CREATE ml_models**: Model registry with performance metrics, hyperparameters, feature importances
- **CREATE model_training_runs**: Training execution tracking with dataset info, timing, status
- **CREATE model_comparison_metrics**: Detailed metrics per model (overall + segmented)
- **ALTER price_predictions**: Added `model_id` (FK), `confidence`, `price_range_min`, `price_range_max`
- **ALTER scraping_logs**: Added `highest_external_id`, `scraping_mode`, `cars_new`, `cars_updated`, `images_downloaded`
- **CREATE VIEW model_performance_history**: Historical analysis view
- **INSERT statements**: Initial XGBoost/CatBoost entries

**To run migration:**
```bash
psql -U postgres -d bpr_cars -f migrations/add_ml_models_schema.sql
```

### 2. **app/models.py** (UPDATED)

#### Updated Classes:

**Car** - Added new columns:
- `external_id`: String(50), unique, indexed - Bilbasen listing ID for incremental scraping
- `tax`: Numeric(10,2) - Periodic vehicle tax amount
- `image_path`: String(500) - Path to downloaded car image
- `image_downloaded`: Boolean - Flag indicating if image was successfully downloaded
- Updated `to_dict()` to expose: external_id, tax, image_path

**PricePrediction** - Added new columns:
- `model_id`: FK to ml_models - Associates prediction with specific ML model
- `confidence`: Numeric(5,2) - Real model confidence score (not calculated)
- `price_range_min`: Numeric(12,2) - Lower bound of predicted price range
- `price_range_max`: Numeric(12,2) - Upper bound of predicted price range
- Updated `to_dict()` to expose: model_id, confidence, price_range_min, price_range_max

**ScrapingLog** - Added new columns:
- `highest_external_id`: String(50) - Highest external_id scraped in this run
- `scraping_mode`: String(20) - 'full' or 'incremental'
- `cars_new`: Integer - Count of newly added cars
- `cars_updated`: Integer - Count of updated existing cars
- `images_downloaded`: Integer - Count of images downloaded
- Updated `to_dict()` to expose all new fields

#### New ORM Classes Created:

**MLModel** - Model registry
- Stores: name, type, algorithm, version, is_active, model_file_path
- Performance metrics: mae, rmse, r2_score, mape, median_ae, percentile_90_error, training_time_seconds
- Configuration: hyperparameters (JSON), feature_importances (JSON)
- Relationships: predictions, comparison_metrics
- Complete `to_dict()` method for API responses

**ModelTrainingRun** - Training execution history
- Stores: run_date, dataset_size, train_size, test_size, training_duration_seconds
- Status tracking: status, models_trained (JSON), best_model_id, notes
- Relationship: best_model (FK to MLModel)
- Complete `to_dict()` method for API responses

**ModelComparisonMetrics** - Detailed comparison data
- Overall metrics: overall_mae, overall_rmse, overall_r2, overall_mape
- Price range metrics: mae_under_100k, mae_100k_300k, mae_300k_500k, mae_over_500k
- Fuel type metrics: mae_petrol, mae_diesel, mae_electric, mae_hybrid
- Year range metrics: mae_pre_2010, mae_2010_2015, mae_2015_2020, mae_post_2020
- Performance: avg_inference_time_ms, confidence_calibration_score
- Relationships: training_run, ml_model
- Complete `to_dict()` method for API responses

## Schema Validation
✅ No Python syntax errors in models.py
✅ All ORM classes have proper relationships
✅ All columns match migration SQL schema
✅ All to_dict() methods include new fields

## Architecture Highlights

### Multi-Model Support
- Each prediction linked to specific model via `model_id` FK
- Model registry tracks all models (XGBoost, CatBoost, Ridge, Lasso, ElasticNet, LSTM, GRU)
- Active/inactive model flags for easy model management

### Incremental Scraping
- `external_id` in cars table enables deduplication
- `highest_external_id` in scraping_logs tracks progress
- `scraping_mode` distinguishes full vs incremental scrapes

### Real Model Confidence
- `confidence` field stores actual model confidence scores
- `price_range_min/max` provides prediction uncertainty ranges
- No more hardcoded or calculated confidence values

### Comprehensive Metrics
- Segmented performance by price range, fuel type, year
- Training execution history with timing and dataset info
- Historical view for trend analysis

### Image Management
- `image_path` stores relative path to downloaded images
- `image_downloaded` flag tracks download status
- `images_downloaded` count in scraping_logs for monitoring

## Next Steps (Phase 2: Scraper Modifications)

1. **Update upload.ipynb**
   - Map scraper CSV columns to database columns
   - Handle external_id as deduplication key
   - Parse price strings and handle missing values
   - Store image_path (relative), set image_downloaded=False

2. **Create auto_scraper.py**
   - Query max(external_id) from database
   - Scrape newest-first until hitting known ID
   - Download new car details + images
   - Update scraping_logs with incremental stats

3. **Create image API endpoints**
   - /api/cars/{car_id}/image
   - /api/images/{external_id}.jpg
   - Serve from /app/static/car_images/

## Database Migration Checklist

Before running migration:
- ✅ Backup current database
- ✅ Review migration SQL for correctness
- ✅ Test in development environment first

After migration:
- ⬜ Verify all tables created
- ⬜ Check foreign key constraints
- ⬜ Test view query performance
- ⬜ Insert initial model records if not auto-created
- ⬜ Update API code to use new ORM models

## Notes
- All numeric columns properly sized (price: 12,2 for billions DKK)
- All indexes on foreign keys and frequently queried columns
- JSON columns for flexible storage of hyperparameters and feature importances
- Timestamps on all tables for audit trail
- Default values for boolean and status columns
