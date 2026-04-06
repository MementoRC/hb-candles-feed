"""
Dexalot spot exchange adapter for the Candle Feed framework.
"""

from typing import Any

from candles_feed.adapters.adapter_mixins import AsyncOnlyAdapter
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry
from candles_feed.core.protocols import NetworkClientProtocol

from .constants import (
    CANDLES_ENDPOINT,
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    REST_URL,
    WS_INTERVALS,
    WSS_URL,
)


@ExchangeRegistry.register("dexalot_spot")
class DexalotSpotAdapter(BaseAdapter, AsyncOnlyAdapter):
    """Dexalot spot exchange adapter.

    Dexalot is a decentralized exchange. This adapter supports 6 intervals
    and uses ISO 8601 timestamps for both REST and WebSocket APIs.
    """

    TIMESTAMP_UNIT: str = "iso8601"

    @staticmethod
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert standard trading pair format to Dexalot exchange format.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USD").
        :returns: Trading pair in Dexalot format (e.g., "BTC/USD").
        """
        return trading_pair.replace("-", "/")

    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals and their durations in seconds.

        :returns: Dictionary mapping interval strings to their duration in seconds.
        """
        return INTERVALS

    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL.
        """
        return WSS_URL

    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.

        :returns: List of interval strings supported by WebSocket API.
        """
        return WS_INTERVALS

    @staticmethod
    def _get_rest_url() -> str:
        """Get REST API URL for candles.

        :returns: REST API URL for candles endpoint.
        """
        return f"{REST_URL}{CANDLES_ENDPOINT}"

    @staticmethod
    def _interval_to_num_and_str(interval: str) -> tuple[str, str]:
        """Convert standard interval string to Dexalot intervalnum and intervalstr.

        The Dexalot API expects separate ``intervalnum`` and ``intervalstr`` params.
        For example, ``"5m"`` → ``intervalnum="5"``, ``intervalstr="minute"``.

        :param interval: Standard interval string (e.g., ``"5m"``, ``"1h"``, ``"1d"``).
        :returns: Tuple of (intervalnum, intervalstr).
        """
        unit = interval[-1]
        if unit == "m":
            intervalstr = "minute"
        elif unit == "h":
            intervalstr = "hour"
        elif unit == "d":
            intervalstr = "day"
        else:
            intervalstr = ""
        # Exchange format e.g. "M5" → numeric part is everything after the first char
        exchange_fmt = INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)
        intervalnum = exchange_fmt[1:]
        return intervalnum, intervalstr

    def _get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    ) -> dict[str, str | int]:
        """Get parameters for REST API request.

        The Dexalot API requires ``intervalnum`` (numeric part, e.g. ``"5"``) and
        ``intervalstr`` (unit word, e.g. ``"minute"``) as separate parameters rather
        than a combined ``interval`` field.

        :param trading_pair: Trading pair.
        :param interval: Candle interval.
        :param start_time: Start time in seconds.
        :param limit: Maximum number of candles to return (not used by Dexalot API).
        :returns: Dictionary of parameters for REST API request.
        """
        intervalnum, intervalstr = self._interval_to_num_and_str(interval)
        params: dict[str, str | int] = {
            "pair": self.get_trading_pair_format(trading_pair),
            "intervalnum": intervalnum,
            "intervalstr": intervalstr,
        }

        if start_time is not None:
            end_time = start_time + limit * INTERVALS[interval]
            start_isotime = self.convert_timestamp_to_exchange(start_time)
            end_isotime = self.convert_timestamp_to_exchange(end_time)
            params["periodfrom"] = str(start_isotime)
            params["periodto"] = str(end_isotime)

        return params

    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        Dexalot REST API response format:
        [
            {
                "date": "2024-01-01T00:00:00.000Z",
                "open": 42000.0,
                "high": 42500.0,
                "low": 41800.0,
                "close": 42200.0,
                "volume": 1.5
            },
            ...
        ]

        :param data: REST API response.
        :returns: List of CandleData objects.
        """
        if not isinstance(data, list):
            return []

        candles: list[CandleData] = []
        for candle_item in data:
            if not isinstance(candle_item, dict):
                continue

            raw_open = candle_item.get("open", 0)
            raw_high = candle_item.get("high", 0)
            raw_low = candle_item.get("low", 0)
            raw_close = candle_item.get("close", 0)
            raw_volume = candle_item.get("volume", 0)

            candles.append(
                CandleData(
                    timestamp_raw=self.ensure_timestamp_in_seconds(candle_item.get("date", 0)),
                    open=float(raw_open) if raw_open != "None" and raw_open is not None else 0.0,
                    high=float(raw_high) if raw_high != "None" and raw_high is not None else 0.0,
                    low=float(raw_low) if raw_low != "None" and raw_low is not None else 0.0,
                    close=float(raw_close)
                    if raw_close != "None" and raw_close is not None
                    else 0.0,
                    volume=float(raw_volume)
                    if raw_volume != "None" and raw_volume is not None
                    else 0.0,
                )
            )
        return candles

    async def fetch_rest_candles(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
        network_client: NetworkClientProtocol | None = None,
    ) -> list[CandleData]:
        """Fetch candles from REST API asynchronously.

        :param trading_pair: Trading pair.
        :param interval: Candle interval.
        :param start_time: Start time in seconds.
        :param limit: Maximum number of candles to return.
        :param network_client: Network client to use for API requests.
        :returns: List of CandleData objects.
        """
        return await AsyncOnlyAdapter._fetch_rest_candles(
            adapter_implementation=self,
            trading_pair=trading_pair,
            interval=interval,
            start_time=start_time,
            limit=limit,
            network_client=network_client,
        )

    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.

        :param trading_pair: Trading pair.
        :param interval: Candle interval.
        :returns: WebSocket subscription payload.
        """
        return {
            "pair": self.get_trading_pair_format(trading_pair),
            "chart": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "type": "chart-v2-subscribe",
        }

    def parse_ws_message(self, data: dict[str, Any] | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        Dexalot WebSocket message format:
        {
            "type": "liveCandle",
            "data": [
                {
                    "date": "2024-01-01T00:05:00.000Z",
                    "open": 42000.0,
                    "high": 42500.0,
                    "low": 41800.0,
                    "close": 42200.0,
                    "volume": 1.5
                },
                ...
            ]
        }
        The last element of the data array (data[-1]) is the most current candle.

        :param data: WebSocket message.
        :returns: List of CandleData objects or None if message is not a candle update.
        """
        if data is None:
            return None

        if not isinstance(data, dict):
            return None

        if data.get("type") != "liveCandle":
            return None

        candle_array = data.get("data")
        if not isinstance(candle_array, list) or len(candle_array) == 0:
            return None

        candle_item = candle_array[-1]
        if not isinstance(candle_item, dict):
            return None

        raw_open = candle_item.get("open", 0)
        raw_high = candle_item.get("high", 0)
        raw_low = candle_item.get("low", 0)
        raw_close = candle_item.get("close", 0)
        raw_volume = candle_item.get("volume", 0)

        return [
            CandleData(
                timestamp_raw=self.ensure_timestamp_in_seconds(candle_item.get("date", 0)),
                open=float(raw_open) if raw_open != "None" and raw_open is not None else 0.0,
                high=float(raw_high) if raw_high != "None" and raw_high is not None else 0.0,
                low=float(raw_low) if raw_low != "None" and raw_low is not None else 0.0,
                close=float(raw_close) if raw_close != "None" and raw_close is not None else 0.0,
                volume=float(raw_volume)
                if raw_volume != "None" and raw_volume is not None
                else 0.0,
            )
        ]
