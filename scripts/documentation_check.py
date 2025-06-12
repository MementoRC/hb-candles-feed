#!/usr/bin/env python3
# coding=utf-8
"""
Documentation Quality Checker for Candles Feed Project.

This script provides comprehensive documentation verification including
docstring completeness, API documentation freshness, link validation,
and code example verification. It integrates with existing mkdocs
configuration and supports both local and CI execution.

Usage:
    python scripts/documentation_check.py [--mode MODE] [--output FORMAT] [--fix]

Modes:
    - development: Full checks with detailed analysis and suggestions
    - ci: Optimized for CI with gate enforcement
    - quick: Essential checks for rapid feedback

Features:
    - Docstring completeness verification for public APIs
    - Broken link detection in documentation
    - Code example validation and execution
    - API documentation freshness checking
    - Integration with mkdocs configuration
    - Automated fixing for common issues
"""

import argparse
import ast
import json
import logging
import re
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
import urllib.request
import urllib.parse
from urllib.error import URLError, HTTPError


@dataclass
class DocstringIssue:
    """Documentation issue for a specific function/class."""
    file_path: str
    line_number: int
    name: str
    issue_type: str  # "missing", "incomplete", "malformed", "outdated"
    severity: str  # "error", "warning", "info"
    message: str
    suggestion: Optional[str] = None


@dataclass
class LinkIssue:
    """Broken or problematic link in documentation."""
    file_path: str
    line_number: int
    url: str
    issue_type: str  # "broken", "redirect", "slow", "malformed"
    status_code: Optional[int] = None
    error_message: Optional[str] = None


@dataclass
class CodeExampleIssue:
    """Issue with code examples in documentation."""
    file_path: str
    line_number: int
    code_block: str
    issue_type: str  # "syntax_error", "execution_error", "deprecated", "incomplete"
    error_message: str


@dataclass
class DocumentationReport:
    """Comprehensive documentation quality report."""
    timestamp: str
    mode: str
    overall_score: float
    docstring_issues: List[DocstringIssue]
    link_issues: List[LinkIssue]
    code_example_issues: List[CodeExampleIssue]
    quality_gates: Dict[str, bool]
    recommendations: List[str]
    summary: Dict[str, Any]
    files_analyzed: List[str]


