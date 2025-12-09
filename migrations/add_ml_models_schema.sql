-- Migration: Add Multi-Model ML Infrastructure
-- Date: 2025-12-09

-- ============================================================================
-- 1. Add external_id and image fields to cars table
-- ============================================================================

ALTER TABLE cars ADD COLUMN IF NOT EXISTS external_id VARCHAR(50) UNIQUE;
CREATE INDEX IF NOT EXISTS idx_cars_external_id ON cars(external_id);

ALTER TABLE cars ADD COLUMN IF NOT EXISTS image_path VARCHAR(500);
ALTER TABLE cars ADD COLUMN IF NOT EXISTS image_downloaded BOOLEAN DEFAULT FALSE;
ALTER TABLE cars ADD COLUMN IF NOT EXISTS tax DECIMAL(10,2);

-- ============================================================================
-- 2. Create ML Models Registry Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS ml_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    model_type VARCHAR(50) NOT NULL, -- 'linear', 'tree', 'rnn', 'ensemble'
    algorithm VARCHAR(50) NOT NULL, -- 'ridge', 'lasso', 'xgboost', 'lstm', etc.
    version VARCHAR(50) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Performance metrics
    mae DECIMAL(10,2),
    rmse DECIMAL(10,2),
    r2_score DECIMAL(5,4),
    mape DECIMAL(5,2),
    
    -- Training info
    training_samples INTEGER,
    training_duration_seconds INTEGER,
    trained_at TIMESTAMP,
    
    -- Metadata
    hyperparameters JSONB,
    feature_names JSONB,
    feature_importances JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_model_version UNIQUE (name, version)
);

CREATE INDEX idx_ml_models_active ON ml_models(is_active);
CREATE INDEX idx_ml_models_type ON ml_models(model_type);
CREATE INDEX idx_ml_models_trained_at ON ml_models(trained_at);

-- ============================================================================
-- 3. Update price_predictions table for multi-model support
-- ============================================================================

ALTER TABLE price_predictions ADD COLUMN IF NOT EXISTS model_id UUID REFERENCES ml_models(id);
ALTER TABLE price_predictions ADD COLUMN IF NOT EXISTS confidence DECIMAL(5,2);
ALTER TABLE price_predictions ADD COLUMN IF NOT EXISTS price_range_min DECIMAL(12,2);
ALTER TABLE price_predictions ADD COLUMN IF NOT EXISTS price_range_max DECIMAL(12,2);

CREATE INDEX IF NOT EXISTS idx_predictions_model_id ON price_predictions(model_id);

-- ============================================================================
-- 4. Create Model Training Runs Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS model_training_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_name VARCHAR(200) NOT NULL,
    trigger_type VARCHAR(50) NOT NULL, -- 'scheduled', 'manual', 'post_scrape'
    
    -- Dataset info
    total_samples INTEGER NOT NULL,
    train_samples INTEGER NOT NULL,
    test_samples INTEGER NOT NULL,
    data_snapshot_date DATE NOT NULL,
    
    -- Timing
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'running', -- 'running', 'completed', 'failed'
    error_message TEXT,
    
    -- Models trained
    models_trained JSONB, -- Array of model IDs
    
    -- Overall metrics
    best_model_id UUID REFERENCES ml_models(id),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_training_runs_started_at ON model_training_runs(started_at);
CREATE INDEX idx_training_runs_status ON model_training_runs(status);

