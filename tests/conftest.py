import pytest
import sys
import os

# Set test database URL before importing app
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

# Add the app directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app as flask_app
from app.models import db

@pytest.fixture
def app():
    """Create and configure a test Flask application."""
    # Override database URI before any DB operations
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    flask_app.config['TESTING'] = True
    
    # Re-initialize the database with the test config
    with flask_app.app_context():
        # Drop any existing tables and recreate
        try:
            db.drop_all()
        except:
            pass
        db.create_all()
        yield flask_app
        # Cleanup
        db.session.remove()
        try:
            db.drop_all()
        except:
            pass

@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create a test CLI runner for the Flask application."""
    return app.test_cli_runner()

@pytest.fixture
def sample_car_data():
    """Sample car data for testing."""
    return {
        'id': 'test-car-123',
        'brand': 'Toyota',
        'model': 'Camry',
        'year': 2020,
        'mileage': 50000,
        'fuel_type': 'Benzin',
        'transmission': 'Automatisk',
        'body_type': 'Sedan',
        'price': 250000,
        'horsepower': 200,
        'engine_size': 2.5,
        'doors': 4,
        'color': 'Black',
        'location': 'Copenhagen',
    }

@pytest.fixture
def sample_prediction_data():
    """Sample prediction request data for testing."""
    return {
        'brand': 'Toyota',
        'model': 'Camry',
        'year': 2020,
        'mileage': 50000,
        'fuel_type': 'Benzin',
        'transmission': 'Automatisk',
        'body_type': 'Sedan',
        'horsepower': 200,
        'engine_size': 2.5,
        'doors': 4,
        'color': 'Black',
    }
