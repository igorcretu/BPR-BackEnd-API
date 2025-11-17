# Cloudflare Tunnel Setup Guide

This guide will help you expose your Raspberry Pi backend to the internet securely using Cloudflare Tunnel, allowing your Netlify frontend to connect to it.

## Why Cloudflare Tunnel?

- ✅ **No port forwarding needed** - Works behind NAT/firewall
- ✅ **Free SSL/HTTPS** - Automatic certificates
- ✅ **DDoS protection** - Cloudflare's security
- ✅ **No public IP needed** - Perfect for home Raspberry Pi
- ✅ **Custom domain** - Use your own domain (e.g., api.yourdomain.com)

## Prerequisites

1. Cloudflare account (free tier works)
2. Domain name managed by Cloudflare
3. Raspberry Pi with Docker running

## Setup Steps

### 1. Install Cloudflared on Raspberry Pi

```bash
# SSH into your Raspberry Pi
ssh pi@your-pi-ip

# Download cloudflared for ARM64 (Raspberry Pi 5)
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb

# Install it
sudo dpkg -i cloudflared-linux-arm64.deb

# Verify installation
cloudflared --version
```

### 2. Authenticate with Cloudflare

```bash
# This will open a browser window for authentication
cloudflared tunnel login
```

This creates a certificate file at `~/.cloudflared/cert.pem`

### 3. Create a Tunnel

```bash
# Create a tunnel named "bpr-backend"
cloudflared tunnel create bpr-backend

# Note the Tunnel ID that's displayed (you'll need it)
# Example output: Created tunnel bpr-backend with id xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### 4. Create Tunnel Configuration

Create the config file:

```bash
mkdir -p ~/.cloudflared
nano ~/.cloudflared/config.yml
```

Add this configuration (replace `TUNNEL_ID` with your actual tunnel ID):

```yaml
tunnel: TUNNEL_ID
credentials-file: /home/pi/.cloudflared/TUNNEL_ID.json

ingress:
  # Route for your API
  - hostname: api.yourdomain.com
    service: http://localhost:5000
    originRequest:
      noTLSVerify: true
  
  # Catch-all rule (required)
  - service: http_status:404
```

**Important:** Replace:
- `TUNNEL_ID` with your actual tunnel ID
- `api.yourdomain.com` with your actual subdomain

### 5. Configure DNS

```bash
# Create DNS record pointing to your tunnel
cloudflared tunnel route dns bpr-backend api.yourdomain.com
```

This automatically creates a CNAME record in Cloudflare DNS.

### 6. Run the Tunnel

#### Option A: Run manually (for testing)

```bash
cloudflared tunnel run bpr-backend
```

#### Option B: Run as a service (recommended for production)

```bash
# Install as a system service
sudo cloudflared service install

# Start the service
sudo systemctl start cloudflared

# Enable on boot
sudo systemctl enable cloudflared

# Check status
sudo systemctl status cloudflared

# View logs
sudo journalctl -u cloudflared -f
```

### 7. Update Backend CORS Settings

The backend needs to accept requests from your Netlify frontend. This is already configured in the code with `CORS(app)`, but you can make it more specific:

In your `.env` file on Raspberry Pi:

```bash
# Add your Netlify domain
ALLOWED_ORIGINS=https://your-site.netlify.app,https://api.yourdomain.com
```

### 8. Test the Connection

From your local machine:

```bash
# Health check
curl https://api.yourdomain.com/health

# Get cars
curl https://api.yourdomain.com/api/cars
```

## Update Frontend to Use Cloudflare Tunnel

In your frontend `.env` file (Netlify):

```bash
# Before (won't work from Netlify)
VITE_API_URL=http://192.168.1.100:5000/api

