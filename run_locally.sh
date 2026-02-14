#!/bin/bash

# FIWB AI - Local Development Launcher (MacOS/Linux)

echo "==================================="
echo "  FIWB AI: Starting Locally"
echo "==================================="

# 1. Backend Setup & Run
echo ""
echo "[1/3] Starting Backend Server..."
cd fiwb-backend

if [ ! -d "venv" ]; then
    echo "   Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "   Installing dependencies..."
pip install -r requirements.txt

echo "   Backend running on http://127.0.0.1:8001"
# Run backend in background
python3 -m uvicorn app.main:app --reload --port 8001 > backend.log 2>&1 &
BACKEND_PID=$!

# 2. Configure Frontend for Localhost
echo ""
echo "[2/3] Configuring Frontend..."
cd ../fiwb-frontend
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8001" > .env.local
echo "   Updated .env.local to point to localhost."

# 3. Frontend Setup & Run
echo ""
echo "[3/3] Starting Frontend Server..."
if [ ! -d "node_modules" ]; then
    echo "   Installing dependencies..."
    npm install
fi

echo "   Frontend running on http://localhost:3000"
# Run frontend in background
npm run dev > frontend.log 2>&1 &
FRONTEND_PID=$!

echo ""
echo "==================================="
echo "  SYSTEM RUNNING LOCALLY"
echo "==================================="
echo ""
echo "Backend:  http://127.0.0.1:8001 (PID: $BACKEND_PID)"
echo "Frontend: http://localhost:3000 (PID: $FRONTEND_PID)"
echo ""
echo "Logs are being written to fiwb-backend/backend.log and fiwb-frontend/frontend.log"
echo "To stop the servers, run: kill $BACKEND_PID $FRONTEND_PID"
echo ""

# Keep the script running to prevent immediate exit if desired, 
# but usually we want to return control to the terminal.
# wait
