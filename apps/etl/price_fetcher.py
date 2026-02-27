import os
import json
from datetime import datetime


def _load_assets_from_config():
    """Fallback: loads assets from JSON config when DB is not available."""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'assets.json')
    with open(config_path, 'r') as f:
        data = json.load(f)
    return data['assets']


def get_yfinance_ticker(symbol, asset_type):
    """
    Converts an asset symbol to a yfinance-compatible ticker.
    - Stocks: use symbol as-is (e.g., 'TSLA', 'NVDA')
    - Crypto: append '-USD' (e.g., 'BTC' → 'BTC-USD')
    """
    if asset_type == 'crypto':
        return f"{symbol}-USD"
    return symbol


def get_live_price(symbol, assets=None):
    """
    Fetches current live price via yfinance.
    Works for both crypto and stocks.
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
    Fetches historical OHLCV data for a given asset via yfinance.
    Works for both crypto and stocks — no API key required.

    Args:
        symbol: Asset symbol (e.g., 'BTC', 'TSLA')
        asset_type: 'crypto' or 'stock'
        start_date: datetime.date or str 'YYYY-MM-DD'
        end_date: datetime.date or str 'YYYY-MM-DD'

    Returns:
        list of dicts: [{date, open, high, low, close, volume}, ...]
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
    # data = get_historical_ohlcv('BTC', 'crypto', None, '2022-01-01', '2022-01-10')
    # print(f"BTC historical: {len(data)} records")
