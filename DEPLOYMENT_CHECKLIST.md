# ✅ Raspberry Pi Deployment Checklist

Print this out and check off as you go!

---

## Before You Start

- [ ] Raspberry Pi 5 is set up and connected to internet
- [ ] You know your Pi's IP address: `___.___.___.___`
- [ ] You can SSH to your Pi: `ssh pi@your-pi-ip`
- [ ] You have a Cloudflare account
- [ ] You have a domain in Cloudflare

---

## Step 1: Initial Setup (5 min)

```bash
ssh pi@your-pi-ip
```

- [ ] Connected via SSH
- [ ] Changed default password: `passwd`
- [ ] Updated system: `sudo apt update && sudo apt upgrade -y`

---

## Step 2: Install Docker (5 min)

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
sudo apt-get install docker-compose-plugin -y
exit
```

- [ ] Docker installed
- [ ] Docker Compose installed
- [ ] Logged out and back in
- [ ] Verified: `docker --version` works

---

## Step 3: Clone Repository (2 min)

```bash
mkdir -p ~/projects && cd ~/projects
git clone https://github.com/igorcretu/BPR-BackEnd.git
cd BPR-BackEnd
```

- [ ] Repository cloned
- [ ] In project directory: `~/projects/BPR-BackEnd`

---

## Step 4: Create .env File (5 min)

```bash
cp .env.example .env
nano .env
```

Fill in:
- [ ] `POSTGRES_PASSWORD=` (generate with: `openssl rand -base64 32`)
- [ ] `SECRET_KEY=` (generate with: `openssl rand -base64 64`)
- [ ] `ALLOWED_ORIGINS=https://your-site.netlify.app`
- [ ] `CLOUDFLARE_TUNNEL_TOKEN=` (get from Step 5)

---

## Step 5: Setup Cloudflare Tunnel (5 min)

**On your PC - Browser:**

1. Go to: https://one.dash.cloudflare.com/
2. Access → Tunnels → Create tunnel
3. Name: `bpr-backend`

- [ ] Tunnel created
- [ ] Token copied (starts with `eyJ...`)

4. Public Hostname:
   - Subdomain: `api`
   - Domain: `yourdomain.com`
   - Service: `HTTP` → `backend:5000`

- [ ] Public hostname configured
- [ ] Token added to `.env` on Raspberry Pi

---

## Step 6: GitHub Container Registry (3 min)

**On your PC - Browser:**

1. https://github.com/settings/tokens
2. Generate new token (classic)
3. Select: `read:packages`

- [ ] Token generated: `ghp_xxxxxxxxxxxx`

**On Raspberry Pi:**

```bash
echo "ghp_xxxxxxxxxxxx" | docker login ghcr.io -u igorcretu --password-stdin
```

- [ ] Login succeeded

---

## Step 7: Start Backend (5 min)

```bash
cd ~/projects/BPR-BackEnd
docker compose -f docker-compose.prod.yml --profile cloudflare up -d
```

- [ ] Containers starting (first time takes 2-5 minutes)
- [ ] Check status: `docker compose -f docker-compose.prod.yml ps`
- [ ] All 3 containers running (postgres, flask, cloudflared)

---

## Step 8: Verify (5 min)

**Test locally on Pi:**

```bash
curl http://localhost:5000/health
curl http://localhost:5000/api/cars
```

- [ ] Health endpoint works
- [ ] Cars endpoint returns 30 cars

**Test publicly from PC:**

```bash
curl https://api.yourdomain.com/health
curl https://api.yourdomain.com/api/cars
```

- [ ] Public access works
- [ ] Data is returned

---

## Step 9: Setup Auto-Deploy (10 min)

**On Raspberry Pi:**

```bash
ssh-keygen -t ed25519 -C "github-actions"
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
cat ~/.ssh/id_ed25519  # Copy this
```

- [ ] SSH key generated
- [ ] Private key copied

**On your PC - Browser:**

Go to: https://github.com/igorcretu/BPR-BackEnd/settings/secrets/actions

Add secrets:
- [ ] `PI_HOST` = `192.168.1.XXX` (your Pi's IP)
- [ ] `PI_USERNAME` = `pi`
- [ ] `PI_SSH_KEY` = (paste private key)
- [ ] `PI_PORT` = `22`

**Test:**

```bash
# On your PC
cd BPR-BackEnd
echo "# Test" >> README.md
git add . && git commit -m "Test deploy" && git push
```

- [ ] GitHub Actions workflow runs
- [ ] Deployment succeeds
- [ ] Changes appear on Pi

---

## Step 10: Connect Frontend (5 min)

**Update frontend .env:**

```bash
VITE_API_URL=https://api.yourdomain.com/api
```

**Or in Netlify Dashboard:**
- Site settings → Environment variables
- Add: `VITE_API_URL` = `https://api.yourdomain.com/api`

- [ ] Frontend environment variable updated
- [ ] Frontend redeployed
- [ ] Frontend can fetch from API

---

## 🎉 Final Verification

- [ ] Backend running on Pi: `docker compose ps`
- [ ] Local access works: `curl http://localhost:5000/health`
- [ ] Public access works: `curl https://api.yourdomain.com/health`
- [ ] Frontend connects successfully
- [ ] Auto-deploy works (push to GitHub → updates Pi)
- [ ] Auto-start works (reboot Pi → containers start automatically)

---

## 📊 Your Setup

**Fill in your details:**

- Raspberry Pi IP: `___.___.___`.___
- Public API URL: `https://api.___________.com`
- Netlify Frontend: `https://__________.netlify.app`
- GitHub Repo: `https://github.com/igorcretu/BPR-BackEnd`

---

## 🔧 Common Commands

Save these for daily use:

```bash
# SSH to Pi
ssh pi@YOUR_PI_IP

# Navigate to project
cd ~/projects/BPR-BackEnd

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Restart
docker compose -f docker-compose.prod.yml restart

# Update manually
git pull && docker compose -f docker-compose.prod.yml pull && \
docker compose -f docker-compose.prod.yml up -d

# Stop
docker compose -f docker-compose.prod.yml down
```

---

## ❓ Problems?

See: **RASPBERRY_PI_DEPLOYMENT.md** - Complete troubleshooting guide

**Most common issues:**

1. **Can't connect via SSH** → Check Pi's IP address
2. **Docker permission denied** → Logout and login again after adding to docker group
3. **Tunnel not working** → Check token in .env, view logs: `docker compose logs cloudflared`
4. **Frontend can't connect** → Check CORS in .env: `ALLOWED_ORIGINS`
5. **Out of space** → Clean up: `docker system prune -a`

---

## 📞 Quick Help

- Full guide: `RASPBERRY_PI_DEPLOYMENT.md`
- Quick commands: `QUICK_REFERENCE.md`
- API docs: `API_DOCUMENTATION.md`
- Cloudflare setup: `DOCKER_CLOUDFLARE_SETUP.md`

---

**Total Time:** ~45 minutes
**Difficulty:** ⭐⭐☆☆☆ (Easy)

**🎉 Once done, you have a production-ready backend running on your Raspberry Pi!**
