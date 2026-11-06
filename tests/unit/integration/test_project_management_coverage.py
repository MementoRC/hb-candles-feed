"""Behaviour tests for candles_feed.integration.project_management."""

import asyncio
import hashlib
import hmac
import json
import re

import pytest
from aioresponses import aioresponses

from candles_feed.integration import project_management as pm
from candles_feed.integration.project_management import (
    GitHubProjectsIntegration,
    Milestone,
    ProjectManagementConfig,
    ProjectManagementIntegration,
    Task,
    TaskPriority,
    TaskStatus,
    WebhookHandler,
)

ISSUES_URL = "https://api.github.com/repos/org/issues"
ISSUE_URL = "https://api.github.com/repos/org/issues/7"


def _issue(**overrides):
    issue = {
        "number": 7,
        "title": "T",
        "body": "B",
        "state": "open",
        "labels": [],
        "html_url": "http://x/7",
        "created_at": "c",
        "updated_at": "u",
    }
    issue.update(overrides)
    return issue


def _gh_config(**kw):
    return ProjectManagementConfig(
        github_projects_enabled=True, github_token="tok", github_org="org", **kw
    )


@pytest.fixture
def logger(mocker):
    return mocker.Mock()


class TestDataclasses:
    def test_task_defaults(self):
        t = Task("1", "t", "d", TaskStatus.PENDING, TaskPriority.LOW)
        assert t.labels == []
        assert t.metadata == {}
        assert t.assignee is None

    def test_milestone_defaults(self):
        m = Milestone("1", "t", "d")
        assert m.metadata == {}
        assert m.progress == 0.0
        assert m.status == "active"

    def test_config_default_mappings(self):
        c = ProjectManagementConfig()
        assert c.status_mapping["closed"] is TaskStatus.DONE
        assert c.priority_mapping["critical"] is TaskPriority.CRITICAL

    def test_config_custom_mappings_preserved(self):
        c = ProjectManagementConfig(
            status_mapping={"x": TaskStatus.BLOCKED}, priority_mapping={"y": TaskPriority.LOW}
        )
        assert c.status_mapping == {"x": TaskStatus.BLOCKED}
        assert c.priority_mapping == {"y": TaskPriority.LOW}


class TestGitHubSync:
    async def test_disabled_returns_empty(self):
        gh = GitHubProjectsIntegration(ProjectManagementConfig())
        assert await gh.sync_tasks() == []

    async def test_default_logger(self):
        gh = GitHubProjectsIntegration(ProjectManagementConfig())
        assert gh.logger.name == pm.__name__

    async def test_sync_maps_issues(self, logger):
        issues = [
            _issue(
                state="closed",
                labels=[{"name": "High-Priority"}, {"name": "bug"}],
                assignee={"login": "bob"},
            ),
            _issue(number=8, labels=[{"name": "low"}]),
            _issue(number=9, labels=[{"name": "urgent"}, {"name": "low"}]),
            _issue(number=10, assignee=None),
        ]
        gh = GitHubProjectsIntegration(_gh_config(), logger)
        with aioresponses() as m:
            m.get(ISSUES_URL, payload=issues)
            tasks = await gh.sync_tasks()
            (call,) = next(iter(m.requests.values()))
            assert call.kwargs["headers"]["Authorization"] == "Bearer tok"

        assert [t.id for t in tasks] == ["7", "8", "9", "10"]
        assert tasks[0].status is TaskStatus.DONE
        assert tasks[0].priority is TaskPriority.HIGH
        assert tasks[0].assignee == "bob"
        assert tasks[0].labels == ["High-Priority", "bug"]
        assert tasks[0].metadata == {
            "github_url": "http://x/7",
            "created_at": "c",
            "updated_at": "u",
        }
        assert tasks[1].priority is TaskPriority.LOW
        assert tasks[1].status is TaskStatus.PENDING
        assert tasks[2].priority is TaskPriority.LOW  # later "low" label overrides
        assert tasks[3].assignee is None
        assert tasks[3].priority is TaskPriority.MEDIUM
        logger.debug.assert_called_once()

    async def test_sync_non_200_logs_error(self, logger):
        gh = GitHubProjectsIntegration(_gh_config(), logger)
        with aioresponses() as m:
            m.get(ISSUES_URL, status=403)
            assert await gh.sync_tasks() == []
        assert "403" in logger.error.call_args.args[0]

    async def test_sync_exception_is_logged_and_swallowed(self, logger):
        gh = GitHubProjectsIntegration(_gh_config(), logger)
        with aioresponses() as m:
            m.get(ISSUES_URL, exception=RuntimeError("net down"))
            assert await gh.sync_tasks() == []
        assert "net down" in logger.error.call_args.args[0]


