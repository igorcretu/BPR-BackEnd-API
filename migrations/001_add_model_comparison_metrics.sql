-- Migration: Add model_comparison_metrics table if missing
-- This table stores detailed comparison metrics for trained models

CREATE TABLE IF NOT EXISTS model_comparison_metrics (
    id VARCHAR(36) PRIMARY KEY,
    model_id VARCHAR(36) NOT NULL REFERENCES ml_models(id),
    training_run_id VARCHAR(36) REFERENCES model_training_runs(id),
    
    -- Overall metrics
    overall_mae NUMERIC(12, 2),
    overall_rmse NUMERIC(12, 2),
    overall_r2 NUMERIC(6, 4),
    overall_mape NUMERIC(6, 4),
    
    -- Metrics by price range
    mae_under_100k NUMERIC(12, 2),
    mae_100k_300k NUMERIC(12, 2),
    mae_300k_500k NUMERIC(12, 2),
    mae_over_500k NUMERIC(12, 2),
    
    -- Metrics by fuel type
    mae_petrol NUMERIC(12, 2),
    mae_diesel NUMERIC(12, 2),
    mae_electric NUMERIC(12, 2),
    mae_hybrid NUMERIC(12, 2),
    
    -- Metrics by year range
    mae_pre_2010 NUMERIC(12, 2),
    mae_2010_2015 NUMERIC(12, 2),
    mae_2015_2020 NUMERIC(12, 2),
    mae_post_2020 NUMERIC(12, 2),
    
    -- Performance metrics
    avg_inference_time_ms NUMERIC(10, 2),
    confidence_calibration_score NUMERIC(6, 4),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_model_comparison_model ON model_comparison_metrics(model_id);
CREATE INDEX IF NOT EXISTS idx_model_comparison_training ON model_comparison_metrics(training_run_id);
