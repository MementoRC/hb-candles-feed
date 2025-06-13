"""
Unit tests for GitHub metrics data classes.
"""

import pytest
from datetime import datetime, timedelta, timezone
from typing import Optional

from candles_feed.core.github_metrics import (
    IssueMetrics,
    PullRequestMetrics,
    CommitActivity,
    ReleaseMetrics,
    ContributorStats,
    CommunityEngagement,
    CICDPerformanceSnapshot,
    CodeQualitySnapshot,
    RepositoryMetricsReport,
)


class TestIssueMetrics:
    def test_default_initialization(self):
        metrics = IssueMetrics()
        assert metrics.total_open_issues == 0
        assert metrics.new_issues_last_7_days == 0
        assert metrics.closed_issues_last_7_days == 0
        assert metrics.average_issue_open_time_days is None
        assert metrics.oldest_open_issue_days is None
        assert metrics.labels_distribution == {}

    def test_custom_initialization(self):
        metrics = IssueMetrics(
            total_open_issues=10,
            new_issues_last_7_days=2,
            labels_distribution={"bug": 1, "feature": 1},
        )
        assert metrics.total_open_issues == 10
        assert metrics.new_issues_last_7_days == 2
        assert metrics.labels_distribution == {"bug": 1, "feature": 1}


class TestPullRequestMetrics:
    def test_default_initialization(self):
        metrics = PullRequestMetrics()
        assert metrics.total_open_prs == 0
        assert metrics.new_prs_last_7_days == 0
        assert metrics.merged_prs_last_7_days == 0
        assert metrics.closed_prs_last_7_days == 0
        assert metrics.average_pr_merge_time_days is None
        assert metrics.average_pr_open_time_days is None
        assert metrics.pr_staleness_info == {}


class TestCommitActivity:
    def test_default_initialization(self):
        metrics = CommitActivity()
        assert metrics.commits_last_7_days == 0
        assert metrics.commits_last_30_days == 0
        assert metrics.commit_frequency_per_week == 0.0


class TestReleaseMetrics:
    def test_default_initialization(self):
        metrics = ReleaseMetrics()
        assert metrics.total_releases == 0
        assert metrics.last_release_date is None
        assert metrics.average_time_between_releases_days is None


class TestContributorStats:
    def test_default_initialization(self):
        metrics = ContributorStats()
        assert metrics.total_contributors == 0
        assert metrics.active_contributors_last_30_days == 0
        assert metrics.top_contributors == []


class TestCommunityEngagement:
    def test_default_initialization(self):
        metrics = CommunityEngagement()
        assert metrics.issue_response_time_avg_hours is None
        assert metrics.pr_review_time_avg_hours is None


class TestCICDPerformanceSnapshot:
    def test_default_initialization(self):
        snapshot = CICDPerformanceSnapshot()
        assert snapshot.last_run_timestamp is None
        assert snapshot.last_run_duration_seconds is None
        assert snapshot.last_run_passed is None
        assert snapshot.test_coverage_percentage is None


class TestCodeQualitySnapshot:
    def test_default_initialization(self):
        snapshot = CodeQualitySnapshot()
        assert snapshot.lint_issues_count is None
        assert snapshot.critical_vulnerabilities is None


class TestRepositoryMetricsReport:
    def test_default_initialization(self):
        report = RepositoryMetricsReport(repo_owner="test_owner", repo_name="test_repo")
        assert report.repo_owner == "test_owner"
        assert report.repo_name == "test_repo"
        assert isinstance(report.timestamp, str)
        now = datetime.now(timezone.utc)  # Changed from utcnow()
        report_time = datetime.fromisoformat(report.timestamp.replace("Z", "+00:00"))
        assert abs((now - report_time).total_seconds()) < 5  # Check if timestamp is recent

        assert report.collection_duration_seconds == 0.0
        assert isinstance(report.issues, IssueMetrics)
        assert isinstance(report.pull_requests, PullRequestMetrics)
        assert isinstance(report.commits, CommitActivity)
        assert isinstance(report.releases, ReleaseMetrics)
        assert isinstance(report.contributors, ContributorStats)
        assert isinstance(report.community, CommunityEngagement)
        assert report.ci_cd_performance is None
        assert report.code_quality is None
        assert report.environment == {}

    def test_to_dict_conversion(self):
        report = RepositoryMetricsReport(
            repo_owner="owner",
            repo_name="repo",
            issues=IssueMetrics(total_open_issues=5),
            ci_cd_performance=CICDPerformanceSnapshot(last_run_passed=True),
            environment={"version": "1.0"},
        )
        report_dict = report.to_dict()

        assert report_dict["repo_owner"] == "owner"
        assert report_dict["repo_name"] == "repo"
        assert "timestamp" in report_dict
        assert report_dict["issues"]["total_open_issues"] == 5
        assert report_dict["ci_cd_performance"]["last_run_passed"] is True
        assert report_dict["code_quality"] is None  # Ensure None fields are handled
        assert report_dict["environment"]["version"] == "1.0"

    def test_serialization_with_optional_fields(self):
        report = RepositoryMetricsReport(repo_owner="owner", repo_name="repo")
        report.code_quality = CodeQualitySnapshot(lint_issues_count=10)
        report_dict = report.to_dict()

        assert report_dict["code_quality"]["lint_issues_count"] == 10
        assert report_dict["ci_cd_performance"] is None
