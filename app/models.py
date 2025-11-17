from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class Car(db.Model):
    __tablename__ = 'cars'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    brand = db.Column(db.String(100), nullable=False, index=True)
    model = db.Column(db.String(100), nullable=False, index=True)
    year = db.Column(db.Integer, nullable=False, index=True)
    mileage = db.Column(db.Integer, nullable=False)
    fuel_type = db.Column(db.String(20), nullable=False, index=True)
    transmission = db.Column(db.String(20), nullable=False)
    body_type = db.Column(db.String(20), nullable=False)
    engine_size = db.Column(db.Numeric(3, 1))
    horsepower = db.Column(db.Integer)
    doors = db.Column(db.Integer)
    seats = db.Column(db.Integer)
    color = db.Column(db.String(50))
    price = db.Column(db.Numeric(10, 2), nullable=False, index=True)
    listing_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    source_url = db.Column(db.Text)
    location = db.Column(db.String(100))
    dealer_name = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    predictions = db.relationship('PricePrediction', backref='car', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'brand': self.brand,
            'model': self.model,
            'year': self.year,
            'mileage': self.mileage,
            'fuel_type': self.fuel_type,
            'transmission': self.transmission,
            'body_type': self.body_type,
            'engine_size': float(self.engine_size) if self.engine_size else None,
            'horsepower': self.horsepower,
            'doors': self.doors,
            'seats': self.seats,
            'color': self.color,
            'price': float(self.price),
            'listing_date': self.listing_date.isoformat() if self.listing_date else None,
            'location': self.location,
            'dealer_name': self.dealer_name,
            'source_url': self.source_url
        }

class PricePrediction(db.Model):
    __tablename__ = 'price_predictions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    car_id = db.Column(db.String(36), db.ForeignKey('cars.id'), index=True)
    predicted_price = db.Column(db.Numeric(10, 2), nullable=False)
    actual_price = db.Column(db.Numeric(10, 2))
    prediction_accuracy = db.Column(db.Numeric(5, 2))
    model_version = db.Column(db.String(50))
    features = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'car_id': self.car_id,
            'predicted_price': float(self.predicted_price),
            'actual_price': float(self.actual_price) if self.actual_price else None,
            'prediction_accuracy': float(self.prediction_accuracy) if self.prediction_accuracy else None,
            'model_version': self.model_version,
            'created_at': self.created_at.isoformat()
        }

class ScrapingLog(db.Model):
    __tablename__ = 'scraping_logs'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_name = db.Column(db.String(100), nullable=False)
    cars_scraped = db.Column(db.Integer, default=0)
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
