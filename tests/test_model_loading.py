#!/usr/bin/env python3
"""
Test script to verify model loading and generate sample recommendations.
Run from project root: python tests/test_model_loading.py
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
import logging
from backend.app.model_service import MovieRecommendationModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_model_loading():
    """Test if models can be loaded successfully."""
    try:
        model_service = MovieRecommendationModel(use_redis=False)
        if model_service.engine is None:
            logger.warning("Model engine is None - models failed to load")
            return False
        logger.info("Model service initialized: device=%s path=%s", model_service.device, model_service.model_path)
        logger.info("Movie data: %d movies", len(model_service.movie_data))
        return True
    except Exception as e:
        logger.exception("Error loading models")
        return False

def generate_sample_recommendations(model_service, user_id=1, n_recommendations=10):
    """Generate sample recommendations for testing."""
    try:
        recommendations, _ = model_service.get_recommendations(user_id, n_recommendations)
        if recommendations:
            logger.info("Generated %d recommendations for user_id=%s", len(recommendations), user_id)
        return recommendations
    except Exception as e:
        logger.exception("Error generating recommendations")
        return []

def main():
    if not test_model_loading():
        logger.error("Model loading failed")
        return
    model_service = MovieRecommendationModel(use_redis=False)
    generate_sample_recommendations(model_service, user_id=1, n_recommendations=10)
    logger.info("Testing complete")

if __name__ == "__main__":
    main()
