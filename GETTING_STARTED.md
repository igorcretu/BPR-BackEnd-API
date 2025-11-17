# 🚀 Getting Started - Complete Setup Guide

Welcome to your BPR Backend! This guide will get you up and running in 10 minutes.

## 📦 What You Got

Your backend is **completely containerized** and **portable**:

```
┌─────────────────────────────────────────────────┐
│  Your Complete Backend Stack                    │
├─────────────────────────────────────────────────┤
│  🐳 PostgreSQL Container (Database)             │
│  🐳 Flask Container (API)                       │
│  🐳 Cloudflare Tunnel Container (Public Access) │
└─────────────────────────────────────────────────┘
```

**One configuration works everywhere:** PC → Raspberry Pi → Any Linux machine!

---

## ⚡ Super Quick Start (PC)

### 1. Extract & Navigate

```bash
unzip BPR-BackEnd.zip
cd BPR-BackEnd
```

### 2. Setup Environment

```bash
cp .env.example .env
# Edit .env with your preferred text editor
```

**Minimum required in .env:**
```bash
POSTGRES_PASSWORD=your-strong-password
SECRET_KEY=your-secret-key
```

### 3. Start Backend (Local Only)

```bash
# Easy way:
./start-dev.sh

# Or manually:
docker compose -f docker-compose.dev.yml up -d
```

### 4. Test It

```bash
curl http://localhost:5000/health
curl http://localhost:5000/api/cars
```

**✅ Done!** Backend is running locally.

---

## 🌐 Add Public Access (Optional but Awesome)

Want to access your backend from anywhere? Use Cloudflare Tunnel!

### Step 1: Get Tunnel Token (2 minutes)

1. Go to: **https://one.dash.cloudflare.com/**
2. Click: **Access → Tunnels → Create a tunnel**
3. Name it: **bpr-backend**
4. Click: **Save tunnel**
5. You'll see a token like: `eyJhXXXXXXXXXXXX...`
6. **COPY THIS TOKEN!**

### Step 2: Configure Public Hostname (1 minute)

Still in the Cloudflare dashboard:

1. **Public Hostname** section:
   - Subdomain: `api`
   - Domain: `yourdomain.com` (select your domain)
   - Path: (leave empty)
   - Service Type: `HTTP`
   - URL: `backend:5000`

2. Click **Save tunnel**

### Step 3: Add Token to Your Project (30 seconds)

```bash
# Add to your .env file
echo "CLOUDFLARE_TUNNEL_TOKEN=eyJhXXXXXXXXXXXX..." >> .env
```

### Step 4: Start with Tunnel (30 seconds)

```bash
# Development (PC)
docker compose -f docker-compose.dev.yml --profile cloudflare up -d

# Or production (Raspberry Pi later)
docker compose -f docker-compose.prod.yml --profile cloudflare up -d
```

### Step 5: Test Public Access

```bash
# From anywhere in the world!
curl https://api.yourdomain.com/health
curl https://api.yourdomain.com/api/cars
```

**🎉 Your API is now public and secure!**

---

## 📁 Project Overview

### Important Files

```
BPR-BackEnd/
├── .env                          # Your secrets (DON'T commit!)
├── docker-compose.dev.yml        # Development setup
├── docker-compose.prod.yml       # Production setup (Raspberry Pi)
├── init.sql                      # Database with 30 sample cars
├── app/
│   ├── main.py                   # API endpoints
│   ├── models.py                 # Database models
│   └── ml/predictor.py          # ML model (placeholder)
└── Documentation/
    ├── README.md                 # Main documentation
    ├── DOCKER_CLOUDFLARE_SETUP.md    # Detailed Cloudflare guide
    ├── FRONTEND_INTEGRATION.md   # Connect to React frontend
    ├── API_DOCUMENTATION.md      # All API endpoints
    └── QUICK_REFERENCE.md        # Command cheat sheet
```

### File Purposes

- **`.env`** - All your configuration (passwords, tokens)
- **`docker-compose.dev.yml`** - For development on your PC
- **`docker-compose.prod.yml`** - For production on Raspberry Pi
- **`init.sql`** - Creates database with sample data automatically
- **`start-dev.sh`** - Easy start script for development

---

## 🔄 Development Workflow

### Daily Development (PC)

```bash
# Start
./start-dev.sh

# Make changes to code in app/
# Changes auto-reload (hot reload enabled)

# View logs
docker compose -f docker-compose.dev.yml logs -f backend

# Stop
docker compose -f docker-compose.dev.yml down
```

### Test Your Changes

```bash
# Test locally
curl http://localhost:5000/api/cars

# Test through tunnel (if enabled)
curl https://api.yourdomain.com/api/cars
```

### Push to GitHub

```bash
git add .
git commit -m "Your changes"
git push origin main

# CI/CD will automatically deploy to Raspberry Pi!
```

---

## 🍓 Deploy to Raspberry Pi

When you get your Raspberry Pi 5:

### First Time Setup

```bash
# SSH to your Pi
ssh pi@your-pi-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Clone your repo
git clone https://github.com/igorcretu/BPR-BackEnd.git
cd BPR-BackEnd

# Create .env with SAME token as your PC
nano .env
```

Add to `.env`:
```bash
POSTGRES_PASSWORD=your-strong-password
SECRET_KEY=your-secret-key
ALLOWED_ORIGINS=https://your-site.netlify.app
CLOUDFLARE_TUNNEL_TOKEN=eyJhXXXXXXXXXXXX...  # Same as PC!
```

```bash
# Login to GitHub Container Registry (for pulling images)
echo $YOUR_GITHUB_TOKEN | docker login ghcr.io -u igorcretu --password-stdin

# Start everything
docker compose -f docker-compose.prod.yml --profile cloudflare up -d

# Check status
docker compose -f docker-compose.prod.yml ps
```