class TestGitHubUpdate:
    async def test_disabled(self):
        gh = GitHubProjectsIntegration(ProjectManagementConfig())
        assert await gh.update_task_status("7", TaskStatus.DONE) is False

    @pytest.mark.parametrize(
        ("status", "state"),
        [
            (TaskStatus.DONE, "closed"),
            (TaskStatus.CANCELLED, "closed"),
            (TaskStatus.PENDING, "open"),
            (TaskStatus.IN_PROGRESS, "open"),
        ],
    )
    async def test_success_sends_mapped_state(self, logger, status, state):
        gh = GitHubProjectsIntegration(_gh_config(), logger)
        with aioresponses() as m:
            m.patch(ISSUE_URL, status=200)
            assert await gh.update_task_status("7", status) is True
            (call,) = next(iter(m.requests.values()))
            assert call.kwargs["json"] == {"state": state}

    async def test_failure_status(self, logger):
        gh = GitHubProjectsIntegration(_gh_config(), logger)
        with aioresponses() as m:
            m.patch(ISSUE_URL, status=422)
            assert await gh.update_task_status("7", TaskStatus.DONE) is False
        assert "422" in logger.error.call_args.args[0]

    async def test_exception(self, logger):
        gh = GitHubProjectsIntegration(_gh_config(), logger)
        with aioresponses() as m:
            m.patch(ISSUE_URL, exception=RuntimeError("boom"))
            assert await gh.update_task_status("7", TaskStatus.DONE) is False
        assert "boom" in logger.error.call_args.args[0]


def _request(mocker, body: bytes, headers: dict[str, str]):
    req = mocker.Mock()
    req.headers = headers
    req.read = mocker.AsyncMock(return_value=body)
    return req


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class TestWebhookSignature:
    def test_no_secret_accepts_anything(self):
        h = WebhookHandler(ProjectManagementConfig())
        assert h._verify_webhook_signature(b"x", "") is True

    def test_valid_and_invalid_signature(self):
        h = WebhookHandler(ProjectManagementConfig(webhook_secret="s3"))
        assert h._verify_webhook_signature(b"x", _sign("s3", b"x")) is True
        assert h._verify_webhook_signature(b"x", _sign("other", b"x")) is False
        assert h._verify_webhook_signature(b"x", "") is False


class TestWebhookHandler:
    async def test_invalid_signature_returns_401(self, mocker, logger):
        h = WebhookHandler(ProjectManagementConfig(webhook_secret="s3"), logger=logger)
        resp = await h._webhook_handler(_request(mocker, b"{}", {"X-Hub-Signature-256": "bad"}))
        assert resp.status == 401
        logger.warning.assert_called_once()

    async def test_issue_event_invokes_callback(self, mocker, logger):
        received = []
        h = WebhookHandler(
            ProjectManagementConfig(webhook_secret="s3"),
            task_update_callback=received.append,
            logger=logger,
        )
        body = json.dumps(
            {
                "action": "closed",
                "issue": _issue(state="closed", assignee={"login": "al"}, labels=[{"name": "bug"}]),
            }
        ).encode()
        headers = {"X-Hub-Signature-256": _sign("s3", body), "X-GitHub-Event": "issues"}
        resp = await h._webhook_handler(_request(mocker, body, headers))
        assert resp.status == 200
        (task,) = received
        assert task.id == "7"
        assert task.status is TaskStatus.DONE
        assert task.priority is TaskPriority.MEDIUM
        assert task.assignee == "al"
        assert task.labels == ["bug"]
        assert task.metadata["action"] == "closed"

    async def test_issue_event_unhandled_action_and_no_callback(self, logger):
        received = []
        h = WebhookHandler(
            ProjectManagementConfig(), task_update_callback=received.append, logger=logger
        )
        await h._handle_issue_event({"action": "labeled", "issue": _issue()})
        assert received == []

        h2 = WebhookHandler(ProjectManagementConfig(), logger=logger)
        await h2._handle_issue_event(
            {"action": "opened", "issue": _issue()}
        )  # no callback: no error
        logger.debug.assert_called_once()

    async def test_issue_event_open_without_assignee(self, logger):
        received = []
        h = WebhookHandler(
            ProjectManagementConfig(), task_update_callback=received.append, logger=logger
        )
        await h._handle_issue_event({"action": "opened", "issue": _issue()})
        assert received[0].status is TaskStatus.PENDING
        assert received[0].assignee is None

    async def test_project_card_event(self, mocker, logger):
        h = WebhookHandler(ProjectManagementConfig(), logger=logger)
        body = json.dumps({"action": "moved"}).encode()
        resp = await h._webhook_handler(_request(mocker, body, {"X-GitHub-Event": "project_card"}))
        assert resp.status == 200
        assert "moved" in logger.debug.call_args.args[0]

    async def test_unknown_event(self, mocker, logger):
        h = WebhookHandler(ProjectManagementConfig(), logger=logger)
        resp = await h._webhook_handler(_request(mocker, b"{}", {}))
        assert resp.status == 200
        assert "unknown" in logger.debug.call_args.args[0]

    async def test_bad_json_returns_500(self, mocker, logger):
        h = WebhookHandler(ProjectManagementConfig(), logger=logger)
        resp = await h._webhook_handler(_request(mocker, b"not json", {}))
        assert resp.status == 500
        logger.error.assert_called_once()


