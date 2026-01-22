#!/bin/bash
# Script to start Electron app when Docker starts
# Run this locally (not in Docker) to auto-launch Electron when Docker backend is ready

set -e

BACKEND_URL="http://localhost:8000"
ELECTRON_DIR="frontend/packages/desktop"
MAX_WAIT=60
WAIT_INTERVAL=2

echo "=========================================="
echo "FlashDash Electron App Launcher"
echo "=========================================="

# Function to check if backend is ready
check_backend() {
    curl -f -s "$BACKEND_URL/health" > /dev/null 2>&1
}

# Wait for Docker backend to be ready
echo "Waiting for Docker backend to be ready..."
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if check_backend; then
        echo "✅ Backend is ready!"
        break
    fi
    echo "Waiting for backend... ($WAITED/$MAX_WAIT seconds)"
    sleep $WAIT_INTERVAL
    WAITED=$((WAITED + WAIT_INTERVAL))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "❌ Backend did not start in time"
    echo "Make sure Docker is running: docker-compose up -d"
    exit 1
fi

# Check if Electron dependencies are installed
if [ ! -d "$ELECTRON_DIR/node_modules" ]; then
    echo "Installing Electron dependencies..."
    cd "$ELECTRON_DIR"
    pnpm install
    cd - > /dev/null
fi

# Create .env file for Electron with Docker backend URL
echo "Configuring Electron to use Docker backend..."
mkdir -p "$ELECTRON_DIR"
echo "VITE_API_BASE_URL=$BACKEND_URL" > "$ELECTRON_DIR/.env"

# Start Electron app
echo "Starting Electron app..."
cd "$ELECTRON_DIR"
pnpm dev
