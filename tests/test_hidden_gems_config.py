"""Unit tests for hidden gems scoring and filters."""
from __future__ import annotations

from backend.app.hidden_gems_config import passes_hidden_gems_filters, serendipity_score


def test_serendipity_prefers_low_popularity():
    obscure = serendipity_score(popularity=5, vote_count=200, vote_average=8.0)
    blockbuster = serendipity_score(popularity=80, vote_count=50000, vote_average=8.0)
    assert obscure > blockbuster


def test_passes_hidden_gems_filters_rejects_blockbuster():
    assert passes_hidden_gems_filters(popularity=100.0, vote_count=20000, vote_average=8.5) is False


def test_passes_hidden_gems_filters_accepts_quality_niche():
    assert passes_hidden_gems_filters(popularity=12.0, vote_count=400, vote_average=7.5) is True
