"""
Unit tests for the BybitBaseAdapter class.
"""

from candles_feed.adapters.bybit.base_adapter import BybitBaseAdapter
from candles_feed.adapters.bybit.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    WS_INTERVALS,
)


class ConcreteBybitAdapter(BybitBaseAdapter):
    """Concrete implementation of BybitBaseAdapter for testing."""

    @staticmethod
    def _get_rest_url() -> str:
        return f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    @staticmethod
    def _get_ws_url() -> str:
        return "wss://test.bybit.com/ws"

    def get_category_param(self) -> str | None:
        return "test"


class TestBybitBaseAdapter:
    """Test suite for the BybitBaseAdapter class."""

    def setup_method(self):
        """Setup method called before each test."""
        self.adapter = ConcreteBybitAdapter()
        self.trading_pair = "BTC-USDT"
        self.interval = "1m"

    def test_get_trading_pair_format(self):
        """Test trading pair format conversion."""
        # Test standard case
        assert ConcreteBybitAdapter.get_trading_pair_format("BTC-USDT") == "BTCUSDT"

        # Test with multiple hyphens
        assert ConcreteBybitAdapter.get_trading_pair_format("BTC-USDT-PERP") == "BTCUSDTPERP"

        # Test with lowercase
        assert ConcreteBybitAdapter.get_trading_pair_format("btc-usdt") == "btcusdt"

    def test_get_rest_url(self):
        """Test REST URL retrieval."""
        assert ConcreteBybitAdapter._get_rest_url() == f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    def test_get_rest_params_minimal(self):
        """Test REST params with minimal parameters."""
        params = self.adapter._get_rest_params(self.trading_pair, self.interval)

        assert params["symbol"] == "BTCUSDT"
        assert params["interval"] == INTERVAL_TO_EXCHANGE_FORMAT.get(self.interval, self.interval)
        assert params["limit"] == MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST
        assert params["category"] == "test"  # From our concrete implementation
        assert "start" not in params
        assert "end" not in params

    def test_get_rest_params_full(self):
        """Test REST params with all parameters."""
        start_time = 1622505600  # 2021-06-01 00:00:00 UTC
        limit = 500

        params = self.adapter._get_rest_params(
            self.trading_pair, self.interval, start_time=start_time, limit=limit
        )

        assert params["symbol"] == "BTCUSDT"
        assert params["interval"] == INTERVAL_TO_EXCHANGE_FORMAT.get(self.interval, self.interval)
        assert params["limit"] == limit
        assert params["category"] == "test"  # From our concrete implementation
        assert params["start"] == start_time * 1000  # Should be in milliseconds
        assert "end" not in params

    def test_parse_rest_response(self, candlestick_response_bybit):
        """Test parsing REST API response."""
        candles = self.adapter._parse_rest_response(candlestick_response_bybit)

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

    def test_parse_rest_response_none(self):
        """Test parsing None REST API response."""
        candles = self.adapter._parse_rest_response(None)
        assert candles == []

    def test_get_ws_subscription_payload(self):
        """Test WebSocket subscription payload generation."""
        payload = self.adapter.get_ws_subscription_payload(self.trading_pair, self.interval)

        assert payload["op"] == "subscribe"
        assert len(payload["args"]) == 1
        assert (
            payload["args"][0]
            == f"kline.{INTERVAL_TO_EXCHANGE_FORMAT.get(self.interval)}.{ConcreteBybitAdapter.get_trading_pair_format(self.trading_pair)}"
        )

    def test_parse_ws_message_valid(self, websocket_message_bybit):
        """Test parsing valid WebSocket message."""
        candles = self.adapter.parse_ws_message(websocket_message_bybit)

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
        # Test with non-kline message
        ws_message = {"method": "ping", "data": "some_data"}
        candles = self.adapter.parse_ws_message(ws_message)
        assert candles is None

        # Test with None
        candles = self.adapter.parse_ws_message(None)
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