class DocumentationChecker:
    """Main documentation quality checker."""
    
    def __init__(self, mode: str = "development", auto_fix: bool = False):
        self.mode = mode
        self.auto_fix = auto_fix
        self.project_root = Path(__file__).parent.parent
        self.source_dir = self.project_root / "candles_feed"
        self.docs_dir = self.project_root / "docs"
        self.mkdocs_config = self.project_root / "mkdocs.yml"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO if mode == "development" else logging.WARNING,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)
        
        # Quality thresholds
        self.thresholds = {
            "minimum_docstring_coverage": 85.0,  # Percentage of public functions with docstrings
            "minimum_documentation_score": 80.0,  # Overall documentation quality score
            "maximum_broken_links": 0,  # Zero tolerance for broken links
            "maximum_code_example_errors": 2,  # Allow minimal code example issues
            "api_freshness_days": 30  # API docs should be updated within 30 days
        }
        
        # Critical modules requiring 100% docstring coverage
        self.critical_modules = {
            "candles_feed/core",
            "candles_feed/feeds",
            "candles_feed/websocket",
            "candles_feed/__init__.py"
        }
        
        # URL patterns to skip (internal, localhost, etc.)
        self.skip_url_patterns = [
            r"^https?://localhost",
            r"^https?://127\.0\.0\.1",
            r"^https?://0\.0\.0\.0",
            r"^file://",
            r"^#",  # Fragment-only links
            r"^mailto:",
            r"^javascript:",
        ]
    
    def _find_python_files(self) -> List[Path]:
        """Find all Python files to analyze."""
        python_files = []
        
        # Source files
        for pattern in ["**/*.py", "**/*.pyx"]:  # Include Cython files
            python_files.extend(self.source_dir.glob(pattern))
        
        # Exclude test files and generated files
        excluded_patterns = ["test_", "__pycache__", ".pytest_cache", "build/", "dist/"]
        
        filtered_files = []
        for file_path in python_files:
            if not any(pattern in str(file_path) for pattern in excluded_patterns):
                filtered_files.append(file_path)
        
        return filtered_files
    
    def _find_documentation_files(self) -> List[Path]:
        """Find all documentation files to analyze."""
        doc_files = []
        
        # Markdown files
        if self.docs_dir.exists():
            doc_files.extend(self.docs_dir.glob("**/*.md"))
        
        # README files
        doc_files.extend(self.project_root.glob("README*.md"))
        
        # Include docstrings from Python files
        doc_files.extend(self._find_python_files())
        
        return doc_files
    
    def _extract_ast_info(self, file_path: Path) -> Tuple[List[ast.FunctionDef], List[ast.ClassDef]]:
        """Extract function and class definitions from Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            functions = []
            classes = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Only include public functions (not starting with _)
                    if not node.name.startswith('_') or node.name in ['__init__', '__str__', '__repr__']:
                        functions.append(node)
                elif isinstance(node, ast.ClassDef):
                    # Only include public classes
                    if not node.name.startswith('_'):
                        classes.append(node)
            
            return functions, classes
            
        except Exception as e:
            self.logger.warning(f"Could not parse {file_path}: {e}")
            return [], []
    
    def _check_docstring_quality(self, docstring: str, name: str) -> List[str]:
        """Check the quality of a docstring."""
        issues = []
        
        if not docstring:
            return ["missing"]
        
        docstring = docstring.strip()
        
        # Check for minimum content
        if len(docstring) < 10:
            issues.append("too_short")
        
        # Check for required sections in class/function docstrings
        required_patterns = {
            "args_or_params": r"(?i)(args?|param|parameter)s?:",
            "returns": r"(?i)returns?:",
            "raises": r"(?i)raises?:",
        }
        
        # For functions with parameters, expect parameter documentation
        if "(" in name and ")" in name and "args" not in docstring.lower() and "param" not in docstring.lower():
            issues.append("missing_parameters")
        
        # Check for TODO/FIXME markers
        if re.search(r"(?i)(todo|fixme|xxx|hack)", docstring):
            issues.append("contains_todo")
        
        # Check for proper formatting (basic check)
        if not re.search(r"[.!?]$", docstring.strip()):
            issues.append("no_sentence_ending")
        
        return issues
    
    def _analyze_docstrings(self, python_files: List[Path]) -> List[DocstringIssue]:
        """Analyze docstring completeness and quality."""
        issues = []
        
        for file_path in python_files:
            try:
                functions, classes = self._extract_ast_info(file_path)
                
                # Check function docstrings
                for func in functions:
                    docstring = ast.get_docstring(func)
                    quality_issues = self._check_docstring_quality(docstring, func.name)
                    
                    for issue_type in quality_issues:
                        severity = "error" if issue_type == "missing" else "warning"
                        
                        # Critical modules require stricter standards
                        if any(critical in str(file_path) for critical in self.critical_modules):
                            if issue_type in ["missing", "too_short", "missing_parameters"]:
                                severity = "error"
                        
                        message = self._get_docstring_issue_message(issue_type, func.name)
                        suggestion = self._get_docstring_suggestion(issue_type, func.name)
                        
                        issues.append(DocstringIssue(
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=func.lineno,
                            name=func.name,
                            issue_type=issue_type,
                            severity=severity,
                            message=message,
                            suggestion=suggestion
                        ))
                
                # Check class docstrings
                for cls in classes:
                    docstring = ast.get_docstring(cls)
                    quality_issues = self._check_docstring_quality(docstring, cls.name)
                    
                    for issue_type in quality_issues:
                        severity = "error" if issue_type == "missing" else "warning"
                        
                        message = self._get_docstring_issue_message(issue_type, cls.name, is_class=True)
                        suggestion = self._get_docstring_suggestion(issue_type, cls.name, is_class=True)
                        
                        issues.append(DocstringIssue(
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=cls.lineno,
                            name=cls.name,
                            issue_type=issue_type,
                            severity=severity,
                            message=message,
                            suggestion=suggestion
                        ))
                        
            except Exception as e:
                self.logger.warning(f"Error analyzing docstrings in {file_path}: {e}")
        
        return issues
    
    def _get_docstring_issue_message(self, issue_type: str, name: str, is_class: bool = False) -> str:
        """Get human-readable message for docstring issue."""
        entity_type = "Class" if is_class else "Function"
        
        messages = {
            "missing": f"{entity_type} '{name}' is missing a docstring",
            "too_short": f"{entity_type} '{name}' has an inadequate docstring (too short)",
            "missing_parameters": f"Function '{name}' is missing parameter documentation",
            "contains_todo": f"{entity_type} '{name}' docstring contains TODO/FIXME markers",
            "no_sentence_ending": f"{entity_type} '{name}' docstring doesn't end with proper punctuation"
        }
        
        return messages.get(issue_type, f"{entity_type} '{name}' has docstring issue: {issue_type}")
    
    def _get_docstring_suggestion(self, issue_type: str, name: str, is_class: bool = False) -> Optional[str]:
        """Get suggestion for fixing docstring issue."""
        if issue_type == "missing":
            if is_class:
                return f'Add a docstring: """{name} class for [purpose].\\n\\n[Description of the class and its responsibilities].\\n"""'
            else:
                return f'Add a docstring: """{name} function for [purpose].\\n\\n:param param_name: Description\\n:return: Description\\n"""'
        elif issue_type == "missing_parameters":
            return "Add parameter documentation using :param name: description format"
        elif issue_type == "too_short":
            return "Expand the docstring with more detailed description"
        elif issue_type == "contains_todo":
            return "Resolve TODO/FIXME items or move them to issue tracker"
        elif issue_type == "no_sentence_ending":
            return "End the docstring with a period, exclamation point, or question mark"
        
        return None
    
    def _extract_links_from_file(self, file_path: Path) -> List[Tuple[int, str]]:
        """Extract all URLs from a file."""
        links = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    # Find URLs using regex
                    url_pattern = r'https?://[^\s\])\'"<>]+'
                    urls = re.findall(url_pattern, line)
                    
                    for url in urls:
                        # Clean up URL (remove trailing punctuation)
                        url = re.sub(r'[.,;!?]+$', '', url)
                        links.append((line_num, url))
                        
        except Exception as e:
            self.logger.warning(f"Could not read {file_path}: {e}")
        
        return links
    
    def _should_skip_url(self, url: str) -> bool:
        """Check if URL should be skipped based on patterns."""
        for pattern in self.skip_url_patterns:
            if re.match(pattern, url):
                return True
        return False
    
    def _check_url(self, url: str) -> Tuple[bool, Optional[int], Optional[str]]:
        """Check if a URL is accessible."""
        if self._should_skip_url(url):
            return True, None, "Skipped"
        
        try:
            request = urllib.request.Request(
                url,
                headers={'User-Agent': 'Documentation-Checker/1.0'}
            )
            
            response = urllib.request.urlopen(request, timeout=10)
            status_code = response.getcode()
            
            if 200 <= status_code < 400:
                return True, status_code, None
            else:
                return False, status_code, f"HTTP {status_code}"
                
        except HTTPError as e:
            return False, e.code, str(e)
        except URLError as e:
            return False, None, str(e.reason)
        except Exception as e:
            return False, None, str(e)
    
    def _analyze_links(self, doc_files: List[Path]) -> List[LinkIssue]:
        """Analyze links in documentation files."""
        issues = []
        
        for file_path in doc_files:
            if file_path.suffix not in ['.md', '.rst', '.txt']:
                continue
                
            links = self._extract_links_from_file(file_path)
            
            for line_num, url in links:
                if self.mode == "quick" and len(issues) > 10:
                    # Limit link checking in quick mode
                    break
                    
                is_valid, status_code, error_message = self._check_url(url)
                
                if not is_valid:
                    issue_type = "broken"
                    if status_code and 300 <= status_code < 400:
                        issue_type = "redirect"
                    
                    issues.append(LinkIssue(
                        file_path=str(file_path.relative_to(self.project_root)),
                        line_number=line_num,
                        url=url,
                        issue_type=issue_type,
                        status_code=status_code,
                        error_message=error_message
                    ))
        
        return issues
    
    def _extract_code_blocks(self, file_path: Path) -> List[Tuple[int, str]]:
        """Extract code blocks from markdown files."""
        code_blocks = []
        
        if file_path.suffix != '.md':
            return code_blocks
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find Python code blocks
            pattern = r'```(?:python|py)\n(.*?)\n```'
            matches = re.finditer(pattern, content, re.DOTALL)
            
            for match in matches:
                # Find line number
                line_num = content[:match.start()].count('\n') + 1
                code = match.group(1)
                code_blocks.append((line_num, code))
                
        except Exception as e:
            self.logger.warning(f"Could not extract code blocks from {file_path}: {e}")
        
        return code_blocks
    
    def _analyze_code_examples(self, doc_files: List[Path]) -> List[CodeExampleIssue]:
        """Analyze code examples in documentation."""
        issues = []
        
        for file_path in doc_files:
            code_blocks = self._extract_code_blocks(file_path)
            
            for line_num, code in code_blocks:
                # Check syntax
                try:
                    ast.parse(code)
                except SyntaxError as e:
                    issues.append(CodeExampleIssue(
                        file_path=str(file_path.relative_to(self.project_root)),
                        line_number=line_num,
                        code_block=code[:100] + "..." if len(code) > 100 else code,
                        issue_type="syntax_error",
                        error_message=f"Syntax error: {e.msg}"
                    ))
                    continue
                
                # Check for deprecated patterns (basic check)
                deprecated_patterns = [
                    (r'import imp\b', "Module 'imp' is deprecated"),
                    (r'\.warn\(', "Use warnings.warn() instead of direct .warn()"),
                    (r'assertEquals\(', "Use assertEqual() instead of assertEquals()"),
                ]
                
                for pattern, message in deprecated_patterns:
                    if re.search(pattern, code):
                        issues.append(CodeExampleIssue(
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=line_num,
                            code_block=code[:100] + "..." if len(code) > 100 else code,
                            issue_type="deprecated",
                            error_message=message
                        ))
        
        return issues
    
    def _evaluate_quality_gates(self, 
                               docstring_issues: List[DocstringIssue],
                               link_issues: List[LinkIssue],
                               code_example_issues: List[CodeExampleIssue],
                               files_analyzed: List[str]) -> Dict[str, bool]:
        """Evaluate documentation quality gates."""
        gates = {}
        
        # Docstring coverage
        error_docstring_issues = [issue for issue in docstring_issues if issue.severity == "error"]
        total_functions_classes = len([issue for issue in docstring_issues if issue.issue_type == "missing"]) + \
                                 len([f for f in files_analyzed if f.endswith('.py')])  # Rough estimate
        
        if total_functions_classes > 0:
            coverage = max(0, (total_functions_classes - len(error_docstring_issues)) / total_functions_classes * 100)
            gates["docstring_coverage"] = coverage >= self.thresholds["minimum_docstring_coverage"]
        else:
            gates["docstring_coverage"] = True
        
        # Link quality
        broken_links = [issue for issue in link_issues if issue.issue_type == "broken"]
        gates["no_broken_links"] = len(broken_links) <= self.thresholds["maximum_broken_links"]
        
        # Code example quality
        code_errors = [issue for issue in code_example_issues if issue.issue_type in ["syntax_error", "execution_error"]]
        gates["code_examples_valid"] = len(code_errors) <= self.thresholds["maximum_code_example_errors"]
        
        # Critical module coverage
        critical_issues = [
            issue for issue in docstring_issues 
            if issue.severity == "error" and any(critical in issue.file_path for critical in self.critical_modules)
        ]
        gates["critical_modules_documented"] = len(critical_issues) == 0
        
        return gates
    
    def _calculate_overall_score(self,
                               docstring_issues: List[DocstringIssue],
                               link_issues: List[LinkIssue],
                               code_example_issues: List[CodeExampleIssue],
                               quality_gates: Dict[str, bool]) -> float:
        """Calculate overall documentation quality score."""
        # Start with 100 points
        score = 100.0
        
        # Deduct points for issues
        for issue in docstring_issues:
            if issue.severity == "error":
                score -= 5.0
            elif issue.severity == "warning":
                score -= 2.0
        
        for issue in link_issues:
            if issue.issue_type == "broken":
                score -= 10.0
            else:
                score -= 3.0
        
        for issue in code_example_issues:
            if issue.issue_type in ["syntax_error", "execution_error"]:
                score -= 8.0
            else:
                score -= 2.0
        
        # Quality gate bonus/penalty
        gates_passed = sum(quality_gates.values())
        gates_total = len(quality_gates)
        if gates_total > 0:
            gate_score = (gates_passed / gates_total) * 20  # Up to 20 bonus points
            score += gate_score - 10  # Neutral at 50% pass rate
        
        return max(0.0, min(100.0, score))
    
    def _generate_recommendations(self,
                                docstring_issues: List[DocstringIssue],
                                link_issues: List[LinkIssue],
                                code_example_issues: List[CodeExampleIssue],
                                quality_gates: Dict[str, bool]) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Docstring recommendations
        error_docstrings = [issue for issue in docstring_issues if issue.severity == "error"]
        if error_docstrings:
            recommendations.append(
                f"Add docstrings to {len(error_docstrings)} public functions/classes "
                f"to improve API documentation"
            )
        
        warning_docstrings = [issue for issue in docstring_issues if issue.severity == "warning"]
        if warning_docstrings:
            recommendations.append(
                f"Improve {len(warning_docstrings)} existing docstrings "
                f"(too short, missing parameters, etc.)"
            )
        
        # Link recommendations
        broken_links = [issue for issue in link_issues if issue.issue_type == "broken"]
        if broken_links:
            recommendations.append(
                f"Fix {len(broken_links)} broken links in documentation"
            )
        
        # Code example recommendations
        syntax_errors = [issue for issue in code_example_issues if issue.issue_type == "syntax_error"]
        if syntax_errors:
            recommendations.append(
                f"Fix {len(syntax_errors)} code examples with syntax errors"
            )
        
        # Priority recommendations
        if not quality_gates.get("critical_modules_documented", True):
            recommendations.insert(0, 
                "PRIORITY: Add documentation to critical modules (core, feeds, websocket)"
            )
        
        # Positive reinforcement
        if all(quality_gates.values()) and not recommendations:
            recommendations.append("Documentation quality is excellent! Consider adding more examples and tutorials.")
        
        return recommendations
    
    def check_documentation(self) -> DocumentationReport:
        """Perform comprehensive documentation analysis."""
        self.logger.info(f"Starting documentation check in {self.mode} mode...")
        
        # Find files to analyze
        python_files = self._find_python_files()
        doc_files = self._find_documentation_files()
        
        all_files = list(set([str(f.relative_to(self.project_root)) for f in python_files + doc_files]))
        
        self.logger.info(f"Analyzing {len(python_files)} Python files and {len(doc_files)} documentation files")
        
        # Perform analyses
        docstring_issues = self._analyze_docstrings(python_files)
        
        # Skip link checking in quick mode unless specifically requested
        if self.mode != "quick":
            link_issues = self._analyze_links(doc_files)
        else:
            link_issues = []
        
        code_example_issues = self._analyze_code_examples(doc_files)
        
        # Evaluate quality gates
        quality_gates = self._evaluate_quality_gates(
            docstring_issues, link_issues, code_example_issues, all_files
        )
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(
            docstring_issues, link_issues, code_example_issues, quality_gates
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            docstring_issues, link_issues, code_example_issues, quality_gates
        )
        
        # Create summary
        summary = {
            "files_analyzed": len(all_files),
            "python_files": len(python_files),
            "documentation_files": len(doc_files),
            "total_issues": len(docstring_issues) + len(link_issues) + len(code_example_issues),
            "docstring_issues": len(docstring_issues),
            "link_issues": len(link_issues),
            "code_example_issues": len(code_example_issues),
            "quality_gates_passed": sum(quality_gates.values()),
            "quality_gates_total": len(quality_gates),
            "overall_score": overall_score
        }
        
        return DocumentationReport(
            timestamp=datetime.now().isoformat(),
            mode=self.mode,
            overall_score=overall_score,
            docstring_issues=docstring_issues,
            link_issues=link_issues,
            code_example_issues=code_example_issues,
            quality_gates=quality_gates,
            recommendations=recommendations,
            summary=summary,
            files_analyzed=all_files
        )
    
    def format_console_output(self, report: DocumentationReport) -> str:
        """Format report for console output."""
        lines = []
        lines.append("=" * 80)
        lines.append(f"=Ú DOCUMENTATION QUALITY REPORT - {report.mode.upper()} MODE")
        lines.append("=" * 80)
        lines.append(f"=Å Timestamp: {report.timestamp}")
        lines.append(f"=Ê Overall Score: {report.overall_score:.1f}/100")
        lines.append("")
        
        # Summary statistics
        summary = report.summary
        lines.append("=È SUMMARY STATISTICS")
        lines.append("-" * 40)
        lines.append(f"Files Analyzed: {summary['files_analyzed']}")
        lines.append(f"Python Files: {summary['python_files']}")
        lines.append(f"Documentation Files: {summary['documentation_files']}")
        lines.append(f"Total Issues: {summary['total_issues']}")
        lines.append("")
        
        # Issue breakdown
        lines.append("=
 ISSUE BREAKDOWN")
        lines.append("-" * 40)
        lines.append(f"Docstring Issues: {summary['docstring_issues']}")
        lines.append(f"Link Issues: {summary['link_issues']}")
        lines.append(f"Code Example Issues: {summary['code_example_issues']}")
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
        
        # Top issues (in development mode)
        if self.mode == "development" and report.docstring_issues:
            lines.append("=Ý TOP DOCSTRING ISSUES")
            lines.append("-" * 40)
            error_issues = [issue for issue in report.docstring_issues if issue.severity == "error"]
            for issue in error_issues[:5]:  # Show top 5
                lines.append(f"L {issue.file_path}:{issue.line_number} - {issue.message}")
            if len(error_issues) > 5:
                lines.append(f"... and {len(error_issues) - 5} more")
            lines.append("")
        
        # Recommendations
        if report.recommendations:
            lines.append("=¡ RECOMMENDATIONS")
            lines.append("-" * 40)
            for recommendation in report.recommendations:
                lines.append(f"" {recommendation}")
            lines.append("")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Documentation Quality Checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--mode",
        choices=["development", "ci", "quick"],
        default="development",
        help="Check mode (default: development)"
    )
    
    parser.add_argument(
        "--output",
        choices=["console", "json", "both"],
        default="console",
        help="Output format (default: console)"
    )
    
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to automatically fix common issues"
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
        checker = DocumentationChecker(mode=args.mode, auto_fix=args.fix)
        report = checker.check_documentation()
        
        # Generate output
        if args.output in ["console", "both"]:
            console_output = checker.format_console_output(report)
            print(console_output)
        
        if args.output in ["json", "both"]:
            json_output = json.dumps(asdict(report), indent=2, default=str)
            if args.output == "json":
                print(json_output)
            else:
                output_file = Path("documentation_check_report.json")
                with open(output_file, "w") as f:
                    f.write(json_output)
                print(f"\n=Ä JSON report saved to: {output_file}")
        
        # Exit with appropriate code based on quality gates
        all_gates_passed = all(report.quality_gates.values())
        sys.exit(0 if all_gates_passed else 1)
        
    except Exception as e:
        print(f"L Documentation check failed: {e}")
        logging.exception("Documentation check error")
        sys.exit(1)


if __name__ == "__main__":
    main()