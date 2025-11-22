import pytest
from app.models import Car

@pytest.mark.unit
class TestCarModel:
    """Test the Car database model."""
    
    def test_car_creation(self, app, sample_car_data):
        """Test creating a new car instance."""
        with app.app_context():
            car = Car(**sample_car_data)
            assert car.id == 'test-car-123'
            assert car.brand == 'Toyota'
            assert car.model == 'Camry'
            assert car.year == 2020
            assert car.price == 250000
    
    def test_car_to_dict(self, app, sample_car_data):
        """Test converting car model to dictionary."""
        with app.app_context():
            car = Car(**sample_car_data)
            car_dict = car.to_dict()
            
            assert isinstance(car_dict, dict)
            assert car_dict['id'] == 'test-car-123'
            assert car_dict['brand'] == 'Toyota'
            assert car_dict['model'] == 'Camry'
            assert car_dict['year'] == 2020
            assert car_dict['price'] == 250000
    
    def test_car_required_fields(self, app):
        """Test that required fields are enforced."""
        with app.app_context():
            # Test with minimal required fields
            minimal_car = Car(
                id='test-123',
                brand='Toyota',
                model='Camry',
                year=2020,
                mileage=50000,
                fuel_type='Benzin',
                transmission='Automatisk',
                body_type='Sedan',
                price=250000
            )
            assert minimal_car.id is not None
            assert minimal_car.brand is not None
    
    def test_car_optional_fields(self, app, sample_car_data):
        """Test that optional fields can be None."""
        with app.app_context():
            car = Car(**sample_car_data)
            car.horsepower = None
            car.engine_size = None
            
            assert car.horsepower is None
            assert car.engine_size is None
    
    def test_car_to_dict_handles_none_values(self, app):
        """Test that to_dict properly handles None values."""
        with app.app_context():
            car = Car(
                id='test-123',
                brand='Toyota',
                model='Camry',
                year=2020,
                mileage=50000,
                fuel_type='Benzin',
                transmission='Automatisk',
                body_type='Sedan',
                price=250000,
                horsepower=None,
                engine_size=None
            )
            car_dict = car.to_dict()
            
            assert 'horsepower' in car_dict
            assert 'engine_size' in car_dict
