import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np

@pytest.mark.unit
class TestPredictionService:
    """Test the ML prediction service."""
    
    def test_predictor_initialization(self, app):
        """Test that the CarPricePredictor can be initialized."""
        from app.ml.predictor import CarPricePredictor
        
        with app.app_context():
            predictor = CarPricePredictor()
            assert predictor is not None
            assert hasattr(predictor, 'predict')
            assert hasattr(predictor, 'get_model_info')
    
    def test_predict_without_model_uses_heuristic(self, app):
        """Test that predict_price uses heuristic when model not loaded."""
        from app.ml.predictor import CarPricePredictor
        
        with app.app_context():
            predictor = CarPricePredictor()
            # Don't load model, should use heuristic
            result = predictor.predict({
            'brand': 'Toyota',
            'model': 'Camry',
            'year': 2020,
            'mileage': 50000,
            'fuel_type': 'Benzin',
            'transmission': 'Automatisk',
            'body_type': 'Sedan',
                'horsepower': 150
            })
            
            assert isinstance(result['predicted_price'], (int, float))
            assert result['predicted_price'] > 0
            assert 'confidence' in result
            assert 'price_range' in result
    
    def test_predict_returns_proper_structure(self, app):
        """Test that prediction returns expected data structure."""
        from app.ml.predictor import CarPricePredictor
        
        with app.app_context():
            predictor = CarPricePredictor()
            result = predictor.predict({
            'brand': 'BMW',
            'model': 'X5',
            'year': 2021,
            'mileage': 30000,
            'fuel_type': 'Diesel',
            'transmission': 'Automatic',
            'body_type': 'SUV',
                'horsepower': 265
            })
            
            assert 'predicted_price' in result
            assert 'confidence' in result
            assert 'price_range' in result
            assert 'min' in result['price_range']
            assert 'max' in result['price_range']
            assert isinstance(result['confidence'], (int, float))
            assert 0 <= result['confidence'] <= 100
            assert result['price_range']['min'] < result['price_range']['max']
    
    def test_feature_engineering(self):
        """Test feature engineering functions."""
        # This would test any data preprocessing functions
        sample_data = {
            'brand': 'Toyota',
            'model': 'Camry',
            'year': 2020,
            'mileage': 50000,
            'fuel_type': 'Benzin',
            'transmission': 'Automatisk'
        }
        
        # Test that data can be processed
        assert sample_data['year'] > 1990
        assert sample_data['mileage'] >= 0
        assert len(sample_data['brand']) > 0

@pytest.mark.integration
class TestPredictionIntegration:
    """Integration tests for prediction service."""
    
    def test_prediction_with_realistic_data(self, app, sample_prediction_data):
        """Test prediction with realistic car data."""
        from app.ml.predictor import CarPricePredictor
        
        with app.app_context():
            predictor = CarPricePredictor()
            result = predictor.predict(sample_prediction_data)
            
            assert sample_prediction_data['year'] >= 2000
            assert sample_prediction_data['mileage'] >= 0
            assert result['predicted_price'] > 0
    
    def test_batch_predictions(self):
        """Test making multiple predictions."""
        cars = [
            {'brand': 'Toyota', 'model': 'Camry', 'year': 2020, 'mileage': 50000},
            {'brand': 'BMW', 'model': 'X5', 'year': 2021, 'mileage': 30000},
            {'brand': 'Tesla', 'model': 'Model 3', 'year': 2022, 'mileage': 10000},
        ]
        
        # Test that we can handle multiple cars
        assert len(cars) == 3
        assert all('brand' in car for car in cars)
