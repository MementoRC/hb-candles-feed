from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class IssueMetrics:
    total_open_issues: int = 0
    new_issues_last_7_days: int = 0
    closed_issues_last_7_days: int = 0
    average_issue_open_time_days: Optional[float] = None
    oldest_open_issue_days: Optional[float] = None
    labels_distribution: Dict[str, int] = field(default_factory=dict)


@dataclass
class PullRequestMetrics:
    total_open_prs: int = 0
    new_prs_last_7_days: int = 0
    merged_prs_last_7_days: int = 0
    closed_prs_last_7_days: int = 0  # Not merged
    average_pr_merge_time_days: Optional[float] = None
    average_pr_open_time_days: Optional[float] = None  # For unmerged, open PRs
    pr_staleness_info: Dict[str, int] = field(default_factory=dict)  # e.g. "0-7 days", "8-30 days"


@dataclass
class CommitActivity:
    commits_last_7_days: int = 0
    commits_last_30_days: int = 0
    commit_frequency_per_week: float = 0.0  # Average over a longer period


@dataclass
class ReleaseMetrics:
    total_releases: int = 0
    last_release_date: Optional[str] = None
    average_time_between_releases_days: Optional[float] = None


@dataclass
class ContributorStats:
    total_contributors: int = 0
    active_contributors_last_30_days: int = 0
    top_contributors: List[Dict[str, Any]] = field(
        default_factory=list
    )  # e.g. [{"login": "user", "commits": 100}]


@dataclass
class CommunityEngagement:
    # Could extend with discussions, stars, forks if needed
    issue_response_time_avg_hours: Optional[float] = None
    pr_review_time_avg_hours: Optional[float] = None


@dataclass
class CICDPerformanceSnapshot:
    # This would be populated from quality_gates.py reports or CI workflow data
    last_run_timestamp: Optional[str] = None
    last_run_duration_seconds: Optional[float] = None
    last_run_passed: Optional[bool] = None
    test_coverage_percentage: Optional[float] = None
    # Potentially add trends here if aggregating multiple reports
    # test_success_rate_trend: Optional[str] = None # e.g. "improving", "declining"
    # coverage_trend: Optional[str] = None


@dataclass
class CodeQualitySnapshot:
    # This would also be populated from quality_gates.py or other static analysis tools
    lint_issues_count: Optional[int] = None
    critical_vulnerabilities: Optional[int] = None
    # code_smells_count: Optional[int] = None
    # duplication_percentage: Optional[float] = None


@dataclass
class RepositoryMetricsReport:
    """Complete repository metrics report."""

    repo_owner: str
    repo_name: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    collection_duration_seconds: float = 0.0

    issues: IssueMetrics = field(default_factory=IssueMetrics)
    pull_requests: PullRequestMetrics = field(default_factory=PullRequestMetrics)
    commits: CommitActivity = field(default_factory=CommitActivity)
    releases: ReleaseMetrics = field(default_factory=ReleaseMetrics)
    contributors: ContributorStats = field(default_factory=ContributorStats)
    community: CommunityEngagement = field(default_factory=CommunityEngagement)

    # Snapshots from other systems
    ci_cd_performance: Optional[CICDPerformanceSnapshot] = None
    code_quality: Optional[CodeQualitySnapshot] = None

    environment: Dict[str, Any] = field(default_factory=dict)  # e.g., script version

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
