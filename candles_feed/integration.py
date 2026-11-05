"""
Integration helpers for using CandlesFeed with Hummingbot.

This module provides functions and utilities to simplify the integration
of CandlesFeed with Hummingbot or other frameworks.
"""

import importlib.util
from typing import Any

from candles_feed.core.candles_feed import CandlesFeed
from candles_feed.core.protocols import Logger

# Detect Hummingbot availability WITHOUT importing it. This module ships as part
# of the candles_feed package and must honor the import boundary that only the
# hb_compat layer may import hummingbot. The throttler / web-assistants-factory
# objects are supplied by the caller and validated by class name below, so the
# hummingbot types are never needed here.
try:
    HUMMINGBOT_AVAILABLE = (
        importlib.util.find_spec("hummingbot.core.api_throttler.async_throttler_base") is not None
        and importlib.util.find_spec("hummingbot.core.web_assistant.web_assistants_factory")
        is not None
    )
except (ImportError, ValueError):
    HUMMINGBOT_AVAILABLE = False


def create_candles_feed_with_hummingbot(
    exchange: str,
    trading_pair: str,
    interval: str = "1m",
    max_records: int = 150,
    throttler: Any | None = None,  # Type as Any to avoid direct dependency
    web_assistants_factory: Any | None = None,  # Type as Any to avoid direct dependency
    logger: Logger | None = None,
) -> CandlesFeed:
    """
    Create a CandlesFeed instance using Hummingbot components.

    This helper function creates a CandlesFeed that uses Hummingbot's networking
    components when available.

    :param exchange: Exchange identifier
    :param trading_pair: Trading pair in standard format (e.g., "BTC-USDT")
    :param interval: Candle interval (e.g., "1m", "5m", "1h")
    :param max_records: Maximum number of candles to store
    :param throttler: Hummingbot AsyncThrottler instance
    :param web_assistants_factory: Hummingbot WebAssistantsFactory instance
    :param logger: Logger instance
    :raises ImportError: If Hummingbot dependencies are not available
    :raises ValueError: If throttler or web_assistants_factory are not provided
    :raises TypeError: If throttler or web_assistants_factory are of incorrect type
    :return: CandlesFeed instance configured to use Hummingbot components
    """
    # Dynamically check HUMMINGBOT_AVAILABLE to allow patching in tests
    import sys

    if not getattr(sys.modules[__name__], "HUMMINGBOT_AVAILABLE", False):
        raise ImportError(
            "Hummingbot dependencies not available. Please install them or use "
            "the standard CandlesFeed constructor for standalone operation."
        )

    if throttler is None or web_assistants_factory is None:
        raise ValueError(
            "Both throttler and web_assistants_factory must be provided to "
            "create a CandlesFeed with Hummingbot components."
        )

    # Validate types - use string comparison to avoid direct dependencies
    # This allows tests to run with mocks when Hummingbot is not available
    throttler_cls_name = throttler.__class__.__name__
    web_assistants_factory_cls_name = web_assistants_factory.__class__.__name__

    # Check class name instead of isinstance to avoid import errors
    if not (
        throttler_cls_name.endswith("AsyncThrottler")
        or throttler_cls_name.endswith("AsyncThrottlerBase")
    ):
        raise TypeError(
            f"throttler must be an instance of AsyncThrottlerBase, got {throttler_cls_name}"
        )

    if not web_assistants_factory_cls_name.endswith("WebAssistantsFactory"):
        raise TypeError(
            f"web_assistants_factory must be an instance of WebAssistantsFactory, got {web_assistants_factory_cls_name}"
        )

    hummingbot_components = {
        "throttler": throttler,
        "web_assistants_factory": web_assistants_factory,
    }

    return CandlesFeed(
        exchange=exchange,
        trading_pair=trading_pair,
        interval=interval,
        max_records=max_records,
        logger=logger,
        hummingbot_components=hummingbot_components,
    )
