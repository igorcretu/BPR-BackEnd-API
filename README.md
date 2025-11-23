# CarPredict Backend API

[![Build and Deploy to Raspberry Pi](https://github.com/igorcretu/BPR-BackEnd-API/actions/workflows/deploy.yml/badge.svg)](https://github.com/igorcretu/BPR-BackEnd-API/actions/workflows/deploy.yml)

A powerful Flask-based REST API providing car listings, advanced filtering, and AI-powered price predictions for the Danish automotive market. Features PostgreSQL database, asynchronous ML predictions, and Docker deployment.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)

## 🚀 Features

### Core API Functionality
- **RESTful API**: Well-structured endpoints following REST principles
- **Car Listings**: Comprehensive database of 28,384 Danish car listings from bilbasen.dk
- **Advanced Filtering**: Multi-parameter filtering (brand, fuel type, transmission, body type, price, year, mileage, etc.)
- **Full-Text Search**: Search across brand, model, variant, and title fields with PostgreSQL full-text search
- **Pagination**: Efficient data retrieval with customizable page sizes (default: 30 items/page)
- **Market Statistics**: Aggregate statistics for price distribution, brand popularity, fuel types, body types
- **ML Price Predictions**: XGBoost/CatBoost-powered price estimation with 85-90% R² score

### Database Management
- **PostgreSQL 16**: Robust relational database with full-text search and UUID support
- **Standardized Data**: 7 fuel types, 9 body types, 3 transmissions, 4 drive types
- **Direct SQL Operations**: psycopg2 for high-performance queries and bulk operations
- **Connection Pooling**: Optimized database connections with retry logic
- **Data Quality**: Clean, validated data with comprehensive field coverage (50+ attributes per car)

### Machine Learning
- **Multiple Models**: XGBoost, CatBoost, LightGBM, Random Forest trained on 28,000+ cars
- **High Accuracy**: 85-90% R² score, MAE ~30,000-40,000 DKK
- **Feature Engineering**: 25+ features including age, mileage_per_year, power_to_weight ratio
- **Categorical Encoding**: Label encoding for brands, fuel types, transmissions, body types, drive types
- **Confidence Scores**: Predictions include confidence percentage (70-95%) and price ranges
- **Smart Defaults**: Handles missing data (new cars with 0 mileage, electric cars with automatic transmission)
- **Fallback Heuristics**: Rule-based predictions when ML model unavailable

### DevOps & Deployment
- **Docker Support**: Containerized deployment with multi-stage builds
- **Docker Compose**: Production and development configurations
- **Cloudflare Tunnels**: Secure public HTTPS access (https://test.bachelorproject26.site)
- **GitHub Actions**: CI/CD pipeline for automated deployment to Raspberry Pi
- **Health Checks**: API health monitoring at `/api/health` endpoint
- **Comprehensive Logging**: Rotating file logs with request ID tracking
- **Error Handling**: Consistent error responses with detailed messages
- **CORS**: Configured for frontend domain access

## 🛠️ Technology Stack

### Backend Framework
- **Flask 3.0.3** - Lightweight WSGI web framework
- **Flask-CORS** - Cross-Origin Resource Sharing support
- **Werkzeug** - WSGI utilities and security

### Database
- **PostgreSQL 16** - Advanced relational database
- **SQLAlchemy 2.0** - SQL toolkit and ORM
- **psycopg2-binary** - PostgreSQL adapter

### Machine Learning
- **TensorFlow 2.17** - Deep learning framework
- **Keras** - High-level neural networks API
- **NumPy** - Numerical computing
- **Pandas** - Data manipulation and analysis
- **scikit-learn** - Machine learning utilities

### Data Processing
- **BeautifulSoup4** - Web scraping (for data collection)
- **Requests** - HTTP library
- **python-dotenv** - Environment variable management

### Development & Deployment
- **Docker & Docker Compose** - Containerization
- **Gunicorn** - WSGI HTTP server
- **Cloudflared** - Tunnel service for secure access

## 📁 Project Structure

```
BackEnd/API/
├── app/
│   ├── __init__.py           # Flask app initialization
│   ├── main.py               # Main application entry point
│   ├── models.py             # SQLAlchemy database models
│   ├── worker.py             # Background worker for ML predictions
│   ├── ml/
│   │   ├── __init__.py
│   │   └── predictor.py      # ML prediction logic
│   ├── routes/
│   │   └── [route files]     # API endpoint handlers
│   ├── services/
│   │   ├── __init__.py
│   │   └── prediction_queue.py # Async prediction queue
│   └── utils/
│       └── request_validation.py # Input validation utilities
├── models/
│   └── [trained ML models]   # Saved TensorFlow models
├── logs/                      # Application logs
├── scripts/
│   └── setup-cloudflare-tunnel.sh # Cloudflare setup script
├── docker-compose.yml         # Production deployment
├── docker-compose.dev.yml     # Development environment
├── docker-compose.prod.yml    # Production configuration
├── Dockerfile                 # Container image definition
├── init.sql                   # Database initialization
├── requirements.txt           # Python dependencies
├── start-dev.sh              # Development startup script
└── README.md                  # This file
```

## 🚦 Getting Started

### Prerequisites
- **Python 3.11** or higher
- **PostgreSQL 16** database
- **Docker & Docker Compose** (for containerized deployment)
- **pip** package manager

### Local Development Setup

#### 1. Clone the Repository
```bash
git clone <repository-url>
cd BackEnd/API
```

#### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Configure Environment Variables
Create a `.env` file in the `API/` directory:

```env
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/carpredict
DB_HOST=localhost
DB_PORT=5432
DB_NAME=carpredict
DB_USER=your_username
DB_PASSWORD=your_password

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-here

# CORS Configuration
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# ML Model Configuration
MODEL_PATH=models/car_price_model.h5
SCALER_PATH=models/scaler.pkl
ENCODER_PATH=models/encoder.pkl

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

#### 5. Initialize Database
```bash
# Create PostgreSQL database
createdb carpredict

# Run initialization script
psql -d carpredict -f init.sql
```

#### 6. Start Development Server
```bash
python app/main.py
```

The API will be available at `http://localhost:8000`

### Docker Deployment

#### Development Environment
```bash
docker-compose -f docker-compose.dev.yml up --build
```

#### Production Environment
```bash
docker-compose -f docker-compose.prod.yml up -d
```

#### Full Stack (with Database)
```bash
docker-compose up -d
```

## 📡 API Endpoints

### Car Listings

#### Get All Cars (Paginated)
```http
GET /api/cars
```

**Query Parameters:**
| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `page` | integer | Page number | 1 |
| `per_page` | integer | Items per page | 30 |
| `q` | string | Search query | - |
| `brand` | string | Filter by brand | - |
| `fuel_type` | string | Filter by fuel type | - |
| `transmission` | string | Filter by transmission | - |
| `body_type` | string | Filter by body type | - |
| `year_min` | integer | Minimum year | - |
| `year_max` | integer | Maximum year | - |
| `price_min` | integer | Minimum price (DKK) | - |
| `price_max` | integer | Maximum price (DKK) | - |

**Response:**
```json
{
  "cars": [
    {
      "id": "123",
      "brand": "Toyota",
      "model": "Camry",
      "year": 2020,
      "price": 250000,
      "mileage": 45000,
      "fuel_type": "Benzin",
      "transmission": "Automatisk",
      ...
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 30,
    "total": 30000,
    "pages": 1000
  }
}
```

#### Get Car by ID
```http
GET /api/cars/:id
```

**Response:**
```json
{
  "car": {
    "id": "123",
    "brand": "Toyota",
    "model": "Camry",
    "variant": "2.5 Hybrid",
    "year": 2020,
    "price": 250000,
    "mileage": 45000,
    "fuel_type": "Benzin",
    "transmission": "Automatisk",
    "body_type": "Sedan",
    "horsepower": 218,
    "engine_size": 2.5,
    "doors": 4,
    "seats": 5,
    "color": "Sort",
    ...
  }
}
```

### Brands

#### Get All Brands
```http
GET /api/brands
```

**Response:**
```json
{
  "brands": [
    {"name": "Toyota", "count": 2500},
    {"name": "Volkswagen", "count": 3200},
    {"name": "BMW", "count": 1800},
    ...
  ]
}
```

### Filters

#### Get Filter Options
```http
GET /api/filters
```

**Response:**
```json
{
  "filters": {
    "fuel_types": [
      {"value": "Benzin", "count": 15000},
      {"value": "Diesel", "count": 10000},
      {"value": "El", "count": 3000},
      ...
    ],
    "transmissions": [
      {"value": "Automatisk", "count": 18000},
      {"value": "Manuel", "count": 12000}
    ],
    "body_types": [
      {"value": "SUV", "count": 8000},
      {"value": "Sedan", "count": 6000},
      ...
    ]
  }
}
```

### Price Prediction

#### Predict Car Price
```http
POST /api/predict
```

**Request Body:**
```json
{
  "brand": "Toyota",
  "model": "Camry",
  "year": 2020,
  "mileage": 45000,
  "fuel_type": "Benzin",
  "transmission": "Automatisk",
  "body_type": "Sedan",
  "horsepower": 218,
  "engine_size": 2.5,
  "doors": 4,
  "color": "Sort",
  "drive_type": "Forhjulstræk"
}
```

**Response:**
```json
{
  "predicted_price": 248500,
  "confidence": 92.5,
  "price_range": {
    "min": 235000,
    "max": 262000
  },
  "model_version": "v1.2.0",
  "prediction_id": "pred_123456"
}
```

### Health Check

#### API Health Status
```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "ml_model": "loaded",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

## 🗄️ Database Schema

### Cars Table
```sql
CREATE TABLE cars (
    id VARCHAR PRIMARY KEY,
    url TEXT,
    brand VARCHAR(100),
    model VARCHAR(100),
    variant VARCHAR(255),
    title TEXT,
    description TEXT,
    price INTEGER,
    new_price INTEGER,
    model_year INTEGER,
    year INTEGER,
    first_registration VARCHAR(50),
    production_date VARCHAR(50),
    mileage INTEGER,
    fuel_type VARCHAR(50),
    transmission VARCHAR(50),
    gear_count INTEGER,
    cylinders INTEGER,
    horsepower INTEGER,
    engine_size DECIMAL(4,2),
    torque_nm INTEGER,
    acceleration DECIMAL(4,2),
    top_speed INTEGER,
    range_km INTEGER,
    battery_capacity DECIMAL(5,2),
    energy_consumption INTEGER,
    home_charging_ac VARCHAR(50),
    fast_charging_dc VARCHAR(50),
    charging_time_dc VARCHAR(50),
    fuel_consumption VARCHAR(50),
    co2_emission VARCHAR(50),
    euro_norm VARCHAR(20),
    tank_capacity INTEGER,
    body_type VARCHAR(50),
    doors INTEGER,
    seats INTEGER,
    color VARCHAR(50),
    weight INTEGER,
    width INTEGER,
    length INTEGER,
    height INTEGER,
    trunk_size INTEGER,
    load_capacity INTEGER,
    towing_capacity INTEGER,
    max_towing_weight INTEGER,
    drive_type VARCHAR(50),
    abs_brakes BOOLEAN,
    esp BOOLEAN,
    airbags INTEGER,
    category VARCHAR(100),
    equipment TEXT,
    periodic_tax VARCHAR(50),
    location VARCHAR(100),
    dealer_name VARCHAR(255),
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cars_brand ON cars(brand);
CREATE INDEX idx_cars_model ON cars(model);
CREATE INDEX idx_cars_year ON cars(year);
CREATE INDEX idx_cars_price ON cars(price);
CREATE INDEX idx_cars_fuel_type ON cars(fuel_type);
CREATE INDEX idx_cars_body_type ON cars(body_type);
```

### Price Predictions Table
```sql
CREATE TABLE price_predictions (
    id SERIAL PRIMARY KEY,
    car_id VARCHAR REFERENCES cars(id),
    predicted_price INTEGER,
    actual_price INTEGER,
    confidence DECIMAL(5,2),
    features JSONB,
    model_version VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🤖 Machine Learning Pipeline

### Model Architecture
```python
# Sequential neural network
model = Sequential([
    Dense(128, activation='relu', input_dim=n_features),
    Dropout(0.3),
    Dense(64, activation='relu'),
    Dropout(0.2),
    Dense(32, activation='relu'),
    Dense(1)  # Price prediction
])
```

### Training Data
- **Dataset Size**: 30,000+ car listings
- **Features**: 20+ numerical and categorical features
- **Target**: Car price in DKK
- **Train/Test Split**: 80/20
- **Validation**: Cross-validation with 5 folds

### Feature Engineering
- **Numerical Features**: Mileage, year, horsepower, engine size, etc.
- **Categorical Encoding**: One-hot encoding for brand, fuel type, transmission
- **Scaling**: StandardScaler for numerical features
- **Missing Values**: Median imputation for numerical, mode for categorical

### Model Performance
- **RMSE**: ~25,000 DKK
- **MAE**: ~18,000 DKK
- **R² Score**: 0.87
- **Training Time**: ~30 minutes on CPU

## 🔧 Configuration

### Flask Application (`app/main.py`)
```python
from flask import Flask
from flask_cors import CORS
import logging

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app, origins=os.getenv('CORS_ORIGINS', '*').split(','))
```

### Database Connection
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
Session = sessionmaker(bind=engine)
```

### Logging Configuration
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.RotatingFileHandler('logs/error.log', maxBytes=10485760, backupCount=5),
        logging.StreamHandler()
    ]
)
```

## 🐳 Docker Configuration

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "app.main:app"]
```

### Docker Compose (Production)
```yaml
version: '3.8'

services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: carpredict
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/carpredict
    depends_on:
      - db
    volumes:
      - ./models:/app/models
      - ./logs:/app/logs

volumes:
  postgres_data:
```

## 🌐 Cloudflare Tunnel Setup

### Installation
```bash
# Run setup script
bash scripts/setup-cloudflare-tunnel.sh
```

### Configuration (`cloudflared-config.yml`)
```yaml
tunnel: <tunnel-id>
credentials-file: /root/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: api.carpredict.com
    service: http://localhost:8000
  - service: http_status:404
```

### Start Tunnel
```bash
cloudflared tunnel run <tunnel-name>
```

## 📊 Monitoring & Logging

### Log Files
- `logs/app.log` - General application logs
- `logs/error.log` - Error logs with rotation
- `logs/access.log` - HTTP access logs

### Log Levels
- **DEBUG**: Detailed information for debugging
- **INFO**: General informational messages
- **WARNING**: Warning messages
- **ERROR**: Error messages
- **CRITICAL**: Critical issues

### Health Monitoring
```bash
# Check API health
curl http://localhost:8000/api/health

# Check database connection
curl http://localhost:8000/api/health/db

# Check ML model status
curl http://localhost:8000/api/health/ml
```

## 🧪 Testing

### Run Unit Tests
```bash
pytest tests/
```

### API Testing with curl
```bash
# Get cars
curl http://localhost:8000/api/cars?page=1&per_page=10

# Get specific car
curl http://localhost:8000/api/cars/123

# Price prediction
curl -X POST http://localhost:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"brand":"Toyota","model":"Camry","year":2020,"mileage":45000}'
```

## 🔒 Security

### Environment Variables
- Never commit `.env` files
- Use strong database passwords
- Rotate SECRET_KEY regularly

### CORS Configuration
- Restrict origins in production
- Use environment variables for allowed origins

### Input Validation
- All inputs validated before processing
- SQL injection prevention via SQLAlchemy ORM
- XSS protection on string inputs

## 🚀 Performance Optimization

### Database Optimization
- Indexed columns for faster queries
- Connection pooling
- Query result caching

### API Optimization
- Pagination for large datasets
- Gzip compression
- Response caching headers

### ML Prediction Optimization
- Model loaded once at startup
- Batch predictions support
- Asynchronous processing queue

## 📝 Development Guidelines

### Code Style
- Follow PEP 8 style guide
- Use type hints
- Document functions with docstrings

### Git Workflow
1. Create feature branch
2. Make changes with descriptive commits
3. Test thoroughly
4. Create pull request

### Adding New Endpoints
1. Define route in `app/routes/`
2. Add validation in `app/utils/`
3. Update this README
4. Add tests

## 📊 Data Standardization

### Categorical Values
The database uses standardized English labels for consistent filtering and predictions:

**Fuel Types (7 categories):**
- Electricity (11,301 cars)
- Petrol (11,004 cars)
- Diesel (3,900 cars)
- Plug-in Hybrid - Petrol (1,588 cars)
- Hybrid - Petrol (449 cars)
- Plug-in Hybrid - Diesel (141 cars)
- Hybrid - Diesel (1 car)

**Body Types (9 categories):**
- Hatchback (10,366 cars)
- SUV (10,297 cars)
- Station Wagon (3,381 cars)
- Sedan (1,514 cars)
- Van (1,406 cars)
- Cabriolet (855 cars)
- Coupe (448 cars)
- Pickup (4 cars)

**Transmissions (3 categories):**
- Automatic
- Manual
- Semi-Automatic

**Drive Types (4 categories):**
- Front-Wheel Drive
- Rear-Wheel Drive
- All-Wheel Drive
- 4WD

### Data Quality Rules
1. **Electric Cars**: All electric vehicles (fuel_type='Electricity') have transmission='Automatic'
2. **New Cars**: Cars with null mileage are set to 0 for prediction
3. **Missing Values**: Smart defaults applied for optional fields (horsepower, doors, etc.)
4. **Mapping**: Predictor.py maps database values to ML model format (e.g., 'Electricity' → 'Electric')

## 🐛 Common Issues & Solutions

### Issue: 400 Bad Request on /api/predict
**Solution**: Check predictor.py mappings match database standardized values

### Issue: Database shows wrong fuel type count
**Solution**: Run data cleanup script to fix variant values (Electric → Electricity)

### Issue: Prediction fails for new cars
**Solution**: Mileage=0 logic implemented in main.py for null mileage values

### Issue: Database connection failed
**Solution**: Check DATABASE_URL, PostgreSQL service, and SSH tunnel (port 5432)

### Issue: ML model not loading
**Solution**: Verify models/ directory contains .pkl files and model_metadata.json

### Issue: CORS errors
**Solution**: Update CORS_ORIGINS environment variable with frontend domain

### Issue: Out of memory on Raspberry Pi
**Solution**: Reduce worker count or upgrade to 8GB RAM model

## 🔗 Related Repositories

- **Frontend**: [BPR-FrontEnd](https://github.com/igorcretu/BPR-FrontEnd) - React TypeScript web application
- **ML Model**: [BPR-BackEnd-ML-Model](https://github.com/igorcretu/BPR-BackEnd-ML-Model) - Data scraping, cleaning, and model training

## 📚 Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [PostgreSQL Manual](https://www.postgresql.org/docs/)
- [XGBoost Documentation](https://xgboost.readthedocs.io/)
- [Docker Docs](https://docs.docker.com/)
- [Cloudflare Tunnels](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)

## 👥 Contributing

This is an academic project for VIA University College. External contributions are not accepted.

## 📄 License

This project is for educational purposes only. Not licensed for commercial use.

## 🎓 Academic Context

**Institution**: VIA University College, Denmark  
**Course**: Bachelor's Thesis Project  
**Team**: Group 26  
**Year**: 2024-2025  
**Deployed**: Raspberry Pi 5 (4GB RAM)  
**Purpose**: Demonstration of full-stack development, ML integration, and DevOps practices

## 📧 Contact

For academic inquiries, please contact VIA University College.

---

**Disclaimer**: This API is created for educational purposes and provides car price predictions as educational estimates only. All data is sourced from public Danish car marketplaces for research purposes.
