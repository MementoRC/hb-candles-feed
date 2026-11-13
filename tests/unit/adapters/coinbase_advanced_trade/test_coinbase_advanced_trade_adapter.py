"""
Unit tests for the CoinbaseAdvancedTradeSpotAdapter class.
"""

from unittest.mock import AsyncMock, MagicMock

from candles_feed.adapters.coinbase_advanced_trade.constants import (
    INTERVAL_TO_GRANULARITY,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    SPOT_CANDLES_ENDPOINT,
    SPOT_REST_URL,
    SPOT_WSS_URL,
    WS_INTERVALS,
)
from candles_feed.adapters.coinbase_advanced_trade.spot_adapter import (
    CoinbaseAdvancedTradeSpotAdapter,
)


class TestCoinbaseAdvancedTradeSpotAdapter:
    """Test suite for the CoinbaseAdvancedTradeSpotAdapter class."""

    def setup_method(self):
        """Setup method called before each test."""
        self.adapter = CoinbaseAdvancedTradeSpotAdapter()
        self.trading_pair = "BTC-USD"
        self.interval = "1m"

    def test_get_trading_pair_format(self):
        """Test trading pair format conversion."""
        # Coinbase keeps the same format
        assert CoinbaseAdvancedTradeSpotAdapter.get_trading_pair_format("BTC-USD") == "BTC-USD"
        assert CoinbaseAdvancedTradeSpotAdapter.get_trading_pair_format("ETH-USDT") == "ETH-USDT"

    def test_get_rest_url(self):
        """Test REST URL retrieval."""
        assert (
            CoinbaseAdvancedTradeSpotAdapter._get_rest_url()
            == f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"
        )

    def test_get_ws_url(self):
        """Test WebSocket URL retrieval."""
        assert self.adapter.get_ws_url() == SPOT_WSS_URL

    def test_get_rest_url_is_public_market_path(self):
        """The candles URL is the public market-data endpoint with a product id template."""
        url = CoinbaseAdvancedTradeSpotAdapter._get_rest_url()

        assert "/brokerage/market/products/{product_id}/candles" in url

    def test_get_rest_params_minimal(self):
        """Without a start time, start/end are derived from limit x interval ending now."""
        params = self.adapter._get_rest_params(self.trading_pair, self.interval)

        assert params["granularity"] == "ONE_MINUTE"
        assert params["limit"] == 350
        assert int(params["end"]) - int(params["start"]) == 350 * INTERVALS[self.interval]

    def test_get_rest_params_full(self):
        """Test REST params with a start time and a limit."""
        start_time = 1622505600  # 2021-06-01 00:00:00 UTC

        params = self.adapter._get_rest_params(
            self.trading_pair, self.interval, start_time=start_time, limit=100
        )

        assert params == {
            "start": str(start_time),
            "end": str(start_time + 100 * INTERVALS[self.interval]),
            "granularity": "ONE_MINUTE",
            "limit": 100,
        }

    def test_get_rest_params_granularity_enums(self):
        """Every supported interval maps to its Coinbase granularity enum."""
        assert INTERVAL_TO_GRANULARITY == {
            "1m": "ONE_MINUTE",
            "5m": "FIVE_MINUTE",
            "15m": "FIFTEEN_MINUTE",
            "1h": "ONE_HOUR",
            "6h": "SIX_HOUR",
            "1d": "ONE_DAY",
        }
        assert set(INTERVAL_TO_GRANULARITY) == set(INTERVALS)

    def test_max_results_per_request_is_350(self):
        """Coinbase returns at most 350 candles per request."""
        assert MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST == 350

    async def test_fetch_rest_candles_formats_product_id(self):
        """The product id is substituted into the URL path."""
        client = MagicMock()
        client.get_rest_data = AsyncMock(return_value={"candles": []})

        await self.adapter.fetch_rest_candles(
            self.trading_pair, self.interval, network_client=client
        )

        _, kwargs = client.get_rest_data.call_args
        assert "BTC-USD" in kwargs["url"]
        assert "{" not in kwargs["url"]

    def test_parse_rest_response(self, candlestick_response_coinbase):
        """Test parsing REST API response."""
        candles = self.adapter._parse_rest_response(candlestick_response_coinbase)

        # Verify response parsing
        assert len(candles) == 2

        # Coinbase uses ISO timestamps
        # Check first candle
        assert isinstance(candles[0].timestamp, int)
        assert candles[0].open == 50000.0
        assert candles[0].high == 51000.0
        assert candles[0].low == 49000.0
        assert candles[0].close == 50500.0
        assert candles[0].volume == 100.0

        # Check second candle
        assert isinstance(candles[1].timestamp, int)
        assert candles[1].open == 50500.0
        assert candles[1].high == 52000.0
        assert candles[1].low == 50000.0
        assert candles[1].close == 51500.0
        assert candles[1].volume == 150.0

    def test_get_ws_subscription_payload(self):
        """Test WebSocket subscription payload generation."""
        payload = self.adapter.get_ws_subscription_payload(self.trading_pair, self.interval)

        assert payload == {
            "type": "subscribe",
            "channel": "candles",
            "product_ids": [self.trading_pair],
        }
        assert "granularity" not in payload

    def test_parse_ws_message_valid(self, websocket_message_coinbase):
        """Test parsing valid WebSocket message."""
        candles = self.adapter.parse_ws_message(websocket_message_coinbase)

        # Verify message parsing
        assert candles is not None
        assert len(candles) == 1

        candle = candles[0]
        assert isinstance(candle.timestamp, int)
        # Stamped with the candle's own start (2023-01-01T00:00:00Z), not the event timestamp
        assert candle.timestamp == 1672531200
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.low == 49000.0
        assert candle.close == 50500.0
        assert candle.volume == 100.0

    def test_parse_ws_message_invalid(self):
        """Test parsing invalid WebSocket message."""
        # Test with non-candle message
        ws_message = {"channel": "heartbeat", "data": "some_data"}
        candles = self.adapter.parse_ws_message(ws_message)
        assert candles is None

        # Test with None
        candles = self.adapter.parse_ws_message(None)
        assert candles is None

        # Test with missing events
        ws_message = {"channel": "candles", "timestamp": "2023-01-01T00:00:00Z"}
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
        assert ws_intervals == WS_INTERVALS == ["5m"]
        assert "5m" in INTERVALS
