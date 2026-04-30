"""
Bitget perpetual exchange adapter for the Candle Feed framework.
"""

from typing import Any, override

from candles_feed.adapters.adapter_mixins import AsyncOnlyAdapter
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.protocols import NetworkClientProtocol

from .constants import (
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    PERPETUAL_CANDLES_ENDPOINT,
    PERPETUAL_INTERVAL_TO_EXCHANGE,
    PERPETUAL_REST_URL,
    WS_INTERVAL_TO_EXCHANGE,
    WS_INTERVALS,
    WSS_URL,
)

# Mapping from quote asset to Bitget product type
_QUOTE_TO_PRODUCT_TYPE: dict[str, str] = {
    "USDT": "USDT-FUTURES",
    "USDC": "USDC-FUTURES",
    "USD": "COIN-FUTURES",
}

# Mapping from product type to WebSocket instType
_PRODUCT_TYPE_TO_WS_INST_TYPE: dict[str, str] = {
    "USDT-FUTURES": "USDT-FUTURES",
    "USDC-FUTURES": "USDC-FUTURES",
    "COIN-FUTURES": "COIN-FUTURES",
}


def _get_product_type(trading_pair: str) -> str:
    """Determine Bitget product type from trading pair quote asset.

    :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT")
    :returns: Bitget product type string
    """
    quote = trading_pair.split("-")[-1].upper() if "-" in trading_pair else ""
    return _QUOTE_TO_PRODUCT_TYPE.get(quote, "USDT-FUTURES")


@ExchangeRegistry.register("bitget_perpetual")
class BitgetPerpetualAdapter(BaseAdapter, AsyncOnlyAdapter):
    """Bitget perpetual exchange adapter."""

    TIMESTAMP_UNIT: str = "milliseconds"

    @staticmethod
    @override
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT")
        :returns: Trading pair in Bitget perpetual format (e.g., "BTCUSDT")
        """
        return trading_pair.replace("-", "")

    @override
    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals and their durations in seconds.

        :returns: Dictionary mapping interval strings to their duration in seconds
        """
        return INTERVALS

    @override
    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return WSS_URL

    @override
    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.

        :returns: List of interval strings supported by WebSocket API
        """
        return WS_INTERVALS

    @staticmethod
    @override
    def _get_rest_url() -> str:
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        return f"{PERPETUAL_REST_URL}{PERPETUAL_CANDLES_ENDPOINT}"

    @override
    def _get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    ) -> dict[str, str | int]:
        """Get parameters for REST API request.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Maximum number of candles to return
        :returns: Dictionary of parameters for REST API request
        """
        product_type = _get_product_type(trading_pair)
        params: dict[str, str | int] = {
            "symbol": self.get_trading_pair_format(trading_pair),
            "granularity": PERPETUAL_INTERVAL_TO_EXCHANGE.get(interval, interval),
            "productType": product_type,
            "limit": limit,
        }

        if start_time:
            params["startTime"] = self.convert_timestamp_to_exchange(start_time)
            params["endTime"] = self.convert_timestamp_to_exchange(
                start_time + limit * INTERVALS.get(interval, 60)
            )

        return params

    @override
    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        Bitget perpetual candle format:
        [
          [
            "1639984000000",  // timestamp (ms)
            "47000.00",       // open
            "47500.00",       // high
            "46800.00",       // low
            "47200.00",       // close
            "123.456",        // volume (base asset)
            "5823456.78"      // quote asset volume
          ],
          ...
        ]

        :param data: REST API response
        :returns: List of CandleData objects
        """
        if data is None:
            return []

        # Bitget may wrap data in a "data" key or return direct array
        if isinstance(data, dict):
            candle_list = data.get("data")
            if not isinstance(candle_list, list):
                return []
        elif isinstance(data, list):
            candle_list = data
        else:
            return []

        candles: list[CandleData] = []
        for row in candle_list:
            if not isinstance(row, list) or len(row) < 7:
                continue
            candles.append(
                CandleData(
                    timestamp_raw=self.ensure_timestamp_in_seconds(row[0]),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
                    quote_asset_volume=float(row[6]),
                )
            )
        return candles

    @override
    async def fetch_rest_candles(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        network_client: NetworkClientProtocol | None = None,
    ) -> list[CandleData]:
        """Fetch candles from REST API asynchronously.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Maximum number of candles to return
        :param network_client: Network client to use for API requests
        :returns: List of CandleData objects
        """
        return await AsyncOnlyAdapter._fetch_rest_candles(
            adapter_implementation=self,
            trading_pair=trading_pair,
            interval=interval,
            start_time=start_time,
            limit=limit,
            network_client=network_client,
        )

    @override
    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :returns: WebSocket subscription payload
        """
        exchange_interval = WS_INTERVAL_TO_EXCHANGE.get(interval, interval)
        product_type = _get_product_type(trading_pair)
        inst_type = _PRODUCT_TYPE_TO_WS_INST_TYPE.get(product_type, "USDT-FUTURES")
        return {
            "op": "subscribe",
            "args": [
                {
                    "instType": inst_type,
                    "channel": f"candle{exchange_interval}",
                    "instId": self.get_trading_pair_format(trading_pair),
                }
            ],
        }

    @override
    def parse_ws_message(self, data: dict[str, Any] | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        Bitget WebSocket candle message format:
        {
          "action": "update",
          "arg": {"instType": "USDT-FUTURES", "channel": "candle1m", "instId": "BTCUSDT"},
          "data": [
            ["1639984000000", "47000.00", "47500.00", "46800.00", "47200.00", "123.456", "5823456.78"]
          ]
        }

        :param data: WebSocket message
        :returns: List of CandleData objects or None if message is not a candle update
        """
        if data is None:
            return None

        # Only process "update" action messages
        if data.get("action") != "update":
            return None

        raw_data = data.get("data")
        if not isinstance(raw_data, list) or len(raw_data) == 0:
            return None

        row = raw_data[0]
        if not isinstance(row, list) or len(row) < 7:
            return None

        return [
            CandleData(
                timestamp_raw=self.ensure_timestamp_in_seconds(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
                quote_asset_volume=float(row[6]),
            )
        ]
