"""
Integration tests for the repository_health_dashboard.py script.
"""

import pytest
import subprocess
import json
from pathlib import Path
import os
from unittest.mock import patch, AsyncMock

from candles_feed.core.github_metrics import RepositoryMetricsReport, IssueMetrics

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
    def test_script_runs_successfully_with_args(self, mock_collector_class, temp_output_file):
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
        with open(temp_output_file, "r") as f:
            report_data = json.load(f)

        assert report_data["repo_owner"] == "test_owner"
        assert report_data["repo_name"] == "test_repo"
        assert report_data["issues"]["total_open_issues"] == 5
        assert "Repository health report saved to" in result.stdout
        assert "--- Repository Health Summary ---" in result.stdout

        mock_collector_class.assert_called_once_with(
            repo_owner="test_owner", repo_name="test_repo", github_token="fake_token"
        )
        mock_collector_class.return_value.collect_all_metrics.assert_called_once()

    def test_script_runs_with_env_vars(self, mock_collector_class, temp_output_file):
        env = {
            "GITHUB_REPOSITORY_OWNER": "env_owner",
            "GITHUB_REPOSITORY": "env_owner/env_repo",  # This will provide repo_name
            "GITHUB_TOKEN": "env_token",
        }
        args = ["--output-file", str(temp_output_file)]
        result = run_script(args, env_vars=env)

        assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"
        assert temp_output_file.exists()
        report_data = json.loads(temp_output_file.read_text())
        assert report_data["repo_owner"] == "env_owner"
        assert report_data["repo_name"] == "env_repo"

        mock_collector_class.assert_called_once_with(
            repo_owner="env_owner", repo_name="env_repo", github_token="env_token"
        )

    def test_script_handles_missing_repo_owner_name(self):
        # No args, no env vars for repo owner/name
        result = run_script([])
        assert result.returncode == 1
        assert "Repository owner and name must be provided" in result.stderr

    def test_script_warns_missing_token(self, mock_collector_class, temp_output_file):
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

    def test_script_loads_quality_gates_report(
        self, mock_collector_class, temp_output_file, temp_quality_gates_file
    ):
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

        # Check that collect_all_metrics was called with the parsed data
        mock_collector_class.return_value.collect_all_metrics.assert_called_once()
        call_args = mock_collector_class.return_value.collect_all_metrics.call_args
        assert "quality_gates_report_data" in call_args.kwargs
        assert call_args.kwargs["quality_gates_report_data"] == {
            "overall_passed": True,
            "timestamp": "2023-01-01T00:00:00Z",
        }

    def test_script_handles_missing_quality_gates_report(
        self, mock_collector_class, temp_output_file
    ):
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

    def test_script_handles_collector_failure(self, mock_collector_class, temp_output_file):
        mock_collector_class.return_value.collect_all_metrics.side_effect = Exception(
            "Collector exploded"
        )
        args = [
            "--repo-owner",
            "test_owner",
            "--repo-name",
            "test_repo",
            "--output-file",
            str(temp_output_file),
        ]
        result = run_script(args)
        assert result.returncode == 1
        assert "Failed to collect repository metrics: Collector exploded" in result.stderr
        assert not temp_output_file.exists()  # Should not write file on collection error

    def test_script_verbose_logging(self, mock_collector_class, temp_output_file):
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
        # Check for a DEBUG level log message (exact message might depend on script's DEBUG logs)
        # For example, if RepositoryInsightsCollector logs something at DEBUG on init or during calls
        # This is a bit fragile, depends on actual DEBUG logs.
        # A more robust way would be to check if logger levels were set to DEBUG.
        # For now, let's assume some debug output from the collector or script itself.
        # Example: "Requesting GitHub API:" is a DEBUG log from RepositoryInsightsCollector._make_request
        # Since collect_all_metrics is mocked, we might not see this.
        # Let's check for the basic logging setup message.
        assert (
            "DEBUG - candles_feed.core.repository_insights" in result.stdout
            or "DEBUG - RepositoryHealthDashboard" in result.stdout
        )
        # The actual logger name might vary based on how it's captured by subprocess.
        # The script sets logging format, so we'd see "DEBUG" in the output.

        # A simple check for "DEBUG" in output might be sufficient if verbose enables it broadly.
        assert "DEBUG" in result.stdout  # General check for DEBUG level messages

    def test_script_output_file_creation_failure(self, mock_collector_class, tmp_path):
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
        assert f"Failed to write report to {output_dir_as_file}" in result.stderr
        # The error message might be OS-dependent, e.g., "Is a directory"
        assert (
            "Is a directory" in result.stderr or "EISDIR" in result.stderr
        )  # Common error messages
