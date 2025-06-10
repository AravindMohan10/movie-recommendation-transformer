#!/usr/bin/env python3
"""
Google Colab Setup Script
Run this in Colab to set up and train models
"""

# Mount Google Drive (uncomment if needed)
# from google.colab import drive
# drive.mount('/content/drive')

# Install dependencies
import subprocess
import sys

def install_packages():
    """Install required packages"""
    packages = [
        "torch",
        "torchvision", 
        "torchaudio",
        "--index-url", "https://download.pytorch.org/whl/cu118",
        "transformers",
        "pandas",
        "numpy",
        "scikit-learn",
        "tqdm"
    ]
    
    print("📦 Installing packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages)
    print("✅ Packages installed!")

if __name__ == "__main__":
    install_packages()
    print("\n🚀 Ready to train! Run: python train_recommendation_engine.py")

