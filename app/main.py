from flask import Flask, jsonify, request
from flask_cors import CORS
from app.models import db, Car, PricePrediction, ScrapingLog, MarketStatistics
from app.ml.predictor import CarPricePredictor
from sqlalchemy import func, desc
import os
from datetime import datetime

app = Flask(__name__)

# Configure CORS - Allow requests from Netlify frontend
allowed_origins = os.getenv('ALLOWED_ORIGINS', '*')
if allowed_origins != '*':
    allowed_origins = allowed_origins.split(',')

CORS(app, 
     resources={r"/*": {"origins": allowed_origins}},
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    if allowed_origins == '*':
        response.headers.add('Access-Control-Allow-Origin', '*')
    elif origin in allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', origin)
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://bpr_user:bpr_password@db:5432/car_prediction')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['JSON_SORT_KEYS'] = False

# Initialize database
db.init_app(app)

# Initialize ML predictor
predictor = CarPricePredictor()

# ============================================
# HEALTH CHECK
# ============================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db.session.execute(db.text('SELECT 1'))
        db_status = 'connected'
    except Exception as e:
        db_status = f'error: {str(e)}'
    
    return jsonify({
        'status': 'healthy',
        'service': 'BPR Backend API',
        'version': '1.0.0',
        'database': db_status,
        'ml_model': predictor.get_model_info()
    }), 200

# ============================================
# CAR ENDPOINTS
# ============================================

@app.route('/api/cars', methods=['GET'])
def get_cars():
    """Get all cars with filtering and pagination"""
    try:
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        per_page = min(per_page, 100)  # Max 100 per page
        
        # Filters
        brand = request.args.get('brand')
        model = request.args.get('model')
        year_min = request.args.get('year_min', type=int)
        year_max = request.args.get('year_max', type=int)
        price_min = request.args.get('price_min', type=float)
        price_max = request.args.get('price_max', type=float)
        mileage_max = request.args.get('mileage_max', type=int)
        fuel_type = request.args.get('fuel_type')
        transmission = request.args.get('transmission')
        body_type = request.args.get('body_type')
        location = request.args.get('location')
        
        # Sorting
        sort_by = request.args.get('sort_by', 'listing_date')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Build query
        query = Car.query
        
        if brand:
            query = query.filter(Car.brand.ilike(f'%{brand}%'))
        if model:
            query = query.filter(Car.model.ilike(f'%{model}%'))
        if year_min:
            query = query.filter(Car.year >= year_min)
        if year_max:
            query = query.filter(Car.year <= year_max)
        if price_min:
            query = query.filter(Car.price >= price_min)
        if price_max:
            query = query.filter(Car.price <= price_max)
        if mileage_max:
            query = query.filter(Car.mileage <= mileage_max)
        if fuel_type:
            query = query.filter(Car.fuel_type.ilike(fuel_type))
        if transmission:
            query = query.filter(Car.transmission.ilike(transmission))
        if body_type:
            query = query.filter(Car.body_type.ilike(body_type))
        if location:
            query = query.filter(Car.location.ilike(f'%{location}%'))
        
        # Apply sorting
        if hasattr(Car, sort_by):
            sort_column = getattr(Car, sort_by)
            if sort_order == 'desc':
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(sort_column)
        
        # Execute query with pagination
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
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
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cars/<car_id>', methods=['GET'])
def get_car(car_id):
    """Get specific car by ID"""
    try:
        car = Car.query.get_or_404(car_id)
        car_data = car.to_dict()
        
        # Include latest prediction if available
        latest_prediction = PricePrediction.query.filter_by(
            car_id=car_id
        ).order_by(desc(PricePrediction.created_at)).first()
        
        if latest_prediction:
            car_data['prediction'] = latest_prediction.to_dict()
        
        return jsonify({
            'success': True,
            'car': car_data
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 404

@app.route('/api/cars', methods=['POST'])
def create_car():
    """Create a new car listing (for scraping/admin use)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['brand', 'model', 'year', 'mileage', 'fuel_type', 
                          'transmission', 'body_type', 'price']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
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
        
        return jsonify({
            'success': True,
            'message': 'Car created successfully',
            'car': car.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# PREDICTION ENDPOINTS
# ============================================

@app.route('/api/predict', methods=['POST'])
def predict_price():
    """Predict car price based on features"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['brand', 'model', 'year', 'mileage', 'fuel_type', 
                          'transmission', 'body_type']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate year
        current_year = datetime.now().year
        if data['year'] < 1900 or data['year'] > current_year + 1:
            return jsonify({
                'success': False,
                'error': f'Year must be between 1900 and {current_year + 1}'
            }), 400
        
        # Validate mileage
        if data['mileage'] < 0:
            return jsonify({
                'success': False,
                'error': 'Mileage cannot be negative'
            }), 400
        
        # Use ML predictor to get price prediction
        prediction_result = predictor.predict(data)
        
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
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/predictions', methods=['GET'])
def get_predictions():
    """Get prediction history"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        pagination = PricePrediction.query.order_by(
            desc(PricePrediction.created_at)
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'predictions': [p.to_dict() for p in pagination.items],
            'pagination': {
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': page
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# FILTER OPTIONS ENDPOINTS
# ============================================

@app.route('/api/brands', methods=['GET'])
def get_brands():
    """Get all available car brands"""
    try:
        brands = db.session.query(
            Car.brand,
            func.count(Car.id).label('count')
        ).group_by(Car.brand).order_by(Car.brand).all()
        
        return jsonify({
            'success': True,
            'brands': [{'name': brand, 'count': count} for brand, count in brands]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/models/<brand>', methods=['GET'])
def get_models(brand):
    """Get all models for a specific brand"""
    try:
        models = db.session.query(
            Car.model,
            func.count(Car.id).label('count')
        ).filter(
            Car.brand.ilike(brand)
        ).group_by(Car.model).order_by(Car.model).all()
        
        return jsonify({
            'success': True,
            'brand': brand,
            'models': [{'name': model, 'count': count} for model, count in models]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/filters', methods=['GET'])
def get_filter_options():
    """Get all available filter options"""
    try:
        # Get unique values for each filter
        fuel_types = db.session.query(Car.fuel_type, func.count(Car.id)).group_by(Car.fuel_type).all()
        transmissions = db.session.query(Car.transmission, func.count(Car.id)).group_by(Car.transmission).all()
        body_types = db.session.query(Car.body_type, func.count(Car.id)).group_by(Car.body_type).all()
        locations = db.session.query(Car.location, func.count(Car.id)).group_by(Car.location).all()
        
        # Get year range
        year_stats = db.session.query(
            func.min(Car.year).label('min_year'),
            func.max(Car.year).label('max_year')
        ).first()
        
        # Get price range
        price_stats = db.session.query(
            func.min(Car.price).label('min_price'),
            func.max(Car.price).label('max_price')
        ).first()
        
        # Get mileage range
        mileage_stats = db.session.query(
            func.min(Car.mileage).label('min_mileage'),
            func.max(Car.mileage).label('max_mileage')
        ).first()
        
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
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# STATISTICS ENDPOINTS
# ============================================

@app.route('/api/stats', methods=['GET'])
def get_statistics():
    """Get overall market statistics"""
    try:
        total_cars = Car.query.count()
        
        # Price statistics
        price_stats = db.session.query(
            func.avg(Car.price).label('avg_price'),
            func.min(Car.price).label('min_price'),
            func.max(Car.price).label('max_price')
        ).first()
        
        # Top brands
        top_brands = db.session.query(
            Car.brand,
            func.count(Car.id).label('count')
        ).group_by(Car.brand).order_by(desc('count')).limit(10).all()
        
        # Fuel type distribution
        fuel_distribution = db.session.query(
            Car.fuel_type,
            func.count(Car.id).label('count')
        ).group_by(Car.fuel_type).all()
        
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
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats/brand/<brand>', methods=['GET'])
def get_brand_statistics(brand):
    """Get statistics for a specific brand"""
    try:
        # Brand statistics
        brand_cars = Car.query.filter(Car.brand.ilike(brand))
        total = brand_cars.count()
        
        if total == 0:
            return jsonify({
                'success': False,
                'error': f'No cars found for brand: {brand}'
            }), 404
        
        # Price statistics for brand
        price_stats = db.session.query(
            func.avg(Car.price).label('avg_price'),
            func.min(Car.price).label('min_price'),
            func.max(Car.price).label('max_price')
        ).filter(Car.brand.ilike(brand)).first()
        
        # Model distribution
        models = db.session.query(
            Car.model,
            func.count(Car.id).label('count'),
            func.avg(Car.price).label('avg_price')
        ).filter(
            Car.brand.ilike(brand)
        ).group_by(Car.model).order_by(desc('count')).all()
        
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
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# SCRAPING LOGS ENDPOINTS
# ============================================

@app.route('/api/scraping/logs', methods=['GET'])
def get_scraping_logs():
    """Get scraping execution logs"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
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
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# SEARCH ENDPOINT
# ============================================

@app.route('/api/search', methods=['GET'])
def search_cars():
    """Search cars by keyword"""
    try:
        query_text = request.args.get('q', '')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        if not query_text:
            return jsonify({
                'success': False,
                'error': 'Search query is required'
            }), 400
        
        # Search in brand, model, and location
        search_filter = db.or_(
            Car.brand.ilike(f'%{query_text}%'),
            Car.model.ilike(f'%{query_text}%'),
            Car.location.ilike(f'%{query_text}%')
        )
        
        pagination = Car.query.filter(search_filter).order_by(
            desc(Car.listing_date)
        ).paginate(page=page, per_page=per_page, error_out=False)
        
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
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Resource not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=os.getenv('FLASK_ENV') == 'development'
    )