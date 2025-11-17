# 🚀 Deploy Your BPR Backend to Raspberry Pi - Step by Step

This guide assumes your Raspberry Pi 5 is already set up with Raspberry Pi OS and you have SSH access.

**Time Required:** 20-30 minutes  
**Prerequisites:** Raspberry Pi 5 running, internet connected, SSH access

---

## 📋 Pre-Deployment Checklist

Before starting, make sure you have:

- [ ] Raspberry Pi 5 running with Raspberry Pi OS
- [ ] SSH access to your Pi (you can connect via `ssh pi@your-pi-ip`)
- [ ] Your GitHub repository: https://github.com/igorcretu/BPR-BackEnd.git
- [ ] Cloudflare account with a domain
- [ ] Your `.env` file from your PC (with database passwords, secret key, and Cloudflare token)

---

## Step 1: Connect to Your Raspberry Pi

```bash
# From your PC, connect via SSH
ssh pi@192.168.1.XXX
# Replace XXX with your Pi's IP address

# You can find your Pi's IP with:
# - Check your router's admin panel
# - Or on the Pi: hostname -I
```

**First time connecting?**
- Default username: `pi`
- Default password: `raspberry` (change this immediately!)

```bash
# Change password (recommended)
passwd
```

---

## Step 2: Update System & Install Docker

```bash
# Update package list
sudo apt update && sudo apt upgrade -y

# Install Docker (official script)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group (so you don't need sudo)
sudo usermod -aG docker $USER

# Install Docker Compose plugin
sudo apt-get install docker-compose-plugin -y

# Log out and back in for group changes to take effect
exit
```

Log back in:
```bash
ssh pi@your-pi-ip
```

Verify Docker is working:
```bash
docker --version
docker compose version

# Should show something like:
# Docker version 24.0.x
# Docker Compose version v2.x.x
```

---

## Step 3: Install Git (if not already installed)

```bash
# Check if git is installed
git --version

# If not installed:
sudo apt install git -y
```

---

## Step 4: Clone Your Backend Repository

```bash
# Create a directory for your project
mkdir -p ~/projects
cd ~/projects

# Clone your repository
git clone https://github.com/igorcretu/BPR-BackEnd.git

# Navigate into the project
cd BPR-BackEnd

# Verify files are there
ls -la
```

You should see:
- `docker-compose.prod.yml`
- `Dockerfile`
- `init.sql`
- `app/` directory
- etc.

---

## Step 5: Create Your .env File

This is the most important step! Your `.env` file contains all your secrets.

```bash
# Create .env from example
cp .env.example .env

# Edit the file
nano .env
```

**In the nano editor, add/update these values:**

```bash
# Database Configuration
POSTGRES_DB=car_prediction
POSTGRES_USER=bpr_user
POSTGRES_PASSWORD=YOUR_STRONG_DATABASE_PASSWORD_HERE

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=YOUR_STRONG_SECRET_KEY_HERE

# CORS Configuration (your Netlify frontend domain)
ALLOWED_ORIGINS=https://your-site.netlify.app,https://api.yourdomain.com

# Cloudflare Tunnel Token (from Step 6)
# Leave this empty for now, we'll add it in Step 6
CLOUDFLARE_TUNNEL_TOKEN=
```

**Generate strong passwords:**
```bash
# Generate a strong password for database
openssl rand -base64 32

# Generate a strong secret key
openssl rand -base64 64
```

**Save and exit nano:**
- Press `Ctrl + X`
- Press `Y` to confirm
- Press `Enter` to save

---

## Step 6: Set Up Cloudflare Tunnel (Public Access)

This makes your backend accessible from the internet (so your Netlify frontend can connect).

### 6.1: Create Tunnel in Cloudflare Dashboard

**On your PC (in a web browser):**

1. Go to: **https://one.dash.cloudflare.com/**
2. Login to your Cloudflare account
3. Go to: **Zero Trust → Access → Tunnels**
4. Click: **Create a tunnel**
5. Select: **Cloudflared**
6. Name: `bpr-backend`
7. Click: **Save tunnel**

### 6.2: Get Your Tunnel Token

On the next screen, you'll see installation instructions.

1. Look for the **Docker** section
2. You'll see a command like:
   ```bash
   docker run cloudflare/cloudflared:latest tunnel --no-autoupdate run --token eyJhIjoiXXXXXXXXXXXXXXXXXXXXXX...
   ```
