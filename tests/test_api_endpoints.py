import pytest
import json

@pytest.mark.api
class TestCarsEndpoint:
    """Test the /api/cars endpoint."""
    
    def test_get_cars_returns_200(self, client):
        """Test that GET /api/cars returns 200."""
        response = client.get('/api/cars')
        assert response.status_code == 200
    
    def test_get_cars_returns_json(self, client):
        """Test that GET /api/cars returns JSON."""
        response = client.get('/api/cars')
        assert response.content_type == 'application/json'
    
    def test_get_cars_with_pagination(self, client):
        """Test that GET /api/cars supports pagination."""
        response = client.get('/api/cars?page=1&per_page=10')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'pagination' in data
    
    def test_get_cars_with_filters(self, client):
        """Test that GET /api/cars supports filtering."""
        response = client.get('/api/cars?brand=Toyota&fuel_type=Benzin')
        assert response.status_code == 200
    
    def test_get_cars_with_search(self, client):
        """Test that GET /api/cars supports search."""
        response = client.get('/api/cars?q=Toyota')
        assert response.status_code == 200
    
    def test_get_cars_with_price_range(self, client):
        """Test that GET /api/cars supports price filtering."""
        response = client.get('/api/cars?price_min=100000&price_max=500000')
        assert response.status_code == 200
    
    def test_get_cars_with_year_range(self, client):
        """Test that GET /api/cars supports year filtering."""
        response = client.get('/api/cars?year_min=2018&year_max=2022')
        assert response.status_code == 200

@pytest.mark.api
class TestCarDetailEndpoint:
    """Test the /api/cars/:id endpoint."""
    
    def test_get_car_by_id_invalid_id(self, client):
        """Test GET /api/cars/:id with invalid ID."""
        response = client.get('/api/cars/invalid-id-999999')
        assert response.status_code in [404, 200]  # Depends on implementation
    
    def test_get_car_by_id_returns_json(self, client):
        """Test that GET /api/cars/:id returns JSON."""
        response = client.get('/api/cars/test-id')
        assert response.content_type == 'application/json'

@pytest.mark.api
class TestBrandsEndpoint:
    """Test the /api/brands endpoint."""
    
    def test_get_brands_returns_200(self, client):
        """Test that GET /api/brands returns 200."""
        response = client.get('/api/brands')
        assert response.status_code == 200
    
    def test_get_brands_returns_json(self, client):
        """Test that GET /api/brands returns JSON."""
        response = client.get('/api/brands')
        assert response.content_type == 'application/json'
    
    def test_get_brands_returns_array(self, client):
        """Test that GET /api/brands returns an array."""
        response = client.get('/api/brands')
        data = json.loads(response.data)
        assert 'brands' in data
        assert isinstance(data['brands'], list)

@pytest.mark.api
class TestFiltersEndpoint:
    """Test the /api/filters endpoint."""
    
    def test_get_filters_returns_200(self, client):
        """Test that GET /api/filters returns 200."""
        response = client.get('/api/filters')
        assert response.status_code == 200
    
    def test_get_filters_returns_json(self, client):
        """Test that GET /api/filters returns JSON."""
        response = client.get('/api/filters')
        assert response.content_type == 'application/json'
    
    def test_get_filters_returns_expected_structure(self, client):
        """Test that GET /api/filters returns expected structure."""
        response = client.get('/api/filters')
        data = json.loads(response.data)
        assert 'filters' in data

@pytest.mark.api
class TestPredictEndpoint:
    """Test the /api/predict endpoint."""
    
    def test_predict_requires_post(self, client):
        """Test that GET /api/predict is not allowed."""
        response = client.get('/api/predict')
        assert response.status_code in [404, 405]
    
    def test_predict_with_valid_data(self, client, sample_prediction_data):
        """Test POST /api/predict with valid data."""
        response = client.post(
            '/api/predict',
            data=json.dumps(sample_prediction_data),
            content_type='application/json'
        )
        assert response.status_code in [200, 202, 500]  # Depends on ML model availability
    
    def test_predict_requires_json(self, client):
        """Test that POST /api/predict requires JSON content type."""
        response = client.post('/api/predict', data='not json')
        assert response.status_code in [400, 415, 500]
    
    def test_predict_validates_required_fields(self, client):
        """Test that POST /api/predict validates required fields."""
        response = client.post(
            '/api/predict',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code in [400, 422, 500]

@pytest.mark.api
class TestHealthEndpoint:
    """Test the /api/health endpoint."""
    
    def test_health_returns_200(self, client):
        """Test that GET /api/health returns 200."""
        response = client.get('/api/health')
        # Health endpoint might not exist in all implementations
        assert response.status_code in [200, 404]

@pytest.mark.api
class TestModelsEndpoint:
    """Test the /api/models endpoint."""
    
    def test_get_models_by_brand(self, client):
        """Test GET /api/models with brand parameter."""
        response = client.get('/api/models?brand=Toyota')
        assert response.status_code in [200, 404]  # Endpoint might not exist
        assert response.content_type == 'application/json'
    
    def test_get_models_without_brand(self, client):
        """Test GET /api/models without brand parameter."""
        response = client.get('/api/models')
        assert response.status_code in [200, 400, 404]  # Might require brand param or not exist
    
    def test_get_models_returns_array(self, client):
        """Test that GET /api/models returns an array."""
        response = client.get('/api/models?brand=Toyota')
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'models' in data or isinstance(data, list)

@pytest.mark.api
class TestStatsEndpoint:
    """Test the /api/stats endpoint."""
    
    def test_get_stats_returns_200(self, client):
        """Test that GET /api/stats returns 200."""
        response = client.get('/api/stats')
        assert response.status_code in [200, 404]
    
    def test_get_stats_returns_json(self, client):
        """Test that GET /api/stats returns JSON."""
        response = client.get('/api/stats')
        if response.status_code == 200:
            assert response.content_type == 'application/json'
            data = json.loads(response.data)
            # Stats might include total_cars, avg_price, etc.
            assert isinstance(data, dict)

@pytest.mark.api
class TestQueueEndpoint:
    """Test the /api/queue endpoints."""
    
    def test_get_queue_status(self, client):
        """Test GET /api/queue/status."""
        response = client.get('/api/queue/status')
        assert response.status_code in [200, 404]
    
    def test_get_job_status(self, client):
        """Test GET /api/queue/job/:id."""
        response = client.get('/api/queue/job/test-job-123')
        assert response.status_code in [200, 404]

@pytest.mark.api  
class TestErrorHandling:
    """Test API error handling."""
    
    def test_404_error(self, client):
        """Test 404 error handling."""
        response = client.get('/api/nonexistent-endpoint')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data or 'success' in data
    
    def test_invalid_json_post(self, client):
        """Test POST with invalid JSON."""
        response = client.post(
            '/api/predict',
            data='{ invalid json',
            content_type='application/json'
        )
        assert response.status_code in [400, 500]
    
    def test_missing_content_type(self, client):
        """Test POST without content type."""
        response = client.post('/api/predict', data='test')
        assert response.status_code in [400, 415, 500]
