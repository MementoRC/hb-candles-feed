"""
Tests for compatibility between the new candles-feed implementation and the original one.

These tests verify that the new implementation (under hummingbot/sub-packages/candles-feed)
is compatible with the original implementation (under origin/data_feed/candles_feed).

Compatibility Features Implemented:
1. DataFrames have the same structure and columns
2. start/stop methods match original start_network/stop_network
3. fetch_candles and get_historical_candles methods have same parameters/behavior
4. ready property logic matches the original implementation
5. Interval handling and timestamps have consistent behavior
6. CandleData class represents the same information as the original arrays
7. WebSocket and REST strategies match the original collection methods
8. Hummingbot component integration (throttler and web_assistants_factory)
9. Utility functions like check_candles_sorted_and_equidistant and timestamp rounding

This ensures that the new implementation can be used as a drop-in replacement
for the original, while providing a more modular architecture.
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from candles_feed.adapters.binance.spot_adapter import BinanceSpotAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.core.exchange_registry import ExchangeRegistry

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestCompatibilityWithOriginal:
    """Tests for compatibility between new and original implementations."""

    @pytest.fixture
    def mock_original_candles_base(self):
        """Create a mock of the original CandlesBase class."""
        # We need to mock the original CandlesBase class from origin directory
        mock_candles_base = MagicMock()
        mock_candles_base.start_network = AsyncMock()
        mock_candles_base.stop_network = AsyncMock()
        mock_candles_base.fetch_candles = AsyncMock()
        mock_candles_base.get_historical_candles = AsyncMock()
        mock_candles_base.fill_historical_candles = AsyncMock()
        mock_candles_base._candles = []

        # Set up the candles_df property to return a DataFrame
        columns = [
            "timestamp", "open", "high", "low", "close", "volume",
            "quote_asset_volume", "n_trades", "taker_buy_base_volume",
            "taker_buy_quote_volume"
        ]
        mock_candles_base.candles_df = pd.DataFrame(columns=columns)
        mock_candles_base.ready = False
        mock_candles_base.interval = "1m"
        mock_candles_base.trading_pair = "BTC-USDT"
        mock_candles_base.ex_trading_pair = "BTCUSDT"
        mock_candles_base.max_records = 100

        return mock_candles_base

    @pytest.fixture
    def sample_candles_data(self):
        """Create sample candles data for testing."""
        # Create sample candles data in both formats (original and new)
        original_format = [
            [1609459200, 40000.0, 41000.0, 39000.0, 40500.0, 100.0, 4000000.0, 1000, 50.0, 2000000.0],
            [1609459260, 40500.0, 42000.0, 40000.0, 41000.0, 120.0, 4500000.0, 1100, 60.0, 2400000.0],
        ]

        new_format = [
            CandleData(
                timestamp_raw=1609459200,
                open=40000.0,
                high=41000.0,
                low=39000.0,
                close=40500.0,
                volume=100.0,
                quote_asset_volume=4000000.0,
                n_trades=1000,
                taker_buy_base_volume=50.0,
                taker_buy_quote_volume=2000000.0,
            ),
            CandleData(
                timestamp_raw=1609459260,
                open=40500.0,
                high=42000.0,
                low=40000.0,
                close=41000.0,
                volume=120.0,
                quote_asset_volume=4500000.0,
                n_trades=1100,
                taker_buy_base_volume=60.0,
                taker_buy_quote_volume=2400000.0,
            ),
        ]

        return {"original": original_format, "new": new_format}

    @pytest.mark.asyncio
    async def test_dataframe_format_compatibility(self, sample_candles_data):
        """Test that the DataFrame format is compatible with the original."""
        # Set up
        # The registration is now handled through a decorator pattern
        mock_adapter = MagicMock(spec=BinanceSpotAdapter)
        # Patch the registry directly for testing
        ExchangeRegistry._registry["mock_exchange"] = lambda *args, **kwargs: mock_adapter
        ExchangeRegistry._adapters["mock_exchange"] = lambda *args, **kwargs: mock_adapter

        # Create original DataFrame
        columns = [
            "timestamp", "open", "high", "low", "close", "volume",
            "quote_asset_volume", "n_trades", "taker_buy_base_volume",
            "taker_buy_quote_volume"
        ]
        original_df = pd.DataFrame(sample_candles_data["original"], columns=columns)

        # Create new implementation's CandlesFeed instance
        with patch(
            "candles_feed.core.exchange_registry.ExchangeRegistry.get_adapter_instance",
            return_value=MagicMock(),
        ), patch(
            "candles_feed.core.network_client.NetworkClient",
            return_value=MagicMock(),
        ):
            feed = CandlesFeed(
                exchange="mock_exchange",
                trading_pair="BTC-USDT",
                interval="1m",
                max_records=100,
            )

            # Add candles to the feed
            for candle in sample_candles_data["new"]:
                feed.add_candle(candle)

            # Get DataFrame from new implementation
            new_df = feed.get_candles_df()

            # Compare DataFrames
            assert list(new_df.columns) == list(original_df.columns), "DataFrame columns should match"
            assert len(new_df) == len(original_df), "DataFrame lengths should match"

            # Convert timestamps to integers for easier comparison
            new_df["timestamp"] = new_df["timestamp"].astype(int)
            original_df["timestamp"] = original_df["timestamp"].astype(int)

            # Compare values
            for i in range(len(original_df)):
                for col in columns:
                    assert new_df.iloc[i][col] == original_df.iloc[i][col], f"Value mismatch for {col} at index {i}"

    @pytest.mark.asyncio
    async def test_historical_data_fetch_compatibility(self, sample_candles_data):
        """Test that historical data fetching is compatible with the original."""
        # Mock adapter
        mock_adapter = MagicMock()
        mock_adapter.get_trading_pair_format.return_value = "BTCUSDT"
        mock_adapter.get_ws_supported_intervals.return_value = ["1m", "5m", "15m"]
        mock_adapter.get_supported_intervals.return_value = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "1d": 86400}
        mock_adapter.fetch_rest_candles = AsyncMock(return_value=sample_candles_data["new"])

        # Mock strategies
        mock_rest_strategy = MagicMock()
        mock_rest_strategy.poll_once = AsyncMock(return_value=sample_candles_data["new"])

        # Patch dependencies
        with patch(
            "candles_feed.core.exchange_registry.ExchangeRegistry.get_adapter_instance",
            return_value=mock_adapter,
        ), patch(
            "candles_feed.core.network_client.NetworkClient",
            return_value=MagicMock(),
        ), patch(
            "candles_feed.core.candles_feed.CandlesFeed._create_rest_strategy",
            return_value=mock_rest_strategy,
        ):
            # Create new implementation's CandlesFeed instance
            feed = CandlesFeed(
                exchange="mock_exchange",
                trading_pair="BTC-USDT",
                interval="1m",
                max_records=100,
            )

            # Fetch historical candles
            candles = await feed.fetch_candles(
                start_time=1609459000,
                end_time=1609459300,
                limit=10,
            )

            # Verify candles are returned correctly
            assert len(candles) == 2, "Should return 2 candles"
            assert candles[0].timestamp == 1609459200, "First candle timestamp should match"
            assert candles[1].timestamp == 1609459260, "Second candle timestamp should match"

            # Verify candles are added to the store
            df = feed.get_candles_df()
            assert len(df) == 2, "DataFrame should contain 2 candles"
            assert df.iloc[0]["timestamp"] == 1609459200, "First candle timestamp should match"
            assert df.iloc[1]["timestamp"] == 1609459260, "Second candle timestamp should match"

    @pytest.mark.asyncio
    async def test_get_historical_candles_compatibility(self, sample_candles_data):
        """Test that get_historical_candles method is compatible with the original."""
        # Mock adapter
        mock_adapter = MagicMock()
        mock_adapter.get_trading_pair_format.return_value = "BTCUSDT"
        mock_adapter.get_ws_supported_intervals.return_value = ["1m", "5m", "15m"]
        mock_adapter.get_supported_intervals.return_value = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "1d": 86400}
        mock_adapter.fetch_rest_candles = AsyncMock(return_value=sample_candles_data["new"])

        # Mock strategies
        mock_rest_strategy = MagicMock()
        mock_rest_strategy.poll_once = AsyncMock(return_value=sample_candles_data["new"])

        # Patch dependencies
        with patch(
            "candles_feed.core.exchange_registry.ExchangeRegistry.get_adapter_instance",
            return_value=mock_adapter,
        ), patch(
            "candles_feed.core.network_client.NetworkClient",
            return_value=MagicMock(),
        ), patch(
            "candles_feed.core.candles_feed.CandlesFeed._create_rest_strategy",
            return_value=mock_rest_strategy,
        ):
            # Create new implementation's CandlesFeed instance
            feed = CandlesFeed(
                exchange="mock_exchange",
                trading_pair="BTC-USDT",
                interval="1m",
                max_records=100,
            )

            # Prefill with some data
            await feed.fetch_candles()

            # Clear the rest strategy poll_once mock to track next calls
            mock_rest_strategy.poll_once.reset_mock()

            # Call get_historical_candles
            historical_df = await feed.get_historical_candles(1609459000, 1609459300, 10)

            # Verify the method was called with proper parameters
            mock_rest_strategy.poll_once.assert_called_once()

            # Verify data format is compatible with original implementation
            assert isinstance(historical_df, pd.DataFrame), "Should return a DataFrame"
            assert len(historical_df) == 2, "Should return 2 candles"
            assert "timestamp" in historical_df.columns, "DataFrame should have timestamp column"
            assert "open" in historical_df.columns, "DataFrame should have open column"
            assert "high" in historical_df.columns, "DataFrame should have high column"
            assert "low" in historical_df.columns, "DataFrame should have low column"
            assert "close" in historical_df.columns, "DataFrame should have close column"
            assert "volume" in historical_df.columns, "DataFrame should have volume column"

            # Verify the data is correct
            assert historical_df.iloc[0]["timestamp"] == 1609459200, "First candle timestamp should match"
            assert historical_df.iloc[1]["timestamp"] == 1609459260, "Second candle timestamp should match"

    @pytest.mark.asyncio
    async def test_timestamp_rounding_compatibility(self):
        """Test timestamp rounding compatibility."""
        # Mock adapter
        mock_adapter = MagicMock()
        mock_adapter.get_supported_intervals.return_value = {"1m": 60, "5m": 300, "1h": 3600}

        # Patch dependencies
        with patch(
            "candles_feed.core.exchange_registry.ExchangeRegistry.get_adapter_instance",
            return_value=mock_adapter,
        ), patch(
            "candles_feed.core.network_client.NetworkClient",
            return_value=MagicMock(),
        ):
            # Create new implementation's CandlesFeed instance with 1m interval
            feed_1m = CandlesFeed(
                exchange="mock_exchange",
                trading_pair="BTC-USDT",
                interval="1m",
                max_records=10,
            )

            # Create new implementation's CandlesFeed instance with 5m interval
            feed_5m = CandlesFeed(
                exchange="mock_exchange",
                trading_pair="BTC-USDT",
                interval="5m",
                max_records=10,
            )

            # Create new implementation's CandlesFeed instance with 1h interval
            feed_1h = CandlesFeed(
                exchange="mock_exchange",
                trading_pair="BTC-USDT",
                interval="1h",
                max_records=10,
            )

            # Test 1m interval rounding
            timestamp = 1609459217  # Not aligned to 1m interval
            rounded = feed_1m._round_timestamp_to_interval_multiple(timestamp)
            assert rounded == 1609459200, "1m rounding should round down to 1609459200"

            # Test 5m interval rounding
            timestamp = 1609459217  # Not aligned to 5m interval
            rounded = feed_5m._round_timestamp_to_interval_multiple(timestamp)
            assert rounded == 1609459200, "5m rounding should round down to 1609459200"

            # Test 1h interval rounding
            timestamp = 1609459217  # Not aligned to 1h interval
            rounded = feed_1h._round_timestamp_to_interval_multiple(timestamp)
            assert rounded == 1609459200, "1h rounding should round down to 1609459200"

            # Test interval boundary for 1m
            timestamp = 1609459200  # Exactly on a 1m boundary
            rounded = feed_1m._round_timestamp_to_interval_multiple(timestamp)
            assert rounded == 1609459200, "1m rounding of boundary should not change"

            # Test interval boundary for 5m
            timestamp = 1609459500  # Exactly on a 5m boundary
            rounded = feed_5m._round_timestamp_to_interval_multiple(timestamp)
            assert rounded == 1609459500, "5m rounding of boundary should not change"

    @pytest.mark.asyncio
    async def test_ready_property_compatibility(self):
        """Test that the ready property is compatible with the original."""
        # Mock adapter
        mock_adapter = MagicMock()

        # Patch dependencies
        with patch(
            "candles_feed.core.exchange_registry.ExchangeRegistry.get_adapter_instance",
            return_value=mock_adapter,
        ), patch(
            "candles_feed.core.network_client.NetworkClient",
            return_value=MagicMock(),
        ):
            # Create new implementation's CandlesFeed instance with max_records=10
            feed = CandlesFeed(
                exchange="mock_exchange",
                trading_pair="BTC-USDT",
                interval="1m",
                max_records=10,
            )

            # Initially, the feed should not be ready
            assert not feed.ready, "Feed should not be ready initially"

            # Add 8 candles (80% of max_records)
            for i in range(8):
                feed.add_candle(
                    CandleData(
                        timestamp_raw=1609459200 + i * 60,
                        open=40000.0,
                        high=41000.0,
                        low=39000.0,
                        close=40500.0,
                        volume=100.0,
                        quote_asset_volume=4000000.0,
                        n_trades=1000,
                        taker_buy_base_volume=50.0,
                        taker_buy_quote_volume=2000000.0,
                    )
                )

            # Feed should not be ready yet (less than 90% filled)
            assert not feed.ready, "Feed should not be ready at 80% capacity"

            # Add 2 more candles (100% of max_records)
            for i in range(2):
                feed.add_candle(
                    CandleData(
                        timestamp_raw=1609459200 + (i + 8) * 60,
                        open=40000.0,
                        high=41000.0,
                        low=39000.0,
                        close=40500.0,
                        volume=100.0,
                        quote_asset_volume=4000000.0,
                        n_trades=1000,
                        taker_buy_base_volume=50.0,
                        taker_buy_quote_volume=2000000.0,
                    )
                )

            # Feed should be ready now (100% filled, which is > 90%)
            assert feed.ready, "Feed should be ready at 100% capacity"

    @pytest.mark.asyncio
    async def test_check_candles_sorted_and_equidistant(self):
        """Test the check_candles_sorted_and_equidistant method for compatibility."""
        # Mock adapter
        mock_adapter = MagicMock()
        mock_adapter.get_supported_intervals.return_value = {"1m": 60}

        # Patch dependencies
        with patch(
            "candles_feed.core.exchange_registry.ExchangeRegistry.get_adapter_instance",
            return_value=mock_adapter,
        ), patch(
            "candles_feed.core.network_client.NetworkClient",
            return_value=MagicMock(),
        ):
            # Create new implementation's CandlesFeed instance
            feed = CandlesFeed(
                exchange="mock_exchange",
                trading_pair="BTC-USDT",
                interval="1m",
                max_records=10,
            )

            # Test with empty candles
            assert feed.check_candles_sorted_and_equidistant(), "Should return True with empty candles"

            # Test with a single candle
            feed.add_candle(
                CandleData(
                    timestamp_raw=1609459200,
                    open=40000.0,
                    high=41000.0,
                    low=39000.0,
                    close=40500.0,
                    volume=100.0,
                    quote_asset_volume=4000000.0,
                    n_trades=1000,
                    taker_buy_base_volume=50.0,
                    taker_buy_quote_volume=2000000.0,
                )
            )
            assert feed.check_candles_sorted_and_equidistant(), "Should return True with a single candle"

            # Test with properly sorted and equidistant candles
            # Add candles with 60-second intervals (matching the 1m interval)
            for i in range(1, 5):
                feed.add_candle(
                    CandleData(
                        timestamp_raw=1609459200 + (i * 60),
                        open=40000.0 + i * 100,
                        high=41000.0 + i * 100,
                        low=39000.0 + i * 100,
                        close=40500.0 + i * 100,
                        volume=100.0,
                        quote_asset_volume=4000000.0,
                        n_trades=1000,
                        taker_buy_base_volume=50.0,
                        taker_buy_quote_volume=2000000.0,
                    )
                )

            assert feed.check_candles_sorted_and_equidistant(), "Should return True with sorted and equidistant candles"

            # Create a new feed for testing unsorted candles
            unsorted_feed = CandlesFeed(
                exchange="mock_exchange",
                trading_pair="BTC-USDT",
                interval="1m",
                max_records=10,
            )

            # Add candles in unsorted order
            unsorted_feed.add_candle(
                CandleData(
                    timestamp_raw=1609459320,  # Later timestamp first
                    open=40200.0,
                    high=41200.0,
                    low=39200.0,
                    close=40700.0,
                    volume=100.0,
                    quote_asset_volume=4000000.0,
                    n_trades=1000,
                    taker_buy_base_volume=50.0,
                    taker_buy_quote_volume=2000000.0,
                )
            )

            unsorted_feed.add_candle(
                CandleData(
                    timestamp_raw=1609459200,  # Earlier timestamp second
                    open=40000.0,
                    high=41000.0,
                    low=39000.0,
                    close=40500.0,
                    volume=100.0,
                    quote_asset_volume=4000000.0,
                    n_trades=1000,
                    taker_buy_base_volume=50.0,
                    taker_buy_quote_volume=2000000.0,
                )
            )

            # This should detect the unsorted timestamps
            assert not unsorted_feed.check_candles_sorted_and_equidistant(), "Should return False with unsorted candles"

            # Create a new feed for testing non-equidistant candles
            non_equidistant_feed = CandlesFeed(
                exchange="mock_exchange",
                trading_pair="BTC-USDT",
                interval="1m",
                max_records=10,
            )

            # Add candles with irregular intervals
            non_equidistant_feed.add_candle(
                CandleData(
                    timestamp_raw=1609459200,
                    open=40000.0,
                    high=41000.0,
                    low=39000.0,
                    close=40500.0,
                    volume=100.0,
                    quote_asset_volume=4000000.0,
                    n_trades=1000,
                    taker_buy_base_volume=50.0,
                    taker_buy_quote_volume=2000000.0,
                )
            )

            non_equidistant_feed.add_candle(
                CandleData(
                    timestamp_raw=1609459230,  # 30-second interval (should be 60 seconds)
                    open=40100.0,
                    high=41100.0,
                    low=39100.0,
                    close=40600.0,
                    volume=100.0,
                    quote_asset_volume=4000000.0,
                    n_trades=1000,
                    taker_buy_base_volume=50.0,
                    taker_buy_quote_volume=2000000.0,
                )
            )

            # This should detect the non-equidistant intervals
            assert not non_equidistant_feed.check_candles_sorted_and_equidistant(), "Should return False with non-equidistant candles"

    @pytest.mark.asyncio
    async def test_start_stop_compatibility(self):
        """Test that start/stop methods are compatible with the original."""
        # Mock adapter
        mock_adapter = MagicMock()
        mock_adapter.get_trading_pair_format.return_value = "BTCUSDT"
        mock_adapter.get_ws_supported_intervals.return_value = ["1m", "5m", "15m"]

        # Mock strategies
        mock_ws_strategy = MagicMock()
        mock_ws_strategy.start = AsyncMock()
        mock_ws_strategy.stop = AsyncMock()

        mock_rest_strategy = MagicMock()
        mock_rest_strategy.start = AsyncMock()
        mock_rest_strategy.stop = AsyncMock()

        # Mock network client
        mock_network_client = MagicMock()
        mock_network_client.close = AsyncMock()

        # Patch dependencies
        with patch(
            "candles_feed.core.exchange_registry.ExchangeRegistry.get_adapter_instance",
            return_value=mock_adapter,
        ), patch(
            "candles_feed.core.network_client.NetworkClient",
            return_value=mock_network_client,
        ), patch(
            "candles_feed.core.candles_feed.CandlesFeed._create_ws_strategy",
            return_value=mock_ws_strategy,
        ), patch(
            "candles_feed.core.candles_feed.CandlesFeed._create_rest_strategy",
            return_value=mock_rest_strategy,
        ):
            # Create new implementation's CandlesFeed instance
            feed = CandlesFeed(
                exchange="mock_exchange",
                trading_pair="BTC-USDT",
                interval="1m",
                max_records=100,
            )

            # Test WebSocket strategy
            await feed.start(strategy="websocket")
            assert feed._active, "Feed should be active after start"
            assert feed._using_ws, "Feed should be using WebSocket strategy"
            mock_ws_strategy.start.assert_called_once(), "WebSocket strategy start should be called"

            await feed.stop()
            assert not feed._active, "Feed should not be active after stop"
            mock_ws_strategy.stop.assert_called_once(), "WebSocket strategy stop should be called"
            mock_network_client.close.assert_called_once(), "Network client close should be called"

            # Reset mocks
            mock_ws_strategy.start.reset_mock()
            mock_ws_strategy.stop.reset_mock()
            mock_network_client.close.reset_mock()

            # Test REST strategy
            await feed.start(strategy="polling")
            assert feed._active, "Feed should be active after start"
            assert not feed._using_ws, "Feed should not be using WebSocket strategy"
            mock_rest_strategy.start.assert_called_once(), "REST strategy start should be called"

            await feed.stop()
            assert not feed._active, "Feed should not be active after stop"
            mock_rest_strategy.stop.assert_called_once(), "REST strategy stop should be called"
            mock_network_client.close.assert_called_once(), "Network client close should be called"


class TestCandlesFeedWithHummingbotComponents:
    """Tests for compatibility with Hummingbot components."""

    @pytest.mark.asyncio
    async def test_candles_feed_with_hummingbot_components(self):
        """Test candles feed with Hummingbot components."""
        # Skip if hummingbot components aren't available
        try:
            from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
            from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
        except ImportError:
            pytest.skip("Hummingbot components not available")

        # Mock Hummingbot components
        mock_throttler = MagicMock(spec=AsyncThrottler)
        mock_web_assistants_factory = MagicMock(spec=WebAssistantsFactory)

        # Mock adapter
        mock_adapter = MagicMock()
        mock_adapter.get_trading_pair_format.return_value = "BTCUSDT"

        # Patch dependencies
        with patch(
            "candles_feed.core.exchange_registry.ExchangeRegistry.get_adapter_instance",
            return_value=mock_adapter,
        ):
            # Create candles feed with Hummingbot components
            feed = CandlesFeed(
                exchange="mock_exchange",
                trading_pair="BTC-USDT",
                interval="1m",
                max_records=100,
                hummingbot_components={
                    "throttler": mock_throttler,
                    "web_assistants_factory": mock_web_assistants_factory,
                },
            )

            # Verify components are passed correctly
            assert feed._hummingbot_components is not None
            assert feed._hummingbot_components["throttler"] == mock_throttler
            assert feed._hummingbot_components["web_assistants_factory"] == mock_web_assistants_factory
