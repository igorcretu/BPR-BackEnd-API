-- Migration: Add Multi-Model ML Infrastructure
-- Date: 2025-12-09

-- ============================================================================
-- 1. Add external_id and image fields to cars table
-- ============================================================================

ALTER TABLE cars ADD COLUMN IF NOT EXISTS external_id VARCHAR(50);
ALTER TABLE cars ADD COLUMN IF NOT EXISTS image_path VARCHAR(500);
ALTER TABLE cars ADD COLUMN IF NOT EXISTS image_downloaded BOOLEAN DEFAULT FALSE;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS tax DECIMAL(10,2);

CREATE INDEX IF NOT EXISTS idx_cars_external_id ON cars(external_id);

-- ============================================================================
-- 2. Create ML Models Registry Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS ml_models (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    model_type VARCHAR(50) NOT NULL,
    algorithm VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    model_file_path VARCHAR(500),
    mae DECIMAL(12,2),
    rmse DECIMAL(12,2),
    r2_score DECIMAL(6,4),
    mape DECIMAL(6,4),
    median_ae DECIMAL(12,2),
    percentile_90_error DECIMAL(12,2),
    training_time_seconds DECIMAL(10,2),
    hyperparameters JSON,
    feature_importances JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ml_models_active ON ml_models(is_active);
CREATE INDEX IF NOT EXISTS idx_ml_models_name ON ml_models(name);

-- ============================================================================
-- 3. Update price_predictions table for multi-model support
-- ============================================================================

ALTER TABLE price_predictions ADD COLUMN IF NOT EXISTS model_id VARCHAR(36);
ALTER TABLE price_predictions ADD COLUMN IF NOT EXISTS confidence DECIMAL(5,2);
ALTER TABLE price_predictions ADD COLUMN IF NOT EXISTS price_range_min DECIMAL(12,2);
ALTER TABLE price_predictions ADD COLUMN IF NOT EXISTS price_range_max DECIMAL(12,2);

CREATE INDEX IF NOT EXISTS idx_predictions_model_id ON price_predictions(model_id);

-- ============================================================================
-- 4. Create Model Training Runs Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS model_training_runs (
    id VARCHAR(36) PRIMARY KEY,
    run_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dataset_size INTEGER,
    train_size INTEGER,
    test_size INTEGER,
    training_duration_seconds DECIMAL(10,2),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    models_trained JSON,
    best_model_id VARCHAR(36),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_training_runs_run_date ON model_training_runs(run_date);
CREATE INDEX IF NOT EXISTS idx_training_runs_status ON model_training_runs(status);

-- ============================================================================
-- 5. Create Model Comparison Metrics Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS model_comparison_metrics (
    id VARCHAR(36) PRIMARY KEY,
    training_run_id VARCHAR(36),
    model_id VARCHAR(36),
    mae DECIMAL(12,2),
    rmse DECIMAL(12,2),
    r2_score DECIMAL(6,4),
    mape DECIMAL(6,4),
    median_ae DECIMAL(12,2),
    percentile_90_error DECIMAL(12,2),
    mae_under_100k DECIMAL(12,2),
    mae_100k_to_300k DECIMAL(12,2),
    mae_300k_to_500k DECIMAL(12,2),
    mae_over_500k DECIMAL(12,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_comparison_metrics_run ON model_comparison_metrics(training_run_id);
CREATE INDEX IF NOT EXISTS idx_comparison_metrics_model ON model_comparison_metrics(model_id);

-- ============================================================================
-- 6. Update scraping_logs table
-- ============================================================================

ALTER TABLE scraping_logs ADD COLUMN IF NOT EXISTS cars_new INTEGER DEFAULT 0;
ALTER TABLE scraping_logs ADD COLUMN IF NOT EXISTS cars_updated INTEGER DEFAULT 0;
ALTER TABLE scraping_logs ADD COLUMN IF NOT EXISTS highest_external_id VARCHAR(50);
ALTER TABLE scraping_logs ADD COLUMN IF NOT EXISTS scraping_mode VARCHAR(20) DEFAULT 'full';
ALTER TABLE scraping_logs ADD COLUMN IF NOT EXISTS images_downloaded INTEGER DEFAULT 0;
COMMENT ON TABLE model_training_runs IS 'History of model training executions';
COMMENT ON TABLE model_comparison_metrics IS 'Detailed comparison metrics for each model in each training run';
COMMENT ON COLUMN cars.external_id IS 'Bilbasen listing ID for tracking and incremental scraping';
COMMENT ON COLUMN cars.image_path IS 'Relative path to downloaded car image';
