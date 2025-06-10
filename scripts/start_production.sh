#!/bin/bash
# Production startup script for CineAI

set -e

echo "🚀 Starting CineAI Production Services"
echo "========================================"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"

# Activate virtual environment
if [ -f "moodenv/bin/activate" ]; then
    source moodenv/bin/activate
elif [ -f "../moodenv/bin/activate" ]; then
    source ../moodenv/bin/activate
elif [ -f "/Users/aravindmohan/moodenv/bin/activate" ]; then
    source /Users/aravindmohan/moodenv/bin/activate
else
    echo "⚠️  Virtual environment not found. Make sure to activate it manually."
fi

echo ""
echo "📊 Checking Models..."
if [ ! -f "Checkpoints/recommendation_engine_ensemble.json" ]; then
    echo "❌ Model files not found in Checkpoints/"
    echo "   Please ensure models are trained and checkpoints are extracted."
    exit 1
fi
echo "✅ Models found"

echo ""
echo "📊 Checking Database..."
if [ ! -f "cineai.db" ]; then
    echo "⚠️  Database file not found. It will be created on first startup."
fi

echo ""
echo "🔧 Starting Backend Server..."
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"
echo "   API: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"

echo ""
echo "🎨 Starting Frontend Server..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID)"
echo "   URL: http://localhost:5173"

echo ""
echo "========================================"
echo "✅ CineAI is running!"
echo ""
echo "📝 Services:"
echo "   - Backend API: http://localhost:8000"
echo "   - Frontend: http://localhost:5173"
echo "   - API Docs: http://localhost:8000/docs"
echo ""
echo "🛑 To stop:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "📊 To view monitoring report:"
echo "   python monitor_recommendations.py"
echo "========================================"

# Wait for user interrupt
trap "echo ''; echo '🛑 Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait

