#!/usr/bin/env python3
"""
Training Status Monitor
Tests and monitors model training process
"""

import psycopg2
from datetime import datetime
import time
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Create database connection"""
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'car_prediction'),
        user=os.getenv('POSTGRES_USER', 'bpr_user'),
        password=os.getenv('POSTGRES_PASSWORD', 'bpr_password')
    )

def check_training_status():
    """Check latest training run status"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("\n" + "="*70)
    print("MODEL TRAINING STATUS CHECK")
    print("="*70)
    
    # Get latest training run
    cur.execute("""
        SELECT 
            id,
            run_date,
            dataset_size,
            train_size,
            test_size,
            training_duration_seconds,
            status,
            models_trained,
            best_model_id,
            notes,
            created_at
        FROM model_training_runs
        ORDER BY run_date DESC
        LIMIT 1
    """)
    
    latest = cur.fetchone()
    
    if not latest:
        print("\n❌ No training runs found in database")
        print("\nThis means either:")
        print("  1. Training has never been run")
        print("  2. Training hasn't started yet")
        print("  3. Training started but hasn't logged to database yet")
        conn.close()
        return False
    
    # Unpack latest training run
    (run_id, run_date, dataset_size, train_size, test_size, 
     duration, status, models_trained, best_model_id, notes, created_at) = latest
    
    print(f"\n📊 LATEST TRAINING RUN")
    print(f"   ID: {run_id}")
    print(f"   Started: {run_date}")
    print(f"   Created: {created_at}")
    print(f"   Status: {status.upper()}")
    print(f"   Dataset Size: {dataset_size:,} cars" if dataset_size else "   Dataset Size: N/A")
    print(f"   Train/Test Split: {train_size}/{test_size}" if train_size else "   Train/Test Split: N/A")
    
    if duration:
        hours = int(duration) // 3600
        minutes = (int(duration) % 3600) // 60
        seconds = int(duration) % 60
        print(f"   Duration: {hours}h {minutes}m {seconds}s")
    else:
        print(f"   Duration: N/A")
    
    if models_trained:
        print(f"   Models Trained: {len(models_trained)}")
        for model_name in models_trained:
            print(f"      - {model_name}")
    
    if best_model_id:
        print(f"   Best Model ID: {best_model_id}")
    
    if notes:
        print(f"   Notes: {notes}")
    
    # Status interpretation
    print(f"\n📈 STATUS INTERPRETATION:")
    if status == 'pending':
        print("   ⏳ Training has been initiated but not started processing yet")
    elif status == 'running':
        print("   🔄 Training is currently in progress")
    elif status == 'completed':
        print("   ✅ Training completed successfully")
    elif status == 'failed':
        print("   ❌ Training failed - check logs for details")
    else:
        print(f"   ❓ Unknown status: {status}")
    
    # Check how recent this is
    if run_date:
        age = datetime.utcnow() - run_date
        print(f"\n⏰ AGE: {age}")
        if age.total_seconds() < 60:
            print("   🆕 Very recent - likely just started!")
        elif age.total_seconds() < 3600:
            print("   🕐 Started within the last hour")
        elif age.total_seconds() < 86400:
            print("   📅 Started today")
        else:
            print("   📆 Started more than a day ago")
    
    # Get all training runs count
    cur.execute("SELECT COUNT(*) FROM model_training_runs")
    total_runs = cur.fetchone()[0]
    print(f"\n📚 TOTAL TRAINING RUNS: {total_runs}")
    
    # Get models info
    cur.execute("""
        SELECT 
            model_type,
            version,
            performance_metrics,
            created_at
        FROM ml_models
        ORDER BY created_at DESC
        LIMIT 5
    """)
    
    models = cur.fetchall()
    if models:
        print(f"\n🤖 LATEST ML MODELS IN DATABASE:")
        for model_type, version, metrics, created in models:
            print(f"   - {model_type} v{version} (created: {created})")
            if metrics and isinstance(metrics, dict):
                if 'test_r2' in metrics:
                    print(f"     R² Score: {metrics['test_r2']:.4f}")
                if 'test_mae' in metrics:
                    print(f"     MAE: {metrics['test_mae']:.2f}")
    
    conn.close()
    return status

def monitor_training(interval=10, max_checks=100):
    """Monitor training progress in real-time"""
    print("\n" + "="*70)
    print("REAL-TIME TRAINING MONITOR")
    print(f"Checking every {interval} seconds (press Ctrl+C to stop)")
    print("="*70)
    
    last_status = None
    checks = 0
    
    try:
        while checks < max_checks:
            status = check_training_status()
            
            if status and status != last_status:
                print(f"\n⚡ STATUS CHANGED: {last_status} → {status}")
            
            if status in ['completed', 'failed']:
                print(f"\n✋ Training finished with status: {status}")
                break
            
            last_status = status
            checks += 1
            
            if checks < max_checks:
                print(f"\n⏳ Checking again in {interval} seconds... (check {checks}/{max_checks})")
                time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoring stopped by user")

def check_process_running():
    """Check if training process is running (Linux/Mac only)"""
    import subprocess
    print("\n" + "="*70)
    print("PROCESS CHECK")
    print("="*70)
    
    try:
        # Try pgrep first
        result = subprocess.run(
            ['pgrep', '-f', 'train_models'],
            capture_output=True,
            text=True,
            timeout=2
        )
        
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"\n✅ Training process is RUNNING")
            print(f"   Process IDs: {', '.join(pids)}")
            return True
        else:
            print(f"\n❌ No training process found")
            return False
            
    except FileNotFoundError:
        print("\n⚠️  'pgrep' command not available (Windows or not in PATH)")
        print("   Process check skipped")
        return None
    except Exception as e:
        print(f"\n⚠️  Could not check process: {e}")
        return None

def check_log_file():
    """Check training log file"""
    print("\n" + "="*70)
    print("LOG FILE CHECK")
    print("="*70)
    
    log_path = "../ML_Model/train_models.log"
    
    if os.path.exists(log_path):
        print(f"\n✅ Log file found: {log_path}")
        
        # Get file size and modification time
        stat = os.stat(log_path)
        size_kb = stat.st_size / 1024
        mod_time = datetime.fromtimestamp(stat.st_mtime)
        age = datetime.now() - mod_time
        
        print(f"   Size: {size_kb:.2f} KB")
        print(f"   Last Modified: {mod_time}")
        print(f"   Age: {age}")
        
        if age.total_seconds() < 60:
            print(f"   🆕 Very recent - likely active!")
        
        # Show last 20 lines
        print(f"\n📄 LAST 20 LINES:")
        print("   " + "-"*66)
        with open(log_path, 'r') as f:
            lines = f.readlines()
            for line in lines[-20:]:
                print(f"   {line.rstrip()}")
        print("   " + "-"*66)
    else:
        print(f"\n❌ Log file not found: {log_path}")
        print("   Training may not have started yet, or logs are elsewhere")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'monitor':
        # Real-time monitoring mode
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        monitor_training(interval=interval)
    else:
        # One-time check mode
        check_training_status()
        check_process_running()
        check_log_file()
        
        print("\n" + "="*70)
        print("💡 TIP: Run 'python check_training_status.py monitor' for real-time monitoring")
        print("="*70 + "\n")
