"""Tests for CandlesBaseProtocol definition."""

import numpy as np
import pandas as pd
import pytest


class TestCandlesBaseProtocol:
    """Verify the protocol defines the correct interface."""

    def test_protocol_is_importable(self):
        from candles_feed.hb_compat.protocols import CandlesBaseProtocol
        assert CandlesBaseProtocol is not None

    def test_protocol_is_runtime_checkable(self):
        from candles_feed.hb_compat.protocols import CandlesBaseProtocol

        class FakeCandles:
            name = "test"
            interval = "1m"
            max_records = 500
            ready = True
            interval_in_seconds = 60

            @property
            def candles_df(self) -> pd.DataFrame:
                return pd.DataFrame()

            def start(self) -> None: ...
            def stop(self) -> None: ...

            async def fetch_candles(self, start_time=None, end_time=None, limit=None) -> np.ndarray:
                return np.array([])

            async def get_historical_candles(self, config) -> pd.DataFrame:
                return pd.DataFrame()

            def get_exchange_trading_pair(self, trading_pair: str) -> str:
                return trading_pair

        assert isinstance(FakeCandles(), CandlesBaseProtocol)

    def test_non_conforming_class_fails(self):
        from candles_feed.hb_compat.protocols import CandlesBaseProtocol

        class NotCandles:
            pass

        assert not isinstance(NotCandles(), CandlesBaseProtocol)
