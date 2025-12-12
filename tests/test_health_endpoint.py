"""
Comprehensive tests for the health check endpoint.
Tests all branches including database connection, ML model status, and error handling.
"""
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import OperationalError


@pytest.mark.api
class TestHealthEndpoint:
    """Test the /health endpoint with comprehensive coverage."""
    
    def test_health_check_success(self, client):
        """Test health check with successful database connection."""
        response = client.get('/health')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'status' in data
        assert 'service' in data
        assert 'version' in data
        assert 'timestamp' in data
        assert 'database' in data
        assert 'ml_model' in data
        
        # Should be healthy when db is connected
        assert data['status'] == 'healthy'
        assert data['database']['status'] == 'connected'
        assert data['service'] == 'BPR Backend API'
    
    def test_health_check_database_error(self, client, app):
        """Test health check when database connection fails."""
        with app.app_context():
            # Mock database execute to raise an error
            with patch('app.main.db.session.execute') as mock_execute:
                mock_execute.side_effect = OperationalError(
                    "connection failed",
                    {},
                    Exception("Database connection refused")
                )
                
                response = client.get('/health')
                
                # Should return 503 when database is down
                assert response.status_code == 503
                
                data = response.get_json()
                assert data['status'] == 'degraded'
                assert 'error' in data['database']['status'].lower()
    
    def test_health_check_ml_model_info(self, client):
        """Test that health check returns ML model information."""
        response = client.get('/health')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'ml_model' in data
        
        # ML model info should be present (could be None, dict, or error dict)
        ml_info = data['ml_model']
        if ml_info and isinstance(ml_info, dict) and 'error' not in ml_info:
            # If predictor is initialized, should have model info
            assert 'name' in ml_info or 'algorithm' in ml_info
    
    def test_health_check_predictor_not_initialized(self, client, app):
        """Test health check when predictor is not initialized."""
        with app.app_context():
            # Mock predictor to be None
            with patch('app.main.predictor', None):
                response = client.get('/health')
                
                # Should still return 200 (or 503 if db is also down)
                assert response.status_code in [200, 503]
                
                data = response.get_json()
                assert 'ml_model' in data
                # When predictor is None, ml_model could be None or error dict
                # Just verify it's in the response, value depends on DB state
                assert data['ml_model'] is None or isinstance(data['ml_model'], dict)
    
    def test_health_check_timestamp_format(self, client):
        """Test that health check returns valid ISO timestamp."""
        response = client.get('/health')
        assert response.status_code == 200
        
        data = response.get_json()
        timestamp = data.get('timestamp')
        assert timestamp is not None
        
        # Should be valid ISO format
        from datetime import datetime
        try:
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            timestamp_valid = True
        except ValueError:
            timestamp_valid = False
        
        assert timestamp_valid
    
    def test_health_check_response_structure(self, client):
        """Test that health check response has all required fields."""
        response = client.get('/health')
        assert response.status_code in [200, 503]
        
        data = response.get_json()
        required_fields = ['status', 'service', 'version', 'timestamp', 'database', 'ml_model']
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
    
    def test_health_check_version(self, client):
        """Test that health check returns version information."""
        response = client.get('/health')
        assert response.status_code in [200, 503]
        
        data = response.get_json()
        assert 'version' in data
        assert data['version'] == '1.0.0'
    
    def test_health_check_only_get_method(self, client):
        """Test that health endpoint only accepts GET method."""
        # POST should not be allowed
        response = client.post('/health')
        assert response.status_code == 405
        
        # PUT should not be allowed
        response = client.put('/health')
        assert response.status_code == 405
        
        # DELETE should not be allowed
        response = client.delete('/health')
        assert response.status_code == 405
    
    def test_health_check_content_type(self, client):
        """Test that health check returns JSON content type."""
        response = client.get('/health')
        assert response.status_code in [200, 503]
        assert response.content_type == 'application/json'
    
    def test_health_check_database_status_values(self, client):
        """Test that database status has expected values."""
        response = client.get('/health')
        assert response.status_code in [200, 503]
        
        data = response.get_json()
        db_status = data['database']['status']
        
        # Should be either 'connected' or contain 'error'
        assert db_status == 'connected' or 'error' in db_status.lower()
    
    def test_health_check_status_values(self, client):
        """Test that overall status has expected values."""
        response = client.get('/health')
        assert response.status_code in [200, 503]
        
        data = response.get_json()
        status = data['status']
        
        # Status should be either 'healthy' or 'degraded'
        assert status in ['healthy', 'degraded']
    
    def test_health_check_multiple_calls(self, client):
        """Test that health check can be called multiple times."""
        # First call
        response1 = client.get('/health')
        assert response1.status_code in [200, 503]
        
        # Second call
        response2 = client.get('/health')
        assert response2.status_code in [200, 503]
        
        # Third call
        response3 = client.get('/health')
        assert response3.status_code in [200, 503]
        
        # All should have same structure
        data1 = response1.get_json()
        data2 = response2.get_json()
        data3 = response3.get_json()
        
        assert set(data1.keys()) == set(data2.keys())
        assert set(data2.keys()) == set(data3.keys())
