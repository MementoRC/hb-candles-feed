"""
Integration tests for the repository_health_dashboard.py script.
"""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from candles_feed.core.github_metrics import IssueMetrics, RepositoryMetricsReport

# Adjust sys.path to allow importing the script if necessary, or use runpy
# For this test, we'll use subprocess to run the script as an executable.

SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent.parent / "scripts" / "repository_health_dashboard.py"
)


@pytest.fixture
def mock_collector_instance():
    instance = AsyncMock()
    report = RepositoryMetricsReport(
        repo_owner="test_owner",
        repo_name="test_repo",
        issues=IssueMetrics(total_open_issues=5, new_issues_last_7_days=1),
        collection_duration_seconds=1.23,
    )
    instance.collect_all_metrics = AsyncMock(return_value=report)
    return instance


@pytest.fixture
def mock_collector_class(mock_collector_instance):
    # The script being tested is scripts/repository_health_dashboard.py.
    # We need to patch RepositoryInsightsCollector where it's imported by the script.
    # The script uses: from candles_feed.core.repository_insights import RepositoryInsightsCollector
    # So, we patch it in the candles_feed.core.repository_insights module.
    with patch(
        "candles_feed.core.repository_insights.RepositoryInsightsCollector",
        return_value=mock_collector_instance,
    ) as mock_class:
        yield mock_class


@pytest.fixture
def temp_output_file(tmp_path):
    return tmp_path / "test_report.json"


@pytest.fixture
def temp_quality_gates_file(tmp_path):
    file_path = tmp_path / "quality_gates.json"
    data = {"overall_passed": True, "timestamp": "2023-01-01T00:00:00Z"}
    with open(file_path, "w") as f:
        json.dump(data, f)
    return file_path


def run_script(args_list, env_vars=None):
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)

    # Ensure python executable is the same as the one running pytest
    python_executable = os.sys.executable

    process = subprocess.run(
        [python_executable, str(SCRIPT_PATH)] + args_list,
        capture_output=True,
        text=True,
        env=env,
        check=False,  # Don't raise exception on non-zero exit, check manually
    )
    return process


