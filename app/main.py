"""
BPR Backend API - Car Price Prediction Platform
Improved version with comprehensive logging and production-ready configuration
"""

from flask import Flask, jsonify, request, g
from flask_cors import CORS
from app.models import db, Car, PricePrediction, ScrapingLog, MarketStatistics
from app.ml.predictor import CarPricePredictor
from sqlalchemy import func, desc
from sqlalchemy.exc import SQLAlchemyError
import os
import logging
import sys
from datetime import datetime
import time
import traceback
from functools import wraps

# ============================================
# LOGGING CONFIGURATION
# ============================================

def setup_logging():
    """Configure comprehensive logging for the application"""
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), '../logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] [%(name)s] [Worker-%(process)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            # Console handler - for Docker logs
            logging.StreamHandler(sys.stdout),
            # File handler - for persistent logs
            logging.FileHandler(os.path.join(log_dir, 'api.log')),
            # Error file handler - separate file for errors
            logging.FileHandler(os.path.join(log_dir, 'errors.log'))
        ]
    )
    
    # Set specific log levels for different modules
    logging.getLogger('werkzeug').setLevel(logging.WARNING)  # Reduce Flask request logs
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)  # Reduce SQL logs
    
    return logging.getLogger(__name__)

logger = setup_logging()

# ============================================
# FLASK APP INITIALIZATION
# ============================================

app = Flask(__name__)
logger.info("=" * 80)
logger.info("INITIALIZING BPR BACKEND API")
logger.info("=" * 80)

# ============================================
# CORS CONFIGURATION
# ============================================

allowed_origins = os.getenv('ALLOWED_ORIGINS', '*')
if allowed_origins != '*':
    allowed_origins = [origin.strip() for origin in allowed_origins.split(',')]
    logger.info(f"CORS configured for specific origins: {allowed_origins}")
else:
    logger.warning("CORS configured to allow all origins (*)")

