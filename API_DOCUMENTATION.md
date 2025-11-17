# API Documentation

Complete reference for the BPR Backend API endpoints.

Base URL: `http://localhost:5000` (development) or `http://your-pi-ip:5000` (production)

## Authentication

Currently, the API does not require authentication. This will be added in future versions.

## Response Format

All API responses follow this structure:

```json
{
  "success": true,
  "data": { ... },
  "pagination": { ... } // Only for paginated endpoints
}
```

Error responses:

```json
{
  "success": false,
  "error": "Error message here"
}
```

---

## Health & Status

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "BPR Backend API",
  "version": "1.0.0",
  "database": "connected",
  "ml_model": {
    "version": "v0.1.0-mock",
    "loaded": false,
    "type": "mock"
  }
}
```

---

## Cars

### GET /api/cars

Get all cars with optional filtering, sorting, and pagination.

**Query Parameters:**
- `page` (int, default: 1) - Page number
- `per_page` (int, default: 20, max: 100) - Items per page
- `brand` (string) - Filter by brand (partial match)
- `model` (string) - Filter by model (partial match)
- `year_min` (int) - Minimum year
- `year_max` (int) - Maximum year
- `price_min` (float) - Minimum price in DKK
- `price_max` (float) - Maximum price in DKK
- `mileage_max` (int) - Maximum mileage in km
- `fuel_type` (string) - Filter by fuel type
- `transmission` (string) - Filter by transmission type
- `body_type` (string) - Filter by body type
- `location` (string) - Filter by location (partial match)
- `sort_by` (string, default: listing_date) - Sort field
- `sort_order` (string, default: desc) - Sort order (asc/desc)

**Example Request:**
```bash
GET /api/cars?brand=Toyota&year_min=2020&page=1&per_page=10
```

**Response:**
```json
{
  "success": true,
  "cars": [
    {
      "id": "uuid",
      "brand": "Toyota",
      "model": "Corolla",
      "year": 2020,
      "mileage": 45000,
      "fuel_type": "Petrol",
      "transmission": "Manual",
      "body_type": "Sedan",
      "engine_size": 1.8,
      "horsepower": 132,
      "doors": 4,
      "seats": 5,
      "color": "Silver",
      "price": 189000.00,
      "listing_date": "2024-11-16T10:30:00",
      "location": "Copenhagen",
      "dealer_name": "AutoDanmark",
      "source_url": "https://example.com/car1"
    }
  ],
  "pagination": {
    "total": 4,
    "pages": 1,
    "current_page": 1,
    "per_page": 10,
    "has_next": false,
    "has_prev": false
  }
}
```

---

### GET /api/cars/{id}

Get specific car details by ID.

**Response:**
```json
{
  "success": true,
  "car": {
    "id": "uuid",
    "brand": "Toyota",
    "model": "Corolla",
    // ... all car fields
    "prediction": {  // If prediction exists
      "id": "uuid",
      "predicted_price": 185000.00,
      "prediction_accuracy": 96.5,
      "model_version": "v0.1.0-mock",
      "created_at": "2024-11-16T10:30:00"
    }
  }
}
```

---

### POST /api/cars

Create a new car listing (for scraping/admin use).

**Request Body:**
```json
{
  "brand": "Toyota",
  "model": "Corolla",
  "year": 2020,
  "mileage": 45000,
  "fuel_type": "Petrol",
  "transmission": "Manual",
  "body_type": "Sedan",
  "engine_size": 1.8,
  "horsepower": 132,
  "doors": 4,
  "seats": 5,
  "color": "Silver",
  "price": 189000,
  "location": "Copenhagen",
  "dealer_name": "AutoDanmark",
  "source_url": "https://example.com/car1"
}
```

**Required fields:** brand, model, year, mileage, fuel_type, transmission, body_type, price

**Response:**
```json
{
  "success": true,
  "message": "Car created successfully",
  "car": { /* created car object */ }
}
```

---

## Predictions

### POST /api/predict

Predict car price based on features.

**Request Body:**
```json
{
  "brand": "Toyota",
  "model": "Corolla",
  "year": 2020,
  "mileage": 45000,
  "fuel_type": "Hybrid",
  "transmission": "Automatic",
  "body_type": "Sedan",
  "horsepower": 122,
  "engine_size": 1.8,
  "doors": 4,
  "seats": 5
}
```

**Required fields:** brand, model, year, mileage, fuel_type, transmission, body_type

**Response:**
```json
{
  "success": true,
  "predicted_price": 212500.50,
  "currency": "DKK",
  "confidence": 92.5,
  "price_range": {
    "min": 191250.45,
    "max": 233750.55
  },
  "model_version": "v0.1.0-mock",
  "similar_cars_count": 32,
  "input_features": { /* echoed input */ }
}
```

---

### GET /api/predictions

Get prediction history with pagination.

**Query Parameters:**
- `page` (int, default: 1)
- `per_page` (int, default: 20)

**Response:**
```json
{
  "success": true,
  "predictions": [
    {
      "id": "uuid",
      "car_id": "uuid",
      "predicted_price": 185000.00,
      "actual_price": 189000.00,
      "prediction_accuracy": 97.89,
      "model_version": "v0.1.0-mock",
      "created_at": "2024-11-16T10:30:00"
    }
  ],
  "pagination": { /* pagination info */ }
}
```

---

## Filters & Options

### GET /api/brands

Get all available car brands with counts.

**Response:**
```json
{
  "success": true,
  "brands": [
    {
      "name": "Toyota",
      "count": 4
    },
    {
      "name": "Volkswagen",
      "count": 4
    }
  ]
}
```

---

### GET /api/models/{brand}

Get all models for a specific brand.

**Response:**
```json
{
  "success": true,
  "brand": "Toyota",
  "models": [
    {
      "name": "Corolla",
      "count": 2
    },
    {
      "name": "RAV4",
      "count": 1
    }
  ]
}
```

---

### GET /api/filters

Get all available filter options and ranges.

**Response:**
```json
{
  "success": true,
  "filters": {
    "fuel_types": [
      { "value": "Petrol", "count": 10 },
      { "value": "Diesel", "count": 8 },
      { "value": "Electric", "count": 5 }
    ],
    "transmissions": [
      { "value": "Automatic", "count": 15 },
      { "value": "Manual", "count": 10 }
    ],
    "body_types": [
      { "value": "SUV", "count": 12 },
      { "value": "Sedan", "count": 10 }
    ],
    "locations": [
      { "value": "Copenhagen", "count": 10 },
      { "value": "Aarhus", "count": 8 }
    ],
    "year_range": {
      "min": 2019,
      "max": 2022
    },
    "price_range": {
      "min": 139000.00,
      "max": 549000.00
    },
    "mileage_range": {
      "min": 15000,
      "max": 78000
    }
  }
}
```

---

## Statistics

### GET /api/stats

Get overall market statistics.

**Response:**
```json
{
  "success": true,
  "statistics": {
    "total_listings": 30,
    "average_price": 282500.00,
    "min_price": 139000.00,
    "max_price": 549000.00,
    "top_brands": [
      { "brand": "Toyota", "count": 4 },
      { "brand": "Volkswagen", "count": 4 }
    ],
    "fuel_distribution": [
      { "fuel_type": "Petrol", "count": 10 },
      { "fuel_type": "Diesel", "count": 8 }
    ]
  }
}
```

---

### GET /api/stats/brand/{brand}

Get statistics for a specific brand.

**Response:**
```json
{
  "success": true,
  "brand": "Toyota",
  "statistics": {
    "total_listings": 4,
    "average_price": 214500.00,
    "min_price": 165000.00,
    "max_price": 289000.00,
    "models": [
      {
        "model": "Corolla",
        "count": 2,
        "average_price": 202000.00
      },
      {
        "model": "RAV4",
        "count": 1,
        "average_price": 289000.00
      }
    ]
  }
}
```

---

## Search

### GET /api/search

Search cars by keyword (searches brand, model, and location).

**Query Parameters:**
- `q` (string, required) - Search query
- `page` (int, default: 1)
- `per_page` (int, default: 20)

**Example:**
```bash
GET /api/search?q=Toyota&page=1
```

**Response:**
```json
{
  "success": true,
  "query": "Toyota",
  "cars": [ /* array of matching cars */ ],
  "pagination": { /* pagination info */ }
}
```

---

## Scraping Logs

### GET /api/scraping/logs

Get web scraping execution logs.

**Query Parameters:**
- `page` (int, default: 1)
- `per_page` (int, default: 20)

**Response:**
```json
{
  "success": true,
  "logs": [
    {
      "id": "uuid",
      "source_name": "bilbasen.dk",
      "cars_scraped": 150,
      "success": true,
      "error_message": null,
      "started_at": "2024-11-14T10:30:00",
      "completed_at": "2024-11-14T10:45:00",
      "created_at": "2024-11-14T10:45:00"
    }
  ],
  "pagination": { /* pagination info */ }
}
```

---

## Error Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request (missing/invalid parameters)
- `404` - Not Found
- `500` - Internal Server Error

---

## Examples with cURL

```bash
# Health check
curl http://localhost:5000/health

# Get all cars
curl http://localhost:5000/api/cars

# Get cars filtered by brand
curl "http://localhost:5000/api/cars?brand=Toyota"

# Get cars with multiple filters
curl "http://localhost:5000/api/cars?brand=Toyota&year_min=2020&price_max=250000"

# Predict car price
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "brand": "Toyota",
    "model": "Corolla",
    "year": 2020,
    "mileage": 45000,
    "fuel_type": "Hybrid",
    "transmission": "Automatic",
    "body_type": "Sedan"
  }'

# Get brands
curl http://localhost:5000/api/brands

# Get models for brand
curl http://localhost:5000/api/models/Toyota

# Search
curl "http://localhost:5000/api/search?q=Electric"

# Get statistics
curl http://localhost:5000/api/stats

# Get brand statistics
curl http://localhost:5000/api/stats/brand/Toyota
```

---

## Rate Limiting

Currently, there is no rate limiting. This may be added in future versions.

---

## CORS

CORS is enabled for all origins in development. Configure appropriately for production.
