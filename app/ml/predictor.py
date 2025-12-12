"""
Machine Learning Price Predictor for Danish Car Market
Trained on bilbasen.dk data
"""

import os
import json
import sys
import numpy as np
from datetime import datetime
import logging

# Import TargetEncoder and inject into __main__ for joblib unpickling
from app.ml.encoding import TargetEncoder
# Make TargetEncoder available in __main__ namespace for pickle
import __main__
__main__.TargetEncoder = TargetEncoder

logger = logging.getLogger(__name__)

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False
    logger.warning("joblib not available - using mock predictions")

try:
    import torch
    from app.ml.pytorch_models import ImprovedLSTMNetwork, ImprovedGRUNetwork
    # Make PyTorch model classes available in __main__ namespace for torch.load unpickling
    __main__.ImprovedLSTMNetwork = ImprovedLSTMNetwork
    __main__.ImprovedGRUNetwork = ImprovedGRUNetwork
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    ImprovedLSTMNetwork = None
    ImprovedGRUNetwork = None
    logger.warning("PyTorch not available - cannot load LSTM/GRU models")


class CarPricePredictor:
    """Car price prediction using trained ML models. Supports all 10 trained models."""
    
    def __init__(self, model_name=None):
        self.models = {}  # Cache of loaded models {model_name: model_data}
        self.current_model_name = model_name  # Selected model, None = best model
        self.model_dir = os.path.join(os.path.dirname(__file__), '../models')
        
        # Will be set when loading a model
        self.model = None
        self.scaler = None
        self.label_encoders = {}
        self.target_encoders = {}
        self.category_mappings = {}
        self.numeric_medians = {}
        self.feature_names = []
        self.metadata = {}
        self.model_loaded = False
        
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
        
        # Load the specified model or best available model
        self._load_model(self.current_model_name)
    
    def _load_model(self, model_name=None):
        """
        Load trained model from disk. 
        Args:
            model_name (str, optional): Specific model to load (e.g., 'XGBoost', 'GRU'). 
                                       If None, loads best available model by R² score.
        """
        if not JOBLIB_AVAILABLE:
            raise RuntimeError("joblib not available - cannot load ML models")
        
        try:
            ml_model_dir = '/app/app/models'
            logger.info(f"Loading model: {model_name or 'best available'} from {ml_model_dir}")
            
            # Get models from database
            from app.models import MLModel
            
            # Build query - filter by name if specified
            query = MLModel.query.filter_by(is_active=True)
            
            if model_name:
                # Specific model requested
                query = query.filter_by(name=model_name)
                models = query.all()
                if not models:
                    raise ValueError(f"Model '{model_name}' not found in database")
            else:
                # Get best model by R² score
                query = query.order_by(MLModel.r2_score.desc())
                models = query.all()
            
            # Try to load the first available model file
            loaded_model_data = None
            for db_model in models:
                model_path = self._normalize_model_path(db_model.model_file_path)
                
                if not os.path.exists(model_path):
                    logger.debug(f"⚠️ Model file not found: {db_model.name} at {model_path}")
                    continue
                
                try:
                    logger.info(f"Loading {db_model.name} from {model_path}")
                    
                    # Determine file type and load accordingly
                    if model_path.endswith('.pt'):
                        # PyTorch model
                        if not TORCH_AVAILABLE:
                            logger.warning(f"Skipping {db_model.name} - PyTorch not available")
                            continue
                        
                        # Load PyTorch model checkpoint
                        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
                        
                        # Reconstruct model from state_dict
                        if 'model_state_dict' in checkpoint:
                            # Determine which architecture to use
                            input_dim = checkpoint.get('input_dim', 50)
                            params = checkpoint.get('params', {})
                            
                            if db_model.name == 'LSTM':
                                model = ImprovedLSTMNetwork(
                                    input_dim=input_dim,
                                    hidden_dim=params.get('hidden_dim', 128),
                                    num_layers=params.get('num_layers', 2),
                                    dropout=params.get('dropout', 0.3)
                                )
                            elif db_model.name == 'GRU':
                                model = ImprovedGRUNetwork(
                                    input_dim=input_dim,
                                    hidden_dim=params.get('hidden_dim', 128),
                                    num_layers=params.get('num_layers', 2),
                                    dropout=params.get('dropout', 0.3)
                                )
                            else:
                                logger.error(f"Unknown PyTorch model type: {db_model.name}")
                                continue
                            
                            model.load_state_dict(checkpoint['model_state_dict'])
                            model.eval()
                            
                            # Load preprocessing objects from separate file
                            preprocessing_path = model_path.rsplit('.', 1)[0] + '_preprocessing.pkl'
                            preprocessing = {}
                            if os.path.exists(preprocessing_path):
                                preprocessing = joblib.load(preprocessing_path)
                                logger.info(f"Loaded preprocessing from {preprocessing_path}")
                            else:
                                logger.warning(f"Preprocessing file not found: {preprocessing_path}")
                            
                            # Create a package-like structure
                            loaded_obj = {
                                'model': model,
                                'y_mean': checkpoint.get('y_mean', 0),
                                'y_std': checkpoint.get('y_std', 1),
                                'scaler': preprocessing.get('scaler'),
                                'target_encoders': preprocessing.get('target_encoders', {}),
                                'category_mappings': preprocessing.get('category_mappings', {}),
                                'numeric_medians': preprocessing.get('numeric_medians', {}),
                                'feature_names': preprocessing.get('feature_names', []),
                                'input_dim': input_dim,
                                'params': params
                            }
                        else:
                            # Old format - direct model object
                            loaded_obj = checkpoint
                    else:
                        # Joblib model (.pkl)
                        loaded_obj = joblib.load(model_path)
                    
                    # Check if it's a package (v3 format) or standalone model
                    if isinstance(loaded_obj, dict) and 'model' in loaded_obj:
                        # v3 package format
                        loaded_model_data = {
                            'model': loaded_obj['model'],
                            'scaler': loaded_obj.get('scaler'),
                            'target_encoders': loaded_obj.get('target_encoders', {}),
                            'category_mappings': loaded_obj.get('category_mappings', {}),
                            'numeric_medians': loaded_obj.get('numeric_medians', {}),
                            'feature_names': loaded_obj.get('feature_names', []),
                            'y_mean': loaded_obj.get('y_mean', 0),
                            'y_std': loaded_obj.get('y_std', 1),
                            'name': db_model.name,
                            'version': f"v3.0.0-{db_model.name.lower().replace(' ', '-')}",
                            'r2_score': db_model.r2_score,
                            'mae': db_model.mae,
                            'rmse': db_model.rmse
                        }
                        logger.info(f"✅ Loaded {db_model.name} (R²={db_model.r2_score:.4f}, MAE={db_model.mae:.0f})")
                    else:
                        # Old standalone format - load it but less preferred
                        loaded_model_data = {
                            'model': loaded_obj,
                            'scaler': None,
                            'target_encoders': {},
                            'category_mappings': {},
                            'numeric_medians': {},
                            'feature_names': [],
                            'name': db_model.name,
                            'version': f"v2.0.0-{db_model.name.lower().replace(' ', '-')}",
                            'r2_score': db_model.r2_score,
                            'mae': db_model.mae,
                            'rmse': db_model.rmse
                        }
                        logger.warning(f"Loaded {db_model.name} in old format (missing preprocessing artifacts)")
                    
                    break  # Successfully loaded
                    
                except Exception as e:
                    logger.error(f"Failed to load {db_model.name}: {e}")
                    continue
            
            if not loaded_model_data:
                raise RuntimeError(f"No valid model files found for: {model_name or 'any model'}")
            
            # Set instance variables from loaded model
            self.model = loaded_model_data['model']
            
            # Set PyTorch models to eval mode
            if TORCH_AVAILABLE and hasattr(self.model, 'eval'):
                self.model.eval()
                logger.info(f"Set {loaded_model_data['name']} to eval mode")
            
            self.scaler = loaded_model_data['scaler']
            self.target_encoders = loaded_model_data['target_encoders']
            self.category_mappings = loaded_model_data['category_mappings']
            self.numeric_medians = loaded_model_data['numeric_medians']
            self.feature_names = loaded_model_data['feature_names']
            self.y_mean = loaded_model_data.get('y_mean', 0)
            self.y_std = loaded_model_data.get('y_std', 1)
            self.current_model_name = loaded_model_data['name']
            self.model_version = loaded_model_data['version']
            self.metadata = {
                'model_name': loaded_model_data['name'],
                'test_r2': loaded_model_data['r2_score'],
                'test_mae': loaded_model_data['mae'],
                'test_rmse': loaded_model_data['rmse'],
                'feature_columns': self.feature_names
            }
            self.model_loaded = True
            
            logger.info(f"✅ Model ready: {self.current_model_name} ({self.model_version})")
                
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise RuntimeError(f"Failed to load model: {e}")
    
    def _normalize_model_path(self, path):
        """Convert database model path to container path."""
        if path.startswith('/app'):
            return path
        elif path.startswith('/home/igor/BachelorApi/BPR-BackEnd-API'):
            return path.replace('/home/igor/BachelorApi/BPR-BackEnd-API/app/models', '/app/app/models')
        else:
            # Assume relative path from models directory
            return f'/app/app/models/{path}'
    
    def switch_model(self, model_name):
        """
        Switch to a different trained model.
        Args:
            model_name (str): Name of the model to switch to (e.g., 'XGBoost', 'GRU')
        """
        if model_name == self.current_model_name:
            logger.info(f"Already using model: {model_name}")
            return
        
        logger.info(f"Switching from {self.current_model_name} to {model_name}")
        self._load_model(model_name)
    
    def get_available_models(self):
        """Get list of all available models from database."""
        try:
            from app.models import MLModel
            models = MLModel.query.filter_by(is_active=True).order_by(MLModel.r2_score.desc()).all()
            
            return [{
                'name': m.name,
                'r2_score': m.r2_score,
                'mae': m.mae,
                'rmse': m.rmse,
                'training_date': m.training_date.isoformat() if m.training_date else None
            } for m in models]
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            return []
    
    def predict(self, car_features):
        """Predict car price based on features using the currently loaded model."""
        if not self.model_loaded:
            raise RuntimeError("No model loaded. Cannot make predictions.")
        return self._predict_with_model(car_features)
    
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
            
            # Handle PyTorch vs sklearn models
            if TORCH_AVAILABLE and hasattr(self.model, 'eval'):
                # PyTorch model
                with torch.no_grad():
                    feature_tensor = torch.FloatTensor(feature_vector_scaled)
                    prediction = self.model(feature_tensor)
                    predicted_price_normalized = float(prediction.item() if prediction.dim() == 0 else prediction[0].item())
                    # Denormalize: y = y_normalized * y_std + y_mean
                    predicted_price = predicted_price_normalized * self.y_std + self.y_mean
            else:
                # sklearn model
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
            
            mae = float(self.metadata.get('test_mae', predicted_price * 0.1))
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
            logger.error(f"Model prediction failed: {e}")
            raise RuntimeError(f"Prediction failed: {e}")
    
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
    
    def get_model_info(self):
        """Get information about the currently loaded model."""
        return {
            'version': self.model_version,
            'loaded': self.model_loaded,
            'model_name': self.current_model_name,
            'test_r2': self.metadata.get('test_r2', 'N/A'),
            'test_mae': self.metadata.get('test_mae', 'N/A'),
            'test_rmse': self.metadata.get('test_rmse', 'N/A'),
            'features_count': len(self.feature_names)
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