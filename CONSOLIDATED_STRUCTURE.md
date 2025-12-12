# BPR Backend API - Consolidated Structure

## 📁 Project Structure

```
BPR-BackEnd-API/
├── app/
│   ├── main.py                  # Flask API entry point
│   ├── models.py                # SQLAlchemy database models
│   ├── worker.py                # Background prediction worker
│   ├── ml/
│   │   ├── predictor.py         # Car price prediction logic
│   │   ├── ml_utils.py          # ML utilities (TargetEncoder, PyTorch loaders)
│   │   └── training/
│   │       ├── __init__.py
│   │       └── train_models.py  # Model training orchestration (10 models)
│   ├── scraping/
│   │   ├── __init__.py
│   │   ├── auto_scraper.py      # Legacy full scraper
│   │   └── bilbasen_incremental.py  # Incremental scraper
│   ├── services/
│   │   └── prediction_queue.py  # Queue management
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── import_csv_to_db.py  # CSV data import utility
│   │   ├── download_missing_images.py  # Image downloader
│   │   └── fix_image_flags.py   # Image flag repair utility
│   └── models/                  # Trained ML models directory
│       ├── *.pt                 # PyTorch models (LSTM, GRU)
│       ├── *.pkl                # Scikit-learn models (XGBoost, CatBoost, etc.)
│       └── *.json               # Model metadata
├── data/
│   └── bilbasen_scrape/
│       ├── images/              # Scraped car images (symlinked)
│       ├── *.csv                # Scraped data
│       ├── *.log                # Scraper logs
│       └── *_checkpoint.json    # Scraping checkpoints
├── logs/                        # Application logs
├── migrations/                  # Database migrations
├── tests/                       # Unit and integration tests
├── docker-compose.prod.yml      # Production Docker configuration
├── docker-compose.yml           # Development Docker configuration
├── Dockerfile
├── requirements.txt
└── README.md
```

## 🎯 Key Changes from Previous Structure

### ✅ **Consolidated Structure**
- **Before**: ML scripts scattered in separate `BPR-BackEnd-ML-Model` folder
- **After**: Everything under `BPR-BackEnd-API` with logical organization

### ✅ **Simplified Docker Mounts**
- **Before**: Complex mounts to `../BPR-BackEnd-ML-Model`
- **After**: Single mount of `./app` and `./data`

### ✅ **Better Organization**
- **Training**: `app/ml/training/`
- **Scraping**: `app/scraping/`
- **Utilities**: `app/utils/`
- **Data**: `data/bilbasen_scrape/`

### ✅ **Updated Paths**
All references updated:
- `/app/ML_Model/train_models.py` → `/app/app/ml/training/train_models.py`
- `/app/ML_Model/auto_scraper.py` → `/app/app/scraping/auto_scraper.py`
- `/app/ML_Model/bilbasen_incremental.py` → `/app/app/scraping/bilbasen_incremental.py`
- `/app/data` → `/app/data/bilbasen_scrape/`

## 🚀 Quick Start

### Development

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f backend

# Run training
docker exec bpr-flask python -m app.ml.training.train_models

# Run scraper
docker exec bpr-flask python -m app.scraping.bilbasen_incremental --mode incremental
```

### Production

```bash
# Start production services
docker compose -f docker-compose.prod.yml up -d

# Check health
curl http://localhost:5000/health

# Trigger training via API
curl -X POST http://localhost:5000/api/trigger-training
```

## 📊 ML Models

The system trains 10 different models:

### Tree-Based Models
1. **XGBoost** - Gradient boosting (usually best performer)
2. **CatBoost** - Categorical-aware boosting
3. **LightGBM** - Fast gradient boosting
4. **RandomForest** - Ensemble decision trees
5. **HistGradientBoosting** - Native sklearn gradient boosting

### Linear Models
6. **Ridge Regression** - L2 regularization
7. **Lasso Regression** - L1 regularization
8. **ElasticNet** - Combined L1+L2 regularization

### Deep Learning Models
9. **LSTM** - Long Short-Term Memory network
10. **GRU** - Gated Recurrent Unit network

All models use:
- **67 engineered features** (numeric, binary, encoded, one-hot)
- **Target encoding** for high-cardinality categories (brand, model)
- **Cross-validation** for robust evaluation
- **Segmented metrics** by price range, fuel type, year

## 🔧 Utilities

### Import CSV Data
```bash
python -m app.utils.import_csv_to_db
```

### Download Missing Images
```bash
python -m app.utils.download_missing_images
```

### Fix Image Flags
```bash
python -m app.utils.fix_image_flags
```

## 🗄️ Database Models

- `cars` - Car listings
- `price_predictions` - Prediction history
- `ml_models` - Model registry
- `scraping_logs` - Scraping statistics
- `market_statistics` - Market analytics
- `prediction_jobs` - Async prediction queue

## 🧪 Testing

```bash
# Run all tests
docker exec bpr-flask pytest

