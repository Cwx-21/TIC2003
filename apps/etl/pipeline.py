"""
Pipeline step abstraction for ETL post-processing.

Allows defining pipeline steps as a list of (name, callable) tuples,
so new steps can be added without modifying the BacktestRunner (OCP).
"""


def run_pipeline(steps, backtest_id, **kwargs):
    """
    Executes a sequence of named pipeline steps.

    Args:
        steps: List of (name, callable) tuples. Each callable receives
               (backtest_id, **kwargs).
        backtest_id: The backtest run ID to pass to each step.
        **kwargs: Additional keyword arguments forwarded to each step.
    """
    total = len(steps)
    for i, (name, step_fn) in enumerate(steps, 1):
        print(f"\n[Phase 1 - Step {i}/{total}] {name}...")
        step_fn(backtest_id, **kwargs)


# ── Default pipeline step functions ──────────────────────────────

def price_ingestion_step(backtest_id, date_range=None, **kwargs):
    """Ingest historical prices for the backtest date range."""
    from historical_price_ingest import ingest_historical_prices
    ingest_historical_prices(date_range=date_range)


def aggregation_step(backtest_id, **kwargs):
    """Aggregate sentiment into time buckets."""
    from aggregation_engine import SentimentAggregator
    SentimentAggregator().run(backtest_id)


def correlation_step(backtest_id, **kwargs):
    """Compute correlation & generate alerts."""
    from correlation_engine import CorrelationEngine
    CorrelationEngine().run(backtest_id)


# ── Default pipeline definition ──────────────────────────────────

DEFAULT_PIPELINE = [
    ("Historical Price Ingestion", price_ingestion_step),
    ("Sentiment Aggregation", aggregation_step),
    ("Correlation & Divergence Analysis", correlation_step),
]
