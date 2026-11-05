"""Tests for the PacificaPerpetualAdapter (offline, fixture based)."""

import time

import pytest

from candles_feed.adapters.pacifica.constants import (
    CANDLES_ENDPOINT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WS_INTERVALS,
    WSS_URL,
)
from candles_feed.adapters.pacifica.perpetual_adapter import PacificaPerpetualAdapter
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.hb_compat.data_types import CandlesConfig
from candles_feed.hb_compat.factory import CandlesFactory
from tests.unit.adapters.base_adapter_test import BaseAdapterTest

T0 = 1704067200  # 2024-01-01T00:00:00Z
NOW = T0 + 86400


def candle(offset: int = 0, interval_seconds: int = 60) -> dict:
    """One candle object, shaped like a REST row and the WebSocket payload."""
    start_ms = (T0 + offset) * 1000
    return {
        "t": start_ms,
        "T": start_ms + interval_seconds * 1000,
        "s": "BTC",
        "i": "1m",
        "o": "2290.0",
        "c": "2300.5",
        "h": "2301.0",
        "l": "2288.0",
        "v": "10.25",
        "n": 42,
    }


class TestPacificaPerpetualAdapter(BaseAdapterTest):
    """Pacifica perpetual adapter tests on top of the shared adapter contract."""

    @pytest.fixture(autouse=True)
    def frozen_time(self, monkeypatch):
        """The REST window defaults to 'now'; freeze it so params are reproducible."""
        monkeypatch.setattr(time, "time", lambda: NOW)

    def create_adapter(self):
        return PacificaPerpetualAdapter()

    def get_expected_trading_pair_format(self, trading_pair):
        return trading_pair.split("-")[0]

    def get_expected_rest_url(self):
        return f"{REST_URL}{CANDLES_ENDPOINT}"

    def get_expected_ws_url(self):
        return WSS_URL

    def get_expected_rest_params_minimal(self, trading_pair, interval):
        span_ms = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST * INTERVALS[interval] * 1000
        return {
            "symbol": "BTC",
            "interval": interval,
            "start_time": NOW * 1000 - span_ms,
            "end_time": NOW * 1000,
            "limit": MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, limit):
        return {
            "symbol": "BTC",
            "interval": interval,
            "start_time": start_time * 1000,
            "end_time": (start_time + limit * INTERVALS[interval]) * 1000,
            "limit": limit,
        }

    def get_expected_ws_subscription_payload(self, trading_pair, interval):
        return {
            "method": "subscribe",
            "params": {"source": "candle", "symbol": "BTC", "interval": interval},
        }

    def get_mock_candlestick_response(self):
        return {"success": True, "data": [candle(0), candle(60)], "error": None, "code": None}

    def get_mock_websocket_message(self):
        return {"channel": "candle", "data": candle(0)}

    def test_max_candles_per_request(self):
        assert PacificaPerpetualAdapter.MAX_CANDLES_PER_REQUEST == 1000

    def test_symbol_is_base_asset_only(self, adapter):
        assert adapter.get_trading_pair_format("ETH-USDC") == "ETH"
        assert adapter._get_rest_params("ETH-USDC", "1m")["symbol"] == "ETH"

    def test_interval_names_pass_through(self, adapter):
        for interval in INTERVALS:
            assert adapter._get_rest_params("BTC-USDC", interval)["interval"] == interval
        assert adapter.get_ws_supported_intervals() == WS_INTERVALS == list(INTERVALS)

    def test_window_spans_limit_intervals_in_milliseconds(self, adapter):
        params = adapter._get_rest_params("BTC-USDC", "1h", start_time=T0, limit=24)
        assert params["start_time"] == T0 * 1000
        assert params["end_time"] == (T0 + 24 * 3600) * 1000
        assert params["limit"] == 24

    def test_parse_rest_response_maps_fields(self, adapter):
        candles = adapter._parse_rest_response(self.get_mock_candlestick_response())
        assert [c.timestamp for c in candles] == [T0, T0 + 60]
        assert candles[0].to_array() == [
            float(T0),
            2290.0,
            2301.0,
            2288.0,
            2300.5,
            10.25,
            0.0,
            42,
            0.0,
            0.0,
        ]

    def test_parse_rest_response_accepts_bare_list_and_missing_trade_count(self, adapter):
        row = {k: v for k, v in candle().items() if k != "n"}
        (parsed,) = adapter._parse_rest_response([row])
        assert parsed.n_trades == 0

    @pytest.mark.parametrize("payload", [{"success": True, "data": []}, []])
    def test_parse_rest_response_empty_data_is_no_data(self, adapter, payload):
        assert adapter._parse_rest_response(payload) == []

    def test_parse_rest_response_skips_non_dict_rows(self, adapter):
        assert len(adapter._parse_rest_response({"data": ["junk", candle()]})) == 1

    @pytest.mark.parametrize(
        "bad",
        [
            None,
            "x",
            {},
            {"data": None},
            {"success": False, "error": "Invalid symbol", "code": 400},
            {"data": [{"t": T0 * 1000}]},
            {"data": [{**candle(), "o": "n/a"}]},
        ],
    )
    def test_parse_rest_response_unparseable_raises_value_error(self, adapter, bad):
        with pytest.raises(ValueError, match="unexpected REST response"):
            adapter._parse_rest_response(bad)

    def test_parse_ws_message_unwraps_channel_envelope(self, adapter):
        (parsed,) = adapter.parse_ws_message({"channel": "candle", "data": candle(0)})
        assert parsed.to_array() == [
            float(T0),
            2290.0,
            2301.0,
            2288.0,
            2300.5,
            10.25,
            0.0,
            42,
            0.0,
            0.0,
        ]

    def test_parse_ws_message_accepts_bare_candle(self, adapter):
        assert adapter.parse_ws_message(candle(60))[0].timestamp == T0 + 60

    @pytest.mark.parametrize(
        "message",
        [
            {"channel": "subscribe", "data": {"source": "candle", "symbol": "BTC"}},
            {"channel": "candle", "data": {}},
            {"channel": "candle", "data": []},
            {"t": T0 * 1000},
        ],
    )
    def test_parse_ws_message_ignores_non_candle_payloads(self, adapter, message):
        assert adapter.parse_ws_message(message) is None

    def test_registry_lookup(self):
        assert ExchangeRegistry.get_adapter_class("pacifica_perpetual") is PacificaPerpetualAdapter
        assert isinstance(
            ExchangeRegistry.get_adapter_instance("pacifica_perpetual", network_config=None),
            PacificaPerpetualAdapter,
        )

    def test_factory_lookup(self):
        assert CandlesFactory._CONNECTOR_MAP["pacifica_perpetual"] == "pacifica_perpetual"
        built = CandlesFactory.get_candle(
            CandlesConfig(connector="pacifica_perpetual", trading_pair="BTC-USDC")
        )
        assert built.name == "pacifica_perpetual"
