#!/bin/bash

# FlashDash Setup Script

set -e

echo "🚀 Setting up FlashDash..."

# Backend setup
echo "📦 Setting up Python backend..."
cd backend/py-service
python3 -m venv .venv || python -m venv .venv
source .venv/bin/activate || .venv/Scripts/activate
pip install --upgrade pip
pip install -r requirements.txt
cd ../..

# Frontend setup
echo "📦 Setting up frontend..."
cd frontend
pnpm install
cd ..

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Configure backend/.env from backend/py-service/.env.example"
echo "2. Configure frontend packages/*/.env from frontend/.env.example"
echo "3. Run 'pnpm -C frontend dev' to start frontend"
echo "4. Run 'uvicorn app.main:app --reload' in backend/py-service to start backend"

