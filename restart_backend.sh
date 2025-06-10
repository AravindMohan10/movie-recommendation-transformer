#!/bin/bash
# Quick backend restart script

cd "$(dirname "$0")/backend"

# Try to activate virtual environment (adjust path if needed)
if [ -f "../moodenv/bin/activate" ]; then
    source ../moodenv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "../venv/bin/activate" ]; then
    source ../venv/bin/activate
fi

# Kill any existing uvicorn processes
pkill -f "uvicorn app.main:app" 2>/dev/null

# Start the server
echo "🚀 Starting CineAI Backend..."
echo "   API: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo ""
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

