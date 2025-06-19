"""
Notification system for external integrations.

This module provides notification capabilities for various external systems
including Slack, Discord, email, and webhook-based notification services.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import aiohttp

from .protocols import Logger


class NotificationLevel(Enum):
    """Notification severity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationChannel(Enum):
    """Supported notification channels."""

    SLACK = "slack"
    DISCORD = "discord"
    WEBHOOK = "webhook"
    EMAIL = "email"


@dataclass
class NotificationConfig:
    """Configuration for notification system."""

    enabled: bool = True
    default_channel: NotificationChannel = NotificationChannel.SLACK
    rate_limit_per_minute: int = 10
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    timeout_seconds: float = 10.0
    channels: dict[NotificationChannel, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize default channel configurations if not provided."""
        if not self.channels:
            self.channels = {
                NotificationChannel.SLACK: {},
                NotificationChannel.DISCORD: {},
                NotificationChannel.WEBHOOK: {},
                NotificationChannel.EMAIL: {},
            }


@dataclass
class NotificationMessage:
    """A notification message to be sent."""

    title: str
    content: str
    level: NotificationLevel = NotificationLevel.INFO
    channel: NotificationChannel | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    template: str | None = None


class NotificationProvider(ABC):
    """Abstract base class for notification providers."""

    def __init__(self, config: dict[str, Any], logger: Logger | None = None):
        """
        Initialize notification provider.

        :param config: Provider-specific configuration
        :param logger: Logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

    @abstractmethod
    async def send_notification(self, message: NotificationMessage) -> bool:
        """
        Send a notification message.

        :param message: The notification message to send
        :return: True if sent successfully, False otherwise
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate the provider configuration.

        :return: True if configuration is valid, False otherwise
        """
        pass


class SlackNotificationProvider(NotificationProvider):
    """Slack notification provider using webhooks."""

    def validate_config(self) -> bool:
        """Validate Slack configuration."""
        return "webhook_url" in self.config and bool(self.config["webhook_url"])

    async def send_notification(self, message: NotificationMessage) -> bool:
        """Send notification to Slack."""
        if not self.validate_config():
            self.logger.error("Invalid Slack configuration")
            return False

        webhook_url = self.config["webhook_url"]

        # Map notification levels to Slack colors
        color_map = {
            NotificationLevel.DEBUG: "#36a64f",  # Green
            NotificationLevel.INFO: "#2196F3",  # Blue
            NotificationLevel.WARNING: "#ff9800",  # Orange
            NotificationLevel.ERROR: "#f44336",  # Red
            NotificationLevel.CRITICAL: "#9c27b0",  # Purple
        }

        payload = {
            "text": message.title,
            "attachments": [
                {
                    "color": color_map.get(message.level, "#36a64f"),
                    "fields": [
                        {"title": "Level", "value": message.level.value.upper(), "short": True},
                        {"title": "Message", "value": message.content, "short": False},
                    ],
                    "footer": "Hummingbot Candles Feed",
                    "ts": int(asyncio.get_event_loop().time()),
                }
            ],
        }

        # Add metadata fields if present
        if message.metadata:
            for key, value in message.metadata.items():
                payload["attachments"][0]["fields"].append(
                    {"title": key.replace("_", " ").title(), "value": str(value), "short": True}
                )

        try:
            async with aiohttp.ClientSession() as session, session.post(
                webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=10.0)
            ) as response:
                if response.status == 200:
                    self.logger.debug(f"Slack notification sent: {message.title}")
                    return True
                else:
                    self.logger.error(f"Slack notification failed: {response.status}")
                    return False
        except Exception as e:
            self.logger.error(f"Failed to send Slack notification: {e}")
            return False


