#!/bin/bash

echo "🚀 Starting CineAI Backend..."
echo "================================"

# Check if we're in the right directory
if [ ! -f "backend/app/main.py" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Activate moodenv (one level up from project root)
MOODENV="${MOODENV:-../moodenv}"
if [ -d "$MOODENV" ] && [ -f "$MOODENV/bin/activate" ]; then
    echo "🐍 Activating venv: $MOODENV"
    source "$MOODENV/bin/activate"
else
    echo "⚠️  moodenv not found at $MOODENV; using default python"
fi

# Build RAG index (Chroma) if missing or explicitly requested
if [ "${SKIP_RAG_BUILD:-0}" != "1" ]; then
    if [ ! -d "data/rag/chroma_db" ] || [ -n "${FORCE_RAG_BUILD}" ]; then
        echo "📚 Building RAG index (Chroma + reviews)..."
        PYTHONPATH=backend python scripts/build_rag_index.py || { echo "❌ RAG index build failed (Chroma required)."; exit 1; }
    fi
fi

# Check if Redis is running
if ! pgrep -x "redis-server" > /dev/null; then
    echo "⚠️  Redis is not running. Starting Redis..."
    redis-server --daemonize yes
    sleep 2
fi

# Check if database exists, if not create it
if [ ! -f "cineai.db" ]; then
    echo "🗄️  Initializing database..."
    cd backend
    python -c "
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath('.')))
from app.database import engine
from app.models import Base
Base.metadata.create_all(bind=engine)
print('Database initialized successfully')
"
    cd ..
fi

# Install dependencies if needed
echo "📦 Checking dependencies..."
cd backend
pip install -r ../requirements.txt > /dev/null 2>&1
cd ..

# Start the backend
echo "🌟 Starting FastAPI server..."
echo "   API will be available at: http://localhost:8000"
echo "   API docs at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000