3. **COPY the token** (the part starting with `eyJ...`)
4. This is your `CLOUDFLARE_TUNNEL_TOKEN`

### 6.3: Configure Public Hostname

Still in the Cloudflare dashboard:

1. Under **Public Hostname**, click **Add a public hostname**
2. Fill in:
   - **Subdomain:** `api`
   - **Domain:** `yourdomain.com` (select your domain from dropdown)
   - **Path:** (leave empty)
   - **Type:** `HTTP`
   - **URL:** `backend:5000`

3. Click **Save hostname**

### 6.4: Add Token to Your Raspberry Pi

**Back on your Raspberry Pi (SSH):**

```bash
# Edit .env file
nano .env
```

Find the line:
```bash
CLOUDFLARE_TUNNEL_TOKEN=
```

Replace it with:
```bash
CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoiXXXXXXXXXXXXXXXXXXXXXX...
```
(paste your actual token)

**Save and exit:** `Ctrl + X`, then `Y`, then `Enter`

---

## Step 7: Login to GitHub Container Registry

Your Docker images are stored in GitHub Container Registry. You need to authenticate.

### 7.1: Create GitHub Personal Access Token

**On your PC (in a web browser):**

1. Go to: **https://github.com/settings/tokens**
2. Click: **Generate new token → Generate new token (classic)**
3. Note: `Raspberry Pi Docker Access`
4. Select scopes:
   - ✅ `read:packages` (to download images)
