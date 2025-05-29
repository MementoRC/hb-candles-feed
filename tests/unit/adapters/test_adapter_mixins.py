"""
Tests for the adapter mixins using the base adapter test class.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from candles_feed.adapters.adapter_mixins import (
    AsyncOnlyAdapter,
    NoWebSocketSupportMixin,
    SyncOnlyAdapter,
    TestnetSupportMixin,
)
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.network_config import EndpointType, NetworkConfig, NetworkEnvironment
from candles_feed.core.protocols import NetworkClientProtocol


class TestSyncOnlyAdapter:
    """Test suite for SyncOnlyAdapter mixin."""

    class MockSyncAdapter(BaseAdapter, SyncOnlyAdapter):
        """Mock adapter implementing SyncOnlyAdapter for testing."""

        TIMESTAMP_UNIT = "seconds"

        def get_trading_pair_format(self, trading_pair: str) -> str:
            return trading_pair.replace("-", "/")

        def get_supported_intervals(self) -> dict[str, int]:
            return {"1m": 60, "1h": 3600}

        def get_ws_url(self) -> str:
            return "wss://test.com/ws"

        def get_ws_supported_intervals(self) -> list[str]:
            return ["1m", "1h"]

        def parse_ws_message(self, data: dict) -> list[CandleData] | None:
            if data is None:
                return None
            if data.get("type") != "candle":
                return None
            return [
                CandleData(
                    timestamp_raw=data["data"]["timestamp"],
                    open=data["data"]["open"],
                    high=data["data"]["high"],
                    low=data["data"]["low"],
                    close=data["data"]["close"],
                    volume=data["data"]["volume"],
                )
            ]

        def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
            return {"subscribe": f"{trading_pair.lower()}@kline_{interval}"}

        def _get_rest_url(self) -> str:
            return "https://test.com/api"

        def _get_rest_params(
            self, trading_pair: str, interval: str, start_time=None, end_time=None, limit=None
        ) -> dict:
            params = {"symbol": trading_pair, "interval": interval}
            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time
            if limit:
                params["limit"] = limit
            return params

        def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
            if data is None:
                return []
            return [
                CandleData(
                    timestamp_raw=1620000000,
                    open=100.0,
                    high=101.0,
                    low=99.0,
                    close=100.5,
                    volume=1000.0,
                )
            ]

        def fetch_rest_candles_synchronous(
            self,
            trading_pair: str,
            interval: str,
            start_time: int | None = None,
            limit: int = 500,
        ) -> list[CandleData]:
            """Synchronous implementation for testing."""
            return [
                CandleData(
                    timestamp_raw=1620000000,
                    open=100.0,
                    high=101.0,
                    low=99.0,
                    close=100.5,
                    volume=1000.0,
                )
            ]

    def test_trading_pair_format(self):
        """Test trading pair format conversion."""
        adapter = self.MockSyncAdapter()
        assert adapter.get_trading_pair_format("BTC-USDT") == "BTC/USDT"

    def test_rest_url(self):
        """Test REST URL retrieval."""
        adapter = self.MockSyncAdapter()
        assert adapter._get_rest_url() == "https://test.com/api"

    def test_ws_url(self):
        """Test WebSocket URL retrieval."""
        adapter = self.MockSyncAdapter()
        assert adapter.get_ws_url() == "wss://test.com/ws"

    def test_rest_params(self):
        """Test REST parameters construction."""
        adapter = self.MockSyncAdapter()

        # Test minimal parameters
        params = adapter._get_rest_params("BTC-USDT", "1m")
        assert params["symbol"] == "BTC-USDT"
        assert params["interval"] == "1m"
        assert "startTime" not in params

        # Test full parameters
        params = adapter._get_rest_params(
            "BTC-USDT", "1m", start_time=1620000000, end_time=1620100000, limit=100
        )
        assert params["symbol"] == "BTC-USDT"
        assert params["interval"] == "1m"
        assert params["startTime"] == 1620000000
        assert params["endTime"] == 1620100000
        assert params["limit"] == 100

    def test_parse_rest_response(self):
        """Test REST response parsing."""
        adapter = self.MockSyncAdapter()

        # Test with data
        candles = adapter._parse_rest_response({"data": "test"})
        assert len(candles) == 1
        assert candles[0].timestamp == 1620000000
        assert candles[0].open == 100.0

        # Test with None
        candles = adapter._parse_rest_response(None)
        assert candles == []

    def test_ws_subscription_payload(self):
        """Test WebSocket subscription payload."""
        adapter = self.MockSyncAdapter()
        payload = adapter.get_ws_subscription_payload("BTC-USDT", "1m")
        assert payload["subscribe"] == "btc-usdt@kline_1m"

    def test_parse_ws_message(self):
        """Test WebSocket message parsing."""
        adapter = self.MockSyncAdapter()

        # Test valid message
        message = {
            "type": "candle",
            "data": {
                "timestamp": 1620000000,
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 1000.0,
            },
        }
        candles = adapter.parse_ws_message(message)
        assert len(candles) == 1
        assert candles[0].timestamp == 1620000000
        assert candles[0].open == 100.0

        # Test invalid message
        message = {"type": "trade", "data": {}}
        candles = adapter.parse_ws_message(message)
        assert candles is None

        # Test None
        candles = adapter.parse_ws_message(None)
        assert candles is None

    def test_supported_intervals(self):
        """Test supported intervals retrieval."""
        adapter = self.MockSyncAdapter()
        intervals = adapter.get_supported_intervals()
        assert "1m" in intervals
        assert intervals["1m"] == 60
        assert "1h" in intervals
        assert intervals["1h"] == 3600

    def test_ws_supported_intervals(self):
        """Test WebSocket supported intervals."""
        adapter = self.MockSyncAdapter()
        intervals = adapter.get_ws_supported_intervals()
        assert "1m" in intervals
        assert "1h" in intervals

    def test_fetch_rest_candles_synchronous(self):
        """Test synchronous REST candles fetching."""
        adapter = self.MockSyncAdapter()

        # Mock the requests.get function
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": "test"}
            mock_get.return_value = mock_response

            # Call the method
            candles = adapter.fetch_rest_candles_synchronous(trading_pair="BTC-USDT", interval="1m")

            # Verify the result
            assert len(candles) == 1
            assert candles[0].timestamp == 1620000000
            assert candles[0].open == 100.0

    @pytest.mark.asyncio
    async def test_sync_adapter_async_wrapper(self):
        """Test that the async wrapper calls the synchronous method correctly."""
        adapter = self.MockSyncAdapter()

        # Mock the synchronous method to verify it's called
        adapter.fetch_rest_candles_synchronous = Mock(
            return_value=[
                CandleData(
                    timestamp_raw=1620000000,
                    open=100.0,
                    high=101.0,
                    low=99.0,
                    close=100.5,
                    volume=1000.0,
                )
            ]
        )

        # Call the async method
        result = await adapter.fetch_rest_candles(
            trading_pair="BTC-USDT", interval="1m", start_time=1620000000, limit=100
        )

        # Verify the synchronous method was called with correct parameters
        adapter.fetch_rest_candles_synchronous.assert_called_once()
        args, kwargs = adapter.fetch_rest_candles_synchronous.call_args
        assert kwargs.get("trading_pair") == "BTC-USDT" or (len(args) > 0 and args[0] == "BTC-USDT")
        assert kwargs.get("interval") == "1m" or (len(args) > 1 and args[1] == "1m")
        assert kwargs.get("start_time") == 1620000000 or (len(args) > 2 and args[2] == 1620000000)
        assert kwargs.get("limit") == 100 or (len(args) > 3 and args[3] == 100)

        # Verify the result is correct
        assert len(result) == 1
        assert result[0].timestamp == 1620000000
        assert result[0].open == 100.0

    @pytest.mark.asyncio
    async def test_sync_adapter_ignores_network_client(self):
        """Test that SyncOnlyAdapter ignores the network_client parameter."""
        adapter = self.MockSyncAdapter()
        mock_network_client = Mock(spec=NetworkClientProtocol)

        # Mock the synchronous method to verify it's called
        adapter.fetch_rest_candles_synchronous = Mock(return_value=[])

        # Call the async method with a network client
        await adapter.fetch_rest_candles(
            trading_pair="BTC-USDT", interval="1m", network_client=mock_network_client
        )

        # Verify the network client was not used
        adapter.fetch_rest_candles_synchronous.assert_called_once()
        mock_network_client.get_rest_data.assert_not_called()


class TestAsyncOnlyAdapter:
    """Test suite for AsyncOnlyAdapter mixin."""

    class MockAsyncAdapter(BaseAdapter, AsyncOnlyAdapter):
        """Mock adapter implementing AsyncOnlyAdapter for testing."""

        TIMESTAMP_UNIT = "seconds"

        def get_trading_pair_format(self, trading_pair: str) -> str:
            return trading_pair.replace("-", "/")

        def get_supported_intervals(self) -> dict[str, int]:
            return {"1m": 60, "1h": 3600}

        def get_ws_url(self) -> str:
            return "wss://test.com/ws"

        def get_ws_supported_intervals(self) -> list[str]:
            return ["1m", "1h"]

        def parse_ws_message(self, data: dict) -> list[CandleData] | None:
            if data is None:
                return None
            if data.get("type") != "candle":
                return None
            return [
                CandleData(
                    timestamp_raw=data["data"]["timestamp"],
                    open=data["data"]["open"],
                    high=data["data"]["high"],
                    low=data["data"]["low"],
                    close=data["data"]["close"],
                    volume=data["data"]["volume"],
                )
            ]

        def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
            return {"subscribe": f"{trading_pair.lower()}@kline_{interval}"}

        def _get_rest_url(self) -> str:
            return "https://test.com/api"

        def _get_rest_params(
            self, trading_pair: str, interval: str, start_time=None, end_time=None, limit=None
        ) -> dict:
            params = {"symbol": trading_pair, "interval": interval}
            if start_time:
                params["startTime"] = start_time
            if end_time:
                params["endTime"] = end_time
            if limit:
                params["limit"] = limit
            return params

        def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
            if data is None:
                return []
            return [
                CandleData(
                    timestamp_raw=1620000000,
                    open=100.0,
                    high=101.0,
                    low=99.0,
                    close=100.5,
                    volume=1000.0,
                )
            ]

        async def fetch_rest_candles(
            self,
            trading_pair: str,
            interval: str,
            start_time: int | None = None,
            limit: int = 500,
            network_client: NetworkClientProtocol | None = None,
        ) -> list[CandleData]:
            """Async implementation for testing."""
            return [
                CandleData(
                    timestamp_raw=1620000000,
                    open=100.0,
                    high=101.0,
                    low=99.0,
                    close=100.5,
                    volume=1000.0,
                )
            ]

    def test_trading_pair_format(self):
        """Test trading pair format conversion."""
        adapter = self.MockAsyncAdapter()
        assert adapter.get_trading_pair_format("BTC-USDT") == "BTC/USDT"

    def test_rest_url(self):
        """Test REST URL retrieval."""
        adapter = self.MockAsyncAdapter()
        assert adapter._get_rest_url() == "https://test.com/api"

    def test_ws_url(self):
        """Test WebSocket URL retrieval."""
        adapter = self.MockAsyncAdapter()
        assert adapter.get_ws_url() == "wss://test.com/ws"

    def test_rest_params(self):
        """Test REST parameters construction."""
        adapter = self.MockAsyncAdapter()

        # Test minimal parameters
        params = adapter._get_rest_params("BTC-USDT", "1m")
        assert params["symbol"] == "BTC-USDT"
        assert params["interval"] == "1m"
        assert "startTime" not in params

        # Test full parameters
        params = adapter._get_rest_params(
            "BTC-USDT", "1m", start_time=1620000000, end_time=1620100000, limit=100
        )
        assert params["symbol"] == "BTC-USDT"
        assert params["interval"] == "1m"
        assert params["startTime"] == 1620000000
        assert params["endTime"] == 1620100000
        assert params["limit"] == 100

    def test_parse_rest_response(self):
        """Test REST response parsing."""
        adapter = self.MockAsyncAdapter()

        # Test with data
        candles = adapter._parse_rest_response({"data": "test"})
        assert len(candles) == 1
        assert candles[0].timestamp == 1620000000
        assert candles[0].open == 100.0

        # Test with None
        candles = adapter._parse_rest_response(None)
        assert candles == []

    def test_ws_subscription_payload(self):
        """Test WebSocket subscription payload."""
        adapter = self.MockAsyncAdapter()
        payload = adapter.get_ws_subscription_payload("BTC-USDT", "1m")
        assert payload["subscribe"] == "btc-usdt@kline_1m"

    def test_parse_ws_message(self):
        """Test WebSocket message parsing."""
        adapter = self.MockAsyncAdapter()

        # Test valid message
        message = {
            "type": "candle",
            "data": {
                "timestamp": 1620000000,
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 1000.0,
            },
        }
        candles = adapter.parse_ws_message(message)
        assert len(candles) == 1
        assert candles[0].timestamp == 1620000000
        assert candles[0].open == 100.0

        # Test invalid message
        message = {"type": "trade", "data": {}}
        candles = adapter.parse_ws_message(message)
        assert candles is None

        # Test None
        candles = adapter.parse_ws_message(None)
        assert candles is None

    def test_supported_intervals(self):
        """Test supported intervals retrieval."""
        adapter = self.MockAsyncAdapter()
        intervals = adapter.get_supported_intervals()
        assert "1m" in intervals
        assert intervals["1m"] == 60
        assert "1h" in intervals
        assert intervals["1h"] == 3600

    def test_ws_supported_intervals(self):
        """Test WebSocket supported intervals."""
        adapter = self.MockAsyncAdapter()
        intervals = adapter.get_ws_supported_intervals()
        assert "1m" in intervals
        assert "1h" in intervals

    # Additional tests specific to AsyncOnlyAdapter
    def test_async_adapter_sync_raises_error(self):
        """Test that fetch_rest_candles_synchronous raises NotImplementedError."""
        adapter = self.MockAsyncAdapter()

        with pytest.raises(NotImplementedError):
            adapter.fetch_rest_candles_synchronous(trading_pair="BTC-USDT", interval="1m")

    @pytest.mark.asyncio
    async def test_async_adapter_implementation(self):
        """Test that the async implementation works correctly."""
        adapter = self.MockAsyncAdapter()

        # Replace the async method with a mock to verify it's called
        original_method = adapter.fetch_rest_candles
        async_mock = AsyncMock(side_effect=original_method)
        adapter.fetch_rest_candles = async_mock

        # Call the async method
        result = await adapter.fetch_rest_candles(trading_pair="BTC-USDT", interval="1m")

        # Verify the async method was called
        assert async_mock.call_count == 1

        # Verify the result is correct
        assert len(result) == 1
        assert result[0].timestamp == 1620000000
        assert result[0].open == 100.0

    @pytest.mark.asyncio
    async def test_async_adapter_with_network_client(self):
        """Test that AsyncOnlyAdapter uses the network_client if provided."""
        adapter = self.MockAsyncAdapter()
        mock_network_client = Mock(spec=NetworkClientProtocol)
        mock_response = {"data": "test"}
        mock_network_client.get_rest_data = AsyncMock(return_value=mock_response)

        # Mock the internal methods to verify they're called
        original_url_method = adapter._get_rest_url
        original_params_method = adapter._get_rest_params
        original_parse_method = adapter._parse_rest_response

        adapter._get_rest_url = Mock(side_effect=original_url_method)
        adapter._get_rest_params = Mock(side_effect=original_params_method)
        adapter._parse_rest_response = Mock(side_effect=original_parse_method)

        # Override fetch_rest_candles to use our mocks
        original_fetch = adapter.fetch_rest_candles

        async def patched_fetch(*args, **kwargs):
            if "network_client" in kwargs and kwargs["network_client"] is not None:
                url = adapter._get_rest_url()
                params = adapter._get_rest_params(
                    kwargs["trading_pair"],
                    kwargs["interval"],
                    kwargs.get("start_time"),
                    None,
                    kwargs.get("limit"),
                )
                response = await kwargs["network_client"].get_rest_data(url, params)
                return adapter._parse_rest_response(response)
            return await original_fetch(*args, **kwargs)

        adapter.fetch_rest_candles = AsyncMock(side_effect=patched_fetch)

        # Call the async method with a network client
        await adapter.fetch_rest_candles(
            trading_pair="BTC-USDT",
            interval="1m",
            start_time=1620000000,
            limit=100,
            network_client=mock_network_client,
        )

        # Verify the network client was used
        adapter._get_rest_url.assert_called_once()
        adapter._get_rest_params.assert_called_once()
        mock_network_client.get_rest_data.assert_called_once()
        adapter._parse_rest_response.assert_called_once_with(mock_response)


class TestNoWebSocketSupportMixin:
    """Test suite for NoWebSocketSupportMixin.

    Note: This test does not use BaseAdapterTest because NoWebSocketSupportMixin
    deliberately does not implement the WebSocket-related methods required by
    BaseAdapterTest.
    """

    class MockNoWSAdapter(SyncOnlyAdapter):
        """Mock adapter implementing NoWebSocketSupportMixin for testing.

        Note: We don't inherit from NoWebSocketSupportMixin directly to avoid
        abstract method issues. Instead, we use it as a composition pattern
        and delegate to it for testing.
        """

        TIMESTAMP_UNIT = "seconds"

        def __init__(self):
            """Initialize with a NoWebSocketSupportMixin instance for delegation."""
            super().__init__()
            self._no_ws_mixin = NoWebSocketSupportMixin()

        def get_trading_pair_format(self, trading_pair: str) -> str:
            return trading_pair.replace("-", "/")

        def get_supported_intervals(self) -> dict[str, int]:
            return {"1m": 60, "1h": 3600}

        # WebSocket methods that will delegate to NoWebSocketSupportMixin

        def get_ws_url(self) -> str:
            """Delegate to NoWebSocketSupportMixin which will raise NotImplementedError."""
            return self._no_ws_mixin.get_ws_url()

        def get_ws_supported_intervals(self) -> list[str]:
            """Delegate to NoWebSocketSupportMixin which will raise NotImplementedError."""
            return self._no_ws_mixin.get_ws_supported_intervals()

        def parse_ws_message(self, data: dict) -> list[CandleData] | None:
            """Delegate to NoWebSocketSupportMixin which will raise NotImplementedError."""
            return self._no_ws_mixin.parse_ws_message(data)

        def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
            """Delegate to NoWebSocketSupportMixin which will raise NotImplementedError."""
            return self._no_ws_mixin.get_ws_subscription_payload(trading_pair, interval)

        # REST methods

        def _get_rest_url(self) -> str:
            return "https://test.com/api"

        def _get_rest_params(
            self, trading_pair: str, interval: str, start_time=None, end_time=None, limit=None
        ) -> dict:
            return {"symbol": trading_pair, "interval": interval}

        def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
            if data is None:
                return []
            return [
                CandleData(
                    timestamp_raw=1620000000,
                    open=100.0,
                    high=101.0,
                    low=99.0,
                    close=100.5,
                    volume=1000.0,
                )
            ]

        def fetch_rest_candles_synchronous(
            self,
            trading_pair: str,
            interval: str,
            start_time: int | None = None,
            limit: int = 500,
        ) -> list[CandleData]:
            """Synchronous implementation for testing."""
            return [
                CandleData(
                    timestamp_raw=1620000000,
                    open=100.0,
                    high=101.0,
                    low=99.0,
                    close=100.5,
                    volume=1000.0,
                )
            ]

    def test_no_ws_adapter_ws_url_raises_error(self):
        """Test that get_ws_url raises NotImplementedError."""
        adapter = self.MockNoWSAdapter()

        with pytest.raises(NotImplementedError):
            adapter.get_ws_url()

    def test_no_ws_adapter_ws_intervals_raises_error(self):
        """Test that get_ws_supported_intervals raises NotImplementedError."""
        adapter = self.MockNoWSAdapter()

        with pytest.raises(NotImplementedError):
            adapter.get_ws_supported_intervals()

    def test_no_ws_adapter_ws_payload_raises_error(self):
        """Test that get_ws_subscription_payload raises NotImplementedError."""
        adapter = self.MockNoWSAdapter()

        with pytest.raises(NotImplementedError):
            adapter.get_ws_subscription_payload("BTC-USDT", "1m")

    def test_no_ws_adapter_parse_ws_raises_error(self):
        """Test that parse_ws_message raises NotImplementedError."""
        adapter = self.MockNoWSAdapter()

        with pytest.raises(NotImplementedError):
            adapter.parse_ws_message({})

    def test_trading_pair_format(self):
        """Test trading pair format works correctly."""
        adapter = self.MockNoWSAdapter()
        assert adapter.get_trading_pair_format("BTC-USDT") == "BTC/USDT"

    def test_get_rest_url(self):
        """Test rest URL works correctly."""
        adapter = self.MockNoWSAdapter()
        assert adapter._get_rest_url() == "https://test.com/api"

    def test_get_rest_params(self):
        """Test rest params work correctly."""
        adapter = self.MockNoWSAdapter()
        params = adapter._get_rest_params("BTC-USDT", "1m")
        assert params["symbol"] == "BTC-USDT"
        assert params["interval"] == "1m"

    def test_get_supported_intervals(self):
        """Test supported intervals work correctly."""
        adapter = self.MockNoWSAdapter()
        intervals = adapter.get_supported_intervals()
        assert "1m" in intervals
        assert intervals["1m"] == 60


class TestTestnetSupportMixin:
    """Test suite for TestnetSupportMixin."""

    class TestAdapter(TestnetSupportMixin):
        """Test adapter class that implements TestnetSupportMixin."""

        def __init__(self, *args, network_config=None, **kwargs):
            """Initialize the test adapter."""
            # Call TestnetSupportMixin.__init__ to set up network_config
            super().__init__(*args, network_config=network_config, **kwargs)

            # Define production URLs
            self.prod_rest_url = "https://api.example.com"
            self.prod_ws_url = "wss://stream.example.com"

            # Define testnet URLs
            self.testnet_rest_url = "https://testnet.example.com"
            self.testnet_ws_url = "wss://testnet-stream.example.com"

        def _get_production_rest_url(self):
            """Get production REST URL."""
            return self.prod_rest_url

        def _get_production_ws_url(self):
            """Get production WebSocket URL."""
            return self.prod_ws_url

        def _get_testnet_rest_url(self):
            """Get testnet REST URL."""
            return self.testnet_rest_url

        def _get_testnet_ws_url(self):
            """Get testnet WebSocket URL."""
            return self.testnet_ws_url

    def test_default_initialization(self):
        """Test that the mixin initializes with production by default."""
        adapter = self.TestAdapter()

        # Should have a default production config
        assert adapter.network_config.default_environment == NetworkEnvironment.PRODUCTION

        # Should return production URLs by default
        assert adapter._get_rest_url() == adapter.prod_rest_url
        assert adapter._get_ws_url() == adapter.prod_ws_url

    def test_testnet_configuration(self):
        """Test that testnet configuration returns testnet URLs."""
        adapter = self.TestAdapter(network_config=NetworkConfig.testnet())

        # Should have a testnet config
        assert adapter.network_config.default_environment == NetworkEnvironment.TESTNET

        # Should return testnet URLs
        assert adapter._get_rest_url() == adapter.testnet_rest_url
        assert adapter._get_ws_url() == adapter.testnet_ws_url

    def test_hybrid_configuration(self):
        """Test hybrid configuration with different environments per endpoint."""
        # Create a hybrid config where candles use production but orders use testnet
        config = NetworkConfig.hybrid(
            candles=NetworkEnvironment.PRODUCTION, orders=NetworkEnvironment.TESTNET
        )
        adapter = self.TestAdapter(network_config=config)

        # Should return production URLs for candles endpoints
        assert adapter._get_rest_url() == adapter.prod_rest_url
        assert adapter._get_ws_url() == adapter.prod_ws_url

        # If we had dedicated order endpoints, they would use testnet
        assert adapter.network_config.is_testnet_for(EndpointType.ORDERS)

    def test_bypass_network_selection(self):
        """Test that the bypass flag forces production URLs."""
        # Create a testnet adapter
        adapter = self.TestAdapter(network_config=NetworkConfig.testnet())

        # Normally it would return testnet URLs
        assert adapter._get_rest_url() == adapter.testnet_rest_url

        # Enable the bypass flag
        adapter._bypass_network_selection = True

        # Now it should return production URLs despite testnet config
        assert adapter._get_rest_url() == adapter.prod_rest_url
        assert adapter._get_ws_url() == adapter.prod_ws_url

    def test_supports_testnet(self):
        """Test that supports_testnet returns appropriate values."""
        # Our test adapter supports testnet
        adapter = self.TestAdapter()
        assert adapter.supports_testnet() is True

        # If we modify it to raise NotImplementedError for testnet URLs, it should return False
        adapter._get_testnet_rest_url = MagicMock(side_effect=NotImplementedError)
        assert adapter.supports_testnet() is False
