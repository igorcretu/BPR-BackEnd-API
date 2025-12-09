from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class Car(db.Model):
    __tablename__ = 'cars'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    external_id = db.Column(db.String(50), unique=True, index=True)
    url = db.Column(db.Text)
    brand = db.Column(db.String(100), nullable=False, index=True)
    model = db.Column(db.String(100), nullable=False, index=True)
    variant = db.Column(db.String(200))
    title = db.Column(db.String(300))
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(12, 2), nullable=False, index=True)
    new_price = db.Column(db.Numeric(12, 2))
    model_year = db.Column(db.Integer)
    year = db.Column(db.Integer, index=True)
    first_registration = db.Column(db.String(20))
    production_date = db.Column(db.String(20))
    mileage = db.Column(db.Integer)
    fuel_type = db.Column(db.String(50), index=True)
    transmission = db.Column(db.String(50))
    gear_count = db.Column(db.Integer)
    cylinders = db.Column(db.Integer)
    horsepower = db.Column(db.Integer)
    torque_nm = db.Column(db.Integer)
    acceleration = db.Column(db.Numeric(4, 1))
    top_speed = db.Column(db.Integer)
    range_km = db.Column(db.Integer)
    battery_capacity = db.Column(db.Numeric(5, 1))
    energy_consumption = db.Column(db.Integer)
    home_charging_ac = db.Column(db.String(50))
    fast_charging_dc = db.Column(db.String(50))
    charging_time_dc = db.Column(db.String(50))
    fuel_consumption = db.Column(db.String(50))
    co2_emission = db.Column(db.String(50))
    euro_norm = db.Column(db.String(10))
    tank_capacity = db.Column(db.Integer)
    body_type = db.Column(db.String(50), index=True)
    weight = db.Column(db.Integer)
    width = db.Column(db.Integer)
    length = db.Column(db.Integer)
    height = db.Column(db.Integer)
    trunk_size = db.Column(db.Integer)
    load_capacity = db.Column(db.Integer)
    towing_capacity = db.Column(db.Integer)
    max_towing_weight = db.Column(db.Integer)
    drive_type = db.Column(db.String(50))
    abs_brakes = db.Column(db.Boolean, default=True)
    esp = db.Column(db.Boolean, default=True)
    airbags = db.Column(db.Integer)
    doors = db.Column(db.Integer)
    seats = db.Column(db.Integer)
    color = db.Column(db.String(100))
    category = db.Column(db.String(50))
    equipment = db.Column(db.Text)
    periodic_tax = db.Column(db.String(50))
    engine_size = db.Column(db.Numeric(3, 1))
    source_url = db.Column(db.Text)
    location = db.Column(db.String(200))
    dealer_name = db.Column(db.String(300))
    tax = db.Column(db.Numeric(10, 2))
    image_path = db.Column(db.String(500))
    image_downloaded = db.Column(db.Boolean, default=False)
    listing_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    predictions = db.relationship('PricePrediction', backref='car', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'external_id': self.external_id,
            'url': self.url,
            'brand': self.brand,
            'model': self.model,
            'variant': self.variant,
            'title': self.title,
            'description': self.description,
            'price': float(self.price) if self.price else None,
            'new_price': float(self.new_price) if self.new_price else None,
            'year': self.year or self.model_year,
            'model_year': self.model_year,
            'first_registration': self.first_registration,
            'production_date': self.production_date,
            'mileage': self.mileage,
            'fuel_type': self.fuel_type,
            'transmission': self.transmission,
            'gear_count': self.gear_count,
            'cylinders': self.cylinders,
            'horsepower': self.horsepower,
            'torque_nm': self.torque_nm,
            'acceleration': float(self.acceleration) if self.acceleration else None,
            'top_speed': self.top_speed,
            'range_km': self.range_km,
            'battery_capacity': float(self.battery_capacity) if self.battery_capacity else None,
            'energy_consumption': self.energy_consumption,
            'home_charging_ac': self.home_charging_ac,
            'fast_charging_dc': self.fast_charging_dc,
            'charging_time_dc': self.charging_time_dc,
            'fuel_consumption': self.fuel_consumption,
            'co2_emission': self.co2_emission,
            'euro_norm': self.euro_norm,
            'tank_capacity': self.tank_capacity,
            'body_type': self.body_type,
            'weight': self.weight,
            'width': self.width,
            'length': self.length,
            'height': self.height,
            'trunk_size': self.trunk_size,
            'load_capacity': self.load_capacity,
            'towing_capacity': self.towing_capacity,
            'max_towing_weight': self.max_towing_weight,
            'drive_type': self.drive_type,
            'abs_brakes': self.abs_brakes,
            'esp': self.esp,
            'airbags': self.airbags,
            'doors': self.doors,
            'seats': self.seats,
            'color': self.color,
            'category': self.category,
            'engine_size': float(self.engine_size) if self.engine_size else None,
            'equipment': self.equipment,
            'periodic_tax': self.periodic_tax,
            'tax': float(self.tax) if self.tax else None,
            'image_path': self.image_path,
            'listing_date': self.listing_date.isoformat() if self.listing_date else None,
            'location': self.location,
            'dealer_name': self.dealer_name,
            'source_url': self.source_url or self.url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class PricePrediction(db.Model):
    __tablename__ = 'price_predictions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    car_id = db.Column(db.String(36), db.ForeignKey('cars.id'), index=True)
    model_id = db.Column(db.String(36), db.ForeignKey('ml_models.id'), index=True)
    predicted_price = db.Column(db.Numeric(10, 2), nullable=False)
    actual_price = db.Column(db.Numeric(10, 2))
    prediction_accuracy = db.Column(db.Numeric(5, 2))
    confidence = db.Column(db.Numeric(5, 2))
    price_range_min = db.Column(db.Numeric(12, 2))
    price_range_max = db.Column(db.Numeric(12, 2))
    model_version = db.Column(db.String(50))
    features = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'car_id': self.car_id,
            'model_id': self.model_id,
            'predicted_price': float(self.predicted_price),
            'actual_price': float(self.actual_price) if self.actual_price else None,
            'prediction_accuracy': float(self.prediction_accuracy) if self.prediction_accuracy else None,
            'confidence': float(self.confidence) if self.confidence else None,
            'price_range_min': float(self.price_range_min) if self.price_range_min else None,
            'price_range_max': float(self.price_range_max) if self.price_range_max else None,
            'model_version': self.model_version,
            'created_at': self.created_at.isoformat()
        }

