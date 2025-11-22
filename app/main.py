"""
BPR Backend API - Car Price Prediction Platform
Improved version with comprehensive logging and production-ready configuration
"""

from flask import Flask, jsonify, request, g, url_for, abort
from flask_cors import CORS
from app.models import db, Car, PricePrediction, ScrapingLog, MarketStatistics, PredictionJob
from app.ml.predictor import CarPricePredictor
from app.utils.request_validation import (
    get_pagination_params,
    normalize_string,
    parse_json_body,
    validate_non_negative_number,
    validate_positive_number,
    validate_year,
)
from app.services.prediction_queue import (
    calculate_position,
    decide_dispatch_mode,
    enqueue_job,
    QueueDecision,
    get_job,
)
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
    
    handlers = [
        # Console handler - for Docker logs (always works)
        logging.StreamHandler(sys.stdout)
    ]
    
    # Try to add file handlers if logs directory is writable
    try:
        os.makedirs(log_dir, exist_ok=True)
        handlers.extend([
            logging.FileHandler(os.path.join(log_dir, 'api.log')),
            logging.FileHandler(os.path.join(log_dir, 'errors.log'))
        ])
    except (PermissionError, OSError) as e:
        print(f"Warning: Could not create file handlers: {e}. Logging to stdout only.", file=sys.stderr)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] [%(name)s] [Worker-%(process)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=handlers
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

def parse_allowed_origins():
    """Resolve CORS origins from env var or fall back to sensible defaults."""
    raw = os.getenv('ALLOWED_ORIGINS')
    if raw:
        return [origin.strip() for origin in raw.split(',') if origin.strip()]

    return [
        "https://bpr-g26.netlify.app",
        "https://test.bachelorproject26.site",
        "https://bachelorproject26.site",
        "http://localhost:5173",
        "http://127.0.0.1:5173", 
        # Added explicit scheme for new frontend deployment
        "https://carpredict.netlify.app"
    ]


ALLOWED_ORIGINS = parse_allowed_origins()
logger.info(f"CORS locked to: {ALLOWED_ORIGINS}")

CORS(app,
     resources={r"/*": {"origins": ALLOWED_ORIGINS}},
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

@app.after_request
def add_cors_and_request_id_headers(response):
    """Add CORS headers to every response"""
    origin = request.headers.get('Origin')
    if origin in ALLOWED_ORIGINS:
        response.headers.add('Access-Control-Allow-Origin', origin)
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    if hasattr(g, 'request_id'):
        response.headers['X-Request-ID'] = g.request_id
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
app.config['PREDICTION_QUEUE_MODE'] = os.getenv('PREDICTION_QUEUE_MODE', 'hybrid')
app.config['PREDICTION_QUEUE_THRESHOLD'] = int(os.getenv('PREDICTION_QUEUE_THRESHOLD', '5'))
app.config['PREDICTION_QUEUE_PRIORITY_DEFAULT'] = int(os.getenv('PREDICTION_QUEUE_PRIORITY_DEFAULT', '100'))

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
    incoming_request_id = request.headers.get('X-Request-ID')
    g.request_id = incoming_request_id or f"{int(time.time() * 1000)}"
    
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


@app.teardown_appcontext
def shutdown_session(exception=None):
    """Ensure scoped sessions do not leak between requests."""
    try:
        if exception:
            db.session.rollback()
    finally:
        db.session.remove()

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
    pagination = get_pagination_params(request.args)
    
    # Filters
    filters = {
        'brand': normalize_string(request.args.get('brand')),
        'model': normalize_string(request.args.get('model')),
        'year_min': request.args.get('year_min', type=int),
        'year_max': request.args.get('year_max', type=int),
        'price_min': request.args.get('price_min', type=float),
        'price_max': request.args.get('price_max', type=float),
        'mileage_max': request.args.get('mileage_max', type=int),
        'fuel_type': normalize_string(request.args.get('fuel_type')),
        'transmission': normalize_string(request.args.get('transmission')),
        'body_type': normalize_string(request.args.get('body_type')),
        'location': normalize_string(request.args.get('location'))
    }
    
    # Search query parameter
    search_query = normalize_string(request.args.get('q'))
    
    # Sorting
    sort_by = request.args.get('sort_by', 'listing_date')
    sort_order = request.args.get('sort_order', 'desc')
    
    # Build query
    query = Car.query
    
    # Apply search filter if provided (searches brand, model, and title)
    if search_query:
        search_filter = db.or_(
            Car.brand.ilike(f'%{search_query}%'),
            Car.model.ilike(f'%{search_query}%'),
            Car.title.ilike(f'%{search_query}%')
        )
        query = query.filter(search_filter)
    
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
    logger.debug(
        f"[{g.request_id}] Executing query for page {pagination.page}, "
        f"per_page {pagination.per_page}"
    )
    pagination_result = query.paginate(
        page=pagination.page,
        per_page=pagination.per_page,
        error_out=False
    )
    
    logger.info(
        f"[{g.request_id}] Found {pagination_result.total} cars, "
        f"returning page {pagination.page}/{pagination_result.pages} "
        f"with {len(pagination_result.items)} items"
    )
    
    return jsonify({
        'success': True,
        'cars': [car.to_dict() for car in pagination_result.items],
        'pagination': {
            'total': pagination_result.total,
            'pages': pagination_result.pages,
            'current_page': pagination.page,
            'per_page': pagination.per_page,
            'has_next': pagination_result.has_next,
            'has_prev': pagination_result.has_prev
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
    required_fields = ['brand', 'model', 'year', 'mileage', 'fuel_type', 
                      'transmission', 'body_type', 'price']
    data = parse_json_body(request, required_fields=required_fields)
    logger.info(f"[{g.request_id}] Creating new car: {data.get('brand')} {data.get('model')}")

    # Sanitize numeric fields
    try:
        year = int(data['year'])
    except (TypeError, ValueError):
        raise ValueError('Year must be an integer')
    validate_year(year)

    try:
        mileage = int(data['mileage'])
    except (TypeError, ValueError):
        raise ValueError('Mileage must be an integer')
    validate_non_negative_number('mileage', mileage)

    try:
        price = float(data['price'])
    except (TypeError, ValueError):
        raise ValueError('Price must be a number')
    validate_positive_number('price', price)
    
    # Create new car
    car = Car(
        brand=data['brand'],
        model=data['model'],
        year=year,
        mileage=mileage,
        fuel_type=data['fuel_type'],
        transmission=data['transmission'],
        body_type=data['body_type'],
        engine_size=data.get('engine_size'),
        horsepower=data.get('horsepower'),
        doors=data.get('doors'),
        seats=data.get('seats'),
        color=data.get('color'),
        price=price,
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
    required_fields = ['brand', 'model', 'year', 'mileage', 'fuel_type', 
                      'transmission', 'body_type']
    data = parse_json_body(request, required_fields=required_fields)
    logger.info(
        f"[{g.request_id}] Price prediction requested for: "
        f"{data.get('brand')} {data.get('model')} {data.get('year')}"
    )

    # Validate numeric inputs
    try:
        data['year'] = int(data['year'])
    except (TypeError, ValueError):
        raise ValueError('Year must be an integer')
    validate_year(data['year'])
    
    try:
        data['mileage'] = int(data['mileage'])
    except (TypeError, ValueError):
        raise ValueError('Mileage must be an integer')
    validate_non_negative_number('mileage', data['mileage'])

    for optional_field in ['horsepower', 'doors', 'seats']:
        if optional_field in data and data[optional_field] is not None:
            try:
                data[optional_field] = int(data[optional_field])
            except (TypeError, ValueError):
                raise ValueError(f"{optional_field} must be an integer")
    if data.get('engine_size') is not None:
        try:
            data['engine_size'] = float(data['engine_size'])
        except (TypeError, ValueError):
            raise ValueError('engine_size must be numeric')

    sanitized_payload = dict(data)

    decision = decide_dispatch_mode(
        queue_mode=app.config['PREDICTION_QUEUE_MODE'],
        requested_mode=request.args.get('mode'),
        queue_threshold=app.config['PREDICTION_QUEUE_THRESHOLD']
    )

    if not predictor:
        logger.warning(f"[{g.request_id}] Predictor unavailable, forcing queue")
        decision = QueueDecision(mode='queue', reason='predictor_unavailable')

    if decision.mode == 'queue':
        requested_priority = request.args.get('priority', type=int)
        priority = (
            requested_priority
            if isinstance(requested_priority, int) and requested_priority >= 0
            else app.config['PREDICTION_QUEUE_PRIORITY_DEFAULT']
        )
        job = enqueue_job(sanitized_payload, priority=priority)
        position = calculate_position(job)
        logger.info(
            f"[{g.request_id}] Queued prediction job {job.id} "
            f"(mode={decision.reason}, priority={priority}, position={position})"
        )
        return jsonify({
            'success': True,
            'queued': True,
            'job': job.to_dict(position=position),
            'status_url': url_for('get_prediction_job', job_id=job.id, _external=True),
            'decision': decision.reason
        }), 202
    
    if not predictor:
        raise ValueError("ML predictor not available")
    
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
    pagination_params = get_pagination_params(request.args)
    
    logger.info(f"[{g.request_id}] Fetching predictions page {pagination_params.page}")
    
    pagination = PricePrediction.query.order_by(
        desc(PricePrediction.created_at)
    ).paginate(
        page=pagination_params.page,
        per_page=pagination_params.per_page,
        error_out=False
    )
    
    logger.info(f"[{g.request_id}] Found {pagination.total} predictions")
    
    return jsonify({
        'success': True,
        'predictions': [p.to_dict() for p in pagination.items],
        'pagination': {
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': pagination.page,
            'per_page': pagination.per_page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    }), 200


# ============================================
# PREDICTION JOB QUEUE ENDPOINTS
# ============================================

@app.route('/api/predict/jobs', methods=['GET'])
@handle_errors
def list_prediction_jobs():
    """List queued prediction jobs."""
    pagination_params = get_pagination_params(request.args)
    status_filter = normalize_string(request.args.get('status'))
    include_position = request.args.get('include_position', 'false').lower() == 'true'

    query = PredictionJob.query
    if status_filter:
        query = query.filter(PredictionJob.status == status_filter)

    pagination = query.order_by(desc(PredictionJob.created_at)).paginate(
        page=pagination_params.page,
        per_page=pagination_params.per_page,
        error_out=False
    )

    jobs = []
    for job in pagination.items:
        position = calculate_position(job) if include_position else None
        jobs.append(job.to_dict(position=position))

    return jsonify({
        'success': True,
        'jobs': jobs,
        'pagination': {
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': pagination.page,
            'per_page': pagination.per_page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    }), 200


@app.route('/api/predict/jobs/<job_id>', methods=['GET'])
@handle_errors
def get_prediction_job(job_id):
    """Retrieve the status/result of a single prediction job."""
    job = get_job(job_id)
    if not job:
        abort(404, description='Prediction job not found')

    include_payload = request.args.get('include', '').lower() == 'payload'
    position = calculate_position(job)

    return jsonify({
        'success': True,
        'job': job.to_dict(include_payload=include_payload, position=position)
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
    brand_normalized = normalize_string(brand)
    if not brand_normalized:
        raise ValueError("Brand is required")

    logger.info(f"[{g.request_id}] Fetching models for brand: {brand_normalized}")
    
    models = db.session.query(
        Car.model,
        func.count(Car.id).label('count')
    ).filter(
        Car.brand.ilike(brand_normalized)
    ).group_by(Car.model).order_by(Car.model).all()
    
    logger.info(f"[{g.request_id}] Found {len(models)} models for {brand_normalized}")
    
    return jsonify({
        'success': True,
        'brand': brand_normalized,
        'models': [{'name': model, 'count': count} for model, count in models]
    }), 200

@app.route('/api/model-specs/<brand>/<model>', methods=['GET'])
@handle_errors
def get_model_specs(brand, model):
    """Get specifications for a specific brand-model combination"""
    brand_normalized = normalize_string(brand)
    model_normalized = normalize_string(model)
    
    if not brand_normalized or not model_normalized:
        raise ValueError("Brand and model are required")

    logger.info(f"[{g.request_id}] Fetching specs for {brand_normalized} {model_normalized}")
    
    # Get distinct specifications for this brand-model combination
    specs = db.session.query(
        Car.body_type,
        Car.fuel_type,
        Car.transmission,
        func.count(Car.id).label('count')
    ).filter(
        Car.brand.ilike(brand_normalized),
        Car.model.ilike(model_normalized)
    ).group_by(
        Car.body_type,
        Car.fuel_type,
        Car.transmission
    ).all()
    
    # Organize data
    body_types = {}
    fuel_types = {}
    transmissions = {}
    
    for spec in specs:
        if spec.body_type:
            body_types[spec.body_type] = body_types.get(spec.body_type, 0) + spec.count
        if spec.fuel_type:
            fuel_types[spec.fuel_type] = fuel_types.get(spec.fuel_type, 0) + spec.count
        if spec.transmission:
            transmissions[spec.transmission] = transmissions.get(spec.transmission, 0) + spec.count
    
    # Sort by count (most common first)
    body_types_list = sorted([{'value': k, 'count': v} for k, v in body_types.items()], key=lambda x: x['count'], reverse=True)
    fuel_types_list = sorted([{'value': k, 'count': v} for k, v in fuel_types.items()], key=lambda x: x['count'], reverse=True)
    transmissions_list = sorted([{'value': k, 'count': v} for k, v in transmissions.items()], key=lambda x: x['count'], reverse=True)
    
    logger.info(f"[{g.request_id}] Found {len(body_types_list)} body types, {len(fuel_types_list)} fuel types, {len(transmissions_list)} transmissions")
    
    return jsonify({
        'success': True,
        'brand': brand_normalized,
        'model': model_normalized,
        'body_types': body_types_list,
        'fuel_types': fuel_types_list,
        'transmissions': transmissions_list
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
    brand_normalized = normalize_string(brand)
    if not brand_normalized:
        raise ValueError("Brand is required")

    logger.info(f"[{g.request_id}] Fetching statistics for brand: {brand_normalized}")
    
    brand_cars = Car.query.filter(Car.brand.ilike(brand_normalized))
    total = brand_cars.count()
    
    if total == 0:
        raise ValueError(f"No cars found for brand: {brand}")
    
    price_stats = db.session.query(
        func.avg(Car.price).label('avg_price'),
        func.min(Car.price).label('min_price'),
        func.max(Car.price).label('max_price')
    ).filter(Car.brand.ilike(brand_normalized)).first()
    
    models = db.session.query(
        Car.model,
        func.count(Car.id).label('count'),
        func.avg(Car.price).label('avg_price')
    ).filter(
        Car.brand.ilike(brand_normalized)
    ).group_by(Car.model).order_by(desc('count')).all()
    
    logger.info(f"[{g.request_id}] Brand statistics: {total} cars, {len(models)} models")
    
    return jsonify({
        'success': True,
        'brand': brand_normalized,
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
    pagination_params = get_pagination_params(request.args)
    
    logger.info(f"[{g.request_id}] Fetching scraping logs page {pagination_params.page}")
    
    pagination = ScrapingLog.query.order_by(
        desc(ScrapingLog.created_at)
    ).paginate(
        page=pagination_params.page,
        per_page=pagination_params.per_page,
        error_out=False
    )
    
    return jsonify({
        'success': True,
        'logs': [log.to_dict() for log in pagination.items],
        'pagination': {
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': pagination.page,
            'per_page': pagination.per_page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    }), 200

# ============================================
# SEARCH ENDPOINT
# ============================================

@app.route('/api/search', methods=['GET'])
@handle_errors
def search_cars():
    """Search cars by keyword"""
    query_text = normalize_string(request.args.get('q'))
    pagination_params = get_pagination_params(request.args)
    
    if not query_text:
        raise ValueError("Search query is required")
    
    logger.info(
        f"[{g.request_id}] Searching for: {query_text} "
        f"(page {pagination_params.page})"
    )
    
    # Search in brand, model, and location
    search_filter = db.or_(
        Car.brand.ilike(f'%{query_text}%'),
        Car.model.ilike(f'%{query_text}%'),
        Car.location.ilike(f'%{query_text}%')
    )
    
    pagination = Car.query.filter(search_filter).order_by(
        desc(Car.listing_date)
    ).paginate(
        page=pagination_params.page,
        per_page=pagination_params.per_page,
        error_out=False
    )
    
    logger.info(f"[{g.request_id}] Search found {pagination.total} results")
    
    return jsonify({
        'success': True,
        'query': query_text,
        'cars': [car.to_dict() for car in pagination.items],
        'pagination': {
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': pagination.page,
            'per_page': pagination.per_page,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
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