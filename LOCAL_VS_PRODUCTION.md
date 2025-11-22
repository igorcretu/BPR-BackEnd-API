# Local Testing vs Production Deployment

## ✅ SAFE - These files are LOCAL ONLY (Won't affect production)

### Database
- `instance/car_prediction.db` - SQLite database for local testing
- Production uses **PostgreSQL** in Docker container

### Test Files & Scripts
- `run_server.py` - Local development server
- `start_server.bat` - Windows launcher script
- `add_sample_data.py` - Generates 200 sample cars for testing
- `init_db.py` - Initializes local SQLite database
- `test_market_stats.py` - Manual test script

### Coverage & Testing
- `htmlcov/` - HTML coverage reports
- `.coverage` - Coverage data file
- `coverage.xml` - Coverage XML report
- `.pytest_cache/` - Pytest cache

### Logs
- `logs/*.log` - Local development logs

---

## 🚀 PRODUCTION DEPLOYMENT (Raspberry Pi)

### Configuration
- Uses: `docker-compose.prod.yml`
- Database: **PostgreSQL** (NOT SQLite)
- Image: `ghcr.io/igorcretu/bpr-backend:latest`
- Server: Waitress (defined in Dockerfile)
- Access: Cloudflare Tunnel (not direct IP)

### Environment Variables (Production)
```bash
DATABASE_URL=postgresql://user:pass@db:5432/car_prediction
FLASK_ENV=production
SECRET_KEY=<strong-production-secret>
POSTGRES_PASSWORD=<strong-db-password>
```

---

## 🛡️ Protection Mechanisms

### 1. `.gitignore`
Excludes local test files from git commits:
- *.db, *.sqlite, instance/
- run_server.py, start_server.bat
- add_sample_data.py, init_db.py
- htmlcov/, .coverage, coverage.xml
- __pycache__/, *.pyc

### 2. `.dockerignore`
Excludes files from Docker image:
- *.db, *.sqlite
- .coverage, htmlcov/
- logs/*.log
- README.md

### 3. Separate Compose Files
- **Dev**: `docker-compose.yml` or `docker-compose.dev.yml`
- **Prod**: `docker-compose.prod.yml` (only this is used on Pi)

---

## 📊 Comparison Table

| Aspect | Local Testing | Production (Pi) |
|--------|---------------|-----------------|
| Database | SQLite | PostgreSQL |
| Server | run_server.py | Docker + Waitress |
| Data | 200 sample cars | Real data |
| Access | 127.0.0.1:5000 | Cloudflare Tunnel |
| OS | Windows | Linux (Raspberry Pi OS) |
| Deploy Method | Direct Python | docker-compose |
| Config File | None / .env.local | docker-compose.prod.yml |

---

## 🎯 Deployment Workflow

### Local Testing (What you do now)
```bash
# Start server
python run_server.py

# Run tests
pytest tests/ --cov=app

# Test endpoints
curl http://127.0.0.1:5000/health
```

### Production Deploy (On Raspberry Pi)
```bash
# Pull latest code
git pull origin main

# Build & start containers
docker-compose -f docker-compose.prod.yml up -d --build

# Check status
docker ps
docker logs bpr-flask
```

---

## ✅ VERIFICATION CHECKLIST

Before pushing to production:

- [ ] `.gitignore` created and committed
- [ ] Local test files (*.db, run_server.py, etc.) not tracked by git
- [ ] All tests passing (212/212)
- [ ] Coverage reports generated locally only
- [ ] `docker-compose.prod.yml` configured correctly
- [ ] Production secrets in `.env` file (not committed)
- [ ] ML model files deployed separately to Pi

---

## 💡 Key Takeaway

**Your local testing setup is completely isolated from production!**

- Local changes to SQLite database stay local
- Test scripts are git-ignored
- Production pulls clean code from GitHub
- Production uses its own PostgreSQL database
- Docker build excludes test files via .dockerignore

**Deploy with confidence! 🚀**
