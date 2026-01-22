#!/bin/bash
# Setup Electron App for Local Development

set -e

echo "=========================================="
echo "Setting up Electron App for Development"
echo "=========================================="

# Navigate to desktop package directory
DESKTOP_DIR="frontend/packages/desktop"

if [ ! -d "$DESKTOP_DIR" ]; then
    echo "Error: Desktop package directory not found!"
    exit 1
fi

cd "$DESKTOP_DIR"

# Create or update .env file for local development
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    echo "VITE_API_BASE_URL=http://localhost:8000" > .env
    echo "✓ Created .env file with local backend URL"
else
    echo "✓ .env file already exists"
    CURRENT_URL=$(grep "VITE_API_BASE_URL" .env | cut -d '=' -f2 || echo "")
    if [ "$CURRENT_URL" != "http://localhost:8000" ]; then
        echo "Current API URL: $CURRENT_URL"
        echo "Updating to local development URL..."
        # Backup existing .env
        cp .env .env.backup
        # Update with local URL
        if grep -q "VITE_API_BASE_URL" .env; then
            sed -i '' 's|VITE_API_BASE_URL=.*|VITE_API_BASE_URL=http://localhost:8000|' .env
        else
            echo "VITE_API_BASE_URL=http://localhost:8000" >> .env
        fi
        echo "✓ Updated .env file (backup saved as .env.backup)"
        echo "  To restore production URL, run: mv .env.backup .env"
    else
        echo "✓ .env file already configured for local development"
    fi
fi

echo ""
echo "Current .env configuration:"
cat .env

echo ""
echo "=========================================="
echo "✓ Electron app setup complete!"
echo "=========================================="
echo ""
echo "To start the Electron app, run from project root:"
echo "  pnpm run dev"
echo ""
echo "Or from frontend directory:"
echo "  cd frontend"
echo "  pnpm dev"
echo ""
echo "Make sure the backend is running on http://localhost:8000"
echo ""
