#!/bin/bash

# Start Development Script
# This script helps you quickly start the development environment

echo "========================================="
echo "BPR Backend - Development Environment"
echo "========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file. Please review and update the values."
    echo ""
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Ask if user wants to start with Cloudflare Tunnel
echo "Do you want to start with Cloudflare Tunnel? (for testing public access)"
echo "Requires CLOUDFLARE_TUNNEL_TOKEN in .env"
read -p "Start with tunnel? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Check if token exists
    if grep -q "CLOUDFLARE_TUNNEL_TOKEN=eyJ" .env; then
        echo "🐳 Starting with Cloudflare Tunnel..."
        docker compose -f docker-compose.dev.yml --profile cloudflare up -d
        TUNNEL_ENABLED=true
    else
        echo "⚠️  CLOUDFLARE_TUNNEL_TOKEN not found in .env"
        echo "   Starting without tunnel..."
        docker compose -f docker-compose.dev.yml up -d
        TUNNEL_ENABLED=false
    fi
else
    echo "🐳 Starting Docker containers (local only)..."
    docker compose -f docker-compose.dev.yml up -d
    TUNNEL_ENABLED=false
fi

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 5

# Check if backend is healthy
if curl -f http://localhost:5000/health > /dev/null 2>&1; then
    echo "✅ Backend is running!"
    echo ""
    echo "========================================="
    echo "🚀 Services are ready!"
    echo "========================================="
    echo ""
    echo "📍 Local Access:"
    echo "  API: http://localhost:5000"
    echo "  Health: http://localhost:5000/health"
    echo "  Database: localhost:5432"
    echo ""
    
    if [ "$TUNNEL_ENABLED" = true ]; then
        # Extract domain from .env if possible
        echo "🌐 Public Access (via Cloudflare Tunnel):"
        echo "  Your API should be accessible at your configured domain"
        echo "  Check Cloudflare Dashboard for tunnel status"
        echo ""
    fi
    
    echo "📝 Useful commands:"
    echo "  docker compose -f docker-compose.dev.yml logs -f        # View logs"
    echo "  docker compose -f docker-compose.dev.yml down           # Stop services"
    echo "  docker compose -f docker-compose.dev.yml down -v        # Stop and reset database"
    echo ""
    echo "📚 API Documentation: See README.md for all endpoints"
    echo ""
else
    echo "⚠️  Backend is starting... Check logs with:"
    echo "   docker compose -f docker-compose.dev.yml logs -f backend"
fi
