-- Clean Migration for ML Infrastructure
-- This migration is idempotent and safe to run multiple times

-- Step 1: Add columns to cars table (one at a time)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cars' AND column_name='external_id') THEN
        ALTER TABLE cars ADD COLUMN external_id VARCHAR(50);
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cars' AND column_name='image_path') THEN
        ALTER TABLE cars ADD COLUMN image_path VARCHAR(500);
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cars' AND column_name='image_downloaded') THEN
        ALTER TABLE cars ADD COLUMN image_downloaded BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cars' AND column_name='tax') THEN
        ALTER TABLE cars ADD COLUMN tax DECIMAL(10,2);
    END IF;
END $$;

-- Step 2: Create ml_models table
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

-- Step 3: Create model_training_runs table
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

-- Step 4: Create model_comparison_metrics table
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

-- Step 5: Add columns to price_predictions table
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='price_predictions' AND column_name='model_id') THEN
        ALTER TABLE price_predictions ADD COLUMN model_id VARCHAR(36);
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='price_predictions' AND column_name='confidence') THEN
        ALTER TABLE price_predictions ADD COLUMN confidence DECIMAL(5,2);
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='price_predictions' AND column_name='price_range_min') THEN
        ALTER TABLE price_predictions ADD COLUMN price_range_min DECIMAL(12,2);
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='price_predictions' AND column_name='price_range_max') THEN
        ALTER TABLE price_predictions ADD COLUMN price_range_max DECIMAL(12,2);
    END IF;
END $$;

-- Step 6: Add columns to scraping_logs table
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='scraping_logs' AND column_name='cars_new') THEN
        ALTER TABLE scraping_logs ADD COLUMN cars_new INTEGER DEFAULT 0;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='scraping_logs' AND column_name='cars_updated') THEN
        ALTER TABLE scraping_logs ADD COLUMN cars_updated INTEGER DEFAULT 0;
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='scraping_logs' AND column_name='highest_external_id') THEN
        ALTER TABLE scraping_logs ADD COLUMN highest_external_id VARCHAR(50);
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='scraping_logs' AND column_name='scraping_mode') THEN
        ALTER TABLE scraping_logs ADD COLUMN scraping_mode VARCHAR(20) DEFAULT 'full';
    END IF;
END $$;

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='scraping_logs' AND column_name='images_downloaded') THEN
        ALTER TABLE scraping_logs ADD COLUMN images_downloaded INTEGER DEFAULT 0;
    END IF;
END $$;

-- Step 7: Create indexes (will only create if they don't exist)
CREATE INDEX IF NOT EXISTS idx_cars_external_id ON cars(external_id);
CREATE INDEX IF NOT EXISTS idx_ml_models_active ON ml_models(is_active);
CREATE INDEX IF NOT EXISTS idx_ml_models_name ON ml_models(name);
CREATE INDEX IF NOT EXISTS idx_predictions_model_id ON price_predictions(model_id);
CREATE INDEX IF NOT EXISTS idx_training_runs_run_date ON model_training_runs(run_date);
CREATE INDEX IF NOT EXISTS idx_training_runs_status ON model_training_runs(status);
CREATE INDEX IF NOT EXISTS idx_comparison_metrics_run ON model_comparison_metrics(training_run_id);
CREATE INDEX IF NOT EXISTS idx_comparison_metrics_model ON model_comparison_metrics(model_id);
