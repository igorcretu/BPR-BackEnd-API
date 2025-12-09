#!/usr/bin/env python3
"""
Debug script to test image path resolution on Raspberry Pi
Run this on the Raspberry Pi where Flask is deployed
"""
import os
import sys

print("="*80)
print("IMAGE PATH DEBUGGING FOR FLASK API")
print("="*80)

# Simulate Flask app location
flask_app_locations = [
    "/home/igor/BachelorApi/BPR-BackEnd-API/app/main.py",
    "/home/igor/BachelorApi/BPR-BackEnd-API/API/app/main.py",
]

test_filename = "6660295.jpg"

for flask_location in flask_app_locations:
    if not os.path.exists(os.path.dirname(flask_location)):
        continue
        
    print(f"\n{'='*80}")
    print(f"Testing with Flask at: {flask_location}")
    print(f"{'='*80}")
    
    current_dir = os.path.dirname(flask_location)
    api_root = os.path.dirname(current_dir)
    project_root = os.path.dirname(api_root)
    
    print(f"\ncurrent_dir: {current_dir}")
    print(f"api_root: {api_root}")
    print(f"project_root: {project_root}")
    
    # Test paths
    possible_paths = [
        os.path.join(project_root, 'BPR-BackEnd-ML-Model', 'bilbasen_scrape', 'images', test_filename),
        f'/home/igor/BachelorApi/BPR-BackEnd-ML-Model/bilbasen_scrape/images/{test_filename}',
    ]
    
    print(f"\nChecking paths for {test_filename}:")
    print("-"*80)
    
    for i, path in enumerate(possible_paths, 1):
        exists = os.path.exists(path)
        status = "✓ EXISTS" if exists else "✗ NOT FOUND"
        print(f"\n{i}. {status}")
        print(f"   Path: {path}")
        if exists:
            print(f"   Size: {os.path.getsize(path)} bytes")

# Check images directory
print(f"\n{'='*80}")
print("CHECKING IMAGES DIRECTORY")
print(f"{'='*80}")

images_dir = "/home/igor/BachelorApi/BPR-BackEnd-ML-Model/bilbasen_scrape/images"
print(f"\nDirectory: {images_dir}")

if os.path.exists(images_dir):
    print("✓ Directory exists")
    jpg_files = [f for f in os.listdir(images_dir) if f.endswith('.jpg')]
    print(f"Total .jpg files: {len(jpg_files)}")
    print(f"\nFirst 5 files:")
    for f in jpg_files[:5]:
        print(f"  - {f}")
else:
    print("✗ Directory NOT FOUND")

print(f"\n{'='*80}")
print("CHECKING ACTUAL FLASK DEPLOYMENT")
print(f"{'='*80}")

# Try to find where Flask is actually running from
import subprocess
try:
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    flask_processes = [line for line in result.stdout.split('\n') if 'main.py' in line or 'gunicorn' in line or 'flask' in line.lower()]
    if flask_processes:
        print("\nFlask/Gunicorn processes found:")
        for proc in flask_processes:
            print(f"  {proc}")
    else:
        print("\nNo Flask processes found")
except Exception as e:
    print(f"\nCouldn't check processes: {e}")
