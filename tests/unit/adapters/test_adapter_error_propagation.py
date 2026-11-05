"""
Adapters must propagate REST failures instead of returning an empty list.

Historical pagination treats an empty page as end-of-data, so an adapter that
swallows a request or parse error would silently truncate the result.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import candles_feed.adapters as adapters_package
from candles_feed.core import candles_feed as candles_feed_module
from candles_feed.core.candles_feed import CandlesFeed, HistoricalCandlesError

ADAPTER_CLASSES = [getattr(adapters_package, name) for name in adapters_package.__all__]

# An error body served with HTTP 200, carrying the error markers of the supported exchanges.
ERROR_PAYLOAD = {
    "code": 10001,
    "retCode": 10001,
    "error": ["EGeneral:Invalid arguments"],
    "msg": "invalid request",
    "message": "invalid request",
}


def _client(**kwargs) -> MagicMock:
    client = MagicMock()
    client.get_rest_data = AsyncMock(**kwargs)
    return client


@pytest.mark.parametrize("adapter_class", ADAPTER_CLASSES, ids=lambda cls: cls.__name__)
class TestAdaptersPropagateRestErrors:
    async def test_network_error_raises(self, adapter_class):
        adapter = adapter_class()
        client = _client(side_effect=ConnectionError("network down"))

        with pytest.raises(ConnectionError):
            await adapter.fetch_rest_candles("BTC-USDT", "1m", network_client=client)

    async def test_error_payload_raises(self, adapter_class):
        adapter = adapter_class()
        client = _client(return_value=ERROR_PAYLOAD)

        with pytest.raises(ValueError):
            await adapter.fetch_rest_candles("BTC-USDT", "1m", network_client=client)

    async def test_none_payload_raises(self, adapter_class):
        adapter = adapter_class()
        client = _client(return_value=None)

        with pytest.raises(ValueError):
            await adapter.fetch_rest_candles("BTC-USDT", "1m", network_client=client)


# --- Real adapter driven through CandlesFeed.get_historical_candles -------------------

HOUR = 3600
BASE = 472_222 * HOUR  # hour-aligned epoch
TOTAL = 1500


def _kline(ts: int) -> list:
    return [ts * 1000, "1", "2", "0.5", "1.5", "10", (ts + HOUR) * 1000 - 1, "15", 3, "5", "7"]


class FlakyBinanceClient:
    """Binance-shaped REST backend whose first ``fail_first`` requests raise."""

    def __init__(self, fail_first: int | None) -> None:
        self.fail_first = fail_first  # None means always fail
        self.calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return None

    async def get_rest_data(self, url, params=None, **_):
        self.calls += 1
        if self.fail_first is None or self.calls <= self.fail_first:
            raise ConnectionError("temporary outage")
        lower = int(params["startTime"]) // 1000
        series = [BASE + i * HOUR for i in range(TOTAL)]
        return [_kline(ts) for ts in series if ts >= lower][: int(params["limit"])]


def _binance_feed(client: FlakyBinanceClient) -> CandlesFeed:
    with patch(
        "candles_feed.hb_compat.hummingbot_network_client_adapter."
        "NetworkClientFactory.create_client",
        return_value=client,
    ):
        return CandlesFeed(exchange="binance_spot", trading_pair="BTC-USDT", interval="1h")


@pytest.fixture(autouse=True)
def _no_backoff(monkeypatch):
    monkeypatch.setattr(candles_feed_module, "HISTORICAL_RETRY_BASE_DELAY", 0, raising=False)


class TestHistoricalThroughRealAdapter:
    async def test_transient_failure_is_retried_and_full_data_returned(self):
        client = FlakyBinanceClient(fail_first=1)
        feed = _binance_feed(client)

        df = await feed.get_historical_candles(BASE, BASE + (TOTAL - 1) * HOUR)

        assert list(df["timestamp"]) == [BASE + i * HOUR for i in range(TOTAL)]

    async def test_persistent_failure_raises_instead_of_truncating(self):
        client = FlakyBinanceClient(fail_first=None)
        feed = _binance_feed(client)

        with pytest.raises(HistoricalCandlesError):
            await feed.get_historical_candles(BASE, BASE + (TOTAL - 1) * HOUR)
