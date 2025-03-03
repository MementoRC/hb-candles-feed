"""
MEXC perpetual exchange adapter for the Candle Feed framework.
"""

from typing import List, Optional

from candles_feed.adapters.mexc.constants import INTERVAL_TO_MEXC_CONTRACT_FORMAT
from candles_feed.adapters.mexc.mexc_base_adapter import MEXCBaseAdapter
from candles_feed.adapters.mexc_perpetual.constants import (
    PERP_CANDLES_ENDPOINT,
    PERP_KLINE_TOPIC,
    PERP_REST_URL,
    PERP_WSS_URL,
)
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("mexc_perpetual")
class MEXCPerpetualAdapter(MEXCBaseAdapter):
    """MEXC perpetual exchange adapter."""

    def get_rest_url(self) -> str:
        """Get REST API URL for candles.

        Returns:
            REST API URL
        """
        return PERP_REST_URL

    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        Returns:
            WebSocket URL
        """
        return PERP_WSS_URL

    def get_kline_topic(self) -> str:
        """Get WebSocket kline topic prefix.

        Returns:
            Kline topic prefix string
        """
        return PERP_KLINE_TOPIC

    def get_interval_format(self, interval: str) -> str:
        """Get exchange-specific interval format.

        Args:
            interval: Standard interval format

        Returns:
            Exchange-specific interval format
        """
        return INTERVAL_TO_MEXC_CONTRACT_FORMAT.get(interval, interval)

    def get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """Get parameters for REST API request.

        Args:
            trading_pair: Trading pair
            interval: Candle interval
            start_time: Start time in seconds
            end_time: End time in seconds
            limit: Maximum number of candles to return

        Returns:
            Dictionary of parameters for REST API request
        """
        # MEXC Contract API uses different parameter names
        params = {
            "symbol": self.get_trading_pair_format(trading_pair),
            "interval": self.get_interval_format(interval),
        }

        if limit:
            params["size"] = limit

        if start_time:
            params["start"] = start_time  # Already in seconds for contract API
        if end_time:
            params["end"] = end_time  # Already in seconds for contract API

        return params

    def parse_rest_response(self, data: Optional[dict]) -> List[CandleData]:
        """Parse REST API response into CandleData objects.

        Args:
            data: REST API response

        Returns:
            List of CandleData objects
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

        candles = []
        for obj in data["data"]:
            candles.append(
                CandleData(
                    timestamp_raw=obj["time"],  # Already in seconds
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
            )
        return candles

    def parse_ws_message(self, data: Optional[dict]) -> Optional[List[CandleData]]:
        """Parse WebSocket message into CandleData objects.

        Args:
            data: WebSocket message

        Returns:
            List of CandleData objects or None if message is not a candle update
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

            try:
                return [
                    CandleData(
                        timestamp_raw=candle.get("t", 0),  # Already in seconds
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
            except (ValueError, TypeError):
                pass

        return None
