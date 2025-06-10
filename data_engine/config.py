"""
Configuration settings for the CineAI Data Engine
"""

import os
from pathlib import Path
from typing import Dict, Any

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / "cache"
MODELS_DIR = BASE_DIR / "models"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
for dir_path in [DATA_DIR, CACHE_DIR, MODELS_DIR, LOGS_DIR]:
    dir_path.mkdir(exist_ok=True)

# TMDB API Configuration (api_key from TMDB_API_KEY env; no fallback for security)
TMDB_CONFIG = {
    "api_key": os.getenv("TMDB_API_KEY", "").strip(),
    "base_url": "https://api.themoviedb.org/3",
    "image_base_url": "https://image.tmdb.org/t/p/",
    "language": "en-US",
    "region": "US",
    "timeout": 30,
    "max_retries": 3,
    "rate_limit": {
        "requests_per_second": 10,
        "requests_per_minute": 40
    }
}

# Database Configuration
DATABASE_CONFIG = {
    "sqlite": {
        "path": BASE_DIR / "cineai.db",
        "check_same_thread": False,
        "timeout": 30
    },
    "postgresql": {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "database": os.getenv("DB_NAME", "cineai"),
        "username": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
        "pool_size": 10,
        "max_overflow": 20
    }
}

# Data Processing Configuration
DATA_CONFIG = {
    "batch_size": 1000,
    "max_workers": 4,
    "chunk_size": 10000,
    "compression": "gzip",
    "encoding": "utf-8",
    "cache_ttl": 3600,  # 1 hour
    "max_memory_usage": "2GB",
    "raw_data_dir": "data/raw"
}

# Feature Engineering Configuration
FEATURE_CONFIG = {
    "text_embeddings": {
        "model": "sentence-transformers/all-MiniLM-L6-v2",
        "max_length": 512,
        "batch_size": 32,
        "device": "auto"
    },
    "image_embeddings": {
        "model": "clip-vit-base-patch32",
        "image_size": 224,
        "batch_size": 16
    },
    "categorical_encoding": {
        "method": "target_encoding",
        "smoothing": 1.0,
        "min_samples": 10
    },
    "numerical_features": {
        "scaling": "robust",
        "outlier_detection": True,
        "outlier_threshold": 3.0
    }
}

# Search Configuration
SEARCH_CONFIG = {
    "index_type": "faiss",  # or "elasticsearch", "pinecone"
    "faiss": {
        "index_type": "IVFFlat",
        "nlist": 100,
        "nprobe": 10,
        "metric": "cosine"
    },
    "elasticsearch": {
        "host": os.getenv("ES_HOST", "localhost"),
        "port": int(os.getenv("ES_PORT", "9200")),
        "index_name": "cineai_movies",
        "shards": 1,
        "replicas": 0
    },
    "max_results": 100,
    "min_score": 0.1,
    "fuzzy_matching": True,
    "autocomplete": True
}

# Model Configuration
MODEL_CONFIG = {
    "recommendation": {
        "type": "hybrid",  # "collaborative", "content", "hybrid"
        "collaborative_weight": 0.3,
        "content_weight": 0.7,
        "embedding_dim": 384,
        "hidden_dims": [256, 128, 64],
        "dropout": 0.2,
        "learning_rate": 0.001,
        "batch_size": 64,
        "epochs": 100,
        "early_stopping_patience": 10
    },
    "reinforcement_learning": {
        "algorithm": "PPO",  # "A2C", "DQN", "PPO"
        "learning_rate": 0.0003,
        "gamma": 0.99,
        "gae_lambda": 0.95,
        "clip_ratio": 0.2,
        "value_loss_coef": 0.5,
        "entropy_coef": 0.01,
        "max_grad_norm": 0.5,
        "update_epochs": 4,
        "batch_size": 64
    }
}

# Logging Configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "simple": {
            "format": "%(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "simple"
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": LOGS_DIR / "data_engine.log",
            "level": "DEBUG",
            "formatter": "detailed"
        }
    },
    "loggers": {
        "data_engine": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False
        }
    }
}

# Cache Configuration
CACHE_CONFIG = {
    "redis": {
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": int(os.getenv("REDIS_PORT", "6379")),
        "db": 0,
        "password": os.getenv("REDIS_PASSWORD", ""),
        "decode_responses": True
    },
    "memory": {
        "max_size": 1000,
        "ttl": 300  # 5 minutes
    }
}

# Monitoring Configuration
MONITORING_CONFIG = {
    "metrics": {
        "enabled": True,
        "prometheus": {
            "port": 8001,
            "path": "/metrics"
        }
    },
    "health_checks": {
        "enabled": True,
        "interval": 30,
        "timeout": 5
    },
    "alerts": {
        "enabled": True,
        "webhook_url": os.getenv("ALERT_WEBHOOK_URL", ""),
        "thresholds": {
            "error_rate": 0.05,
            "response_time": 5.0,
            "memory_usage": 0.8
        }
    }
}

def get_config() -> Dict[str, Any]:
    """Get the complete configuration dictionary."""
    return {
        "tmdb": TMDB_CONFIG,
        "database": DATABASE_CONFIG,
        "data": DATA_CONFIG,
        "features": FEATURE_CONFIG,
        "search": SEARCH_CONFIG,
        "model": MODEL_CONFIG,
        "logging": LOGGING_CONFIG,
        "cache": CACHE_CONFIG,
        "monitoring": MONITORING_CONFIG
    }

def validate_config() -> bool:
    """Validate the configuration settings."""
    # Check required environment variables
    if not TMDB_CONFIG["api_key"]:
        print("⚠️  TMDB_API_KEY not set. Some features may not work.")
    
    # Check directories
    for dir_path in [DATA_DIR, CACHE_DIR, MODELS_DIR, LOGS_DIR]:
        if not dir_path.exists():
            print(f"⚠️  Directory {dir_path} does not exist and will be created.")
    
    return True 