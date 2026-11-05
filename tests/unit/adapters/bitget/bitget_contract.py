"""Shared offline contract tests for the Bitget spot and perpetual adapters.

Concrete test modules subclass :class:`BitgetAdapterContract` and set the class attributes.
"""

import pytest

from candles_feed.adapters.bitget.constants import (
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    WS_INTERVAL_TO_EXCHANGE,
    WSS_URL,
)
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.hb_compat.data_types import CandlesConfig
from candles_feed.hb_compat.factory import CandlesFactory
from tests.unit.adapters.base_adapter_test import BaseAdapterTest

T0 = 1704067200  # 2024-01-01T00:00:00Z


class BitgetAdapterContract(BaseAdapterTest):
    """Behaviour every Bitget adapter must satisfy."""

    ADAPTER_CLS: type
    REGISTRY_NAME: str
    CONNECTOR_NAME: str  # upstream hummingbot connector name
    REST_INTERVALS: dict[str, str]
    REST_URL: str
    INST_TYPE: str  # instType in the WS subscription for BTC-USDT
    MIN_ROW_LEN: int  # columns the REST parser needs

    def rest_row(self, offset: int = 0, open_: str = "2290.0") -> list[str]:
        """Build one REST candle row of the exchange's documented width."""
        raise NotImplementedError

    def create_adapter(self):
        return self.ADAPTER_CLS()

    def get_expected_trading_pair_format(self, trading_pair):
        return trading_pair.replace("-", "")

    def get_expected_rest_url(self):
        return self.REST_URL

    def get_expected_ws_url(self):
        return WSS_URL

    def get_expected_rest_params_minimal(self, trading_pair, interval):
        return {
            "symbol": "BTCUSDT",
            "granularity": self.REST_INTERVALS[interval],
            "limit": MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        }

    def get_expected_rest_params_full(self, trading_pair, interval, start_time, limit):
        params = self.get_expected_rest_params_minimal(trading_pair, interval)
        params.update(
            {
                "limit": limit,
                "startTime": start_time * 1000,
                "endTime": (start_time + limit * INTERVALS[interval]) * 1000,
            }
        )
        return params

    def get_expected_ws_subscription_payload(self, trading_pair, interval):
        return {
            "op": "subscribe",
            "args": [
                {
                    "instType": self.INST_TYPE,
                    "channel": f"candle{WS_INTERVAL_TO_EXCHANGE[interval]}",
                    "instId": "BTCUSDT",
                }
            ],
        }

    def get_mock_candlestick_response(self):
        return {
            "code": "00000",
            "msg": "success",
            "requestTime": T0 * 1000,
            "data": [self.rest_row(60, "2300.5"), self.rest_row(0)],
        }

    def get_mock_websocket_message(self):
        return {
            "action": "update",
            "arg": {"instType": self.INST_TYPE, "channel": "candle1m", "instId": "BTCUSDT"},
            "data": [self.rest_row(0)[:7]],
            "ts": T0 * 1000 + 500,
        }

    def test_all_intervals_map_to_exchange_granularity(self, adapter):
        for interval, code in self.REST_INTERVALS.items():
            assert adapter._get_rest_params("BTC-USDT", interval)["granularity"] == code
        assert set(self.REST_INTERVALS) == set(adapter.get_supported_intervals())

    def test_rest_window_is_limit_intervals_from_start(self, adapter):
        params = adapter._get_rest_params("BTC-USDT", "5m", start_time=T0, limit=100)
        assert params["startTime"] == T0 * 1000
        assert params["endTime"] == (T0 + 100 * 300) * 1000
        assert params["limit"] == 100

    def test_rest_without_start_time_has_no_window(self, adapter):
        params = adapter._get_rest_params("BTC-USDT", "1m")
        assert "startTime" not in params
        assert "endTime" not in params

    def test_default_limit_is_max_candles_per_request(self, adapter):
        assert self.ADAPTER_CLS.MAX_CANDLES_PER_REQUEST == MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST
        assert (
            adapter._get_rest_params("BTC-USDT", "1m")["limit"]
            == self.ADAPTER_CLS.MAX_CANDLES_PER_REQUEST
        )

    def test_parse_rest_response_maps_columns_and_keeps_exchange_order(self, adapter):
        candles = adapter._parse_rest_response(self.get_mock_candlestick_response())
        assert [c.timestamp for c in candles] == [T0 + 60, T0]
        assert candles[0].to_array()[:6] == [float(T0 + 60), 2300.5, 2301.0, 2288.0, 2300.5, 10.25]
        assert candles[0].quote_asset_volume == 23500.0

    def test_parse_rest_response_accepts_bare_list(self, adapter):
        assert len(adapter._parse_rest_response([self.rest_row(0)])) == 1

    def test_parse_rest_response_empty_data_is_no_data(self, adapter):
        assert adapter._parse_rest_response({"code": "00000", "data": []}) == []
        assert adapter._parse_rest_response([]) == []

    def test_parse_rest_response_skips_short_and_non_list_rows(self, adapter):
        short = self.rest_row(0)[: self.MIN_ROW_LEN - 1]
        data = {"data": [short, "junk", self.rest_row(60)]}
        assert [c.timestamp for c in adapter._parse_rest_response(data)] == [T0 + 60]

    @pytest.mark.parametrize(
        "bad",
        [None, "x", 5, {}, {"data": None}, {"code": "40009", "msg": "sign signature error"}],
    )
    def test_parse_rest_response_unparseable_raises(self, adapter, bad):
        with pytest.raises(ValueError, match="unexpected REST response"):
            adapter._parse_rest_response(bad)

    def test_ws_intervals_use_exchange_codes(self, adapter):
        assert adapter.get_ws_supported_intervals() == list(WS_INTERVAL_TO_EXCHANGE)
        payload = adapter.get_ws_subscription_payload("BTC-USDT", "1h")
        assert payload["args"][0]["channel"] == "candle1H"

    def test_parse_ws_message_maps_columns(self, adapter):
        (candle,) = adapter.parse_ws_message(self.get_mock_websocket_message())
        assert candle.to_array()[:7] == [float(T0), 2290.0, 2301.0, 2288.0, 2300.5, 10.25, 23500.0]

    @pytest.mark.parametrize(
        "message",
        [
            {"event": "subscribe", "arg": {"channel": "candle1m"}},
            {"action": "snapshot", "data": [["1704067200000"] + ["1"] * 6]},
            {"action": "update", "data": []},
            {"action": "update", "data": "x"},
            {"action": "update", "data": [["1704067200000", "1", "2"]]},
        ],
    )
    def test_parse_ws_message_ignores_non_candle_payloads(self, adapter, message):
        assert adapter.parse_ws_message(message) is None

    def test_registry_lookup(self):
        assert ExchangeRegistry.get_adapter_class(self.REGISTRY_NAME) is self.ADAPTER_CLS
        assert isinstance(
            ExchangeRegistry.get_adapter_instance(self.REGISTRY_NAME, network_config=None),
            self.ADAPTER_CLS,
        )

    def test_factory_lookup(self):
        assert CandlesFactory._CONNECTOR_MAP[self.CONNECTOR_NAME] == self.REGISTRY_NAME
        candle = CandlesFactory.get_candle(
            CandlesConfig(connector=self.CONNECTOR_NAME, trading_pair="BTC-USDT")
        )
        assert candle.name == self.REGISTRY_NAME