class TestWebhookLifecycle:
    async def test_start_disabled(self, mocker, logger):
        runner_cls = mocker.patch.object(pm.web, "AppRunner")
        h = WebhookHandler(ProjectManagementConfig(webhook_enabled=False), logger=logger)
        await h.start()
        runner_cls.assert_not_called()
        assert h._runner is None

    async def test_start_and_stop(self, mocker, logger):
        runner = mocker.Mock(setup=mocker.AsyncMock(), cleanup=mocker.AsyncMock())
        mocker.patch.object(pm.web, "AppRunner", return_value=runner)
        site = mocker.Mock(start=mocker.AsyncMock())
        site_cls = mocker.patch.object(pm.web, "TCPSite", return_value=site)
        h = WebhookHandler(ProjectManagementConfig(webhook_port=9999), logger=logger)

        await h.start()
        runner.setup.assert_awaited_once()
        site_cls.assert_called_once_with(runner, "0.0.0.0", 9999)
        site.start.assert_awaited_once()
        routes = [r.resource.canonical for r in h._app.router.routes() if r.method == "POST"]
        assert routes == ["/webhook/project-management"]

        await h.stop()
        runner.cleanup.assert_awaited_once()
        assert h._runner is None
        assert h._app is None

    async def test_start_failure_reraises(self, mocker, logger):
        runner = mocker.Mock(setup=mocker.AsyncMock(side_effect=OSError("in use")))
        mocker.patch.object(pm.web, "AppRunner", return_value=runner)
        h = WebhookHandler(ProjectManagementConfig(), logger=logger)
        with pytest.raises(OSError, match="in use"):
            await h.start()
        assert "in use" in logger.error.call_args.args[0]

    async def test_stop_without_start(self, logger):
        h = WebhookHandler(ProjectManagementConfig(), logger=logger)
        await h.stop()
        logger.info.assert_called_once()


def _task(tid="1", status=TaskStatus.PENDING):
    return Task(tid, f"title{tid}", "d", status, TaskPriority.LOW)


