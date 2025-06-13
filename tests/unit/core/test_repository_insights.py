"""
Unit tests for the RepositoryInsightsCollector.
"""

import pytest
import aiohttp  # Changed from httpx
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
from aioresponses import aioresponses

from candles_feed.core.repository_insights import RepositoryInsightsCollector
from candles_feed.core.github_metrics import (
    IssueMetrics,
    PullRequestMetrics,
    CommitActivity,
    ReleaseMetrics,
    ContributorStats,
    CommunityEngagement,
    RepositoryMetricsReport,
    CICDPerformanceSnapshot,
    CodeQualitySnapshot,
)

REPO_OWNER = "test_owner"
REPO_NAME = "test_repo"
MOCK_TOKEN = "test_token"


@pytest.fixture
def collector():
    return RepositoryInsightsCollector(
        repo_owner=REPO_OWNER, repo_name=REPO_NAME, github_token=MOCK_TOKEN
    )


# mock_aiohttp_session fixture is removed


class TestRepositoryInsightsCollector:
    @pytest.mark.asyncio
    async def test_init(self, collector):
        assert collector.repo_owner == REPO_OWNER
        assert collector.repo_name == REPO_NAME
        assert collector.repo_path == f"{REPO_OWNER}/{REPO_NAME}"
        assert "Authorization" in collector.headers
        assert collector.headers["Authorization"] == f"Bearer {MOCK_TOKEN}"

    @pytest.mark.asyncio
    async def test_make_request_success(self, collector):
        with aioresponses() as m:
            url = f"{collector.BASE_URL}/test_endpoint"
            m.get(url, payload={"data": "success"}, status=200)

            # Call with client=None to test internal session creation
            result = await collector._make_request("/test_endpoint", client=None)

            assert result == {"data": "success"}
            m.assert_called_once_with(url, params=None, headers=collector.headers)

    @pytest.mark.asyncio
    async def test_make_request_http_error(self, collector):
        with aioresponses() as m:
            url = f"{collector.BASE_URL}/test_endpoint"
            m.get(url, status=404, body="Simulated Not Found")

            with pytest.raises(aiohttp.ClientResponseError) as excinfo:
                # Call with client=None to test internal session creation
                await collector._make_request("/test_endpoint", client=None)

            assert excinfo.value.status == 404

    @pytest.mark.asyncio
    async def test_fetch_paginated_data_success(self, collector):
        endpoint = "/paginated_endpoint"
        base_url = collector.BASE_URL

        with aioresponses() as m:
            # Page 1
            m.get(
                f"{base_url}{endpoint}?per_page=100&page=1",
                payload=[{"id": 1}, {"id": 2}],
                headers={"Link": f'<{base_url}/resource?page=2>; rel="next"'},
                status=200,
            )
            # Page 2
            m.get(f"{base_url}{endpoint}?per_page=100&page=2", payload=[{"id": 3}], status=200)

            # Call with client=None to test internal session creation
            results = await collector._fetch_paginated_data(endpoint, client=None)
            assert results == [{"id": 1}, {"id": 2}, {"id": 3}]

            # Verify calls were made (aioresponses tracks calls automatically)
            # Example: Check call count if needed, though specific params are checked by matching URLs
            assert len(m.requests) == 2

    @pytest.mark.asyncio
    async def test_get_issue_metrics_basic(self, collector):
        async with aiohttp.ClientSession() as session:  # Create a real session
            now = datetime.now(timezone.utc)
            # seven_days_ago = now - timedelta(days=7) # Not directly used in this version of test logic

        mock_open_issues_resp = [
            {
                "created_at": (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "state": "open",
                "labels": [{"name": "bug"}],
            },
            {
                "created_at": (now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "state": "open",
                "labels": [{"name": "feature"}],
            },
        ]
        # Issues for "since" query (new/closed in last 7 days)
        mock_all_issues_resp = [
            # New open issue (opened 3 days ago)
            {
                "created_at": (now - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "state": "open",
                "closed_at": None,
                "labels": [{"name": "bug"}],
            },
            # Issue closed in last 7 days (opened 15 days ago, closed 2 days ago)
            {
                "created_at": (now - timedelta(days=15)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "closed_at": (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "state": "closed",
                "labels": [],
            },
            # Old issue, created 30 days ago, still open - not new, not recently closed.
            {
                "created_at": (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "state": "open",
                "closed_at": None,
                "labels": [{"name": "documentation"}],
            },
        ]

        with patch.object(collector, "_fetch_paginated_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = [
                mock_open_issues_resp,  # For total_open_issues and oldest_open_issue_days
                mock_all_issues_resp,  # For new_issues_last_7_days, closed_issues_last_7_days, avg_issue_open_time
            ]

            metrics = await collector.get_issue_metrics(client=session)  # Pass the real session

            assert metrics.total_open_issues == 2
            assert metrics.new_issues_last_7_days == 1
            assert metrics.closed_issues_last_7_days == 1
            assert metrics.oldest_open_issue_days == pytest.approx(10, abs=0.1)

            # (15-2) = 13 days open time for the closed issue
            expected_avg_open_time = (
                (now - timedelta(days=2)) - (now - timedelta(days=15))
            ).total_seconds() / (24 * 3600)
            assert metrics.average_issue_open_time_days == pytest.approx(expected_avg_open_time)

            # Labels from all_issues_last_period
            assert metrics.labels_distribution == {"bug": 1, "documentation": 1}

            assert mock_fetch.call_count == 2
            # Call 1 for open issues
            call_args1 = mock_fetch.call_args_list[0]
            assert call_args1.args[0] == f"/repos/{REPO_OWNER}/{REPO_NAME}/issues"  # endpoint
            assert call_args1.args[1] == {
                "state": "open",
                "sort": "created",
                "direction": "asc",
            }  # params
            assert call_args1.args[2] is session  # client
            assert call_args1.kwargs == {}

            # Call 2 for all issues since 7 days ago
            call_args2 = mock_fetch.call_args_list[1]
            assert call_args2.args[0] == f"/repos/{REPO_OWNER}/{REPO_NAME}/issues"  # endpoint
            # Check params for the second call
            params_call2 = call_args2.args[1]
            assert params_call2["state"] == "all"
            assert "since" in params_call2
            assert call_args2.args[2] is session  # client
            assert call_args2.kwargs == {}

    @pytest.mark.asyncio
    async def test_get_pull_request_metrics_stubbed(self, collector):
        async with aiohttp.ClientSession() as session:  # Create a real session
            # Currently stubbed, so it should return default PullRequestMetrics
            metrics = await collector.get_pull_request_metrics(
                client=session
            )  # Pass the real session
            assert isinstance(metrics, PullRequestMetrics)
            assert metrics.total_open_prs == 0  # Default value

    @pytest.mark.asyncio
    async def test_get_commit_activity_success(self, collector):
        async with aiohttp.ClientSession() as session:  # Create a real session
            mock_activity_data = [
                {"week": 1672531200, "total": 10, "days": [0, 1, 2, 3, 4, 0, 0]},  # Week 1
                {"week": 1673136000, "total": 15, "days": [1, 2, 3, 4, 5, 0, 0]},  # Week 2
                {"week": 1673740800, "total": 5, "days": [0, 0, 1, 2, 2, 0, 0]},  # Week 3
                {
                    "week": 1674345600,
                    "total": 20,
                    "days": [2, 3, 4, 5, 6, 0, 0],
                },  # Week 4 (last week)
            ]
        with patch.object(collector, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_activity_data
            metrics = await collector.get_commit_activity(client=session)  # Pass the real session

        assert metrics.commits_last_7_days == 20
        assert metrics.commits_last_30_days == (10 + 15 + 5 + 20)
        assert metrics.commit_frequency_per_week == (10 + 15 + 5 + 20) / 4

    @pytest.mark.asyncio
    async def test_get_commit_activity_empty_or_error(self, collector):
        url = f"{collector.BASE_URL}/repos/{REPO_OWNER}/{REPO_NAME}/stats/commit_activity"

        # Test 202 (computing)
        async with aiohttp.ClientSession(headers=collector.headers) as session:
            with aioresponses() as m:
                m.get(url, status=202)
                metrics = await collector.get_commit_activity(client=session)
                assert metrics.commits_last_7_days == 0  # Should return default

        # Test 204 (no content)
        async with aiohttp.ClientSession(headers=collector.headers) as session:
            with aioresponses() as m:
                m.get(url, status=204)
                metrics = await collector.get_commit_activity(client=session)
                assert metrics.commits_last_7_days == 0

        # Test empty list response
        async with aiohttp.ClientSession(headers=collector.headers) as session:
            with aioresponses() as m:
                m.get(url, payload=[])
                metrics = await collector.get_commit_activity(client=session)
                assert metrics.commits_last_7_days == 0

    @pytest.mark.asyncio
    async def test_get_release_metrics_success(self, collector):
        async with aiohttp.ClientSession() as session:  # Create a real session
            now = datetime.now(timezone.utc).replace(
                microsecond=0
            )  # Ensure microseconds are zero for consistent comparison
            mock_releases_data = [
                {"published_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "name": "v1.1"},  # Newest
                {
                    "published_at": (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "name": "v1.0",
                },
                {
                    "created_at": (now - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "name": "v0.9",
                },  # Uses created_at
            ]
        with patch.object(collector, "_fetch_paginated_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_releases_data
            metrics = await collector.get_release_metrics(client=session)  # Pass the real session

        assert metrics.total_releases == 3
        assert metrics.last_release_date == now.isoformat()

        # Avg time: ((30-0) + (90-30)) / 2 = (30 + 60) / 2 = 45 days
        expected_avg_days = (30 + 60) / 2.0
        assert metrics.average_time_between_releases_days == pytest.approx(expected_avg_days)

    @pytest.mark.asyncio
    async def test_get_contributor_stats_success(self, collector):
        async with aiohttp.ClientSession() as session:  # Create a real session
            now_utc = datetime.now(timezone.utc)
            thirty_days_ago_ts = (now_utc - timedelta(days=30)).timestamp()

        mock_contributors_data = [
            {
                "author": {"login": "user1"},
                "total": 100,
                "weeks": [
                    {"w": int((now_utc - timedelta(days=5)).timestamp()), "c": 5},  # Active
                ],
            },
            {
                "author": {"login": "user2"},
                "total": 50,
                "weeks": [
                    {
                        "w": int((now_utc - timedelta(days=40)).timestamp()),
                        "c": 10,
                    },  # Not active recently
                ],
            },
            {
                "author": {"login": "user3"},
                "total": 75,
                "weeks": [
                    {"w": int(thirty_days_ago_ts + 3600), "c": 2},  # Active (just within 30 days)
                ],
            },
        ]
        with patch.object(collector, "_make_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_contributors_data
            metrics = await collector.get_contributor_stats(client=session)  # Pass the real session

        assert metrics.total_contributors == 3
        assert metrics.active_contributors_last_30_days == 2  # user1 and user3
        assert len(metrics.top_contributors) == 3  # All of them, as it's < 5
        assert metrics.top_contributors[0]["login"] == "user1"
        assert metrics.top_contributors[0]["commits"] == 100

    def test_parse_quality_gates_report(self, collector):
        report_data = {
            "timestamp": "2023-01-01T12:00:00Z",
            "total_duration": 120.5,
            "overall_passed": True,
            "checks": [
                {
                    "name": "Coverage Analysis",
                    "details": {"coverage_percentage": 85.0},
                },  # Example structure
                {"name": "Linting", "details": {"issue_count": 10}},
                {"name": "Security Scan", "details": {"critical_vulnerabilities": 2}},
            ],
        }
        # Note: _parse_quality_gates_report currently doesn't parse details from checks
        # It relies on summary or direct fields in report_data for some values.
        # This test reflects the current implementation.

        ci_snapshot, cq_snapshot = collector._parse_quality_gates_report(report_data)

        assert isinstance(ci_snapshot, CICDPerformanceSnapshot)
        assert ci_snapshot.last_run_timestamp == "2023-01-01T12:00:00Z"
        assert ci_snapshot.last_run_duration_seconds == 120.5
        assert ci_snapshot.last_run_passed is True
        assert (
            ci_snapshot.test_coverage_percentage is None
        )  # As it's not directly read from checks in current impl

        assert isinstance(cq_snapshot, CodeQualitySnapshot)
        assert cq_snapshot.lint_issues_count is None  # As it's not directly read
        assert cq_snapshot.critical_vulnerabilities is None  # As it's not directly read

    def test_parse_quality_gates_report_empty(self, collector):
        ci_snapshot, cq_snapshot = collector._parse_quality_gates_report({})
        assert isinstance(ci_snapshot, CICDPerformanceSnapshot)  # Default object
        assert isinstance(cq_snapshot, CodeQualitySnapshot)  # Default object

        ci_snapshot_none, cq_snapshot_none = collector._parse_quality_gates_report(None)
        assert ci_snapshot_none is None
        assert cq_snapshot_none is None

    @pytest.mark.asyncio
    async def test_collect_all_metrics_success(self, collector):
        # Mock all get_* methods
        with patch.object(
            collector,
            "get_issue_metrics",
            AsyncMock(return_value=IssueMetrics(total_open_issues=1)),
        ) as m_issues, patch.object(
            collector,
            "get_pull_request_metrics",
            AsyncMock(return_value=PullRequestMetrics(total_open_prs=2)),
        ) as m_prs, patch.object(
            collector,
            "get_commit_activity",
            AsyncMock(return_value=CommitActivity(commits_last_7_days=3)),
        ) as m_commits, patch.object(
            collector,
            "get_release_metrics",
            AsyncMock(return_value=ReleaseMetrics(total_releases=4)),
        ) as m_releases, patch.object(
            collector,
            "get_contributor_stats",
            AsyncMock(return_value=ContributorStats(total_contributors=5)),
        ) as m_contrib, patch.object(
            collector, "get_community_engagement", AsyncMock(return_value=CommunityEngagement())
        ) as m_community, patch.object(collector, "_parse_quality_gates_report") as m_parse_qg:
            m_parse_qg.return_value = (
                CICDPerformanceSnapshot(last_run_passed=True),
                CodeQualitySnapshot(lint_issues_count=0),
            )

            quality_data = {"some_key": "some_value"}
            report = await collector.collect_all_metrics(quality_gates_report_data=quality_data)

            assert isinstance(report, RepositoryMetricsReport)
            assert report.issues.total_open_issues == 1
            assert report.pull_requests.total_open_prs == 2
            assert report.commits.commits_last_7_days == 3
            assert report.releases.total_releases == 4
            assert report.contributors.total_contributors == 5
            assert report.ci_cd_performance.last_run_passed is True
            assert report.code_quality.lint_issues_count == 0
            assert report.collection_duration_seconds > 0
            assert report.environment == {"collector_version": "0.1.0"}

            m_issues.assert_called_once()
            m_prs.assert_called_once()
            m_commits.assert_called_once()
            m_releases.assert_called_once()
            m_contrib.assert_called_once()
            m_community.assert_called_once()
            m_parse_qg.assert_called_once_with(quality_data)

    @pytest.mark.asyncio
    async def test_collect_all_metrics_partial_failure(self, collector, caplog):
        with patch.object(
            collector, "get_issue_metrics", AsyncMock(side_effect=Exception("Issue fetch failed"))
        ) as m_issues, patch.object(
            collector,
            "get_pull_request_metrics",
            AsyncMock(return_value=PullRequestMetrics(total_open_prs=2)),
        ) as m_prs:
            report = await collector.collect_all_metrics()

            assert isinstance(report.issues, IssueMetrics)  # Should be default
            assert report.issues.total_open_issues == 0
            assert report.pull_requests.total_open_prs == 2  # This one succeeded

            assert "Failed to collect issues metrics" in caplog.text
            assert "Issue fetch failed" in caplog.text
