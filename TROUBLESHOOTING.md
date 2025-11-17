# 🔧 Raspberry Pi Troubleshooting Guide

Quick solutions to common problems when deploying to Raspberry Pi.

---

## 🆘 Quick Diagnostics

Run this first to see what's wrong:

```bash
cd ~/projects/BPR-BackEnd

# Check container status
docker compose -f docker-compose.prod.yml ps

# Check logs for errors
docker compose -f docker-compose.prod.yml logs --tail=50

# Check disk space
df -h

# Check memory
free -h

# Check Docker is running
docker info
```

---

## Problem: Can't SSH to Raspberry Pi

### Symptoms
- `ssh: connect to host X.X.X.X port 22: Connection refused`
- `ssh: connect to host X.X.X.X port 22: No route to host`

### Solutions

**1. Find your Pi's IP address**

On the Raspberry Pi (connected to monitor):
```bash
hostname -I
```

Or check your router's admin panel.

**2. Check Pi is on network**
```bash
ping your-pi-ip
```

**3. Enable SSH (if disabled)**

On the Raspberry Pi:
```bash
sudo systemctl enable ssh
sudo systemctl start ssh
```

**4. Check firewall**
```bash
sudo ufw status
# If active and blocking:
sudo ufw allow 22/tcp
```

---

## Problem: Docker Permission Denied

### Symptoms
- `permission denied while trying to connect to the Docker daemon socket`
- `Got permission denied while trying to connect to the Docker daemon`

### Solution

```bash
# Add your user to docker group
sudo usermod -aG docker $USER

# IMPORTANT: Log out and log back in
exit

# SSH back in
ssh pi@your-pi-ip

# Verify it works
docker ps
```

---

## Problem: Containers Won't Start

### Symptoms
- `docker compose ps` shows containers as `Exited`
- Containers keep restarting

### Solutions

**1. Check logs**
```bash
docker compose -f docker-compose.prod.yml logs backend
docker compose -f docker-compose.prod.yml logs db
```

**2. Database not ready**

Wait 30-60 seconds. Database takes time to initialize on first run.

```bash
# Check if database is healthy
docker compose -f docker-compose.prod.yml ps db

# Should show: "healthy"
```

**3. Port already in use**

```bash
# Check what's using port 5000
sudo lsof -i :5000

# Kill the process
sudo kill -9 <PID>

# Or change the port in docker-compose.prod.yml
```

**4. Out of memory**

```bash
# Check memory
free -h

# If low, stop other services or restart Pi
sudo reboot
```

**5. Missing .env file**

```bash
# Check if .env exists
ls -la .env

# If not, create it
cp .env.example .env
nano .env
```

---

## Problem: Can't Pull Docker Images

### Symptoms
- `Error response from daemon: pull access denied`
- `unauthorized: authentication required`

### Solution

```bash
# Make sure you're logged in to GitHub Container Registry
echo "YOUR_GITHUB_TOKEN" | docker login ghcr.io -u igorcretu --password-stdin

# Token needs 'read:packages' permission
# Create one at: https://github.com/settings/tokens
```

---

## Problem: Database Won't Initialize

### Symptoms
- Cars endpoint returns empty array
- Database has no tables

### Solutions

**1. Check if init.sql ran**

```bash
# Connect to database
docker compose -f docker-compose.prod.yml exec db \
  psql -U bpr_user -d car_prediction

# Check tables
\dt

# Should show: cars, price_predictions, scraping_logs, market_statistics
```

**2. Manually initialize database**

```bash
# Copy init.sql to container
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U bpr_user -d car_prediction < init.sql
```

**3. Reset database (WARNING: deletes all data)**

```bash
# Stop and remove volumes
docker compose -f docker-compose.prod.yml down -v

# Start fresh
docker compose -f docker-compose.prod.yml --profile cloudflare up -d

# Database will initialize automatically
```

---

## Problem: Cloudflare Tunnel Not Working

### Symptoms
- Can access locally but not via `https://api.yourdomain.com`
- `cloudflared` container keeps restarting

### Solutions

**1. Check tunnel token**

```bash
# View .env
cat .env | grep CLOUDFLARE_TUNNEL_TOKEN

# Should start with: eyJ
# If empty or wrong, update it
nano .env
```

**2. Check tunnel logs**

```bash
docker compose -f docker-compose.prod.yml logs cloudflared

# Look for:
# ✅ "Connection established"
# ✅ "Registered tunnel connection"
# ❌ "authentication failed" → bad token
# ❌ "unable to reach origin" → backend not running
```

