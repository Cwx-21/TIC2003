"""
Price Fetcher

Wraps the yfinance library to provide live and historical OHLCV price data
for all tracked assets. Handles the symbol translation required for crypto
tickers (e.g., 'BTC' → 'BTC-USD') and normalises yfinance DataFrame output
into plain Python dicts for downstream consumption.

No API key is required — yfinance fetches data from Yahoo Finance's public
endpoints. Rate limiting should be respected by callers (e.g., 2-second
delays between per-asset calls in the live price loop).
"""

import os
import json


def _load_assets_from_config():
    """
    Fallback: loads assets from JSON config when DB is not available.

    Returns:
        list[dict]: Asset definitions from config/assets.json.
    """
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'assets.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['assets']


def get_yfinance_ticker(symbol, asset_type):
    """
    Converts an asset symbol to a yfinance-compatible ticker string.

    Stocks use the symbol as-is (e.g., 'TSLA', 'NVDA').
    Crypto symbols are suffixed with '-USD' (e.g., 'BTC' → 'BTC-USD').

    Args:
        symbol (str): Asset ticker symbol.
        asset_type (str): Either 'crypto' or 'stock'.

    Returns:
        str: yfinance-compatible ticker string.
    """
    if asset_type == 'crypto':
        return f"{symbol}-USD"
    return symbol


def get_live_price(symbol, assets=None):
    """
    Fetches the current market price for an asset via yfinance.

    Resolves the asset type from the provided assets list (or falls back to
    the config file) to apply the correct ticker translation.

    Args:
        symbol (str): Asset ticker (e.g., 'BTC', 'TSLA').
        assets (list[dict], optional): Pre-loaded asset list. If None, loaded from config.

    Returns:
        float: Current closing price, or 0.0 if unavailable.
    """
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance not installed. Run: pip install yfinance")
        return 0.0

    if assets is None:
        assets = _load_assets_from_config()

    # Find asset type
    asset_type = 'stock'
    for asset in assets:
        if asset['symbol'] == symbol.upper():
            asset_type = asset.get('type', 'stock')
            break

    ticker_symbol = get_yfinance_ticker(symbol, asset_type)

    try:
        ticker = yf.Ticker(ticker_symbol)
        data = ticker.history(period='1d')
        if not data.empty:
            return float(data['Close'].iloc[-1])
        return 0.0
    except Exception as e:
        print(f"Error fetching live price for {symbol}: {e}")
        return 0.0


def get_historical_ohlcv(symbol, asset_type, start_date, end_date):
    """
    Fetches historical daily OHLCV data for an asset via yfinance.

    Applies the appropriate ticker translation and returns normalised records
    as a list of plain Python dicts, ready for batch insertion into
    historical_prices via insert_historical_prices_batch().

    Args:
        symbol (str): Asset ticker (e.g., 'BTC', 'TSLA').
        asset_type (str): 'crypto' or 'stock'.
        start_date (str | datetime.date): Start date in 'YYYY-MM-DD' format or date object.
        end_date (str | datetime.date): End date in 'YYYY-MM-DD' format or date object.

    Returns:
        list[dict]: Daily records with keys: date, open, high, low, close, volume.
                    Returns an empty list if no data is found or on error.
    """
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance not installed. Run: pip install yfinance")
        return []

    ticker_symbol = get_yfinance_ticker(symbol, asset_type)

    if isinstance(start_date, str):
        start_str = start_date
    else:
        start_str = start_date.strftime('%Y-%m-%d')

    if isinstance(end_date, str):
        end_str = end_date
    else:
        end_str = end_date.strftime('%Y-%m-%d')

    try:
        print(f"  [yfinance] Fetching {ticker_symbol} from {start_str} to {end_str}...")
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(start=start_str, end=end_str, interval='1d')

        if df.empty:
            print(f"  [yfinance] No data returned for {ticker_symbol}")
            return []

        result = []
        for date_idx, row in df.iterrows():
            result.append({
                'date': date_idx.strftime('%Y-%m-%d'),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': float(row['Volume'])
            })

        print(f"  [yfinance] {ticker_symbol}: fetched {len(result)} daily records")
        return result

    except Exception as e:
        print(f"Error fetching yfinance OHLCV for {ticker_symbol}: {e}")
        return []


if __name__ == "__main__":
    # Quick test
    print(f"BTC Live: ${get_live_price('BTC')}")