# After (works from anywhere!)
VITE_API_URL=https://api.yourdomain.com/api
```

## Complete Docker Compose with Cloudflare

You can also run Cloudflare Tunnel in Docker. Here's the updated `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  db:
    image: postgres:16-alpine
    container_name: bpr-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-car_prediction}
      POSTGRES_USER: ${POSTGRES_USER:-bpr_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - bpr-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-bpr_user}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Flask Backend
  backend:
    image: ghcr.io/igorcretu/bpr-backend:latest
    container_name: bpr-flask
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    environment:
      FLASK_APP: app.main
      FLASK_ENV: production
      DATABASE_URL: postgresql://${POSTGRES_USER:-bpr_user}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB:-car_prediction}
      SECRET_KEY: ${SECRET_KEY}
    ports:
      - "5000:5000"
    networks:
      - bpr-network
    volumes:
      - ./models:/app/models
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Cloudflare Tunnel (optional - run as Docker container)
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: bpr-cloudflared
    restart: unless-stopped
    command: tunnel --no-autoupdate run
    depends_on:
      - backend
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
    networks:
      - bpr-network

volumes:
  postgres_data:

networks:
  bpr-network:
    driver: bridge
```

To use the Docker version, get your tunnel token:

```bash
cloudflared tunnel token bpr-backend
```

Add it to your `.env`:

```bash
CLOUDFLARE_TUNNEL_TOKEN=your-token-here
```

## Security Best Practices

### 1. Enable HTTPS Only

In Cloudflare Dashboard:
- Go to SSL/TLS → Overview
- Set to "Full" or "Full (strict)"

### 2. Add Rate Limiting (Optional)

In Cloudflare Dashboard:
- Security → WAF
- Create rate limiting rules

### 3. Configure Firewall Rules

Block access except from Cloudflare:

```bash
# On Raspberry Pi, allow only Cloudflare IPs and local network
sudo ufw allow from 173.245.48.0/20
sudo ufw allow from 103.21.244.0/22
sudo ufw allow from 103.22.200.0/22
# ... add all Cloudflare IP ranges
# See: https://www.cloudflare.com/ips/
```

## Troubleshooting

### Tunnel not connecting

```bash
# Check tunnel status
cloudflared tunnel info bpr-backend

# Check service logs
sudo journalctl -u cloudflared -f

# Test local backend first
curl http://localhost:5000/health
```

### CORS errors

Check that CORS is enabled in your Flask app (already done in main.py):

```python
from flask_cors import CORS
app = Flask(__name__)
CORS(app)  # Allows all origins
```

For production, specify allowed origins:

```python
CORS(app, origins=["https://your-site.netlify.app"])
```

### DNS not resolving

```bash
# Check DNS record
dig api.yourdomain.com

# Should show a CNAME to <tunnel-id>.cfargotunnel.com
```

## Testing Checklist

- [ ] Tunnel is running: `sudo systemctl status cloudflared`
- [ ] Backend is healthy: `curl http://localhost:5000/health`
- [ ] DNS resolves: `dig api.yourdomain.com`
- [ ] HTTPS works: `curl https://api.yourdomain.com/health`
- [ ] Frontend can connect from Netlify
- [ ] CORS headers present in response

## Monitoring

```bash
# View tunnel logs
sudo journalctl -u cloudflared -f

# View backend logs
cd ~/bpr-backend
docker compose logs -f backend

# Check tunnel metrics in Cloudflare Dashboard
# Go to: Zero Trust → Access → Tunnels → bpr-backend
```

## Alternative: Cloudflare Tunnel Token (Simpler Setup)

If you prefer a simpler setup without installing cloudflared:

1. Create tunnel in Cloudflare Dashboard: https://one.dash.cloudflare.com/
2. Go to Zero Trust → Access → Tunnels
3. Create a tunnel
4. Copy the token
5. Use the Docker compose setup above with the token

This is actually **easier** and recommended!

## Summary

Once set up:

1. **Your Raspberry Pi** runs the backend on `localhost:5000`
2. **Cloudflare Tunnel** exposes it as `https://api.yourdomain.com`
3. **Your Netlify frontend** connects to `https://api.yourdomain.com/api`
4. **Everything is secure** with HTTPS and no open ports!

## Cost

**Completely FREE!** Cloudflare Tunnel is included in the free tier.

## Next Steps

After setup:
1. Test locally: `curl https://api.yourdomain.com/health`
2. Update frontend: `VITE_API_URL=https://api.yourdomain.com/api`
3. Deploy frontend to Netlify
4. Your app is live! 🎉
