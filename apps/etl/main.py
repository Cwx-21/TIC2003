"""
HypeCheck ETL Entry Point

CLI interface for the HypeCheck data pipeline. Supports two operation modes:

  live      — Connects to Telegram channels and processes messages in real-time.
              Runs three concurrent async tasks: TelegramMonitor, price_loop,
              and a live aggregation processor (LiveProcessor).

  backtest  — Replays the WallStreetBets 2022 CSV dataset through the full
              sentiment analysis and correlation pipeline (BacktestRunner).

Usage:
    python main.py --mode live
    python main.py --mode backtest
    python main.py --mode backtest --clear
"""

import argparse
import asyncio
import time
import os
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load env vars from .env file (if exists)
load_dotenv()

from db import (
    init_db, insert_price, seed_assets,
    create_live_session, update_live_session_count, complete_live_session,
    close_pool
)
from price_fetcher import get_live_price
from live_engine import LiveProcessor


def load_config():
    """
    Loads the asset registry and Telegram channel list from config/assets.json.

    Returns:
        dict: Parsed JSON config containing 'assets' and 'telegram_channels' keys.
    """
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'assets.json')
    with open(config_path, 'r') as f:
        return json.load(f)


async def price_loop(session_id=None):
    """
    Continuously polls yfinance for live prices and inserts records into price_history.

    Iterates over all configured assets, fetches the current price, and persists
    it with a UTC timestamp. Sleeps 60 seconds between full polling cycles to
    respect yfinance rate limits.

    Args:
        session_id (int, optional): Live session ID to tag price records with.
    """
    print("Starting Live Price Loop...")
    config = load_config()
    assets = config['assets']

    while True:
        try:
            for asset in assets:
                symbol = asset['symbol']
                price = get_live_price(symbol)
                if price > 0:
                    insert_price(
                        symbol, price,
                        event_timestamp=datetime.now(timezone.utc),
                        session_id=session_id
                    )
                    print(f"[Price] {symbol}: ${price}")
                # Rate limit respect
                await asyncio.sleep(2)

            # Update every 60 seconds
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Price loop error: {e}")
            await asyncio.sleep(10)


def run_backtest_mode():
    """
    Executes the full backtest pipeline against the WallStreetBets 2022 CSV.

    Initialises the database schema, instantiates a BacktestRunner, and runs
    the pipeline which includes sentiment ingestion, aggregation, correlation,
    and alert generation. Closes the connection pool on completion.
    """
    print("Starting ETL Service in BACKTEST MODE...")
    init_db()
    from backtest_engine import BacktestRunner
    runner = BacktestRunner()
    runner.run()
    close_pool()


def run_live_mode():
    """
    Launches the live monitoring pipeline with concurrent async tasks.

    Initialises the database, seeds assets from config, and creates a live
    session record. Then runs four async tasks concurrently on a single event loop:
      - TelegramMonitor.start() — listens for new messages on configured channels.
      - price_loop()            — polls yfinance for current prices every 60s.
      - session_counter()       — updates total_messages_processed every 60s.
      - live_aggregation_loop() — runs LiveProcessor.process_window() every 60s.

    On KeyboardInterrupt, marks the session as stopped and closes the pool.
    """
    print("Starting ETL Service in LIVE MODE (Telegram)...")
    init_db()

    config = load_config()

    # Seed assets table from config
    seed_assets(config['assets'])

    # Create a live session record
    asset_symbols = [a['symbol'] for a in config['assets']]
    channels = config.get('telegram_channels', [])

    session_id = create_live_session(
        name=f"Live Session {datetime.now().strftime('%Y%m%d_%H%M%S')}",
        channels=channels,
        assets_tracked=asset_symbols
    )

    if session_id:
        print(f"Initialized Live Session ID: {session_id}")
    else:
        print("WARNING: Failed to create live session record. Continuing without session tracking.")

    from telegram_client import TelegramMonitor

    monitor = TelegramMonitor(session_id=session_id)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Schedule both task listeners
    loop.create_task(monitor.start())
    loop.create_task(price_loop(session_id=session_id))

    # Periodically update session message count
    async def session_counter():
        while True:
            await asyncio.sleep(60)
            if session_id and monitor.message_count > 0:
                update_live_session_count(session_id, monitor.message_count)

    # Periodically run the live aggregation processor
    async def live_aggregation_loop():
        if not session_id:
            return

        processor = LiveProcessor(session_id)
        while True:
            # Wake up every 60 seconds
            await asyncio.sleep(60)

            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(seconds=60)

            try:
                await processor.process_window(start_time, end_time)
            except Exception as e:
                print(f"Error in Live Aggregation Loop: {e}")

    loop.create_task(session_counter())
    loop.create_task(live_aggregation_loop())

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("Stopping Live Mode...")
        if session_id:
            # Update final count and mark session as stopped
            update_live_session_count(session_id, monitor.message_count)
            complete_live_session(session_id, status='stopped')
            print(f"Live Session {session_id} marked as stopped ({monitor.message_count} messages processed).")
        close_pool()


def main():
    """
    Parses CLI arguments and dispatches to the appropriate operation mode.

    Flags:
        --mode   'live' or 'backtest' (default: live).
        --clear  Truncates all data tables before running.
    """
    parser = argparse.ArgumentParser(description='HypeCheck ETL Service')
    parser.add_argument('--mode', choices=['live', 'backtest'], default='live', help='Operation mode')
    parser.add_argument('--clear', action='store_true', help='Clear database before running')
    args = parser.parse_args()

    # Wait for DB to be ready
    time.sleep(3)

    if args.clear:
        from db import clear_all_data
        init_db()  # Ensure tables exist before truncating
        clear_all_data()

    if args.mode == 'live':
        run_live_mode()
    elif args.mode == 'backtest':
        run_backtest_mode()


if __name__ == "__main__":
    main()
