"""Behavioural tests for candles_feed.core.notifications."""

import logging
from typing import Any

import pytest

from candles_feed.core import notifications as notif
from candles_feed.core.notifications import (
    DiscordNotificationProvider,
    NotificationChannel,
    NotificationConfig,
    NotificationLevel,
    NotificationManager,
    NotificationMessage,
    NotificationProvider,
    SlackNotificationProvider,
    WebhookNotificationProvider,
)


class FakeResponse:
    def __init__(self, status: int):
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeSession:
    """Stand-in for aiohttp.ClientSession recording post calls."""

    status = 200
    error: Exception | None = None
    calls: list[tuple[str, dict[str, Any]]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def post(self, url, **kwargs):
        type(self).calls.append((url, kwargs))
        if type(self).error is not None:
            raise type(self).error
        return FakeResponse(type(self).status)


@pytest.fixture
def session(monkeypatch):
    class Session(FakeSession):
        calls: list[tuple[str, dict[str, Any]]] = []
        status = 200
        error = None

    monkeypatch.setattr(notif.aiohttp, "ClientSession", Session)
    return Session


@pytest.fixture
def logger(mocker):
    return mocker.MagicMock()


@pytest.fixture
def no_sleep(mocker):
    return mocker.patch("candles_feed.core.notifications.asyncio.sleep", new=mocker.AsyncMock())


def msg(**kw) -> NotificationMessage:
    return NotificationMessage(title="T", content="C", **kw)


class TestConfig:
    def test_default_channels_populated(self):
        cfg = NotificationConfig()
        assert set(cfg.channels) == set(NotificationChannel)

    def test_explicit_channels_kept(self):
        chans = {NotificationChannel.SLACK: {"webhook_url": "x"}}
        assert NotificationConfig(channels=chans).channels == chans

    def test_message_defaults(self):
        m = msg()
        assert m.level is NotificationLevel.INFO
        assert m.channel is None and m.metadata == {} and m.template is None


class TestProviderBase:
    def test_default_logger(self):
        p = SlackNotificationProvider({})
        assert isinstance(p.logger, logging.Logger)

    def test_abstract(self):
        with pytest.raises(TypeError):
            NotificationProvider({})  # type: ignore[abstract]


class TestSlack:
    @pytest.mark.parametrize(
        "cfg,ok", [({}, False), ({"webhook_url": ""}, False), ({"webhook_url": "u"}, True)]
    )
    def test_validate(self, cfg, ok):
        assert SlackNotificationProvider(cfg).validate_config() is ok

    async def test_invalid_config(self, logger, session):
        assert await SlackNotificationProvider({}, logger).send_notification(msg()) is False
        logger.error.assert_called_once_with("Invalid Slack configuration")
        assert session.calls == []

    async def test_success_payload(self, logger, session):
        p = SlackNotificationProvider({"webhook_url": "http://s"}, logger)
        m = msg(level=NotificationLevel.ERROR, metadata={"build_id": 7})
        assert await p.send_notification(m) is True
        url, kw = session.calls[0]
        assert url == "http://s"
        att = kw["json"]["attachments"][0]
        assert kw["json"]["text"] == "T"
        assert att["color"] == "#f44336"
        assert {"title": "Build Id", "value": "7", "short": True} in att["fields"]
        assert att["fields"][0]["value"] == "ERROR"

    async def test_no_metadata_fields(self, logger, session):
        p = SlackNotificationProvider({"webhook_url": "u"}, logger)
        await p.send_notification(msg())
        assert len(session.calls[0][1]["json"]["attachments"][0]["fields"]) == 2

    async def test_bad_status(self, logger, session):
        session.status = 500
        p = SlackNotificationProvider({"webhook_url": "u"}, logger)
        assert await p.send_notification(msg()) is False
        logger.error.assert_called_once_with("Slack notification failed: 500")

    async def test_exception(self, logger, session):
        session.error = RuntimeError("boom")
        p = SlackNotificationProvider({"webhook_url": "u"}, logger)
        assert await p.send_notification(msg()) is False
        assert "boom" in logger.error.call_args[0][0]


class TestDiscord:
    @pytest.mark.parametrize(
        "cfg,ok", [({}, False), ({"webhook_url": ""}, False), ({"webhook_url": "u"}, True)]
    )
    def test_validate(self, cfg, ok):
        assert DiscordNotificationProvider(cfg).validate_config() is ok

    async def test_invalid_config(self, logger, session):
        assert await DiscordNotificationProvider({}, logger).send_notification(msg()) is False
        logger.error.assert_called_once_with("Invalid Discord configuration")

    async def test_success_payload(self, logger, session):
        session.status = 204
        p = DiscordNotificationProvider({"webhook_url": "http://d"}, logger)
        m = msg(level=NotificationLevel.CRITICAL, metadata={"some_key": "v"})
        assert await p.send_notification(m) is True
        embed = session.calls[0][1]["json"]["embeds"][0]
        assert embed["title"] == "T" and embed["description"] == "C"
        assert embed["color"] == 0x9C27B0
        assert {"name": "Some Key", "value": "v", "inline": True} in embed["fields"]

    async def test_no_metadata(self, logger, session):
        session.status = 204
        p = DiscordNotificationProvider({"webhook_url": "u"}, logger)
        await p.send_notification(msg())
        assert len(session.calls[0][1]["json"]["embeds"][0]["fields"]) == 1

    async def test_bad_status(self, logger, session):
        session.status = 200
        p = DiscordNotificationProvider({"webhook_url": "u"}, logger)
        assert await p.send_notification(msg()) is False
        logger.error.assert_called_once_with("Discord notification failed: 200")

    async def test_exception(self, logger, session):
        session.error = ValueError("bad")
        p = DiscordNotificationProvider({"webhook_url": "u"}, logger)
        assert await p.send_notification(msg()) is False
        assert "bad" in logger.error.call_args[0][0]


class TestWebhook:
    @pytest.mark.parametrize("cfg,ok", [({}, False), ({"url": ""}, False), ({"url": "u"}, True)])
    def test_validate(self, cfg, ok):
        assert WebhookNotificationProvider(cfg).validate_config() is ok

    async def test_invalid_config(self, logger, session):
        assert await WebhookNotificationProvider({}, logger).send_notification(msg()) is False
        logger.error.assert_called_once_with("Invalid webhook configuration")

    async def test_success_with_auth(self, logger, session):
        session.status = 201
        p = WebhookNotificationProvider(
            {"url": "http://w", "auth_token": "tok", "headers": {"X": "1"}}, logger
        )
        assert await p.send_notification(msg(metadata={"a": 1})) is True
        url, kw = session.calls[0]
        assert url == "http://w"
        assert kw["headers"] == {"X": "1", "Authorization": "Bearer tok"}
        assert kw["json"]["level"] == "info" and kw["json"]["metadata"] == {"a": 1}

    async def test_success_without_auth(self, logger, session):
        p = WebhookNotificationProvider({"url": "u"}, logger)
        assert await p.send_notification(msg()) is True
        assert session.calls[0][1]["headers"] == {}

    async def test_bad_status(self, logger, session):
        session.status = 404
        p = WebhookNotificationProvider({"url": "u"}, logger)
        assert await p.send_notification(msg()) is False
        logger.error.assert_called_once_with("Webhook notification failed: 404")

    async def test_exception(self, logger, session):
        session.error = OSError("net")
        p = WebhookNotificationProvider({"url": "u"}, logger)
        assert await p.send_notification(msg()) is False
        assert "net" in logger.error.call_args[0][0]


def make_manager(logger, **kw) -> NotificationManager:
    channels = {
        NotificationChannel.SLACK: {"webhook_url": "s"},
        NotificationChannel.DISCORD: {"webhook_url": "d"},
        NotificationChannel.WEBHOOK: {"url": "w"},
    }
    return NotificationManager(NotificationConfig(channels=channels, **kw), logger)


class TestManagerInit:
    def test_default_config_has_no_valid_providers(self, logger):
        m = NotificationManager(logger=logger)
        assert m.providers == {}
        assert logger.warning.call_count == 3

    def test_default_logger(self):
        assert isinstance(NotificationManager().logger, logging.Logger)

    def test_valid_providers(self, logger):
        m = make_manager(logger)
        assert set(m.providers) == {
            NotificationChannel.SLACK,
            NotificationChannel.DISCORD,
            NotificationChannel.WEBHOOK,
        }

    def test_missing_channel_skipped(self, logger):
        cfg = NotificationConfig(channels={NotificationChannel.EMAIL: {}})
        m = NotificationManager(cfg, logger)
        assert m.providers == {}
        logger.warning.assert_not_called()

    def test_provider_init_exception(self, logger, mocker):
        mocker.patch.object(SlackNotificationProvider, "validate_config", side_effect=KeyError("k"))
        m = make_manager(logger)
        assert NotificationChannel.SLACK not in m.providers
        assert any("Failed to initialize slack" in c[0][0] for c in logger.error.call_args_list)


class TestRateLimit:
    def test_disabled(self, logger):
        assert (
            make_manager(logger, enabled=False)._check_rate_limit(NotificationChannel.SLACK)
            is False
        )

    def test_limit_enforced(self, logger):
        m = make_manager(logger, rate_limit_per_minute=2)
        ch = NotificationChannel.SLACK
        assert [m._check_rate_limit(ch) for _ in range(3)] == [True, True, False]

    def test_old_timestamps_expire(self, logger, mocker):
        m = make_manager(logger, rate_limit_per_minute=1)
        ch = NotificationChannel.SLACK
        mocker.patch("candles_feed.core.notifications.time.time", return_value=1000.0)
        assert m._check_rate_limit(ch) is True
        assert m._check_rate_limit(ch) is False
        mocker.patch("candles_feed.core.notifications.time.time", return_value=1061.0)
        assert m._check_rate_limit(ch) is True


class StubProvider:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    async def send_notification(self, message):
        self.calls += 1
        r = self.results.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


class TestSend:
    async def test_disabled(self, logger):
        m = make_manager(logger, enabled=False)
        assert await m.send_notification(msg()) is False
        logger.debug.assert_called_with("Notifications disabled")

    async def test_success_default_channel(self, logger):
        m = make_manager(logger)
        stub = StubProvider([True])
        m.providers[NotificationChannel.SLACK] = stub  # type: ignore[assignment]
        assert await m.send_notification(msg()) is True
        assert stub.calls == 1

    async def test_message_channel_overrides_default(self, logger):
        m = make_manager(logger)
        slack, disc = StubProvider([True]), StubProvider([True])
        m.providers[NotificationChannel.SLACK] = slack  # type: ignore[assignment]
        m.providers[NotificationChannel.DISCORD] = disc  # type: ignore[assignment]
        assert await m.send_notification(msg(channel=NotificationChannel.DISCORD)) is True
        assert (slack.calls, disc.calls) == (0, 1)

    async def test_missing_provider_no_fallback(self, logger):
        m = make_manager(logger)
        assert await m.send_notification(msg(channel=NotificationChannel.EMAIL)) is False
        logger.warning.assert_any_call("No provider available for email")
        logger.error.assert_called_with("Failed to send notification via all available channels")

    async def test_rate_limited_then_fallback(self, logger):
        m = make_manager(logger, rate_limit_per_minute=1)
        slack, disc = StubProvider([True]), StubProvider([True])
        m.providers[NotificationChannel.SLACK] = slack  # type: ignore[assignment]
        m.providers[NotificationChannel.DISCORD] = disc  # type: ignore[assignment]
        m._check_rate_limit(NotificationChannel.SLACK)
        ok = await m.send_notification(msg(), fallback_channels=[NotificationChannel.DISCORD])
        assert ok is True
        assert (slack.calls, disc.calls) == (0, 1)
        logger.warning.assert_any_call("Rate limit exceeded for slack")

    async def test_retry_until_success(self, logger, no_sleep):
        m = make_manager(logger, retry_delay_seconds=2.0)
        stub = StubProvider([False, RuntimeError("x"), True])
        m.providers[NotificationChannel.SLACK] = stub  # type: ignore[assignment]
        assert await m.send_notification(msg()) is True
        assert stub.calls == 3
        assert [c[0][0] for c in no_sleep.call_args_list] == [2.0, 4.0]

    async def test_all_attempts_fail(self, logger, no_sleep):
        m = make_manager(logger, retry_attempts=2)
        stub = StubProvider([False, RuntimeError("last")])
        m.providers[NotificationChannel.SLACK] = stub  # type: ignore[assignment]
        assert await m.send_notification(msg()) is False
        assert stub.calls == 2
        assert no_sleep.await_count == 1
        logger.error.assert_any_call("Notification attempt 2 failed: last")


class TestConvenience:
    @pytest.mark.parametrize(
        "status,level",
        [
            ("success", NotificationLevel.INFO),
            ("FAILURE", NotificationLevel.ERROR),
            ("cancelled", NotificationLevel.WARNING),
            ("weird", NotificationLevel.INFO),
        ],
    )
    async def test_build_status(self, logger, mocker, status, level):
        m = make_manager(logger)
        send = mocker.patch.object(m, "send_notification", new=mocker.AsyncMock(return_value=True))
        assert await m.send_build_status(status, "main", "abcdef123456", "CI", {"k": 1}) is True
        sent = send.call_args[0][0]
        assert sent.level is level
        assert sent.title == f"Build {status.title()}: CI"
        assert sent.content == "Branch: main\nCommit: abcdef12"
        assert sent.metadata == {
            "branch": "main",
            "commit": "abcdef123456",
            "workflow": "CI",
            "k": 1,
        }

    async def test_build_status_no_details(self, logger, mocker):
        m = make_manager(logger)
        send = mocker.patch.object(m, "send_notification", new=mocker.AsyncMock(return_value=False))
        assert await m.send_build_status("started", "b", "12345678", "w") is False
        assert set(send.call_args[0][0].metadata) == {"branch", "commit", "workflow"}

    async def test_send_alert(self, logger, mocker):
        m = make_manager(logger)
        send = mocker.patch.object(m, "send_notification", new=mocker.AsyncMock(return_value=True))
        assert await m.send_alert("A", "body", NotificationLevel.CRITICAL, {"x": 1}) is True
        sent = send.call_args[0][0]
        assert (sent.title, sent.content, sent.level) == ("A", "body", NotificationLevel.CRITICAL)
        assert sent.metadata == {"x": 1}

    async def test_send_alert_defaults(self, logger, mocker):
        m = make_manager(logger)
        send = mocker.patch.object(m, "send_notification", new=mocker.AsyncMock(return_value=True))
        await m.send_alert("A", "b")
        sent = send.call_args[0][0]
        assert sent.level is NotificationLevel.WARNING and sent.metadata == {}