**Done!** Your API is live at `https://api.yourdomain.com`

### Auto-Deploy Updates

Every time you push to `main`:
1. GitHub Actions builds new Docker image
2. Pushes to GitHub Container Registry
3. SSH to Raspberry Pi
4. Pulls new image
5. Restarts containers

**Zero-downtime deployments!** 🚀

---

## 🔗 Connect Frontend (Netlify)

### In Your Frontend Repository

Update `.env.production`:

```bash
VITE_API_URL=https://api.yourdomain.com/api
```

### In Netlify Dashboard

1. Site settings → Environment variables
2. Add: `VITE_API_URL` = `https://api.yourdomain.com/api`
3. Redeploy

### Test Connection

In your browser console on Netlify site:

```javascript
fetch('https://api.yourdomain.com/health')
  .then(r => r.json())
  .then(console.log);
```

Should return: `{ status: "healthy", ... }`

---

## 📚 Available Endpoints

Your backend has **15+ endpoints** ready to use:

### Cars
- `GET /api/cars` - List cars (with filters, pagination)
- `GET /api/cars/{id}` - Get car details
- `POST /api/cars` - Create car (for scraping)
- `GET /api/search?q=Toyota` - Search cars

### Predictions
- `POST /api/predict` - Predict car price
- `GET /api/predictions` - Prediction history

### Filters
- `GET /api/brands` - All brands
- `GET /api/models/{brand}` - Models for brand
- `GET /api/filters` - All filter options

### Statistics
- `GET /api/stats` - Market statistics
- `GET /api/stats/brand/{brand}` - Brand statistics

**Full API docs:** See [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

---

## 🎯 Your Development Flow

```
┌──────────────┐
│   Your PC    │
│              │
│  1. Write    │
│     Code     │
│              │
│  2. Test     │
│     Local    │
│              │
│  3. Test     │
│     Tunnel   │
│              │
│  4. Push to  │
│     GitHub   │
└──────┬───────┘
       │
       │ git push
       ▼
┌──────────────┐
│   GitHub     │
│              │
│  CI/CD       │
│  Actions     │
│  Builds &    │
│  Deploys     │
└──────┬───────┘
       │
       │ auto-deploy
       ▼
┌──────────────┐
│ Raspberry Pi │
│              │
│  Backend     │
│  Database    │
│  Tunnel      │
│              │
│  Live at:    │
│  api.your    │
│  domain.com  │
└──────────────┘
```

---

## 🆘 Troubleshooting

### Backend Won't Start

```bash
# Check logs
docker compose -f docker-compose.dev.yml logs backend

# Common issues:
# 1. Port 5000 already in use
sudo lsof -i :5000  # Find what's using it
# 2. Database not ready
docker compose -f docker-compose.dev.yml logs db
```

### Tunnel Not Working

```bash
# Check tunnel logs
docker compose logs cloudflared

# Verify token in .env
cat .env | grep CLOUDFLARE_TUNNEL_TOKEN

# Check Cloudflare Dashboard
# https://one.dash.cloudflare.com/ → Tunnels
```

### CORS Errors

```bash
# Update .env with your Netlify domain
echo "ALLOWED_ORIGINS=https://your-site.netlify.app" >> .env

# Restart
docker compose restart backend
```

### Database Issues

```bash
# Reset database (WARNING: deletes all data)
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up -d

# Check database directly
docker compose exec db psql -U bpr_user -d car_prediction
```

---

## 📖 Next Steps

1. ✅ **Test locally** - Make sure everything works
2. ✅ **Set up Cloudflare Tunnel** - Get public access
3. ✅ **Push to GitHub** - Version control
4. ✅ **Connect frontend** - Integrate with React
5. ✅ **Deploy to Raspberry Pi** - When you get it
6. ✅ **Add your ML model** - Replace placeholder in `app/ml/predictor.py`
7. ✅ **Add web scraping** - POST scraped data to `/api/cars`

---

## 💡 Pro Tips

### Use the Quick Reference

Keep [QUICK_REFERENCE.md](QUICK_REFERENCE.md) handy for common commands.

### Backup Your .env

```bash
cp .env .env.backup
# Store this safely! It's your entire configuration
```

### Monitor Your API

```bash
# Watch logs live
docker compose logs -f

# Check resource usage
docker stats

# View Cloudflare metrics
# https://one.dash.cloudflare.com/ → Tunnels → bpr-backend
```

### Test Everything

```bash
# Health check
curl http://localhost:5000/health

# Get sample cars
curl http://localhost:5000/api/cars

# Test prediction
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"brand":"Toyota","model":"Corolla","year":2020,"mileage":45000,"fuel_type":"Petrol","transmission":"Manual","body_type":"Sedan"}'
```

---

## 🎉 You're All Set!

You now have:
- ✅ Professional backend API with 15+ endpoints
- ✅ PostgreSQL database with sample data
- ✅ Cloudflare Tunnel for secure public access
- ✅ Docker setup that works on PC and Raspberry Pi
- ✅ CI/CD pipeline for auto-deployment
- ✅ Complete documentation

**Cost:** $0 (Everything is free!)

**Time to deploy:** ~10 minutes

**Maintenance:** Automatic updates via CI/CD

---

## 📞 Need Help?

1. **Quick commands:** [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
2. **Cloudflare setup:** [DOCKER_CLOUDFLARE_SETUP.md](DOCKER_CLOUDFLARE_SETUP.md)
3. **Frontend connection:** [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md)
4. **API reference:** [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
5. **GitHub issues:** Open an issue on GitHub

---

**Happy coding! 🚀**

Your backend is production-ready and waiting for your frontend and ML model!
