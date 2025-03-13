"""
MEXC spot exchange adapter for the Candle Feed framework.
"""
import contextlib
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry

from .base_adapter import MEXCBaseAdapter
from .constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    SPOT_CANDLES_ENDPOINT,
    SPOT_KLINE_TOPIC,
    SPOT_REST_URL,
    SPOT_WSS_URL,
)


@ExchangeRegistry.register("mexc_spot")
class MEXCSpotAdapter(MEXCBaseAdapter):
    """MEXC spot exchange adapter."""

    TIMESTAMP_UNIT = "milliseconds"

    @staticmethod
    def _get_rest_url() -> str:
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        return f"{SPOT_REST_URL}{SPOT_CANDLES_ENDPOINT}"

    @staticmethod
    def _get_ws_url() -> str:
        """Get WebSocket URL (internal implementation).

        :returns: WebSocket URL
        """
        return SPOT_WSS_URL

    def get_kline_topic(self) -> str:
        """Get WebSocket kline topic prefix.

        :returns: Kline topic prefix string
        """
        return SPOT_KLINE_TOPIC

    def get_interval_format(self, interval: str) -> str:
        """Get exchange-specific interval format.

        :param interval: Standard interval format
        :returns: Exchange-specific interval format
        """
        return INTERVAL_TO_EXCHANGE_FORMAT.get(interval, interval)

    def _get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
    ) -> dict[str, str | int]:
        """Get parameters for REST API request.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param end_time: End time in seconds
        :param limit: Maximum number of candles to return
        :returns: Dictionary of parameters for REST API request
        """
        params: dict[str, str | int] = {
            "symbol": self.get_trading_pair_format(trading_pair),
            "interval": interval,
        }

        if limit:
            params["limit"] = limit

        if start_time:
            params["startTime"] = self.convert_timestamp_to_exchange(start_time)
        if end_time:
            params["endTime"] = self.convert_timestamp_to_exchange(end_time)

        return params

    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        :param data: REST API response
        :returns: List of CandleData objects
        """
        if data is None:
            return []

        # MEXC REST API format is similar to Binance
        # [
        #   [
        #     1499040000000,      // Open time
        #     "0.01634790",       // Open
        #     "0.80000000",       // High
        #     "0.01575800",       // Low
        #     "0.01577100",       // Close
        #     "148976.11427815",  // Volume
        #     1499644799999,      // Close time
        #     "2434.19055334",    // Quote asset volume
        #     308,                // Number of trades
        #     "1756.87402397",    // Taker buy base asset volume
        #     "28.46694368",      // Taker buy quote asset volume
        #   ]
        # ]

        candles: list[CandleData] = []

        # Check if data is a list (standard format)
        if isinstance(data, list):
            candles.extend(
                CandleData(
                    timestamp_raw=self.ensure_timestamp_in_seconds(row[0]),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
                    quote_asset_volume=float(row[7]),
                    n_trades=int(row[8]),
                    taker_buy_base_volume=float(row[9]),
                    taker_buy_quote_volume=float(row[10]),
                )
                for row in data
                if len(row) >= 11
            )
        return candles

    def parse_ws_message(self, data: dict | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        :param data: WebSocket message
        :returns: List of CandleData objects or None if message is not a candle update
        """
        if data is None:
            return None

        # Check if we have a candle update
        if "d" in data and "c" in data.get("d", {}):
            candle = data["d"]

            with contextlib.suppress(ValueError, TypeError):
                timestamp = self.ensure_timestamp_in_seconds(candle.get("t", 0))
                return [
                    CandleData(
                        timestamp_raw=timestamp,
                        open=float(candle.get("o", 0.0)),
                        high=float(candle.get("h", 0.0)),
                        low=float(candle.get("l", 0.0)),
                        close=float(candle.get("c", 0.0)),
                        volume=float(candle.get("v", 0.0)),
                        quote_asset_volume=float(candle.get("qv", 0.0)),
                        n_trades=int(candle.get("n", 0)),
                        taker_buy_base_volume=0.0,  # Not available in websocket
                        taker_buy_quote_volume=0.0,  # Not available in websocket
                    )
                ]
        return None