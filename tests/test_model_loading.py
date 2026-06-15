#!/usr/bin/env python3
"""
Test script to verify model loading and generate sample recommendations.
Run manually: pytest tests/test_model_loading.py -m slow
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.app.model_service import MovieRecommendationModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pytestmark = pytest.mark.slow


def test_model_loading():
    """Load checkpoints and initialize the recommendation engine."""
    model_service = MovieRecommendationModel(use_redis=False)
    assert model_service.engine is not None
    assert len(model_service.movie_data) > 0


def test_generate_sample_recommendations():
    model_service = MovieRecommendationModel(use_redis=False)
    recommendations, _ = model_service.get_recommendations(1, 5)
    assert isinstance(recommendations, list)
