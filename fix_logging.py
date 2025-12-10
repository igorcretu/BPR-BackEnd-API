#!/usr/bin/env python3
"""Script to add comprehensive logging to trigger_scraping function"""

import re

# Read the file
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the trigger_scraping function
old_pattern = r'''@app\.route\('/api/trigger-scraping', methods=\['POST'\]\)
@handle_errors
def trigger_scraping\(\):
    """Trigger scraping process in the background"""
    import threading
    
    logger\.info\(f"\[{g\.request_id}\] Scraping trigger requested"\)
    
    # Check if already running
    try:
        # Check for any scraper process \(new incremental scraper or legacy ones\)
        patterns_to_check = \['bilbasen_incremental', 'auto_scraper', 'bilbasen_scraper'\]
        found_running = False
        
        for pattern in patterns_to_check:
            result = subprocess\.run\(
                \['pgrep', '-f', pattern\],
                capture_output=True,
                text=True,
                timeout=2
            \)
            if result\.returncode == 0:
                found_running = True
                logger\.info\(f"\[{g\.request_id}\] Found running scraper: {pattern}"\)
                break
        
        if found_running:
            return jsonify\({
                'success': False,
                'message': 'Scraper is already running',
                'running': True
            }\), 400
    except Exception as e:
        logger\.warning\(f"\[{g\.request_id}\] Could not check scraper status: {type\(e\).__name__}: {e}"\)
    
    # Parse request for scraping mode
    data = request\.get_json\(\) or {}
    mode = data\.get\('mode', 'incremental'\)  # 'incremental' or 'full'
    
    def run_scraper\(\):
        """Background thread to run scraper"""
        try:'''

new_text = '''@app.route('/api/trigger-scraping', methods=['POST'])
@handle_errors
def trigger_scraping():
    """Trigger scraping process in the background"""
    import threading
    
    logger.info(f"[{g.request_id}] ========== SCRAPER TRIGGER START ==========")
    logger.info(f"[{g.request_id}] Scraping trigger requested")
    
    # Check if already running
    try:
        logger.info(f"[{g.request_id}] Step 1: Checking for running scraper processes...")
        # Check for any scraper process (new incremental scraper or legacy ones)
        patterns_to_check = ['bilbasen_incremental', 'auto_scraper', 'bilbasen_scraper']
        found_running = False
        
        for pattern in patterns_to_check:
            logger.info(f"[{g.request_id}] Checking for pattern: {pattern}")
            result = subprocess.run(
                ['pgrep', '-f', pattern],
                capture_output=True,
                text=True,
                timeout=2
            )
            logger.info(f"[{g.request_id}] pgrep result for {pattern}: returncode={result.returncode}, stdout={result.stdout.strip()}")
            if result.returncode == 0:
                found_running = True
                logger.warning(f"[{g.request_id}] Found running scraper: {pattern} (PID: {result.stdout.strip()})")
                break
        
        if found_running:
            logger.info(f"[{g.request_id}] Scraper already running - rejecting request")
            return jsonify({
                'success': False,
                'message': 'Scraper is already running',
                'running': True
            }), 400
        
        logger.info(f"[{g.request_id}] No running scraper found - proceeding")
    except Exception as e:
        logger.warning(f"[{g.request_id}] Could not check scraper status: {type(e).__name__}: {e}")
        logger.warning(f"[{g.request_id}] Continuing anyway...")
    
    # Parse request for scraping mode
    data = request.get_json() or {}
    mode = data.get('mode', 'incremental')  # 'incremental' or 'full'
    logger.info(f"[{g.request_id}] Step 2: Parsed scraping mode: {mode}")
    
    # Capture request_id before thread context
    request_id = g.request_id
    
    def run_scraper():
        """Background thread to run scraper"""
        thread_id = threading.current_thread().name
        try:
            logger.info(f"[{request_id}][{thread_id}] ===== BACKGROUND THREAD STARTED =====")'''

content = re.sub(old_pattern, new_text, content, flags=re.DOTALL)

# Write back
with open('app/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed!")
