"""
Historical Price Ingestion Script

Fetches historical OHLCV data for all tracked assets using yfinance
(free, no API key required) and inserts into the historical_prices table.
"""

from datetime import datetime, date
from db import fetch_active_assets, insert_historical_prices_batch
from price_fetcher import get_historical_ohlcv


def ingest_historical_prices(date_range=None):
    """
    Fetches and inserts historical prices for all active assets.
    
    Args:
        date_range: tuple of (start_date, end_date) as strings 'YYYY-MM-DD' or date objects.
                    Defaults to 2022-01-01 to 2022-12-31 if not provided.
    """
    # Default date range covers the WallStreetBets 2022 CSV
    if date_range:
        start_date, end_date = date_range
    else:
        start_date = '2022-01-01'
        end_date = '2022-12-31'

    print(f"\n{'='*60}")
    print(f"Historical Price Ingestion")
    print(f"Date Range: {start_date} → {end_date}")
    print(f"{'='*60}")

    # Fetch assets from DB (single source of truth)
    assets = fetch_active_assets()
    if not assets:
        print("No active assets found in DB. Ensure assets are seeded.")
        return

    print(f"Found {len(assets)} active assets: {[a['symbol'] for a in assets]}")

    total_inserted = 0

    for asset in assets:
        symbol = asset['symbol']
        asset_type = asset['type']

        print(f"\nFetching prices for {symbol} ({asset_type})...")

        ohlcv_data = get_historical_ohlcv(
            symbol=symbol,
            asset_type=asset_type,
            start_date=start_date,
            end_date=end_date
        )

        if not ohlcv_data:
            print(f"  No price data returned for {symbol}. Skipping.")
            continue

        # Determine the source label
        source = 'yfinance'

        # Build batch records: (asset_symbol, price_open, price_close, price_high, price_low, volume, event_date, source)
        records = []
        for day in ohlcv_data:
            records.append((
                symbol,
                day['open'],
                day['close'],
                day['high'],
                day['low'],
                day['volume'],
                day['date'],
                source
            ))

        inserted = insert_historical_prices_batch(records)
        total_inserted += inserted
        print(f"  Inserted {inserted} price records for {symbol}.")

    print(f"\n{'='*60}")
    print(f"Historical Price Ingestion Complete!")
    print(f"Total records inserted: {total_inserted}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    # Standalone execution for testing
    from db import init_db
    init_db()
    ingest_historical_prices()
