"""Default-env tests for the hummingbot network client adapters (fakes, no network)."""

import enum
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from candles_feed.core.network_client import NetworkClient
from candles_feed.core.rate_limiter import RateLimitExceededError
from candles_feed.hb_compat import hummingbot_network_client_adapter as adapter_module
from candles_feed.hb_compat.hummingbot_network_client_adapter import (
    HummingbotNetworkClient,
    HummingbotThrottlerAdapter,
    HummingbotWSAssistantAdapter,
    NetworkClientFactory,
)


@pytest.fixture(autouse=True)
def mock_network_client_factory():
    """Override the package conftest: these tests exercise the real factory."""
    return


class FakeResponse:
    def __init__(self, status=200, payload=None, headers=None, body="boom"):
        self.status = status
        self.headers = headers or {}
        self._payload = payload if payload is not None else {"ok": True}
        self._body = body

    async def json(self):
        return self._payload

    async def text(self):
        return self._body


class FakeRestAssistant:
    def __init__(self, response):
        self.response = response
        self.requests = []

    async def call(self, request):
        self.requests.append(request)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class FakeWS:
    def __init__(self, messages=(), error=None):
        self.messages = list(messages)
        self.error = error
        self.sent = []
        self.connected_to = None
        self.disconnected = False

    async def connect(self, ws_url):
        self.connected_to = ws_url

    async def disconnect(self):
        self.disconnected = True

    async def send(self, payload):
        self.sent.append(payload)

    async def iter_messages(self):
        for message in self.messages:
            yield message
        if self.error:
            raise self.error


class FakeFactory:
    def __init__(self, rest=None, ws=None, with_close=True):
        self.rest = rest
        self.ws = ws
        self.rest_calls = 0
        self.closed = False
        if with_close:
            self.close = self._close

    async def get_rest_assistant(self):
        self.rest_calls += 1
        return self.rest

    async def get_ws_assistant(self):
        return self.ws

    async def _close(self):
        self.closed = True


class RESTMethod(enum.Enum):
    GET = "GET"
    POST = "POST"


class RESTRequest:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


@pytest.fixture
def available(monkeypatch):
    monkeypatch.setattr(adapter_module, "HUMMINGBOT_AVAILABLE", True)


@pytest.fixture
def stack(monkeypatch):
    """Provide ``connections.data_types`` the way hummingbot would."""

    def fake_import(area, module):
        assert (area, module) == ("web", "connections.data_types")
        return SimpleNamespace(RESTMethod=RESTMethod, RESTRequest=RESTRequest)

    monkeypatch.setattr(adapter_module, "import_web_stack", fake_import)


@pytest.fixture
def no_stack(monkeypatch):
    def missing(area, module):
        raise ImportError("no web stack")

    monkeypatch.setattr(adapter_module, "import_web_stack", missing)


def make_client(response=None, logger=None, *, with_close=True):
    rest = FakeRestAssistant(response or FakeResponse())
    factory = FakeFactory(rest=rest, ws=FakeWS(), with_close=with_close)
    return HummingbotNetworkClient(Mock(), factory, logger or Mock()), rest, factory


# ---- WS assistant adapter ---------------------------------------------------------------


async def test_ws_adapter_connect_is_noop_and_disconnect_delegates():
    ws = FakeWS()
    ws_adapter = HummingbotWSAssistantAdapter(ws)
    await ws_adapter.connect()
    assert not ws.disconnected
    await ws_adapter.disconnect()
    assert ws.disconnected


async def test_ws_adapter_disconnect_tolerates_assistant_without_disconnect():
    await HummingbotWSAssistantAdapter(object()).disconnect()


async def test_ws_adapter_send_serialises_dicts_only():
    ws = FakeWS()
    ws_adapter = HummingbotWSAssistantAdapter(ws)
    await ws_adapter.send({"op": "subscribe"})
    await ws_adapter.send("raw-text")
    assert ws.sent == ['{"op": "subscribe"}', "raw-text"]


async def test_ws_adapter_iter_messages_decodes_and_skips_empty_and_invalid():
    messages = [
        SimpleNamespace(data='{"a": 1}'),
        SimpleNamespace(data={"b": 2}),
        SimpleNamespace(data=""),
        SimpleNamespace(data="{not json"),
        SimpleNamespace(data=None),
    ]
    logger = Mock()
    ws_adapter = HummingbotWSAssistantAdapter(FakeWS(messages), logger)

    received = [message async for message in ws_adapter.iter_messages()]

    assert received == [{"a": 1}, {"b": 2}]
    logger.error.assert_called_once()
    assert "{not json" in logger.error.call_args.args[0]