**3. Check tunnel in Cloudflare Dashboard**

1. Go to: https://one.dash.cloudflare.com/
2. Access → Tunnels → bpr-backend
3. Should show: "Healthy" with green indicator

**4. Verify public hostname**

In Cloudflare Dashboard, check:
- Subdomain: `api`
- Domain: `yourdomain.com`
- Service: `HTTP` → `backend:5000` (NOT localhost:5000!)

**5. Test backend is accessible**

```bash
# On Pi, test backend is running
curl http://localhost:5000/health

# Should return JSON response
```

**6. Restart tunnel**

```bash
docker compose -f docker-compose.prod.yml restart cloudflared
```

---

## Problem: CORS Errors from Frontend

### Symptoms
- Browser console shows: `Access to fetch at 'https://api.yourdomain.com' ... has been blocked by CORS policy`

### Solution

**1. Update ALLOWED_ORIGINS in .env**

```bash
nano .env
```

Change:
```bash
# Wrong:
ALLOWED_ORIGINS=*

# Correct:
ALLOWED_ORIGINS=https://your-site.netlify.app,https://api.yourdomain.com
```

**2. Restart backend**

```bash
docker compose -f docker-compose.prod.yml restart backend
```

**3. Verify CORS headers**

```bash
curl -I https://api.yourdomain.com/api/cars

# Should include:
# Access-Control-Allow-Origin: https://your-site.netlify.app
```

---

## Problem: Out of Disk Space

### Symptoms
- `no space left on device`
- Containers won't start

### Solutions

**1. Check disk usage**

```bash
df -h

# If /dev/root or / is >90% full:
```

**2. Clean Docker**

```bash
# Remove unused containers, images, networks
docker system prune -a

# Answer 'y' to confirm

# This can free up several GB
```

**3. Clean old logs**

```bash
# Clean system logs
sudo journalctl --vacuum-time=7d

# Clean apt cache
sudo apt clean
```

**4. Remove old backups**

```bash
# If you have backup files
rm ~/backup_*.sql
```

---

## Problem: Backend Returns 500 Errors

### Symptoms
- API returns `500 Internal Server Error`
- Health endpoint might work, but other endpoints don't

### Solutions

**1. Check backend logs**

```bash
docker compose -f docker-compose.prod.yml logs backend

# Look for Python tracebacks or errors
```

**2. Check database connection**

```bash
# Test database connectivity
docker compose -f docker-compose.prod.yml exec backend \
  python -c "from app.models import db; db.session.execute(db.text('SELECT 1'))"

# Should output nothing (success)
```

**3. Check environment variables**

```bash
# View what backend sees
docker compose -f docker-compose.prod.yml exec backend env

# Verify DATABASE_URL is correct
```

**4. Restart backend**

```bash
docker compose -f docker-compose.prod.yml restart backend
```

---

## Problem: CI/CD Auto-Deploy Not Working

### Symptoms
- Push to GitHub doesn't deploy to Pi
- GitHub Actions workflow fails

### Solutions

**1. Check GitHub Actions logs**

1. Go to: https://github.com/igorcretu/BPR-BackEnd/actions
2. Click on the failed workflow
3. Read the error message

**2. Verify GitHub Secrets**

Go to: https://github.com/igorcretu/BPR-BackEnd/settings/secrets/actions

