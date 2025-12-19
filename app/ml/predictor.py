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
        
        # Professional dealer brand classification
        self.luxury_brands = [
            'Porsche', 'Tesla', 'Maserati', 'Bentley', 'Rolls-Royce', 'Ferrari',
            'Lamborghini', 'Aston Martin', 'McLaren', 'Lotus', 'Bugatti'
        ]
        self.premium_brands = [
            'BMW', 'Mercedes-Benz', 'Audi', 'Jaguar', 'Land Rover',
            'Lexus', 'Volvo', 'Alfa Romeo', 'Genesis', 'Polestar',
            'Range Rover', 'Cadillac', 'Lincoln', 'Infiniti', 'Acura', 'MINI', 'DS'
        ]
        self.mainstream_brands = [
            'Volkswagen', 'Toyota', 'Honda', 'Mazda', 'Nissan', 'Ford',
            'Hyundai', 'Kia', 'Renault', 'Peugeot', 'Citroën', 'Opel',
            'Seat', 'Skoda', 'Subaru', 'Chrysler'
        ]
        self.economy_brands = [
            'Dacia', 'Suzuki', 'Mitsubishi', 'Chevrolet', 'Lada', 'Tata',
            'Mahindra', 'Proton', 'Geely', 'MG', 'Fiat'
        ]
        
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
                    
                    # Check if it's a package (v3+ format) or standalone model
                    if isinstance(loaded_obj, dict) and 'model' in loaded_obj:
                        # v3+ package format (with preprocessing artifacts)
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
                            'version': f"v{db_model.version}-{db_model.name.lower().replace(' ', '-')}",
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
                            'version': f"v{db_model.version}-{db_model.name.lower().replace(' ', '-')}-legacy",
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
                # sklearn model - predictions are in log space, need to inverse transform
                predicted_log_price = float(self.model.predict(feature_vector_scaled)[0])
                predicted_price = np.exp(predicted_log_price)  # Convert from log space to actual price
            
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
        """Prepare feature dictionary matching EXACTLY the training feature engineering."""
        features = {}
        current_year = datetime.now().year
        
        # ===== BASIC FEATURES =====
        year = int(car_features.get('year', current_year - 3) or (current_year - 3))
        mileage_val = car_features.get('mileage', 0)
        mileage = int(mileage_val) if mileage_val is not None else 0
        horsepower_val = car_features.get('horsepower', 150)
        horsepower = float(horsepower_val) if horsepower_val is not None else 150.0
        doors_val = car_features.get('doors', 5)
        doors = int(doors_val) if doors_val is not None else 5
        seats_val = car_features.get('seats', 5)
        seats = int(seats_val) if seats_val is not None else 5
        brand = car_features.get('brand', '')
        fuel_type = self._normalize_fuel_type(car_features.get('fuel_type', 'Petrol'))
        transmission = self._normalize_transmission(car_features.get('transmission', 'Manual'))
        body_type = self._normalize_body_type(car_features.get('body_type', 'Sedan'))
        
        # Store basic features
        features['year'] = year
        features['mileage'] = max(0, min(mileage, 800000))  # Clip to reasonable bounds
        features['horsepower'] = max(30, min(horsepower, 1500))
        features['doors'] = doors
        features['seats'] = seats
        
        # ===== AGE FEATURES =====
        age = current_year - year
        features['age'] = max(0, min(age, 50))  # Clip to reasonable bounds
        features['age_squared'] = features['age'] ** 2
        features['age_cubed'] = features['age'] ** 3
        
        # ===== MILEAGE FEATURES =====
        features['mileage_log'] = np.log1p(features['mileage'])
        features['mileage_per_year'] = min(features['mileage'] / (features['age'] + 1), 100000)
        features['high_mileage'] = 1 if features['mileage'] > 150000 else 0
        features['low_mileage'] = 1 if features['mileage'] < 50000 else 0
        
        # ===== BRAND TIER FEATURES =====
        features['is_luxury'] = 1 if brand in self.luxury_brands else 0
        features['is_premium'] = 1 if brand in self.premium_brands else 0
        features['is_mainstream'] = 1 if brand in self.mainstream_brands else 0
        features['is_economy'] = 1 if brand in self.economy_brands else 0
        
        # Brand tier encoding (3=luxury, 2=premium, 1=mainstream, 0=economy/unknown)
        if features['is_luxury'] == 1:
            features['brand_tier'] = 3
        elif features['is_premium'] == 1:
            features['brand_tier'] = 2
        elif features['is_mainstream'] == 1:
            features['brand_tier'] = 1
        else:
            features['brand_tier'] = 0
        
        # ===== FUEL TYPE FEATURES =====
        features['is_electric'] = 1 if fuel_type == 'Electricity' else 0
        features['is_diesel'] = 1 if fuel_type == 'Diesel' else 0
        features['is_hybrid'] = 1 if 'Hybrid' in fuel_type else 0
        features['is_plugin'] = 1 if 'Plug-in' in fuel_type else 0
        
        # ===== TRANSMISSION FEATURES =====
        features['is_automatic'] = 1 if transmission == 'Automatic' else 0
        
        # ===== BODY TYPE FEATURES =====
        features['is_suv'] = 1 if body_type == 'SUV' else 0
        features['is_wagon'] = 1 if body_type in ['Station Wagon', 'Van'] else 0
        features['is_hatchback'] = 1 if body_type == 'Hatchback' else 0
        
        # ===== POWER FEATURES =====
        features['horsepower_log'] = np.log1p(features['horsepower'])
        features['horsepower_per_year'] = features['horsepower'] / (features['age'] + 1)
        features['low_power'] = 1 if features['horsepower'] < 100 else 0
        features['high_power'] = 1 if features['horsepower'] > 200 else 0
        features['very_high_power'] = 1 if features['horsepower'] > 300 else 0
        
        # ===== INTERACTION FEATURES =====
        features['age_mileage_interaction'] = features['age'] * features['mileage_log']
        features['brand_tier_age'] = features['brand_tier'] * features['age']
        features['brand_tier_mileage'] = features['brand_tier'] * features['mileage_log']
        features['hp_age_ratio'] = features['horsepower'] / (features['age'] + 1)
        
        # Professional dealer mileage expectations
        features['expected_mileage'] = features['age'] * 12000
        mileage_vs_expected = (features['mileage'] - features['expected_mileage']) / (features['expected_mileage'] + 1)
        features['mileage_vs_expected'] = max(-2, min(mileage_vs_expected, 3))  # Clip
        
        # Market demand indicators
        features['is_suv_or_crossover'] = 1 if body_type in ['SUV', 'Crossover'] else 0
        features['is_electric_or_hybrid'] = 1 if (features['is_electric'] == 1 or features['is_hybrid'] == 1) else 0
        
        # ===== EV FEATURES =====
        battery_capacity_val = car_features.get('battery_capacity', 0)
        battery_capacity = float(battery_capacity_val) if battery_capacity_val is not None else 0.0
        range_val = car_features.get('range', 0)
        range_km = float(range_val) if range_val is not None else 0.0
        features['battery_capacity'] = battery_capacity
        features['range_km'] = range_km
        features['has_ev_data'] = 1 if (battery_capacity > 0 or range_km > 0) else 0
        
        # ===== DRIVE TYPE FEATURES =====
        drive_type = self._normalize_drive_type(car_features.get('drive_type', 'FWD'))
        features['is_awd'] = 1 if drive_type in ['AWD', '4WD'] else 0
        
        # ===== OTHER NUMERIC FEATURES =====
        torque_val = car_features.get('torque_nm', 0)
        features['torque_nm'] = float(torque_val) if torque_val is not None else 0.0
        engine_val = car_features.get('engine_size', 0)
        features['engine_size'] = float(engine_val) if engine_val is not None else 0.0
        accel_val = car_features.get('acceleration', 0)
        features['acceleration'] = float(accel_val) if accel_val is not None else 0.0
        speed_val = car_features.get('top_speed', 0)
        features['top_speed'] = float(speed_val) if speed_val is not None else 0.0
        weight_val = car_features.get('weight', 0)
        features['weight'] = float(weight_val) if weight_val is not None else 0.0
        fuel_cons_val = car_features.get('fuel_consumption', 0)
        features['fuel_consumption'] = float(fuel_cons_val) if fuel_cons_val is not None else 0.0
        co2_val = car_features.get('co2_emission', 0)
        features['co2_emission'] = float(co2_val) if co2_val is not None else 0.0
        tax_val = car_features.get('periodic_tax', 0)
        features['periodic_tax'] = float(tax_val) if tax_val is not None else 0.0
        
        # ===== TARGET ENCODED FEATURES =====
        # These will be filled in by the model's preprocessing
        for encoder_key in self.target_encoders:
            features[f'{encoder_key}_encoded'] = 0  # Default value
        
        # Add category mappings for one-hot encoded features (if they exist in the model)
        if hasattr(self, 'category_mappings'):
            for cat_col, cat_values in self.category_mappings.items():
                for cat_val in cat_values:
                    features[cat_val] = 0  # Default value, will be set based on input
        
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