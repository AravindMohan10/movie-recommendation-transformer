#!/bin/bash

echo "🎬 Setting up CineAI - Your Premium Movie Recommendation System"
echo "================================================================"

# Check if Python 3.8+ is installed
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
if (( $(echo "$python_version < 3.8" | bc -l) )); then
    echo "❌ Python 3.8+ is required. Current version: $python_version"
    exit 1
fi
echo "✅ Python version: $python_version"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed."
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi
echo "✅ Node.js is installed"

# Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    echo "⚠️  Redis is not installed. Installing Redis..."
    
    # Install Redis based on OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew install redis
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        sudo apt-get update
        sudo apt-get install -y redis-server
    else
        echo "❌ Please install Redis manually for your OS"
        exit 1
    fi
fi
echo "✅ Redis is installed"

# Start Redis if not running
if ! pgrep -x "redis-server" > /dev/null; then
    echo "🚀 Starting Redis server..."
    redis-server --daemonize yes
    sleep 2
fi
echo "✅ Redis server is running"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
cd backend
pip install -r ../requirements.txt
cd ..

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
cd frontend
npm install
cd ..

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs
mkdir -p data/cache

# Set up environment variables
echo "🔧 Setting up environment variables..."
if [ ! -f .env ]; then
    cat > .env << EOF
# Database
DATABASE_URL=sqlite:///./cineai.db

# JWT Secret
SECRET_KEY=your-super-secret-key-change-in-production

# Redis
REDIS_URL=redis://localhost:6379

# Model Path
MODEL_PATH=./Checkpoints/best_performer_mf_regularized.pt

# API Settings
API_HOST=0.0.0.0
API_PORT=8000

# Frontend
FRONTEND_URL=http://localhost:5173
EOF
    echo "✅ Created .env file"
else
    echo "✅ .env file already exists"
fi

# Initialize database
echo "🗄️  Initializing database..."
cd backend
python -c "
from app.database import engine
from app.models import Base
Base.metadata.create_all(bind=engine)
print('Database initialized successfully')
"
cd ..

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "To start the application:"
echo "1. Start the backend: cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo "2. Start the frontend: cd frontend && npm run dev"
echo ""
echo "The application will be available at:"
echo "   Frontend: http://localhost:5173"
echo "   Backend API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Happy watching! 🍿" 