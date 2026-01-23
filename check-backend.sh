#!/bin/bash
# Check if backend is running and accessible

echo "=========================================="
echo "Backend Status Check"
echo "=========================================="

# Check if port 8000 is listening
if lsof -i :8000 > /dev/null 2>&1; then
    echo "✓ Port 8000 is in use"
    lsof -i :8000 | grep LISTEN
else
    echo "✗ Port 8000 is not in use - backend is not running"
    echo ""
    echo "Start backend with:"
    echo "  cd backend/py-service"
    echo "  source venv/bin/activate"
    echo "  uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
    exit 1
fi

echo ""
echo "Testing endpoints..."

# Test health endpoint
echo -n "Health endpoint: "
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ OK"
    curl -s http://localhost:8000/health | head -1
else
    echo "✗ FAILED"
fi

# Test devices endpoint
echo -n "Devices endpoint: "
if curl -s http://localhost:8000/devices > /dev/null 2>&1; then
    echo "✓ OK"
    DEVICE_COUNT=$(curl -s http://localhost:8000/devices | grep -o '"serial"' | wc -l)
    echo "  Found $DEVICE_COUNT device(s)"
else
    echo "✗ FAILED"
fi

echo ""
echo "=========================================="
