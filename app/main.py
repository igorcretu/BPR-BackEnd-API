"""
BPR Backend API - Car Price Prediction Platform
Improved version with comprehensive logging and production-ready configuration
"""

from flask import Flask, jsonify, request, g, url_for, abort
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
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
from sqlalchemy import func, desc, case
from sqlalchemy.exc import SQLAlchemyError
import os
import logging
import sys
import subprocess
import threading
import json
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

# Only set pooling options for PostgreSQL, not SQLite
if not database_url.startswith('sqlite'):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,  # Test connections before using them
        'max_overflow': 20
    }
else:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}
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
        except HTTPException:
            # Re-raise HTTP exceptions (404, 405, etc.) to be handled by Flask's error handlers
            raise
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
    from app.models import MLModel, ScrapingLog, ModelTrainingRun
    
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
    
    # Get ML model info from predictor
    ml_info = predictor.get_model_info() if predictor else {'error': 'Predictor not initialized'}
    
    # Get all registered ML models status
    ml_models_status = []
    try:
        all_models = MLModel.query.order_by(desc(MLModel.r2_score)).all()
        for model in all_models:
            ml_models_status.append({
                'id': model.id,
                'name': model.name,
                'algorithm': model.algorithm,
                'is_active': model.is_active,
                'r2_score': float(model.r2_score) if model.r2_score else None,
                'mae': float(model.mae) if model.mae else None,
                'version': model.version,
                'created_at': model.created_at.isoformat() if model.created_at else None
            })
    except Exception as e:
        logger.error(f"[{g.request_id}] Failed to fetch ML models: {str(e)}")
        ml_models_status = {'error': str(e)}
    
    # Get latest scraping status
    scraping_status = None
    try:
        latest_scrape = ScrapingLog.query.order_by(desc(ScrapingLog.created_at)).first()
        if latest_scrape:
            scraping_status = {
                'last_run': latest_scrape.started_at.isoformat() if latest_scrape.started_at else None,
                'completed_at': latest_scrape.completed_at.isoformat() if latest_scrape.completed_at else None,
                'success': latest_scrape.success,
                'cars_scraped': latest_scrape.cars_scraped,
                'cars_new': latest_scrape.cars_new,
                'cars_updated': latest_scrape.cars_updated,
                'images_downloaded': latest_scrape.images_downloaded,
                'error_message': latest_scrape.error_message,
                'source': latest_scrape.source_name
            }
    except Exception as e:
        logger.error(f"[{g.request_id}] Failed to fetch scraping status: {str(e)}")
        scraping_status = {'error': str(e)}
    
    # Get latest training status
    training_status = None
    try:
        latest_training = ModelTrainingRun.query.order_by(desc(ModelTrainingRun.run_date)).first()
        if latest_training:
            training_status = {
                'last_run': latest_training.run_date.isoformat() if latest_training.run_date else None,
                'status': latest_training.status,
                'dataset_size': latest_training.dataset_size,
                'train_size': latest_training.train_size,
                'test_size': latest_training.test_size,
                'duration_seconds': float(latest_training.training_duration_seconds) if latest_training.training_duration_seconds else None,
                'models_trained': latest_training.models_trained,
                'best_model_id': latest_training.best_model_id
            }
    except Exception as e:
        logger.error(f"[{g.request_id}] Failed to fetch training status: {str(e)}")
        training_status = {'error': str(e)}
    
    # Check if scraper is currently running (new incremental scraper or legacy ones)
    scraper_process = None
    try:
        # Try pgrep first (Linux/Unix) - check multiple patterns
        try:
            # Check for any scraper process (prioritize new incremental scraper)
            patterns_to_check = ['bilbasen_incremental', 'auto_scraper', 'bilbasen_scraper']
            all_pids = []
            
            for pattern in patterns_to_check:
                result = subprocess.run(
                    ['pgrep', '-f', pattern],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    pids = result.stdout.strip().split('\n')
                    all_pids.extend([int(p) for p in pids if p])
            
            if all_pids:
                scraper_process = {
                    'running': True,
                    'process_count': len(all_pids),
                    'pids': all_pids
                }
            else:
                scraper_process = {'running': False}
        except (FileNotFoundError, OSError, PermissionError):
            # Fallback to psutil (cross-platform)
            try:
                import psutil
                running_pids = []
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        if 'bilbasen_incremental' in cmdline or 'bilbasen_scraper' in cmdline or 'auto_scraper' in cmdline:
                            running_pids.append(proc.info['pid'])
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                if running_pids:
                    scraper_process = {
                        'running': True,
                        'process_count': len(running_pids),
                        'pids': running_pids
                    }
                else:
                    scraper_process = {'running': False}
            except Exception as e:
                logger.debug(f"[{g.request_id}] psutil also failed: {type(e).__name__}")
                scraper_process = {'running': False, 'error': f'{type(e).__name__}'}
        
        if scraper_process is None:
            scraper_process = {'running': False}
            
    except Exception as e:
        logger.warning(f"[{g.request_id}] Could not check scraper process: {type(e).__name__}: {str(e)}")
        scraper_process = {'running': False, 'error': f'{type(e).__name__}'}
    
    # Check if training is currently running
    training_process = None
    try:
        # Try pgrep first (Linux/Unix)
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'train_models'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                training_process = {
                    'running': True,
                    'process_count': len([p for p in pids if p]),
                    'pids': [int(p) for p in pids if p]
                }
            else:
                training_process = {'running': False}
        except (FileNotFoundError, OSError, PermissionError):
            # Fallback to psutil (cross-platform)
            try:
                import psutil
                running_pids = []
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        if 'train_models' in cmdline:
                            running_pids.append(proc.info['pid'])
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                if running_pids:
                    training_process = {
                        'running': True,
                        'process_count': len(running_pids),
                        'pids': running_pids
                    }
                else:
                    training_process = {'running': False}
            except Exception as e:
                logger.debug(f"[{g.request_id}] psutil also failed: {type(e).__name__}")
                training_process = {'running': False, 'error': f'{type(e).__name__}'}
        
        if training_process is None:
            training_process = {'running': False}
            
    except Exception as e:
        logger.warning(f"[{g.request_id}] Could not check training process: {type(e).__name__}: {str(e)}")
        training_process = {'running': False, 'error': f'{type(e).__name__}'}
    
    response = {
        'status': 'healthy' if db_status == 'connected' else 'degraded',
        'service': 'BPR Backend API',
        'version': '1.0.0',
        'git_commit': '6e8cea7',  # Latest commit with improved process detection
        'timestamp': datetime.utcnow().isoformat(),
        'message': 'API is operational',
        'database': {
            'status': db_status,
            'message': 'Database is connected' if db_status == 'connected' else db_status
        },
        'ml_model': ml_info,
        'ml_models': ml_models_status,
        'scraping': scraping_status,
        'training': training_status,
        'processes': {
            'scraper': scraper_process,
            'training': training_process
        }
    }
    
    status_code = 200 if db_status == 'connected' else 503
    return jsonify(response), status_code

@app.route('/api/debug/script-paths', methods=['GET'])
@handle_errors
def debug_script_paths():
    """Debug endpoint to verify script paths are accessible"""
    logger.info(f"[{g.request_id}] Script paths debug requested")
    
    # Check training script
    training_script_docker = '/app/ML_Model/train_models.py'
    training_script_local = os.path.join(os.path.dirname(__file__), '../../ML_Model/train_models.py')
    
    # Check scraper scripts (both old and new)
    scraper_script_docker = '/app/ML_Model/auto_scraper.py'
    scraper_script_local = os.path.join(os.path.dirname(__file__), '../../ML_Model/auto_scraper.py')
    
    incremental_scraper_docker = '/app/ML_Model/bilbasen_incremental.py'
    incremental_scraper_local = os.path.join(os.path.dirname(__file__), '../../ML_Model/bilbasen_incremental.py')
    
    # Check Python availability
    python3_available = False
    python_available = False
    try:
        subprocess.run(['which', 'python3'], capture_output=True, check=True)
        python3_available = True
    except:
        pass
    
    try:
        subprocess.run(['which', 'python'], capture_output=True, check=True)
        python_available = True
    except:
        pass
    
    # List ML_Model directory if it exists
    ml_model_dir_contents = []
    ml_model_dir = '/app/ML_Model'
    if os.path.exists(ml_model_dir) and os.path.isdir(ml_model_dir):
        try:
            ml_model_dir_contents = os.listdir(ml_model_dir)
        except Exception as e:
            ml_model_dir_contents = [f"Error: {str(e)}"]
    
    return jsonify({
        'training_script': {
            'docker_path': training_script_docker,
            'docker_exists': os.path.exists(training_script_docker),
            'docker_readable': os.access(training_script_docker, os.R_OK) if os.path.exists(training_script_docker) else False,
            'local_path': training_script_local,
            'local_exists': os.path.exists(training_script_local),
            'local_readable': os.access(training_script_local, os.R_OK) if os.path.exists(training_script_local) else False
        },
        'scraper_script_legacy': {
            'docker_path': scraper_script_docker,
            'docker_exists': os.path.exists(scraper_script_docker),
            'docker_readable': os.access(scraper_script_docker, os.R_OK) if os.path.exists(scraper_script_docker) else False,
            'local_path': scraper_script_local,
            'local_exists': os.path.exists(scraper_script_local),
            'local_readable': os.access(scraper_script_local, os.R_OK) if os.path.exists(scraper_script_local) else False
        },
        'scraper_script_incremental': {
            'docker_path': incremental_scraper_docker,
            'docker_exists': os.path.exists(incremental_scraper_docker),
            'docker_readable': os.access(incremental_scraper_docker, os.R_OK) if os.path.exists(incremental_scraper_docker) else False,
            'local_path': incremental_scraper_local,
            'local_exists': os.path.exists(incremental_scraper_local),
            'local_readable': os.access(incremental_scraper_local, os.R_OK) if os.path.exists(incremental_scraper_local) else False,
            'currently_used': True
        },
        'python': {
            'python3_available': python3_available,
            'python_available': python_available
        },
        'ml_model_directory': {
            'path': ml_model_dir,
            'exists': os.path.exists(ml_model_dir),
            'is_directory': os.path.isdir(ml_model_dir) if os.path.exists(ml_model_dir) else False,
            'contents': ml_model_dir_contents
        },
        'current_working_directory': os.getcwd(),
        'app_file_location': __file__
    }), 200

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

@app.route('/api/trigger-scraping', methods=['POST'])
@handle_errors
def trigger_scraping():
    """Trigger scraping process in the background"""
    import threading
    
    logger.info(f"[{g.request_id}] ========== SCRAPER TRIGGER START ==========")
    logger.info(f"[{g.request_id}] Scraping trigger requested")
    
    # Check if already running
    try:
        logger.info(f"[{g.request_id}] Step 1: Checking for running scraper processes...")
        # Check for any scraper process (new incremental scraper or legacy ones)
        patterns_to_check = ['bilbasen_incremental', 'auto_scraper', 'bilbasen_scraper']
        found_running = False
        
        for pattern in patterns_to_check:
            logger.info(f"[{g.request_id}] Checking for pattern: {pattern}")
            result = subprocess.run(
                ['pgrep', '-f', pattern],
                capture_output=True,
                text=True,
                timeout=2
            )
            logger.info(f"[{g.request_id}] pgrep result for {pattern}: returncode={result.returncode}, stdout={result.stdout.strip()}")
            if result.returncode == 0:
                found_running = True
                logger.warning(f"[{g.request_id}] Found running scraper: {pattern} (PID: {result.stdout.strip()})")
                break
        
        if found_running:
            logger.info(f"[{g.request_id}] Scraper already running - rejecting request")
            return jsonify({
                'success': False,
                'message': 'Scraper is already running',
                'running': True
            }), 400
        
        logger.info(f"[{g.request_id}] No running scraper found - proceeding")
    except Exception as e:
        logger.warning(f"[{g.request_id}] Could not check scraper status: {type(e).__name__}: {e}")
        logger.warning(f"[{g.request_id}] Continuing anyway...")
    
    # Parse request for scraping mode
    data = request.get_json() or {}
    mode = data.get('mode', 'incremental')  # 'incremental' or 'full'
    logger.info(f"[{g.request_id}] Step 2: Parsed scraping mode: {mode}")
    
    # Capture request_id before thread context
    request_id = g.request_id
    
    # Create initial scraping log entry in database
    from app.models import ScrapingLog
    scraping_log = ScrapingLog(
        source_name='bilbasen',
        scraping_mode=mode,
        started_at=datetime.utcnow(),
        success=False  # Will update to True if successful
    )
    db.session.add(scraping_log)
    db.session.commit()
    log_id = scraping_log.id
    logger.info(f"[{g.request_id}] Created scraping log entry: {log_id}")
    
    def run_scraper():
        """Background thread to run scraper"""
        thread_id = threading.current_thread().name
        try:
            logger.info(f"[{request_id}][{thread_id}] ===== BACKGROUND THREAD STARTED =====")
            # Use the new incremental scraper that works with AWS WAF
            script_path = '/app/ML_Model/bilbasen_incremental.py'
            logger.info(f"[{request_id}][{thread_id}] Step 3a: Checking Docker script path: {script_path}")
            
            # Check if script exists
            if not os.path.exists(script_path):
                logger.warning(f"[{request_id}][{thread_id}] Docker path not found, trying local development path...")
                # Fallback to relative path for local development
                script_path = os.path.join(os.path.dirname(__file__), '../../ML_Model/bilbasen_incremental.py')
                logger.info(f"[{request_id}][{thread_id}] Step 3b: Using fallback script path: {script_path}")
            
            script_exists = os.path.exists(script_path)
            script_readable = os.access(script_path, os.R_OK) if script_exists else False
            script_executable = os.access(script_path, os.X_OK) if script_exists else False
            
            logger.info(f"[{request_id}][{thread_id}] Script validation: exists={script_exists}, readable={script_readable}, executable={script_executable}")
            
            if not script_exists:
                error_msg = f"Scraper script not found at: {script_path}"
                logger.error(f"[{request_id}][{thread_id}] {error_msg}")
                raise FileNotFoundError(error_msg)
            
            logger.info(f"[{request_id}][{thread_id}] Step 4: Script validated, preparing to start: {script_path}")
            
            # Use python3 on Linux
            python_cmd = 'python3'
            logger.info(f"[{request_id}][{thread_id}] Step 5: Using Python command: {python_cmd}")
            
            # Verify python3 exists
            try:
                python_check = subprocess.run(['which', python_cmd], capture_output=True, text=True, timeout=2)
                logger.info(f"[{request_id}][{thread_id}] Python location: {python_check.stdout.strip()}")
            except Exception as e:
                logger.warning(f"[{request_id}][{thread_id}] Could not verify python location: {e}")
            
            # Prepare environment variables for the scraper script
            logger.info(f"[{request_id}][{thread_id}] Step 6: Preparing environment variables...")
            env = os.environ.copy()
            
            # Get database credentials from Flask's DATABASE_URL
            database_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            logger.info(f"[{request_id}][{thread_id}] Database URL present: {bool(database_url)}")
            
            # Parse database URL to extract credentials
            # Format: postgresql://user:password@host:port/dbname
            if database_url and 'postgresql://' in database_url:
                import re
                match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url)
                if match:
                    db_user, db_pass, db_host, db_port, db_name = match.groups()
                    env['POSTGRES_USER'] = db_user
                    env['POSTGRES_PASSWORD'] = db_pass
                    env['POSTGRES_HOST'] = db_host
                    env['POSTGRES_PORT'] = db_port
                    env['POSTGRES_DB'] = db_name
                    logger.info(f"[{request_id}][{thread_id}] Parsed DB credentials from URI")
                else:
                    logger.warning(f"[{request_id}][{thread_id}] Could not parse database URL")
            
            # Fallback to defaults if not parsed
            if 'POSTGRES_DB' not in env:
                env['POSTGRES_DB'] = 'car_prediction'
                logger.info(f"[{request_id}][{thread_id}] Using default POSTGRES_DB")
            if 'POSTGRES_USER' not in env:
                env['POSTGRES_USER'] = 'bpr_user'
                logger.info(f"[{request_id}][{thread_id}] Using default POSTGRES_USER")
            if 'POSTGRES_PASSWORD' not in env:
                env['POSTGRES_PASSWORD'] = 'your_secure_password'
                logger.info(f"[{request_id}][{thread_id}] Using default POSTGRES_PASSWORD")
            if 'POSTGRES_HOST' not in env:
                env['POSTGRES_HOST'] = 'db'
                logger.info(f"[{request_id}][{thread_id}] Using default POSTGRES_HOST")
            if 'POSTGRES_PORT' not in env:
                env['POSTGRES_PORT'] = '5432'
                logger.info(f"[{request_id}][{thread_id}] Using default POSTGRES_PORT")
            
            logger.info(f"[{request_id}][{thread_id}] Final env vars: DB={env.get('POSTGRES_DB')}, USER={env.get('POSTGRES_USER')}, HOST={env.get('POSTGRES_HOST')}, PORT={env.get('POSTGRES_PORT')}")
            
            # Build command - mode ignored for incremental scraper (always incremental)
            logger.info(f"[{request_id}][{thread_id}] Step 7: Building command...")
            cmd = [python_cmd, script_path]
            if mode == 'test':
                cmd.append('--test')  # Only 10 listings for testing
                logger.info(f"[{request_id}][{thread_id}] Test mode enabled - will scrape only 10 listings")
            
            logger.info(f"[{request_id}][{thread_id}] Step 8: Executing command: {' '.join(cmd)}")
            logger.info(f"[{request_id}][{thread_id}] Working directory: {os.getcwd()}")
            logger.info(f"[{request_id}][{thread_id}] Environment summary: POSTGRES_HOST={env.get('POSTGRES_HOST')}, POSTGRES_DB={env.get('POSTGRES_DB')}")
            
            logger.info(f"[{request_id}][{thread_id}] Step 9: Starting subprocess.Popen...")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                start_new_session=True
            )
            logger.info(f"[{request_id}][{thread_id}] [SUCCESS] Process spawned with PID: {process.pid}")
            
            # Wait a moment and check if process is still alive
            import time
            logger.info(f"[{request_id}][{thread_id}] Step 10: Waiting 0.5s to check process health...")
            time.sleep(0.5)
            
            poll_result = process.poll()
            logger.info(f"[{request_id}][{thread_id}] Process poll result: {poll_result} (None=still running)")
            
            if poll_result is not None:
                stdout, stderr = process.communicate(timeout=5)
                stdout_text = stdout.decode('utf-8', errors='ignore')
                stderr_text = stderr.decode('utf-8', errors='ignore')
                
                logger.error(f"[{request_id}][{thread_id}] [FAILED] Scraper died immediately!")
                logger.error(f"[{request_id}][{thread_id}] Exit code: {process.returncode}")
                logger.error(f"[{request_id}][{thread_id}] STDOUT ({len(stdout_text)} chars): {stdout_text[:500]}")
                logger.error(f"[{request_id}][{thread_id}] STDERR ({len(stderr_text)} chars): {stderr_text[:500]}")
                
                # Try to determine the error type
                error_type = "Unknown error"
                if 'ModuleNotFoundError' in stderr_text or 'ImportError' in stderr_text:
                    error_type = "Missing Python dependency"
                    logger.error(f"[{request_id}][{thread_id}] ERROR TYPE: {error_type}")
                elif 'SyntaxError' in stderr_text:
                    error_type = "Python syntax error in script"
                    logger.error(f"[{request_id}][{thread_id}] ERROR TYPE: {error_type}")
                elif 'PermissionError' in stderr_text or 'Permission denied' in stderr_text:
                    error_type = "Permission denied"
                    logger.error(f"[{request_id}][{thread_id}] ERROR TYPE: {error_type}")
                elif 'ConnectionError' in stderr_text or 'could not connect' in stderr_text.lower():
                    error_type = "Database connection failed"
                    logger.error(f"[{request_id}][{thread_id}] ERROR TYPE: {error_type}")
                else:
                    logger.error(f"[{request_id}][{thread_id}] ERROR TYPE: {error_type}")
                
                # Update database log with immediate failure
                try:
                    from app.models import ScrapingLog
                    log_entry = db.session.get(ScrapingLog, log_id)
                    if log_entry:
                        log_entry.success = False
                        log_entry.error_message = f"{error_type}: {stderr_text[:500]}"
                        log_entry.completed_at = datetime.utcnow()
                        db.session.commit()
                        logger.info(f"[{request_id}][{thread_id}] Updated scraping log with immediate failure")
                except Exception as db_error:
                    logger.error(f"[{request_id}][{thread_id}] Failed to update scraping log: {db_error}")
            else:
                logger.info(f"[{request_id}][{thread_id}] [SUCCESS] Process still running after 0.5s - scraper appears healthy")
                
                # Monitor for another 5 seconds to catch early crashes
                logger.info(f"[{request_id}][{thread_id}] Step 10b: Monitoring process for 5 more seconds...")
                for i in range(1, 6):
                    time.sleep(1)
                    poll_result = process.poll()
                    if poll_result is not None:
                        stdout, stderr = process.communicate(timeout=5)
                        stdout_text = stdout.decode('utf-8', errors='ignore')
                        stderr_text = stderr.decode('utf-8', errors='ignore')
                        
                        logger.error(f"[{request_id}][{thread_id}] [FAILED] Scraper died after {i} seconds!")
                        logger.error(f"[{request_id}][{thread_id}] Exit code: {process.returncode}")
                        logger.error(f"[{request_id}][{thread_id}] STDOUT: {stdout_text}")
                        logger.error(f"[{request_id}][{thread_id}] STDERR: {stderr_text}")
                        
                        # Error classification
                        error_type = "Script execution error"
                        if 'ModuleNotFoundError' in stderr_text or 'ImportError' in stderr_text:
                            error_type = "Missing Python dependency"
                            logger.error(f"[{request_id}][{thread_id}] ERROR TYPE: {error_type}")
                        elif 'psycopg2' in stderr_text or 'PostgreSQL' in stderr_text:
                            error_type = "Database connection/library issue"
                            logger.error(f"[{request_id}][{thread_id}] ERROR TYPE: {error_type}")
                        elif 'ConnectionError' in stderr_text or 'Connection refused' in stderr_text:
                            error_type = "Database connection refused"
                            logger.error(f"[{request_id}][{thread_id}] ERROR TYPE: {error_type}")
                        else:
                            logger.error(f"[{request_id}][{thread_id}] ERROR TYPE: {error_type}")
                        
                        # Update database log with failure
                        try:
                            from app.models import ScrapingLog
                            log_entry = db.session.get(ScrapingLog, log_id)
                            if log_entry:
                                log_entry.success = False
                                log_entry.error_message = f"{error_type}: {stderr_text[:500]}"
                                log_entry.completed_at = datetime.utcnow()
                                db.session.commit()
                                logger.info(f"[{request_id}][{thread_id}] Updated scraping log with failure after {i}s")
                        except Exception as db_error:
                            logger.error(f"[{request_id}][{thread_id}] Failed to update scraping log: {db_error}")
                        break
                    logger.info(f"[{request_id}][{thread_id}] Still running after {i} seconds...")
                else:
                    logger.info(f"[{request_id}][{thread_id}] [SUCCESS] Process survived 5.5 seconds - scraper is running")
                    logger.info(f"[{request_id}][{thread_id}] Scraper will continue running in background")
                    
                    # Update database log - scraper started successfully
                    # Note: Final stats will be updated by the scraper script itself when it completes
                    try:
                        from app.models import ScrapingLog
                        log_entry = db.session.get(ScrapingLog, log_id)
                        if log_entry:
                            log_entry.success = True  # Started successfully
                            # Don't set completed_at yet - scraper will update when done
                            db.session.commit()
                            logger.info(f"[{request_id}][{thread_id}] Updated scraping log - scraper running")
                    except Exception as db_error:
                        logger.error(f"[{request_id}][{thread_id}] Failed to update scraping log: {db_error}")
                
        except Exception as e:
            logger.error(f"[{request_id}][{thread_id}] [EXCEPTION] Failed to start scraper: {type(e).__name__}: {e}", exc_info=True)
            # Update database log with exception
            try:
                from app.models import ScrapingLog
                log_entry = db.session.get(ScrapingLog, log_id)
                if log_entry:
                    log_entry.success = False
                    log_entry.error_message = f"Exception: {type(e).__name__}: {str(e)}"
                    log_entry.completed_at = datetime.utcnow()
                    db.session.commit()
            except Exception as db_error:
                logger.error(f"[{request_id}][{thread_id}] Failed to update scraping log with exception: {db_error}")
    
    logger.info(f"[{g.request_id}] Step 11: Creating background thread...")
    thread = threading.Thread(target=run_scraper, daemon=True, name=f"ScraperThread-{g.request_id[:8]}")
    logger.info(f"[{g.request_id}] Step 12: Starting background thread...")
    thread.start()
    logger.info(f"[{g.request_id}] Background thread started: {thread.name}")
    logger.info(f"[{g.request_id}] ========== RETURNING 202 RESPONSE ==========")
    
    return jsonify({
        'success': True,
        'message': 'Incremental scraper started - will fetch new listings and add to database',
        'scraper_type': 'incremental',
        'mode': mode,
        'estimated_duration': 'Minutes to hours depending on new listings'
    }), 202