-- ============================================================================
-- 5. Create Model Comparison Metrics Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS model_comparison_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    training_run_id UUID REFERENCES model_training_runs(id) ON DELETE CASCADE,
    model_id UUID REFERENCES ml_models(id) ON DELETE CASCADE,
    
    -- Overall metrics
    mae DECIMAL(10,2) NOT NULL,
    rmse DECIMAL(10,2) NOT NULL,
    r2_score DECIMAL(5,4) NOT NULL,
    mape DECIMAL(5,2) NOT NULL,
    
    -- Performance by price range
    mae_under_100k DECIMAL(10,2),
    mae_100k_to_300k DECIMAL(10,2),
    mae_300k_to_500k DECIMAL(10,2),
    mae_over_500k DECIMAL(10,2),
    
    -- Performance by fuel type
    mae_petrol DECIMAL(10,2),
    mae_diesel DECIMAL(10,2),
    mae_electric DECIMAL(10,2),
    mae_hybrid DECIMAL(10,2),
    
    -- Performance by year range
    mae_pre_2010 DECIMAL(10,2),
    mae_2010_to_2015 DECIMAL(10,2),
    mae_2015_to_2020 DECIMAL(10,2),
    mae_post_2020 DECIMAL(10,2),
    
    -- Timing
    avg_inference_time_ms DECIMAL(8,2),
    
    -- Confidence calibration
    confidence_mae DECIMAL(5,2), -- How accurate are confidence scores
    
    -- Additional metrics
    median_absolute_error DECIMAL(10,2),
    percentile_90_error DECIMAL(10,2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_run_model UNIQUE (training_run_id, model_id)
);

CREATE INDEX idx_comparison_metrics_run ON model_comparison_metrics(training_run_id);
CREATE INDEX idx_comparison_metrics_model ON model_comparison_metrics(model_id);

-- ============================================================================
-- 6. Update scraping_logs table
-- ============================================================================

ALTER TABLE scraping_logs ADD COLUMN IF NOT EXISTS cars_new INTEGER DEFAULT 0;
ALTER TABLE scraping_logs ADD COLUMN IF NOT EXISTS cars_updated INTEGER DEFAULT 0;
ALTER TABLE scraping_logs ADD COLUMN IF NOT EXISTS highest_external_id VARCHAR(50);
ALTER TABLE scraping_logs ADD COLUMN IF NOT EXISTS scraping_mode VARCHAR(20) DEFAULT 'full'; -- 'full' or 'incremental'
ALTER TABLE scraping_logs ADD COLUMN IF NOT EXISTS images_downloaded INTEGER DEFAULT 0;

-- ============================================================================
-- 7. Create Model Performance History View
-- ============================================================================

CREATE OR REPLACE VIEW model_performance_history AS
SELECT 
    m.id as model_id,
    m.name as model_name,
    m.model_type,
    m.algorithm,
    tr.started_at as training_date,
    mcm.mae,
    mcm.rmse,
    mcm.r2_score,
    mcm.mape,
    mcm.avg_inference_time_ms,
    tr.total_samples,
    tr.duration_seconds as training_duration_seconds
FROM ml_models m
JOIN model_comparison_metrics mcm ON m.id = mcm.model_id
JOIN model_training_runs tr ON mcm.training_run_id = tr.id
WHERE tr.status = 'completed'
ORDER BY tr.started_at DESC, mcm.mae ASC;

-- ============================================================================
-- 8. Insert Initial Model Registry (Existing XGBoost)
-- ============================================================================

INSERT INTO ml_models (name, model_type, algorithm, version, file_path, is_active, trained_at)
VALUES 
    ('XGBoost Regressor', 'tree', 'xgboost', 'v1.0.0', 'models/xgboost_model.pkl', true, CURRENT_TIMESTAMP),
    ('CatBoost Regressor', 'tree', 'catboost', 'v1.0.0', 'models/catboost_model.pkl', true, CURRENT_TIMESTAMP)
ON CONFLICT (name, version) DO NOTHING;

-- ============================================================================
-- 9. Create Indexes for Performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_cars_brand_model ON cars(brand, model);
CREATE INDEX IF NOT EXISTS idx_cars_fuel_year ON cars(fuel_type, year);
CREATE INDEX IF NOT EXISTS idx_predictions_confidence ON price_predictions(confidence);

COMMENT ON TABLE ml_models IS 'Registry of all machine learning models available for price prediction';
COMMENT ON TABLE model_training_runs IS 'History of model training executions';
COMMENT ON TABLE model_comparison_metrics IS 'Detailed comparison metrics for each model in each training run';
COMMENT ON COLUMN cars.external_id IS 'Bilbasen listing ID for tracking and incremental scraping';
COMMENT ON COLUMN cars.image_path IS 'Relative path to downloaded car image';
