#!/bin/bash
# Start Frontend Development Server Locally (Without Docker)

set -e

echo "=========================================="
echo "Starting FlashDash Frontend"
echo "=========================================="

# Navigate to frontend directory
cd "$(dirname "$0")/frontend"

# Check if pnpm is installed
if ! command -v pnpm &> /dev/null; then
    echo "pnpm is not installed. Installing..."
    npm install -g pnpm
fi

# Install dependencies if needed
if [ ! -d "node_modules" ] || [ ! -d "apps/web-flasher/node_modules" ]; then
    echo "Installing dependencies..."
    pnpm install
fi

# Set environment variable for API URL
export VITE_API_BASE_URL=${VITE_API_BASE_URL:-http://localhost:8000}

# Create .env file in web-flasher app
mkdir -p apps/web-flasher
echo "VITE_API_BASE_URL=$VITE_API_BASE_URL" > apps/web-flasher/.env

echo "Frontend will connect to backend at: $VITE_API_BASE_URL"
echo ""
echo "Starting development server..."
echo "Press Ctrl+C to stop"
echo "=========================================="

# Start web flasher app
pnpm --filter @flashdash/web-flasher dev
