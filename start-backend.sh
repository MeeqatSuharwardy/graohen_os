#!/bin/bash
# Start Backend Server Locally (Without Docker)

set -e

echo "=========================================="
echo "Starting FlashDash Backend"
echo "=========================================="

# Navigate to backend directory
cd "$(dirname "$0")/backend/py-service"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
if [ ! -f "venv/.installed" ]; then
    echo "Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    touch venv/.installed
fi

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from env.example..."
    cp env.example .env
    echo ""
    echo "⚠️  Please edit .env file with your settings"
    echo "   For local development, you can use defaults"
    echo ""
fi

# Create required directories
mkdir -p bundles apks logs

# Start server
echo "Starting backend server on http://127.0.0.1:8000"
echo "API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo "=========================================="

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
