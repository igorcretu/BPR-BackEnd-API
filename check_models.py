#!/usr/bin/env python3
"""
Check ML Model Status
Checks if models exist and if training is needed.
"""
import os
import sys
from sqlalchemy import create_engine, text

def check_model_status():
    """Check ML model status and recommend actions."""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print('❌ DATABASE_URL environment variable not set')
        return 1

    try:
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            # Check if ml_models table exists
            check_table = text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'ml_models'
                )
            """)
            result = conn.execute(check_table)
            table_exists = result.scalar()
            
            if not table_exists:
                print('⚠️  ml_models table not found')
                print('💡 Run migration first: python run_migration.py')
                return 1
            
            # Count active models
            count_models = text('SELECT COUNT(*) FROM ml_models WHERE is_active = true')
            result = conn.execute(count_models)
            active_models = result.scalar()
            
            # Count cars
            count_cars = text('SELECT COUNT(*) FROM cars')
            result = conn.execute(count_cars)
            car_count = result.scalar()
            
            print(f'📊 Status:')
            print(f'  Active ML models: {active_models}')
            print(f'  Cars in database: {car_count}')
            
            if car_count < 100:
                print('⚠️  Not enough data for training (minimum: 100 cars)')
                print('💡 Upload data first or run scraper')
                return 0
            
            if active_models == 0:
                print('🎯 Sufficient data available, but no models trained')
                print('💡 Train models: python train_models.py')
                return 2  # Exit code 2 means training needed
            
            print(f'✅ {active_models} active models found')
            
            # Show latest training info
            latest_training = text("""
                SELECT run_date, dataset_size, status, best_model_id
                FROM model_training_runs
                ORDER BY run_date DESC
                LIMIT 1
            """)
            result = conn.execute(latest_training)
            row = result.fetchone()
            
            if row:
                print(f'\n📅 Latest training:')
                print(f'  Date: {row[0]}')
                print(f'  Dataset size: {row[1]}')
                print(f'  Status: {row[2]}')
                print(f'  Best model ID: {row[3]}')
            
            return 0
            
    except Exception as e:
        print(f'❌ Error checking status: {e}')
        return 1

if __name__ == '__main__':
    sys.exit(check_model_status())
