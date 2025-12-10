#!/usr/bin/env python3
"""
Test Training Trigger
Triggers model training via API and monitors the result
"""

import requests
import time
import sys

API_URL = "http://localhost:5000"

def trigger_training():
    """Trigger model training via API"""
    print("="*70)
    print("TRIGGERING MODEL TRAINING")
    print("="*70)
    
    try:
        response = requests.post(
            f"{API_URL}/api/trigger-training",
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"\n📡 Response Status: {response.status_code}")
        print(f"📄 Response Body:")
        print(f"   {response.json()}")
        
        if response.status_code == 202:
            print("\n✅ SUCCESS! Training has been triggered")
            print("\n📝 Next steps:")
            print("   1. Wait a few seconds for training to initialize")
            print("   2. Run: python check_training_status.py")
            print("   3. Or monitor in real-time: python check_training_status.py monitor")
            print("   4. Check Docker logs: docker logs -f bpr-flask")
            print("   5. Check training log: tail -f ../ML_Model/train_models.log")
            return True
            
        elif response.status_code == 400:
            print("\n⚠️  Training may already be running")
            print("   Check status with: python check_training_status.py")
            return False
            
        else:
            print(f"\n❌ Unexpected response code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to API")
        print(f"   Make sure the backend is running at {API_URL}")
        print("   Start it with: docker-compose up -d")
        return False
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def check_api_health():
    """Check if API is accessible"""
    print("\n" + "="*70)
    print("API HEALTH CHECK")
    print("="*70)
    
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        print(f"\n✅ API is accessible at {API_URL}")
        print(f"   Status: {response.status_code}")
        
        data = response.json()
        if 'training_status' in data:
            print(f"\n🤖 Current Training Status from Health Endpoint:")
            training = data['training_status']
            if training:
                print(f"   Last Run: {training.get('last_run', 'N/A')}")
                print(f"   Status: {training.get('status', 'N/A')}")
                print(f"   Duration: {training.get('duration', 'N/A')}")
            else:
                print("   No training runs found")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to API at {API_URL}")
        print("   Make sure Docker containers are running")
        return False
        
    except Exception as e:
        print(f"\n⚠️  Error checking health: {e}")
        return False

if __name__ == '__main__':
    # Check API health first
    if not check_api_health():
        sys.exit(1)
    
    # Trigger training
    print("\n")
    success = trigger_training()
    
    if success:
        print("\n⏳ Waiting 5 seconds before checking status...")
        time.sleep(5)
        
        # Run status check
        print("\n")
        import subprocess
        subprocess.run([sys.executable, 'check_training_status.py'])
