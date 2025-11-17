# 🚀 Raspberry Pi Quick Start Card

**Print this and keep it handy!**

---

## 🎯 Your Project Details

Fill these in:

```
Raspberry Pi IP:     ___.___.___.___ 
SSH Command:         ssh pi@___.___.___.___
Project Location:    ~/projects/BPR-BackEnd
Public API URL:      https://api.___________.com
Frontend URL:        https://__________.netlify.app
GitHub Repo:         https://github.com/igorcretu/BPR-BackEnd
```

---

## ⚡ Essential Commands

### Connect to Pi
```bash
ssh pi@YOUR_PI_IP
```

### Navigate to Project
```bash
cd ~/projects/BPR-BackEnd
```

### View Status
```bash
docker compose -f docker-compose.prod.yml ps
```

### View Logs (Real-time)
```bash
docker compose -f docker-compose.prod.yml logs -f
```

### Restart Everything
```bash
docker compose -f docker-compose.prod.yml restart
```

### Update & Restart
```bash
git pull && \
docker compose -f docker-compose.prod.yml pull && \
docker compose -f docker-compose.prod.yml up -d
```

### Stop Everything
```bash
docker compose -f docker-compose.prod.yml down
```

### Start Everything
```bash
docker compose -f docker-compose.prod.yml --profile cloudflare up -d
```

---

## 🧪 Test Commands

### Local Test (on Pi)
```bash
curl http://localhost:5000/health
```

### Public Test (from anywhere)
```bash
curl https://api.yourdomain.com/health
```

### Check Disk Space
```bash
df -h
```

### Check Memory
```bash
free -h
```

---

## 🔧 Common Fixes

### Backend not responding
```bash
docker compose -f docker-compose.prod.yml restart backend
```

### Tunnel not working
```bash
docker compose -f docker-compose.prod.yml restart cloudflared
docker compose -f docker-compose.prod.yml logs cloudflared
```

### Database issues
```bash
docker compose -f docker-compose.prod.yml restart db
docker compose -f docker-compose.prod.yml logs db
```

### Out of space
```bash
docker system prune -a
```

### Complete reset
```bash
cd ~/projects/BPR-BackEnd
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml --profile cloudflare up -d
```

---

## 📊 Monitoring URLs

- **Cloudflare Dashboard:** https://one.dash.cloudflare.com/
- **GitHub Actions:** https://github.com/igorcretu/BPR-BackEnd/actions
- **Your API:** https://api.yourdomain.com/health
- **Your Frontend:** https://your-site.netlify.app

---

## 📚 Documentation Files

All in `~/projects/BPR-BackEnd/`:

- **RASPBERRY_PI_DEPLOYMENT.md** - Complete guide
- **DEPLOYMENT_CHECKLIST.md** - Step-by-step checklist  
- **TROUBLESHOOTING.md** - Problem solutions
- **QUICK_REFERENCE.md** - Command reference
- **API_DOCUMENTATION.md** - All API endpoints

---

## 🆘 Emergency Contacts

**If something breaks:**

1. Check logs: `docker compose logs -f`
2. Check TROUBLESHOOTING.md
3. Restart: `docker compose restart`
4. Reboot Pi: `sudo reboot`

---

## ✅ Health Check

Run this to verify everything:

```bash
cd ~/projects/BPR-BackEnd

echo "=== Container Status ==="
docker compose -f docker-compose.prod.yml ps

echo -e "\n=== Local Health Check ==="
curl -s http://localhost:5000/health | head -n 3

echo -e "\n=== Public Health Check ==="
curl -s https://api.yourdomain.com/health | head -n 3

echo -e "\n=== Disk Space ==="
df -h | grep "/$"

echo -e "\n=== Memory ==="
free -h | grep "Mem:"
```

All should show ✅ green/healthy.

---

## 🎓 First Deployment Steps

1. SSH: `ssh pi@your-pi-ip`
2. Update: `sudo apt update && sudo apt upgrade -y`
3. Docker: `curl -fsSL https://get.docker.com | sh`
4. Clone: `git clone https://github.com/igorcretu/BPR-BackEnd.git`
5. Setup: Follow RASPBERRY_PI_DEPLOYMENT.md
6. Done! 🎉

---

**Keep this card for quick reference!**

**Full guide:** `RASPBERRY_PI_DEPLOYMENT.md`
