# Cloudflare Tunnel - Docker Setup (Portable)

This guide shows you how to set up Cloudflare Tunnel entirely in Docker, so you can move your setup between PC and Raspberry Pi without reconfiguration.

## Benefits of Docker-Based Setup

✅ **Portable** - Move between PC and Raspberry Pi seamlessly  
✅ **No manual installation** - Everything in containers  
✅ **Easy backup** - Just backup your `.env` file  
✅ **Clean** - No system-level installations  
✅ **Consistent** - Same setup everywhere  

## One-Time Setup (Do This Once on Any Machine)

### Step 1: Create Cloudflare Tunnel (Web Dashboard Method)

This is the **easiest** way and works without installing anything on your system.

1. **Go to Cloudflare Zero Trust Dashboard**
   - Visit: https://one.dash.cloudflare.com/
   - Login with your Cloudflare account
   - Go to: **Access → Tunnels**

2. **Create a New Tunnel**
   - Click "Create a tunnel"
   - Choose "Cloudflared"
   - Name it: `bpr-backend`
   - Click "Save tunnel"

3. **Install Connector - Choose Docker**
   - You'll see installation options
   - Select "Docker"
   - **Copy the token** that looks like:
     ```
     eyJhIjoiXXXXXXXXXXXXXXXXXXXXXX...
     ```
   - Save this token - you'll need it!

4. **Configure Public Hostname**
   - Subdomain: `api`
   - Domain: `yourdomain.com` (select your domain)
   - Path: Leave empty
   - Service Type: `HTTP`
   - URL: `backend:5000`
   
   Click "Save tunnel"

5. **Done!** 
   - Your tunnel is created
   - You have your token
   - DNS is automatically configured

### Step 2: Add Token to Your Project

On your PC (or later on Raspberry Pi):

```bash
cd ~/BPR-BackEnd

# Create .env if it doesn't exist
cp .env.example .env

# Add your Cloudflare Tunnel token
nano .env
```

Add this line to `.env`:

```bash
CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoiXXXXXXXXXXXXXXXXXXXXXX...
```

That's it! The token contains all the configuration.

### Step 3: Start Everything with Docker

```bash
# Start backend, database, AND Cloudflare Tunnel
docker compose -f docker-compose.prod.yml --profile cloudflare up -d

# Check everything is running
docker compose -f docker-compose.prod.yml --profile cloudflare ps

# View logs
docker compose -f docker-compose.prod.yml --profile cloudflare logs -f cloudflared
```

### Step 4: Test It

```bash
# From anywhere in the world
curl https://api.yourdomain.com/health

# Should return:
# {
#   "status": "healthy",
#   "service": "BPR Backend API",
#   ...
# }
```

## Moving from PC to Raspberry Pi

This is the **beauty** of the Docker setup - it's super easy!

### On Your PC (Before Moving)

```bash
# 1. Make sure your .env file has the token
cat .env | grep CLOUDFLARE_TUNNEL_TOKEN

# 2. Commit your code (but not .env!)
git add .
git commit -m "Ready for Raspberry Pi deployment"
git push origin main
```

### On Raspberry Pi (When You Get It)

```bash
# 1. Clone your repository
git clone https://github.com/igorcretu/BPR-BackEnd.git
cd BPR-BackEnd

# 2. Create .env with the SAME token
nano .env
```

Add to `.env`:
```bash
POSTGRES_DB=car_prediction
POSTGRES_USER=bpr_user
POSTGRES_PASSWORD=your-strong-password
SECRET_KEY=your-secret-key
ALLOWED_ORIGINS=https://your-site.netlify.app
CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoiXXXXXXXXXXXXXXXXXXXXXX...  # Same token as PC!
```

```bash
# 3. Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u igorcretu --password-stdin

# 4. Start everything
docker compose -f docker-compose.prod.yml --profile cloudflare up -d

# 5. Done! Your API is live at https://api.yourdomain.com
```

