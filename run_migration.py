#!/usr/bin/env python3
"""
Database Migration Runner
Applies the multi-model schema migration to the database.
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

def run_migration():
    """Run database migration from SQL file."""
    db_url = os.getenv('DATABASE_URL')
    
    # Fallback: construct from individual variables if DATABASE_URL not set
    if not db_url:
        user = os.getenv('POSTGRES_USER', 'bpr_user')
        password = os.getenv('POSTGRES_PASSWORD', 'postgres')
        host = os.getenv('POSTGRES_HOST', 'db')
        port = os.getenv('POSTGRES_PORT', '5432')
        database = os.getenv('POSTGRES_DB', 'car_prediction')
        db_url = f'postgresql://{user}:{password}@{host}:{port}/{database}'
    
    if not db_url:
        print('❌ DATABASE_URL environment variable not set')
        return 1

    try:
        engine = create_engine(db_url)
        
        # Path to migration SQL file
        migration_file = '/app/migrations/add_ml_models_schema.sql'
        if not os.path.exists(migration_file):
            # Try alternative path if running locally
            migration_file = 'migrations/add_ml_models_schema.sql'
        
        if not os.path.exists(migration_file):
            print(f'❌ Migration file not found: {migration_file}')
            return 1
        
        print(f'📖 Reading migration from: {migration_file}')
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        print('🗄️  Applying database migration...')
        with engine.connect() as conn:
            # Check if migration was already applied
            check_query = text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'ml_models'
                )
            """)
            result = conn.execute(check_query)
            table_exists = result.scalar()
            
            if table_exists:
                print('ℹ️  Migration appears to have been applied already (ml_models table exists)')
                print('✅ Skipping migration')
                return 0
            
            # Execute migration
            trans = conn.begin()
            try:
                # Split by semicolon and execute each statement
                statements = [s.strip() for s in migration_sql.split(';') if s.strip() and not s.strip().startswith('--')]
                
                for idx, statement in enumerate(statements, 1):
                    if statement:
                        print(f'  Executing statement {idx}/{len(statements)}...')
                        conn.execute(text(statement))
                
                trans.commit()
                print('✅ Database migration completed successfully!')
                return 0
                
            except Exception as e:
                trans.rollback()
                print(f'❌ Migration error: {e}')
                print('⚠️  Rolling back changes...')
                return 1
                
    except Exception as e:
        print(f'❌ Migration failed: {e}')
        return 1

if __name__ == '__main__':
    sys.exit(run_migration())