class TestProjectManagementIntegration:
    def test_defaults(self):
        p = ProjectManagementIntegration()
        assert isinstance(p.config, ProjectManagementConfig)
        assert p.webhook_handler.task_update_callback == p._handle_task_update

    def test_handle_task_update_caches(self, logger):
        p = ProjectManagementIntegration(logger=logger)
        t = _task()
        p._handle_task_update(t)
        assert p._tasks_cache == {"1": t}

    async def test_get_tasks_initial_sync(self, mocker):
        p = ProjectManagementIntegration(ProjectManagementConfig())
        mocker.patch.object(
            p.github_integration,
            "sync_tasks",
            mocker.AsyncMock(return_value=[_task("a"), _task("b")]),
        )
        assert [t.id for t in await p.get_tasks()] == ["a", "b"]
        # cache now populated: no second sync
        await p.get_tasks()
        p.github_integration.sync_tasks.assert_awaited_once()

    async def test_get_tasks_sync_disabled(self, mocker):
        p = ProjectManagementIntegration(ProjectManagementConfig(auto_sync_enabled=False))
        sync = mocker.patch.object(p.github_integration, "sync_tasks", mocker.AsyncMock())
        assert await p.get_tasks() == []
        sync.assert_not_called()

    async def test_get_task(self):
        p = ProjectManagementIntegration()
        t = _task()
        p._tasks_cache["1"] = t
        assert await p.get_task("1") is t
        assert await p.get_task("nope") is None

    async def test_update_status_local_only(self):
        p = ProjectManagementIntegration()
        p._tasks_cache["1"] = _task()
        assert await p.update_task_status("1", TaskStatus.DONE) is True
        assert p._tasks_cache["1"].status is TaskStatus.DONE
        assert await p.update_task_status("missing", TaskStatus.DONE) is False

    async def test_update_status_github_success_and_failure(self, mocker):
        p = ProjectManagementIntegration(_gh_config())
        p._tasks_cache["1"] = _task()
        upd = mocker.patch.object(
            p.github_integration, "update_task_status", mocker.AsyncMock(side_effect=[True, False])
        )
        assert await p.update_task_status("1", TaskStatus.DONE) is True
        assert p._tasks_cache["1"].status is TaskStatus.DONE
        assert await p.update_task_status("1", TaskStatus.BLOCKED) is False
        assert p._tasks_cache["1"].status is TaskStatus.DONE  # unchanged on failure
        assert upd.await_count == 2

    async def test_update_status_github_success_uncached_task(self, mocker):
        p = ProjectManagementIntegration(_gh_config())
        mocker.patch.object(
            p.github_integration, "update_task_status", mocker.AsyncMock(return_value=True)
        )
        assert await p.update_task_status("zzz", TaskStatus.DONE) is True

    async def test_periodic_sync_updates_cache_then_cancels(self, mocker, logger):
        p = ProjectManagementIntegration(
            ProjectManagementConfig(sync_interval_seconds=0.01), logger
        )
        mocker.patch.object(
            p.github_integration, "sync_tasks", mocker.AsyncMock(return_value=[_task("x")])
        )
        job = asyncio.create_task(p._sync_tasks_periodically())
        for _ in range(100):
            if "x" in p._tasks_cache:
                break
            await asyncio.sleep(0.01)
        job.cancel()
        await job  # CancelledError is swallowed by the loop and returns cleanly
        assert "x" in p._tasks_cache

    async def test_periodic_sync_disabled_skips_sync(self, mocker, logger):
        cfg = ProjectManagementConfig(auto_sync_enabled=False, sync_interval_seconds=0.01)
        p = ProjectManagementIntegration(cfg, logger)
        sync = mocker.patch.object(p.github_integration, "sync_tasks", mocker.AsyncMock())
        job = asyncio.create_task(p._sync_tasks_periodically())
        await asyncio.sleep(0.03)
        job.cancel()
        await job
        sync.assert_not_called()

    async def test_periodic_sync_error_is_logged_and_continues(self, mocker, logger):
        p = ProjectManagementIntegration(
            ProjectManagementConfig(sync_interval_seconds=0.01), logger
        )
        sync = mocker.patch.object(
            p.github_integration,
            "sync_tasks",
            mocker.AsyncMock(side_effect=[RuntimeError("bad"), [_task("ok")]]),
        )
        job = asyncio.create_task(p._sync_tasks_periodically())
        for _ in range(100):
            if "ok" in p._tasks_cache:
                break
            await asyncio.sleep(0.01)
        job.cancel()
        await job
        assert sync.await_count >= 2
        assert any("bad" in str(c.args[0]) for c in logger.error.call_args_list)
        assert "ok" in p._tasks_cache

    async def test_start_and_stop(self, mocker, logger):
        p = ProjectManagementIntegration(ProjectManagementConfig(sync_interval_seconds=60), logger)
        mocker.patch.object(p.webhook_handler, "start", mocker.AsyncMock())
        stop_wh = mocker.patch.object(p.webhook_handler, "stop", mocker.AsyncMock())
        mocker.patch.object(p.github_integration, "sync_tasks", mocker.AsyncMock(return_value=[]))
        await p.start()
        assert p._sync_task is not None
        await asyncio.sleep(0)
        await p.stop()
        assert p._sync_task is None
        stop_wh.assert_awaited_once()

    async def test_start_without_auto_sync(self, mocker, logger):
        p = ProjectManagementIntegration(ProjectManagementConfig(auto_sync_enabled=False), logger)
        mocker.patch.object(p.webhook_handler, "start", mocker.AsyncMock())
        await p.start()
        assert p._sync_task is None

    async def test_start_failure_stops_and_reraises(self, mocker, logger):
        p = ProjectManagementIntegration(ProjectManagementConfig(), logger)
        mocker.patch.object(p.webhook_handler, "start", mocker.AsyncMock(side_effect=OSError("x")))
        stop_wh = mocker.patch.object(p.webhook_handler, "stop", mocker.AsyncMock())
        with pytest.raises(OSError):
            await p.start()
        stop_wh.assert_awaited_once()
        assert re.search("Failed to start", logger.error.call_args.args[0])