class ScrapingLog(db.Model):
    __tablename__ = 'scraping_logs'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_name = db.Column(db.String(100), nullable=False)
    cars_scraped = db.Column(db.Integer, default=0)
    highest_external_id = db.Column(db.String(50))
    scraping_mode = db.Column(db.String(20))
    cars_new = db.Column(db.Integer, default=0)
    cars_updated = db.Column(db.Integer, default=0)
    images_downloaded = db.Column(db.Integer, default=0)
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)
    started_at = db.Column(db.DateTime, nullable=False)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'source_name': self.source_name,
            'cars_scraped': self.cars_scraped,
            'highest_external_id': self.highest_external_id,
            'scraping_mode': self.scraping_mode,
            'cars_new': self.cars_new,
            'cars_updated': self.cars_updated,
            'images_downloaded': self.images_downloaded,
            'success': self.success,
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat()
        }

class MarketStatistics(db.Model):
    __tablename__ = 'market_statistics'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    brand = db.Column(db.String(100))
    model = db.Column(db.String(100))
    year = db.Column(db.Integer)
    avg_price = db.Column(db.Numeric(10, 2))
    min_price = db.Column(db.Numeric(10, 2))
    max_price = db.Column(db.Numeric(10, 2))
    avg_mileage = db.Column(db.Integer)
    total_listings = db.Column(db.Integer)
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'brand': self.brand,
            'model': self.model,
            'year': self.year,
            'avg_price': float(self.avg_price) if self.avg_price else None,
            'min_price': float(self.min_price) if self.min_price else None,
            'max_price': float(self.max_price) if self.max_price else None,
            'avg_mileage': self.avg_mileage,
            'total_listings': self.total_listings,
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None
        }


