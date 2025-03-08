"""
Coinbase Advanced Trade adapter for the Candle Feed framework.
"""
from abc import ABC, abstractmethod

from candles_feed.adapters.base_adapter import BaseAdapter
from candles_feed.adapters.coinbase_advanced_trade.constants import (
    INTERVAL_TO_EXCHANGE_FORMAT,
    INTERVALS,
    WS_INTERVALS,
)
from candles_feed.core.candle_data import CandleData


class CoinbaseAdvancedTradeAdapter(BaseAdapter, ABC):
    """Coinbase Advanced Trade exchange adapter."""

    TIMESTAMP_UNIT: str = "seconds"
    
    @staticmethod
    @abstractmethod
    def get_rest_url() -> str:
        """Get REST API URL for candles.
        
        :returns: REST API URL
        """
        pass
        
    @staticmethod
    @abstractmethod
    def get_ws_url() -> str:
        """Get WebSocket URL.
        
        :returns: WebSocket URL
        """
        pass

    @staticmethod
    def get_trading_pair_format(trading_pair: str) -> str:
        """Convert standard trading pair format to exchange format.

        :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT").
        :returns: Trading pair in Coinbase format (same as standard).
        """
        return trading_pair

    def get_rest_params(
        self,
        trading_pair: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int | None = None,
    ) -> dict:
        """Get parameters for REST API request.

        :param trading_pair: Trading pair.
        :param interval: Candle interval.
        :param start_time: Start time in seconds.
        :param end_time: End time in seconds.
        :param limit: Maximum number of candles to return (not used by Coinbase).
        :returns: Dictionary of parameters for REST API request.
        """
        params = {"granularity": INTERVALS[interval]}

        if start_time is not None:
            params["start"] = self.convert_timestamp_to_exchange(start_time)
        if end_time is not None:
            params["end"] = self.convert_timestamp_to_exchange(end_time)

        return params

    def parse_rest_response(self, data: dict | list | None) -> list[CandleData]:
        """Parse REST API response into CandleData objects.

        :param data: REST API response.
        :returns: List of CandleData objects.
        """
        # Coinbase candle format:
        # {
        #   "candles": [
        #     {
        #       "start": "2022-05-15T16:00:00Z",
        #       "low": "29288.38",
        #       "high": "29477.29",
        #       "open": "29405.34",
        #       "close": "29374.47",
        #       "volume": "142.0450069"
        #     },
        #     ...
        #   ]
        # }

        candles: list[CandleData] = []

        assert isinstance(data, dict), f"Unexpected data type: {type(data)}"

        candles.extend(
            CandleData(
                timestamp_raw=self.ensure_timestamp_in_seconds(candle.get("start", 0)),
                open=float(candle.get("open", 0)),
                high=float(candle.get("high", 0)),
                low=float(candle.get("low", 0)),
                close=float(candle.get("close", 0)),
                volume=float(candle.get("volume", 0)),
            )
            for candle in data.get("candles", [])
        )
        return candles

    def get_ws_subscription_payload(self, trading_pair: str, interval: str) -> dict:
        """Get WebSocket subscription payload.

        :param trading_pair: Trading pair.
        :param interval: Candle interval.
        :returns: WebSocket subscription payload.
        """
        return {
            "type": "subscribe",
            "product_ids": [trading_pair],
            "channel": "candles",
            "granularity": INTERVALS[interval],
        }

    def parse_ws_message(self, data: dict) -> list[CandleData] | None:
        """Parse WebSocket message into CandleData objects.

        :param data: WebSocket message.
        :returns: List of CandleData objects or None if message is not a candle update.
        """
        # Coinbase WS candle format:
        # {
        #   "channel": "candles",
        #   "client_id": "...",
        #   "timestamp": "2023-02-14T17:02:36.346Z",
        #   "sequence_num": 1234,
        #   "events": [
        #     {
        #       "type": "candle",
        #       "candles": [
        #         {
        #           "start": "2023-02-14T17:01:00Z",
        #           "low": "22537.4",
        #           "high": "22540.7",
        #           "open": "22537.4",
        #           "close": "22540.7",
        #           "volume": "0.1360142"
        #         }
        #       ]
        #     }
        #   ]
        # }

        if not isinstance(data, dict) or "events" not in data:
            return None

        ts: int = self.ensure_timestamp_in_seconds(data.get("timestamp", 0))
        candles: list[CandleData] = []
        for event in data["events"]:
            if not isinstance(event, dict) or "candles" not in event:
                continue

            candles.extend(
                CandleData(
                    timestamp_raw=ts,
                    open=float(candle.get("open", 0)),
                    high=float(candle.get("high", 0)),
                    low=float(candle.get("low", 0)),
                    close=float(candle.get("close", 0)),
                    volume=float(candle.get("volume", 0)),
                )
                for candle in event.get("candles", [])
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
