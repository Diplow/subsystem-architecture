#!/usr/bin/env python3
"""
Rule of 6 checker orchestrator.

Discovers subsystems and runs all Rule of 6 checks.
"""

import json
import time
from pathlib import Path
from typing import List

from ..models import CheckResults, SubsystemInfo, FileInfo
from ..utils.file_utils import FileCache, is_test_file
from ..utils.exception_handler import RuleOf6ExceptionHandler
from .rules import RuleOf6Rules


class RuleOf6Checker:
    """Orchestrates Rule of 6 checks across the codebase."""

    def __init__(self, target_path: str = "src"):
        self.target_path = Path(target_path)
        self.file_cache = FileCache()

        # Find project root
        project_root = self._find_project_root(self.target_path)

        # Set up exception handling
        self.exception_handler = RuleOf6ExceptionHandler(project_root)
        self.exception_handler.load_exceptions(self.target_path)

        # Set up rules
        self.rules = RuleOf6Rules(self.file_cache, self.exception_handler)

    def run_all_checks(self) -> CheckResults:
        """Run all Rule of 6 checks and return results."""
        start_time = time.time()
        results = CheckResults(target_path=str(self.target_path))

        # Discover subsystems (same approach as architecture checker)
        subsystems = self._find_all_subsystems()

        # Run all checks
        for error in self.rules.check_subsystem_count(subsystems):
            results.add_error(error)

        for error in self.rules.check_file_functions(subsystems):
            results.add_error(error)

        for error in self.rules.check_object_parameter_keys(subsystems):
            results.add_error(error)

        results.execution_time = time.time() - start_time
        return results

    def _find_all_subsystems(self) -> List[SubsystemInfo]:
        """Find all subsystems in target path."""
        subsystems = []

        for deps_file in sorted(self.target_path.rglob("dependencies.json")):
            subsystem_dir = deps_file.parent
            dependencies = self.file_cache.load_dependencies_json(deps_file)
            files = self._find_subsystem_files(subsystem_dir)
            total_lines = sum(f.lines for f in files)
            subsystem_type = dependencies.get("type")

            subsystem = SubsystemInfo(
                path=subsystem_dir,
                name=subsystem_dir.name,
                dependencies=dependencies,
                files=files,
                total_lines=total_lines,
                parent_path=subsystem_dir.parent,
                subsystem_type=subsystem_type,
            )
            subsystems.append(subsystem)

        return subsystems

    def _find_subsystem_files(self, subsystem_dir: Path) -> List[FileInfo]:
        """Find TypeScript files in a subsystem, excluding child subsystems."""
        files = []

        for pattern in ["*.ts", "*.tsx"]:
            for ts_file in subsystem_dir.glob(pattern):
                if not is_test_file(ts_file):
                    file_info = self.file_cache.get_file_info(ts_file)
                    files.append(file_info)

        for subdir in subsystem_dir.iterdir():
            if subdir.is_dir() and not (subdir / "dependencies.json").exists():
                files.extend(self._find_subsystem_files(subdir))

        return files

    @staticmethod
    def _find_project_root(target_path: Path) -> Path:
        """Find project root by looking for common markers."""
        current = target_path.resolve()
        root_markers = {'package.json', '.git', 'pnpm-lock.yaml'}
        max_depth = 10

        for _ in range(max_depth):
            if any((current / marker).exists() for marker in root_markers):
                return current
            if current == current.parent:
                break
            current = current.parent

        return Path.cwd()
