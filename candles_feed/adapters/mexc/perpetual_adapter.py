"""
MEXC perpetual exchange adapter for the Candle Feed framework.
"""

import contextlib

from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry

from .base_adapter import MEXCBaseAdapter
from .constants import (
    INTERVAL_TO_PERPETUAL_FORMAT,
    PERPETUAL_KLINE_TOPIC,
    PERPETUAL_REST_URL,
    PERPETUAL_WSS_URL,
)


@ExchangeRegistry.register("mexc_perpetual")
class MEXCPerpetualAdapter(MEXCBaseAdapter):
    """MEXC perpetual exchange adapter."""

    TIMESTAMP_UNIT = "seconds"

    @staticmethod
    def _get_rest_url() -> str:
        """Get REST API URL for candles.

        :returns: REST API URL
        """
        return PERPETUAL_REST_URL

    @staticmethod
    def _get_ws_url() -> str:
        """Get WebSocket URL.

        :returns: WebSocket URL
        """
        return PERPETUAL_WSS_URL

    def get_kline_topic(self) -> str:
        """Get WebSocket kline topic prefix.

        :returns: Kline topic prefix string
        """
        return PERPETUAL_KLINE_TOPIC

    def get_interval_format(self, interval: str) -> str:
        """Get exchange-specific interval format.

        :param interval: Standard interval format
        :returns: Exchange-specific interval format
        """
        return INTERVAL_TO_PERPETUAL_FORMAT.get(interval, interval)

    def _get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        limit: int = 500,
    ) -> dict:
        """Get parameters for REST API request.

        :param trading_pair: Trading pair
        :param interval: Candle interval
        :param start_time: Start time in seconds
        :param limit: Maximum number of candles to return
        :returns: Dictionary of parameters for REST API request
        """
        # MEXC Contract API uses different parameter names
        params: dict[str, str | int] = {
            "symbol": self.get_trading_pair_format(trading_pair),
            "interval": self.get_interval_format(interval),
        }

        # limit is now an int with a default. MEXC Perpetual uses "size".
        params["size"] = limit

        if start_time:
            params["start"] = self.convert_timestamp_to_exchange(start_time)

        return params

    def _parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        :param data: REST API response
        :returns: List of CandleData objects
        """
        if (
            data is None
            or not isinstance(data, dict)
            or "data" not in data
            or not isinstance(data["data"], list)
        ):
            return []

        # MEXC Contract REST API format:
        # {
        #   "success": true,
        #   "code": 0,
        #   "data": [
        #     {
        #       "time": 1603123200,  // Open time
        #       "open": "11930.63",  // Open price
        #       "close": "11924.13", // Close price
        #       "high": "11936.73",  // High price
        #       "low": "11923.83",   // Low price
        #       "vol": "265.64788", // Volume (in contracts)
        #       "amount": "3171102" // Quote volume
        #     },
        #     ...
        #   ]
        # }

        candles: list[CandleData] = []
        candles.extend(
            CandleData(
                timestamp_raw=self.ensure_timestamp_in_seconds(obj["time"]),  # Already in seconds
                open=float(obj["open"]),
                high=float(obj["high"]),
                low=float(obj["low"]),
                close=float(obj["close"]),
                volume=float(obj["vol"]),
                quote_asset_volume=float(obj["amount"]),
                n_trades=0,  # Not provided by MEXC Contract API
                taker_buy_base_volume=0.0,  # Not provided
                taker_buy_quote_volume=0.0,  # Not provided
            )
            for obj in data["data"]
        )
        return candles

    def parse_ws_message(self, data: dict | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        :param data: WebSocket message
        :returns: List of CandleData objects or None if message is not a candle update
        """
        if data is None:
            return None

        # Contract WebSocket format is different from spot
        # {
        #   "channel": "push.kline",
        #   "data": {
        #     "a": "7236.16",  // amount (quote volume)
        #     "c": "41573.11", // close
        #     "h": "41771.37", // high
        #     "interval": "Min15", // interval
        #     "l": "41528.81",  // low
        #     "o": "41724.93",  // open
        #     "q": "0",         // ignore
        #     "symbol": "BTC_USDT", // symbol
        #     "t": 1617345900,  // timestamp
        #     "v": "0.174"      // volume
        #   },
        #   "symbol": "BTC_USDT"
        # }

        if "channel" in data and "data" in data and data.get("channel") == "push.kline":
            candle = data["data"]

            with contextlib.suppress(ValueError, TypeError):
                return [
                    CandleData(
                        timestamp_raw=self.ensure_timestamp_in_seconds(candle.get("t", 0)),
                        open=float(candle.get("o", 0.0)),
                        high=float(candle.get("h", 0.0)),
                        low=float(candle.get("l", 0.0)),
                        close=float(candle.get("c", 0.0)),
                        volume=float(candle.get("v", 0.0)),
                        quote_asset_volume=float(candle.get("a", 0.0)),
                        n_trades=0,  # Not available in contract websocket
                        taker_buy_base_volume=0.0,  # Not available
                        taker_buy_quote_volume=0.0,  # Not available
                    )
                ]
        return None
