"""
Unit tests for the ExchangePlugin abstract base class in mocking_resources.
"""

from typing import Any
from unittest.mock import MagicMock

import pytest
from aiohttp import web

from candles_feed.adapters.binance.spot_adapter import BinanceSpotAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.mocking_resources.core.exchange_plugin import ExchangePlugin
from candles_feed.mocking_resources.core.exchange_type import ExchangeType


class TestExchangePlugin:
    """Tests for the ExchangePlugin abstract base class."""

    class ConcreteExchangePlugin(ExchangePlugin):
        """A concrete implementation of ExchangePlugin for testing."""

        @property
        def rest_routes(self) -> dict[str, tuple[str, str]]:
            return {"/api/test": ("GET", "handle_test"), "/api/candles": ("GET", "handle_klines")}

        @property
        def ws_routes(self) -> dict[str, str]:
            return {"/ws": "handle_websocket"}

        def format_rest_candles(
            self, candles: list[CandleData], trading_pair: str, interval: str
        ) -> Any:
            return [
                {
                    "timestamp": c.timestamp,
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume,
                }
                for c in candles
            ]

        def format_ws_candle_message(
            self, candle: CandleData, trading_pair: str, interval: str, is_final: bool = False
        ) -> Any:
            return {
                "type": "candle",
                "data": {
                    "timestamp": candle.timestamp,
                    "trading_pair": trading_pair,
                    "interval": interval,
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume,
                    "final": is_final,
                },
            }

        def parse_ws_subscription(self, message: dict) -> list[tuple[str, str]]:
            if message.get("type") == "subscribe":
                channel = message.get("channel")
                if channel == "candles":
                    trading_pair = message.get("trading_pair")
                    interval = message.get("interval")
                    return [(trading_pair, interval)]
            return []

        def create_ws_subscription_success(
            self, message: dict, subscriptions: list[tuple[str, str]]
        ) -> dict:
            return {
                "type": "subscribed",
                "channel": message.get("channel"),
                "subscriptions": [
                    {"trading_pair": tp, "interval": interval} for tp, interval in subscriptions
                ],
            }

        def create_ws_subscription_key(self, trading_pair: str, interval: str) -> str:
            return f"{trading_pair}_{interval}"

        def parse_rest_candles_params(self, request: web.Request) -> dict[str, Any]:
            params = request.query
            return {
                "symbol": params.get("symbol"),
                "interval": params.get("interval"),
                "start_time": params.get("start"),
                "end_time": params.get("end"),
                "limit": params.get("limit", "100"),
            }

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.exchange_type = ExchangeType.BINANCE_SPOT
        self.plugin = self.ConcreteExchangePlugin(self.exchange_type, BinanceSpotAdapter)

    def test_init(self):
        """Test initialization of the plugin."""
        assert self.plugin.exchange_type == self.exchange_type

    def test_rest_routes(self):
        """Test the rest_routes property."""
        routes = self.plugin.rest_routes
        assert isinstance(routes, dict)
        assert len(routes) == 2
        assert routes["/api/test"] == ("GET", "handle_test")
        assert routes["/api/candles"] == ("GET", "handle_klines")

    def test_ws_routes(self):
        """Test the ws_routes property."""
        routes = self.plugin.ws_routes
        assert isinstance(routes, dict)
        assert len(routes) == 1
        assert routes["/ws"] == "handle_websocket"

    def test_format_rest_candles(self):
        """Test formatting REST candles response."""
        candles = [
            CandleData(
                timestamp_raw=1613677200,
                open=50000.0,
                high=50500.0,
                low=49500.0,
                close=50200.0,
                volume=10.0,
                quote_asset_volume=500000.0,
                n_trades=100,
                taker_buy_base_volume=5.0,
                taker_buy_quote_volume=250000.0,
            )
        ]

        result = self.plugin.format_rest_candles(candles, "BTCUSDT", "1m")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["timestamp"] == candles[0].timestamp
        assert result[0]["open"] == candles[0].open
        assert result[0]["high"] == candles[0].high
        assert result[0]["low"] == candles[0].low
        assert result[0]["close"] == candles[0].close
        assert result[0]["volume"] == candles[0].volume

    def test_format_ws_candle_message(self):
        """Test formatting WebSocket candle message."""
        candle = CandleData(
            timestamp_raw=1613677200,
            open=50000.0,
            high=50500.0,
            low=49500.0,
            close=50200.0,
            volume=10.0,
            quote_asset_volume=500000.0,
            n_trades=100,
            taker_buy_base_volume=5.0,
            taker_buy_quote_volume=250000.0,
        )

        result = self.plugin.format_ws_candle_message(candle, "BTCUSDT", "1m", is_final=True)

        assert isinstance(result, dict)
        assert result["type"] == "candle"
        assert result["data"]["timestamp"] == candle.timestamp
        assert result["data"]["trading_pair"] == "BTCUSDT"
        assert result["data"]["interval"] == "1m"
        assert result["data"]["open"] == candle.open
        assert result["data"]["high"] == candle.high
        assert result["data"]["low"] == candle.low
        assert result["data"]["close"] == candle.close
        assert result["data"]["volume"] == candle.volume
        assert result["data"]["final"] is True

    def test_parse_ws_subscription(self):
        """Test parsing WebSocket subscription message."""
        message = {
            "type": "subscribe",
            "channel": "candles",
            "trading_pair": "BTCUSDT",
            "interval": "1m",
        }

        result = self.plugin.parse_ws_subscription(message)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == ("BTCUSDT", "1m")

    def test_create_ws_subscription_success(self):
        """Test creating WebSocket subscription success response."""
        message = {
            "type": "subscribe",
            "channel": "candles",
            "trading_pair": "BTCUSDT",
            "interval": "1m",
        }
        subscriptions = [("BTCUSDT", "1m"), ("ETHUSDT", "5m")]

        result = self.plugin.create_ws_subscription_success(message, subscriptions)

        assert isinstance(result, dict)
        assert result["type"] == "subscribed"
        assert result["channel"] == "candles"
        assert len(result["subscriptions"]) == 2
        assert result["subscriptions"][0]["trading_pair"] == "BTCUSDT"
        assert result["subscriptions"][0]["interval"] == "1m"
        assert result["subscriptions"][1]["trading_pair"] == "ETHUSDT"
        assert result["subscriptions"][1]["interval"] == "5m"

    def test_create_ws_subscription_key(self):
        """Test creating WebSocket subscription key."""
        result = self.plugin.create_ws_subscription_key("BTCUSDT", "1m")
        assert result == "BTCUSDT_1m"

    def test_parse_rest_candles_params(self):
        """Test parsing REST candles parameters."""
        # Create a mock request
        mock_request = MagicMock()
        mock_request.query = {
            "symbol": "BTCUSDT",
            "interval": "1m",
            "start": "1613677200000",
            "end": "1613680800000",
            "limit": "500",
        }

        result = self.plugin.parse_rest_candles_params(mock_request)

        assert isinstance(result, dict)
        assert result["symbol"] == "BTCUSDT"
        assert result["interval"] == "1m"
        assert result["start_time"] == "1613677200000"
        assert result["end_time"] == "1613680800000"
        assert result["limit"] == "500"

    def test_normalize_trading_pair(self):
        """Test normalizing trading pair."""
        result = self.plugin.normalize_trading_pair("btcusdt")
        assert result == "BTCUSDT"
