#!/usr/bin/env python3
"""
Apply migration to production database
Run this to add ml_models, scraping_logs, and model_training_runs tables
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def apply_migration():
    # Production DATABASE_URL
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        print('❌ DATABASE_URL not found in .env file')
        return 1
    
    print(f'🔗 Connecting to database...')
    print(f'   URL: {db_url[:30]}...')
    
    try:
        engine = create_engine(db_url)
        
        migration_file = 'migrations/add_ml_models_schema.sql'
        
        print(f'📖 Reading migration from: {migration_file}')
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        with engine.connect() as conn:
            print('🗄️  Checking if migration already applied...')
            
            # Check if ml_models table exists
            check_query = text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'ml_models'
                )
            """)
            result = conn.execute(check_query)
            table_exists = result.scalar()
            
            if table_exists:
                print('✅ ml_models table already exists - migration already applied')
                
                # Show what tables exist
                show_tables = text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('ml_models', 'scraping_logs', 'model_training_runs')
                    ORDER BY table_name
                """)
                tables = conn.execute(show_tables).fetchall()
                print('\n📊 Existing migration tables:')
                for table in tables:
                    print(f'   ✓ {table[0]}')
                
                return 0
            
            print('🚀 Applying migration to production database...')
            print('⚠️  This will create: ml_models, model_training_runs, and update other tables')
            
            trans = conn.begin()
            try:
                # Split by semicolon and execute each statement
                statements = [s.strip() for s in migration_sql.split(';') 
                             if s.strip() and not s.strip().startswith('--')]
                
                total = len(statements)
                for idx, statement in enumerate(statements, 1):
                    if statement:
                        print(f'  [{idx}/{total}] Executing statement...')
                        conn.execute(text(statement))
                
                trans.commit()
                print('\n✅ Migration completed successfully!')
                print('\n📊 New tables created:')
                print('   ✓ ml_models')
                print('   ✓ model_training_runs')
                print('   ✓ model_comparison_metrics')
                print('\n📋 Updated tables:')
                print('   ✓ cars (added external_id, image fields)')
                print('   ✓ price_predictions (added model_id, confidence)')
                
                return 0
                
            except Exception as e:
                trans.rollback()
                print(f'\n❌ Migration failed: {e}')
                print('⚠️  All changes rolled back')
                return 1
                
    except Exception as e:
        print(f'❌ Connection error: {e}')
        return 1

if __name__ == '__main__':
    result = apply_migration()
    exit(result)
