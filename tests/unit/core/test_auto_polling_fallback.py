"""start("auto") must fall back to REST polling when websockets are unusable (#95)."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from candles_feed.core.candle_data import CandleData
from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.core.exchange_registry import ExchangeRegistry


def _candles(interval_s: int = 60, count: int = 3) -> list[CandleData]:
    end = int(time.time()) // interval_s * interval_s
    return [
        CandleData(
            timestamp_raw=end - (count - i) * interval_s,
            open=1.0,
            high=2.0,
            low=0.5,
            close=1.5,
            volume=10.0,
            quote_asset_volume=15.0,
            n_trades=1,
            taker_buy_base_volume=5.0,
            taker_buy_quote_volume=7.0,
        )
        for i in range(count)
    ]


class _FakeAdapter:
    """Minimal adapter; ws intervals either unimplemented or a fixed list."""

    def __init__(self, ws_intervals: list[str] | None):
        self._ws_intervals = ws_intervals
        self.fetch_rest_candles = AsyncMock(return_value=_candles())

    def get_trading_pair_format(self, trading_pair: str) -> str:
        return trading_pair

    def get_supported_intervals(self) -> dict[str, int]:
        return {"1m": 60, "5m": 300}

    def get_ws_supported_intervals(self) -> list[str]:
        if self._ws_intervals is None:
            raise NotImplementedError("REST only")
        return self._ws_intervals


def _make_feed(adapter: _FakeAdapter, interval: str = "1m") -> CandlesFeed:
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    with (
        patch.object(ExchangeRegistry, "get_adapter_instance", return_value=adapter),
        patch(
            "candles_feed.hb_compat.hummingbot_network_client_adapter.NetworkClientFactory.create_client",
            return_value=client,
        ),
    ):
        return CandlesFeed(exchange="fake", trading_pair="BTC-USDT", interval=interval)


async def _wait_for_candles(feed: CandlesFeed) -> None:
    for _ in range(200):
        if feed.get_candles():
            return
        await asyncio.sleep(0.01)


@pytest.mark.asyncio
async def test_auto_falls_back_to_polling_for_rest_only_adapter():
    adapter = _FakeAdapter(ws_intervals=None)
    feed = _make_feed(adapter)
    try:
        await feed.start("auto")
        await _wait_for_candles(feed)

        assert feed._using_ws is False
        assert feed._ws_strategy is None
        assert len(feed.get_candles_df()) == 3
        adapter.fetch_rest_candles.assert_awaited()
    finally:
        await feed.stop()


@pytest.mark.asyncio
async def test_auto_falls_back_to_polling_when_interval_not_ws_supported():
    adapter = _FakeAdapter(ws_intervals=["5m"])
    feed = _make_feed(adapter, interval="1m")
    try:
        await feed.start("auto")
        await _wait_for_candles(feed)

        assert feed._using_ws is False
        assert feed._ws_strategy is None
        assert len(feed.get_candles_df()) == 3
    finally:
        await feed.stop()
