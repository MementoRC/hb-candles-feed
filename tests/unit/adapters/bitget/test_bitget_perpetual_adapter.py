"""Tests for the BitgetPerpetualAdapter (offline, fixture based)."""

import pytest

from candles_feed.adapters.bitget.constants import (
    PERPETUAL_CANDLES_ENDPOINT,
    PERPETUAL_INTERVAL_TO_EXCHANGE,
    PERPETUAL_REST_URL,
)
from candles_feed.adapters.bitget.perpetual_adapter import BitgetPerpetualAdapter
from tests.unit.adapters.bitget.bitget_contract import T0, BitgetAdapterContract


class TestBitgetPerpetualAdapter(BitgetAdapterContract):
    ADAPTER_CLS = BitgetPerpetualAdapter
    REGISTRY_NAME = "bitget_perpetual"
    CONNECTOR_NAME = "bitget_perpetual"
    REST_INTERVALS = PERPETUAL_INTERVAL_TO_EXCHANGE
    REST_URL = f"{PERPETUAL_REST_URL}{PERPETUAL_CANDLES_ENDPOINT}"
    INST_TYPE = "USDT-FUTURES"
    MIN_ROW_LEN = 7

    def rest_row(self, offset=0, open_="2290.0"):
        # [ts, open, high, low, close, base volume, quote volume]
        return [
            str((T0 + offset) * 1000),
            open_,
            "2301.0",
            "2288.0",
            "2300.5",
            "10.25",
            "23500.0",
        ]

    def get_expected_rest_params_minimal(self, trading_pair, interval):
        params = super().get_expected_rest_params_minimal(trading_pair, interval)
        params["productType"] = "USDT-FUTURES"
        return params

    def test_perpetual_granularity_uses_uppercase_suffixes(self, adapter):
        assert adapter._get_rest_params("BTC-USDT", "1m")["granularity"] == "1m"
        assert adapter._get_rest_params("BTC-USDT", "1h")["granularity"] == "1H"
        assert adapter._get_rest_params("BTC-USDT", "1w")["granularity"] == "1W"

    @pytest.mark.parametrize(
        ("pair", "product_type"),
        [
            ("BTC-USDT", "USDT-FUTURES"),
            ("BTC-USDC", "USDC-FUTURES"),
            ("BTC-USD", "COIN-FUTURES"),
            ("BTC-EUR", "USDT-FUTURES"),
            ("BTCUSDT", "USDT-FUTURES"),
        ],
    )
    def test_product_type_follows_quote_asset(self, adapter, pair, product_type):
        assert adapter._get_rest_params(pair, "1m")["productType"] == product_type
        assert (
            adapter.get_ws_subscription_payload(pair, "1m")["args"][0]["instType"] == product_type
        )

    def test_symbol_has_no_separator(self, adapter):
        assert adapter._get_rest_params("ETH-USDC", "1m")["symbol"] == "ETHUSDC"
