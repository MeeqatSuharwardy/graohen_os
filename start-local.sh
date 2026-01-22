#!/bin/bash
# Start Both Backend and Frontend Locally (Without Docker)
# Opens two terminal windows/tabs

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=========================================="
echo "Starting FlashDash Locally"
echo "=========================================="

# Function to start backend in new terminal (macOS)
start_backend() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        osascript -e "tell application \"Terminal\" to do script \"cd '$SCRIPT_DIR' && ./start-backend.sh\""
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        gnome-terminal -- bash -c "cd '$SCRIPT_DIR' && ./start-backend.sh; exec bash" 2>/dev/null || \
        xterm -e "cd '$SCRIPT_DIR' && ./start-backend.sh" 2>/dev/null || \
        echo "Please run './start-backend.sh' in a separate terminal"
    else
        echo "Please run './start-backend.sh' in a separate terminal"
    fi
}

# Start backend in background or new terminal
echo "Starting backend..."
start_backend

# Wait a moment for backend to start
sleep 3

# Start frontend in current terminal
echo "Starting frontend..."
echo ""
cd "$SCRIPT_DIR"
./start-frontend.sh