class DiscordNotificationProvider(NotificationProvider):
    """Discord notification provider using webhooks."""

    def validate_config(self) -> bool:
        """Validate Discord configuration."""
        return "webhook_url" in self.config and bool(self.config["webhook_url"])

    async def send_notification(self, message: NotificationMessage) -> bool:
        """Send notification to Discord."""
        if not self.validate_config():
            self.logger.error("Invalid Discord configuration")
            return False

        webhook_url = self.config["webhook_url"]

        # Map notification levels to Discord colors (as integers)
        color_map = {
            NotificationLevel.DEBUG: 0x36A64F,  # Green
            NotificationLevel.INFO: 0x2196F3,  # Blue
            NotificationLevel.WARNING: 0xFF9800,  # Orange
            NotificationLevel.ERROR: 0xF44336,  # Red
            NotificationLevel.CRITICAL: 0x9C27B0,  # Purple
        }

        embed = {
            "title": message.title,
            "description": message.content,
            "color": color_map.get(message.level, 0x36A64F),
            "fields": [{"name": "Level", "value": message.level.value.upper(), "inline": True}],
            "footer": {"text": "Hummingbot Candles Feed"},
            "timestamp": asyncio.get_event_loop().time(),
        }

        # Add metadata fields if present
        if message.metadata:
            for key, value in message.metadata.items():
                embed["fields"].append(
                    {"name": key.replace("_", " ").title(), "value": str(value), "inline": True}
                )

        payload = {"embeds": [embed]}

        try:
            async with aiohttp.ClientSession() as session, session.post(
                webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=10.0)
            ) as response:
                if response.status == 204:  # Discord returns 204 for success
                    self.logger.debug(f"Discord notification sent: {message.title}")
                    return True
                else:
                    self.logger.error(f"Discord notification failed: {response.status}")
                    return False
        except Exception as e:
            self.logger.error(f"Failed to send Discord notification: {e}")
            return False


class WebhookNotificationProvider(NotificationProvider):
    """Generic webhook notification provider."""

    def validate_config(self) -> bool:
        """Validate webhook configuration."""
        return "url" in self.config and bool(self.config["url"])

    async def send_notification(self, message: NotificationMessage) -> bool:
        """Send notification via webhook."""
        if not self.validate_config():
            self.logger.error("Invalid webhook configuration")
            return False

        url = self.config["url"]
        headers = self.config.get("headers", {})
        auth_token = self.config.get("auth_token")

        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        payload = {
            "title": message.title,
            "content": message.content,
            "level": message.level.value,
            "metadata": message.metadata,
            "timestamp": asyncio.get_event_loop().time(),
        }

        try:
            async with aiohttp.ClientSession() as session, session.post(
                url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10.0)
            ) as response:
                if 200 <= response.status < 300:
                    self.logger.debug(f"Webhook notification sent: {message.title}")
                    return True
                else:
                    self.logger.error(f"Webhook notification failed: {response.status}")
                    return False
        except Exception as e:
            self.logger.error(f"Failed to send webhook notification: {e}")
            return False


