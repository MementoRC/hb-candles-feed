#!/usr/bin/env python3
"""
Repository Health Dashboard Generator.

This script collects various metrics about a GitHub repository and outputs them
in JSON format, suitable for generating a health dashboard or for trend analysis.
It leverages the GitHub API and can integrate with other local reports (e.g., quality gates).
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
import importlib.util

# Adjust sys.path to import from candles_feed.core
# This assumes the script is run from the project root or that candles_feed is in PYTHONPATH
if importlib.util.find_spec("candles_feed.core") is None:
    current_file_dir = Path(__file__).resolve().parent
    project_root_dir = current_file_dir.parent  # Assumes scripts/ is one level down from root
    sys.path.insert(0, str(project_root_dir))
    # Re-check after modifying path, to ensure it's now available for subsequent imports
    if importlib.util.find_spec("candles_feed.core") is None:
        sys.stderr.write(
            "Error: Could not find 'candles_feed.core' even after adding project root to sys.path.\n"
            "Ensure the script is run from the project root or 'candles_feed' is installed.\n"
        )
        sys.exit(1)

from candles_feed.core.repository_insights import RepositoryInsightsCollector

# Setup basic logging for the script
logger = logging.getLogger("RepositoryHealthDashboard")


def load_json_report_data(file_path: Path | None) -> dict | None:
    """Loads a JSON report from the given file path."""
    if file_path and file_path.exists() and file_path.is_file():
        try:
            with open(file_path, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Could not decode JSON from {file_path}. Skipping.")
        except OSError:
            logger.warning(f"Could not read file {file_path}. Skipping.")
    elif file_path:
        logger.warning(f"Report file {file_path} not found or is not a file. Skipping.")
    return None


async def run_dashboard_collection():
    """Main asynchronous logic for collecting and saving dashboard data."""
    parser = argparse.ArgumentParser(
        description="Generate a repository health dashboard report.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--repo-owner",
        type=str,
        default=os.getenv("GITHUB_REPOSITORY_OWNER"),
        help="Owner of the GitHub repository (e.g., 'MementoRC'). Environment variable: GITHUB_REPOSITORY_OWNER.",
    )
    parser.add_argument(
        "--repo-name",
        type=str,
        help="Name of the GitHub repository (e.g., 'hb-candles-feed'). If GITHUB_REPOSITORY is set, this is derived.",
    )
    parser.add_argument(
        "--github-token",
        type=str,
        default=os.getenv("GITHUB_TOKEN"),
        help="GitHub API token for authentication. Environment variable: GITHUB_TOKEN.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("repository_health_report.json"),
        help="Path to save the JSON report.",
    )
    parser.add_argument(
        "--quality-gates-report",
        type=Path,
        help="Optional path to a quality_gates_report.json file to include CI/CD and quality snapshots.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level for this script and core modules).",
    )

    args = parser.parse_args()

    # Configure logging level based on verbosity
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        stream=sys.stdout,
    )
    logger.setLevel(log_level)
    logging.getLogger("candles_feed.core.repository_insights").setLevel(
        log_level
    )  # Also set for collector
    # Keep httpx logs less verbose unless specifically debugging it
    logging.getLogger("httpx").setLevel(logging.WARNING if not args.verbose else logging.DEBUG)

    repo_owner_val = args.repo_owner
    repo_name_val = args.repo_name

    github_repository_env = os.getenv("GITHUB_REPOSITORY")
    if not repo_owner_val and github_repository_env:
        try:
            repo_owner_val, repo_name_from_env = github_repository_env.split("/", 1)
            if not repo_name_val:
                repo_name_val = repo_name_from_env
        except ValueError:
            logger.error(
                f"Invalid GITHUB_REPOSITORY format: {github_repository_env}. Expected 'owner/name'."
            )
            sys.exit(1)

    if not repo_owner_val or not repo_name_val:
        logger.error(
            "Repository owner and name must be provided via arguments or GITHUB_REPOSITORY environment variable."
        )
        sys.exit(1)

    if not args.github_token:
        logger.warning(
            "GITHUB_TOKEN not provided. API requests will be unauthenticated and severely rate-limited."
        )

    logger.info(f"Starting repository health data collection for {repo_owner_val}/{repo_name_val}")

    collector = RepositoryInsightsCollector(
        repo_owner=repo_owner_val,
        repo_name=repo_name_val,
        github_token=args.github_token,
    )

    quality_gates_data_content = None
    if args.quality_gates_report:
        logger.info(f"Attempting to load quality gates report from: {args.quality_gates_report}")
        quality_gates_data_content = load_json_report_data(args.quality_gates_report)
        if quality_gates_data_content:
            logger.info("Successfully loaded quality gates report.")
        else:
            logger.warning(
                f"Failed to load or parse quality gates report from {args.quality_gates_report}. CI/CD and quality snapshots might be incomplete."
            )

    try:
        report = await collector.collect_all_metrics(
            quality_gates_report_data=quality_gates_data_content
        )
    except Exception as e:
        logger.exception(f"Failed to collect repository metrics: {e}")
        sys.exit(1)

    report_dict = report.to_dict()

    try:
        args.output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_file, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, default=str)
        logger.info(f"Repository health report saved to: {args.output_file}")
    except OSError as e:
        logger.error(f"Failed to write report to {args.output_file}: {e}")
        sys.exit(1)

    # Print a brief summary to console
    summary_lines = [
        "\n--- Repository Health Summary ---",
        f"Report for: {report.repo_owner}/{report.repo_name}",
        f"Generated at: {report.timestamp}",
        f"Collection duration: {report.collection_duration_seconds:.2f}s",
        f"Open Issues: {report.issues.total_open_issues}",
        f"Open PRs: {report.pull_requests.total_open_prs}",  # This will be 0 if PR metrics are stubbed
        f"Commits (last 7 days): {report.commits.commits_last_7_days}",
    ]
    if report.ci_cd_performance:
        summary_lines.append(
            f"Last CI/CD Run Timestamp: {report.ci_cd_performance.last_run_timestamp}"
        )
        summary_lines.append(f"Last CI/CD Run Passed: {report.ci_cd_performance.last_run_passed}")
    summary_lines.append("--- End Summary ---")
    print("\n".join(summary_lines))


if __name__ == "__main__":
    asyncio.run(run_dashboard_collection())