async def test_ws_adapter_iter_messages_passes_empty_dict_ping():
    ws_adapter = HummingbotWSAssistantAdapter(
        FakeWS([SimpleNamespace(data={}), SimpleNamespace(data="{}")]), Mock()
    )
    assert [m async for m in ws_adapter.iter_messages()] == [{}, {}]


async def test_ws_adapter_iter_messages_skips_falsy_non_dict_payloads():
    messages = [SimpleNamespace(data=data) for data in ([], 0, False, {}, {"a": 1}, [1])]
    ws_adapter = HummingbotWSAssistantAdapter(FakeWS(messages), Mock())
    assert [m async for m in ws_adapter.iter_messages()] == [{}, {"a": 1}, [1]]


async def test_ws_adapter_iter_messages_splits_batched_str_frame():
    logger = Mock()
    ws_adapter = HummingbotWSAssistantAdapter(
        FakeWS([SimpleNamespace(data='{"a": 1}\n{}\nbad\n{"b": 2}')]), logger
    )
    assert [m async for m in ws_adapter.iter_messages()] == [{"a": 1}, {}, {"b": 2}]
    logger.error.assert_called_once()


async def test_ws_adapter_iter_messages_logs_and_reraises_stream_errors():
    logger = Mock()
    ws_adapter = HummingbotWSAssistantAdapter(FakeWS(error=RuntimeError("socket died")), logger)

    with pytest.raises(RuntimeError, match="socket died"):
        async for _ in ws_adapter.iter_messages():
            pass

    assert "socket died" in logger.error.call_args.args[0]


async def test_ws_adapter_is_async_iterable():
    ws_adapter = HummingbotWSAssistantAdapter(FakeWS([SimpleNamespace(data='{"x": 1}')]))
    assert [m async for m in ws_adapter] == [{"x": 1}]


def test_ws_adapter_defaults_to_module_logger():
    assert HummingbotWSAssistantAdapter(FakeWS())._logger.name == adapter_module.__name__


# ---- throttler adapter ------------------------------------------------------------------


def test_throttler_adapter_passes_limit_id_by_keyword():
    throttler = Mock()
    result = HummingbotThrottlerAdapter(throttler).execute_task("klines")
    throttler.execute_task.assert_called_once_with(limit_id="klines")
    assert result is throttler.execute_task.return_value


# ---- network client ---------------------------------------------------------------------


def test_client_requires_hummingbot_components(monkeypatch):
    monkeypatch.setattr(adapter_module, "HUMMINGBOT_AVAILABLE", False)
    with pytest.raises(ImportError, match="not available"):
        HummingbotNetworkClient(Mock(), Mock())


def test_client_defaults_to_module_logger(available):
    client = HummingbotNetworkClient(Mock(), Mock())
    assert client._logger.name == adapter_module.__name__


async def test_rest_assistant_is_fetched_once(available):
    client, _, factory = make_client()
    await client._ensure_rest_assistant()
    await client._ensure_rest_assistant()
    assert factory.rest_calls == 1


async def test_get_rest_data_builds_request_and_returns_json(available, stack):
    client, rest, _ = make_client(FakeResponse(payload=[1, 2, 3]))

    result = await client.get_rest_data(
        "https://x.test/k",
        params={"a": 1, "skip": None},
        data={"b": 2, "skip": None},
        headers={"h": "v"},
        method="post",
    )

    assert result == [1, 2, 3]
    (request,) = rest.requests
    assert request.kwargs["method"] is RESTMethod.POST
    assert request.kwargs["url"] == "https://x.test/k"
    assert request.kwargs["params"] == {"a": 1}
    assert json.loads(request.kwargs["data"]) == {"b": 2}
    assert request.kwargs["headers"] == {"h": "v"}


async def test_get_rest_data_without_params_or_body(available, stack):
    client, rest, _ = make_client()
    await client.get_rest_data("https://x.test/k")
    kwargs = rest.requests[0].kwargs
    assert kwargs["method"] is RESTMethod.GET
    assert kwargs["params"] is None
    assert kwargs["data"] is None


async def test_get_rest_data_empty_body_after_cleaning_is_none(available, stack):
    client, rest, _ = make_client()
    await client.get_rest_data("https://x.test/k", data={"only": None})
    assert rest.requests[0].kwargs["data"] is None


@pytest.mark.parametrize("status", [429, 418])
async def test_get_rest_data_rate_limit_status_raises_and_logs(available, stack, status):
    logger = Mock()
    client, _, _ = make_client(FakeResponse(status=status, headers={"Retry-After": "3"}), logger)

    with pytest.raises(RateLimitExceededError):
        await client.get_rest_data("https://x.test/k")

    assert "https://x.test/k" in logger.error.call_args.args[0]


