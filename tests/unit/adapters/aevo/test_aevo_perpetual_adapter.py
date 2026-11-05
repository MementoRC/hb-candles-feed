"""Tests for the AevoPerpetualAdapter (offline, fixture based)."""

import pytest

from candles_feed.adapters.aevo.constants import (
    CANDLES_ENDPOINT,
    INTERVAL_TO_EXCHANGE,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WS_INTERVALS,
    WSS_URL,
)
from candles_feed.adapters.aevo.perpetual_adapter import AevoPerpetualAdapter
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.hb_compat.data_types import CandlesConfig
from candles_feed.hb_compat.factory import CandlesFactory
from tests.unit.adapters.base_adapter_test import BaseAdapterTest

T0 = 1704067200  # 2024-01-01T00:00:00Z

# Shaped like GET /mark-history: [timestamp_ns, mark price] string pairs.
HISTORY_RESPONSE = {
    "history": [
        [str(T0 * 10**9), "2290.5"],
        [str((T0 + 60) * 10**9), "2301.25"],
    ]
}

# Shaped like a "ticker-500ms" channel push.
TICKER_MESSAGE = {
    "channel": "ticker-500ms:ETH-PERP",
    "timestamp": str((T0 + 120) * 10**9),
    "data": {
        "timestamp": str((T0 + 120) * 10**9),
        "instrument_id": "2",
        "instrument_name": "ETH-PERP",
        "instrument_type": "PERPETUAL",
        "mark_price": "2305.5",
        "index_price": "2305.1",
        "funding_rate": "0.0001",
    },
}


class TestAevoPerpetualAdapter(BaseAdapterTest):
    """Aevo perpetual adapter tests on top of the shared adapter contract."""

    def create_adapter(self):
        return AevoPerpetualAdapter()

    def get_expected_trading_pair_format(self, trading_pair):
        return f"{trading_pair.split('-')[0]}-PERP"

    def get_expected_rest_url(self):
        return f"{REST_URL}{CANDLES_ENDPOINT}"

    def get_expected_ws_url(self):
        return WSS_URL

    def get_expected_rest_params_minimal(self, trading_pair, interval):
        return {
            "instrument_name": "BTC-PERP",
            "resolution": INTERVAL_TO_EXCHANGE[interval],
            "limit": MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, limit):
        params = self.get_expected_rest_params_minimal(trading_pair, interval)
        params.update({"limit": limit, "start_timestamp": start_time * 10**9})
        return params

    def get_expected_ws_subscription_payload(self, trading_pair, interval):
        return {"op": "subscribe", "data": ["ticker-500ms:BTC-PERP"]}

    def get_mock_candlestick_response(self):
        return HISTORY_RESPONSE

    def get_mock_websocket_message(self):
        return TICKER_MESSAGE

    def test_resolution_is_interval_seconds(self, adapter):
        for interval, seconds in INTERVALS.items():
            assert adapter._get_rest_params("ETH-USDC", interval)["resolution"] == seconds

    def test_start_time_converted_to_nanoseconds(self, adapter):
        params = adapter._get_rest_params("ETH-USDC", "1m", start_time=T0, limit=10)
        assert params["start_timestamp"] == T0 * 10**9
        assert params["limit"] == 10

    def test_timestamp_unit_is_nanoseconds(self, adapter):
        """Regression: TIMESTAMP_UNIT was undefined, so conversion raised NotImplementedError."""
        assert adapter.convert_timestamp_to_exchange(T0) == T0 * 10**9
        assert adapter.ensure_timestamp_in_seconds(T0 * 10**9) == T0

    def test_max_candles_per_request(self):
        assert AevoPerpetualAdapter.MAX_CANDLES_PER_REQUEST == 200

    def test_parse_rest_response_converts_ns_and_uses_mark_price_for_ohlc(self, adapter):
        candles = adapter._parse_rest_response(HISTORY_RESPONSE)
        assert [c.timestamp for c in candles] == [T0, T0 + 60]
        assert candles[0].to_array()[:6] == [float(T0), 2290.5, 2290.5, 2290.5, 2290.5, 0.0]
        assert candles[1].close == 2301.25

    def test_parse_rest_response_empty_history_is_no_data(self, adapter):
        assert adapter._parse_rest_response({"history": []}) == []

    def test_parse_rest_response_skips_short_or_non_list_rows(self, adapter):
        data = {"history": [[str(T0 * 10**9)], "junk", [str(T0 * 10**9), "1.5"]]}
        assert [c.close for c in adapter._parse_rest_response(data)] == [1.5]

    @pytest.mark.parametrize(
        "bad", [None, [], "x", {}, {"history": None}, {"error": "RATE_LIMIT_EXCEEDED"}]
    )
    def test_parse_rest_response_unparseable_raises(self, adapter, bad):
        with pytest.raises(ValueError, match="unexpected REST response"):
            adapter._parse_rest_response(bad)

    def test_ws_intervals_match_rest(self, adapter):
        assert adapter.get_ws_supported_intervals() == WS_INTERVALS == list(INTERVALS)

    def test_ws_subscription_ignores_interval(self, adapter):
        payloads = {
            repr(adapter.get_ws_subscription_payload("ETH-USDC", interval))
            for interval in ("1m", "1h")
        }
        assert len(payloads) == 1

    def test_parse_ws_message_builds_mark_price_candle(self, adapter):
        (candle,) = adapter.parse_ws_message(TICKER_MESSAGE)
        assert candle.timestamp == T0 + 120
        assert (candle.open, candle.high, candle.low, candle.close) == (2305.5,) * 4
        assert candle.volume == 0.0

    def test_parse_ws_message_takes_timestamp_from_data_when_missing_on_envelope(self, adapter):
        message = {k: v for k, v in TICKER_MESSAGE.items() if k != "timestamp"}
        assert adapter.parse_ws_message(message)[0].timestamp == T0 + 120

    def test_parse_ws_message_without_timestamp_uses_now(self, adapter):
        message = {
            "channel": "ticker-500ms:ETH-PERP",
            "data": {"mark_price": "1.0"},
        }
        assert adapter.parse_ws_message(message)[0].timestamp > T0

    @pytest.mark.parametrize(
        "message",
        [
            {"channel": "orderbook:ETH-PERP", "data": {"mark_price": "1"}},
            {"channel": "ticker-500ms:ETH-PERP", "data": "x"},
            {"channel": "ticker-500ms:ETH-PERP", "data": {"index_price": "1"}},
            {"op": "subscribe"},
        ],
    )
    def test_parse_ws_message_ignores_non_ticker_payloads(self, adapter, message):
        assert adapter.parse_ws_message(message) is None

    def test_registry_instance_accepts_network_config(self):
        """Regression: instantiation through the registry must accept constructor kwargs."""
        adapter = ExchangeRegistry.get_adapter_instance("aevo_perpetual", network_config=None)
        assert isinstance(adapter, AevoPerpetualAdapter)

    def test_factory_lookup(self):
        assert CandlesFactory._CONNECTOR_MAP["aevo_perpetual"] == "aevo_perpetual"
        candle = CandlesFactory.get_candle(
            CandlesConfig(connector="aevo_perpetual", trading_pair="ETH-USDC")
        )
        assert candle.name == "aevo_perpetual"