class PredictionJob(db.Model):
    __tablename__ = 'prediction_jobs'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)
    priority = db.Column(db.Integer, nullable=False, default=100, index=True)
    payload = db.Column(db.JSON, nullable=False)
    result = db.Column(db.JSON)
    error_message = db.Column(db.Text)
    attempts = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    last_error_at = db.Column(db.DateTime)

    __table_args__ = (
        db.CheckConstraint('priority >= 0', name='prediction_jobs_priority_check'),
    )

    def to_dict(self, *, include_payload: bool = False, position: int | None = None):
        data = {
            'id': self.id,
            'status': self.status,
            'priority': self.priority,
            'attempts': self.attempts,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'last_error_at': self.last_error_at.isoformat() if self.last_error_at else None,
            'result': self.result if self.status == 'completed' else None,
            'error_message': self.error_message if self.status == 'failed' else None,
        }
        if include_payload:
            data['payload'] = self.payload
        if position is not None:
            data['queue_position'] = position
        return data


class MLModel(db.Model):
    __tablename__ = 'ml_models'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    model_type = db.Column(db.String(50), nullable=False)
    algorithm = db.Column(db.String(100), nullable=False)
    version = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True, index=True)
    model_file_path = db.Column(db.String(500))
    mae = db.Column(db.Numeric(12, 2))
    rmse = db.Column(db.Numeric(12, 2))
    r2_score = db.Column(db.Numeric(6, 4))
    mape = db.Column(db.Numeric(6, 4))
    median_ae = db.Column(db.Numeric(12, 2))
    percentile_90_error = db.Column(db.Numeric(12, 2))
    training_time_seconds = db.Column(db.Numeric(10, 2))
    hyperparameters = db.Column(db.JSON)
    feature_importances = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    predictions = db.relationship('PricePrediction', backref='ml_model', lazy=True)
    comparison_metrics = db.relationship('ModelComparisonMetrics', backref='ml_model', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'model_type': self.model_type,
            'algorithm': self.algorithm,
            'version': self.version,
            'is_active': self.is_active,
            'model_file_path': self.model_file_path,
            'mae': float(self.mae) if self.mae else None,
            'rmse': float(self.rmse) if self.rmse else None,
            'r2_score': float(self.r2_score) if self.r2_score else None,
            'mape': float(self.mape) if self.mape else None,
            'median_ae': float(self.median_ae) if self.median_ae else None,
            'percentile_90_error': float(self.percentile_90_error) if self.percentile_90_error else None,
            'training_time_seconds': float(self.training_time_seconds) if self.training_time_seconds else None,
            'hyperparameters': self.hyperparameters,
            'feature_importances': self.feature_importances,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ModelTrainingRun(db.Model):
    __tablename__ = 'model_training_runs'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    dataset_size = db.Column(db.Integer)
    train_size = db.Column(db.Integer)
    test_size = db.Column(db.Integer)
    training_duration_seconds = db.Column(db.Numeric(10, 2))
    status = db.Column(db.String(20), nullable=False, default='pending')
    models_trained = db.Column(db.JSON)
    best_model_id = db.Column(db.String(36), db.ForeignKey('ml_models.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    best_model = db.relationship('MLModel', foreign_keys=[best_model_id], backref='training_runs_as_best')
    
    def to_dict(self):
        return {
            'id': self.id,
            'run_date': self.run_date.isoformat() if self.run_date else None,
            'dataset_size': self.dataset_size,
            'train_size': self.train_size,
            'test_size': self.test_size,
            'training_duration_seconds': float(self.training_duration_seconds) if self.training_duration_seconds else None,
            'status': self.status,
            'models_trained': self.models_trained,
            'best_model_id': self.best_model_id,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ModelComparisonMetrics(db.Model):
    __tablename__ = 'model_comparison_metrics'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_id = db.Column(db.String(36), db.ForeignKey('ml_models.id'), nullable=False, index=True)
    training_run_id = db.Column(db.String(36), db.ForeignKey('model_training_runs.id'), index=True)
    
    # Overall metrics
    overall_mae = db.Column(db.Numeric(12, 2))
    overall_rmse = db.Column(db.Numeric(12, 2))
    overall_r2 = db.Column(db.Numeric(6, 4))
    overall_mape = db.Column(db.Numeric(6, 4))
    
    # Metrics by price range
    mae_under_100k = db.Column(db.Numeric(12, 2))
    mae_100k_300k = db.Column(db.Numeric(12, 2))
    mae_300k_500k = db.Column(db.Numeric(12, 2))
    mae_over_500k = db.Column(db.Numeric(12, 2))
    
    # Metrics by fuel type
    mae_petrol = db.Column(db.Numeric(12, 2))
    mae_diesel = db.Column(db.Numeric(12, 2))
    mae_electric = db.Column(db.Numeric(12, 2))
    mae_hybrid = db.Column(db.Numeric(12, 2))
    
    # Metrics by year range
    mae_pre_2010 = db.Column(db.Numeric(12, 2))
    mae_2010_2015 = db.Column(db.Numeric(12, 2))
    mae_2015_2020 = db.Column(db.Numeric(12, 2))
    mae_post_2020 = db.Column(db.Numeric(12, 2))
    
    # Performance metrics
    avg_inference_time_ms = db.Column(db.Numeric(10, 2))
    confidence_calibration_score = db.Column(db.Numeric(6, 4))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    training_run = db.relationship('ModelTrainingRun', backref='comparison_metrics')
    
    def to_dict(self):
        return {
            'id': self.id,
            'model_id': self.model_id,
            'training_run_id': self.training_run_id,
            'overall_mae': float(self.overall_mae) if self.overall_mae else None,
            'overall_rmse': float(self.overall_rmse) if self.overall_rmse else None,
            'overall_r2': float(self.overall_r2) if self.overall_r2 else None,
            'overall_mape': float(self.overall_mape) if self.overall_mape else None,
            'mae_under_100k': float(self.mae_under_100k) if self.mae_under_100k else None,
            'mae_100k_300k': float(self.mae_100k_300k) if self.mae_100k_300k else None,
            'mae_300k_500k': float(self.mae_300k_500k) if self.mae_300k_500k else None,
            'mae_over_500k': float(self.mae_over_500k) if self.mae_over_500k else None,
            'mae_petrol': float(self.mae_petrol) if self.mae_petrol else None,
            'mae_diesel': float(self.mae_diesel) if self.mae_diesel else None,
            'mae_electric': float(self.mae_electric) if self.mae_electric else None,
            'mae_hybrid': float(self.mae_hybrid) if self.mae_hybrid else None,
            'mae_pre_2010': float(self.mae_pre_2010) if self.mae_pre_2010 else None,
            'mae_2010_2015': float(self.mae_2010_2015) if self.mae_2010_2015 else None,
            'mae_2015_2020': float(self.mae_2015_2020) if self.mae_2015_2020 else None,
            'mae_post_2020': float(self.mae_post_2020) if self.mae_post_2020 else None,
            'avg_inference_time_ms': float(self.avg_inference_time_ms) if self.avg_inference_time_ms else None,
            'confidence_calibration_score': float(self.confidence_calibration_score) if self.confidence_calibration_score else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }