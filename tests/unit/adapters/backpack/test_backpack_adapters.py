"""Tests for the pieces shared by the Backpack spot and perpetual adapters."""

import pytest

from candles_feed.adapters.backpack.base_adapter import BackpackBaseAdapter
from candles_feed.adapters.backpack.constants import INTERVAL_TO_EXCHANGE_FORMAT, INTERVALS

T0 = 1704067200  # 2024-01-01T00:00:00Z


class TestBackpackConstants:
    def test_monthly_interval_uses_exchange_code(self):
        assert INTERVAL_TO_EXCHANGE_FORMAT["1M"] == "1month"
        assert INTERVAL_TO_EXCHANGE_FORMAT["1m"] == "1m"
        assert set(INTERVAL_TO_EXCHANGE_FORMAT) == set(INTERVALS)


class TestBackpackTimestamps:
    @pytest.mark.parametrize(
        "text",
        [
            "2024-01-01T00:00:00",
            "2024-01-01 00:00:00",
            "2024-01-01T00:00:00Z",
            "2024-01-01T00:00:00+00:00",
            "2023-12-31T19:00:00-05:00",
        ],
    )
    def test_iso_to_seconds(self, text):
        assert BackpackBaseAdapter._iso_to_seconds(text) == T0
