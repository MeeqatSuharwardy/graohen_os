#!/bin/bash

# FlashDash Development Script

# Start backend in background
echo "Starting backend service..."
cd backend/py-service
source .venv/bin/activate || .venv/Scripts/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 17890 &
BACKEND_PID=$!
cd ../..

# Wait a bit for backend to start
sleep 2

# Start frontend
echo "Starting frontend..."
cd frontend
pnpm dev

# Cleanup on exit
trap "kill $BACKEND_PID 2>/dev/null" EXIT

