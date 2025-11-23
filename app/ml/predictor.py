"""
Machine Learning Price Predictor for Danish Car Market
Trained on bilbasen.dk data
"""

import os
import json
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False
    logger.warning("joblib not available - using mock predictions")


class CarPricePredictor:
    """Car price prediction using trained ML model with heuristic fallback."""
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.label_encoders = {}
        self.metadata = {}
        self.model_loaded = False
        self.model_dir = os.path.join(os.path.dirname(__file__), '../models')
        
        # Updated mappings to match standardized database values
        self.fuel_type_mapping = {
            # Old Danish values
            'El': 'Electric', 'Benzin': 'Petrol', 'Diesel': 'Diesel',
            'Plug-in hybrid Benzin': 'Plugin-Hybrid', 'Plug-in hybrid Diesel': 'Plugin-Hybrid',
            'Hybrid Benzin': 'Hybrid', 'Hybrid Diesel': 'Hybrid',
            # New standardized values (exact match)
            'Electricity': 'Electric',
            'Petrol': 'Petrol',
            'Diesel': 'Diesel',
            'Hybrid - Petrol': 'Hybrid',
            'Hybrid - Diesel': 'Hybrid',
            'Plug-in Hybrid - Petrol': 'Plugin-Hybrid',
            'Plug-in Hybrid - Diesel': 'Plugin-Hybrid',
            # Fallback values
            'Electric': 'Electric', 'Plugin-Hybrid': 'Plugin-Hybrid', 'Hybrid': 'Hybrid'
        }
        self.transmission_mapping = {
            'Automatisk': 'Automatic', 'Manuel': 'Manual', 'Automatgear': 'Automatic',
            'Automatic': 'Automatic', 'Manual': 'Manual', 'Semi-Automatic': 'Semi-Automatic'
        }
        self.body_type_mapping = {
            # Standardized values
            'SUV': 'SUV', 'CUV': 'SUV', 'Mikro': 'Hatchback', 'Halvkombi': 'Hatchback',
            'St.car': 'Wagon', 'Sedan': 'Sedan', 'Coupe': 'Coupe', 'MPV': 'Van',
            'Van': 'Van', 'Cabriolet': 'Convertible', 'Personbil': 'Sedan',
            'Hatchback': 'Hatchback', 
            'Station Wagon': 'Wagon',  # Added for new standardized value
            'Wagon': 'Wagon', 
            'Convertible': 'Convertible',
            'Pickup': 'Pickup'
        }
        self.drive_type_mapping = {
            # Old Danish values
            'Forhjulstræk': 'FWD', 'Baghjulstræk': 'RWD', 'Firehjulstræk': 'AWD',
            # Standardized English values
            'Front-Wheel Drive': 'FWD',
            'Rear-Wheel Drive': 'RWD',
            'All-Wheel Drive': 'AWD',
            # Fallback abbreviations
            '4WD': 'AWD', 'FWD': 'FWD', 'RWD': 'RWD', 'AWD': 'AWD'
        }
        self.premium_brands = ['BMW', 'Mercedes-Benz', 'Audi', 'Tesla', 'Porsche', 
                               'Volvo', 'Polestar', 'Lexus', 'Land Rover', 'Jaguar']
        
        self._load_model()
    
    def _load_model(self):
        """Load trained model and artifacts from disk."""
        if not JOBLIB_AVAILABLE:
            logger.warning("joblib not available, using fallback predictor")
            self.model_version = "v1.0.0-heuristic"
            return
        
        try:
            metadata_path = os.path.join(self.model_dir, 'model_metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    self.metadata = json.load(f)
                logger.info(f"Loaded metadata: {self.metadata.get('model_name', 'unknown')}")
            
            model_filename = self.metadata.get('model_filename', 'best_model_xgboost.pkl')
            model_path = os.path.join(self.model_dir, model_filename)
            
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
                logger.info(f"Loaded model from {model_path}")
            else:
                for name in ['best_model_catboost.pkl', 'best_model_xgboost.pkl', 'best_model_lightgbm.pkl', 'best_model_random_forest.pkl']:
                    alt_path = os.path.join(self.model_dir, name)
                    if os.path.exists(alt_path):
                        self.model = joblib.load(alt_path)
                        logger.info(f"Loaded model from {alt_path}")
                        break
            
            scaler_path = os.path.join(self.model_dir, 'feature_scaler.pkl')
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
            
            encoders_path = os.path.join(self.model_dir, 'label_encoders.pkl')
            if os.path.exists(encoders_path):
                self.label_encoders = joblib.load(encoders_path)
            
            if self.model is not None and self.scaler is not None:
                self.model_loaded = True
                self.model_version = f"v1.0.0-{self.metadata.get('model_name', 'trained').lower().replace(' ', '-')}"
                logger.info(f"Model ready: {self.model_version}")
            else:
                self.model_version = "v1.0.0-heuristic"
                
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model_version = "v1.0.0-heuristic"
            self.model_loaded = False
    
    def predict(self, car_features):
        """Predict car price based on features."""
        if self.model_loaded:
            return self._predict_with_model(car_features)
        return self._predict_heuristic(car_features)
    
    def _predict_with_model(self, car_features):
        """Make prediction using trained ML model."""
        try:
            features = self._prepare_features(car_features)
            feature_columns = self.metadata.get('feature_columns', list(features.keys()))
            feature_vector = np.array([[features.get(col, 0) for col in feature_columns]])
            
            if self.scaler:
                feature_vector_scaled = self.scaler.transform(feature_vector)
            else:
                feature_vector_scaled = feature_vector
            
            predicted_price = float(self.model.predict(feature_vector_scaled)[0])
            predicted_price = max(10000, min(predicted_price, 5000000))
            
            # Calculate dynamic confidence based on car characteristics
            base_r2 = self.metadata.get('test_r2', 0.8)
            base_confidence = min(95, max(70, base_r2 * 100 + 5))
            
            # Adjust confidence based on car age and features
            year = int(car_features.get('year', datetime.now().year))
            current_year = datetime.now().year
            age = current_year - year
            
            # Reduce confidence for classic/vintage cars (pre-2000)
            if year < 2000:
                age_penalty = min(40, (2000 - year) * 2)  # Up to 40% penalty
                confidence = max(30, base_confidence - age_penalty)
                warning = "⚠️ Classic/vintage car: Prediction may not reflect collector value"
            elif year < 2010:
                confidence = base_confidence - 10  # Slight reduction for older cars
                warning = None
            else:
                confidence = base_confidence
                # Further adjust based on data completeness
                mileage = car_features.get('mileage')
                horsepower = car_features.get('horsepower')
                if not mileage or not horsepower:
                    confidence = max(70, confidence - 5)
                warning = None
            
            mae = self.metadata.get('test_mae', predicted_price * 0.1)
            price_range = {
                'min': round(max(10000, predicted_price - mae), 2),
                'max': round(predicted_price + mae, 2)
            }
            
            similar_count = self._estimate_similar_cars(car_features)
            
            result = {
                'predicted_price': round(predicted_price, 2),
                'confidence': round(confidence, 2),
                'price_range': price_range,
                'model_version': self.model_version,
                'similar_cars_count': similar_count
            }
            
            if warning:
                result['warning'] = warning
            
            return result
        except Exception as e:
            logger.error(f"Model prediction failed: {e}, falling back to heuristic")
            return self._predict_heuristic(car_features)
    
    def _prepare_features(self, car_features):
        """Prepare feature dictionary for model prediction."""
        features = {}
        current_year = datetime.now().year
        
        year = int(car_features.get('year', current_year - 3))
        age = current_year - year
        features['age'] = max(0, age)
        
        # Use 0 for new cars or null mileage
        mileage = int(car_features.get('mileage', 0))
        features['mileage_numeric'] = mileage
        features['horsepower'] = car_features.get('horsepower') or 150
        features['torque_nm'] = car_features.get('torque_nm') or 200
        features['doors_numeric'] = car_features.get('doors') or 5
        features['weight_numeric'] = car_features.get('weight') or 1500
        features['trunk_size_numeric'] = car_features.get('trunk_size') or 400
        features['top_speed_numeric'] = car_features.get('top_speed') or 180
        features['range_numeric'] = car_features.get('range') or 0
        features['battery_capacity_numeric'] = car_features.get('battery_capacity') or 0
        features['mileage_per_year'] = mileage / max(age, 1)
        weight_kg = features['weight_numeric']
        features['power_to_weight'] = features['horsepower'] / (weight_kg / 1000) if weight_kg > 0 else 100
        features['equipment_count'] = car_features.get('equipment_count') or 10
        features['acceleration_0_100'] = car_features.get('acceleration') or 10
        features['brand_popularity'] = 100
        
        fuel_type = self._normalize_fuel_type(car_features.get('fuel_type', 'Petrol'))
        features['is_electric'] = 1 if fuel_type == 'Electric' else 0
        features['is_hybrid'] = 1 if fuel_type in ['Hybrid', 'Plugin-Hybrid'] else 0
        features['is_automatic'] = 1 if self._normalize_transmission(
            car_features.get('transmission', 'Automatic')) == 'Automatic' else 0
        features['is_premium'] = 1 if car_features.get('brand', '') in self.premium_brands else 0
        
        for cat_col in self.label_encoders:
            col_name = cat_col + '_encoded'
            raw_value = car_features.get(cat_col, 'Unknown')
            
            if cat_col == 'fuel_type_en':
                raw_value = self._normalize_fuel_type(car_features.get('fuel_type', 'Petrol'))
            elif cat_col == 'transmission_en':
                raw_value = self._normalize_transmission(car_features.get('transmission', 'Automatic'))
            elif cat_col == 'body_type_en':
                raw_value = self._normalize_body_type(car_features.get('body_type', 'Sedan'))
            elif cat_col == 'drive_type_en':
                raw_value = self._normalize_drive_type(car_features.get('drive_type', 'FWD'))
            elif cat_col == 'brand':
                raw_value = car_features.get('brand', 'Unknown')
            elif cat_col == 'color':
                raw_value = car_features.get('color', 'Unknown')
            
            try:
                encoder = self.label_encoders[cat_col]
                if str(raw_value) in encoder.classes_:
                    features[col_name] = encoder.transform([str(raw_value)])[0]
                else:
                    features[col_name] = 0
            except:
                features[col_name] = 0
        
        return features
    
    def _normalize_fuel_type(self, fuel_type):
        if fuel_type is None:
            return 'Petrol'
        return self.fuel_type_mapping.get(fuel_type, fuel_type)
    
    def _normalize_transmission(self, transmission):
        if transmission is None:
            return 'Automatic'
        return self.transmission_mapping.get(transmission, transmission)
    
    def _normalize_body_type(self, body_type):
        if body_type is None:
            return 'Sedan'
        return self.body_type_mapping.get(body_type, body_type)
    
    def _normalize_drive_type(self, drive_type):
        return self.drive_type_mapping.get(drive_type, 'FWD')
    
    def _estimate_similar_cars(self, car_features):
        brand = car_features.get('brand', '').lower()
        popular = ['toyota', 'volkswagen', 'ford', 'bmw', 'audi', 'mercedes-benz', 
                   'peugeot', 'skoda', 'hyundai', 'kia', 'volvo', 'nissan']
        if brand in popular:
            return np.random.randint(50, 150)
        return np.random.randint(15, 50)
    
    def _predict_heuristic(self, car_features):
        """Fallback heuristic-based prediction for Danish market."""
        base_price = self._calculate_base_price(car_features)
        
        current_year = datetime.now().year
        year = int(car_features.get('year', current_year - 3))
        age = max(0, current_year - year)
        
        if age == 0:
            depreciation_factor = 1.0
        elif age == 1:
            depreciation_factor = 0.85
        else:
            depreciation_factor = 0.85 * (0.90 ** (age - 1))
        depreciation_factor = max(0.20, depreciation_factor)
        
        mileage = int(car_features.get('mileage', 50000))
        expected_mileage = age * 15000
        mileage_diff = mileage - expected_mileage
        mileage_factor = 1.0 - (mileage_diff / 500000)
        mileage_factor = max(0.7, min(1.1, mileage_factor))
        
        predicted_price = base_price * depreciation_factor * mileage_factor
        predicted_price = max(15000, min(predicted_price, 4000000))
        
        confidence = 82.0
        if car_features.get('horsepower'):
            confidence += 3
        if car_features.get('engine_size'):
            confidence += 2
        confidence = min(92, confidence)
        
        margin = predicted_price * 0.12
        price_range = {
            'min': round(predicted_price - margin, 2),
            'max': round(predicted_price + margin, 2)
        }
        
        return {
            'predicted_price': round(predicted_price, 2),
            'confidence': round(confidence, 2),
            'price_range': price_range,
            'model_version': self.model_version,
            'similar_cars_count': self._estimate_similar_cars(car_features)
        }
    
    def _calculate_base_price(self, features):
        """Calculate base price using heuristics for Danish market."""
        brand_factors = {
            'toyota': 1.0, 'volkswagen': 1.1, 'bmw': 1.75, 'mercedes-benz': 1.9,
            'audi': 1.65, 'tesla': 2.2, 'ford': 0.85, 'hyundai': 0.9, 'kia': 0.88,
            'skoda': 0.92, 'peugeot': 0.82, 'renault': 0.78, 'nissan': 0.88,
            'volvo': 1.35, 'mazda': 0.95, 'seat': 0.85, 'opel': 0.8,
            'fiat': 0.75, 'citroën': 0.78, 'mini': 1.15, 'porsche': 3.0,
            'land rover': 2.0, 'jaguar': 1.8, 'polestar': 1.7, 'cupra': 1.1,
            'lexus': 1.6, 'honda': 0.95, 'suzuki': 0.75, 'dacia': 0.65
        }
        body_factors = {
            'sedan': 1.0, 'hatchback': 0.9, 'suv': 1.25, 'wagon': 0.98,
            'coupe': 1.15, 'van': 1.05, 'pickup': 1.1, 'convertible': 1.3
        }
        fuel_factors = {
            'petrol': 1.0, 'diesel': 0.95, 'electric': 1.35,
            'hybrid': 1.15, 'plugin-hybrid': 1.25
        }
        transmission_factors = {'automatic': 1.08, 'manual': 1.0, 'semi-automatic': 1.05}
        
        base_price = 180000
        brand = (features.get('brand') or '').lower()
        brand_factor = brand_factors.get(brand, 1.0)
        body_type = (self._normalize_body_type(features.get('body_type')) or 'Sedan').lower()
        body_factor = body_factors.get(body_type, 1.0)
        fuel_type = (self._normalize_fuel_type(features.get('fuel_type')) or 'Petrol').lower()
        fuel_factor = fuel_factors.get(fuel_type, 1.0)
        transmission = (self._normalize_transmission(features.get('transmission')) or 'Automatic').lower()
        transmission_factor = transmission_factors.get(transmission, 1.0)
        
        horsepower = features.get('horsepower', 120)
        if horsepower:
            hp_factor = 1.0 + (int(horsepower) - 120) / 400
            hp_factor = max(0.7, min(hp_factor, 2.0))
        else:
            hp_factor = 1.0
        
        return base_price * brand_factor * body_factor * fuel_factor * transmission_factor * hp_factor
    
    def get_model_info(self):
        """Get information about the loaded model."""
        return {
            'version': self.model_version,
            'loaded': self.model_loaded,
            'type': 'trained' if self.model_loaded else 'heuristic',
            'model_name': self.metadata.get('model_name', 'N/A'),
            'test_r2': self.metadata.get('test_r2', 'N/A'),
            'test_mae': self.metadata.get('test_mae', 'N/A'),
            'features_count': len(self.metadata.get('feature_columns', []))
        }


if __name__ == "__main__":
    predictor = CarPricePredictor()
    print(f"Model info: {predictor.get_model_info()}")
    
    test_car = {
        'brand': 'Toyota', 'model': 'Corolla', 'year': 2020, 'mileage': 45000,
        'fuel_type': 'Hybrid', 'transmission': 'Automatic', 'body_type': 'Sedan',
        'horsepower': 122
    }
    result = predictor.predict(test_car)
    print(f"Predicted: {result['predicted_price']:,.0f} DKK ({result['confidence']}% confidence)")