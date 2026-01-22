#!/bin/bash
set -e

echo "=========================================="
echo "Starting FlashDash services..."
echo "=========================================="

# Function to check if a service is running
check_service() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            echo "✓ $name is ready"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    
    echo "✗ $name failed to start after $max_attempts attempts"
    return 1
}

# Start nginx
echo "Starting nginx..."
nginx -t && nginx || {
    echo "✗ Failed to start nginx"
    exit 1
}
echo "✓ Nginx started"

# Start Python backend
echo "Starting Python backend..."
cd /app/backend

# Set Python path
export PYTHONPATH=/app/backend:$PYTHONPATH

# Start uvicorn in background
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /app/logs/backend.log 2>&1 &
BACKEND_PID=$!

echo "Backend PID: $BACKEND_PID"

# Wait for backend to be ready
echo "Waiting for backend to be ready..."
if ! check_service "http://localhost:8000/health" "Backend"; then
    echo "Backend logs:"
    tail -50 /app/logs/backend.log
    exit 1
fi

# Verify frontend files exist
if [ ! -d "/app/frontend/web" ] || [ -z "$(ls -A /app/frontend/web)" ]; then
    echo "⚠️  Warning: Frontend web files not found or empty"
fi

if [ ! -d "/app/frontend/web-flasher" ] || [ -z "$(ls -A /app/frontend/web-flasher)" ]; then
    echo "⚠️  Warning: Web flasher files not found or empty"
fi

echo "=========================================="
echo "All services started successfully!"
echo "=========================================="
echo "Backend API: http://localhost:8000"
echo "Frontend: http://localhost/"
echo "Web Flasher: http://localhost/flash"
echo "API Docs: http://localhost:8000/docs"
echo "=========================================="

# Keep container running and monitor processes
while true; do
    # Check if backend is still running
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo "✗ Backend process died, exiting..."
        tail -50 /app/logs/backend.log
        exit 1
    fi
    
    # Check if nginx is still running
    if ! pgrep -x nginx > /dev/null; then
        echo "✗ Nginx process died, exiting..."
        exit 1
    fi
    
    sleep 5
done