**That's it!** Same tunnel, same token, works on both machines.

## Understanding the Docker Setup

### docker-compose.prod.yml

```yaml
cloudflared:
  image: cloudflare/cloudflared:latest
  container_name: bpr-cloudflared
  restart: unless-stopped
  command: tunnel --no-autoupdate run --token ${CLOUDFLARE_TUNNEL_TOKEN}
  depends_on:
    backend:
      condition: service_healthy
  networks:
    - bpr-network
  profiles:
    - cloudflare
```

**What this does:**
- Uses official Cloudflare Docker image
- Runs the tunnel with your token
- Connects to `backend:5000` on the Docker network
- Starts automatically if backend is healthy
- Uses `cloudflare` profile (optional activation)

### Network Routing

```
Internet → https://api.yourdomain.com
    ↓
Cloudflare Network
    ↓
Cloudflared Container (Docker)
    ↓
Backend Container (Docker network: backend:5000)
    ↓
PostgreSQL Container (Docker network: db:5432)
```

Everything stays inside Docker - no exposed ports needed!

## Usage Commands

### Start with Cloudflare Tunnel

```bash
# Start all services including tunnel
docker compose -f docker-compose.prod.yml --profile cloudflare up -d
```

### Start without Cloudflare Tunnel (Local only)

```bash
# Just backend and database
docker compose -f docker-compose.prod.yml up -d
```

### View Tunnel Logs

```bash
docker compose -f docker-compose.prod.yml logs -f cloudflared
```

### Restart Just the Tunnel

```bash
docker compose -f docker-compose.prod.yml restart cloudflared
```

### Stop Everything

```bash
docker compose -f docker-compose.prod.yml --profile cloudflare down
```

## Testing Your Setup

### 1. Check Containers

```bash
docker compose -f docker-compose.prod.yml --profile cloudflare ps

# Should show:
# - bpr-postgres (running)
# - bpr-flask (running)  
# - bpr-cloudflared (running)
```

### 2. Check Tunnel Connection

```bash
docker compose -f docker-compose.prod.yml logs cloudflared

# Should show:
# "Connection established"
# "Registered tunnel connection"
```

### 3. Test Locally First

```bash
# Test backend directly
curl http://localhost:5000/health

# Should work
```

### 4. Test Through Tunnel

```bash
# Test through Cloudflare
curl https://api.yourdomain.com/health

# Should also work!
```

### 5. Test from Frontend

In your browser console on your Netlify site:

```javascript
fetch('https://api.yourdomain.com/api/cars')
  .then(r => r.json())
  .then(console.log);
```

## Environment Variables Reference

Required in `.env`:

```bash
# Database
POSTGRES_DB=car_prediction
POSTGRES_USER=bpr_user
POSTGRES_PASSWORD=your-strong-password

# Flask
SECRET_KEY=your-secret-key

# CORS (important for frontend!)
ALLOWED_ORIGINS=https://your-site.netlify.app,https://api.yourdomain.com

# Cloudflare Tunnel Token (from dashboard)
CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoiXXXXXXXXXXXXXXXXXXXXXX...
```

## Backup Your Configuration

Your entire setup is in one file!

```bash
# Backup your .env file
cp .env .env.backup

# Store it safely (encrypted!)
# This is ALL you need to recreate your setup anywhere
```

## Updating the Tunnel Configuration

If you need to change the tunnel settings (like subdomain):

1. Go to Cloudflare Dashboard: https://one.dash.cloudflare.com/
2. Access → Tunnels → bpr-backend
3. Click "Configure"
4. Update Public Hostname settings
5. Save

**No restart needed!** Changes are live immediately.

## Troubleshooting

### Tunnel Container Keeps Restarting

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs cloudflared

# Common issues:
# 1. Invalid token - check your .env
# 2. Backend not healthy - check backend logs
```

### "Unable to reach backend service"

```bash
# Check backend is running
docker compose -f docker-compose.prod.yml ps backend