class NotificationManager:
    """Manages notification delivery across multiple channels."""

    def __init__(self, config: NotificationConfig | None = None, logger: Logger | None = None):
        """
        Initialize notification manager.

        :param config: Notification configuration
        :param logger: Logger instance
        """
        self.config = config or NotificationConfig()
        self.logger = logger or logging.getLogger(__name__)
        self.providers: dict[NotificationChannel, NotificationProvider] = {}
        self._rate_limit_tracker: dict[NotificationChannel, list[float]] = {}

        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize notification providers based on configuration."""
        provider_classes = {
            NotificationChannel.SLACK: SlackNotificationProvider,
            NotificationChannel.DISCORD: DiscordNotificationProvider,
            NotificationChannel.WEBHOOK: WebhookNotificationProvider,
        }

        for channel, provider_class in provider_classes.items():
            if channel in self.config.channels:
                try:
                    provider = provider_class(self.config.channels[channel], self.logger)
                    if provider.validate_config():
                        self.providers[channel] = provider
                        self.logger.debug(f"Initialized {channel.value} notification provider")
                    else:
                        self.logger.warning(f"Invalid configuration for {channel.value} provider")
                except Exception as e:
                    self.logger.error(f"Failed to initialize {channel.value} provider: {e}")

    def _check_rate_limit(self, channel: NotificationChannel) -> bool:
        """Check if rate limit allows sending notification."""
        if not self.config.enabled:
            return False

        current_time = asyncio.get_event_loop().time()
        if channel not in self._rate_limit_tracker:
            self._rate_limit_tracker[channel] = []

        # Remove timestamps older than 1 minute
        minute_ago = current_time - 60.0
        self._rate_limit_tracker[channel] = [
            timestamp for timestamp in self._rate_limit_tracker[channel] if timestamp > minute_ago
        ]

        # Check if under rate limit
        if len(self._rate_limit_tracker[channel]) >= self.config.rate_limit_per_minute:
            return False

        # Add current timestamp
        self._rate_limit_tracker[channel].append(current_time)
        return True

    async def send_notification(
        self,
        message: NotificationMessage,
        fallback_channels: list[NotificationChannel] | None = None,
    ) -> bool:
        """
        Send a notification message.

        :param message: The notification message to send
        :param fallback_channels: Alternative channels to try if primary fails
        :return: True if sent successfully via any channel, False otherwise
        """
        if not self.config.enabled:
            self.logger.debug("Notifications disabled")
            return False

        # Determine target channel
        target_channel = message.channel or self.config.default_channel
        channels_to_try = [target_channel]

        if fallback_channels:
            channels_to_try.extend(fallback_channels)

        for channel in channels_to_try:
            if channel not in self.providers:
                self.logger.warning(f"No provider available for {channel.value}")
                continue

            if not self._check_rate_limit(channel):
                self.logger.warning(f"Rate limit exceeded for {channel.value}")
                continue

            provider = self.providers[channel]

            # Retry logic
            for attempt in range(self.config.retry_attempts):
                try:
                    success = await provider.send_notification(message)
                    if success:
                        return True

                    if attempt < self.config.retry_attempts - 1:
                        await asyncio.sleep(self.config.retry_delay_seconds * (attempt + 1))

                except Exception as e:
                    self.logger.error(f"Notification attempt {attempt + 1} failed: {e}")
                    if attempt < self.config.retry_attempts - 1:
                        await asyncio.sleep(self.config.retry_delay_seconds * (attempt + 1))

        self.logger.error("Failed to send notification via all available channels")
        return False

    async def send_build_status(
        self,
        status: str,
        branch: str,
        commit_sha: str,
        workflow_name: str,
        details: dict[str, Any] | None = None,
    ) -> bool:
        """
        Send build status notification.

        :param status: Build status (success, failure, started, etc.)
        :param branch: Git branch name
        :param commit_sha: Git commit SHA
        :param workflow_name: Name of the workflow/pipeline
        :param details: Additional build details
        :return: True if sent successfully, False otherwise
        """
        level_map = {
            "success": NotificationLevel.INFO,
            "failure": NotificationLevel.ERROR,
            "error": NotificationLevel.ERROR,
            "started": NotificationLevel.INFO,
            "cancelled": NotificationLevel.WARNING,
        }

        level = level_map.get(status.lower(), NotificationLevel.INFO)

        message = NotificationMessage(
            title=f"Build {status.title()}: {workflow_name}",
            content=f"Branch: {branch}\nCommit: {commit_sha[:8]}",
            level=level,
            metadata={
                "branch": branch,
                "commit": commit_sha,
                "workflow": workflow_name,
                **(details or {}),
            },
        )

        return await self.send_notification(message)

    async def send_alert(
        self,
        title: str,
        message: str,
        level: NotificationLevel = NotificationLevel.WARNING,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Send an alert notification.

        :param title: Alert title
        :param message: Alert message
        :param level: Alert severity level
        :param metadata: Additional alert metadata
        :return: True if sent successfully, False otherwise
        """
        notification = NotificationMessage(
            title=title, content=message, level=level, metadata=metadata or {}
        )

        return await self.send_notification(notification)
