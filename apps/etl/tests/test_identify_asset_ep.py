"""
Equivalence Partitioning (EP) Tests for Asset Identification.

Tests the identify_asset() function by dividing the input domain
into equivalence classes where all values produce the same behavior.
One representative test value is selected per partition.

Partitions:
  P1: Exact symbol match (ticker in text with word boundaries)
  P2: Keyword match (keyword substring in text)
  P3: No match (text has no asset reference)
  P4: Multiple assets (first match wins)
  P5: Case sensitivity (symbol case matters, keyword case-insensitive)
  P6: Partial keyword match (keyword embedded in larger word)
  P7: Empty/minimal input
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from asset_matcher import identify_asset


@pytest.fixture
def sample_assets():
    """Minimal asset config for testing — mirrors structure from config/assets.json."""
    return [
        {
            "symbol": "BTC",
            "name": "Bitcoin",
            "keywords": ["bitcoin", "btc", "satoshi"]
        },
        {
            "symbol": "ETH",
            "name": "Ethereum",
            "keywords": ["ethereum", "eth", "vitalik"]
        },
        {
            "symbol": "GME",
            "name": "GameStop",
            "keywords": ["gme", "gamestop", "deepfuckingvalue", "roaringkitty"]
        },
    ]


class TestIdentifyAssetEP:
    """Equivalence Partitioning tests for identify_asset()."""

    # ── P1: Exact Symbol Match ───────────────────────────────────

    def test_exact_symbol_match(self, sample_assets):
        """P1: Text contains the ticker symbol with word boundaries."""
        result = identify_asset("I'm buying BTC today", sample_assets)
        assert result == "BTC"

    def test_exact_symbol_at_start(self, sample_assets):
        """P1 variant: Symbol at the start of text."""
        result = identify_asset("BTC is pumping hard", sample_assets)
        assert result == "BTC"

    def test_exact_symbol_at_end(self, sample_assets):
        """P1 variant: Symbol at the end of text."""
        result = identify_asset("All in on ETH", sample_assets)
        assert result == "ETH"

    # ── P2: Keyword Match ────────────────────────────────────────

    def test_keyword_match(self, sample_assets):
        """P2: Text contains a keyword (case-insensitive)."""
        result = identify_asset("bitcoin is pumping", sample_assets)
        assert result == "BTC"

    def test_keyword_match_mixed_case(self, sample_assets):
        """P2 variant: Keyword in mixed case."""
        result = identify_asset("BITCOIN to the moon!", sample_assets)
        assert result == "BTC"

    def test_keyword_match_different_asset(self, sample_assets):
        """P2 variant: Keyword for a different asset."""
        result = identify_asset("gamestop short squeeze incoming", sample_assets)
        assert result == "GME"

    # ── P3: No Match ─────────────────────────────────────────────

    def test_no_match(self, sample_assets):
        """P3: Text contains no asset reference."""
        result = identify_asset("hello world, nice weather today", sample_assets)
        assert result is None

    def test_no_match_unrelated_finance(self, sample_assets):
        """P3 variant: Finance-related text but no tracked asset."""
        result = identify_asset("AAPL stock is doing great", sample_assets)
        assert result is None

    # ── P4: Multiple Assets ──────────────────────────────────────

    def test_multiple_assets_first_wins(self, sample_assets):
        """P4: Text mentions multiple assets — first in config order wins."""
        result = identify_asset("BTC vs ETH comparison", sample_assets)
        assert result == "BTC"  # BTC is first in assets list

    def test_multiple_assets_keyword_order(self, sample_assets):
        """P4 variant: Multiple keywords — first asset in config wins."""
        result = identify_asset("ethereum and bitcoin battle", sample_assets)
        assert result == "BTC"  # BTC is first in assets list, "bitcoin" matches

    # ── P5: Case Sensitivity ─────────────────────────────────────

    def test_symbol_lowercase_no_symbol_match(self, sample_assets):
        """P5: Lowercase 'btc' should NOT match as a symbol (symbol match is case-sensitive),
        but SHOULD match as a keyword (keywords include 'btc')."""
        result = identify_asset("btc to the moon", sample_assets)
        assert result == "BTC"  # Matches via keyword 'btc', not symbol

    # ── P6: Partial/Embedded Keyword ─────────────────────────────

    def test_keyword_embedded_in_word(self, sample_assets):
        """P6: Keyword 'bitcoin' is a substring of 'bitcoiner' — still matches
        because keyword check uses 'in' (substring match)."""
        result = identify_asset("bitcoiner community growing", sample_assets)
        assert result == "BTC"

    def test_keyword_embedded_eth(self, sample_assets):
        """P6 variant: 'eth' keyword inside 'ethereum' — matches via 'ethereum' keyword first."""
        result = identify_asset("ethereum update released", sample_assets)
        assert result == "ETH"

    # ── P7: Empty/Minimal Input ──────────────────────────────────

    def test_empty_string(self, sample_assets):
        """P7: Empty string should return None."""
        result = identify_asset("", sample_assets)
        assert result is None

    def test_whitespace_only(self, sample_assets):
        """P7 variant: Whitespace-only string should return None."""
        result = identify_asset("   ", sample_assets)
        assert result is None

    def test_very_short_text(self, sample_assets):
        """P7 variant: Very short text with no match."""
        result = identify_asset("hi", sample_assets)
        assert result is None

    # ── Edge: Empty Assets List ──────────────────────────────────

    def test_empty_assets_list(self):
        """Edge: No assets configured — should always return None."""
        result = identify_asset("BTC is great", [])
        assert result is None
