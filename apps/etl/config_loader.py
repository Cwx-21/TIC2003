"""
Shared configuration loader for ETL pipeline.

Loads asset definitions from config/assets.json.
Extracted from backtest_engine.py and telegram_client.py to eliminate duplication (DRY).
"""

import os
import json


def load_config():
    """Loads the full config (assets, channels, etc.) from config/assets.json."""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'assets.json')
    with open(config_path, 'r') as f:
        return json.load(f)
