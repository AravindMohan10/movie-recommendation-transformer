
# Movie Recommendation System - Colab Training
# Run this in Google Colab with A100 GPU

# Install dependencies
!pip install transformers torch scikit-learn pandas numpy

# Mount Google Drive to save models
from google.colab import drive
drive.mount('/content/drive')

# Upload your data files to Drive first, then:
import torch
import pandas as pd

# Load your processed data
training_data = torch.load('/content/drive/MyDrive/processed_training_data_new.pt')

# Train models here...
# (We'll add the full training code next)

# Save trained models back to Drive
torch.save(trained_model, '/content/drive/MyDrive/content_model_trained.pt')
