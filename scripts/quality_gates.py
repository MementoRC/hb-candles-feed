#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quality Gates Orchestrator for Candles Feed Project.

This script implements comprehensive quality gates with enterprise-grade reporting,
trend analysis, and CI/CD integration. It orchestrates all quality checks and
provides detailed reporting with fail-fast behavior.

Usage:
    python scripts/quality_gates.py [--mode MODE] [--output FORMAT] [--config FILE]

Modes:
    - development: Full checks with detailed reporting (default)
    - ci: Optimized for CI environment with structured output
    - quick: Essential checks only for rapid feedback

Output Formats:
    - console: Human-readable console output (default)
    - json: Machine-readable JSON for CI integration
    - both: Both console and JSON output
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


@dataclass
class QualityCheckResult:
    """Result of a quality check."""
    name: str
    passed: bool
    duration: float
    message: str
    details: Dict[str, Any]
    command: Optional[str] = None
    exit_code: Optional[int] = None


@dataclass
class QualityGateReport:
    """Complete quality gate report."""
    timestamp: str
    mode: str
    overall_passed: bool
    total_duration: float
    checks: List[QualityCheckResult]
    summary: Dict[str, Any]
    environment: Dict[str, Any]


class QualityGatesOrchestrator:
    """Main orchestrator for quality gates."""
    
    def __init__(self, mode: str = "development", output_format: str = "console"):
        self.mode = mode
        self.output_format = output_format
        self.project_root = Path(__file__).parent.parent
        self.start_time = time.time()
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO if mode == "development" else logging.WARNING,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)
        
        # Quality checks configuration
        self.quality_checks = self._configure_quality_checks()
        
    def _configure_quality_checks(self) -> List[Dict[str, Any]]:
        """Configure quality checks based on mode."""
        base_checks = [
            {
                "name": "Code Formatting",
                "command": ["pixi", "run", "format", "--check"],
                "description": "Verify code follows formatting standards",
                "critical": True,
                "quick": True
            },
            {
                "name": "Linting",
                "command": ["pixi", "run", "lint"],
                "description": "Check code quality and style violations",
                "critical": True,
                "quick": True
            },
            {
                "name": "Type Checking",
                "command": ["pixi", "run", "typecheck"],
                "description": "Validate type annotations and static analysis",
                "critical": True,
                "quick": False
            },
            {
                "name": "Unit Tests",
                "command": ["pixi", "run", "test-unit"],
                "description": "Execute unit test suite",
                "critical": True,
                "quick": True
            },
            {
                "name": "Integration Tests",
                "command": ["pixi", "run", "test-integration"],
                "description": "Execute integration test suite",
                "critical": True,
                "quick": False
            },
            {
                "name": "Coverage Analysis",
                "command": ["python", "scripts/coverage_analysis.py", "--mode", self.mode],
                "description": "Analyze test coverage and trends",
                "critical": True,
                "quick": False
            },
            {
                "name": "Documentation Check",
                "command": ["python", "scripts/documentation_check.py", "--mode", self.mode],
                "description": "Validate documentation completeness and quality",
                "critical": False,
                "quick": False
            },
            {
                "name": "Security Scan",
                "command": ["pixi", "run", "security-scan"] if self._has_security_scan() else None,
                "description": "Security vulnerability analysis",
                "critical": True,
                "quick": False
            }
        ]
        
        # Filter checks based on mode
        if self.mode == "quick":
            return [check for check in base_checks if check.get("quick", False) and check["command"]]
        elif self.mode == "ci":
            return [check for check in base_checks if check["command"]]
        else:  # development mode
            return [check for check in base_checks if check["command"]]
    
    def _has_security_scan(self) -> bool:
        """Check if security scan command is available."""
        try:
            result = subprocess.run(
                ["pixi", "task", "list"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            return "security-scan" in result.stdout
        except Exception:
            return False
    
    def _run_command(self, command: List[str], description: str) -> QualityCheckResult:
        """Run a quality check command and return results."""
        start_time = time.time()
        
        try:
            self.logger.info(f"Running {description}...")
            
            # Change to project root for command execution
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            duration = time.time() - start_time
            passed = result.returncode == 0
            
            # Extract additional details from output
            details = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "cwd": str(self.project_root)
            }
            
            message = f"PASS {description} passed" if passed else f"FAIL {description} failed"
            if not passed and result.stderr:
                message += f": {result.stderr.strip()}"
            
            return QualityCheckResult(
                name=description,
                passed=passed,
                duration=duration,
                message=message,
                details=details,
                command=" ".join(command),
                exit_code=result.returncode
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return QualityCheckResult(
                name=description,
                passed=False,
                duration=duration,
                message=f"TIMEOUT {description} timed out after 5 minutes",
                details={"error": "timeout", "timeout_seconds": 300},
                command=" ".join(command),
                exit_code=-1
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return QualityCheckResult(
                name=description,
                passed=False,
                duration=duration,
                message=f"ERROR {description} failed with exception: {str(e)}",
                details={"error": str(e), "exception_type": type(e).__name__},
                command=" ".join(command),
                exit_code=-2
            )
    
    def run_quality_gates(self) -> QualityGateReport:
        """Execute all configured quality gates."""
        self.logger.info(f"Starting quality gates in {self.mode} mode...")
        
        results = []
        overall_passed = True
        failed_critical = []
        
        for check_config in self.quality_checks:
            result = self._run_command(
                check_config["command"],
                check_config["name"]
            )
            
            results.append(result)
            
            if not result.passed:
                overall_passed = False
                if check_config.get("critical", False):
                    failed_critical.append(result.name)
                    
                # Fail-fast for critical failures in CI mode
                if self.mode == "ci" and check_config.get("critical", False):
                    self.logger.error(f"Critical check failed: {result.name}")
                    break
        
        total_duration = time.time() - self.start_time
        
        # Generate summary
        summary = {
            "total_checks": len(results),
            "passed_checks": sum(1 for r in results if r.passed),
            "failed_checks": sum(1 for r in results if not r.passed),
            "critical_failures": failed_critical,
            "pass_rate": sum(1 for r in results if r.passed) / len(results) if results else 0,
            "average_duration": sum(r.duration for r in results) / len(results) if results else 0
        }
        
        # Environment information
        environment = {
            "python_version": sys.version,
            "working_directory": str(self.project_root),
            "mode": self.mode,
            "timestamp": datetime.now().isoformat()
        }
        
        return QualityGateReport(
            timestamp=datetime.now().isoformat(),
            mode=self.mode,
            overall_passed=overall_passed,
            total_duration=total_duration,
            checks=results,
            summary=summary,
            environment=environment
        )
    
    def _format_console_output(self, report: QualityGateReport) -> str:
        """Format report for console output."""
        lines = []
        lines.append("=" * 80)
        lines.append(f"QUALITY GATES REPORT - {report.mode.upper()} MODE")
        lines.append("=" * 80)
        lines.append(f"Timestamp: {report.timestamp}")
        lines.append(f"Total Duration: {report.total_duration:.2f}s")
        lines.append(f"Overall Status: {'PASSED' if report.overall_passed else 'FAILED'}")
        lines.append("")
        
        # Summary statistics
        summary = report.summary
        lines.append("SUMMARY STATISTICS")
        lines.append("-" * 40)
        lines.append(f"Total Checks: {summary['total_checks']}")
        lines.append(f"Passed: {summary['passed_checks']} OK")
        lines.append(f"Failed: {summary['failed_checks']} FAIL")
        lines.append(f"Pass Rate: {summary['pass_rate']:.1%}")
        lines.append(f"Average Duration: {summary['average_duration']:.2f}s")
        lines.append("")
        
        # Individual check results
        lines.append("DETAILED RESULTS")
        lines.append("-" * 40)
        for check in report.checks:
            status = "OK" if check.passed else "FAIL"
            lines.append(f"{status} {check.name} ({check.duration:.2f}s)")
            if not check.passed and self.mode == "development":
                lines.append(f"   Error: {check.message}")
                if check.details.get("stderr"):
                    lines.append(f"   Details: {check.details['stderr'][:200]}...")
        
        # Critical failures
        if summary["critical_failures"]:
            lines.append("")
            lines.append("CRITICAL FAILURES")
            lines.append("-" * 40)
            for failure in summary["critical_failures"]:
                lines.append(f"FAIL {failure}")
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _save_json_report(self, report: QualityGateReport, filename: str = "quality_gates_report.json"):
        """Save report as JSON file."""
        report_dict = asdict(report)
        
        output_path = self.project_root / filename
        with open(output_path, "w") as f:
            json.dump(report_dict, f, indent=2, default=str)
        
        self.logger.info(f"JSON report saved to: {output_path}")
    
    def generate_output(self, report: QualityGateReport):
        """Generate output in the specified format."""
        if self.output_format in ["console", "both"]:
            console_output = self._format_console_output(report)
            print(console_output)
        
        if self.output_format in ["json", "both"]:
            self._save_json_report(report)
            if self.output_format == "json":
                # Also print JSON to stdout for CI integration
                print(json.dumps(asdict(report), indent=2, default=str))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Quality Gates Orchestrator for Candles Feed Project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--mode",
        choices=["development", "ci", "quick"],
        default="development",
        help="Execution mode (default: development)"
    )
    
    parser.add_argument(
        "--output",
        choices=["console", "json", "both"],
        default="console",
        help="Output format (default: console)"
    )
    
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to custom configuration file"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        orchestrator = QualityGatesOrchestrator(
            mode=args.mode,
            output_format=args.output
        )
        
        report = orchestrator.run_quality_gates()
        orchestrator.generate_output(report)
        
        # Exit with appropriate code
        sys.exit(0 if report.overall_passed else 1)
        
    except KeyboardInterrupt:
        print("\nQuality gates interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Quality gates failed with exception: {e}")
        logging.exception("Unexpected error in quality gates")
        sys.exit(1)


if __name__ == "__main__":
    main()