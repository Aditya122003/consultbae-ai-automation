#!/usr/bin/env bash
# ConsultBae AI Automation Platform - All-in-One Startup Script
# Boots up the FastAPI audio extraction backend on port 8000 and the Angular 19 frontend on port 4200
# NOTE: set -e removed intentionally so Angular port-in-use errors do NOT kill the backend

# Change directory to the repository root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "============================================================"
echo "⚡ Starting ConsultBae AI Automation & Audio Platform"
echo "============================================================"

# Ensure MySQL is accessible and run ETL pipeline if tables are empty
echo "📊 Running ETL Ingestion Check..."
python3 -m pipeline.ingest_and_merge

# Start FastAPI Backend Server
echo "🚀 Starting FastAPI Backend Server on http://localhost:8000..."
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Trap exit signals to cleanly shut down background services
cleanup() {
    echo ""
    echo "🛑 Shutting down backend (PID $BACKEND_PID)..."
    kill $BACKEND_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM

# Start Angular Frontend — try 4200 first, fallback to 4201 if already in use
echo "🌐 Starting Angular 19 Frontend on http://localhost:4200..."
cd "$PROJECT_ROOT/frontend-angular"

if lsof -i :4200 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 4200 already in use — trying port 4201..."
    NG_CLI_ANALYTICS=false npx ng serve --port 4201 --host 0.0.0.0 || true
else
    NG_CLI_ANALYTICS=false npx ng serve --port 4200 --host 0.0.0.0 || true
fi

# Keep backend alive even if Angular exits
echo "ℹ️  Angular exited. Backend still running on http://localhost:8000 (PID $BACKEND_PID)"
wait $BACKEND_PID
