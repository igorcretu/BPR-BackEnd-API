# Frontend Integration Guide

How to connect your React frontend (Netlify) to the Flask backend (Raspberry Pi) using Cloudflare Tunnel.

## Overview

```
┌─────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│                 │         │                  │         │                  │
│  React Frontend │────────▶│  Cloudflare      │────────▶│  Raspberry Pi 5  │
│  (Netlify)      │  HTTPS  │  Tunnel          │  HTTP   │  (Flask Backend) │
│                 │         │                  │         │                  │
└─────────────────┘         └──────────────────┘         └──────────────────┘
  your-site.netlify.app     api.yourdomain.com            localhost:5000
```

## Setup Steps

### 1. Backend Setup (Raspberry Pi)

Follow [CLOUDFLARE_TUNNEL_SETUP.md](CLOUDFLARE_TUNNEL_SETUP.md) to:
1. Install Cloudflare Tunnel on your Raspberry Pi
2. Create and configure the tunnel
3. Point `api.yourdomain.com` to your Pi
4. Start the backend and tunnel

**Test the backend:**
```bash
curl https://api.yourdomain.com/health
```

### 2. Frontend Setup (Netlify)

#### Update Environment Variables

In your frontend repository, update `.env`:

```bash
# .env (for local development)
VITE_API_URL=http://localhost:5000/api

# .env.production (for Netlify)
VITE_API_URL=https://api.yourdomain.com/api
```

Or set it directly in Netlify dashboard:
1. Go to Site settings → Environment variables
2. Add: `VITE_API_URL` = `https://api.yourdomain.com/api`

#### Update API Service

Your `src/services/api.ts` should already be configured:

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5000/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
});

export default api;
```

#### Test API Calls

```typescript
// src/services/api.ts
export const carApi = {
  // Get all cars
  getCars: async (params = {}) => {
    const response = await api.get('/cars', { params });
    return response.data;
  },
  
  // Get car by ID
  getCarById: async (id: string) => {
    const response = await api.get(`/cars/${id}`);
    return response.data;
  },
  
  // Predict price
  predictPrice: async (carData: any) => {
    const response = await api.post('/predict', carData);
    return response.data;
  },
  
  // Get brands
  getBrands: async () => {
    const response = await api.get('/brands');
    return response.data;
  },
  
  // Get statistics
  getStats: async () => {
    const response = await api.get('/stats');
    return response.data;
  },
};
```

### 3. CORS Configuration

#### Backend (Already Configured)

The backend is configured to accept requests from your frontend:

```python
# In app/main.py
allowed_origins = os.getenv('ALLOWED_ORIGINS', '*')
CORS(app, origins=allowed_origins, supports_credentials=True)
```

#### Production CORS Settings

On your Raspberry Pi, update `.env`:

```bash
# .env on Raspberry Pi
ALLOWED_ORIGINS=https://your-site.netlify.app,https://api.yourdomain.com
```

Then restart:
```bash
docker compose -f docker-compose.prod.yml restart backend
```

### 4. Testing the Connection

#### From Your Local Machine

```bash
# Test health
curl https://api.yourdomain.com/health

# Test API endpoint
curl https://api.yourdomain.com/api/cars
```

#### From Frontend (in Browser Console)

```javascript
// Test in browser console on your Netlify site
fetch('https://api.yourdomain.com/health')
  .then(r => r.json())
  .then(console.log);

fetch('https://api.yourdomain.com/api/cars')
  .then(r => r.json())
  .then(console.log);
```

### 5. Example React Components

#### Fetch Cars

```typescript
// src/components/CarList.tsx
import { useState, useEffect } from 'react';
import { carApi } from '../services/api';

function CarList() {
  const [cars, setCars] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCars = async () => {
      try {
        const data = await carApi.getCars();
        setCars(data.cars);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchCars();
  }, []);

  if (loading) return <div>Loading cars...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <h2>Available Cars</h2>
      {cars.map((car: any) => (
        <div key={car.id}>
          <h3>{car.brand} {car.model}</h3>
          <p>{car.year} - {car.price} DKK</p>
        </div>
      ))}
    </div>
  );
}

export default CarList;
```

#### Predict Car Price

```typescript
// src/components/PricePrediction.tsx
import { useState } from 'react';
import { carApi } from '../services/api';

