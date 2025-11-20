# BPR Backend - Car Price Prediction API

[![Build and Deploy](https://github.com/igorcretu/BPR-BackEnd/actions/workflows/docker-build-deploy.yml/badge.svg)](https://github.com/igorcretu/BPR-BackEnd/actions)

> Bachelor Thesis Project - Group 26 | VIA University College

Backend API for the Car Price Prediction Platform for the Danish automotive market. Built with Flask, PostgreSQL, and Machine Learning.

## 🎯 Features

- **RESTful API** - Complete CRUD operations for car listings
- **Price Prediction** - ML-powered car price estimation
- **Advanced Filtering** - Search and filter by multiple parameters
- **Market Statistics** - Analyze trends and market data
- **Web Scraping Integration** - Automated data collection from Danish car sites
- **Docker Support** - Containerized deployment with PostgreSQL
- **CI/CD Pipeline** - Automated testing and deployment to Raspberry Pi 5
- **Asynchronous Queue** - Built-in prediction worker prevents overloads

## 🏗️ Tech Stack

- **Framework:** Flask 3.0
- **Database:** PostgreSQL 16
- **ORM:** SQLAlchemy
- **ML:** TensorFlow/Keras (placeholder ready)
- **Containerization:** Docker & Docker Compose
- **CI/CD:** GitHub Actions
- **Hosting:** Raspberry Pi 5

## 📋 API Endpoints

**Base URL (Development):** `http://localhost:5000`  
**Base URL (Production):** `https://api.yourdomain.com` (via Cloudflare Tunnel)

### Health & Info

- `GET /health` - Health check and service status

### Cars

- `GET /api/cars` - List all cars (with pagination & filters)
- `GET /api/cars/{id}` - Get specific car details
- `POST /api/cars` - Create new car listing
- `GET /api/search?q={query}` - Search cars by keyword

### Predictions

- `POST /api/predict` - Predict car price
- `POST /api/predict?mode=queue` - Enqueue a prediction job for deferred processing
- `GET /api/predict/jobs` - List queued jobs with statuses
- `GET /api/predict/jobs/{job_id}` - Check a specific job's status/result
- `GET /api/predictions` - Get prediction history

### Filters & Options

- `GET /api/brands` - Get all available brands
- `GET /api/models/{brand}` - Get models for a brand
- `GET /api/filters` - Get all available filter options

### Statistics

- `GET /api/stats` - Get overall market statistics
- `GET /api/stats/brand/{brand}` - Get statistics for specific brand

### Scraping

- `GET /api/scraping/logs` - Get web scraping execution logs

## 🚀 Quick Start (Local Development)

### Prerequisites

- Docker & Docker Compose
- Git

### Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/igorcretu/BPR-BackEnd.git
   cd BPR-BackEnd
   ```

2. **Create environment file**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start the services**

   ```bash
   docker compose up -d
   ```

4. **Check the logs**

   ```bash
   docker compose logs -f backend
   ```

5. **Test the API**

   ```bash
   curl http://localhost:5000/health
   ```

The API will be available at `http://localhost:5000`

The database is automatically initialized with sample data (30 cars) on first run.

## 🧵 Prediction Job Queue

High traffic from Cloudflare or the public frontend can now be absorbed by an internal job queue. Clients can opt-in (`POST /api/predict?mode=queue`) or let the API decide based on the backlog. Jobs are persisted in PostgreSQL, processed in FIFO order (respecting priority), and exposed through `/api/predict/jobs` endpoints for progress polling.

### Queue workflow

1. Submit a job via `POST /api/predict?mode=queue` (or let `mode=auto`/default handle it).
2. Receive a `job_id` plus `status_url` for polling.
3. Poll `GET /api/predict/jobs/{job_id}` until status becomes `completed` or `failed`.
4. A dedicated `prediction-worker` service pulls from the queue and runs the ML predictor.

Synchronous predictions still work (`mode=sync`), so existing integrations remain unaffected.

### Configuration knobs

- `PREDICTION_QUEUE_MODE` (`sync`, `queue`, `hybrid`, default `hybrid`).
- `PREDICTION_QUEUE_THRESHOLD` – backlog size that flips hybrid mode to queue (default `5`).
- `PREDICTION_QUEUE_PRIORITY_DEFAULT` – numeric priority assigned when clients do not provide one.
- `PREDICTION_QUEUE_POLL_INTERVAL` – worker sleep duration when idle (seconds, default `1.5`).
- `PREDICTION_QUEUE_MAX_ATTEMPTS` – worker retry limit before marking a job as failed (default `3`).

Set these in `.env` to tune behavior for production versus local development.

### Running the worker

- Docker Compose (`docker-compose.yml`, `docker-compose.dev.yml`, `docker-compose.prod.yml`) already defines a `prediction-worker` service; `docker compose up -d` will bring it online automatically.
- For ad-hoc debugging you can run the worker locally: `python -m app.worker` from the `API/` folder.
- Tail worker logs with `docker compose logs -f prediction-worker` to monitor throughput/errors.

## 📁 Project Structure

```text
BPR-BackEnd/
├── app/
│   ├── __init__.py
│   ├── main.py              # Main Flask application
│   ├── models.py            # Database models
│   └── ml/
│       ├── __init__.py
│       └── predictor.py     # ML prediction engine (placeholder)
├── .github/
│   └── workflows/
│       └── docker-build-deploy.yml  # CI/CD pipeline
├── models/                  # ML model files (gitignored)
├── logs/                    # Application logs (gitignored)
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Local development setup
├── docker-compose.prod.yml # Production setup (Raspberry Pi)
├── init.sql                # Database initialization script
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
└── README.md
```

## 🔧 API Usage Examples

### Get all cars with filters

```bash
curl "http://localhost:5000/api/cars?brand=Toyota&year_min=2020&page=1&per_page=10"
```

### Predict car price

```bash
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "brand": "Toyota",
    "model": "Corolla",
    "year": 2020,
    "mileage": 45000,
    "fuel_type": "Hybrid",
    "transmission": "Automatic",
    "body_type": "Sedan",
    "horsepower": 122
  }'
```

### Get market statistics

```bash
curl http://localhost:5000/api/stats
```

### Search for cars

```bash
curl "http://localhost:5000/api/search?q=Toyota"
```

## 🤖 Machine Learning Model

The ML predictor is currently a placeholder implementation in `app/ml/predictor.py`.

### To add your trained model

1. Train your model and save it:

   ```python
   model.save('models/car_price_model.h5')
   ```

2. Replace the mock implementation in `app/ml/predictor.py`:

   ```python
   def _load_model(self):
       from tensorflow import keras
       self.model = keras.models.load_model(self.model_path)
       self.model_loaded = True
   ```

3. Update the `predict()` method to use the actual model:

   ```python
   def predict(self, car_features):
       features_array = self._preprocess_features(car_features)
       predicted_price = self.model.predict(features_array)[0][0]
       # ... rest of implementation
   ```

## 🐳 Docker Commands

```bash
# Start services
docker compose up -d

# View logs
docker compose logs -f backend

# Stop services
docker compose down

# Rebuild and start
docker compose up -d --build

# Reset database (WARNING: deletes all data)
docker compose down -v
docker compose up -d

# Execute commands in container
docker compose exec backend python -c "from app.models import db; print('Database OK')"

# Access PostgreSQL directly
docker compose exec db psql -U bpr_user -d car_prediction
```

## 🔄 CI/CD Pipeline

The project uses GitHub Actions for continuous integration and deployment.

### Workflow

1. **Push to `main`** → Triggers CI/CD
2. **Build Docker image** → Creates container image
3. **Push to GitHub Container Registry** → Stores image at `ghcr.io/igorcretu/bpr-backend:latest`
4. **Deploy to Raspberry Pi** → SSH to Pi, pull new image, restart containers

### Setup GitHub Secrets

Add these secrets in your GitHub repository settings:

- `PI_HOST` - Raspberry Pi IP address
- `PI_USERNAME` - SSH username
- `PI_SSH_KEY` - SSH private key
- `PI_PORT` - SSH port (optional, default 22)

## 🍓 Raspberry Pi Deployment

### 📖 Complete Step-by-Step Guide

**Got your Raspberry Pi? Follow this guide:**

➡️ **[RASPBERRY_PI_DEPLOYMENT.md](RASPBERRY_PI_DEPLOYMENT.md)** - Complete deployment guide (20-30 minutes)

**Quick checklist version:**

➡️ **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Print and check off as you go

**Having issues?**

➡️ **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Solutions to common problems

### ⚡ Quick Summary

1. **SSH to your Pi:** `ssh pi@your-pi-ip`
2. **Install Docker:** One command
3. **Clone repo:** `git clone https://github.com/igorcretu/BPR-BackEnd.git`
4. **Create .env:** Copy from .env.example, add Cloudflare token
5. **Start everything:** `docker compose -f docker-compose.prod.yml --profile cloudflare up -d`
6. **Test:** `curl https://api.yourdomain.com/health`

**Done!** Your backend is live. ✅

### Cloudflare Tunnel Details (Recommended)

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Create project directory
mkdir -p ~/bpr-backend
cd ~/bpr-backend

# Clone repository
git clone https://github.com/igorcretu/BPR-BackEnd.git .

# Create .env file
cp .env.example .env
nano .env  # Edit with production values

# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u igorcretu --password-stdin

# Start services
docker compose -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f
```

### Cloudflare Tunnel Quick Setup

**Why Cloudflare Tunnel?**

- ✅ Expose your Pi to the internet securely (no port forwarding)
- ✅ Free HTTPS/SSL certificates
- ✅ DDoS protection
- ✅ Works behind NAT/firewall
- ✅ Connect your Netlify frontend to your Pi backend
- ✅ **Portable** - Same setup works on PC and Raspberry Pi

**🐳 Docker Method (Recommended - Easiest & Portable):**

1. **Create tunnel in Cloudflare Dashboard:**
   - Go to [Cloudflare Dashboard](https://one.dash.cloudflare.com/)
   - Access → Tunnels → Create a tunnel
   - Name: `bpr-backend`
   - Copy the tunnel token (starts with `eyJ...`)

2. **Configure the tunnel:**
   - Public Hostname:
     - Subdomain: `api`
     - Domain: `yourdomain.com`
     - Service: `HTTP` → `backend:5000`
   - Save tunnel

3. **Add token to `.env`:**

   ```bash
   echo "CLOUDFLARE_TUNNEL_TOKEN=your-token-here" >> .env
   ```

4. **Start with tunnel:**

   ```bash
   docker compose -f docker-compose.prod.yml --profile cloudflare up -d
   ```

5. **Test:**

   ```bash
   curl https://api.yourdomain.com/health
   ```

**That's it!** Your API is now accessible at `https://api.yourdomain.com`

**📖 Full Guide:** See [DOCKER_CLOUDFLARE_SETUP.md](DOCKER_CLOUDFLARE_SETUP.md) for complete Docker-based setup.

**Alternative:** See [CLOUDFLARE_TUNNEL_SETUP.md](CLOUDFLARE_TUNNEL_SETUP.md) for local installation method.

**After Cloudflare Tunnel setup:**

- Your API: `https://api.yourdomain.com`
- Update frontend `.env`: `VITE_API_URL=https://api.yourdomain.com/api`
- Same token works on PC and Raspberry Pi!

### Moving from PC to Raspberry Pi

The Docker method makes this **super easy**:

1. **On PC:** Test everything works
2. **On Raspberry Pi:**

   ```bash
   git clone https://github.com/igorcretu/BPR-BackEnd.git
   cd BPR-BackEnd
   cp .env.example .env
   # Add same CLOUDFLARE_TUNNEL_TOKEN as PC
   docker compose -f docker-compose.prod.yml --profile cloudflare up -d
   ```

3. **Done!** Same tunnel, same configuration, works immediately.

### Manual deployment

```bash
cd ~/bpr-backend
git pull origin main
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

## 🗄️ Database

### Schema

The database includes these main tables:

- **cars** - Car listings with all details
- **price_predictions** - ML prediction history
- **prediction_jobs** - Asynchronous queue entries and their lifecycle metadata
- **scraping_logs** - Web scraping execution logs
- **market_statistics** - Aggregated market data

### Sample Data

The `init.sql` script automatically creates:

- 30 sample cars (various brands and models)
- 20 sample predictions
- 4 scraping logs
- Market statistics

### Reset Database

```bash
docker compose down -v  # Deletes volumes
docker compose up -d    # Recreates with fresh data
```

## 🧪 Testing

Test the API endpoints:

```bash
# Health check
curl http://localhost:5000/health

# Get cars
curl http://localhost:5000/api/cars

# Get specific brand
curl http://localhost:5000/api/cars?brand=Toyota

# Predict price
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"brand":"Toyota","model":"Corolla","year":2020,"mileage":45000,"fuel_type":"Petrol","transmission":"Manual","body_type":"Sedan"}'
```

## 📊 Monitoring

View logs:

```bash
# Backend logs
docker compose logs -f backend

# Database logs
docker compose logs -f db

# All logs
docker compose logs -f
```

## 🛠️ Development

### Adding new endpoints

1. Add route in `app/main.py`
2. Update README with new endpoint
3. Test locally
4. Push to GitHub (CI/CD handles deployment)

### Adding new models

1. Define model in `app/models.py`
2. Add to database via migration or `init.sql`
3. Create API endpoints
4. Update documentation

## 👥 Team - Group 26

- **Igor Crețu** - Full-stack Development & ML Integration

**Supervisor:** [Supervisor Name]  
**Institution:** VIA University College  
**Academic Year:** 2024/2025

## 📚 Related Repositories

- [Frontend](https://github.com/igorcretu/BPR-FrontEnd) - React + TypeScript frontend
- [Documentation](https://github.com/BPR-Group26/BPR-Documentation) - Project documentation

## 📝 License

This project is part of a Bachelor thesis at VIA University College.

## 🆘 Troubleshooting

### Container won't start

```bash
# Check logs
docker compose logs backend

# Verify database connection
docker compose exec backend python -c "from app.models import db; db.session.execute(db.text('SELECT 1'))"
```

### Database connection errors

```bash
# Verify database is running
docker compose ps db

# Check database logs
docker compose logs db

# Verify credentials in .env
cat .env
```

### Port already in use

```bash
# Change port in docker-compose.yml or .env
# Or stop conflicting service:
sudo lsof -i :5000
sudo kill -9 <PID>
```

## 📞 Support

For issues or questions, please open an issue on GitHub or contact the team.
