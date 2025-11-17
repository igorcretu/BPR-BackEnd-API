# Quick Reference - Docker + Cloudflare Tunnel

## 🚀 Quick Start

### First Time Setup (5 minutes)

1. **Get Cloudflare Tunnel Token:**
   ```
   1. Go to: https://one.dash.cloudflare.com/
   2. Access → Tunnels → Create tunnel
   3. Name: bpr-backend
   4. Copy token (eyJ...)
   5. Configure:
      - Subdomain: api
      - Domain: yourdomain.com  
      - Service: HTTP → backend:5000
   ```

2. **Add to .env:**
   ```bash
   CLOUDFLARE_TUNNEL_TOKEN=eyJhXXXXXXXXXXXX...
   ```

3. **Start:**
   ```bash
   docker compose -f docker-compose.prod.yml --profile cloudflare up -d
   ```

4. **Test:**
   ```bash
   curl https://api.yourdomain.com/health
   ```

**Done!** ✅

---

## 📋 Common Commands

### Development (PC)

```bash
# Start everything (local only)
./start-dev.sh

# Or manually:
docker compose -f docker-compose.dev.yml up -d

# Start with Cloudflare Tunnel (test public access)
docker compose -f docker-compose.dev.yml --profile cloudflare up -d

# Stop
docker compose -f docker-compose.dev.yml down

# Reset database
docker compose -f docker-compose.dev.yml down -v
```

### Production (Raspberry Pi)

```bash
# Start everything including Cloudflare Tunnel
docker compose -f docker-compose.prod.yml --profile cloudflare up -d

# Without tunnel (local network only)
docker compose -f docker-compose.prod.yml up -d

# Stop
docker compose -f docker-compose.prod.yml --profile cloudflare down

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Just tunnel logs
docker compose -f docker-compose.prod.yml logs -f cloudflared

# Restart backend
docker compose -f docker-compose.prod.yml restart backend

# Update and restart
git pull origin main
docker compose -f docker-compose.prod.yml --profile cloudflare pull
docker compose -f docker-compose.prod.yml --profile cloudflare up -d
```

---

## 🔍 Debugging

### Check Status

```bash
# All containers
docker compose -f docker-compose.prod.yml --profile cloudflare ps

# Should show:
# ✅ bpr-postgres (healthy)
# ✅ bpr-flask (healthy)
# ✅ bpr-cloudflared (running)
```

### View Logs

```bash
# All logs
docker compose -f docker-compose.prod.yml --profile cloudflare logs -f

# Backend only
docker compose -f docker-compose.prod.yml logs -f backend

# Tunnel only
docker compose -f docker-compose.prod.yml logs -f cloudflared

# Database only
docker compose -f docker-compose.prod.yml logs -f db
```

### Test Connectivity

```bash
# Test backend locally
curl http://localhost:5000/health

# Test through tunnel (from anywhere)
curl https://api.yourdomain.com/health

# Test specific endpoint
curl https://api.yourdomain.com/api/cars

# Test with verbose output
curl -v https://api.yourdomain.com/health
```

### Common Issues

**Tunnel keeps restarting:**
```bash
# Check token in .env
cat .env | grep CLOUDFLARE_TUNNEL_TOKEN

# View tunnel logs
docker compose -f docker-compose.prod.yml logs cloudflared
```

**CORS errors:**
```bash
# Check ALLOWED_ORIGINS in .env
cat .env | grep ALLOWED_ORIGINS

# Should be:
# ALLOWED_ORIGINS=https://your-site.netlify.app

# Restart backend after changing
docker compose -f docker-compose.prod.yml restart backend
```

**Backend not healthy:**
```bash
# Check backend logs
docker compose -f docker-compose.prod.yml logs backend

# Check database connection
docker compose -f docker-compose.prod.yml exec backend \
  python -c "from app.models import db; db.session.execute(db.text('SELECT 1'))"
```

---

## 🔄 Moving Between PC and Raspberry Pi

### Export from PC

```bash
# Just need your .env file!
cat .env

# Copy these values:
# - CLOUDFLARE_TUNNEL_TOKEN
# - POSTGRES_PASSWORD
# - SECRET_KEY
```

### Import to Raspberry Pi

```bash
# Clone repo
git clone https://github.com/igorcretu/BPR-BackEnd.git
cd BPR-BackEnd

# Create .env with same values
nano .env

# Start
docker compose -f docker-compose.prod.yml --profile cloudflare up -d
```

**That's it!** Same token = same tunnel = works immediately! 🎉

---

## 📊 Monitoring

### Cloudflare Dashboard

```
https://one.dash.cloudflare.com/
→ Access → Tunnels → bpr-backend

Shows:
- Connection status
- Traffic metrics
- Active connections
```

### Docker Stats

```bash
# Resource usage
docker stats

# Specific container
docker stats bpr-cloudflared
```

### Logs

```bash
# Follow logs live
docker compose -f docker-compose.prod.yml --profile cloudflare logs -f

# Last 100 lines
docker compose -f docker-compose.prod.yml logs --tail=100

# Since 1 hour ago
docker compose -f docker-compose.prod.yml logs --since=1h
```

---

## 🔐 Security Checklist

- [ ] Strong `POSTGRES_PASSWORD` in .env
- [ ] Strong `SECRET_KEY` in .env  
- [ ] `ALLOWED_ORIGINS` set to your Netlify domain (not `*`)
- [ ] `.env` not committed to Git
- [ ] Cloudflare SSL/TLS set to "Full" or "Full (strict)"
- [ ] Backend only exposed to localhost (127.0.0.1:5000)

---

## 📞 Need Help?

1. Check logs: `docker compose logs -f`
2. See [DOCKER_CLOUDFLARE_SETUP.md](DOCKER_CLOUDFLARE_SETUP.md)
3. See [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md)
4. See [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

---

## 🎯 Quick Tests

### Test Suite

```bash
# 1. Backend health
curl http://localhost:5000/health

# 2. Database connection
curl http://localhost:5000/api/cars

# 3. Tunnel connection
curl https://api.yourdomain.com/health

# 4. CORS headers
curl -I https://api.yourdomain.com/api/cars

# 5. Prediction endpoint
curl -X POST https://api.yourdomain.com/api/predict \
  -H "Content-Type: application/json" \
  -d '{"brand":"Toyota","model":"Corolla","year":2020,"mileage":45000,"fuel_type":"Petrol","transmission":"Manual","body_type":"Sedan"}'
```

All should return 200 OK ✅

---

## 💡 Pro Tips

1. **Backup .env:** This file is your entire config
   ```bash
   cp .env .env.backup
   ```

2. **Check before deploying:**
   ```bash
   docker compose -f docker-compose.prod.yml config
   ```

3. **Clean up old images:**
   ```bash
   docker image prune -f
   ```

4. **View container sizes:**
   ```bash
   docker images
   ```

5. **Export database:**
   ```bash
   docker compose -f docker-compose.prod.yml exec db \
     pg_dump -U bpr_user car_prediction > backup.sql
   ```

---

## ⚡ One-Liners

```bash
# Restart everything
docker compose -f docker-compose.prod.yml --profile cloudflare restart

# See what's using port 5000
lsof -i :5000

# Check if tunnel is connected
docker compose -f docker-compose.prod.yml exec cloudflared \
  cloudflared tunnel info

# Force rebuild
docker compose -f docker-compose.prod.yml build --no-cache

# Remove everything and start fresh
docker compose -f docker-compose.prod.yml --profile cloudflare down -v && \
docker compose -f docker-compose.prod.yml --profile cloudflare up -d
```
