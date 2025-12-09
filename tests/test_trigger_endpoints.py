"""
Tests for manual trigger endpoints (scraping and training)
"""
import pytest
from unittest.mock import patch, MagicMock
import subprocess


def test_trigger_scraping_success(client):
    """Test successful scraping trigger"""
    with patch('app.main.subprocess.run') as mock_run, \
         patch('app.main.threading.Thread') as mock_thread:
        # Mock pgrep to return no running process
        mock_run.return_value = MagicMock(returncode=1)
        
        response = client.post('/api/trigger-scraping', 
                              json={'mode': 'incremental'},
                              content_type='application/json')
        
        assert response.status_code == 202
        data = response.get_json()
        assert data['success'] is True
        assert 'estimated_duration' in data


def test_trigger_scraping_already_running(client):
    """Test scraping trigger when already running"""
    with patch('app.main.subprocess.run') as mock_run:
        # Mock pgrep to return running process
        mock_run.return_value = MagicMock(returncode=0)
        
        response = client.post('/api/trigger-scraping',
                              json={'mode': 'incremental'},
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False


def test_trigger_scraping_full_mode(client):
    """Test scraping trigger with full mode"""
    with patch('app.main.subprocess.run') as mock_run, \
         patch('app.main.threading.Thread') as mock_thread:
        mock_run.return_value = MagicMock(returncode=1)
        
        response = client.post('/api/trigger-scraping',
                              json={'mode': 'full'},
                              content_type='application/json')
        
        assert response.status_code == 202
        data = response.get_json()
        assert data['success'] is True


def test_trigger_scraping_no_mode(client):
    """Test scraping trigger without mode (defaults to incremental)"""
    with patch('app.main.subprocess.run') as mock_run, \
         patch('app.main.threading.Thread') as mock_thread:
        mock_run.return_value = MagicMock(returncode=1)
        
        response = client.post('/api/trigger-scraping',
                              json={},
                              content_type='application/json')
        
        assert response.status_code == 202


def test_trigger_scraping_check_timeout(client):
    """Test scraping trigger when check times out - continues anyway"""
    with patch('app.main.subprocess.run') as mock_run, \
         patch('app.main.threading.Thread') as mock_thread:
        mock_run.side_effect = subprocess.TimeoutExpired('pgrep', 2)
        
        response = client.post('/api/trigger-scraping',
                              json={'mode': 'incremental'},
                              content_type='application/json')
        
        # Should still proceed with scraping despite timeout
        assert response.status_code == 202


def test_trigger_training_success(client):
    """Test successful training trigger"""
    with patch('app.main.subprocess.run') as mock_run, \
         patch('app.main.threading.Thread') as mock_thread:
        # Mock pgrep to return no running process
        mock_run.return_value = MagicMock(returncode=1)
        
        response = client.post('/api/trigger-training')
        
        assert response.status_code == 202
        data = response.get_json()
        assert data['success'] is True
        assert 'estimated_duration' in data


def test_trigger_training_already_running(client):
    """Test training trigger when already running"""
    with patch('app.main.subprocess.run') as mock_run:
        # Mock pgrep to return running process
        mock_run.return_value = MagicMock(returncode=0)
        
        response = client.post('/api/trigger-training')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False


def test_trigger_training_check_timeout(client):
    """Test training trigger when check times out - continues anyway"""
    with patch('app.main.subprocess.run') as mock_run, \
         patch('app.main.threading.Thread') as mock_thread:
        mock_run.side_effect = subprocess.TimeoutExpired('pgrep', 2)
        
        response = client.post('/api/trigger-training')
        
        # Should still proceed with training despite timeout
        assert response.status_code == 202


def test_health_check_with_processes(client):
    """Test health endpoint returns process status"""
    with patch('app.main.subprocess.run') as mock_run:
        # Mock scraper running, training not running
        def side_effect(*args, **kwargs):
            cmd = args[0]
            if 'bilbasen_scraper' in ' '.join(cmd):
                result = MagicMock(returncode=0)
                result.stdout = "12345\n67890"
                return result
            else:
                return MagicMock(returncode=1)
        
        mock_run.side_effect = side_effect
        
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'processes' in data
        assert data['processes']['scraper']['running'] is True
        assert data['processes']['training']['running'] is False


def test_health_check_process_check_error(client):
    """Test health endpoint when process check fails"""
    with patch('app.main.subprocess.run') as mock_run:
        mock_run.side_effect = Exception("Process check failed")
        
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.get_json()
        # Should still return health data even if process check fails
        assert 'database' in data
        assert 'ml_model' in data
