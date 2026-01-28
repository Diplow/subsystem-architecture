#!/usr/bin/env python3
"""
CLI entry point for Rule of 6 checking.

Usage:
    python3 -m scripts.checks.architecture.ruleof6.main [path]
    pnpm check:ruleof6 [path]
"""

import sys
import argparse

from .checker import RuleOf6Checker
from .reporter import RuleOf6Reporter


def main():
    """Main entry point for Rule of 6 checking."""
    parser = argparse.ArgumentParser(
        description="Rule of 6 Enforcement — validates subsystem count, functions per file, "
                    "function length, and argument count."
    )
    parser.add_argument(
        'target_path', nargs='?', default='src',
        help='Target directory to check (default: src)',
    )
    parser.add_argument(
        '--output', '-o',
        default='test-results/rule-of-6-check.json',
        help='Output file for detailed JSON report',
    )
    args = parser.parse_args()

    checker = RuleOf6Checker(args.target_path)
    results = checker.run_all_checks()

    reporter = RuleOf6Reporter(args.output)
    success = reporter.report_results(results)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
