"""Additional branch-coverage tests for RepositoryInsightsCollector."""

from datetime import UTC, datetime, timedelta

import aiohttp
import pytest

from candles_feed.core.repository_insights import RepositoryInsightsCollector


@pytest.fixture
def collector():
    return RepositoryInsightsCollector("owner", "repo")


@pytest.fixture
def served(serve_get, monkeypatch):
    """Local server standing in for the GitHub API."""
    monkeypatch.setattr(RepositoryInsightsCollector, "BASE_URL", serve_get.url)
    return serve_get


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class TestInit:
    def test_no_token_means_no_auth_header(self, collector):
        assert "Authorization" not in collector.headers
        assert collector.monitoring_manager is None

    def test_monitoring_manager_stored(self):
        sentinel = object()
        c = RepositoryInsightsCollector("o", "r", monitoring_manager=sentinel)
        assert c.monitoring_manager is sentinel


class TestMakeRequest:
    async def test_none_params_are_stripped(self, collector, served):
        served.add("/x", payload={"ok": 1})
        async with aiohttp.ClientSession() as session:
            result = await collector._make_request("/x", params={"a": 1, "b": None}, client=session)
        assert result == {"ok": 1}
        (request,) = served.requests
        assert dict(request.query) == {"a": "1"}

    async def test_provided_client_is_not_closed(self, collector, served):
        served.add("/x", payload=[])
        async with aiohttp.ClientSession() as session:
            await collector._make_request("/x", client=session)
            assert not session.closed

    async def test_client_error_is_reraised(self, collector, served):
        served.add("/x", disconnect=True)
        with pytest.raises(aiohttp.ClientConnectionError):
            await collector._make_request("/x")


class TestFetchPaginated:
    async def test_stops_when_no_link_header(self, collector, served):
        served.add("/p", payload=[{"id": 1}])
        async with aiohttp.ClientSession() as session:
            items = await collector._fetch_paginated_data("/p", {"k": None}, session)
        assert items == [{"id": 1}]
        assert len(served.requests) == 1

    async def test_stops_on_link_without_next(self, collector, served):
        served.add(
            "/p",
            payload=[{"id": 1}],
            headers={"Link": f'<{served.url}/p?page=1>; rel="prev"'},
        )
        async with aiohttp.ClientSession() as session:
            items = await collector._fetch_paginated_data("/p", client=session)
        assert items == [{"id": 1}]

    async def test_stops_on_empty_page(self, collector, served):
        served.add("/p", payload=[])
        async with aiohttp.ClientSession() as session:
            assert await collector._fetch_paginated_data("/p", client=session) == []

    async def test_http_error_raises(self, collector, served):
        served.add("/p", status=500)
        with pytest.raises(aiohttp.ClientResponseError) as exc:
            await collector._fetch_paginated_data("/p")
        assert exc.value.status == 500

    async def test_client_error_raises(self, collector, served):
        served.add("/p", disconnect=True)
        with pytest.raises(aiohttp.ClientConnectionError):
            await collector._fetch_paginated_data("/p")


class TestIssueMetricsEdges:
    async def test_no_issues_leaves_defaults(self, collector, mocker):
        mocker.patch.object(collector, "_fetch_paginated_data", mocker.AsyncMock(return_value=[]))
        metrics = await collector.get_issue_metrics(client=mocker.Mock())
        assert metrics.total_open_issues == 0
        assert metrics.average_issue_open_time_days is None
        assert metrics.labels_distribution == {}

    async def test_closed_before_created_is_not_averaged_and_unnamed_label(self, collector, mocker):
        now = datetime.now(UTC)
        issues = [
            {
                "created_at": _fmt(now - timedelta(days=20)),
                "closed_at": _fmt(now - timedelta(days=30)),  # closed before created, old
                "state": "closed",
                "labels": [{}],
            }
        ]
        mocker.patch.object(
            collector, "_fetch_paginated_data", mocker.AsyncMock(side_effect=[[], issues])
        )
        metrics = await collector.get_issue_metrics(client=mocker.Mock())
        assert metrics.closed_issues_last_7_days == 0
        assert metrics.new_issues_last_7_days == 0
        assert metrics.average_issue_open_time_days is None
        assert metrics.labels_distribution == {"unknown": 1}


class TestCommitActivity:
    async def test_fewer_than_four_weeks(self, collector, mocker):
        mocker.patch.object(
            collector,
            "_make_request",
            mocker.AsyncMock(return_value=[{"total": 4}, {"total": 6}]),
        )
        metrics = await collector.get_commit_activity(client=mocker.Mock())
        assert metrics.commits_last_7_days == 6
        assert metrics.commits_last_30_days == 10
        assert metrics.commit_frequency_per_week == 5

    async def test_non_list_response_keeps_defaults(self, collector, mocker):
        mocker.patch.object(
            collector, "_make_request", mocker.AsyncMock(return_value={"message": "x"})
        )
        metrics = await collector.get_commit_activity(client=mocker.Mock())
        assert metrics.commits_last_7_days == 0

    async def test_other_http_error_is_reraised(self, collector, served):
        served.add(f"/repos/{collector.repo_path}/stats/commit_activity", status=500)
        async with aiohttp.ClientSession() as session:
            with pytest.raises(aiohttp.ClientResponseError):
                await collector.get_commit_activity(client=session)

    async def test_client_error_is_swallowed(self, collector, mocker):
        mocker.patch.object(
            collector,
            "_make_request",
            mocker.AsyncMock(side_effect=aiohttp.ClientConnectionError("down")),
        )
        metrics = await collector.get_commit_activity(client=mocker.Mock())
        assert metrics.commits_last_7_days == 0


