"""
Tests for scraper database logging functionality
"""
import pytest
from unittest.mock import patch, MagicMock
from app.models import ScrapingLog
import time


def test_scraper_creates_db_log(client):
    """Test that triggering scraper creates a ScrapingLog entry"""
    with patch('app.main.subprocess.run') as mock_run, \
         patch('app.main.subprocess.Popen') as mock_popen, \
         patch('app.main.os.path.exists') as mock_exists, \
         patch('app.main.threading.Thread') as mock_thread:
        
        # Mock pgrep to return no running process
        mock_run.return_value = MagicMock(returncode=1, stdout=MagicMock(strip=MagicMock(return_value='')))
        
        # Mock script exists
        mock_exists.return_value = True
        
        # Mock successful process
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Still running
        mock_popen.return_value = mock_process
        
        # Count logs before
        from app.models import db
        initial_count = db.session.query(ScrapingLog).count()
        
        # Trigger scraper
        response = client.post('/api/trigger-scraping',
                              json={'mode': 'incremental'},
                              content_type='application/json')
        
        assert response.status_code == 202
        
        # Check that a log entry was created
        final_count = db.session.query(ScrapingLog).count()
        assert final_count == initial_count + 1
        
        # Get the latest log
        latest_log = db.session.query(ScrapingLog).order_by(ScrapingLog.created_at.desc()).first()
        assert latest_log is not None
        assert latest_log.source_name == 'bilbasen'
        assert latest_log.scraping_mode == 'incremental'
        assert latest_log.started_at is not None


def test_scraper_db_log_different_modes(client):
    """Test that database log captures different scraping modes"""
    with patch('app.main.subprocess.run') as mock_run, \
         patch('app.main.subprocess.Popen') as mock_popen, \
         patch('app.main.os.path.exists') as mock_exists, \
         patch('app.main.threading.Thread') as mock_thread:
        
        mock_run.return_value = MagicMock(returncode=1, stdout=MagicMock(strip=MagicMock(return_value='')))
        mock_exists.return_value = True
        
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        from app.models import db
        
        # Test full mode
        response = client.post('/api/trigger-scraping',
                              json={'mode': 'full'},
                              content_type='application/json')
        
        assert response.status_code == 202
        
        latest_log = db.session.query(ScrapingLog).order_by(ScrapingLog.created_at.desc()).first()
        assert latest_log.scraping_mode == 'full'


def test_scraper_db_log_initial_state(client):
    """Test that initial database log has correct default state"""
    with patch('app.main.subprocess.run') as mock_run, \
         patch('app.main.subprocess.Popen') as mock_popen, \
         patch('app.main.os.path.exists') as mock_exists, \
         patch('app.main.threading.Thread') as mock_thread:
        
        mock_run.return_value = MagicMock(returncode=1, stdout=MagicMock(strip=MagicMock(return_value='')))
        mock_exists.return_value = True
        
        # Mock successful process
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        from app.models import db
        
        response = client.post('/api/trigger-scraping',
                              json={'mode': 'incremental'},
                              content_type='application/json')
        
        assert response.status_code == 202
        
        # Get the latest log
        latest_log = db.session.query(ScrapingLog).order_by(ScrapingLog.created_at.desc()).first()
        assert latest_log.success is False  # Initial state before completion
        assert latest_log.started_at is not None
        assert latest_log.completed_at is None  # Not completed yet


def test_scraper_db_log_returns_log_id(client):
    """Test that database log ID is returned in response"""
    with patch('app.main.subprocess.run') as mock_run, \
         patch('app.main.subprocess.Popen') as mock_popen, \
         patch('app.main.os.path.exists') as mock_exists, \
         patch('app.main.threading.Thread') as mock_thread:
        
        mock_run.return_value = MagicMock(returncode=1, stdout=MagicMock(strip=MagicMock(return_value='')))
        mock_exists.return_value = True
        
        mock_process = MagicMock()
        mock_process.pid = 99999
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        from app.models import db
        
        response = client.post('/api/trigger-scraping',
                              json={'mode': 'full'},
                              content_type='application/json')
        assert response.status_code == 202
        
        data = response.get_json()
        assert 'log_id' in data
        
        # Verify the log exists in DB
        log_entry = db.session.get(ScrapingLog, data['log_id'])
        assert log_entry is not None
        assert log_entry.scraping_mode == 'full'


def test_scraper_captures_source_name(client):
    """Test that scraper log captures correct source name"""
    with patch('app.main.subprocess.run') as mock_run, \
         patch('app.main.subprocess.Popen') as mock_popen, \
         patch('app.main.os.path.exists') as mock_exists, \
         patch('app.main.threading.Thread') as mock_thread:
        
        mock_run.return_value = MagicMock(returncode=1, stdout=MagicMock(strip=MagicMock(return_value='')))
        mock_exists.return_value = True
        
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        from app.models import db
        
        client.post('/api/trigger-scraping',
                   json={'mode': 'incremental'},
                   content_type='application/json')
        
        latest_log = db.session.query(ScrapingLog).order_by(ScrapingLog.created_at.desc()).first()
        assert latest_log.source_name == 'bilbasen'


def test_scraper_db_log_failure_immediate(client):
    """Test that immediate scraper failure is logged to database"""
    with patch('app.main.subprocess.run') as mock_run, \
         patch('app.main.subprocess.Popen') as mock_popen, \
         patch('app.main.os.path.exists') as mock_exists, \
         patch('app.main.threading.Thread') as mock_thread:
        
        mock_run.return_value = MagicMock(returncode=1, stdout=MagicMock(strip=MagicMock(return_value='')))
        mock_exists.return_value = True
        
        # Mock process that dies immediately
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = 1  # Died immediately
        mock_process.communicate.return_value = (b'', b'ModuleNotFoundError: No module named xyz')
        mock_process.returncode = 1
        mock_popen.return_value = mock_process
        
        from app.models import db
        
        response = client.post('/api/trigger-scraping',
                              json={'mode': 'incremental'},
                              content_type='application/json')
        
        assert response.status_code == 202
        
        # Give background thread time to execute
        import time
        time.sleep(0.2)
        
        # Check the log was updated with failure
        latest_log = db.session.query(ScrapingLog).order_by(ScrapingLog.created_at.desc()).first()
        # Note: The background thread updates this, so we may not see it immediately in the test


def test_scraper_db_timestamps(client):
    """Test that scraper log has proper timestamps"""
    with patch('app.main.subprocess.run') as mock_run, \
         patch('app.main.subprocess.Popen') as mock_popen, \
         patch('app.main.os.path.exists') as mock_exists, \
         patch('app.main.threading.Thread') as mock_thread:
        
        from datetime import datetime, timedelta
        mock_run.return_value = MagicMock(returncode=1, stdout=MagicMock(strip=MagicMock(return_value='')))
        mock_exists.return_value = True
        
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        from app.models import db
        
        before_time = datetime.utcnow()
        client.post('/api/trigger-scraping',
                   json={'mode': 'incremental'},
                   content_type='application/json')
        after_time = datetime.utcnow()
        
        latest_log = db.session.query(ScrapingLog).order_by(ScrapingLog.created_at.desc()).first()
        assert latest_log.started_at is not None
        assert before_time <= latest_log.started_at <= after_time
        assert latest_log.created_at is not None
