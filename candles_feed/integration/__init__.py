"""
Integration package for external tools and services.

This package provides integration capabilities with various external tools
and services including monitoring systems, notification services, and
project management tools.
"""

# Import Hummingbot integration from parent module
try:
    import os
    import sys

    # Add parent directory to path to import from integration.py
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from integration import HUMMINGBOT_AVAILABLE, create_candles_feed_with_hummingbot

    sys.path.pop(0)
except ImportError:
    # Fallback: read from sibling integration.py directly
    import importlib.util
    import os

    integration_py_path = os.path.join(os.path.dirname(__file__), "..", "integration.py")
    spec = importlib.util.spec_from_file_location("hummingbot_integration", integration_py_path)
    hummingbot_integration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hummingbot_integration)
    create_candles_feed_with_hummingbot = hummingbot_integration.create_candles_feed_with_hummingbot
    HUMMINGBOT_AVAILABLE = hummingbot_integration.HUMMINGBOT_AVAILABLE

from .monitoring import (
    ExternalMonitoringIntegration,
    HealthCheckServer,
    PrometheusMetricsExporter,
)
from .notifications import NotificationIntegration
from .project_management import ProjectManagementIntegration

__all__ = [
    # Hummingbot integration
    "create_candles_feed_with_hummingbot",
    "HUMMINGBOT_AVAILABLE",
    # External tool integrations
    "ExternalMonitoringIntegration",
    "PrometheusMetricsExporter",
    "HealthCheckServer",
    "NotificationIntegration",
    "ProjectManagementIntegration",
]