@app.route('/api/scraper-logs', methods=['GET'])
@handle_errors
def get_scraper_logs():
    """Get recent scraper logs for monitoring"""
    logger.info(f"[{g.request_id}] Scraper logs requested")
    
    try:
        # Path to incremental scraper log
        log_dir = '/app/ML_Model/logs'
        today = datetime.now().strftime('%Y%m%d')
        log_file = os.path.join(log_dir, f'incremental_{today}.log')
        
        if not os.path.exists(log_file):
            # Try fallback location for local development
            log_file = os.path.join(os.path.dirname(__file__), '../../ML_Model/logs', f'incremental_{today}.log')
            log_file = os.path.abspath(log_file)
        
        if not os.path.exists(log_file):
            return jsonify({
                'success': False,
                'message': 'No log file found for today',
                'logs': []
            }), 404
        
        # Get last N lines with robust parameter parsing
        try:
            lines_param = request.args.get('lines', '50')
            # Strip any quotes or whitespace that might have been added
            lines_param = str(lines_param).strip().strip('"').strip("'")
            lines_to_read = int(lines_param)
            if lines_to_read <= 0:
                lines_to_read = 50
        except (ValueError, TypeError) as e:
            logger.warning(f"[{g.request_id}] Invalid lines parameter '{request.args.get('lines')}', using default 50")
            lines_to_read = 50
        
        with open(log_file, 'r', encoding='utf-8') as f:
            # Read all lines and get last N
            all_lines = f.readlines()
            recent_lines = all_lines[-lines_to_read:] if len(all_lines) > lines_to_read else all_lines
        
        return jsonify({
            'success': True,
            'log_file': os.path.basename(log_file),
            'total_lines': len(all_lines),
            'returned_lines': len(recent_lines),
            'logs': recent_lines
        }), 200
        
    except Exception as e:
        logger.error(f"[{g.request_id}] Failed to read logs: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to read logs: {str(e)}',
            'logs': []
        }), 500

