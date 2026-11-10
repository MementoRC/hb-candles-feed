"""Tests for SimpleWSAssistant.iter_messages frame decoding."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import aiohttp

from candles_feed.core.network_client import SimpleWSAssistant


class _FakeWS:
    def __init__(self, frames):
        self._frames = frames

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for frame in self._frames:
            yield SimpleNamespace(type=aiohttp.WSMsgType.TEXT, data=frame)


async def _collect(frames):
    assistant = SimpleWSAssistant(_FakeWS(frames), MagicMock())
    return [m async for m in assistant.iter_messages()], assistant._logger


async def test_single_json_frame_unchanged():
    messages, _ = await _collect(['{"a": 1}', "{}"])
    assert messages == [{"a": 1}, {}]


async def test_newline_delimited_frame_yields_each_object():
    messages, _ = await _collect(['{"a": 1}\n{"b": 2}\n'])
    assert messages == [{"a": 1}, {"b": 2}]


async def test_batched_frame_skips_bad_lines_and_logs():
    messages, logger = await _collect(['{"a": 1}\nnot-json\n\n{"b": 2}'])
    assert messages == [{"a": 1}, {"b": 2}]
    logger.error.assert_called_once()


def test_no_adapter_raises_on_empty_dict_message():
    """`{}` now reaches parse_ws_message through the hummingbot client path."""
    from candles_feed.core.exchange_registry import ExchangeRegistry

    for name in ExchangeRegistry.get_registered_exchanges():
        adapter_cls = ExchangeRegistry.get_adapter_class(name)
        if not adapter_cls.__module__.startswith("candles_feed.adapters."):
            continue  # skip mocks registered by other tests
        try:
            adapter = adapter_cls()
        except TypeError:
            continue
        try:
            result = adapter.parse_ws_message({})
        except NotImplementedError:
            continue
        assert not result, name


async def test_garbage_frame_yields_nothing_and_does_not_raise():
    messages, logger = await _collect(["garbage"])
    assert messages == []
    logger.error.assert_called_once()
