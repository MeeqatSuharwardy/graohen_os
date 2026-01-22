#!/bin/bash
# Fix Frontend Setup - Install dependencies and configure environment

set -e

echo "=========================================="
echo "Fixing Frontend Setup"
echo "=========================================="

# Navigate to frontend directory
cd "$(dirname "$0")/frontend"

# Check if pnpm is installed
if ! command -v pnpm &> /dev/null; then
    echo "Installing pnpm..."
    npm install -g pnpm
fi

echo "Installing dependencies..."
pnpm install

echo "Creating .env file for web-flasher..."
mkdir -p apps/web-flasher
echo "VITE_API_BASE_URL=http://localhost:8000" > apps/web-flasher/.env

echo ""
echo "=========================================="
echo "✓ Frontend setup complete!"
echo "=========================================="
echo ""
echo "To start the frontend, run:"
echo "  cd frontend"
echo "  pnpm --filter @flashdash/web-flasher dev"
echo ""
echo "Or use the start script:"
echo "  ./start-frontend.sh"
echo ""
