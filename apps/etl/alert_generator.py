"""
Shared alert generation logic for ETL pipeline.

Contains threshold constants and alert generation functions used by
both the backtest correlation engine and the live processor.
Extracted to eliminate duplication (DRY).
"""

from db import insert_alert


# ── Thresholds (single source of truth) ──────────────────────────
DIVERGENCE_THRESHOLD = 0.5       # abs(divergence) > this triggers an alert
VOLUME_SPIKE_THRESHOLD = 3.0     # message_volume > (mean * this) triggers a volume spike alert


def check_divergence_alert(divergence, threshold=DIVERGENCE_THRESHOLD):
    """
    Pure-function check: should a divergence alert fire, and at what severity?

    Args:
        divergence: The computed divergence value (sentiment - normalized price change).
        threshold: The divergence threshold for triggering an alert.

    Returns:
        Tuple of (should_alert: bool, severity: str | None).
        severity is 'critical' if abs(divergence) > threshold * 2, else 'warning'.
    """
    if abs(divergence) <= threshold:
        return False, None
    severity = 'critical' if abs(divergence) > (threshold * 2) else 'warning'
    return True, severity


def generate_divergence_alert(symbol, divergence, weighted_avg, price_change_pct,
                               price_close, msg_volume, timestamp,
                               backtest_id=None, session_id=None,
                               threshold=DIVERGENCE_THRESHOLD):
    """
    Checks divergence against threshold and inserts an alert if needed.

    Returns:
        True if an alert was generated, False otherwise.
    """
    should_alert, severity = check_divergence_alert(divergence, threshold)
    if not should_alert:
        return False

    direction = "bullish sentiment / bearish price" if divergence > 0 else "bearish sentiment / bullish price"

    insert_alert(
        asset_symbol=symbol,
        alert_type='divergence',
        severity=severity,
        message=f"Sentiment-price divergence detected for {symbol}: {direction} (divergence={divergence:.3f})",
        details={
            'divergence': float(round(divergence, 4)),
            'weighted_sentiment': float(round(weighted_avg, 4)),
            'price_change_pct': float(round(price_change_pct, 4)),
            'price_close': float(round(price_close, 2)),
            'message_volume': int(msg_volume)
        },
        event_timestamp=timestamp,
        backtest_id=backtest_id,
        session_id=session_id
    )
    return True


def generate_volume_spike_alert(symbol, msg_count, baseline_volume, timestamp,
                                 backtest_id=None, session_id=None,
                                 spike_threshold=VOLUME_SPIKE_THRESHOLD):
    """
    Checks message volume against baseline and inserts a volume spike alert if needed.

    Args:
        msg_count: Current message count.
        baseline_volume: The baseline volume to compare against (mean or previous bucket).
        spike_threshold: Multiplier for the baseline to trigger an alert.

    Returns:
        True if an alert was generated, False otherwise.
    """
    if baseline_volume <= 0:
        return False
    if msg_count <= (baseline_volume * spike_threshold):
        return False

    insert_alert(
        asset_symbol=symbol,
        alert_type='volume_spike',
        severity='info',
        message=f"Message volume spike for {symbol}: {msg_count} messages (baseline: {int(baseline_volume)})",
        details={
            'message_volume': int(msg_count),
            'mean_volume': float(round(baseline_volume, 1)),
            'spike_ratio': float(round(msg_count / baseline_volume, 2))
        },
        event_timestamp=timestamp,
        backtest_id=backtest_id,
        session_id=session_id
    )
    return True
