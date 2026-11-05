"""Tests for the BitgetSpotAdapter (offline, fixture based)."""

from candles_feed.adapters.bitget.constants import (
    SPOT_CANDLES_ENDPOINT,
    SPOT_INTERVAL_TO_EXCHANGE,
    SPOT_REST_URL,
)
from candles_feed.adapters.bitget.spot_adapter import BitgetSpotAdapter
from tests.unit.adapters.bitget.bitget_contract import T0, BitgetAdapterContract


class TestBitgetSpotAdapter(BitgetAdapterContract):
    ADAPTER_CLS = BitgetSpotAdapter
    REGISTRY_NAME = "bitget_spot"
    CONNECTOR_NAME = "bitget"
    REST_INTERVALS = SPOT_INTERVAL_TO_EXCHANGE
    REST_URL = f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"
    INST_TYPE = "SPOT"
    MIN_ROW_LEN = 8

    def rest_row(self, offset=0, open_="2290.0"):
        # [ts, open, high, low, close, base volume, usdt volume, quote volume]
        return [
            str((T0 + offset) * 1000),
            open_,
            "2301.0",
            "2288.0",
            "2300.5",
            "10.25",
            "23500.0",
            "23500.0",
        ]

    def test_spot_granularity_uses_word_suffixes(self, adapter):
        assert adapter._get_rest_params("BTC-USDT", "1m")["granularity"] == "1min"
        assert adapter._get_rest_params("BTC-USDT", "1d")["granularity"] == "1day"
        assert adapter._get_rest_params("BTC-USDT", "1w")["granularity"] == "1week"

    def test_spot_params_have_no_product_type(self, adapter):
        assert "productType" not in adapter._get_rest_params("BTC-USDT", "1m")

    def test_quote_volume_is_taken_from_last_column(self, adapter):
        row = self.rest_row()
        row[6], row[7] = "111.0", "222.0"
        assert adapter._parse_rest_response([row])[0].quote_asset_volume == 222.0
