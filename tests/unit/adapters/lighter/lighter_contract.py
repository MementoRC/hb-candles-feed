"""Shared offline contract tests for the Lighter spot and perpetual adapters.

Concrete test modules subclass :class:`LighterAdapterContract` and set the class attributes.
"""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from candles_feed.adapters.lighter.constants import (
    CANDLES_PATH_URL,
    INTERVALS,
    MAINNET_BASE_URL,
    ORDER_BOOK_DETAILS_PATH_URL,
)
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.hb_compat.data_types import CandlesConfig
from candles_feed.hb_compat.factory import CandlesFactory

T0 = 1704067200  # 2024-01-01T00:00:00Z
PAIR = "ETH-USDC"

# Shaped like GET /api/v1/orderBookDetails. Spot and perpetual markets live under different
# keys; the perpetual "ETH" market has id 0 (falsy) on purpose.
ORDER_BOOK_DETAILS = {
    "code": 200,
    "order_book_details": [
        {"symbol": "BTC", "market_id": 1},
        {"symbol": "ETH", "market_id": 0},
    ],
    "spot_order_book_details": [
        {"symbol": "ETH/USDC", "market_id": 2048},
        {"symbol": "BTC/USDC", "market_id": 2049},
    ],
}

# Shaped like GET /api/v1/candles: timestamps in ms, unsorted, strings or numbers.
CANDLES_FIXTURE = {
    "code": 200,
    "r": "1m",
    "c": [
        {
            "t": (T0 + 60) * 1000,
            "o": 2300.5,
            "h": 2310.0,
            "l": 2299.0,
            "c": 2305.0,
            "v": 3.5,
            "V": 8067.5,
        },
        {
            "t": T0 * 1000,
            "o": "2290.0",
            "h": "2301.0",
            "l": "2288.0",
            "c": "2300.5",
            "v": "10.25",
            "V": "23500.0",
        },
    ],
}


