#!/usr/bin/env python3
"""
Rule of 6 check reporting.

Handles console output and JSON report generation.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from ..models import ArchError, CheckResults, ErrorType, Severity


# Display order and section titles for violation types
_SECTION_ORDER = [
    (ErrorType.SUBSYSTEM_COUNT, "Subsystems Per Parent"),
    (ErrorType.FILE_FUNCTIONS, "Functions Per File"),
    (ErrorType.FUNCTION_LINES, "Function Line Count"),
    (ErrorType.FUNCTION_ARGS, "Function Arguments / Object Keys"),
]


class RuleOf6Reporter:
    """Handles reporting of Rule of 6 check results."""

    def __init__(self, output_file: str = "test-results/rule-of-6-check.json"):
        self.output_file = Path(output_file)

    def report_results(self, results: CheckResults) -> bool:
        """Report results to both JSON file and console. Returns True if no errors."""
        self.output_file.parent.mkdir(exist_ok=True)
        self._write_json_report(results)
        self._display_console_summary(results)
        return not results.has_errors()

    # ------------------------------------------------------------------
    # JSON report
    # ------------------------------------------------------------------

    def _write_json_report(self, results: CheckResults) -> None:
        """Write detailed JSON report to file."""
        report_data = results.to_dict()
        report_data["timestamp"] = datetime.now().isoformat()
        with open(self.output_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)

    # ------------------------------------------------------------------
    # Console summary
    # ------------------------------------------------------------------

    def _display_console_summary(self, results: CheckResults) -> None:
        """Display concise summary information on console."""
        total_errors = len(results.errors)
        total_warnings = len(results.warnings)

        if total_errors > 0 or total_warnings > 0:
            print(f"Rule of 6: {total_errors} errors, {total_warnings} warnings")
            print()
            self._display_top_violations(results)
            print(f"Detailed report: {self.output_file}")
        else:
            print("Rule of 6 checks passed!")
            print(f"Detailed report: {self.output_file}")

    def _display_top_violations(self, results: CheckResults) -> None:
        """Display top 10 violations for each violation type."""
        all_issues = results.get_all_issues()

        # Group by error type
        by_type: Dict[ErrorType, List[ArchError]] = {}
        for issue in all_issues:
            by_type.setdefault(issue.error_type, []).append(issue)

        for error_type, section_title in _SECTION_ORDER:
            violations = by_type.get(error_type)
            if not violations:
                continue

            # Sort by severity (errors first) then by message
            sorted_violations = sorted(
                violations,
                key=lambda v: (0 if v.severity == Severity.ERROR else 1, v.message),
            )

            print(section_title)
            print("=" * len(section_title))

            for i, violation in enumerate(sorted_violations[:10], 1):
                severity_icon = "E" if violation.severity == Severity.ERROR else "W"
                location = ""
                if violation.file_path and violation.line_number:
                    location = f"  {violation.file_path}:{violation.line_number}"
                elif violation.file_path:
                    location = f"  {violation.file_path}"
                elif violation.subsystem:
                    location = f"  {violation.subsystem}"

                print(f"{i:2}. [{severity_icon}] {violation.message}")
                if location:
                    print(f"    {location}")

            if len(sorted_violations) > 10:
                print(f"     ... and {len(sorted_violations) - 10} more")

            print()