5. Click: **Generate token**
6. **COPY THE TOKEN** (you'll only see it once!)

### 7.2: Login on Raspberry Pi

**Back on your Raspberry Pi (SSH):**

```bash
# Login to GitHub Container Registry
echo "YOUR_GITHUB_TOKEN" | docker login ghcr.io -u igorcretu --password-stdin

# You should see: "Login Succeeded"
```

Replace `YOUR_GITHUB_TOKEN` with the token you just created.

**Example:**
```bash
echo "ghp_xxxxxxxxxxxxxxxxxxxx" | docker login ghcr.io -u igorcretu --password-stdin
```

---

## Step 8: Start Your Backend

Now the moment of truth! Start all your containers.

```bash
# Make sure you're in the project directory
cd ~/projects/BPR-BackEnd

# Start all services (backend, database, cloudflare tunnel)
docker compose -f docker-compose.prod.yml --profile cloudflare up -d

# This will:
# 1. Pull PostgreSQL image
# 2. Pull your Flask backend image from GitHub
# 3. Pull Cloudflare Tunnel image
# 4. Start all containers
# 5. Initialize database with sample data
```

**First time will take 2-5 minutes** (downloading images).

---

## Step 9: Verify Everything is Running

### 9.1: Check Container Status

```bash
# List running containers
docker compose -f docker-compose.prod.yml --profile cloudflare ps

# You should see 3 containers:
# ✅ bpr-postgres (healthy)
# ✅ bpr-flask (healthy)
# ✅ bpr-cloudflared (running)
```

### 9.2: Check Logs

```bash
# View all logs
docker compose -f docker-compose.prod.yml logs

# View just backend logs
docker compose -f docker-compose.prod.yml logs backend

# Follow logs in real-time
docker compose -f docker-compose.prod.yml logs -f

# Stop following: Ctrl + C
```

Look for:
- ✅ Database: `database system is ready to accept connections`
- ✅ Backend: `Running on http://0.0.0.0:5000`
- ✅ Cloudflare: `Connection established` or `Registered tunnel connection`

---

## Step 10: Test Your Backend

### 10.1: Test Locally (on the Pi)

```bash
# Test health endpoint
curl http://localhost:5000/health

# Expected output:
# {
#   "status": "healthy",
#   "service": "BPR Backend API",
#   "version": "1.0.0",
#   "database": "connected",
#   ...
# }

# Test cars endpoint
curl http://localhost:5000/api/cars

# Should return list of 30 sample cars
```

### 10.2: Test Public Access (from your PC)

**On your PC (not SSH, just regular terminal/browser):**

```bash
# Test health (replace with your actual domain)
curl https://api.yourdomain.com/health

# Test in browser
# Open: https://api.yourdomain.com/health
```

You should see the same JSON response!

### 10.3: Test from Browser Console

Open your browser console (F12) and run:

```javascript
fetch('https://api.yourdomain.com/health')
  .then(r => r.json())
  .then(console.log);

fetch('https://api.yourdomain.com/api/cars')
  .then(r => r.json())
  .then(console.log);
```

---

## Step 11: Enable Auto-Start on Boot

Make sure your backend starts automatically when the Pi reboots.

```bash
# Docker containers with "restart: unless-stopped" will auto-start
# This is already configured in docker-compose.prod.yml

# Test it:
sudo reboot

# Wait 2 minutes, then SSH back in
ssh pi@your-pi-ip

# Check if containers are running
docker ps

# Should show all 3 containers running
```

---

## Step 12: Set Up Auto-Deploy (CI/CD)

Make your backend auto-update when you push to GitHub.

### 12.1: Set Up SSH Key for GitHub Actions

**On your Raspberry Pi:**

```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -C "github-actions-deploy"

# Just press Enter for all prompts (use default location, no passphrase)

# Display your public key
cat ~/.ssh/id_ed25519.pub

# Copy this public key
```

**Add to Raspberry Pi's authorized_keys:**

```bash
# This allows GitHub Actions to SSH in
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys

# Set correct permissions
chmod 600 ~/.ssh/authorized_keys
```

**Display your private key:**

```bash
cat ~/.ssh/id_ed25519

# Copy the ENTIRE output (including the BEGIN and END lines)
```

### 12.2: Add Secrets to GitHub

**On your PC (in a web browser):**

1. Go to: **https://github.com/igorcretu/BPR-BackEnd/settings/secrets/actions**
2. Click: **New repository secret**

Add these secrets:

**Secret 1: PI_HOST**
- Name: `PI_HOST`
- Value: Your Raspberry Pi's IP address (e.g., `192.168.1.100`)

**Secret 2: PI_USERNAME**
- Name: `PI_USERNAME`
- Value: `pi` (or your username)

**Secret 3: PI_SSH_KEY**
- Name: `PI_SSH_KEY`
- Value: Paste the private key from `cat ~/.ssh/id_ed25519`

**Secret 4: PI_PORT** (optional)
- Name: `PI_PORT`
- Value: `22` (default SSH port)

### 12.3: Test Auto-Deploy

**On your PC:**

```bash
# Make a small change to your backend
cd BPR-BackEnd
echo "# Test deployment" >> README.md

# Commit and push
git add .
git commit -m "Test auto-deployment"
git push origin main
```

**Watch the deployment:**

1. Go to: **https://github.com/igorcretu/BPR-BackEnd/actions**
2. You should see your workflow running
3. Wait for it to complete (~2-3 minutes)

**On your Raspberry Pi:**

```bash
# Check if deployment happened
cd ~/projects/BPR-BackEnd
git log -1

# Should show your latest commit

# Check if containers restarted
docker compose -f docker-compose.prod.yml ps
```

---

## Step 13: Connect Your Frontend

Now that your backend is running, connect your Netlify frontend.

### 13.1: Update Frontend Environment Variables

**In your frontend repository:**

Update `.env.production`:
```bash
VITE_API_URL=https://api.yourdomain.com/api
```

Or in **Netlify Dashboard:**
1. Go to: Site settings → Environment variables
2. Add: 
   - Key: `VITE_API_URL`
   - Value: `https://api.yourdomain.com/api`
3. Click: **Save**
4. Trigger redeploy: Deploys → Trigger deploy

### 13.2: Test Connection

Open your Netlify site in a browser, open console (F12), and run:

```javascript
fetch('https://api.yourdomain.com/api/cars')
  .then(r => r.json())
  .then(console.log);
```

Should return your cars! 🎉

---

## 🎉 You're Done!

Your backend is now:
- ✅ Running on Raspberry Pi
- ✅ Accessible at https://api.yourdomain.com
- ✅ Connected to your Netlify frontend
- ✅ Auto-deploying on git push
- ✅ Auto-starting on boot
- ✅ Production-ready!

---

## 📊 Daily Operations

### View Logs

```bash
ssh pi@your-pi-ip
cd ~/projects/BPR-BackEnd

# All logs
docker compose -f docker-compose.prod.yml logs -f

# Just backend
docker compose -f docker-compose.prod.yml logs -f backend

# Last 100 lines
docker compose -f docker-compose.prod.yml logs --tail=100
```

### Restart Services

```bash
# Restart everything
docker compose -f docker-compose.prod.yml restart

# Restart just backend
docker compose -f docker-compose.prod.yml restart backend

# Restart just tunnel
docker compose -f docker-compose.prod.yml restart cloudflared
```

### Update Backend Manually

```bash
cd ~/projects/BPR-BackEnd

# Pull latest code
git pull origin main

# Pull latest Docker images
docker compose -f docker-compose.prod.yml --profile cloudflare pull

# Restart
docker compose -f docker-compose.prod.yml --profile cloudflare up -d
```

### Stop Services

```bash
# Stop all containers (but keep data)
docker compose -f docker-compose.prod.yml down

# Stop and remove data (WARNING: deletes database!)
docker compose -f docker-compose.prod.yml down -v
```

### Monitor Resources

```bash
# View resource usage
docker stats

# View disk usage
df -h

# View memory usage
free -h

# View running processes
htop  # (install with: sudo apt install htop)
```

---

## 🔧 Troubleshooting

### Backend Won't Start

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs backend

# Common issues:
# 1. Database not ready - wait 30 seconds
# 2. Port already in use - check: sudo lsof -i :5000
# 3. Out of memory - check: free -h
```

### Can't Access from Internet

```bash
# Check tunnel is running
docker compose -f docker-compose.prod.yml ps cloudflared

# Check tunnel logs
docker compose -f docker-compose.prod.yml logs cloudflared

# Should see: "Connection established"

# Check Cloudflare Dashboard
# https://one.dash.cloudflare.com/ → Tunnels
# Should show "Healthy"
```

### Database Issues

```bash
# Check database logs
docker compose -f docker-compose.prod.yml logs db

# Connect to database
docker compose -f docker-compose.prod.yml exec db \
  psql -U bpr_user -d car_prediction

# Inside psql:
\dt              # List tables
SELECT COUNT(*) FROM cars;  # Should show 30
\q              # Quit
```

### Out of Disk Space

```bash
# Check disk usage
df -h

# Clean up Docker
docker system prune -a

# Remove old images
docker image prune -a
```

### CI/CD Not Working

```bash
# Check GitHub Actions logs
# Go to: https://github.com/igorcretu/BPR-BackEnd/actions

# Check SSH connection from Pi
ssh -T pi@localhost  # Should work without password

# Check secrets in GitHub
# Settings → Secrets → Actions
# Should have: PI_HOST, PI_USERNAME, PI_SSH_KEY
```

---

## 🔐 Security Best Practices

### Change Default Password

```bash
passwd
# Choose a strong password!
```

### Update Regularly

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Docker images
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### Enable Firewall (Optional)

```bash
# Install ufw
sudo apt install ufw

# Allow SSH
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### Backup Database

```bash
# Backup database
docker compose -f docker-compose.prod.yml exec db \
  pg_dump -U bpr_user car_prediction > backup_$(date +%Y%m%d).sql

# Restore database
cat backup_20241117.sql | docker compose exec -T db \
  psql -U bpr_user car_prediction
```

---

## 📞 Quick Reference Commands

```bash
# SSH to Pi
ssh pi@your-pi-ip

# Navigate to project
cd ~/projects/BPR-BackEnd

# View status
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Restart
docker compose -f docker-compose.prod.yml restart

# Update
git pull && docker compose -f docker-compose.prod.yml pull && \
docker compose -f docker-compose.prod.yml up -d

# Stop
docker compose -f docker-compose.prod.yml down

# Test locally
curl http://localhost:5000/health

# Test publicly
curl https://api.yourdomain.com/health
```

---

## 🎯 What's Next?

1. ✅ Add your trained ML model to `app/ml/predictor.py`
2. ✅ Set up web scraping to populate database
3. ✅ Monitor your API usage in Cloudflare Dashboard
4. ✅ Set up database backups (cron job)
5. ✅ Add more features to your API

---

## 📚 Additional Resources

- **Project Documentation:** All `.md` files in your repo
- **Docker Commands:** `docker compose --help`
- **Cloudflare Dashboard:** https://one.dash.cloudflare.com/
- **GitHub Actions:** https://github.com/igorcretu/BPR-BackEnd/actions

---

**🎉 Congratulations!** Your backend is production-ready and running on your Raspberry Pi!

If you have any issues, check the troubleshooting section or the logs. Everything is containerized, so it's easy to restart or reset if needed.

**Your backend is now accessible at:** `https://api.yourdomain.com` 🚀
