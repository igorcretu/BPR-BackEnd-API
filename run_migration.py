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
        # Use 'db' if running in Docker, 'localhost' otherwise
        host = os.getenv('POSTGRES_HOST', 'localhost')
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
        
        # Check if migration was already applied first
        with engine.connect() as conn:
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
        
        # Execute migration - each statement in its own transaction to avoid abort cascade
        # Split by semicolon and execute each statement
        statements = [s.strip() for s in migration_sql.split(';') if s.strip() and not s.strip().startswith('--')]
        
        failed_statements = []
        succeeded = 0
        skipped = 0
        
        for idx, statement in enumerate(statements, 1):
            if not statement:
                continue
                
            try:
                print(f'  [{idx}/{len(statements)}] Executing...')
                # Each statement in its own transaction
                with engine.begin() as conn:
                    conn.execute(text(statement))
                succeeded += 1
                    
            except Exception as e:
                # Check if it's a benign error (column/table already exists, etc.)
                error_str = str(e).lower()
                if 'already exists' in error_str or 'duplicate' in error_str:
                    print(f'    ⚠️  Skipped (already exists)')
                    skipped += 1
                elif 'does not exist' in error_str and 'drop' in statement.lower():
                    print(f'    ⚠️  Skipped (does not exist)')
                    skipped += 1
                else:
                    print(f'    ❌ Error: {e}')
                    failed_statements.append((idx, statement[:100], e))
        
        print(f'\n📊 Migration Summary:')
        print(f'   ✅ Succeeded: {succeeded}')
        print(f'   ⚠️  Skipped: {skipped}')
        print(f'   ❌ Failed: {len(failed_statements)}')
        
        if failed_statements:
            print(f'\n❌ Failed statements:')
            for idx, stmt, err in failed_statements:
                print(f'  [{idx}] {stmt}...')
                print(f'      Error: {str(err)[:100]}')
            return 1
        
        print('\n✅ Database migration completed successfully!')
        return 0
                
    except Exception as e:
        print(f'❌ Migration failed: {e}')
        return 1

if __name__ == '__main__':
    sys.exit(run_migration())