# Check backend health
docker compose -f docker-compose.prod.yml exec backend curl http://localhost:5000/health

# Check Docker network
docker network inspect bpr-backend_bpr-network
```

### CORS Errors

```bash
# Make sure ALLOWED_ORIGINS is set in .env
cat .env | grep ALLOWED_ORIGINS

# Should include your Netlify domain
# ALLOWED_ORIGINS=https://your-site.netlify.app

# Restart backend after changing
docker compose -f docker-compose.prod.yml restart backend
```

### Token Expired or Invalid

If your tunnel stops working:

1. Go to Cloudflare Dashboard
2. Access → Tunnels → bpr-backend
3. Click on the tunnel
4. Click "Configure"
5. You might need to regenerate the token
6. Update `.env` with new token
7. Restart: `docker compose -f docker-compose.prod.yml restart cloudflared`

## Security Best Practices

### 1. Never Commit .env File

```bash
# Already in .gitignore
git status

# .env should NOT appear
```

### 2. Use Strong Passwords

```bash
# Generate strong password
openssl rand -base64 32

# Add to .env
```

### 3. Limit CORS Origins

```bash
# In .env, specify exact origins
ALLOWED_ORIGINS=https://your-site.netlify.app

# NOT this:
# ALLOWED_ORIGINS=*
```

### 4. Keep Token Secret

Your `CLOUDFLARE_TUNNEL_TOKEN` is sensitive!
- Don't commit it to Git
- Don't share it publicly
- Store it encrypted if backing up

## Monitoring

### Check Tunnel Status in Dashboard

1. Go to: https://one.dash.cloudflare.com/
2. Access → Tunnels → bpr-backend
3. You'll see:
   - Connection status (should be "Healthy")
   - Traffic metrics
   - Number of connections
   - Last seen time

### Check in Docker

```bash
# Watch tunnel logs live
docker compose -f docker-compose.prod.yml logs -f cloudflared

# Check resource usage
docker stats bpr-cloudflared
```

## Alternative: Local cloudflared (Not Recommended)

If you really want to install cloudflared on the system instead of Docker:

See [CLOUDFLARE_TUNNEL_SETUP.md](CLOUDFLARE_TUNNEL_SETUP.md)

But the Docker method is **easier** and **more portable**!

## Comparison: Docker vs Local Installation

| Feature | Docker Method | Local Install |
|---------|--------------|---------------|
| **Portability** | ✅ Copy .env and go | ❌ Reinstall everywhere |
| **Clean** | ✅ No system changes | ❌ System-level install |
| **Backup** | ✅ Just .env file | ❌ Config files scattered |
| **Updates** | ✅ Auto (Docker image) | ⚠️ Manual |
| **Ease** | ✅ One command | ⚠️ Multiple steps |

**Winner:** Docker Method! 🏆

## CI/CD Integration

Your GitHub Actions already handles deployment:

```yaml
# In .github/workflows/docker-build-deploy.yml
- name: Deploy to Raspberry Pi
  script: |
    cd /home/pi/bpr-backend
    git pull origin main
    docker compose -f docker-compose.prod.yml --profile cloudflare pull
    docker compose -f docker-compose.prod.yml --profile cloudflare up -d
```

Just make sure your `.env` is on the Raspberry Pi with the tunnel token!

## Summary

### Initial Setup (Once)
1. Create tunnel in Cloudflare Dashboard
2. Copy token
3. Add to `.env`

### Development (PC)
```bash
docker compose -f docker-compose.prod.yml --profile cloudflare up -d
```

### Production (Raspberry Pi)
```bash
# Same .env file
# Same command
docker compose -f docker-compose.prod.yml --profile cloudflare up -d
```

### Result
✅ Your API is accessible at `https://api.yourdomain.com` from anywhere  
✅ Works on PC and Raspberry Pi identically  
✅ One `.env` file is your entire configuration  
✅ No manual installations or configurations  
✅ Completely free!  

🎉 **Perfect portability!**
