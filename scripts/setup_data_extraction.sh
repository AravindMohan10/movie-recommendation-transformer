#!/bin/bash

# Setup script for CineAI data extraction
# This script helps configure the TMDB API key and run data extraction

set -e

echo "🎬 CineAI Data Extraction Setup"
echo "================================"

# Check if TMDB API key is already set
if [ -n "$TMDB_API_KEY" ]; then
    echo "✅ TMDB API key is already set"
else
    echo "❌ TMDB API key is not set"
    echo ""
    echo "To get a TMDB API key:"
    echo "1. Go to https://www.themoviedb.org/settings/api"
    echo "2. Create an account if you don't have one"
    echo "3. Request an API key (v3 auth)"
    echo "4. Copy your API key"
    echo ""
    
    read -p "Enter your TMDB API key: " api_key
    
    if [ -n "$api_key" ]; then
        echo "export TMDB_API_KEY='$api_key'" >> ~/.zshrc
        echo "export TMDB_API_KEY='$api_key'" >> ~/.bash_profile
        export TMDB_API_KEY="$api_key"
        echo "✅ TMDB API key has been set"
        echo "   Please restart your terminal or run: source ~/.zshrc"
    else
        echo "❌ No API key provided. Exiting."
        exit 1
    fi
fi

# Install required packages
echo ""
echo "📦 Installing required packages..."
source ~/moodenv/bin/activate
pip install pandas tqdm aiohttp

# Create necessary directories
echo ""
echo "📁 Creating data directories..."
mkdir -p data/raw
mkdir -p data/processed
mkdir -p cache
mkdir -p logs

echo ""
echo "🚀 Ready to extract data!"
echo ""
echo "To extract data, run:"
echo "  python data_engine/extract_data.py"
echo ""
echo "To run the complete ETL pipeline, run:"
echo "  python data_engine/etl_pipeline.py"
echo ""
echo "Or run both in sequence:"
echo "  python data_engine/extract_data.py && python data_engine/etl_pipeline.py" 