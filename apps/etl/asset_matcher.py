"""
Shared asset identification logic for ETL pipeline.

Matches text content to tracked assets by symbol or keyword.
Extracted from backtest_engine.py and telegram_client.py to eliminate duplication (DRY).
"""


def identify_asset(text, assets):
    """
    Returns the asset symbol if found in text, else None.
    Priority: Exact Symbol Match > Keyword Match.

    Args:
        text: The text content to search for asset references.
        assets: List of asset dicts, each with 'symbol' and 'keywords' keys.

    Returns:
        The matched asset symbol string, or None if no match found.
    """
    text_lower = text.lower()

    for asset in assets:
        # Check symbol (case-sensitive, space-padded for word boundary)
        if f" {asset['symbol']} " in f" {text} ":
            return asset['symbol']

        # Check keywords (case-insensitive)
        for kw in asset['keywords']:
            if kw in text_lower:
                return asset['symbol']

    return None