async def test_get_rest_data_http_error_raises_oserror_with_body(available, stack):
    client, _, _ = make_client(FakeResponse(status=500, body="server exploded"))

    with pytest.raises(OSError, match="HTTP status is 500.*server exploded"):
        await client.get_rest_data("https://x.test/k", method="GET")


async def test_get_rest_data_propagates_assistant_errors(available, stack):
    logger = Mock()
    client, _, _ = make_client(ConnectionError("down"), logger)

    with pytest.raises(ConnectionError):
        await client.get_rest_data("https://x.test/k")

    assert "down" in logger.error.call_args.args[0]


async def test_build_request_falls_back_to_factory_request_class(available, no_stack):
    client, rest, factory = make_client()
    factory.rest_request_class = RESTRequest

    await client.get_rest_data("https://x.test/k", params={"a": 1}, method="get")

    kwargs = rest.requests[0].kwargs
    assert kwargs["method"] == "GET"
    assert kwargs["params"] == {"a": 1}


async def test_build_request_without_any_request_class_raises_import_error(available, no_stack):
    client, _, _ = make_client()
    with pytest.raises(ImportError, match="no web stack"):
        await client.get_rest_data("https://x.test/k")


async def test_establish_ws_connection_connects_and_wraps(available):
    client, _, factory = make_client()
    ws_adapter = await client.establish_ws_connection("wss://x.test/ws")
    assert factory.ws.connected_to == "wss://x.test/ws"
    assert isinstance(ws_adapter, HummingbotWSAssistantAdapter)
    await client.send_ws_message(ws_adapter, {"op": "ping"})
    assert factory.ws.sent == ['{"op": "ping"}']


async def test_establish_ws_connection_failure_is_logged_and_raised(available):
    logger = Mock()
    client, _, factory = make_client(logger=logger)

    async def broken(ws_url):
        raise TimeoutError("handshake")

    factory.ws.connect = broken
    with pytest.raises(TimeoutError):
        await client.establish_ws_connection("wss://x.test/ws")
    assert "wss://x.test/ws" in logger.error.call_args.args[0]


async def test_close_delegates_only_when_factory_can_close(available):
    client, _, factory = make_client()
    await client.close()
    assert factory.closed

    quiet, _, quiet_factory = make_client(with_close=False)
    await quiet.close()
    assert not quiet_factory.closed


async def test_context_manager_prepares_rest_assistant_and_closes(available):
    client, _, factory = make_client()
    async with client as entered:
        assert entered is client
        assert factory.rest_calls == 1
    assert factory.closed


# ---- NetworkClientFactory ---------------------------------------------------------------


def test_factory_without_components_falls_back_to_standalone_client():
    assert isinstance(NetworkClientFactory.create_client(), NetworkClient)
    assert isinstance(NetworkClientFactory.create_client({}), NetworkClient)


@pytest.mark.parametrize("missing", ["throttler", "web_assistants_factory"])
def test_factory_with_partial_components_falls_back(available, missing):
    components = {"throttler": Mock(), "web_assistants_factory": Mock()}
    del components[missing]
    assert isinstance(NetworkClientFactory.create_client(components), NetworkClient)


def test_factory_uses_hummingbot_client_when_available(available):
    throttler, web_factory, logger = Mock(), Mock(), Mock()
    client = NetworkClientFactory.create_client(
        {"throttler": throttler, "web_assistants_factory": web_factory}, logger
    )
    assert isinstance(client, HummingbotNetworkClient)
    assert client._throttler is throttler
    assert client._web_assistants_factory is web_factory
    assert client._logger is logger


def test_factory_falls_back_when_hummingbot_unavailable(monkeypatch):
    monkeypatch.setattr(adapter_module, "HUMMINGBOT_AVAILABLE", False)
    components = {"throttler": Mock(), "web_assistants_factory": Mock()}
    assert isinstance(NetworkClientFactory.create_client(components), NetworkClient)


@pytest.mark.parametrize("error", [ImportError("gone"), TypeError("bad args")])
def test_factory_warns_and_falls_back_when_client_construction_fails(available, monkeypatch, error):
    def explode(**kwargs):
        raise error

    monkeypatch.setattr(adapter_module, "HummingbotNetworkClient", explode)
    logger = Mock()
    components = {"throttler": Mock(), "web_assistants_factory": Mock()}

    client = NetworkClientFactory.create_client(components, logger)

    assert isinstance(client, NetworkClient)
    assert str(error) in logger.warning.call_args.args[0]


def test_factory_construction_failure_without_logger_still_falls_back(available, monkeypatch):
    def explode(**kwargs):
        raise TypeError("bad args")

    monkeypatch.setattr(adapter_module, "HummingbotNetworkClient", explode)
    components = {"throttler": Mock(), "web_assistants_factory": Mock()}
    assert isinstance(NetworkClientFactory.create_client(components), NetworkClient)
