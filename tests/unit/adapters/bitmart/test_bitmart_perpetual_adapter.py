"""Tests for the BitmartPerpetualAdapter (offline, fixture based)."""

import time

import pytest

from candles_feed.adapters.bitmart.constants import (
    CANDLES_ENDPOINT,
    INTERVAL_TO_EXCHANGE_REST,
    INTERVAL_TO_EXCHANGE_WS,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WS_INTERVALS,
    WSS_URL,
)
from candles_feed.adapters.bitmart.perpetual_adapter import BitmartPerpetualAdapter
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.hb_compat.data_types import CandlesConfig
from candles_feed.hb_compat.factory import CandlesFactory
from tests.unit.adapters.base_adapter_test import BaseAdapterTest

T0 = 1704067200  # 2024-01-01T00:00:00Z
NOW = T0 + 86400


def kline(offset: int = 0) -> dict:
    """One row shaped like GET /contract/public/kline."""
    return {
        "timestamp": T0 + offset,
        "open_price": "2290.0",
        "high_price": "2301.0",
        "low_price": "2288.0",
        "close_price": "2300.5",
        "volume": "10",
    }


class TestBitmartPerpetualAdapter(BaseAdapterTest):
    """Bitmart perpetual adapter tests on top of the shared adapter contract."""

    @pytest.fixture(autouse=True)
    def frozen_time(self, monkeypatch):
        """The REST window defaults to 'now'; freeze it so params are reproducible."""
        monkeypatch.setattr(time, "time", lambda: NOW)

    def create_adapter(self):
        return BitmartPerpetualAdapter()

    def get_expected_trading_pair_format(self, trading_pair):
        return trading_pair.replace("-", "")

    def get_expected_rest_url(self):
        return f"{REST_URL}{CANDLES_ENDPOINT}"

    def get_expected_ws_url(self):
        return WSS_URL

    def get_expected_rest_params_minimal(self, trading_pair, interval):
        seconds = INTERVALS[interval]
        return {
            "symbol": "BTCUSDT",
            "step": INTERVAL_TO_EXCHANGE_REST[interval],
            "start_time": NOW - MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST * seconds,
            "end_time": NOW,
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, limit):
        return {
            "symbol": "BTCUSDT",
            "step": INTERVAL_TO_EXCHANGE_REST[interval],
            "start_time": start_time,
            "end_time": start_time + limit * INTERVALS[interval],
        }

    def get_expected_ws_subscription_payload(self, trading_pair, interval):
        return {"action": "subscribe", "args": ["futures/klineBin1m:BTCUSDT"]}

    def get_mock_candlestick_response(self):
        return {"code": 1000, "message": "Ok", "data": [kline(0), kline(60)], "trace": "abc"}

    def get_mock_websocket_message(self):
        return {
            "group": "futures/klineBin1m:BTCUSDT",
            "data": {
                "symbol": "BTCUSDT",
                "items": [{"ts": T0, "o": 2290.0, "h": 2301.0, "l": 2288.0, "c": 2300.5, "v": 10}],
            },
        }

    def test_max_candles_per_request(self):
        assert BitmartPerpetualAdapter.MAX_CANDLES_PER_REQUEST == 1000

    def test_step_is_interval_in_minutes(self, adapter):
        assert adapter._get_rest_params("BTC-USDT", "1h")["step"] == 60
        assert adapter._get_rest_params("BTC-USDT", "1d")["step"] == 1440
        assert adapter._get_rest_params("BTC-USDT", "1w")["step"] == 10080

    def test_window_always_sent_and_spans_limit_intervals(self, adapter):
        """Bitmart answers 400 unless start_time and end_time are both present."""
        params = adapter._get_rest_params("BTC-USDT", "5m", limit=100)
        assert params["end_time"] - params["start_time"] == 100 * 300
        assert params["end_time"] == NOW

    def test_start_time_given_defines_window(self, adapter):
        params = adapter._get_rest_params("BTC-USDT", "5m", start_time=T0, limit=100)
        assert (params["start_time"], params["end_time"]) == (T0, T0 + 100 * 300)

    def test_rest_params_carry_no_limit_field(self, adapter):
        assert "limit" not in adapter._get_rest_params("BTC-USDT", "1m", limit=5)

    def test_parse_rest_response_maps_object_rows(self, adapter):
        candles = adapter._parse_rest_response(self.get_mock_candlestick_response())
        assert [c.timestamp for c in candles] == [T0, T0 + 60]
        assert candles[0].to_array()[:6] == [float(T0), 2290.0, 2301.0, 2288.0, 2300.5, 10.0]

    def test_parse_rest_response_empty_data_is_no_data(self, adapter):
        assert adapter._parse_rest_response({"code": 1000, "data": []}) == []

    @pytest.mark.parametrize(
        "bad",
        [
            None,
            [],
            "x",
            {},
            {"data": None},
            {"code": 30002, "message": "Symbol not exist"},
            {"data": [{"timestamp": T0}]},
            {"data": ["junk"]},
            {"data": [{**kline(), "close_price": "n/a"}]},
        ],
    )
    def test_parse_rest_response_unparseable_raises_value_error(self, adapter, bad):
        with pytest.raises(ValueError, match="unexpected REST response"):
            adapter._parse_rest_response(bad)

    def test_ws_payload_uses_uppercase_hour_suffix(self, adapter):
        payload = adapter.get_ws_subscription_payload("ETH-USDT", "4h")
        assert payload == {"action": "subscribe", "args": ["futures/klineBin4H:ETHUSDT"]}
        assert adapter.get_ws_supported_intervals() == WS_INTERVALS == list(INTERVAL_TO_EXCHANGE_WS)

    def test_parse_ws_message_returns_every_item(self, adapter):
        message = self.get_mock_websocket_message()
        message["data"]["items"].append({"ts": T0 + 60, "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 3})
        assert [c.timestamp for c in adapter.parse_ws_message(message)] == [T0, T0 + 60]

    @pytest.mark.parametrize(
        "message",
        [
            {"action": "subscribe", "group": "futures/klineBin1m:BTCUSDT", "success": True},
            {"data": {"items": []}},
            {"data": {"items": "x"}},
            {"data": {"items": ["junk"]}},
            {"data": "x"},
        ],
    )
    def test_parse_ws_message_ignores_non_candle_payloads(self, adapter, message):
        assert adapter.parse_ws_message(message) is None

    def test_registry_lookup(self):
        assert ExchangeRegistry.get_adapter_class("bitmart_perpetual") is BitmartPerpetualAdapter
        assert isinstance(
            ExchangeRegistry.get_adapter_instance("bitmart_perpetual", network_config=None),
            BitmartPerpetualAdapter,
        )

    def test_factory_lookup(self):
        assert CandlesFactory._CONNECTOR_MAP["bitmart_perpetual"] == "bitmart_perpetual"
        candle = CandlesFactory.get_candle(
            CandlesConfig(connector="bitmart_perpetual", trading_pair="BTC-USDT")
        )
        assert candle.name == "bitmart_perpetual"