class TestReleaseMetrics:
    async def test_no_releases(self, collector, mocker):
        mocker.patch.object(collector, "_fetch_paginated_data", mocker.AsyncMock(return_value=[]))
        metrics = await collector.get_release_metrics(client=mocker.Mock())
        assert metrics.total_releases == 0
        assert metrics.last_release_date is None

    async def test_single_release_has_no_average(self, collector, mocker):
        mocker.patch.object(
            collector,
            "_fetch_paginated_data",
            mocker.AsyncMock(return_value=[{"published_at": "2024-01-02T03:04:05Z"}]),
        )
        metrics = await collector.get_release_metrics(client=mocker.Mock())
        assert metrics.total_releases == 1
        assert metrics.last_release_date == "2024-01-02T03:04:05+00:00"
        assert metrics.average_time_between_releases_days is None

    async def test_releases_without_dates(self, collector, mocker):
        mocker.patch.object(
            collector,
            "_fetch_paginated_data",
            mocker.AsyncMock(return_value=[{"name": "a"}, {"name": "b"}]),
        )
        metrics = await collector.get_release_metrics(client=mocker.Mock())
        assert metrics.total_releases == 2
        assert metrics.last_release_date is None
        assert metrics.average_time_between_releases_days is None

    async def test_only_one_dated_release_among_many(self, collector, mocker):
        mocker.patch.object(
            collector,
            "_fetch_paginated_data",
            mocker.AsyncMock(
                return_value=[{"created_at": "2024-01-02T00:00:00Z"}, {"name": "undated"}]
            ),
        )
        metrics = await collector.get_release_metrics(client=mocker.Mock())
        assert metrics.average_time_between_releases_days is None


class TestContributorStats:
    async def test_top_five_and_missing_fields(self, collector, mocker):
        data = [{"author": {"login": f"u{i}"}, "total": i, "weeks": []} for i in range(7)]
        data.append({"total": 100})  # no author, no weeks
        mocker.patch.object(collector, "_make_request", mocker.AsyncMock(return_value=data))
        metrics = await collector.get_contributor_stats(client=mocker.Mock())
        assert metrics.total_contributors == 8
        assert metrics.active_contributors_last_30_days == 0
        assert len(metrics.top_contributors) == 5
        assert metrics.top_contributors[0] == {"login": "unknown", "commits": 100}
        assert metrics.top_contributors[1] == {"login": "u6", "commits": 6}

    async def test_inactive_weeks_with_zero_commits(self, collector, mocker):
        future = int((datetime.now(UTC) + timedelta(days=1)).timestamp())
        data = [{"author": {"login": "a"}, "total": 1, "weeks": [{"w": future, "c": 0}]}]
        mocker.patch.object(collector, "_make_request", mocker.AsyncMock(return_value=data))
        metrics = await collector.get_contributor_stats(client=mocker.Mock())
        assert metrics.active_contributors_last_30_days == 0

    async def test_empty_response_keeps_defaults(self, collector, mocker):
        mocker.patch.object(collector, "_make_request", mocker.AsyncMock(return_value=[]))
        metrics = await collector.get_contributor_stats(client=mocker.Mock())
        assert metrics.total_contributors == 0

    @pytest.mark.parametrize("status", [202, 204])
    async def test_computing_or_empty_statuses_are_tolerated(self, collector, mocker, status):
        err = aiohttp.ClientResponseError(mocker.Mock(), (), status=status, message="m")
        mocker.patch.object(collector, "_make_request", mocker.AsyncMock(side_effect=err))
        metrics = await collector.get_contributor_stats(client=mocker.Mock())
        assert metrics.total_contributors == 0

    async def test_other_http_error_is_reraised(self, collector, mocker):
        err = aiohttp.ClientResponseError(mocker.Mock(), (), status=500, message="m")
        mocker.patch.object(collector, "_make_request", mocker.AsyncMock(side_effect=err))
        with pytest.raises(aiohttp.ClientResponseError):
            await collector.get_contributor_stats(client=mocker.Mock())

    async def test_client_error_is_swallowed(self, collector, mocker):
        mocker.patch.object(
            collector,
            "_make_request",
            mocker.AsyncMock(side_effect=aiohttp.ClientConnectionError("down")),
        )
        metrics = await collector.get_contributor_stats(client=mocker.Mock())
        assert metrics.total_contributors == 0


class TestCommunityAndCollectAll:
    async def test_community_engagement_returns_default(self, collector, mocker):
        metrics = await collector.get_community_engagement(client=mocker.Mock())
        assert type(metrics).__name__ == "CommunityEngagement"

    async def test_collect_all_without_quality_data_skips_snapshots(self, collector, mocker):
        for name in (
            "get_issue_metrics",
            "get_pull_request_metrics",
            "get_commit_activity",
            "get_release_metrics",
            "get_contributor_stats",
            "get_community_engagement",
        ):
            mocker.patch.object(collector, name, mocker.AsyncMock(side_effect=RuntimeError(name)))
        parse = mocker.patch.object(collector, "_parse_quality_gates_report")
        report = await collector.collect_all_metrics()
        parse.assert_not_called()
        assert report.collection_duration_seconds >= 0
        assert report.environment == {"collector_version": "0.1.0"}