class TestRepositoryHealthDashboardScript:
    def test_script_runs_successfully_with_args(
        self, temp_output_file
    ):  # mock_collector_class removed
        args = [
            "--repo-owner",
            "test_owner",
            "--repo-name",
            "test_repo",
            "--github-token",
            "fake_token",
            "--output-file",
            str(temp_output_file),
        ]
        result = run_script(args)

        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"

        assert temp_output_file.exists()
        with open(temp_output_file) as f:
            report_data = json.load(f)

        assert report_data["repo_owner"] == "test_owner"
        assert report_data["repo_name"] == "test_repo"

        # Expect default/zero values due to API call failures with "fake_token"
        assert report_data["issues"]["total_open_issues"] == 0
        assert report_data["issues"]["new_issues_last_7_days"] == 0
        # Assuming PullRequestMetrics and CommitMetrics also default to 0 for these key fields
        assert report_data["pull_requests"]["total_open_prs"] == 0
        assert report_data["commits"]["commits_last_7_days"] == 0

        assert isinstance(report_data["collection_duration_seconds"], float)
        assert report_data["collection_duration_seconds"] >= 0

        assert "Repository health report saved to" in result.stdout
        assert "--- Repository Health Summary ---" in result.stdout
        assert "Open Issues: 0" in result.stdout
        assert "Open PRs: 0" in result.stdout  # Assuming default is 0
        assert "Commits (last 7 days): 0" in result.stdout  # Assuming default is 0

        # Mock assertions removed as the real collector is used.

    def test_script_runs_with_env_vars(self, temp_output_file):
        # Test that environment variables are parsed correctly
        # Uses real collector, so expect default/zero values due to API failures with "env_token"
        env = {
            "GITHUB_REPOSITORY": "env_owner/env_repo",  # This will provide both repo_owner and repo_name
            "GITHUB_TOKEN": "env_token",
        }
        args = ["--output-file", str(temp_output_file)]
        result = run_script(args, env_vars=env)

        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"
        assert temp_output_file.exists()

        with open(temp_output_file) as f:
            report_data = json.load(f)

        assert report_data["repo_owner"] == "env_owner"
        assert report_data["repo_name"] == "env_repo"

        # Expect default/zero values due to API call failures with "env_token"
        assert report_data["issues"]["total_open_issues"] == 0
        assert report_data["issues"]["new_issues_last_7_days"] == 0
        assert report_data["pull_requests"]["total_open_prs"] == 0
        assert report_data["commits"]["commits_last_7_days"] == 0

        assert isinstance(report_data["collection_duration_seconds"], float)
        assert report_data["collection_duration_seconds"] >= 0

        assert "Repository health report saved to" in result.stdout
        assert "--- Repository Health Summary ---" in result.stdout
        assert "Open Issues: 0" in result.stdout
        assert "Open PRs: 0" in result.stdout
        assert "Commits (last 7 days): 0" in result.stdout

    def test_script_handles_missing_repo_owner_name(self):
        # No args, no env vars for repo owner/name
        result = run_script([])
        assert result.returncode == 1
        assert "Repository owner and name must be provided" in result.stdout

    def test_script_warns_missing_token(self, temp_output_file):
        args = [
            "--repo-owner",
            "test_owner",
            "--repo-name",
            "test_repo",
            "--output-file",
            str(temp_output_file),
            # No token
        ]
        result = run_script(args)
        assert result.returncode == 0
        assert (
            "GITHUB_TOKEN not provided. API requests will be unauthenticated" in result.stdout
        )  # Logged as warning

    def test_script_loads_quality_gates_report(self, temp_output_file, temp_quality_gates_file):
        args = [
            "--repo-owner",
            "test_owner",
            "--repo-name",
            "test_repo",
            "--github-token",
            "fake_token",
            "--output-file",
            str(temp_output_file),
            "--quality-gates-report",
            str(temp_quality_gates_file),
        ]
        result = run_script(args)
        assert result.returncode == 0
        assert (
            f"Attempting to load quality gates report from: {temp_quality_gates_file}"
            in result.stdout
        )
        assert "Successfully loaded quality gates report." in result.stdout

        # Verify the output file was created and contains expected data
        assert temp_output_file.exists()
        with open(temp_output_file) as f:
            report_data = json.load(f)

        assert report_data["repo_owner"] == "test_owner"
        assert report_data["repo_name"] == "test_repo"
        # The quality gates data should be included in ci_cd_performance
        assert report_data["ci_cd_performance"] is not None
        assert report_data["ci_cd_performance"]["last_run_passed"] is True
        assert report_data["ci_cd_performance"]["last_run_timestamp"] == "2023-01-01T00:00:00Z"

    def test_script_handles_missing_quality_gates_report(self, temp_output_file):
        missing_qg_file = Path("non_existent_quality_report.json")
        args = [
            "--repo-owner",
            "test_owner",
            "--repo-name",
            "test_repo",
            "--output-file",
            str(temp_output_file),
            "--quality-gates-report",
            str(missing_qg_file),
        ]
        result = run_script(args)
        assert result.returncode == 0  # Script should still succeed
        assert (
            f"Report file {missing_qg_file} not found or is not a file. Skipping." in result.stdout
        )  # Logged as warning
        assert (
            f"Failed to load or parse quality gates report from {missing_qg_file}" in result.stdout
        )

    def test_script_handles_network_issues_gracefully(self, temp_output_file):
        # Test that the script handles network/API failures gracefully and still produces output
        # This tests real API failure scenarios (404, 401) that would occur with fake tokens/repos
        args = [
            "--repo-owner",
            "nonexistent_owner",
            "--repo-name",
            "nonexistent_repo",
            "--github-token",
            "fake_token",
            "--output-file",
            str(temp_output_file),
        ]
        result = run_script(args)
        assert result.returncode == 0  # Script should still succeed with default values
        assert temp_output_file.exists()  # File should still be created

        with open(temp_output_file) as f:
            report_data = json.load(f)

        # Should contain default/zero values due to API failures
        assert report_data["repo_owner"] == "nonexistent_owner"
        assert report_data["repo_name"] == "nonexistent_repo"
        assert report_data["issues"]["total_open_issues"] == 0
        assert report_data["pull_requests"]["total_open_prs"] == 0

    def test_script_verbose_logging(self, temp_output_file):
        args = [
            "--repo-owner",
            "test_owner",
            "--repo-name",
            "test_repo",
            "--output-file",
            str(temp_output_file),
            "--verbose",
        ]
        result = run_script(args)
        assert result.returncode == 0

        # Check that INFO log from the script's main logger is present.
        # This confirms logging is active and configured by the script.
        # When --verbose is used, DEBUG level is set for loggers, so INFO logs will also appear.
        assert (
            "INFO - RepositoryHealthDashboard - Starting repository health data collection"
            in result.stdout
        )

        # Check for DEBUG level messages which should appear with --verbose
        # The GitHub API requests should produce DEBUG logs when verbose is enabled
        assert "DEBUG" in result.stdout or "Requesting GitHub API" in result.stdout

    def test_script_output_file_creation_failure(self, tmp_path):
        # Make output file path a directory to cause IOError
        output_dir_as_file = tmp_path / "output_is_dir"
        output_dir_as_file.mkdir()  # Create it as a directory

        args = [
            "--repo-owner",
            "test_owner",
            "--repo-name",
            "test_repo",
            "--output-file",
            str(output_dir_as_file),
        ]
        result = run_script(args)
        assert result.returncode == 1
        assert f"Failed to write report to {output_dir_as_file}" in result.stdout
        # The error message might be OS-dependent, e.g., "Is a directory"
        assert (
            "Is a directory" in result.stdout or "EISDIR" in result.stdout
        )  # Common error messages
