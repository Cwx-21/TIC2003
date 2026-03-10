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
    """Loads assets from the JSON config."""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'assets.json')
    with open(config_path, 'r') as f:
        return json.load(f)

async def price_loop(session_id=None):
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
    print("Starting ETL Service in BACKTEST MODE...")
    init_db()
    from backtest_engine import BacktestRunner
    runner = BacktestRunner()
    runner.run()
    close_pool()

def run_live_mode():
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
