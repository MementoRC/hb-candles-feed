"""
KuCoin perpetual exchange adapter for the Candle Feed framework.
"""

import time
from typing import Dict, List, Optional

from candles_feed.adapters.kucoin.constants import INTERVAL_TO_KUCOIN_PERP_FORMAT
from candles_feed.adapters.kucoin.kucoin_base_adapter import KuCoinBaseAdapter
from candles_feed.adapters.kucoin_perpetual.constants import (
    PERP_CANDLES_ENDPOINT,
    PERP_REST_URL,
    PERP_WSS_URL,
)
from candles_feed.core.candle_data import CandleData
from candles_feed.core.exchange_registry import ExchangeRegistry


@ExchangeRegistry.register("kucoin_perpetual")
class KuCoinPerpetualAdapter(KuCoinBaseAdapter):
    """KuCoin perpetual exchange adapter."""

    def get_rest_url(self) -> str:
        """Get REST API URL for candles.

        Returns:
            REST API URL
        """
        return f"{PERP_REST_URL}{PERP_CANDLES_ENDPOINT}"

    def get_ws_url(self) -> str:
        """Get WebSocket URL.

        Returns:
            WebSocket URL
        """
        return PERP_WSS_URL

    def get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
    ) -> dict[str, str | int]:
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
        # KuCoin Futures uses different API parameters
        params: dict[str, str | int] = {
            "symbol": trading_pair,
            "granularity": INTERVAL_TO_KUCOIN_PERP_FORMAT.get(interval, interval),
        }

        if start_time:
            params["from"] = start_time * 1000  # Convert to milliseconds

        if end_time:
            params["to"] = end_time * 1000  # Convert to milliseconds

        return params

    def parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        Args:
            data: REST API response

        Returns:
            List of CandleData objects
        """
        # KuCoin Futures candle format:
        # {
        #   "code": "200000",
        #   "data": [
        #     [
        #       1602832560,  // timestamp
        #       13059.3,     // open
        #       13059.3,     // close
        #       13059.8,     // high
        #       13058.1,     // low
        #       0.3,         // volume
        #       3918.36      // turnover
        #     ],
        #     ...
        #   ]
        # }

        candles: list[CandleData] = []

        if data is None:
            return candles

        if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
            for row in data["data"]:
                if len(row) >= 7:  # Ensure we have enough data
                    candles.append(
                        CandleData(
                            timestamp_raw=row[0],  # Already in seconds
                            open=float(row[1]),
                            high=float(row[3]),  # Different order in perpetual
                            low=float(row[4]),
                            close=float(row[2]),  # Different order in perpetual
                            volume=float(row[5]),
                            quote_asset_volume=float(row[6]),  # turnover
                            n_trades=0,  # Not provided by KuCoin Futures
                            taker_buy_base_volume=0.0,  # Not provided
                            taker_buy_quote_volume=0.0,  # Not provided
                        )
                    )
        return candles

    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.

        Args:
            trading_pair: Trading pair
            interval: Candle interval

        Returns:
            WebSocket subscription payload
        """
        # Futures uses a different topic format
        perp_interval = INTERVAL_TO_KUCOIN_PERP_FORMAT.get(interval, interval)
        return {
            "id": int(time.time() * 1000),
            "type": "subscribe",
            "topic": f"/contractMarket/candle:{trading_pair}_{perp_interval}",
            "privateChannel": False,
            "response": True,
        }

    def parse_ws_message(self, data: dict | None) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        Args:
            data: WebSocket message

        Returns:
            List of CandleData objects or None if message is not a candle update
        """
        # KuCoin Futures websocket message format:
        # {
        #   "type": "message",
        #   "topic": "/contractMarket/candle:BTCUSDTM_1min",
        #   "subject": "candle.update",
        #   "data": {
        #     "symbol": "BTCUSDTM",
        #     "candles": [
        #       "1620279780",     // timestamp
        #       "57041.1",        // open
        #       "57041.1",        // close
        #       "57041.1",        // high
        #       "57041.1",        // low
        #       "0",              // volume
        #       "0",              // turnover
        #       "1min"            // interval
        #     ]
        #   }
        # }

        # Handle None input
        if data is None:
            return None

        if (
            data.get("type") == "message"
            and "data" in data
            and "candles" in data["data"]
            and "/contractMarket/candle:" in data.get("topic", "")
        ):
            candle_data = data["data"]["candles"]

            # Ensure we have enough data
            if len(candle_data) >= 7:
                return [
                    CandleData(
                        timestamp_raw=int(candle_data[0]),  # Already in seconds
                        open=float(candle_data[1]),
                        high=float(candle_data[3]),  # Different order in perpetual
                        low=float(candle_data[4]),
                        close=float(candle_data[2]),  # Different order in perpetual
                        volume=float(candle_data[5]),
                        quote_asset_volume=float(candle_data[6]),  # turnover
                        n_trades=0,  # Not provided by KuCoin Futures
                        taker_buy_base_volume=0.0,  # Not provided
                        taker_buy_quote_volume=0.0,  # Not provided
                    )
                ]

        return None
