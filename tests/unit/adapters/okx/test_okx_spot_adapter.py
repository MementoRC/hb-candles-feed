"""
Unit tests for the OKXSpotAdapter class.
"""
from unittest import IsolatedAsyncioTestCase

import aiohttp
import pytest

from candles_feed import CandleData
from candles_feed.adapters.okx.constants import (
    CANDLES_ENDPOINT,
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    SPOT_REST_URL,
    WS_INTERVALS,
    SPOT_WSS_URL,
)
from candles_feed.adapters.okx.spot_adapter import OKXSpotAdapter
from candles_feed.mocking_resources.core.server import MockedExchangeServer
from candles_feed.mocking_resources.exchanges.okx import OKXSpotPlugin


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
        assert self.adapter.get_rest_url() == f"{SPOT_REST_URL}{CANDLES_ENDPOINT}"

    def test_get_ws_url(self):
        """Test WebSocket URL retrieval."""
        assert self.adapter.get_ws_url() == SPOT_WSS_URL

    def test_get_rest_params_minimal(self):
        """Test REST params with minimal parameters."""
        params = self.adapter.get_rest_params(self.trading_pair, self.interval)

        assert params["instId"] == "BTC/USDT"  # Hyphen is replaced with slash
        assert params["bar"] == INTERVAL_TO_EXCHANGE_FORMAT[self.interval]
        assert params["limit"] == MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST
        assert "after" not in params
        assert "before" not in params

    def test_get_rest_params_full(self):
        """Test REST params with all parameters."""
        start_time = 1622505600  # 2021-06-01 00:00:00 UTC
        end_time = 1622592000  # 2021-06-02 00:00:00 UTC
        limit = 200

        params = self.adapter.get_rest_params(
            self.trading_pair,
            self.interval,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

        assert params["instId"] == "BTC/USDT"
        assert params["bar"] == INTERVAL_TO_EXCHANGE_FORMAT[self.interval]
        assert params["limit"] == limit
        assert params["after"] == start_time * 1000  # Convert to milliseconds
        assert params["before"] == end_time * 1000  # Convert to milliseconds

    def test_parse_rest_response(self, websocket_response_okx):
        """Test parsing REST API response."""
        candles = self.adapter.parse_rest_response(websocket_response_okx)

        # Verify response parsing
        assert len(candles) == 2

        # Check first candle
        assert candles[0].timestamp == 1672531200  # 2023-01-01 00:00:00 UTC in seconds
        assert candles[0].open == 50000.0
        assert candles[0].high == 50500.0
        assert candles[0].low == 51000.0
        assert candles[0].close == 49000.0
        assert candles[0].volume == 100.0
        assert candles[0].quote_asset_volume == 5000000.0

        # Check second candle
        assert candles[1].timestamp == 1672531260  # 2023-01-01 00:01:00 UTC in seconds
        assert candles[1].open == 51500.0
        assert candles[1].high == 50500.0
        assert candles[1].low == 52000.0
        assert candles[1].close == 50000.0
        assert candles[1].volume == 150.0
        assert candles[1].quote_asset_volume == 7500000.0

    def test_get_ws_subscription_payload(self):
        """Test WebSocket subscription payload generation."""
        payload = self.adapter.get_ws_subscription_payload(self.trading_pair, self.interval)

        assert payload["op"] == "subscribe"
        assert len(payload["args"]) == 1
        assert payload["args"][0]["channel"] == f"candle{INTERVAL_TO_EXCHANGE_FORMAT[self.interval]}"
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
                "channel": f"candle{INTERVAL_TO_EXCHANGE_FORMAT[self.interval]}",
                "instId": "BTC/USDT",
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

class TestOKXSpotAdapterWithMockedExchange(IsolatedAsyncioTestCase):
    """Test suite for the OKXSpotAdapter class."""

    @pytest.mark.asyncio
    async def asyncSetUp(self):
        """Setup method called before each test."""
        self.adapter = OKXSpotAdapter()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"
        self.start_time = 1622505600  # 2021-06-01 00:00:00 UTC
        self.end_time = 1622592000  # 2021-06-02 00:00:00 UTC

        # MockedExchangeServer setup
        self.plugin = OKXSpotPlugin()
        # Use a fixed port instead of dynamic port 0
        self.mock_server = MockedExchangeServer(self.plugin, "127.0.0.1", 8080)
        await self.mock_server.start()
        self.mock_server_url = self.mock_server.url
        
        # Monkey patch the adapter's get_rest_url method to use our mock server URL
        # Save the original method
        self.original_get_rest_url = OKXSpotAdapter.get_rest_url
        # The lambda needs to handle the self parameter since get_rest_url is called as an instance method
        mock_server_url = self.mock_server_url
        OKXSpotAdapter.get_rest_url = lambda *args: mock_server_url

        # Add mock data
        self.mock_server.add_trading_pair(self.trading_pair, self.interval, 50000.0)

    @pytest.mark.asyncio
    async def asyncTearDown(self):
        # Restore the original method
        OKXSpotAdapter.get_rest_url = self.original_get_rest_url
        await self.mock_server.stop()

    def test_get_trading_pair_format(self):
        """Test trading pair format conversion."""
        assert self.adapter.get_trading_pair_format("BTC-USDT") == "BTC-USDT"
        assert self.adapter.get_trading_pair_format("ETH-BTC") == "ETH-BTC"

    def test_get_rest_url(self):
        """Test REST URL retrieval."""
        assert self.adapter.get_rest_url() == self.mock_server_url

    def test_get_ws_url(self):
        """Test WebSocket URL retrieval."""
        assert self.adapter.get_ws_url().startswith("wss://ws.okx.com:8443/ws/v5/public")

    def test_get_rest_params_minimal(self):
        """Test REST params with minimal parameters."""
        params = self.adapter.get_rest_params(self.trading_pair, self.interval)

        assert params["instId"] == "BTC/USDT"
        assert params["bar"] == "1m"
        assert params["limit"] == 1440
        assert "after" not in params
        assert "before" not in params

    def test_get_rest_params_full(self):
        """Test REST params with all parameters."""
        limit = 200
        params = self.adapter.get_rest_params(
            self.trading_pair, self.interval, start_time=self.start_time, end_time=self.end_time, limit=limit
        )

        assert params["instId"] == "BTC/USDT"
        assert params["bar"] == "1m"
        assert params["limit"] == limit
        assert params["after"] == self.start_time * 1000
        assert params["before"] == self.end_time * 1000

    @pytest.mark.asyncio
    async def test_parse_rest_response(self):
        """Test parsing REST API response."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.mock_server_url}/api/v5/market/candles",
                params=self.adapter.get_rest_params(self.trading_pair, self.interval, limit=2),
            ) as response:
                response_data = await response.json()

        candles = self.adapter.parse_rest_response(response_data)

        assert len(candles) == 2
        assert isinstance(candles[0], CandleData)

    def test_get_ws_subscription_payload(self):
        """Test WebSocket subscription payload generation."""
        payload = self.adapter.get_ws_subscription_payload(self.trading_pair, self.interval)

        assert payload["op"] == "subscribe"
        assert payload["args"][0]["channel"] == "candle1m"
        assert payload["args"][0]["instId"] == "BTC/USDT"

    def test_parse_ws_message_valid(self):
        """Test parsing valid WebSocket message."""
        candle = CandleData(
            timestamp_raw=1672531200,
            open=float("50000.0"),
            high=float("51000.0"),
            low=float("49000.0"),
            close=float("50500.0"),
            volume=float("100.0"),
            quote_asset_volume=float("5000000.0"),
        )
        message = self.plugin.format_ws_candle_message(candle, self.trading_pair, self.interval)

        candles = self.adapter.parse_ws_message(message)

        assert len(candles) == 1
        assert isinstance(candles[0], CandleData)

    def test_parse_ws_message_invalid(self):
        """Test parsing invalid WebSocket message."""
        assert self.adapter.parse_ws_message({"event": "subscribe"}) is None
        assert self.adapter.parse_ws_message(None) is None
        assert self.adapter.parse_ws_message({"arg": {"channel": "candle1m", "instId": "BTC/USDT"}}) is None

    def test_get_supported_intervals(self):
        """Test getting supported intervals."""
        intervals = self.adapter.get_supported_intervals()
        self.assertIsInstance(intervals, dict)
        self.assertIn("1m", intervals)

    def test_get_ws_supported_intervals(self):
        """Test getting WebSocket supported intervals."""
        ws_intervals = self.adapter.get_ws_supported_intervals()
        self.assertIsInstance(ws_intervals, list)
        self.assertIn("1m", ws_intervals)