# Run with coverage
docker exec bpr-flask pytest --cov=app tests/

# Run specific test file
docker exec bpr-flask pytest tests/test_trigger_endpoints.py
```

## 📝 API Endpoints

### Prediction
- `POST /api/predict` - Get car price prediction
- `GET /api/predictions/<id>` - Get prediction by ID

### Training
- `POST /api/trigger-training` - Start model training
- `GET /api/training/status` - Check training status

### Scraping
- `POST /api/trigger-scraping` - Start scraping job
- `GET /api/scraping/status` - Check scraper status

### Health & Info
- `GET /health` - Health check
- `GET /api/system/info` - System information
- `GET /api/models` - List all ML models

## 🐳 Docker Configuration

### Volume Mounts

**Development** (`docker-compose.yml`):
```yaml
volumes:
  - ./app:/app/app           # Live code reload
  - ./logs:/app/logs         # Persistent logs
  - ./data:/app/data         # Scraping data & images
```

**Production** (`docker-compose.prod.yml`):
```yaml
volumes:
  - ./app:/app/app           # Application code
  - ./logs:/app/logs         # Persistent logs
  - ./data:/app/data         # Scraping data & images
```

### Environment Variables

Required in `.env`:
```env
POSTGRES_PASSWORD=your_secure_password
SECRET_KEY=your_secret_key
ALLOWED_ORIGINS=https://yourdomain.com
```

## 🔍 Troubleshooting

### Models Not Found
```bash
# Check model directory
docker exec bpr-flask ls -la /app/app/models/

# Check database registry
docker exec bpr-flask python -c "from app.models import MLModel, db; from app.main import app; app.app_context().push(); print(MLModel.query.all())"
```

### Scraper Issues
```bash
# Check scraper logs
docker exec bpr-flask cat /app/data/bilbasen_scrape/incremental_scraper.log

# Test database connection
docker exec bpr-flask python -c "import psycopg2; import os; conn = psycopg2.connect(os.getenv('DATABASE_URL')); print('✅ Connected')"
```

### Training Issues
```bash
# Check training logs
docker exec bpr-flask cat /app/logs/train_models.log

# Run training with verbose output
docker exec bpr-flask python -m app.ml.training.train_models --verbose
```

## 📚 Migration from Old Structure

If you're migrating from the old `BPR-BackEnd-ML-Model` structure:

1. ✅ **Files have been copied** to new locations
2. ✅ **Paths updated** in code and configs
3. ✅ **Docker mounts simplified** - no more `../BPR-BackEnd-ML-Model`
4. ✅ **Data directory created** with symlink to images
5. ⚠️ **Old structure kept** for reference (can be deleted later)

### What Was Removed
- `linear_models.py`, `rnn_models.py` - Functionality merged into `train_models.py`
- Jupyter notebooks - Development artifacts
- `models/` folder in ML-Model - Was empty

### What Was Kept
- All functional scripts (training, scraping, utilities)
- All trained models
- All scraped data and images
- All configuration files

## 🎓 Best Practices

1. **Always use API for training/scraping** - Don't run scripts directly in production
2. **Monitor logs** - Check `/app/logs/` for issues
3. **Backup models** - Models in `/app/app/models/` are valuable
4. **Use incremental scraping** - Full scrapes are resource-intensive
5. **Keep data directory clean** - Old logs and checkpoints can accumulate

## 🔗 Related Documentation

- [Deployment Guide](DEPLOYMENT_SETUP.md)
- [Model Loading Fix](MODEL_LOADING_FIX.md)
- [Phase Completion Notes](PHASE*.md)

---

**Last Updated**: December 2024  
**Version**: 4.0 (Consolidated Structure)
