#!/bin/bash

# Cloudflare Tunnel Quick Setup Script for Raspberry Pi
# This script helps you set up Cloudflare Tunnel quickly

echo "========================================="
echo "Cloudflare Tunnel Setup for BPR Backend"
echo "========================================="
echo ""

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo; then
    echo "⚠️  Warning: This doesn't appear to be a Raspberry Pi"
    echo "   This script is designed for ARM64 (Raspberry Pi 5)"
    read -p "   Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if cloudflared is already installed
if command -v cloudflared &> /dev/null; then
    echo "✅ cloudflared is already installed"
    cloudflared --version
else
    echo "📦 Installing cloudflared..."
    
    # Download for ARM64
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb
    
    # Install
    sudo dpkg -i cloudflared-linux-arm64.deb
    
    # Clean up
    rm cloudflared-linux-arm64.deb
    
    echo "✅ cloudflared installed successfully"
fi

echo ""
echo "========================================="
echo "Next Steps:"
echo "========================================="
echo ""
echo "1. Authenticate with Cloudflare:"
echo "   cloudflared tunnel login"
echo ""
echo "2. Create a tunnel:"
echo "   cloudflared tunnel create bpr-backend"
echo ""
echo "3. Configure the tunnel:"
echo "   See CLOUDFLARE_TUNNEL_SETUP.md for detailed instructions"
echo ""
echo "4. Route DNS:"
echo "   cloudflared tunnel route dns bpr-backend api.yourdomain.com"
echo ""
echo "5. Run the tunnel:"
echo "   cloudflared tunnel run bpr-backend"
echo ""
echo "6. Or install as service:"
echo "   sudo cloudflared service install"
echo "   sudo systemctl start cloudflared"
echo "   sudo systemctl enable cloudflared"
echo ""
echo "📖 Full guide: CLOUDFLARE_TUNNEL_SETUP.md"
echo ""
