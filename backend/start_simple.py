#!/usr/bin/env python3
"""
Simple backend startup script for CineAI
"""

import os
import sys
import sqlite3
from pathlib import Path

def create_database():
    """Create the SQLite database and tables"""
    try:
        # Create database file
        db_path = Path("../cineai.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR UNIQUE NOT NULL,
                email VARCHAR UNIQUE NOT NULL,
                hashed_password VARCHAR NOT NULL,
                signup_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def install_dependencies():
    """Install required Python packages"""
    try:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "../requirements.txt"])
        print("✅ Dependencies installed")
        return True
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def start_server():
    """Start the FastAPI server"""
    try:
        import uvicorn
        print("🚀 Starting CineAI Backend Server...")
        print("   API: http://localhost:8000")
        print("   Docs: http://localhost:8000/docs")
        print("   Press Ctrl+C to stop")
        print()
        
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except ImportError:
        print("❌ uvicorn not found. Installing...")
        install_dependencies()
        start_server()
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    print("🎬 CineAI Backend Setup")
    print("========================")
    
    # Create database
    if not create_database():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Start server
    start_server() 