Should have:
- `PI_HOST` (your Pi's IP)
- `PI_USERNAME` (usually `pi`)
- `PI_SSH_KEY` (private SSH key)
- `PI_PORT` (usually `22`)

**3. Test SSH from Pi to itself**

```bash
# On Raspberry Pi
ssh -T pi@localhost

# Should connect without password
```

**4. Check SSH key is authorized**

```bash
cat ~/.ssh/authorized_keys

# Should contain your public key
```

**5. Regenerate SSH key**

```bash
ssh-keygen -t ed25519 -C "github-actions-new"
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Update PI_SSH_KEY secret in GitHub with new private key
cat ~/.ssh/id_ed25519
```

---

## Problem: Pi Rebooted, Containers Not Running

### Symptoms
- After reboot, backend is not accessible
- `docker ps` shows no containers

### Solutions

**1. Check if Docker service is running**

```bash
sudo systemctl status docker

# If not running:
sudo systemctl start docker
sudo systemctl enable docker
```

**2. Manually start containers**

```bash
cd ~/projects/BPR-BackEnd
docker compose -f docker-compose.prod.yml --profile cloudflare up -d
```

**3. Verify restart policy**

```bash
# Check docker-compose.prod.yml has:
# restart: unless-stopped

grep "restart:" docker-compose.prod.yml
```

---

## Problem: Slow Performance

### Symptoms
- API responses are slow
- High CPU usage

### Solutions

**1. Check resource usage**

```bash
# Overall system
htop  # (install with: sudo apt install htop)

# Docker containers
docker stats

# Disk I/O
sudo iotop  # (install with: sudo apt install iotop)
```

**2. Reduce logging**

```bash
# In docker-compose.prod.yml, add:
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

**3. Check database queries**

Slow queries might be the issue. Check logs for long-running queries.

**4. Add swap space**

```bash
# Check swap
free -h

# If swap is 0, add some:
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Change CONF_SWAPSIZE=100 to CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

---

## Problem: Can't Connect to Database

### Symptoms
- Backend logs show database connection errors
- `Connection refused` or `Connection timeout`

### Solutions

**1. Check database is running**

```bash
docker compose -f docker-compose.prod.yml ps db

# Should show: "healthy"
```

**2. Check database logs**

```bash
docker compose -f docker-compose.prod.yml logs db

# Look for errors
```

**3. Verify DATABASE_URL in .env**

```bash
cat .env | grep DATABASE_URL

# Should be:
# postgresql://bpr_user:YOUR_PASSWORD@db:5432/car_prediction
```

**4. Test database connection**

```bash
docker compose -f docker-compose.prod.yml exec db \
  psql -U bpr_user -d car_prediction -c "SELECT 1;"

# Should return: 1
```

---

## Problem: Git Pull Fails

### Symptoms
- `git pull` shows conflicts
- Can't update code

### Solutions

**1. Stash local changes**

```bash
git stash
git pull origin main
git stash pop
```

**2. Force pull (WARNING: overwrites local changes)**

```bash
git fetch origin
git reset --hard origin/main
```

**3. Check Git config**

```bash
git config --list

# If needed:
git config --global user.email "you@example.com"
git config --global user.name "Your Name"
```

---

## 🆘 Nuclear Options (Last Resort)

If nothing else works, try these:

### Complete Container Reset

```bash
cd ~/projects/BPR-BackEnd

# Stop and remove everything
docker compose -f docker-compose.prod.yml down -v

# Remove all Docker data
docker system prune -a -f

# Start fresh
docker compose -f docker-compose.prod.yml --profile cloudflare up -d
```

### Complete Project Reset

```bash
cd ~/projects

# Backup .env file
cp BPR-BackEnd/.env ~/env_backup

# Remove project
rm -rf BPR-BackEnd

# Re-clone
git clone https://github.com/igorcretu/BPR-BackEnd.git
cd BPR-BackEnd

# Restore .env
cp ~/env_backup .env

# Start
docker compose -f docker-compose.prod.yml --profile cloudflare up -d
```

### Raspberry Pi Reboot

```bash
sudo reboot
```

Sometimes, a simple reboot fixes everything!

---

## 📞 Still Having Issues?

1. **Check logs:** `docker compose logs -f`
2. **Check GitHub Actions:** https://github.com/igorcretu/BPR-BackEnd/actions
3. **Check Cloudflare Dashboard:** https://one.dash.cloudflare.com/
4. **Read full guides:**
   - RASPBERRY_PI_DEPLOYMENT.md
   - DOCKER_CLOUDFLARE_SETUP.md
   - QUICK_REFERENCE.md

---

## 🔍 Diagnostic Commands Summary

```bash
# System
hostname -I           # Get IP address
free -h              # Check memory
df -h                # Check disk space
htop                 # Monitor processes

# Docker
docker ps            # Running containers
docker compose ps    # Project containers
docker stats         # Resource usage
docker logs <name>   # Container logs
docker system df     # Docker disk usage

# Network
curl localhost:5000/health              # Local test
curl https://api.yourdomain.com/health  # Public test
ping google.com      # Internet connectivity

# Files
ls -la .env          # Check .env exists
cat .env             # View .env
nano .env            # Edit .env

# Git
git status           # Check repo status
git log -1           # Last commit
git pull             # Update code
```

---

**Most problems are solved by:**
1. Checking logs
2. Verifying .env file
3. Restarting containers
4. Checking Cloudflare Dashboard

**Good luck! 🍀**
