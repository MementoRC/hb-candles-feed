"""
Tests for the CCXT base adapter functionality.
"""

from unittest.mock import Mock, patch

import pytest

from candles_feed.adapters.ccxt.ccxt_base_adapter import CCXTBaseAdapter


class TestCCXTBaseAdapter:
    """Tests for the CCXTBaseAdapter class."""

    class MockCCXTAdapter(CCXTBaseAdapter):
        """Mock CCXT adapter for testing."""

        exchange_name = "binance"
        market_type = "spot"

        def _get_rest_url(self) -> str:
            """Get REST API URL for testing."""
            return "https://api.binance.com/api/v3/klines"

    @patch("ccxt.binance")
    def test_init_creates_exchange(self, mock_binance):
        """Test initialization creates CCXT exchange instance."""
        # Setup mock
        mock_exchange = Mock()
        mock_binance.return_value = mock_exchange

        # Create adapter
        adapter = self.MockCCXTAdapter()

        # Verify exchange was created with correct options
        mock_binance.assert_called_once_with(
            {"enableRateLimit": True, "options": {"defaultType": "spot"}}
        )

        # Verify exchange is stored
        assert adapter.exchange == mock_exchange

    @patch("ccxt.binance")
    def test_trading_pair_format_conversion(self, mock_binance):
        """Test trading pair format conversion."""
        # Setup
        adapter = self.MockCCXTAdapter()

        # Test
        result = adapter.get_trading_pair_format("BTC-USDT")

        # Verify
        assert result == "BTC/USDT"

    @patch("ccxt.binance")
    def test_get_rest_params(self, mock_binance):
        """Test get_rest_params returns correct parameters."""
        # Setup
        adapter = self.MockCCXTAdapter()

        # Test with all parameters (end_time no longer supported by protocol)
        result = adapter._get_rest_params(
            trading_pair="BTC-USDT",
            interval="1m",
            start_time=1620000000,
            limit=100,
        )

        # Verify
        assert result["symbol"] == "BTC/USDT"
        assert result["timeframe"] == "1m"
        assert result["since"] == 1620000000 * 1000  # Converted to milliseconds
        assert result["limit"] == 100

        # Test with minimal parameters
        result = adapter._get_rest_params(trading_pair="BTC-USDT", interval="1m")

        # Verify
        assert result["symbol"] == "BTC/USDT"
        assert result["timeframe"] == "1m"
        assert result["since"] is None
        assert result["limit"] == 500  # Default value

    @patch("ccxt.binance")
    def test_parse_rest_response(self, mock_binance):
        """Test parse_rest_response converts OHLCV data correctly."""
        # Setup
        adapter = self.MockCCXTAdapter()

        # Mock OHLCV data (timestamp, open, high, low, close, volume)
        ohlcv_data = [
            [1620000000000, 50000.0, 51000.0, 49000.0, 50500.0, 10.5],
            [1620060000000, 50500.0, 52000.0, 50000.0, 51500.0, 15.2],
        ]

        # Test
        result = adapter._parse_rest_response(ohlcv_data)

        # Verify
        assert len(result) == 2

        # First candle
        assert result[0].timestamp == 1620000000  # Converted to seconds
        assert result[0].open == 50000.0
        assert result[0].high == 51000.0
        assert result[0].low == 49000.0
        assert result[0].close == 50500.0
        assert result[0].volume == 10.5

        # Second candle
        assert result[1].timestamp == 1620060000  # Converted to seconds
        assert result[1].open == 50500.0
        assert result[1].high == 52000.0
        assert result[1].low == 50000.0
        assert result[1].close == 51500.0
        assert result[1].volume == 15.2

    @patch("ccxt.binance")
    def test_fetch_rest_candles_synchronous(self, mock_binance):
        """Test fetch_rest_candles_synchronous calls CCXT correctly."""
        # Setup
        mock_exchange = Mock()
        mock_binance.return_value = mock_exchange

        # Mock fetch_ohlcv response
        mock_exchange.fetch_ohlcv.return_value = [
            [1620000000000, 50000.0, 51000.0, 49000.0, 50500.0, 10.5]
        ]

        adapter = self.MockCCXTAdapter()

        # Test
        result = adapter.fetch_rest_candles_synchronous(
            trading_pair="BTC-USDT", interval="1m", start_time=1620000000, limit=100
        )

        # Verify fetch_ohlcv was called with correct parameters
        mock_exchange.fetch_ohlcv.assert_called_once_with(
            symbol="BTC/USDT",
            timeframe="1m",
            since=1620000000 * 1000,  # Converted to milliseconds
            limit=100,
        )

        # Verify result
        assert len(result) == 1
        assert result[0].timestamp == 1620000000
        assert result[0].open == 50000.0
        assert result[0].high == 51000.0
        assert result[0].low == 49000.0
        assert result[0].close == 50500.0
        assert result[0].volume == 10.5

    @patch("ccxt.binance")
    def test_get_supported_intervals(self, mock_binance):
        """Test get_supported_intervals returns correct intervals."""
        # Setup
        mock_exchange = Mock()
        mock_exchange.timeframes = {"1m": "1m", "5m": "5m", "1h": "1h", "1d": "1d"}
        mock_binance.return_value = mock_exchange

        adapter = self.MockCCXTAdapter()

        # Test
        result = adapter.get_supported_intervals()

        # Verify common timeframes are converted correctly
        assert "1m" in result
        assert result["1m"] == 60
        assert "1h" in result
        assert result["1h"] == 3600
        assert "1d" in result
        assert result["1d"] == 86400

    @patch("ccxt.binance")
    def test_websocket_methods_raise_not_implemented(self, mock_binance):
        """Test WebSocket methods raise NotImplementedError."""
        # Setup
        adapter = self.MockCCXTAdapter()

        # Verify WebSocket methods raise NotImplementedError
        with pytest.raises(NotImplementedError):
            adapter.get_ws_url()

        with pytest.raises(NotImplementedError):
            adapter.get_ws_supported_intervals()

        with pytest.raises(NotImplementedError):
            adapter.get_ws_subscription_payload("BTC-USDT", "1m")

        with pytest.raises(NotImplementedError):
            adapter.parse_ws_message({})

    @patch("ccxt.binance")
    @pytest.mark.asyncio
    async def test_fetch_rest_candles_async_wrapper(self, mock_binance):
        """Test async fetch_rest_candles wraps synchronous method."""
        # Setup
        mock_exchange = Mock()
        mock_exchange.fetch_ohlcv.return_value = [
            [1620000000000, 50000.0, 51000.0, 49000.0, 50500.0, 10.5]
        ]
        mock_binance.return_value = mock_exchange

        adapter = self.MockCCXTAdapter()

        # Mock the synchronous method to verify it's called
        original_sync_method = adapter.fetch_rest_candles_synchronous
        adapter.fetch_rest_candles_synchronous = Mock(side_effect=original_sync_method)

        # Test
        result = await adapter.fetch_rest_candles(
            trading_pair="BTC-USDT", interval="1m", start_time=1620000000, limit=100
        )

        # Verify synchronous method was called with correct parameters - positional arguments are fine
        adapter.fetch_rest_candles_synchronous.assert_called_once()
        args, kwargs = adapter.fetch_rest_candles_synchronous.call_args
        assert args[0] == "BTC-USDT"  # trading_pair
        assert args[1] == "1m"  # interval
        assert args[2] == 1620000000  # start_time
        assert args[3] == 100  # limit

        # Verify result
        assert len(result) == 1
        assert result[0].timestamp == 1620000000
        assert result[0].open == 50000.0
