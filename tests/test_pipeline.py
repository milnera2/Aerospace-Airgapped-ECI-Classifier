"""
tests/test_pipeline.py

Smoke tests for the ECI classification pipeline using mock test cases.

Run with:  pytest tests/
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pipeline import orchestrate_classification
from test_cases import COMMERCIAL_BASELINE, DEFENSE_ARTICLE, DUAL_USE_EDGE_CASE


def test_commercial_baseline_not_halted():
    """Commercial baseline should complete without halting."""
    result = orchestrate_classification(COMMERCIAL_BASELINE["description"])
    assert result["status"] == "CLASSIFICATION_COMPLETE"
    assert result["guardrail_triggered"] is False
    assert result["extractor_output"] is not None
    assert result["legal_output"] is not None
    assert result["marking_output"] is not None


def test_defense_article_not_halted():
    """Defense article should complete without halting."""
    result = orchestrate_classification(DEFENSE_ARTICLE["description"])
    assert result["status"] == "CLASSIFICATION_COMPLETE"
    assert result["guardrail_triggered"] is False
    assert result["marking_output"] is not None


def test_dual_use_edge_case_halted():
    """Dual-use edge case should trigger hard stop and not produce markings."""
    result = orchestrate_classification(DUAL_USE_EDGE_CASE["description"])
    assert result["status"] == "HALTED_FOR_HUMAN_REVIEW"
    assert result["guardrail_triggered"] is True
    assert result["marking_output"] is None
    assert "violations" in result["guardrail_details"]