class LighterAdapterContract:
    """Behaviour every Lighter adapter must satisfy."""

    ADAPTER_CLS: type
    SYMBOL: str  # expected exchange symbol for "ETH-USDC"
    MARKET_ID: int  # id of "ETH-USDC" in ORDER_BOOK_DETAILS
    REGISTRY_NAME: str
    CONNECTOR_NAME: str  # upstream hummingbot connector name

    @pytest.fixture
    def adapter(self):
        return self.ADAPTER_CLS()

    @pytest.fixture
    def resolved(self, adapter):
        adapter._market_ids[PAIR] = self.MARKET_ID
        return adapter

    def test_symbol_conversion(self):
        assert self.ADAPTER_CLS.get_trading_pair_format(PAIR) == self.SYMBOL

    def test_intervals(self, adapter):
        intervals = adapter.get_supported_intervals()
        assert intervals == INTERVALS
        assert list(intervals) == ["1m", "5m", "15m", "30m", "1h", "4h", "12h", "1d", "1w"]
        assert intervals["1w"] == 604800

    def test_no_websocket(self, adapter):
        for call in (
            adapter.get_ws_url,
            adapter.get_ws_supported_intervals,
            lambda: adapter.get_ws_subscription_payload(PAIR, "1m"),
            lambda: adapter.parse_ws_message({}),
        ):
            with pytest.raises(NotImplementedError):
                call()

    def test_rest_url(self, adapter):
        assert adapter._get_rest_url() == f"{MAINNET_BASE_URL}{CANDLES_PATH_URL}"

    def test_rest_params(self, resolved):
        params = resolved._get_rest_params(PAIR, "5m", start_time=T0, limit=12)
        assert params == {
            "market_id": self.MARKET_ID,
            "resolution": "5m",
            "start_timestamp": T0 * 1000,
            "end_timestamp": (T0 + 12 * 300) * 1000,
            "count_back": 12,
        }

    def test_zero_limit_requests_one_candle(self, resolved):
        params = resolved._get_rest_params(PAIR, "1h", start_time=T0, limit=0)
        assert params["end_timestamp"] - params["start_timestamp"] == 3600 * 1000
        assert params["count_back"] == 1

    @pytest.mark.parametrize("limit", [None, 99999])
    def test_limit_none_or_oversized_capped_at_1000(self, resolved, limit):
        params = resolved._get_rest_params(PAIR, "1m", start_time=T0, limit=limit)
        assert params["count_back"] == 1000
        assert params["end_timestamp"] - params["start_timestamp"] == 1000 * 60 * 1000

    def test_window_clamped_to_end_of_current_bucket(self, resolved):
        now = int(time.time())
        start = now - now % 60
        params = resolved._get_rest_params(PAIR, "1m", start_time=start, limit=1000)
        assert params["end_timestamp"] == (start + 60) * 1000
        assert params["count_back"] == 1

    def test_default_window_covers_latest_candles(self, resolved):
        now = time.time()
        params = resolved._get_rest_params(PAIR, "1m", limit=10)
        assert abs(params["end_timestamp"] / 1000 - (now - now % 60 + 60)) < 5
        assert params["count_back"] == 10

    def test_start_not_before_end_raises_clear_error(self, resolved):
        future = int(time.time()) + 10 * 86400
        with pytest.raises(
            ValueError, match="end_timestamp .* must be greater than start_timestamp"
        ):
            resolved._get_rest_params(PAIR, "1m", start_time=future, limit=5)

    def test_unresolved_market_raises(self, adapter):
        with pytest.raises(ValueError, match="market id"):
            adapter._get_rest_params(PAIR, "1m", start_time=T0)

    def test_parse_ten_columns_in_seconds_sorted(self, adapter):
        candles = adapter._parse_rest_response(CANDLES_FIXTURE)
        assert all(isinstance(c, CandleData) for c in candles)
        assert candles[0].to_array() == [
            float(T0),
            2290.0,
            2301.0,
            2288.0,
            2300.5,
            10.25,
            23500.0,
            0,
            0.0,
            0.0,
        ]
        assert candles[1].timestamp == T0 + 60
        assert isinstance(candles[0].timestamp, int)

    def test_rows_missing_prices_are_skipped_not_zeroed(self, adapter):
        rows = {"c": [{"t": T0 * 1000, "v": 1}, CANDLES_FIXTURE["c"][1]]}
        assert len(adapter._parse_rest_response(rows)) == 1

    @pytest.mark.parametrize("bad", [None, {}, [], "x", {"c": None}])
    def test_parse_empty_inputs(self, adapter, bad):
        assert adapter._parse_rest_response(bad) == []

    @staticmethod
    def _client(details=ORDER_BOOK_DETAILS):
        async def get_rest_data(url, params=None, data=None, headers=None, method="GET"):
            if url.endswith(ORDER_BOOK_DETAILS_PATH_URL):
                return details
            return CANDLES_FIXTURE

        client = MagicMock()
        client.get_rest_data = AsyncMock(side_effect=get_rest_data)
        return client

    async def test_fetch_resolves_market_id_once_then_fetches(self, adapter):
        client = self._client()
        for _ in range(2):
            candles = await adapter.fetch_rest_candles(
                PAIR, "1m", start_time=T0, limit=10, network_client=client
            )
            assert [c.timestamp for c in candles] == [T0, T0 + 60]
        urls = [c.kwargs["url"] for c in client.get_rest_data.await_args_list]
        assert urls.count(f"{MAINNET_BASE_URL}{ORDER_BOOK_DETAILS_PATH_URL}") == 1
        candle_call = client.get_rest_data.await_args_list[1]
        assert candle_call.kwargs["url"] == f"{MAINNET_BASE_URL}{CANDLES_PATH_URL}"
        assert candle_call.kwargs["params"]["market_id"] == self.MARKET_ID

    async def test_fetch_unknown_market_raises_clear_error(self, adapter):
        client = self._client(details={"order_book_details": [], "spot_order_book_details": []})
        with pytest.raises(ValueError, match="market not found"):
            await adapter.fetch_rest_candles(
                PAIR, "1m", start_time=T0, limit=10, network_client=client
            )

    async def test_fetch_with_empty_window_returns_empty_without_requests(self, adapter):
        client = self._client()
        future = int(time.time()) + 10 * 86400
        assert (
            await adapter.fetch_rest_candles(
                PAIR, "1m", start_time=future, limit=5, network_client=client
            )
            == []
        )
        client.get_rest_data.assert_not_awaited()

    async def test_fetch_requires_network_client(self, adapter):
        with pytest.raises(ValueError, match="network_client"):
            await adapter.fetch_rest_candles(PAIR, "1m")

    def test_registry_lookup(self):
        assert ExchangeRegistry.get_adapter_class(self.REGISTRY_NAME) is self.ADAPTER_CLS

    def test_factory_lookup(self):
        assert CandlesFactory._CONNECTOR_MAP[self.CONNECTOR_NAME] == self.REGISTRY_NAME
        candle = CandlesFactory.get_candle(
            CandlesConfig(connector=self.CONNECTOR_NAME, trading_pair=PAIR)
        )
        assert candle.name == self.REGISTRY_NAME
