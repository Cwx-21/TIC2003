"""
Boundary Value Analysis (BVA) Tests for Divergence Alert Thresholds.

Tests the check_divergence_alert() function at and around the two
decision boundaries:
  - Alert boundary: DIVERGENCE_THRESHOLD = 0.5 (strict >)
  - Severity boundary: DIVERGENCE_THRESHOLD * 2 = 1.0 (strict >)

BVA rationale: Defects cluster at boundaries. By testing values
immediately below, at, and above each boundary, we catch off-by-one
errors in comparison operators (> vs >=).
"""

import sys
import os

# Add the etl directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from alert_generator import check_divergence_alert


class TestDivergenceAlertBVA:
    """BVA tests for the divergence alert threshold logic."""

    # ── Alert Boundary Tests (threshold = 0.5) ──────────────────

    def test_below_alert_boundary(self):
        """Divergence 0.49: just below threshold, should NOT alert."""
        should_alert, severity = check_divergence_alert(0.49)
        assert should_alert is False
        assert severity is None

    def test_at_alert_boundary(self):
        """Divergence 0.50: exactly at threshold (uses strict >), should NOT alert."""
        should_alert, severity = check_divergence_alert(0.50)
        assert should_alert is False
        assert severity is None

    def test_just_above_alert_boundary(self):
        """Divergence 0.51: just above threshold, SHOULD alert with 'warning'."""
        should_alert, severity = check_divergence_alert(0.51)
        assert should_alert is True
        assert severity == 'warning'

    # ── Severity Boundary Tests (threshold * 2 = 1.0) ───────────

    def test_below_severity_boundary(self):
        """Divergence 0.99: above alert but below critical, should be 'warning'."""
        should_alert, severity = check_divergence_alert(0.99)
        assert should_alert is True
        assert severity == 'warning'

    def test_at_severity_boundary(self):
        """Divergence 1.00: exactly at severity boundary (strict >), should be 'warning'."""
        should_alert, severity = check_divergence_alert(1.00)
        assert should_alert is True
        assert severity == 'warning'

    def test_just_above_severity_boundary(self):
        """Divergence 1.01: just above severity boundary, should be 'critical'."""
        should_alert, severity = check_divergence_alert(1.01)
        assert should_alert is True
        assert severity == 'critical'

    # ── Negative Divergence Tests (symmetric boundaries) ─────────

    def test_negative_below_alert_boundary(self):
        """Divergence -0.49: negative but below threshold, should NOT alert."""
        should_alert, severity = check_divergence_alert(-0.49)
        assert should_alert is False
        assert severity is None

    def test_negative_above_alert_boundary(self):
        """Divergence -0.51: negative above threshold, SHOULD alert with 'warning'."""
        should_alert, severity = check_divergence_alert(-0.51)
        assert should_alert is True
        assert severity == 'warning'

    def test_negative_critical(self):
        """Divergence -1.01: negative above severity boundary, should be 'critical'."""
        should_alert, severity = check_divergence_alert(-1.01)
        assert should_alert is True
        assert severity == 'critical'

    # ── Edge Cases ───────────────────────────────────────────────

    def test_zero_divergence(self):
        """Divergence 0.00: no divergence at all, should NOT alert."""
        should_alert, severity = check_divergence_alert(0.00)
        assert should_alert is False
        assert severity is None

    def test_custom_threshold(self):
        """Test with a custom threshold of 1.0 — value 0.51 should NOT alert."""
        should_alert, severity = check_divergence_alert(0.51, threshold=1.0)
        assert should_alert is False
        assert severity is None

    def test_custom_threshold_boundary(self):
        """Test with custom threshold 1.0 — value 1.01 should alert as 'warning'."""
        should_alert, severity = check_divergence_alert(1.01, threshold=1.0)
        assert should_alert is True
        assert severity == 'warning'
