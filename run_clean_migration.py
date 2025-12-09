#!/usr/bin/env python3
"""
Simple migration runner - runs entire SQL file as one script
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def run_migration():
    # Get database credentials
    db_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB', 'car_prediction'),
        'user': os.getenv('POSTGRES_USER', 'bpr_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
    }
    
    migration_file = 'migrations/clean_migration.sql'
    
    print(f'📖 Reading migration: {migration_file}')
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    print(f'🔗 Connecting to database...')
    conn = psycopg2.connect(**db_config)
    conn.autocommit = True  # Important for DO blocks
    cur = conn.cursor()
    
    print(f'🗄️  Executing migration...')
    try:
        cur.execute(sql)
        print('✅ Migration completed successfully!')
        
        # Verify tables exist
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema='public' 
            AND table_name IN ('ml_models', 'model_training_runs', 'model_comparison_metrics')
            ORDER BY table_name
        """)
        tables = cur.fetchall()
        print(f'\n📊 Created tables:')
        for table in tables:
            print(f'   ✓ {table[0]}')
            
    except Exception as e:
        print(f'❌ Error: {e}')
        return 1
    finally:
        cur.close()
        conn.close()
    
    return 0

if __name__ == '__main__':
    exit(run_migration())
