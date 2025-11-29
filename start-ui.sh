#!/bin/bash
# Startup script for AI Orchestrator Web UI

set -e

echo "🚀 Starting AI Orchestrator Web UI"
echo ""

# Check if backend dependencies are installed
if [ ! -d "ui/venv" ]; then
    echo "📦 Setting up backend virtual environment..."
    cd ui
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
else
    echo "✓ Backend virtual environment found"
    echo "📦 Ensuring backend dependencies are installed..."
    cd ui
    source venv/bin/activate
    pip install -r requirements.txt >/dev/null
    cd ..
fi

# Check if frontend dependencies are installed
if [ ! -d "ui/frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd ui/frontend
    npm install
    cd ../..
else
    echo "✓ Frontend dependencies found"
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

echo ""
echo "Starting servers..."
echo ""

# Start backend
cd ui
source venv/bin/activate
python app.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start frontend
cd ui/frontend
npm run dev &
FRONTEND_PID=$!
cd ../..

echo ""
echo "✅ Servers started!"
echo ""
echo "Backend:  http://localhost:5000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for user interrupt
wait
