"""
Base Gate.io adapter implementation for the Candle Feed framework.

This module provides a base implementation for Gate.io-based exchange adapters
to reduce code duplication across spot and perpetual markets.
"""

from abc import abstractmethod
from typing import override

from candles_feed.adapters.adapter_mixins import AsyncOnlyAdapter
from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.core.candle_data import CandleData
from candles_feed.core.protocols import NetworkClientProtocol

from .constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST,
    SPOT_CHANNEL_NAME,
    WS_INTERVALS,
)


class GateIoBaseAdapter(BaseAdapter, AsyncOnlyAdapter):
    """Base class for Gate.io exchange adapters.

    This class provides shared functionality for Gate.io spot and perpetual adapters.
    Child classes only need to implement methods that differ between the markets.
    """

    TIMESTAMP_UNIT: str = "seconds"
    REST_PAIR_PARAM: str = "currency_pair"  # futures endpoint calls it "contract"
    MAX_CANDLES_PER_REQUEST = MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST

    @abstractmethod
    def _get_rest_url(self) -> str:
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        pass

    @abstractmethod
    def _get_ws_url(self) -> str:
        """Get WebSocket URL (internal implementation).

        :returns: WebSocket URL
        """
        pass

    @override
    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return self._get_ws_url()

    @abstractmethod
    def get_channel_name(self) -> str:
        """Get WebSocket channel name.

        :returns: Channel name string
        """
        pass

    @staticmethod
    @override
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT")
        :returns: Trading pair in Gate.io format (e.g., "BTC_USDT")
        """
        return trading_pair.replace("-", "_")

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
        params: dict[str, str | int] = {  # type: ignore
            self.REST_PAIR_PARAM: self.get_trading_pair_format(trading_pair),
            "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
            "limit": limit,
        }

        if start_time:
            params["from"] = self.convert_timestamp_to_exchange(start_time)  # type: ignore

        return params

    @override
    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        :param data: REST API response
        :returns: List of CandleData objects
        """
        # Gate.io v4 spot candle format (list rows):
        #   [ts, quote_volume, close, high, low, open, base_volume, window_closed]
        # Gate.io v4 futures candle format (dict rows):
        #   {"t": ts, "v": contracts, "c": close, "h": high, "l": low, "o": open, "sum": quote}
        if not isinstance(data, list):
            raise self._bad_response(data)

        return [self._row_to_candle(row) for row in data]

    def _row_to_candle(self, row: list | dict) -> CandleData:
        """Convert a single REST row (spot list or futures dict) to CandleData.

        :param row: Raw candle row from the Gate.io REST API
        :returns: CandleData object
        """
        if isinstance(row, dict):
            timestamp = row["t"]
            open_, high, low, close = row["o"], row["h"], row["l"], row["c"]
            volume, quote_volume = row["v"], row.get("sum", 0)
        else:
            timestamp = row[0]
            quote_volume, close, high, low, open_, volume = row[1:7]
        return self._build_candle(timestamp, open_, high, low, close, volume, quote_volume)

    def _build_candle(
        self,
        timestamp: str | int,
        open_: str | float,
        high: str | float,
        low: str | float,
        close: str | float,
        volume: str | float,
        quote_volume: str | float,
    ) -> CandleData:
        """Build a CandleData from raw Gate.io values."""
        return CandleData(
            timestamp_raw=self.ensure_timestamp_in_seconds(timestamp),
            open=float(open_),
            high=float(high),
            low=float(low),
            close=float(close),
            volume=float(volume),
            quote_asset_volume=float(quote_volume),
            n_trades=0,  # No trade count data available
            taker_buy_base_volume=0.0,  # No taker data available
            taker_buy_quote_volume=0.0,  # No taker data available
        )

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
        return {
            "method": "subscribe",
            "params": [
                f"{self.get_channel_name()}",
                {
                    "currency_pair": self.get_trading_pair_format(trading_pair),
                    "interval": INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval),
                },
            ],
            "id": 12345,
        }

    @override
    def parse_ws_message(self, data: dict | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        :param data: WebSocket message
        :returns: List of CandleData objects or None if message is not a candle update
        """
        # Gate.io WS candle update:
        # {"channel": "spot.candlesticks", "event": "update",
        #  "result": {"t": ts, "v": quote_volume, "c": close, "h": high, "l": low,
        #             "o": open, "n": "1m_BTC_USDT", "a": base_amount, "w": false}}
        # Futures sends "result" as a list of such dicts (v = contracts, a = quote amount).
        if (
            not isinstance(data, dict)
            or data.get("event") != "update"
            or data.get("channel") != self.get_channel_name()  # type: ignore
        ):
            return None

        result = data.get("result")
        items = result if isinstance(result, list) else [result]
        is_spot = self.get_channel_name() == SPOT_CHANNEL_NAME
        candles: list[CandleData] = []
        for item in items:
            if not isinstance(item, dict) or not {"t", "o", "h", "l", "c", "v"} <= item.keys():
                continue
            volume, quote_volume = (
                (item.get("a", 0), item["v"])
                if is_spot
                else (
                    item["v"],
                    item.get("a", 0),
                )
            )
            candles.append(
                self._build_candle(
                    item["t"], item["o"], item["h"], item["l"], item["c"], volume, quote_volume
                )
            )
        return candles or None

    def get_supported_intervals(self) -> dict[str, int]:
        """Get supported intervals and their durations in seconds.

        :returns: Dictionary mapping interval strings to their duration in seconds
        """
        return INTERVALS

    def get_ws_supported_intervals(self) -> list[str]:
        """Get intervals supported by WebSocket API.

        :returns: List of interval strings supported by WebSocket API
        """
        return WS_INTERVALS
