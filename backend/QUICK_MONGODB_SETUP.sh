#!/bin/bash
# Quick MongoDB Setup Script
# Ensures MongoDB is ready to store emails and files (no backup needed)

set -e

echo "=========================================="
echo "MongoDB Setup - Ready Database for Storage"
echo "=========================================="
echo ""

# Check if we're on the server
if [ ! -d "/root/graohen_os" ]; then
    echo "⚠️  This script should be run on the server"
    echo "   Expected directory: /root/graohen_os"
    exit 1
fi

cd /root/graohen_os/backend/py-service

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "⚠️  Virtual environment not found. Creating..."
    python3.11 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# Run MongoDB setup script
echo "🔧 Setting up MongoDB collections and indexes..."
echo ""

python3 scripts/setup_mongodb.py

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ MongoDB is ready to store data!"
    echo "=========================================="
    echo ""
    echo "Collections ready:"
    echo "  - emails (for encrypted email storage)"
    echo "  - files (for encrypted file storage)"
    echo ""
    echo "You can now use the email and drive APIs!"
else
    echo ""
    echo "❌ Setup failed. Check the error messages above."
    exit 1
fi
