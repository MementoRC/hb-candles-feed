"""
Unit tests for the OKXSpotAdapter class.
"""

from unittest.mock import MagicMock

import pytest

from candles_feed.adapters.okx_spot.okx_spot_adapter import OKXSpotAdapter
from candles_feed.adapters.okx_spot.constants import (
    INTERVALS, REST_URL, WSS_URL, WS_INTERVALS, CANDLES_ENDPOINT,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST, INTERVAL_TO_OKX_FORMAT
)
from candles_feed.core.candle_data import CandleData


class TestOKXSpotAdapter:
    """Test suite for the OKXSpotAdapter class."""
    
    def setup_method(self):
        """Setup method called before each test."""
        self.adapter = OKXSpotAdapter()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"
        
    def test_get_trading_pair_format(self):
        """Test trading pair format conversion."""
        # OKX keeps the same format, but later replaces "-" with "/" in requests
        assert self.adapter.get_trading_pair_format("BTC-USDT") == "BTC-USDT"
        assert self.adapter.get_trading_pair_format("ETH-BTC") == "ETH-BTC"
    
    def test_get_rest_url(self):
        """Test REST URL retrieval."""
        assert self.adapter.get_rest_url() == f"{REST_URL}{CANDLES_ENDPOINT}"
    
    def test_get_ws_url(self):
        """Test WebSocket URL retrieval."""
        assert self.adapter.get_ws_url() == WSS_URL
    
    def test_get_rest_params_minimal(self):
        """Test REST params with minimal parameters."""
        params = self.adapter.get_rest_params(self.trading_pair, self.interval)
        
        assert params["instId"] == "BTC/USDT"  # Hyphen is replaced with slash
        assert params["bar"] == INTERVAL_TO_OKX_FORMAT[self.interval]
        assert params["limit"] == MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST
        assert "after" not in params
        assert "before" not in params
    
    def test_get_rest_params_full(self):
        """Test REST params with all parameters."""
        start_time = 1622505600  # 2021-06-01 00:00:00 UTC
        end_time = 1622592000    # 2021-06-02 00:00:00 UTC
        limit = 200
        
        params = self.adapter.get_rest_params(
            self.trading_pair, 
            self.interval, 
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        assert params["instId"] == "BTC/USDT"
        assert params["bar"] == INTERVAL_TO_OKX_FORMAT[self.interval]
        assert params["limit"] == limit
        assert params["after"] == start_time
        assert params["before"] == end_time
    
    def test_parse_rest_response(self, candlestick_response_okx):
        """Test parsing REST API response."""
        candles = self.adapter.parse_rest_response(candlestick_response_okx)
        
        # Verify response parsing
        assert len(candles) == 2
        
        # Check first candle
        assert candles[0].timestamp == 1672531200  # 2023-01-01 00:00:00 UTC in seconds
        assert candles[0].open == 50000.0
        assert candles[0].high == 51000.0
        assert candles[0].low == 49000.0
        assert candles[0].close == 50500.0
        assert candles[0].volume == 100.0
        assert candles[0].quote_asset_volume == 5000000.0
        
        # Check second candle
        assert candles[1].timestamp == 1672531260  # 2023-01-01 00:01:00 UTC in seconds
        assert candles[1].open == 50500.0
        assert candles[1].high == 52000.0
        assert candles[1].low == 50000.0
        assert candles[1].close == 51500.0
        assert candles[1].volume == 150.0
        assert candles[1].quote_asset_volume == 7500000.0
    
    def test_get_ws_subscription_payload(self):
        """Test WebSocket subscription payload generation."""
        payload = self.adapter.get_ws_subscription_payload(self.trading_pair, self.interval)
        
        assert payload["op"] == "subscribe"
        assert len(payload["args"]) == 1
        assert payload["args"][0]["channel"] == f"candle{INTERVAL_TO_OKX_FORMAT[self.interval]}"
        assert payload["args"][0]["instId"] == "BTC/USDT"
    
    def test_parse_ws_message_valid(self, websocket_message_okx):
        """Test parsing valid WebSocket message."""
        candles = self.adapter.parse_ws_message(websocket_message_okx)
        
        # Verify message parsing
        assert candles is not None
        assert len(candles) == 1
        
        candle = candles[0]
        assert candle.timestamp == 1672531200  # 2023-01-01 00:00:00 UTC in seconds
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0
        assert candle.quote_asset_volume == 5000000.0
    
    def test_parse_ws_message_invalid(self):
        """Test parsing invalid WebSocket message."""
        # Test with non-candle message
        ws_message = {"event": "subscribe"}
        candles = self.adapter.parse_ws_message(ws_message)
        assert candles is None
        
        # Test with None
        candles = self.adapter.parse_ws_message(None)
        assert candles is None
        
        # Test with missing data field
        ws_message = {
            "arg": {
                "channel": f"candle{INTERVAL_TO_OKX_FORMAT[self.interval]}",
                "instId": "BTC/USDT"
            }
        }
        candles = self.adapter.parse_ws_message(ws_message)
        assert candles is None
    
    def test_get_supported_intervals(self):
        """Test getting supported intervals."""
        intervals = self.adapter.get_supported_intervals()
        
        # Verify intervals match the expected values
        assert intervals == INTERVALS
        assert "1m" in intervals
        assert intervals["1m"] == 60
        assert "1h" in intervals
        assert intervals["1h"] == 3600
        assert "1d" in intervals
        assert intervals["1d"] == 86400
    
    def test_get_ws_supported_intervals(self):
        """Test getting WebSocket supported intervals."""
        ws_intervals = self.adapter.get_ws_supported_intervals()
        
        # Verify WS intervals match the expected values
        assert ws_intervals == WS_INTERVALS
        assert "1m" in ws_intervals
        assert "1h" in ws_intervals