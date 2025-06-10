#!/bin/bash

echo "🚀 Starting CineAI Backend..."
echo "================================"

# Activate virtualenv if it exists
if [ -d "moodenv" ]; then
    echo "📦 Activating virtualenv: moodenv"
    source moodenv/bin/activate
else
    echo "⚠️  Virtualenv 'moodenv' not found. Using system Python."
fi

# Check if we're in the right directory
if [ ! -f "backend/app/main.py" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Go to backend directory
cd backend

# Start the backend
echo "🌟 Starting FastAPI server..."
echo "   API will be available at: http://localhost:8000"
echo "   API docs at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

