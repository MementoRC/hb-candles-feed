#!/usr/bin/env python3
"""
Coverage Analysis with Trend Tracking for Candles Feed Project.

This script provides comprehensive test coverage analysis with trend tracking,
baseline comparison, regression detection, and detailed reporting capabilities.
It integrates with the existing CI infrastructure and supports both local and
automated execution.

Usage:
    python scripts/coverage_analysis.py [--mode MODE] [--baseline FILE] [--output FORMAT]

Modes:
    - development: Detailed analysis with trends and recommendations
    - ci: Optimized for CI with gate enforcement
    - baseline: Generate new baseline for future comparisons

Features:
    - Coverage trend analysis and regression detection
    - Module-level coverage breakdown and analysis
    - Integration with existing coverage.xml reports
    - Baseline comparison and drift analysis
    - Quality gate enforcement with configurable thresholds
    - JSON output for CI integration
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
from typing import Dict, List, Optional, Any, Tuple
import xml.etree.ElementTree as ET


@dataclass
class CoverageMetrics:
    """Coverage metrics for a module or overall project."""
    line_rate: float
    branch_rate: float
    lines_covered: int
    lines_valid: int
    branches_covered: int
    branches_valid: int
    complexity: int = 0


@dataclass
class ModuleCoverage:
    """Coverage information for a specific module."""
    name: str
    filename: str
    metrics: CoverageMetrics
    missing_lines: List[int]
    critical_missing: List[int]  # Missing lines in critical functions


@dataclass
class CoverageTrend:
    """Coverage trend analysis between two time points."""
    metric_name: str
    current_value: float
    previous_value: Optional[float]
    change: Optional[float]
    change_percentage: Optional[float]
    trend_direction: str  # "improving", "declining", "stable", "unknown"


@dataclass
class CoverageReport:
    """Comprehensive coverage analysis report."""
    timestamp: str
    mode: str
    overall_metrics: CoverageMetrics
    modules: List[ModuleCoverage]
    trends: List[CoverageTrend]
    quality_gates: Dict[str, bool]
    recommendations: List[str]
    baseline_comparison: Optional[Dict[str, Any]]
    summary: Dict[str, Any]


class CoverageAnalyzer:
    """Main coverage analyzer with trend tracking."""
    
    def __init__(self, mode: str = "development", baseline_file: Optional[Path] = None):
        self.mode = mode
        self.baseline_file = baseline_file
        self.project_root = Path(__file__).parent.parent
        self.coverage_file = self.project_root / "coverage.xml"
        self.baseline_dir = self.project_root / ".coverage_baselines"
        self.baseline_dir.mkdir(exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO if mode == "development" else logging.WARNING,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)
        
        # Quality gate thresholds
        self.thresholds = {
            "minimum_line_coverage": 75.0,  # Based on current 75.7% coverage
            "minimum_branch_coverage": 45.0,  # Based on current 46.38% coverage
            "coverage_regression_threshold": 2.0,  # Max allowed regression percentage
            "critical_module_threshold": 80.0,  # Threshold for critical modules
            "new_code_threshold": 85.0  # Higher standard for new code
        }
        
        # Critical modules that require higher coverage
        self.critical_modules = {
            "candles_feed/core",
            "candles_feed/feeds",
            "candles_feed/websocket",
            "candles_feed/data_sources"
        }
    
    def _run_coverage_collection(self) -> bool:
        """Run test suite with coverage collection."""
        try:
            self.logger.info("Running test suite with coverage collection...")
            
            # Run pytest with coverage
            result = subprocess.run(
                ["pixi", "run", "test", "--cov=candles_feed", "--cov-report=xml", "--cov-report=term"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode != 0:
                self.logger.error(f"Test execution failed: {result.stderr}")
                return False
            
            self.logger.info(" Coverage collection completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Coverage collection failed: {e}")
            return False
    
    def _parse_coverage_xml(self) -> Tuple[CoverageMetrics, List[ModuleCoverage]]:
        """Parse coverage.xml file and extract metrics."""
        if not self.coverage_file.exists():
            raise FileNotFoundError(f"Coverage file not found: {self.coverage_file}")
        
        tree = ET.parse(self.coverage_file)
        root = tree.getroot()
        
        # Extract overall metrics
        overall_metrics = CoverageMetrics(
            line_rate=float(root.get("line-rate", 0)),
            branch_rate=float(root.get("branch-rate", 0)),
            lines_covered=int(root.get("lines-covered", 0)),
            lines_valid=int(root.get("lines-valid", 0)),
            branches_covered=int(root.get("branches-covered", 0)),
            branches_valid=int(root.get("branches-valid", 0)),
            complexity=int(root.get("complexity", 0))
        )
        
        # Extract module-level metrics
        modules = []
        for package in root.findall(".//package"):
            package_name = package.get("name", "unknown")
            
            for class_elem in package.findall("classes/class"):
                filename = class_elem.get("filename", "unknown")
                class_name = class_elem.get("name", "unknown")
                
                # Calculate metrics for this class/module
                lines = class_elem.findall("lines/line")
                covered_lines = [int(line.get("number")) for line in lines if int(line.get("hits", 0)) > 0]
                missing_lines = [int(line.get("number")) for line in lines if int(line.get("hits", 0)) == 0]
                
                if lines:
                    line_rate = len(covered_lines) / len(lines)
                    
                    # Identify critical missing lines (simplified heuristic)
                    critical_missing = self._identify_critical_missing_lines(missing_lines, filename)
                    
                    module_metrics = CoverageMetrics(
                        line_rate=line_rate,
                        branch_rate=float(class_elem.get("branch-rate", 0)),
                        lines_covered=len(covered_lines),
                        lines_valid=len(lines),
                        branches_covered=0,  # Would need more complex parsing
                        branches_valid=0,
                        complexity=int(class_elem.get("complexity", 0))
                    )
                    
                    module = ModuleCoverage(
                        name=f"{package_name}/{class_name}",
                        filename=filename,
                        metrics=module_metrics,
                        missing_lines=missing_lines,
                        critical_missing=critical_missing
                    )
                    modules.append(module)
        
        return overall_metrics, modules
    
    def _identify_critical_missing_lines(self, missing_lines: List[int], filename: str) -> List[int]:
        """Identify missing lines in critical functions (simplified heuristic)."""
        # This is a simplified implementation
        # In practice, you'd analyze the AST to identify critical functions
        critical_patterns = ["def __init__", "async def", "def process", "def handle"]
        
        try:
            source_file = self.project_root / filename
            if source_file.exists():
                with open(source_file, 'r') as f:
                    lines = f.readlines()
                
                critical_missing = []
                for line_num in missing_lines:
                    if line_num <= len(lines):
                        line_content = lines[line_num - 1].strip()
                        if any(pattern in line_content for pattern in critical_patterns):
                            critical_missing.append(line_num)
                
                return critical_missing
        except Exception:
            pass
        
        return []
    
    def _load_baseline(self, baseline_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        """Load baseline coverage data for comparison."""
        if baseline_path is None:
            # Try to find the most recent baseline
            baseline_files = list(self.baseline_dir.glob("baseline_*.json"))
            if not baseline_files:
                return None
            baseline_path = max(baseline_files, key=lambda p: p.stat().st_mtime)
        
        try:
            with open(baseline_path, 'r') as f:
                baseline_data = json.load(f)
            self.logger.info(f"Loaded baseline from: {baseline_path}")
            return baseline_data
        except Exception as e:
            self.logger.warning(f"Could not load baseline: {e}")
            return None
    
    def _save_baseline(self, metrics: CoverageMetrics, modules: List[ModuleCoverage]):
        """Save current coverage as baseline."""
        baseline_data = {
            "timestamp": datetime.now().isoformat(),
            "overall_metrics": asdict(metrics),
            "modules": {module.name: asdict(module.metrics) for module in modules}
        }
        
        baseline_file = self.baseline_dir / f"baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(baseline_file, 'w') as f:
            json.dump(baseline_data, f, indent=2)
        
        self.logger.info(f"Baseline saved to: {baseline_file}")
    
    def _calculate_trends(self, current_metrics: CoverageMetrics, baseline_data: Optional[Dict[str, Any]]) -> List[CoverageTrend]:
        """Calculate coverage trends compared to baseline."""
        trends = []
        
        if baseline_data is None:
            # No baseline data available
            trend_metrics = [
                ("Line Coverage", current_metrics.line_rate * 100),
                ("Branch Coverage", current_metrics.branch_rate * 100)
            ]
            
            for metric_name, current_value in trend_metrics:
                trends.append(CoverageTrend(
                    metric_name=metric_name,
                    current_value=current_value,
                    previous_value=None,
                    change=None,
                    change_percentage=None,
                    trend_direction="unknown"
                ))
        else:
            # Compare with baseline
            baseline_metrics = baseline_data["overall_metrics"]
            
            comparisons = [
                ("Line Coverage", current_metrics.line_rate * 100, baseline_metrics["line_rate"] * 100),
                ("Branch Coverage", current_metrics.branch_rate * 100, baseline_metrics["branch_rate"] * 100)
            ]
            
            for metric_name, current_value, previous_value in comparisons:
                change = current_value - previous_value
                change_percentage = (change / previous_value * 100) if previous_value > 0 else 0
                
                if abs(change_percentage) < 0.5:
                    trend_direction = "stable"
                elif change_percentage > 0:
                    trend_direction = "improving"
                else:
                    trend_direction = "declining"
                
                trends.append(CoverageTrend(
                    metric_name=metric_name,
                    current_value=current_value,
                    previous_value=previous_value,
                    change=change,
                    change_percentage=change_percentage,
                    trend_direction=trend_direction
                ))
        
        return trends
    
    def _evaluate_quality_gates(self, metrics: CoverageMetrics, trends: List[CoverageTrend], modules: List[ModuleCoverage]) -> Dict[str, bool]:
        """Evaluate quality gates based on thresholds."""
        gates = {}
        
        # Overall coverage thresholds
        gates["minimum_line_coverage"] = (metrics.line_rate * 100) >= self.thresholds["minimum_line_coverage"]
        gates["minimum_branch_coverage"] = (metrics.branch_rate * 100) >= self.thresholds["minimum_branch_coverage"]
        
        # Regression check
        line_trend = next((t for t in trends if t.metric_name == "Line Coverage"), None)
        if line_trend and line_trend.change_percentage is not None:
            gates["no_coverage_regression"] = line_trend.change_percentage >= -self.thresholds["coverage_regression_threshold"]
        else:
            gates["no_coverage_regression"] = True  # No baseline to compare
        
        # Critical modules check
        critical_modules_ok = True
        for module in modules:
            if any(critical_path in module.name for critical_path in self.critical_modules):
                if (module.metrics.line_rate * 100) < self.thresholds["critical_module_threshold"]:
                    critical_modules_ok = False
                    break
        gates["critical_modules_coverage"] = critical_modules_ok
        
        return gates
    
    def _generate_recommendations(self, metrics: CoverageMetrics, modules: List[ModuleCoverage], gates: Dict[str, bool]) -> List[str]:
        """Generate actionable recommendations for improving coverage."""
        recommendations = []
        
        # Overall coverage recommendations
        if not gates["minimum_line_coverage"]:
            current_coverage = metrics.line_rate * 100
            gap = self.thresholds["minimum_line_coverage"] - current_coverage
            recommendations.append(
                f"=È Increase overall line coverage by {gap:.1f}% to meet minimum threshold "
                f"(current: {current_coverage:.1f}%, target: {self.thresholds['minimum_line_coverage']:.1f}%)"
            )
        
        if not gates["minimum_branch_coverage"]:
            current_coverage = metrics.branch_rate * 100
            gap = self.thresholds["minimum_branch_coverage"] - current_coverage
            recommendations.append(
                f"<? Improve branch coverage by {gap:.1f}% to meet minimum threshold "
                f"(current: {current_coverage:.1f}%, target: {self.thresholds['minimum_branch_coverage']:.1f}%)"
            )
        
        # Module-specific recommendations
        low_coverage_modules = [
            module for module in modules 
            if (module.metrics.line_rate * 100) < 70.0  # Below 70% threshold
        ]
        
        if low_coverage_modules:
            low_coverage_modules.sort(key=lambda m: m.metrics.line_rate)
            recommendations.append(
                f"<¯ Focus on improving coverage in {len(low_coverage_modules)} modules with coverage below 70%"
            )
            
            for module in low_coverage_modules[:3]:  # Top 3 worst modules
                coverage_pct = module.metrics.line_rate * 100
                recommendations.append(
                    f"   " {module.name}: {coverage_pct:.1f}% coverage "
                    f"({len(module.missing_lines)} uncovered lines)"
                )
        
        # Critical missing lines
        critical_missing_total = sum(len(module.critical_missing) for module in modules)
        if critical_missing_total > 0:
            recommendations.append(
                f"=¨ Address {critical_missing_total} missing lines in critical functions"
            )
        
        # Positive reinforcement
        if all(gates.values()):
            recommendations.append("<‰ All quality gates passed! Consider raising coverage targets for continuous improvement.")
        
        return recommendations
    
    def analyze_coverage(self) -> CoverageReport:
        """Perform comprehensive coverage analysis."""
        self.logger.info(f"Starting coverage analysis in {self.mode} mode...")
        
        # Run coverage collection if in development or CI mode
        if self.mode in ["development", "ci"]:
            if not self._run_coverage_collection():
                raise RuntimeError("Coverage collection failed")
        
        # Parse coverage data
        overall_metrics, modules = self._parse_coverage_xml()
        
        # Load baseline for comparison
        baseline_data = self._load_baseline(self.baseline_file)
        
        # Calculate trends
        trends = self._calculate_trends(overall_metrics, baseline_data)
        
        # Evaluate quality gates
        quality_gates = self._evaluate_quality_gates(overall_metrics, trends, modules)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(overall_metrics, modules, quality_gates)
        
        # Create baseline comparison summary
        baseline_comparison = None
        if baseline_data:
            baseline_comparison = {
                "baseline_timestamp": baseline_data.get("timestamp"),
                "line_coverage_change": next((t.change for t in trends if t.metric_name == "Line Coverage"), 0),
                "branch_coverage_change": next((t.change for t in trends if t.metric_name == "Branch Coverage"), 0)
            }
        
        # Generate summary statistics
        summary = {
            "total_modules": len(modules),
            "modules_above_threshold": sum(1 for m in modules if (m.metrics.line_rate * 100) >= 70),
            "critical_modules_count": sum(1 for m in modules if any(cp in m.name for cp in self.critical_modules)),
            "total_missing_lines": sum(len(m.missing_lines) for m in modules),
            "critical_missing_lines": sum(len(m.critical_missing) for m in modules),
            "quality_gates_passed": sum(quality_gates.values()),
            "quality_gates_total": len(quality_gates),
            "overall_quality_score": (sum(quality_gates.values()) / len(quality_gates)) * 100 if quality_gates else 0
        }
        
        # Save baseline if in baseline mode
        if self.mode == "baseline":
            self._save_baseline(overall_metrics, modules)
        
        return CoverageReport(
            timestamp=datetime.now().isoformat(),
            mode=self.mode,
            overall_metrics=overall_metrics,
            modules=modules,
            trends=trends,
            quality_gates=quality_gates,
            recommendations=recommendations,
            baseline_comparison=baseline_comparison,
            summary=summary
        )
    
    def format_console_output(self, report: CoverageReport) -> str:
        """Format report for console output."""
        lines = []
        lines.append("=" * 80)
        lines.append(f"=Ê COVERAGE ANALYSIS REPORT - {report.mode.upper()} MODE")
        lines.append("=" * 80)
        lines.append(f"=Å Timestamp: {report.timestamp}")
        lines.append("")
        
        # Overall metrics
        metrics = report.overall_metrics
        lines.append("=È OVERALL COVERAGE METRICS")
        lines.append("-" * 40)
        lines.append(f"Line Coverage:   {metrics.line_rate * 100:6.2f}% ({metrics.lines_covered:,}/{metrics.lines_valid:,} lines)")
        lines.append(f"Branch Coverage: {metrics.branch_rate * 100:6.2f}% ({metrics.branches_covered:,}/{metrics.branches_valid:,} branches)")
        lines.append("")
        
        # Trends
        if report.trends:
            lines.append("=Ê COVERAGE TRENDS")
            lines.append("-" * 40)
            for trend in report.trends:
                if trend.change is not None:
                    direction_icon = {"improving": "=È", "declining": "=É", "stable": "¡"}.get(trend.trend_direction, "S")
                    lines.append(f"{direction_icon} {trend.metric_name}: {trend.current_value:.2f}% "
                               f"({trend.change:+.2f}% from baseline)")
                else:
                    lines.append(f"S {trend.metric_name}: {trend.current_value:.2f}% (no baseline)")
            lines.append("")
        
        # Quality gates
        lines.append("=¦ QUALITY GATES")
        lines.append("-" * 40)
        for gate_name, passed in report.quality_gates.items():
            status = "" if passed else "L"
            readable_name = gate_name.replace("_", " ").title()
            lines.append(f"{status} {readable_name}")
        
        overall_status = " PASSED" if all(report.quality_gates.values()) else "L FAILED"
        lines.append(f"\nOverall Quality Gates: {overall_status}")
        lines.append("")
        
        # Recommendations
        if report.recommendations:
            lines.append("=¡ RECOMMENDATIONS")
            lines.append("-" * 40)
            for recommendation in report.recommendations:
                lines.append(f"" {recommendation}")
            lines.append("")
        
        # Summary
        summary = report.summary
        lines.append("=Ë SUMMARY STATISTICS")
        lines.append("-" * 40)
        lines.append(f"Total Modules: {summary['total_modules']}")
        lines.append(f"Modules Above 70% Coverage: {summary['modules_above_threshold']}")
        lines.append(f"Critical Modules: {summary['critical_modules_count']}")
        lines.append(f"Missing Lines: {summary['total_missing_lines']:,}")
        lines.append(f"Critical Missing Lines: {summary['critical_missing_lines']}")
        lines.append(f"Quality Score: {summary['overall_quality_score']:.1f}%")
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Coverage Analysis with Trend Tracking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--mode",
        choices=["development", "ci", "baseline"],
        default="development",
        help="Analysis mode (default: development)"
    )
    
    parser.add_argument(
        "--baseline",
        type=Path,
        help="Path to baseline coverage file for comparison"
    )
    
    parser.add_argument(
        "--output",
        choices=["console", "json", "both"],
        default="console",
        help="Output format (default: console)"
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
        analyzer = CoverageAnalyzer(mode=args.mode, baseline_file=args.baseline)
        report = analyzer.analyze_coverage()
        
        # Generate output
        if args.output in ["console", "both"]:
            console_output = analyzer.format_console_output(report)
            print(console_output)
        
        if args.output in ["json", "both"]:
            json_output = json.dumps(asdict(report), indent=2, default=str)
            if args.output == "json":
                print(json_output)
            else:
                output_file = Path("coverage_analysis_report.json")
                with open(output_file, "w") as f:
                    f.write(json_output)
                print(f"\n=Ä JSON report saved to: {output_file}")
        
        # Exit with appropriate code based on quality gates
        all_gates_passed = all(report.quality_gates.values())
        sys.exit(0 if all_gates_passed else 1)
        
    except Exception as e:
        print(f"L Coverage analysis failed: {e}")
        logging.exception("Coverage analysis error")
        sys.exit(1)


if __name__ == "__main__":
    main()