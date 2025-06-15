import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple  # Added Any, Dict

import aiohttp  # Using aiohttp for async requests

from .github_metrics import (
    CICDPerformanceSnapshot,
    CodeQualitySnapshot,
    CommitActivity,
    CommunityEngagement,
    ContributorStats,
    IssueMetrics,
    PullRequestMetrics,
    ReleaseMetrics,
    RepositoryMetricsReport,
)

# Configure logging
logger = logging.getLogger(__name__)
# BasicConfig will be set by the script using this module, or here if run directly.
# logging.basicConfig(level=logging.INFO)


class RepositoryInsightsCollector:
    """Collects insights and metrics from a GitHub repository."""

    BASE_URL = "https://api.github.com"

    def __init__(
        self,
        repo_owner: str,
        repo_name: str,
        github_token: str | None = None,
        monitoring_manager: Any | None = None,
    ):  # Placeholder for MonitoringManager
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.repo_path = f"{repo_owner}/{repo_name}"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if github_token:
            self.headers["Authorization"] = f"Bearer {github_token}"

        self.monitoring_manager = monitoring_manager

    async def _make_request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        client: aiohttp.ClientSession | None = None,
    ) -> Any:
        """Helper function to make GET requests to GitHub API."""
        url = f"{self.BASE_URL}{endpoint}"

        # Clean params, removing None values to avoid serialization issues
        # aiohttp handles None in params, but explicit cleaning is safer for other libraries if reused.
        cleaned_params = None
        if params is not None:
            cleaned_params = {k: v for k, v in params.items() if v is not None}

        temp_session = False
        if client is None:
            timeout = aiohttp.ClientTimeout(total=20.0)
            client = aiohttp.ClientSession(headers=self.headers, timeout=timeout)
            temp_session = True

        try:
            logger.debug(f"Requesting GitHub API: {url} with params: {cleaned_params}")
            async with client.get(url, params=cleaned_params) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            logger.error(f"GitHub API request failed for {url}: {e.status} - {e.message}")
            raise
        except aiohttp.ClientError as e:  # Catches other client errors like connection issues
            logger.error(f"GitHub API request error for {url}: {e}")
            raise
        finally:
            if temp_session and client:
                await client.close()

    async def _fetch_paginated_data(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        client: aiohttp.ClientSession | None = None,
    ) -> list[dict[str, Any]]:
        """Fetches all items from a paginated GitHub API endpoint."""
        all_items = []
        current_params = params.copy() if params else {}
        current_params.setdefault("per_page", 100)
        page = 1

        # Clean initial params
        if current_params is not None:
            current_params = {k: v for k, v in current_params.items() if v is not None}

        temp_session = False
        if client is None:
            timeout = aiohttp.ClientTimeout(total=20.0)
            client = aiohttp.ClientSession(headers=self.headers, timeout=timeout)
            temp_session = True

        try:
            while True:
                current_params["page"] = page
                url = f"{self.BASE_URL}{endpoint}"
                logger.debug(
                    f"Requesting paginated GitHub API: {url} with params: {current_params}"
                )
                async with client.get(url, params=current_params) as response:
                    response.raise_for_status()
                    items = await response.json()
                    if not items:
                        break
                    all_items.extend(items)
                    page += 1
                    if (
                        "Link" not in response.headers
                        or 'rel="next"' not in response.headers["Link"]
                    ):
                        break
        except aiohttp.ClientResponseError as e:
            logger.error(f"GitHub API pagination failed for {endpoint}: {e.status} - {e.message}")
            raise
        except aiohttp.ClientError as e:
            logger.error(f"GitHub API pagination error for {endpoint}: {e}")
            raise
        finally:
            if temp_session and client:
                await client.close()
        return all_items

    async def get_issue_metrics(self, client: aiohttp.ClientSession) -> IssueMetrics:
        metrics = IssueMetrics()
        now_utc = datetime.now(timezone.utc)
        seven_days_ago_utc = now_utc - timedelta(days=7)

        open_issues_data = await self._fetch_paginated_data(
            f"/repos/{self.repo_path}/issues",
            {"state": "open", "sort": "created", "direction": "asc"},
            client,
        )
        metrics.total_open_issues = len(open_issues_data)

        if open_issues_data:
            oldest_issue_date_str = open_issues_data[0]["created_at"]  # Due to sort direction
            oldest_issue_date = datetime.strptime(
                oldest_issue_date_str, "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)
            metrics.oldest_open_issue_days = (now_utc - oldest_issue_date).total_seconds() / (
                24 * 3600
            )

        issues_since_date_str = seven_days_ago_utc.isoformat()
        all_issues_last_period = await self._fetch_paginated_data(
            f"/repos/{self.repo_path}/issues",
            {
                "state": "all",
                "since": issues_since_date_str,
                "sort": "created",
                "direction": "desc",
            },
            client,
        )

        total_open_time_seconds = 0
        issues_counted_for_avg_open_time = 0

        for issue in all_issues_last_period:
            created_at = datetime.strptime(issue["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )

            if created_at >= seven_days_ago_utc and (
                issue["state"] == "open" or issue["closed_at"] is None
            ):  # Check if it's still open or was opened and not yet closed
                metrics.new_issues_last_7_days += 1

            if issue["closed_at"]:
                closed_at = datetime.strptime(issue["closed_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=timezone.utc
                )
                if closed_at >= seven_days_ago_utc:  # Check if closed within the last 7 days
                    metrics.closed_issues_last_7_days += 1

                # For average open time, consider all closed issues in the fetched period
                # Ensure created_at is before closed_at for meaningful duration
                if closed_at > created_at:
                    total_open_time_seconds += (closed_at - created_at).total_seconds()
                    issues_counted_for_avg_open_time += 1

            for label in issue.get("labels", []):
                label_name = label.get("name", "unknown")
                metrics.labels_distribution[label_name] = (
                    metrics.labels_distribution.get(label_name, 0) + 1
                )

        if issues_counted_for_avg_open_time > 0:
            metrics.average_issue_open_time_days = (
                total_open_time_seconds / issues_counted_for_avg_open_time
            ) / (24 * 3600)

        logger.info(f"Collected issue metrics for {self.repo_path}")
        return metrics

    async def get_pull_request_metrics(self, client: aiohttp.ClientSession) -> PullRequestMetrics:
        # This is a stub. Implementation would be similar to get_issue_metrics,
        # querying PR endpoints and calculating relevant stats.
        metrics = PullRequestMetrics()
        logger.info(f"Pull request metrics collection (stubbed) for {self.repo_path}")
        # Example: Get open PRs
        # open_prs_data = await self._fetch_paginated_data(f"/repos/{self.repo_path}/pulls", {"state": "open"}, client)
        # metrics.total_open_prs = len(open_prs_data)
        return metrics

    async def get_commit_activity(self, client: aiohttp.ClientSession) -> CommitActivity:
        metrics = CommitActivity()
        try:
            # This endpoint returns commit activity for the last year, grouped by week.
            # It might return 202 if stats are being computed.
            commit_stats_response = await self._make_request(
                f"/repos/{self.repo_path}/stats/commit_activity", client=client
            )

            if commit_stats_response and isinstance(commit_stats_response, list):
                if len(commit_stats_response) > 0:
                    metrics.commits_last_7_days = commit_stats_response[-1]["total"]
                if len(commit_stats_response) >= 4:
                    metrics.commits_last_30_days = sum(
                        week["total"] for week in commit_stats_response[-4:]
                    )
                else:  # Less than 4 weeks of data
                    metrics.commits_last_30_days = sum(
                        week["total"] for week in commit_stats_response
                    )

                total_commits_year = sum(week["total"] for week in commit_stats_response)
                if len(commit_stats_response) > 0:
                    metrics.commit_frequency_per_week = total_commits_year / len(
                        commit_stats_response
                    )
            else:  # Empty list or unexpected response
                logger.warning(
                    f"Commit activity data for {self.repo_path} was empty or not in expected list format."
                )

        except aiohttp.ClientResponseError as e:
            if e.status == 202:
                logger.warning(
                    f"Commit activity stats for {self.repo_path} are being computed by GitHub. Try again later."
                )
            elif e.status == 204:  # No content, often for empty repos
                logger.warning(
                    f"Commit activity stats for {self.repo_path} not available (empty repository or no commits)."
                )
            else:  # Re-raise other HTTP errors
                raise
        except aiohttp.ClientError as e:  # Catch other client errors
            logger.error(
                f"Failed to get commit activity for {self.repo_path} due to client error: {e}"
            )
            # Metrics will remain default
        logger.info(f"Collected commit activity for {self.repo_path}")
        return metrics

    async def get_release_metrics(self, client: aiohttp.ClientSession) -> ReleaseMetrics:
        metrics = ReleaseMetrics()
        releases = await self._fetch_paginated_data(
            f"/repos/{self.repo_path}/releases", client=client
        )
        metrics.total_releases = len(releases)
        if releases:
            # API generally returns newest first.
            last_release = releases[0]
            last_release_date_str = last_release.get("published_at") or last_release.get(
                "created_at"
            )
            if last_release_date_str:
                metrics.last_release_date = (
                    datetime.strptime(last_release_date_str, "%Y-%m-%dT%H:%M:%SZ")
                    .replace(tzinfo=timezone.utc)
                    .isoformat()
                )

            if len(releases) > 1:
                release_dates = sorted(
                    [
                        datetime.strptime(
                            r.get("published_at") or r.get("created_at"), "%Y-%m-%dT%H:%M:%SZ"
                        ).replace(tzinfo=timezone.utc)
                        for r in releases
                        if r.get("published_at") or r.get("created_at")
                    ],
                    reverse=True,
                )

                if len(release_dates) > 1:
                    total_time_diff_days = 0
                    for i in range(len(release_dates) - 1):
                        time_diff = release_dates[i] - release_dates[i + 1]
                        total_time_diff_days += time_diff.total_seconds() / (24 * 3600)
                    metrics.average_time_between_releases_days = total_time_diff_days / (
                        len(release_dates) - 1
                    )
        logger.info(f"Collected release metrics for {self.repo_path}")
        return metrics

    async def get_contributor_stats(self, client: aiohttp.ClientSession) -> ContributorStats:
        metrics = ContributorStats()
        try:
            # /stats/contributors can be heavy and return 202 if computing.
            contributors_data = await self._make_request(
                f"/repos/{self.repo_path}/stats/contributors", client=client
            )
            if contributors_data and isinstance(contributors_data, list):
                metrics.total_contributors = len(contributors_data)

                active_count = 0
                thirty_days_ago_ts = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()

                for contrib_stat in contributors_data:
                    if "weeks" in contrib_stat:
                        # Check if any commit in any week by this contributor falls in the last 30 days
                        for week_activity in contrib_stat["weeks"]:
                            if week_activity["w"] >= thirty_days_ago_ts and week_activity["c"] > 0:
                                active_count += 1
                                break
                metrics.active_contributors_last_30_days = active_count

                sorted_contributors = sorted(
                    contributors_data, key=lambda c: c.get("total", 0), reverse=True
                )
                metrics.top_contributors = [
                    {
                        "login": c.get("author", {}).get("login", "unknown"),
                        "commits": c.get("total", 0),
                    }
                    for c in sorted_contributors[:5]  # Top 5
                ]
        except aiohttp.ClientResponseError as e:
            if e.status == 202:
                logger.warning(
                    f"Contributor stats for {self.repo_path} are being computed by GitHub. Try again later."
                )
            elif e.status == 204:
                logger.warning(
                    f"Contributor stats for {self.repo_path} not available (empty repository or no contributors)."
                )
            else:
                raise
        except aiohttp.ClientError as e:  # Catch other client errors
            logger.error(
                f"Failed to get contributor stats for {self.repo_path} due to client error: {e}"
            )
            # Metrics will remain default
        logger.info(f"Collected contributor stats for {self.repo_path}")
        return metrics

    async def get_community_engagement(self, client: aiohttp.ClientSession) -> CommunityEngagement:
        # This is a stub. Real implementation would involve analyzing issue/PR comment timings, etc.
        metrics = CommunityEngagement()
        logger.info(f"Community engagement metrics collection (stubbed) for {self.repo_path}")
        return metrics

    def _parse_quality_gates_report(
        self, report_data: dict[str, Any]
    ) -> tuple[CICDPerformanceSnapshot | None, CodeQualitySnapshot | None]:
        """Parses a QualityGateReport structure to extract CI/CD and Code Quality snapshots."""
        ci_cd_snapshot = None
        code_quality_snapshot = None

        if report_data is None:  # Explicitly check for None
            return ci_cd_snapshot, code_quality_snapshot

        # CI/CD Performance Snapshot
        # Uses summary and specific check details from QualityGateReport
        coverage_percentage = None
        lint_issues = None
        security_vulnerabilities = None

        for check in report_data.get("checks", []):
            if check.get("name") == "Coverage Analysis":
                # Assuming coverage details are in check['details'] or a sub-field
                # This needs to match the actual structure of coverage_analysis.py output if integrated
                # For now, let's assume a simple structure or it's part of the main summary
                pass  # Placeholder
            if check.get("name") == "Linting":
                # Example: if linting check provides a count of issues
                # lint_issues = check.get("details", {}).get("issue_count")
                pass  # Placeholder
            if check.get("name") == "Security Scan":
                # Example: if security scan provides vulnerability counts
                # security_vulnerabilities = check.get("details", {}).get("critical_vulnerabilities")
                pass  # Placeholder

        # Fallback to summary if specific check details are not parsed as above
        # This part needs to align with the actual structure of QualityGateReport
        # summary = report_data.get("summary", {})
        # Example: if coverage is directly in summary (it might not be)
        # coverage_percentage = report_data.get("summary", {}).get("coverage_percentage")

        ci_cd_snapshot = CICDPerformanceSnapshot(
            last_run_timestamp=report_data.get("timestamp"),
            last_run_duration_seconds=report_data.get("total_duration"),
            last_run_passed=report_data.get("overall_passed"),
            test_coverage_percentage=coverage_percentage,  # Needs actual data source
        )

        code_quality_snapshot = CodeQualitySnapshot(
            lint_issues_count=lint_issues,  # Needs actual data source
            critical_vulnerabilities=security_vulnerabilities,  # Needs actual data source
        )

        return ci_cd_snapshot, code_quality_snapshot

    async def collect_all_metrics(
        self, quality_gates_report_data: dict[str, Any] | None = None
    ) -> RepositoryMetricsReport:
        """Collects all repository metrics and generates a report."""
        collection_start_time = time.monotonic()
        report = RepositoryMetricsReport(repo_owner=self.repo_owner, repo_name=self.repo_name)

        # Use a shared client for all GitHub API calls within this collection run
        timeout = aiohttp.ClientTimeout(total=30.0)
        # Connector for connection pooling settings
        connector = aiohttp.TCPConnector(
            limit_per_host=5, limit=20
        )  # limit is total connections, limit_per_host for GitHub
        async with aiohttp.ClientSession(
            headers=self.headers, timeout=timeout, connector=connector
        ) as client:
            # Gather GitHub specific metrics concurrently
            # Using return_exceptions=True to allow individual tasks to fail without stopping all
            results = await asyncio.gather(
                self.get_issue_metrics(client),
                self.get_pull_request_metrics(client),
                self.get_commit_activity(client),
                self.get_release_metrics(client),
                self.get_contributor_stats(client),
                self.get_community_engagement(client),
                return_exceptions=True,
            )

        # Assign results, checking for exceptions
        metric_fields = [
            "issues",
            "pull_requests",
            "commits",
            "releases",
            "contributors",
            "community",
        ]
        for i, field_name in enumerate(metric_fields):
            if isinstance(results[i], Exception):
                logger.error(
                    f"Failed to collect {field_name} metrics for {self.repo_path}: {results[i]}"
                )
                # Default empty metric object for this field is already set in RepositoryMetricsReport
            else:
                setattr(report, field_name, results[i])

        # Load snapshots from other systems if data provided
        if quality_gates_report_data:
            ci_snapshot, cq_snapshot = self._parse_quality_gates_report(quality_gates_report_data)
            report.ci_cd_performance = ci_snapshot
            report.code_quality = cq_snapshot
            logger.info(f"Processed quality gates data for {self.repo_path}")

        report.collection_duration_seconds = time.monotonic() - collection_start_time
        report.environment = {"collector_version": "0.1.0"}  # Example version

        logger.info(
            f"Repository metrics collection for {self.repo_path} completed in {report.collection_duration_seconds:.2f}s"
        )
        return report
