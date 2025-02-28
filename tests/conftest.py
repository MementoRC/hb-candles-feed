"""
Global test fixtures and configuration for the Candles Feed framework tests.
"""

import asyncio
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from candles_feed.core.candle_data import CandleData
from candles_feed.core.data_processor import DataProcessor
from candles_feed.core.network_client import NetworkClient
from candles_feed.core.network_strategies import RESTPollingStrategy, WebSocketStrategy
from candles_feed.core.protocols import CandleDataAdapter, WSAssistant


# Configure logging for tests
@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """Configure logging for tests."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_throttler():
    """Create a mock throttler for testing."""
    # Create a simple mock with async throttle method
    throttler = MagicMock()
    throttler.execute_task = AsyncMock()
    return throttler


@pytest.fixture
def mock_websocket_assistant():
    """Create a mock websocket assistant for testing."""
    ws = MagicMock(spec=WSAssistant)
    ws.connect = AsyncMock()
    ws.disconnect = AsyncMock()
    ws.send = AsyncMock()
    
    # Setup async iterator for iter_messages
    async def mock_iter_messages():
        # This empty generator allows tests to override it as needed
        if False:
            yield
            
    ws.iter_messages = mock_iter_messages
    
    return ws


@pytest.fixture
def mock_network_client(mock_throttler, mock_websocket_assistant):
    """Create a mock network client for testing."""
    client = MagicMock(spec=NetworkClient)
    client.throttler = mock_throttler
    client.get_rest_data = AsyncMock()
    client.establish_ws_connection = AsyncMock(return_value=mock_websocket_assistant)
    client.send_ws_message = AsyncMock()
    
    return client


@pytest.fixture
def mock_adapter():
    """Create a mock adapter for testing."""
    adapter = MagicMock(spec=CandleDataAdapter)
    
    # Setup basic methods
    adapter.get_trading_pair_format.return_value = "BTCUSDT"
    adapter.get_rest_url.return_value = "https://api.example.com/candles"
    adapter.get_ws_url.return_value = "wss://ws.example.com"
    
    # Setup intervals
    adapter.get_supported_intervals.return_value = {
        "1s": 1,
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400
    }
    adapter.get_ws_supported_intervals.return_value = ["1m", "5m", "15m", "1h"]
    
    # Setup request params
    adapter.get_rest_params.return_value = {
        "symbol": "BTCUSDT",
        "interval": "1m",
        "limit": 1000
    }
    
    # Setup subscription payload
    adapter.get_ws_subscription_payload.return_value = {
        "method": "SUBSCRIBE",
        "params": ["btcusdt@kline_1m"],
        "id": 1
    }
    
    return adapter


@pytest.fixture
def sample_candle_data():
    """Create sample candle data for testing."""
    return CandleData(
        timestamp_raw=int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()),
        open=50000.0,
        high=51000.0,
        low=49000.0,
        close=50500.0,
        volume=100.0,
        quote_asset_volume=5000000.0,
        n_trades=1000,
        taker_buy_base_volume=60.0,
        taker_buy_quote_volume=3000000.0
    )


@pytest.fixture
def sample_candles() -> List[CandleData]:
    """Create a list of sample candles for testing."""
    base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())
    
    return [
        CandleData(
            timestamp_raw=base_time,
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=100.0
        ),
        CandleData(
            timestamp_raw=base_time + 60,
            open=50500.0,
            high=52000.0,
            low=50000.0,
            close=51500.0,
            volume=150.0
        ),
        CandleData(
            timestamp_raw=base_time + 120,
            open=51500.0,
            high=52500.0,
            low=51000.0,
            close=52000.0,
            volume=200.0
        ),
        CandleData(
            timestamp_raw=base_time + 180,
            open=52000.0,
            high=53000.0,
            low=51500.0,
            close=52500.0,
            volume=250.0
        )
    ]


@pytest.fixture
def candlestick_response_binance():
    """Create a sample Binance REST API response."""
    base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()) * 1000  # Binance uses milliseconds
    
    return [
        [
            base_time,
            "50000.0",
            "51000.0",
            "49000.0",
            "50500.0",
            "100.0",
            base_time + 59999,
            "5000000.0",
            1000,
            "60.0",
            "3000000.0",
            "0"
        ],
        [
            base_time + 60000,
            "50500.0",
            "52000.0",
            "50000.0",
            "51500.0",
            "150.0",
            base_time + 119999,
            "7500000.0",
            1500,
            "90.0",
            "4500000.0",
            "0"
        ]
    ]


@pytest.fixture
def websocket_message_binance():
    """Create a sample Binance WebSocket message."""
    base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()) * 1000  # Binance uses milliseconds
    
    return {
        "e": "kline",
        "E": base_time + 100,
        "s": "BTCUSDT",
        "k": {
            "t": base_time,
            "T": base_time + 59999,
            "s": "BTCUSDT",
            "i": "1m",
            "f": 100,
            "L": 200,
            "o": "50000.0",
            "c": "50500.0",
            "h": "51000.0",
            "l": "49000.0",
            "v": "100.0",
            "n": 1000,
            "x": False,
            "q": "5000000.0",
            "V": "60.0",
            "Q": "3000000.0",
            "B": "0"
        }
    }


@pytest.fixture
def candlestick_response_bybit():
    """Create a sample Bybit REST API response."""
    base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()) * 1000  # Bybit uses milliseconds
    
    return {
        "retCode": 0,
        "retMsg": "OK",
        "result": {
            "list": [
                [
                    str(base_time),
                    "50000.0",
                    "51000.0",
                    "49000.0",
                    "50500.0",
                    "100.0",
                    "5000000.0"
                ],
                [
                    str(base_time + 60000),
                    "50500.0",
                    "52000.0",
                    "50000.0",
                    "51500.0",
                    "150.0",
                    "7500000.0"
                ]
            ],
            "category": "spot"
        }
    }


@pytest.fixture
def websocket_message_bybit():
    """Create a sample Bybit WebSocket message."""
    base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()) * 1000  # Bybit uses milliseconds
    
    return {
        "topic": "kline.1m.BTCUSDT",
        "data": [
            {
                "start": base_time,
                "end": base_time + 59999,
                "interval": "1",
                "open": "50000.0",
                "close": "50500.0",
                "high": "51000.0",
                "low": "49000.0",
                "volume": "100.0",
                "turnover": "5000000.0",
                "confirm": False,
                "timestamp": base_time + 30000
            }
        ],
        "ts": base_time + 30000,
        "type": "snapshot"
    }


@pytest.fixture
def candlestick_response_coinbase():
    """Create a sample Coinbase REST API response."""
    base_time = datetime(2023, 1, 1, tzinfo=timezone.utc).isoformat()
    
    return {
        "candles": [
            {
                "start": base_time,
                "low": "49000.0",
                "high": "51000.0",
                "open": "50000.0",
                "close": "50500.0",
                "volume": "100.0"
            },
            {
                "start": (datetime(2023, 1, 1, 0, 1, tzinfo=timezone.utc)).isoformat(),
                "low": "50000.0",
                "high": "52000.0",
                "open": "50500.0",
                "close": "51500.0",
                "volume": "150.0"
            }
        ]
    }


@pytest.fixture
def websocket_message_coinbase():
    """Create a sample Coinbase WebSocket message."""
    base_time = datetime(2023, 1, 1, tzinfo=timezone.utc).isoformat()
    
    return {
        "channel": "candles",
        "client_id": "test-client",
        "timestamp": datetime(2023, 1, 1, 0, 0, 1, tzinfo=timezone.utc).isoformat(),
        "sequence_num": 1234,
        "events": [
            {
                "type": "candle",
                "candles": [
                    {
                        "start": base_time,
                        "low": "49000.0",
                        "high": "51000.0",
                        "open": "50000.0",
                        "close": "50500.0",
                        "volume": "100.0"
                    }
                ]
            }
        ]
    }


@pytest.fixture
def candlestick_response_kraken():
    """Create a sample Kraken REST API response."""
    base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())
    
    return {
        "error": [],
        "result": {
            "XXBTZUSD": [
                [
                    base_time,
                    "50000.0",
                    "51000.0",
                    "49000.0",
                    "50500.0",
                    "100.0",
                    "5000000.0"
                ],
                [
                    base_time + 60,
                    "50500.0",
                    "52000.0",
                    "50000.0",
                    "51500.0",
                    "150.0",
                    "7500000.0"
                ]
            ],
            "last": base_time + 120
        }
    }


@pytest.fixture
def websocket_message_kraken():
    """Create a sample Kraken WebSocket message."""
    base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())
    
    return {
        "channelID": 42,
        "channelName": "ohlc-1",
        "pair": "XBT/USD",
        "data": [
            [
                base_time,
                "50000.0",
                "50500.0",
                "51000.0",
                "49000.0",
                "50500.0", 
                "100.0",
                base_time + 60,
                "5000000.0"
            ]
        ]
    }


@pytest.fixture
def candlestick_response_kucoin():
    """Create a sample KuCoin REST API response."""
    base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())
    
    return {
        "code": "200000",
        "data": {
            "candles": [
                [
                    str(base_time),
                    "50000.0",
                    "50500.0",
                    "51000.0",
                    "49000.0",
                    "100.0",
                    "5000000.0"
                ],
                [
                    str(base_time + 60),
                    "50500.0",
                    "51500.0",
                    "52000.0",
                    "50000.0",
                    "150.0",
                    "7500000.0"
                ]
            ],
            "type": "1min"
        }
    }


@pytest.fixture
def websocket_message_kucoin():
    """Create a sample KuCoin WebSocket message."""
    base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())
    
    return {
        "type": "message",
        "topic": "/market/candles:BTC-USDT_1min",
        "subject": "trade.candles.update",
        "data": {
            "symbol": "BTC-USDT",
            "candles": [
                str(base_time),
                "50000.0",
                "50500.0",
                "51000.0",
                "49000.0",
                "100.0",
                "5000000.0"
            ],
            "time": base_time * 1000
        }
    }


@pytest.fixture
def candlestick_response_okx():
    """Create a sample OKX REST API response."""
    base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()) * 1000  # OKX uses milliseconds
    
    return {
        "code": "0",
        "msg": "",
        "data": [
            [
                str(base_time),
                "50000.0",
                "50500.0",
                "51000.0",
                "49000.0",
                "100.0",
                "5000000.0"
            ],
            [
                str(base_time + 60000),
                "50500.0",
                "51500.0",
                "52000.0",
                "50000.0",
                "150.0",
                "7500000.0"
            ]
        ]
    }


@pytest.fixture
def websocket_message_okx():
    """Create a sample OKX WebSocket message."""
    base_time = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp()) * 1000  # OKX uses milliseconds
    
    return {
        "arg": {
            "channel": "candle1m",
            "instId": "BTC-USDT"
        },
        "data": [
            [
                str(base_time),
                "50000.0",
                "51000.0",
                "49000.0",
                "50500.0",
                "100.0",
                "5000000.0"
            ]
        ]
    }


@pytest.fixture
def data_processor():
    """Create a data processor for testing."""
    return MagicMock(spec=DataProcessor)


@pytest.fixture
def candles_deque():
    """Create a deque for storing candles."""
    return deque(maxlen=100)


@pytest.fixture
def websocket_strategy(mock_network_client, mock_adapter, data_processor, candles_deque):
    """Create a WebSocket strategy for testing."""
    return WebSocketStrategy(
        network_client=mock_network_client,
        adapter=mock_adapter,
        trading_pair="BTC-USDT",
        interval="1m",
        data_processor=data_processor,
        candles_store=candles_deque
    )


@pytest.fixture
def rest_polling_strategy(mock_network_client, mock_adapter, data_processor, candles_deque):
    """Create a REST polling strategy for testing."""
    return RESTPollingStrategy(
        network_client=mock_network_client,
        adapter=mock_adapter,
        trading_pair="BTC-USDT",
        interval="1m",
        data_processor=data_processor,
        candles_store=candles_deque
    )