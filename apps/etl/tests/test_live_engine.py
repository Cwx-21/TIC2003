import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

# Import the class we want to test
from live_engine import LiveProcessor

@pytest.fixture
def mock_db_functions():
    """Mocks all database calls used by LiveProcessor."""
    with patch('live_engine.fetch_active_assets') as mock_assets, \
         patch('live_engine.fetch_sentiment_logs_for_window') as mock_logs, \
         patch('live_engine.fetch_latest_price') as mock_price, \
         patch('live_engine.fetch_previous_correlation') as mock_corr, \
         patch('live_engine.insert_aggregations_batch') as mock_insert_agg, \
         patch('live_engine.insert_correlations_batch') as mock_insert_corr, \
         patch('alert_generator.insert_alert') as mock_insert_alert:
         
        # Default mock returns
        mock_assets.return_value = [{'symbol': 'BTC'}, {'symbol': 'ETH'}]
        mock_logs.return_value = []
        mock_price.return_value = None
        mock_corr.return_value = None
        
        yield {
            'assets': mock_assets,
            'logs': mock_logs,
            'price': mock_price,
            'corr': mock_corr,
            'insert_agg': mock_insert_agg,
            'insert_corr': mock_insert_corr,
            'insert_alert': mock_insert_alert
        }

@pytest.fixture
def processor(mock_db_functions):
    """Returns a LiveProcessor instance with mocked DB calls."""
    return LiveProcessor(session_id=999)

@pytest.mark.asyncio
async def test_process_window_no_data(processor, mock_db_functions):
    """Test behavior when no messages occurred in the 60s window."""
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(seconds=60)
    
    # Run processor
    await processor.process_window(start_time, end_time)
    
    # Verify no inserts happened
    mock_db_functions['insert_agg'].assert_not_called()
    mock_db_functions['insert_corr'].assert_not_called()
    mock_db_functions['insert_alert'].assert_not_called()

@pytest.mark.asyncio
async def test_process_window_with_data(processor, mock_db_functions):
    """Test basic aggregation math with mock data."""
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(seconds=60)
    
    # Mock sentiment logs for BTC
    mock_db_functions['logs'].return_value = [
        {'asset_symbol': 'BTC', 'sentiment_score': 0.8, 'credibility_score': 1.0, 'event_timestamp': start_time},
        {'asset_symbol': 'BTC', 'sentiment_score': 0.2, 'credibility_score': 0.5, 'event_timestamp': start_time + timedelta(seconds=10)},
    ]
    
    # Mock previous price and correlation
    mock_db_functions['price'].return_value = {'price': 52000.0, 'event_timestamp': end_time}
    mock_db_functions['corr'].return_value = {
        'price_at_bucket': 50000.0, 
        'message_volume': 10,
        'avg_sentiment': 0.5,
        'weighted_sentiment': 0.5,
        'time_bucket': start_time - timedelta(minutes=1)
    }
    
    # Run processor
    await processor.process_window(start_time, end_time)
    
    # Verify Aggregations
    # expected_avg = (0.8 + 0.2) / 2 = 0.50
    # expected_weighted = ((0.8 * 1.0) + (0.2 * 0.5)) / (1.0 + 0.5) = 0.9 / 1.5 = 0.60
    assert mock_db_functions['insert_agg'].called
    agg_args = mock_db_functions['insert_agg'].call_args[0][0]
    
    assert len(agg_args) == 1
    btc_agg = agg_args[0]
    assert btc_agg[0] == 'BTC'
    assert btc_agg[3] == 0.5     # avg_sentiment_score
    assert round(btc_agg[4], 2) == 0.60  # weighted_avg_sentiment
    assert btc_agg[5] == 2       # message_volume

    # Verify Correlations
    # price change = (52000 - 50000) / 50000 = 0.04 (4%)
    # pct change * 100 = 4.0
    # norm change = 4.0 / 2.0 = 2.0
    # divergence = 0.60 (weighted_avg) - 2.0 = -1.4
    assert mock_db_functions['insert_corr'].called
    corr_args = mock_db_functions['insert_corr'].call_args[0][0]
    
    assert len(corr_args) == 1
    btc_corr = corr_args[0]
    assert btc_corr[0] == 'BTC'
    assert btc_corr[5] == 52000.0   # price_close
    assert btc_corr[6] == 4.0       # pct change
    assert round(btc_corr[7], 1) == -1.4   # divergence

    # Verify Divergence Alert fires
    assert mock_db_functions['insert_alert'].called
    alert_kwargs = mock_db_functions['insert_alert'].call_args[1]
    assert alert_kwargs['alert_type'] == 'divergence'
    assert alert_kwargs['asset_symbol'] == 'BTC'
