import requests
import time
from datetime import datetime

# CoinGecko API (Free tier has rate limits, be careful)
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"

# Mapping symbols to CoinGecko IDs
ASSET_MAP = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'DOGE': 'dogecoin',
    'SOL': 'solana'
}

def get_live_price(symbol):
    """Fetches key price data from CoinGecko."""
    coin_id = ASSET_MAP.get(symbol.upper())
    if not coin_id:
        return 0.0

    try:
        url = f"{COINGECKO_API_URL}/simple/price"
        params = {
            'ids': coin_id,
            'vs_currencies': 'usd'
        }
        res = requests.get(url, params=params, timeout=5)
        res.raise_for_status()
        data = res.json()
        return data.get(coin_id, {}).get('usd', 0.0)
    except Exception as e:
        print(f"Error fetching live price for {symbol}: {e}")
        return 0.0

def get_historical_price(symbol, timestamp):
    """
    Fetches historical price from CoinGecko.
    Timestamp should be a pandas Timestamp or datetime object.
    CoinGecko expects dd-mm-yyyy format.
    """
    coin_id = ASSET_MAP.get(symbol.upper())
    if not coin_id:
        return 0.0

    date_str = timestamp.strftime('%d-%m-%Y')
    
    try:
        url = f"{COINGECKO_API_URL}/coins/{coin_id}/history"
        params = {
            'date': date_str,
            'localization': 'false'
        }
        # Artificial delay to respect rate limits (approx 10-30 req/min for free tier)
        time.sleep(1.5) 
        
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        price = data.get('market_data', {}).get('current_price', {}).get('usd', 0.0)
        return price
    except Exception as e:
        print(f"Error fetching historical price for {symbol} on {date_str}: {e}")
        return 0.0

if __name__ == "__main__":
    # Test
    print(f"BTC Live: ${get_live_price('BTC')}")
    # print(f"BTC Historical: ${get_historical_price('BTC', datetime(2023, 1, 1))}")
