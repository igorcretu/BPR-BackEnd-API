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


def test_health_check_with_psutil_fallback(client):
    """Test health endpoint uses psutil when pgrep not available"""
    with patch('app.main.subprocess.run') as mock_run, \
         patch('psutil.process_iter') as mock_process_iter:
        # Simulate pgrep not found
        mock_run.side_effect = FileNotFoundError("pgrep not found")
        
        # Mock psutil to return a scraper process
        mock_proc = MagicMock()
        mock_proc.info = {
            'pid': 12345,
            'name': 'python3',
            'cmdline': ['python3', 'bilbasen_scraper_pi.py']
        }
        mock_process_iter.return_value = [mock_proc]
        
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'processes' in data
        assert data['processes']['scraper']['running'] is True
        assert 12345 in data['processes']['scraper']['pids']


def test_health_check_psutil_no_processes(client):
    """Test health endpoint with psutil when no processes running"""
    with patch('app.main.subprocess.run') as mock_run, \
         patch('psutil.process_iter') as mock_process_iter:
        # Simulate pgrep not found
        mock_run.side_effect = FileNotFoundError("pgrep not found")
        
        # Mock psutil to return no matching processes
        mock_proc = MagicMock()
        mock_proc.info = {
            'pid': 99999,
            'name': 'python3',
            'cmdline': ['python3', 'some_other_script.py']
        }
        mock_process_iter.return_value = [mock_proc]
        
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'processes' in data
        assert data['processes']['scraper']['running'] is False


def test_debug_script_paths_endpoint(client):
    """Test debug endpoint for script path verification"""
    with patch('os.path.exists') as mock_exists, \
         patch('os.access') as mock_access, \
         patch('os.path.isdir') as mock_isdir, \
         patch('os.listdir') as mock_listdir:
        # Mock Docker paths exist
        mock_exists.side_effect = lambda path: '/app/ML_Model' in path
        mock_access.return_value = True
        mock_isdir.return_value = True
        mock_listdir.return_value = ['train_models.py', 'auto_scraper.py', 'requirements.txt']
        
        response = client.get('/api/debug/script-paths')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'training_script' in data
        assert 'scraper_script' in data
        assert 'python' in data
        assert 'ml_model_directory' in data
        assert data['training_script']['docker_path'] == '/app/ML_Model/train_models.py'
        assert data['scraper_script']['docker_path'] == '/app/ML_Model/auto_scraper.py'


def test_trigger_training_creates_db_record(client, app):
    """Test that triggering training creates a database record"""
    from app.models import ModelTrainingRun
    
    with patch('app.main.subprocess.run') as mock_run, \
         patch('app.main.subprocess.Popen') as mock_popen, \
         patch('app.main.threading.Thread') as mock_thread:
        # Mock no running process
        mock_run.return_value = MagicMock(returncode=1)
        mock_popen.return_value = MagicMock(pid=12345)
        
        response = client.post('/api/trigger-training',
                              json={},
                              content_type='application/json')
        
        assert response.status_code == 202
        data = response.get_json()
        assert data['success'] is True
        assert 'training_id' in data
        
        # Verify database record was created
        with app.app_context():
            training_run = ModelTrainingRun.query.filter_by(id=data['training_id']).first()
            assert training_run is not None
            assert training_run.status == 'pending'


def test_trigger_training_with_pending_training(client, app):
    """Test that training cannot be triggered when one is already pending"""
    from app.models import ModelTrainingRun
    from app.main import db
    
    with app.app_context():
        # Create a pending training run
        existing_run = ModelTrainingRun(status='pending', notes='Test run')
        db.session.add(existing_run)
        db.session.commit()
        existing_id = existing_run.id
    
    response = client.post('/api/trigger-training',
                          json={},
                          content_type='application/json')
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert 'already in progress' in data['message'].lower()
    
    # Cleanup
    with app.app_context():
        ModelTrainingRun.query.filter_by(id=existing_id).delete()
        db.session.commit()


def test_trigger_training_env_vars_mapping(client):
    """Test that environment variables are correctly mapped for training script"""
    import time
    
    with patch('app.main.subprocess.run') as mock_run, \
         patch('app.main.subprocess.Popen') as mock_popen, \
         patch('os.environ', {'POSTGRES_DB': 'test_db', 'POSTGRES_USER': 'test_user', 'POSTGRES_PASSWORD': 'test_pass'}):
        
        mock_run.return_value = MagicMock(returncode=1)
        mock_popen.return_value = MagicMock(pid=12345)
        
        response = client.post('/api/trigger-training')
        
        assert response.status_code == 202
        
        # Give thread time to start
        time.sleep(0.1)
        
        # Verify Popen was called with environment variables
        assert mock_popen.called
        call_kwargs = mock_popen.call_args[1]
        assert 'env' in call_kwargs
        env = call_kwargs['env']
        assert env.get('DB_NAME') == 'test_db'
        assert env.get('DB_USER') == 'test_user'
        assert env.get('DB_PASS') == 'test_pass'
        assert env.get('DB_HOST') == 'db'


def test_trigger_scraping_env_vars_mapping(client):
    """Test that environment variables are correctly mapped for scraping script"""
    import time
    
    with patch('app.main.subprocess.run') as mock_run, \
         patch('app.main.subprocess.Popen') as mock_popen, \
         patch('os.environ', {'POSTGRES_DB': 'test_db', 'POSTGRES_USER': 'test_user', 'POSTGRES_PASSWORD': 'test_pass'}):
        
        mock_run.return_value = MagicMock(returncode=1)
        mock_popen.return_value = MagicMock(pid=12345)
        
        response = client.post('/api/trigger-scraping', json={'mode': 'incremental'})
        
        assert response.status_code == 202
        
        # Give thread time to start
        time.sleep(0.1)
        
        # Verify Popen was called with environment variables
        assert mock_popen.called
        call_kwargs = mock_popen.call_args[1]
        assert 'env' in call_kwargs
        env = call_kwargs['env']
        assert env.get('DB_NAME') == 'test_db'
        assert env.get('DB_USER') == 'test_user'
        assert env.get('DB_PASS') == 'test_pass'