CORS(app, 
     resources={r"/*": {"origins": allowed_origins}},
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

@app.after_request
def after_request(response):
    """Add CORS headers to every response"""
    origin = request.headers.get('Origin')
    if allowed_origins == '*':
        response.headers.add('Access-Control-Allow-Origin', '*')
    elif origin in allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', origin)
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# ============================================
# DATABASE CONFIGURATION
# ============================================

database_url = os.getenv('DATABASE_URL', 'postgresql://bpr_user:bpr_password@db:5432/car_prediction')
logger.info(f"Database URL configured: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,  # Test connections before using them
    'max_overflow': 20
}
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['JSON_SORT_KEYS'] = False

# Initialize database
db.init_app(app)
logger.info("Database initialized with connection pooling")

# ============================================
# ML PREDICTOR INITIALIZATION
# ============================================

logger.info("Initializing ML predictor...")
try:
    predictor = CarPricePredictor()
    logger.info(f"ML Predictor initialized: {predictor.get_model_info()}")
except Exception as e:
    logger.error(f"Failed to initialize ML predictor: {str(e)}")
    logger.error(traceback.format_exc())
    predictor = None

# ============================================
# REQUEST LOGGING MIDDLEWARE
# ============================================

@app.before_request
def before_request():
    """Log request details and start timing"""
    g.start_time = time.time()
    g.request_id = f"{int(time.time() * 1000)}"
    
    logger.info(
        f"[{g.request_id}] "
        f"{request.method} {request.path} "
        f"from {request.remote_addr} "
        f"User-Agent: {request.headers.get('User-Agent', 'Unknown')[:50]}"
    )
    
    if request.method in ['POST', 'PUT', 'PATCH']:
        try:
            data = request.get_json(silent=True)
            if data:
                # Log request body but sanitize sensitive fields
                safe_data = {k: ('***' if 'password' in k.lower() else v) 
                           for k, v in data.items()}
                logger.info(f"[{g.request_id}] Request body: {safe_data}")
        except Exception:
            pass

@app.after_request
def after_request_logging(response):
    """Log response details and timing"""
    if hasattr(g, 'start_time'):
        duration = time.time() - g.start_time
        logger.info(
            f"[{g.request_id}] "
            f"Response: {response.status_code} "
            f"Duration: {duration:.3f}s "
            f"Size: {response.content_length or 0} bytes"
        )
    return response

# ============================================
# ERROR HANDLING DECORATOR
# ============================================

def handle_errors(f):
    """Decorator to handle errors consistently across endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except SQLAlchemyError as e:
            logger.error(f"[{g.request_id}] Database error in {f.__name__}: {str(e)}")
            logger.error(traceback.format_exc())
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': 'Database error occurred',
                'detail': str(e) if app.debug else None
            }), 500
        except ValueError as e:
            logger.warning(f"[{g.request_id}] Validation error in {f.__name__}: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
        except Exception as e:
            logger.error(f"[{g.request_id}] Unexpected error in {f.__name__}: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({
                'success': False,
                'error': 'Internal server error',
                'detail': str(e) if app.debug else None
            }), 500
    return decorated_function

# ============================================
# HEALTH CHECK
# ============================================

@app.route('/health', methods=['GET'])
@handle_errors
def health_check():
    """Health check endpoint with detailed status"""
    logger.debug(f"[{g.request_id}] Health check requested")
    
    # Check database connection
    db_status = 'disconnected'
    try:
        db.session.execute(db.text('SELECT 1'))
        db_status = 'connected'
        logger.debug(f"[{g.request_id}] Database connection: OK")
    except Exception as e:
        db_status = f'error: {str(e)}'
        logger.error(f"[{g.request_id}] Database connection: FAILED - {str(e)}")
    
    # Get ML model info
    ml_info = predictor.get_model_info() if predictor else {'error': 'Predictor not initialized'}
    
    response = {
        'status': 'healthy' if db_status == 'connected' else 'degraded',
        'service': 'BPR Backend API',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'database': db_status,
        'ml_model': ml_info
    }
    
    status_code = 200 if db_status == 'connected' else 503
    return jsonify(response), status_code

# ============================================
# CAR ENDPOINTS
# ============================================

@app.route('/api/cars', methods=['GET'])
@handle_errors
def get_cars():
    """Get all cars with filtering and pagination"""
    logger.info(f"[{g.request_id}] Fetching cars with filters: {request.args}")
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    # Filters
    filters = {
        'brand': request.args.get('brand'),
        'model': request.args.get('model'),
        'year_min': request.args.get('year_min', type=int),
        'year_max': request.args.get('year_max', type=int),
        'price_min': request.args.get('price_min', type=float),
        'price_max': request.args.get('price_max', type=float),
        'mileage_max': request.args.get('mileage_max', type=int),
        'fuel_type': request.args.get('fuel_type'),
        'transmission': request.args.get('transmission'),
        'body_type': request.args.get('body_type'),
        'location': request.args.get('location')
    }
    
    # Sorting
    sort_by = request.args.get('sort_by', 'listing_date')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Build query
    query = Car.query
    
    # Apply filters
    if filters['brand']:
        query = query.filter(Car.brand.ilike(f"%{filters['brand']}%"))
    if filters['model']:
        query = query.filter(Car.model.ilike(f"%{filters['model']}%"))
    if filters['year_min']:
        query = query.filter(Car.year >= filters['year_min'])
    if filters['year_max']:
        query = query.filter(Car.year <= filters['year_max'])
    if filters['price_min']:
        query = query.filter(Car.price >= filters['price_min'])
    if filters['price_max']:
        query = query.filter(Car.price <= filters['price_max'])
    if filters['mileage_max']:
        query = query.filter(Car.mileage <= filters['mileage_max'])
    if filters['fuel_type']:
        query = query.filter(Car.fuel_type.ilike(filters['fuel_type']))
    if filters['transmission']:
        query = query.filter(Car.transmission.ilike(filters['transmission']))
    if filters['body_type']:
        query = query.filter(Car.body_type.ilike(filters['body_type']))
    if filters['location']:
        query = query.filter(Car.location.ilike(f"%{filters['location']}%"))
    
    # Apply sorting
    if hasattr(Car, sort_by):
        sort_column = getattr(Car, sort_by)
        if sort_order == 'desc':
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
    
    # Execute query with pagination
    logger.debug(f"[{g.request_id}] Executing query for page {page}, per_page {per_page}")
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    logger.info(
        f"[{g.request_id}] Found {pagination.total} cars, "
        f"returning page {page}/{pagination.pages} with {len(pagination.items)} items"
    )
    
    return jsonify({
        'success': True,
        'cars': [car.to_dict() for car in pagination.items],
        'pagination': {
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page,
            'per_page': per_page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    }), 200

@app.route('/api/cars/<car_id>', methods=['GET'])
@handle_errors
def get_car(car_id):
    """Get specific car by ID"""
    logger.info(f"[{g.request_id}] Fetching car with ID: {car_id}")
    
    car = Car.query.get_or_404(car_id)
    car_data = car.to_dict()
    
    # Include latest prediction if available
    latest_prediction = PricePrediction.query.filter_by(
        car_id=car_id
    ).order_by(desc(PricePrediction.created_at)).first()
    
    if latest_prediction:
        car_data['prediction'] = latest_prediction.to_dict()
        logger.debug(f"[{g.request_id}] Included prediction for car {car_id}")
    
    logger.info(f"[{g.request_id}] Successfully retrieved car {car_id}")
    return jsonify({
        'success': True,
        'car': car_data
    }), 200

@app.route('/api/cars', methods=['POST'])
@handle_errors
def create_car():
    """Create a new car listing"""
    data = request.get_json()
    logger.info(f"[{g.request_id}] Creating new car: {data.get('brand')} {data.get('model')}")
    
    # Validate required fields
    required_fields = ['brand', 'model', 'year', 'mileage', 'fuel_type', 
                      'transmission', 'body_type', 'price']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
    
    # Create new car
    car = Car(
        brand=data['brand'],
        model=data['model'],
        year=data['year'],
        mileage=data['mileage'],
        fuel_type=data['fuel_type'],
        transmission=data['transmission'],
        body_type=data['body_type'],
        engine_size=data.get('engine_size'),
        horsepower=data.get('horsepower'),
        doors=data.get('doors'),
        seats=data.get('seats'),
        color=data.get('color'),
        price=data['price'],
        source_url=data.get('source_url'),
        location=data.get('location'),
        dealer_name=data.get('dealer_name')
    )
    
    db.session.add(car)
    db.session.commit()
    
    logger.info(f"[{g.request_id}] Successfully created car with ID: {car.id}")
    
    return jsonify({
        'success': True,
        'message': 'Car created successfully',
        'car': car.to_dict()
    }), 201

# ============================================
# PREDICTION ENDPOINTS
# ============================================

@app.route('/api/predict', methods=['POST'])
@handle_errors
def predict_price():
    """Predict car price based on features"""
    data = request.get_json()
    logger.info(
        f"[{g.request_id}] Price prediction requested for: "
        f"{data.get('brand')} {data.get('model')} {data.get('year')}"
    )
    
    if not predictor:
        raise ValueError("ML predictor not available")
    
    # Validate required fields
    required_fields = ['brand', 'model', 'year', 'mileage', 'fuel_type', 
                      'transmission', 'body_type']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
    
    # Validate year
    current_year = datetime.now().year
    if data['year'] < 1900 or data['year'] > current_year + 1:
        raise ValueError(f"Year must be between 1900 and {current_year + 1}")
    
    # Validate mileage
    if data['mileage'] < 0:
        raise ValueError("Mileage cannot be negative")
    
    # Get prediction
    logger.debug(f"[{g.request_id}] Running ML prediction...")
    start_time = time.time()
    prediction_result = predictor.predict(data)
    prediction_time = time.time() - start_time
    
    logger.info(
        f"[{g.request_id}] Prediction completed in {prediction_time:.3f}s: "
        f"{prediction_result['predicted_price']} DKK "
        f"(confidence: {prediction_result['confidence']}%)"
    )
    
    return jsonify({
        'success': True,
        'predicted_price': prediction_result['predicted_price'],
        'currency': 'DKK',
        'confidence': prediction_result['confidence'],
        'price_range': prediction_result['price_range'],
        'model_version': prediction_result['model_version'],
        'similar_cars_count': prediction_result['similar_cars_count'],
        'input_features': data
    }), 200

@app.route('/api/predictions', methods=['GET'])
@handle_errors
def get_predictions():
    """Get prediction history"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    logger.info(f"[{g.request_id}] Fetching predictions page {page}")
    
    pagination = PricePrediction.query.order_by(
        desc(PricePrediction.created_at)
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    logger.info(f"[{g.request_id}] Found {pagination.total} predictions")
    
    return jsonify({
        'success': True,
        'predictions': [p.to_dict() for p in pagination.items],
        'pagination': {
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        }
    }), 200

# ============================================
# FILTER OPTIONS ENDPOINTS
# ============================================

@app.route('/api/brands', methods=['GET'])
@handle_errors
def get_brands():
    """Get all available car brands"""
    logger.info(f"[{g.request_id}] Fetching brands")
    
    brands = db.session.query(
        Car.brand,
        func.count(Car.id).label('count')
    ).group_by(Car.brand).order_by(Car.brand).all()
    
    logger.info(f"[{g.request_id}] Found {len(brands)} brands")
    
    return jsonify({
        'success': True,
        'brands': [{'name': brand, 'count': count} for brand, count in brands]
    }), 200

@app.route('/api/models/<brand>', methods=['GET'])
@handle_errors
def get_models(brand):
    """Get all models for a specific brand"""
    logger.info(f"[{g.request_id}] Fetching models for brand: {brand}")
    
    models = db.session.query(
        Car.model,
        func.count(Car.id).label('count')
    ).filter(
        Car.brand.ilike(brand)
    ).group_by(Car.model).order_by(Car.model).all()
    
    logger.info(f"[{g.request_id}] Found {len(models)} models for {brand}")
    
    return jsonify({
        'success': True,
        'brand': brand,
        'models': [{'name': model, 'count': count} for model, count in models]
    }), 200

@app.route('/api/filters', methods=['GET'])
@handle_errors
def get_filter_options():
    """Get all available filter options"""
    logger.info(f"[{g.request_id}] Fetching filter options")
    
    # Get unique values for each filter
    fuel_types = db.session.query(Car.fuel_type, func.count(Car.id)).group_by(Car.fuel_type).all()
    transmissions = db.session.query(Car.transmission, func.count(Car.id)).group_by(Car.transmission).all()
    body_types = db.session.query(Car.body_type, func.count(Car.id)).group_by(Car.body_type).all()
    locations = db.session.query(Car.location, func.count(Car.id)).group_by(Car.location).all()
    
    # Get ranges
    year_stats = db.session.query(
        func.min(Car.year).label('min_year'),
        func.max(Car.year).label('max_year')
    ).first()
    
    price_stats = db.session.query(
        func.min(Car.price).label('min_price'),
        func.max(Car.price).label('max_price')
    ).first()
    
    mileage_stats = db.session.query(
        func.min(Car.mileage).label('min_mileage'),
        func.max(Car.mileage).label('max_mileage')
    ).first()
    
    logger.info(f"[{g.request_id}] Retrieved all filter options successfully")
    
    return jsonify({
        'success': True,
        'filters': {
            'fuel_types': [{'value': ft, 'count': count} for ft, count in fuel_types if ft],
            'transmissions': [{'value': t, 'count': count} for t, count in transmissions if t],
            'body_types': [{'value': bt, 'count': count} for bt, count in body_types if bt],
            'locations': [{'value': loc, 'count': count} for loc, count in locations if loc],
            'year_range': {
                'min': year_stats.min_year if year_stats else None,
                'max': year_stats.max_year if year_stats else None
            },
            'price_range': {
                'min': float(price_stats.min_price) if price_stats and price_stats.min_price else None,
                'max': float(price_stats.max_price) if price_stats and price_stats.max_price else None
            },
            'mileage_range': {
                'min': mileage_stats.min_mileage if mileage_stats else None,
                'max': mileage_stats.max_mileage if mileage_stats else None
            }
        }
    }), 200

# ============================================
# STATISTICS ENDPOINTS
# ============================================

@app.route('/api/stats', methods=['GET'])
@handle_errors
def get_statistics():
    """Get overall market statistics"""
    logger.info(f"[{g.request_id}] Fetching market statistics")
    
    total_cars = Car.query.count()
    
    price_stats = db.session.query(
        func.avg(Car.price).label('avg_price'),
        func.min(Car.price).label('min_price'),
        func.max(Car.price).label('max_price')
    ).first()
    
    top_brands = db.session.query(
        Car.brand,
        func.count(Car.id).label('count')
    ).group_by(Car.brand).order_by(desc('count')).limit(10).all()
    
    fuel_distribution = db.session.query(
        Car.fuel_type,
        func.count(Car.id).label('count')
    ).group_by(Car.fuel_type).all()
    
    logger.info(f"[{g.request_id}] Statistics: {total_cars} total cars")
    
    return jsonify({
        'success': True,
        'statistics': {
            'total_listings': total_cars,
            'average_price': float(price_stats.avg_price) if price_stats.avg_price else 0,
            'min_price': float(price_stats.min_price) if price_stats.min_price else 0,
            'max_price': float(price_stats.max_price) if price_stats.max_price else 0,
            'top_brands': [{'brand': brand, 'count': count} for brand, count in top_brands],
            'fuel_distribution': [{'fuel_type': ft, 'count': count} for ft, count in fuel_distribution]
        }
    }), 200

@app.route('/api/stats/brand/<brand>', methods=['GET'])
@handle_errors
def get_brand_statistics(brand):
    """Get statistics for a specific brand"""
    logger.info(f"[{g.request_id}] Fetching statistics for brand: {brand}")
    
    brand_cars = Car.query.filter(Car.brand.ilike(brand))
    total = brand_cars.count()
    
    if total == 0:
        raise ValueError(f"No cars found for brand: {brand}")
    
    price_stats = db.session.query(
        func.avg(Car.price).label('avg_price'),
        func.min(Car.price).label('min_price'),
        func.max(Car.price).label('max_price')
    ).filter(Car.brand.ilike(brand)).first()
    
    models = db.session.query(
        Car.model,
        func.count(Car.id).label('count'),
        func.avg(Car.price).label('avg_price')
    ).filter(
        Car.brand.ilike(brand)
    ).group_by(Car.model).order_by(desc('count')).all()
    
    logger.info(f"[{g.request_id}] Brand statistics: {total} cars, {len(models)} models")
    
    return jsonify({
        'success': True,
        'brand': brand,
        'statistics': {
            'total_listings': total,
            'average_price': float(price_stats.avg_price) if price_stats.avg_price else 0,
            'min_price': float(price_stats.min_price) if price_stats.min_price else 0,
            'max_price': float(price_stats.max_price) if price_stats.max_price else 0,
            'models': [
                {
                    'model': model,
                    'count': count,
                    'average_price': float(avg_price) if avg_price else 0
                }
                for model, count, avg_price in models
            ]
        }
    }), 200

# ============================================
# SCRAPING LOGS ENDPOINTS
# ============================================

@app.route('/api/scraping/logs', methods=['GET'])
@handle_errors
def get_scraping_logs():
    """Get scraping execution logs"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    logger.info(f"[{g.request_id}] Fetching scraping logs page {page}")
    
    pagination = ScrapingLog.query.order_by(
        desc(ScrapingLog.created_at)
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'success': True,
        'logs': [log.to_dict() for log in pagination.items],
        'pagination': {
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        }
    }), 200

# ============================================
# SEARCH ENDPOINT
# ============================================

@app.route('/api/search', methods=['GET'])
@handle_errors
def search_cars():
    """Search cars by keyword"""
    query_text = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    if not query_text:
        raise ValueError("Search query is required")
    
    logger.info(f"[{g.request_id}] Searching for: {query_text}")
    
    # Search in brand, model, and location
    search_filter = db.or_(
        Car.brand.ilike(f'%{query_text}%'),
        Car.model.ilike(f'%{query_text}%'),
        Car.location.ilike(f'%{query_text}%')
    )
    
    pagination = Car.query.filter(search_filter).order_by(
        desc(Car.listing_date)
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    logger.info(f"[{g.request_id}] Search found {pagination.total} results")
    
    return jsonify({
        'success': True,
        'query': query_text,
        'cars': [car.to_dict() for car in pagination.items],
        'pagination': {
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        }
    }), 200

# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(error):
    logger.warning(f"[{g.request_id}] 404 error: {request.path}")
    return jsonify({
        'success': False,
        'error': 'Resource not found',
        'path': request.path
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"[{g.request_id}] 500 error: {str(error)}")
    logger.error(traceback.format_exc())
    db.session.rollback()
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

@app.errorhandler(Exception)
def handle_exception(error):
    logger.error(f"[{g.request_id}] Unhandled exception: {str(error)}")
    logger.error(traceback.format_exc())
    db.session.rollback()
    return jsonify({
        'success': False,
        'error': 'An unexpected error occurred',
        'detail': str(error) if app.debug else None
    }), 500

# ============================================
# APPLICATION STARTUP
# ============================================

if __name__ == '__main__':
    logger.info("Starting Flask development server...")
    logger.warning("WARNING: Do not use Flask dev server in production!")
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=os.getenv('FLASK_ENV') == 'development'
    )
else:
    logger.info("Application loaded by WSGI server")
    logger.info(f"Configuration: {app.config['SQLALCHEMY_ENGINE_OPTIONS']}")