@app.route('/api/trigger-training', methods=['POST'])
@handle_errors
def trigger_training():
    """Trigger model training process in the background"""
    import threading
    from app.models import ModelTrainingRun
    
    logger.info(f"[{g.request_id}] Training trigger requested")
    
    # Check if there's already a pending or running training
    try:
        existing_training = ModelTrainingRun.query.filter(
            ModelTrainingRun.status.in_(['pending', 'running'])
        ).first()
        
        if existing_training:
            return jsonify({
                'success': False,
                'message': 'Training is already in progress',
                'running': True,
                'training_id': existing_training.id
            }), 400
    except Exception as e:
        logger.warning(f"[{g.request_id}] Could not check existing training: {e}")
    
    # Check if process is actually running
    try:
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'train_models'],
                capture_output=True,
                text=True,
                timeout=2
            )
        except (FileNotFoundError, OSError, PermissionError) as e:
            # Fallback to ps
            logger.debug(f"[{g.request_id}] pgrep not available for trigger check, using ps fallback")
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=2)
            if any('train_models' in line for line in result.stdout.split('\n')):
                return jsonify({
                    'success': False,
                    'message': 'Training process is already running',
                    'running': True
                }), 400
            result = None
        
        if result and result.returncode == 0:
            return jsonify({
                'success': False,
                'message': 'Training process is already running',
                'running': True
            }), 400
    except Exception as e:
        logger.warning(f"[{g.request_id}] Could not check training process: {type(e).__name__}: {e}")
    
    # Create a database entry immediately to track the training
    training_run = None
    try:
        training_run = ModelTrainingRun(
            status='pending',
            notes='Training initiated via API'
        )
        db.session.add(training_run)
        db.session.commit()
        logger.info(f"[{g.request_id}] Created training run record: {training_run.id}")
    except Exception as e:
        logger.error(f"[{g.request_id}] Failed to create training run record: {e}")
        db.session.rollback()
    
    def run_training():
        """Background thread to run training"""
        try:
            # Use absolute path - ML_Model is mounted at /app/ML_Model in Docker
            script_path = '/app/ML_Model/train_models.py'
            
            # Check if script exists
            if not os.path.exists(script_path):
                # Fallback to relative path for local development
                script_path = os.path.join(os.path.dirname(__file__), '../../ML_Model/train_models.py')
                logger.warning(f"Using fallback script path: {script_path}")
            
            logger.info(f"Starting training with script: {script_path}")
            
            # Use python3 or python depending on availability
            python_cmd = 'python3'
            try:
                subprocess.run(['which', 'python3'], capture_output=True, check=True)
            except:
                python_cmd = 'python'
            
            # Prepare environment variables for the training script
            # The script expects: DB_NAME, DB_USER, DB_PASS, DB_HOST, DB_PORT
            env = os.environ.copy()
            
            # Get database credentials from Flask's DATABASE_URL or set defaults
            database_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            
            # Parse database URL to extract credentials
            # Format: postgresql://user:password@host:port/dbname
            if database_url and 'postgresql://' in database_url:
                import re
                match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url)
                if match:
                    db_user, db_pass, db_host, db_port, db_name = match.groups()
                    env['DB_USER'] = db_user
                    env['DB_PASS'] = db_pass
                    env['DB_HOST'] = db_host
                    env['DB_PORT'] = db_port
                    env['DB_NAME'] = db_name
            
            # Fallback to defaults if not parsed
            if 'DB_NAME' not in env:
                env['DB_NAME'] = 'car_prediction'
            if 'DB_USER' not in env:
                env['DB_USER'] = 'bpr_user'
            if 'DB_PASS' not in env:
                env['DB_PASS'] = 'your_secure_password'
            if 'DB_HOST' not in env:
                env['DB_HOST'] = 'db'
            if 'DB_PORT' not in env:
                env['DB_PORT'] = '5432'
            
            logger.info(f"Training env: DB_NAME={env.get('DB_NAME')}, DB_USER={env.get('DB_USER')}, DB_HOST={env.get('DB_HOST')}")
            
            process = subprocess.Popen(
                [python_cmd, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                start_new_session=True
            )
            logger.info(f"Model training started with PID: {process.pid}")
        except Exception as e:
            logger.error(f"Failed to start training: {e}", exc_info=True)
            # Update training run status to failed if we created one
            if training_run:
                try:
                    training_run.status = 'failed'
                    training_run.notes = f'Failed to start: {str(e)}'
                    db.session.commit()
                except:
                    db.session.rollback()
    
    thread = threading.Thread(target=run_training, daemon=True)
    thread.start()
    
    return jsonify({
        'success': True,
        'message': 'Model training started',
        'training_id': training_run.id if training_run else None,
        'estimated_duration': 'Several hours depending on dataset size'
    }), 202

@app.route('/api/cars/<car_id>/image', methods=['GET'])
@handle_errors
def get_car_image(car_id):
    """Get car image by car ID"""
    from flask import send_file
    logger.info(f"[{g.request_id}] Fetching image for car ID: {car_id}")
    
    car = Car.query.get_or_404(car_id)
    
    if not car.image_path or not car.image_downloaded:
        logger.warning(f"[{g.request_id}] No image available for car {car_id}")
        abort(404, description="Image not available")
    
    # Try multiple possible locations for the image
    # Extract just the filename from the path (e.g., "images/6660295.jpg" -> "6660295.jpg")
    filename = os.path.basename(car.image_path)
    
    # Get the current file location and navigate to the images
    # Structure: BPR-BackEnd-API/app/main.py -> ../../BPR-BackEnd-ML-Model/bilbasen_scrape/images/
    current_dir = os.path.dirname(__file__)  # BPR-BackEnd-API/app/
    api_root = os.path.dirname(current_dir)  # BPR-BackEnd-API/
    project_root = os.path.dirname(api_root)  # parent directory (contains both BPR-BackEnd-API and BPR-BackEnd-ML-Model)
    
    possible_paths = [
        # Docker volume mount
        f'/app/images/{filename}',
        # From project root to ML-Model images (non-Docker)
        os.path.join(project_root, 'BPR-BackEnd-ML-Model', 'bilbasen_scrape', 'images', filename),
        # Absolute path on Raspberry Pi (non-Docker)
        f'/home/igor/BachelorApi/BPR-BackEnd-ML-Model/bilbasen_scrape/images/{filename}',
        # Legacy paths
        os.path.join(current_dir, '..', car.image_path),
        os.path.join(current_dir, '..', 'images', filename),
    ]
    
    image_full_path = None
    for path in possible_paths:
        logger.debug(f"[{g.request_id}] Checking path: {path}")
        if os.path.exists(path):
            image_full_path = path
            logger.info(f"[{g.request_id}] Found image at: {path}")
            break
    
    if not image_full_path:
        checked_paths = '\n  '.join(possible_paths)
        logger.error(f"[{g.request_id}] Image file not found. Checked paths:\n  {checked_paths}")
        abort(404, description="Image file not found")
    
    logger.info(f"[{g.request_id}] Serving image for car {car_id} from {image_full_path}")
    return send_file(image_full_path, mimetype='image/jpeg')

@app.route('/api/images/<external_id>', methods=['GET'])
@handle_errors
def get_image_by_external_id(external_id):
    """Get car image by external_id (Bilbasen listing ID)"""
    from flask import send_file
    logger.info(f"[{g.request_id}] Fetching image for external_id: {external_id}")
    
    car = Car.query.filter_by(external_id=external_id).first_or_404()
    
    if not car.image_path or not car.image_downloaded:
        logger.warning(f"[{g.request_id}] No image available for external_id {external_id}")
        abort(404, description="Image not available")
    
    # Extract filename and use same path checking as get_car_image
    filename = os.path.basename(car.image_path)
    current_dir = os.path.dirname(__file__)
    api_root = os.path.dirname(current_dir)
    project_root = os.path.dirname(api_root)
    
    possible_paths = [
        # Docker volume mount
        f'/app/images/{filename}',
        # From project root to ML-Model images (non-Docker)
        os.path.join(project_root, 'BPR-BackEnd-ML-Model', 'bilbasen_scrape', 'images', filename),
        # Absolute path on Raspberry Pi (non-Docker)
        f'/home/igor/BachelorApi/BPR-BackEnd-ML-Model/bilbasen_scrape/images/{filename}',
        # Legacy paths
        os.path.join(current_dir, '..', car.image_path),
        os.path.join(current_dir, '..', 'images', filename),
    ]
    
    image_full_path = None
    for path in possible_paths:
        logger.debug(f"[{g.request_id}] Checking path: {path}")
        if os.path.exists(path):
            image_full_path = path
            logger.info(f"[{g.request_id}] Found image at: {path}")
            break
    
    if not image_full_path:
        checked_paths = '\n  '.join(possible_paths)
        logger.error(f"[{g.request_id}] Image file not found. Checked paths:\n  {checked_paths}")
        abort(404, description="Image file not found")
    
    logger.info(f"[{g.request_id}] Serving image for external_id {external_id}")
    return send_file(image_full_path, mimetype='image/jpeg')

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
    
    # Handle mileage - set to 0 for new cars or null values
    try:
        mileage_value = data.get('mileage')
        if mileage_value is None or mileage_value == '' or mileage_value == 'N/A':
            data['mileage'] = 0
        else:
            data['mileage'] = int(mileage_value)
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


@app.route('/api/predictions/multi/<car_id>', methods=['GET'])
@handle_errors
def get_multi_model_predictions(car_id):
    """Get predictions from all models for a specific car"""
    from app.models import MLModel
    
    logger.info(f"[{g.request_id}] Fetching multi-model predictions for car {car_id}")
    
    # Get all predictions for this car
    predictions = PricePrediction.query.filter_by(car_id=car_id).all()
    
    if not predictions:
        logger.warning(f"[{g.request_id}] No predictions found for car {car_id}")
        return jsonify({
            'success': True,
            'predictions': [],
            'message': 'No predictions available for this car'
        }), 200
    
    # Group by model
    predictions_by_model = {}
    for pred in predictions:
        model_info = MLModel.query.get(pred.model_id) if pred.model_id else None
        model_name = model_info.name if model_info else 'Unknown'
        
        pred_dict = pred.to_dict()
        if model_info:
            pred_dict['model_name'] = model_name
            pred_dict['model_type'] = model_info.model_type
            pred_dict['model_algorithm'] = model_info.algorithm
        
        predictions_by_model[model_name] = pred_dict
    
    logger.info(f"[{g.request_id}] Found {len(predictions_by_model)} model predictions")
    
    return jsonify({
        'success': True,
        'car_id': car_id,
        'predictions': predictions_by_model
    }), 200


@app.route('/api/models', methods=['GET'])
@handle_errors
def get_ml_models():
    """Get all registered ML models"""
    from app.models import MLModel
    
    logger.info(f"[{g.request_id}] Fetching ML models")
    
    # Get filter parameters
    active_only = request.args.get('active', 'true').lower() == 'true'
    model_type = request.args.get('type')
    
    query = MLModel.query
    
    if active_only:
        query = query.filter_by(is_active=True)
    
    if model_type:
        query = query.filter_by(model_type=model_type)
    
    models = query.order_by(desc(MLModel.r2_score)).all()
    
    logger.info(f"[{g.request_id}] Found {len(models)} models")
    
    return jsonify({
        'success': True,
        'models': [m.to_dict() for m in models]
    }), 200


@app.route('/api/models/<model_id>', methods=['GET'])
@handle_errors
def get_ml_model(model_id):
    """Get specific ML model details"""
    from app.models import MLModel, ModelComparisonMetrics
    
    logger.info(f"[{g.request_id}] Fetching model {model_id}")
    
    model = MLModel.query.get_or_404(model_id)
    model_dict = model.to_dict()
    
    # Include latest comparison metrics
    latest_metrics = ModelComparisonMetrics.query.filter_by(
        model_id=model_id
    ).order_by(desc(ModelComparisonMetrics.created_at)).first()
    
    if latest_metrics:
        model_dict['comparison_metrics'] = latest_metrics.to_dict()
    
    logger.info(f"[{g.request_id}] Retrieved model {model.name}")
    
    return jsonify({
        'success': True,
        'model': model_dict
    }), 200


@app.route('/api/models/comparison', methods=['GET'])
@handle_errors
def get_model_comparison():
    """Get comprehensive model comparison data"""
    from app.models import MLModel, ModelComparisonMetrics, ModelTrainingRun
    
    logger.info(f"[{g.request_id}] Fetching model comparison data")
    
    # Get all active models with their latest metrics
    models = MLModel.query.filter_by(is_active=True).all()
    
    comparison_data = []
    for model in models:
        model_dict = model.to_dict()
        
        # Get latest metrics
        latest_metrics = ModelComparisonMetrics.query.filter_by(
            model_id=model.id
        ).order_by(desc(ModelComparisonMetrics.created_at)).first()
        
        if latest_metrics:
            model_dict['comparison_metrics'] = latest_metrics.to_dict()
        
        comparison_data.append(model_dict)
    
    # Get latest training run info
    latest_training_run = ModelTrainingRun.query.order_by(
        desc(ModelTrainingRun.run_date)
    ).first()
    
    training_run_info = latest_training_run.to_dict() if latest_training_run else None
    
    logger.info(f"[{g.request_id}] Compiled comparison data for {len(comparison_data)} models")
    
    return jsonify({
        'success': True,
        'models': comparison_data,
        'latest_training_run': training_run_info,
        'total_models': len(comparison_data)
    }), 200


@app.route('/api/training/runs', methods=['GET'])
@handle_errors
def get_training_runs():
    """Get training run history"""
    from app.models import ModelTrainingRun
    
    pagination_params = get_pagination_params(request.args)
    
    logger.info(f"[{g.request_id}] Fetching training runs page {pagination_params.page}")
    
    pagination = ModelTrainingRun.query.order_by(
        desc(ModelTrainingRun.run_date)
    ).paginate(
        page=pagination_params.page,
        per_page=pagination_params.per_page,
        error_out=False
    )
    
    return jsonify({
        'success': True,
        'training_runs': [run.to_dict() for run in pagination.items],
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
# MARKET STATISTICS ENDPOINT
# ============================================

@app.route('/api/market/statistics', methods=['GET'])
@handle_errors
def get_market_statistics():
    """Get comprehensive market statistics for data visualization"""
    logger.info(f"[{g.request_id}] Fetching market statistics")
    
    try:
        # Check if we have any data
        total_cars = db.session.query(func.count(Car.id)).scalar()
        if not total_cars or total_cars == 0:
            logger.warning(f"[{g.request_id}] No cars in database for statistics")
            return jsonify({
                'success': False,
                'error': 'No data available',
                'message': 'The database does not contain any car listings yet.'
            }), 404
    
        # Price statistics by brand (top 15 brands by count)
        brand_stats = db.session.query(
            Car.brand,
            func.count(Car.id).label('total_cars'),
            func.avg(Car.price).label('avg_price'),
            func.min(Car.price).label('min_price'),
            func.max(Car.price).label('max_price')
        ).filter(
            Car.price.isnot(None)
        ).group_by(Car.brand).order_by(desc('total_cars')).limit(15).all()
        
        # Fuel type distribution
        fuel_type_dist = db.session.query(
            Car.fuel_type,
            func.count(Car.id).label('count'),
            func.avg(Car.price).label('avg_price')
        ).filter(
            Car.fuel_type.isnot(None),
            Car.price.isnot(None)
        ).group_by(Car.fuel_type).all()
        
        # Body type distribution
        body_type_dist = db.session.query(
            Car.body_type,
            func.count(Car.id).label('count'),
            func.avg(Car.price).label('avg_price')
        ).filter(
            Car.body_type.isnot(None),
            Car.price.isnot(None)
        ).group_by(Car.body_type).order_by(desc('count')).all()
        
        # Transmission distribution
        transmission_dist = db.session.query(
            Car.transmission,
            func.count(Car.id).label('count')
        ).filter(
            Car.transmission.isnot(None)
        ).group_by(Car.transmission).all()
        
        # Year distribution (last 10 years)
        current_year = datetime.now().year
        year_dist = db.session.query(
            Car.year,
            func.count(Car.id).label('count'),
            func.avg(Car.price).label('avg_price'),
            func.avg(Car.mileage).label('avg_mileage')
        ).filter(
            Car.year.isnot(None),
            Car.year >= current_year - 10,
            Car.price.isnot(None)
        ).group_by(Car.year).order_by(Car.year).all()
        
        # Price ranges distribution
        price_ranges = db.session.query(
            func.count(Car.id).label('count'),
            case(
                (Car.price < 100000, 'Under 100k'),
                (Car.price < 200000, '100k-200k'),
                (Car.price < 300000, '200k-300k'),
                (Car.price < 500000, '300k-500k'),
                (Car.price < 1000000, '500k-1M'),
                else_='Over 1M'
            ).label('range')
        ).filter(
            Car.price.isnot(None)
        ).group_by('range').all()
        
        # Mileage statistics by year
        mileage_by_year = db.session.query(
            Car.year,
            func.avg(Car.mileage).label('avg_mileage'),
            func.min(Car.mileage).label('min_mileage'),
            func.max(Car.mileage).label('max_mileage')
        ).filter(
            Car.year.isnot(None),
            Car.mileage.isnot(None),
            Car.year >= current_year - 10
        ).group_by(Car.year).order_by(Car.year).all()
        
        # Top models by brand (top 6 brands)
        top_brands = [b[0] for b in brand_stats[:6]]
        models_by_brand = {}
        for brand in top_brands:
            models = db.session.query(
                Car.model,
                func.count(Car.id).label('count'),
                func.avg(Car.price).label('avg_price')
            ).filter(
                Car.brand == brand,
                Car.price.isnot(None)
            ).group_by(Car.model).order_by(desc('count')).limit(5).all()
            models_by_brand[brand] = [
                {'model': m[0], 'count': m[1], 'avg_price': float(m[2])}
                for m in models
            ]
        
        # Overall statistics
        overall_stats = db.session.query(
            func.count(Car.id).label('total_cars'),
            func.avg(Car.price).label('avg_price'),
            func.min(Car.price).label('min_price'),
            func.max(Car.price).label('max_price'),
            func.avg(Car.mileage).label('avg_mileage'),
            func.avg(Car.year).label('avg_year')
        ).filter(Car.price.isnot(None)).first()
        
        # Price trend by listing date (last 30 days if available)
        price_trend = db.session.query(
            func.date(Car.listing_date).label('date'),
            func.avg(Car.price).label('avg_price'),
            func.count(Car.id).label('listings')
        ).filter(
            Car.listing_date.isnot(None),
            Car.price.isnot(None)
        ).group_by(func.date(Car.listing_date)).order_by(func.date(Car.listing_date).desc()).limit(30).all()
        
        # Horsepower distribution
        hp_ranges = db.session.query(
            func.count(Car.id).label('count'),
            case(
                (Car.horsepower < 100, 'Under 100 HP'),
                (Car.horsepower < 150, '100-150 HP'),
                (Car.horsepower < 200, '150-200 HP'),
                (Car.horsepower < 300, '200-300 HP'),
                else_='Over 300 HP'
            ).label('range')
        ).filter(
            Car.horsepower.isnot(None)
        ).group_by('range').all()
        
        logger.info(f"[{g.request_id}] Market statistics compiled successfully")
        
        return jsonify({
            'success': True,
            'statistics': {
                'overall': {
                    'total_cars': overall_stats.total_cars,
                    'avg_price': float(overall_stats.avg_price) if overall_stats.avg_price else None,
                    'min_price': float(overall_stats.min_price) if overall_stats.min_price else None,
                    'max_price': float(overall_stats.max_price) if overall_stats.max_price else None,
                    'avg_mileage': float(overall_stats.avg_mileage) if overall_stats.avg_mileage else None,
                    'avg_year': float(overall_stats.avg_year) if overall_stats.avg_year else None
                },
            'brands': [
                {
                    'brand': b[0],
                    'total_cars': b[1],
                    'avg_price': float(b[2]) if b[2] else None,
                    'min_price': float(b[3]) if b[3] else None,
                    'max_price': float(b[4]) if b[4] else None
                }
                for b in brand_stats
            ],
            'fuel_types': [
                {
                    'type': f[0],
                    'count': f[1],
                    'avg_price': float(f[2]) if f[2] else None
                }
                for f in fuel_type_dist
            ],
            'body_types': [
                {
                    'type': b[0],
                    'count': b[1],
                    'avg_price': float(b[2]) if b[2] else None
                }
                for b in body_type_dist
            ],
            'transmissions': [
                {'type': t[0], 'count': t[1]}
                for t in transmission_dist
            ],
            'years': [
                {
                    'year': y[0],
                    'count': y[1],
                    'avg_price': float(y[2]) if y[2] else None,
                    'avg_mileage': float(y[3]) if y[3] else None
                }
                for y in year_dist
            ],
            'price_ranges': sorted([
                {'range': p[1], 'count': p[0]}
                for p in price_ranges
            ], key=lambda x: {
                'Under 100k': 0,
                '100k-200k': 1,
                '200k-300k': 2,
                '300k-500k': 3,
                '500k-1M': 4,
                'Over 1M': 5
            }.get(x['range'], 999)),
            'mileage_by_year': [
                {
                    'year': m[0],
                    'avg_mileage': float(m[1]) if m[1] else None,
                    'min_mileage': float(m[2]) if m[2] else None,
                    'max_mileage': float(m[3]) if m[3] else None
                }
                for m in mileage_by_year
            ],
            'models_by_brand': models_by_brand,
            'price_trend': [
                {
                    'date': str(t[0]),
                    'avg_price': float(t[1]) if t[1] else None,
                    'listings': t[2]
                }
                for t in reversed(list(price_trend))
            ],
            'horsepower_ranges': sorted([
                {'range': h[1], 'count': h[0]}
                for h in hp_ranges
            ], key=lambda x: {
                'Under 100 HP': 0,
                '100-150 HP': 1,
                '150-200 HP': 2,
                '200-300 HP': 3,
                'Over 300 HP': 4
            }.get(x['range'], 999))
            }
        }), 200
    
    except Exception as e:
        logger.error(f"[{g.request_id}] Error fetching market statistics: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'Failed to fetch market statistics',
            'message': str(e)
        }), 500

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

@app.errorhandler(405)
def method_not_allowed(error):
    logger.warning(f"[{g.request_id}] 405 error: {request.method} {request.path}")
    return jsonify({
        'success': False,
        'error': 'Method not allowed',
        'method': request.method,
        'path': request.path
    }), 405

@app.errorhandler(Exception)
def handle_exception(error):
    # Don't catch HTTP exceptions, let Flask handle them
    if isinstance(error, HTTPException):
        return error
    
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