function PricePrediction() {
  const [formData, setFormData] = useState({
    brand: '',
    model: '',
    year: 2020,
    mileage: 50000,
    fuel_type: 'Petrol',
    transmission: 'Manual',
    body_type: 'Sedan',
  });
  const [prediction, setPrediction] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const result = await carApi.predictPrice(formData);
      setPrediction(result);
    } catch (error) {
      console.error('Prediction failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>Predict Car Price</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Brand"
          value={formData.brand}
          onChange={(e) => setFormData({...formData, brand: e.target.value})}
          required
        />
        <input
          type="text"
          placeholder="Model"
          value={formData.model}
          onChange={(e) => setFormData({...formData, model: e.target.value})}
          required
        />
        {/* Add more fields */}
        <button type="submit" disabled={loading}>
          {loading ? 'Predicting...' : 'Predict Price'}
        </button>
      </form>

      {prediction && (
        <div>
          <h3>Predicted Price: {prediction.predicted_price} DKK</h3>
          <p>Confidence: {prediction.confidence}%</p>
          <p>Range: {prediction.price_range.min} - {prediction.price_range.max} DKK</p>
        </div>
      )}
    </div>
  );
}

export default PricePrediction;
```

## Deployment Checklist

- [ ] **Backend Running:** `docker compose ps` shows all services up
- [ ] **Cloudflare Tunnel Active:** `sudo systemctl status cloudflared`
- [ ] **Backend Accessible:** `curl https://api.yourdomain.com/health`
- [ ] **CORS Configured:** `ALLOWED_ORIGINS` set in backend `.env`
- [ ] **Frontend ENV Set:** `VITE_API_URL` configured in Netlify
- [ ] **Frontend Deployed:** Latest code pushed to Netlify
- [ ] **API Calls Working:** Test from frontend in production

## Troubleshooting

### CORS Errors

**Symptom:** Console shows CORS policy errors

**Solution:**
1. Check backend `.env` has correct `ALLOWED_ORIGINS`
2. Restart backend: `docker compose -f docker-compose.prod.yml restart backend`
3. Check response headers: `curl -I https://api.yourdomain.com/api/cars`

### Connection Refused

**Symptom:** `ERR_CONNECTION_REFUSED` or timeout

**Solution:**
1. Check tunnel is running: `sudo systemctl status cloudflared`
2. Check backend is running: `docker compose ps`
3. Test locally first: `curl http://localhost:5000/health`

### 404 Not Found

**Symptom:** API returns 404 for all endpoints

**Solution:**
1. Check `VITE_API_URL` includes `/api` at the end
2. Verify endpoints in API_DOCUMENTATION.md
3. Check backend logs: `docker compose logs backend`

### SSL Certificate Errors

**Symptom:** SSL/TLS certificate errors

**Solution:**
1. Check Cloudflare SSL/TLS settings (should be "Full")
2. Verify DNS is pointing to Cloudflare
3. Wait a few minutes for SSL to provision

## Performance Tips

### Enable Caching

Add caching headers in backend responses for static data:

```python
@app.after_request
def add_cache_headers(response):
    if request.path.startswith('/api/brands') or request.path.startswith('/api/filters'):
        response.headers['Cache-Control'] = 'public, max-age=3600'  # 1 hour
    return response
```

### Use React Query

Install React Query for better data management:

```bash
npm install @tanstack/react-query
```

```typescript
import { useQuery } from '@tanstack/react-query';

function CarList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['cars'],
    queryFn: () => carApi.getCars(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Component code...
}
```

## Security Best Practices

1. **Use HTTPS Only:** Always use `https://` for production API calls
2. **Validate Input:** Add validation on frontend before sending to API
3. **Handle Errors:** Implement proper error handling for all API calls
4. **Rate Limiting:** Consider adding rate limiting on frontend
5. **API Keys:** If you add authentication later, store keys securely

## Monitoring

### Check Backend Health

Create a health check component:

```typescript
import { useEffect, useState } from 'react';

function HealthCheck() {
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    fetch(import.meta.env.VITE_API_URL.replace('/api', '/health'))
      .then(r => r.json())
      .then(setHealth)
      .catch(console.error);
  }, []);

  return health ? (
    <div style={{position: 'fixed', bottom: 10, right: 10, padding: 10, background: health.status === 'healthy' ? 'green' : 'red', color: 'white'}}>
      API: {health.status}
    </div>
  ) : null;
}
```

## Summary

Once everything is set up:

1. **Your Raspberry Pi** runs Flask backend at `localhost:5000`
2. **Cloudflare Tunnel** exposes it as `https://api.yourdomain.com`
3. **Your Netlify frontend** connects to `https://api.yourdomain.com/api`
4. **Users** access your site at `https://your-site.netlify.app`

Everything works seamlessly with HTTPS, no port forwarding, and Cloudflare's security! 🎉

## Need Help?

- Backend issues: Check `docker compose logs backend`
- Tunnel issues: Check `sudo journalctl -u cloudflared -f`
- Frontend issues: Check browser console
- API Reference: See [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
