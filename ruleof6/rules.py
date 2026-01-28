#!/usr/bin/env python3
"""
Rule of 6 check implementations.

Contains the 4 Rule of 6 checks:
- Subsystem count: max 6 declared subsystems per parent
- Functions per file: max 6 exported functions
- Function lines: 50 warning / 100 error
- Function arguments: max 6 (or 1 object with max 6 keys)
"""

from pathlib import Path
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..models import (
    ArchError, ErrorType, Severity, RecommendationType, SubsystemInfo,
)
from ..shared.typescript_parser import TypeScriptParser, FunctionInfo
from ..utils.exception_handler import RuleOf6ExceptionHandler
from ..utils.file_utils import FileCache, get_file_content, is_test_file


# Thresholds
MAX_SUBSYSTEMS = 6
MAX_FUNCTIONS_PER_FILE = 6
MAX_FUNCTION_LINES_WARNING = 50
MAX_FUNCTION_LINES_ERROR = 100
MAX_FUNCTION_ARGS = 6
MAX_OBJECT_KEYS = 6


class RuleOf6Rules:
    """Implements the four Rule of 6 checks."""

    def __init__(self, file_cache: FileCache, exception_handler: RuleOf6ExceptionHandler):
        self.file_cache = file_cache
        self.exception_handler = exception_handler
        self.ts_parser = TypeScriptParser()

    # ------------------------------------------------------------------
    # 1. Subsystem count
    # ------------------------------------------------------------------

    def check_subsystem_count(self, subsystems: List[SubsystemInfo]) -> List[ArchError]:
        """Check that no subsystem declares more than 6 child subsystems."""
        errors: List[ArchError] = []
        for subsystem in subsystems:
            declared_children = subsystem.dependencies.get("subsystems", [])
            if len(declared_children) > MAX_SUBSYSTEMS:
                errors.append(ArchError.create_error(
                    message=(
                        f"Subsystem '{subsystem.name}' declares {len(declared_children)} "
                        f"child subsystems (max {MAX_SUBSYSTEMS})"
                    ),
                    error_type=ErrorType.SUBSYSTEM_COUNT,
                    subsystem=str(subsystem.path),
                    recommendation=(
                        "Introduce a router subsystem to group related children. "
                        "Focus on meaningful groupings, not arbitrary splits."
                    ),
                    recommendation_type=RecommendationType.REDUCE_SUBSYSTEMS,
                ))
        return errors

    # ------------------------------------------------------------------
    # 2 + 3. File function count, function lines, function arguments
    # ------------------------------------------------------------------

    def check_file_functions(self, subsystems: List[SubsystemInfo]) -> List[ArchError]:
        """Check function count, lines, and arguments across all subsystem files."""
        errors: List[ArchError] = []
        target_path = self._find_target_path(subsystems)

        # Collect all TypeScript files from subsystems
        all_files: List[Path] = []
        for subsystem in subsystems:
            for file_info in subsystem.files:
                if not is_test_file(file_info.path) and not self._is_type_file(file_info.path):
                    all_files.append(file_info.path)

        # Process files in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self._check_single_file, file_path, target_path): file_path
                for file_path in all_files
            }
            for future in as_completed(futures):
                file_errors = future.result()
                errors.extend(file_errors)

        return errors

    def _check_single_file(self, file_path: Path, target_path: Path) -> List[ArchError]:
        """Check a single file for function count, lines, and argument violations."""
        errors: List[ArchError] = []
        content = get_file_content(file_path)
        if not content:
            return errors

        functions = self.ts_parser.extract_functions(content, file_path)

        try:
            relative_path = str(file_path.relative_to(target_path))
        except ValueError:
            relative_path = str(file_path)

        # --- Function count per file ---
        file_exception = self.exception_handler.get_file_exception(file_path)
        file_threshold = file_exception.threshold if file_exception else MAX_FUNCTIONS_PER_FILE

        if len(functions) > file_threshold:
            func_names = [f.name for f in functions[:8]]
            if len(functions) > 8:
                func_names.append("...")

            if file_exception:
                message = f"File '{relative_path}' has {len(functions)} functions (custom limit {file_threshold})"
            else:
                message = f"File '{relative_path}' has {len(functions)} functions (max {file_threshold})"

            errors.append(ArchError.create_warning(
                message=message,
                error_type=ErrorType.FILE_FUNCTIONS,
                file_path=relative_path,
                recommendation=(
                    "Split into multiple files by grouping related functions. "
                    "Prefix internal helpers with '_'."
                ),
                recommendation_type=RecommendationType.REDUCE_FUNCTIONS,
            ))

        # --- Per-function checks ---
        for func in functions:
            errors.extend(self._check_function_lines(func, relative_path))
            errors.extend(self._check_function_arguments(func, relative_path))

        return errors

    def _check_function_lines(self, func: FunctionInfo, relative_path: str) -> List[ArchError]:
        """Check function line count with custom threshold support."""
        errors: List[ArchError] = []
        custom_rule = self.exception_handler.get_function_exception(relative_path, func.name)

        if custom_rule:
            if func.line_count > custom_rule.threshold:
                errors.append(ArchError.create_warning(
                    message=(
                        f"Function '{func.name}' has {func.line_count} lines "
                        f"(custom limit {custom_rule.threshold})"
                    ),
                    error_type=ErrorType.FUNCTION_LINES,
                    file_path=relative_path,
                    line_number=func.line_start,
                    recommendation=(
                        f"Refactor to stay within custom threshold. "
                        f"Justification: {custom_rule.justification}"
                    ),
                    recommendation_type=RecommendationType.REDUCE_FUNCTION_LINES,
                ))
        elif func.line_count > MAX_FUNCTION_LINES_WARNING:
            if func.line_count >= MAX_FUNCTION_LINES_ERROR:
                errors.append(ArchError.create_warning(
                    message=(
                        f"Function '{func.name}' has {func.line_count} lines "
                        f"(enforced max {MAX_FUNCTION_LINES_ERROR})"
                    ),
                    error_type=ErrorType.FUNCTION_LINES,
                    file_path=relative_path,
                    line_number=func.line_start,
                    recommendation=(
                        "Immediately refactor into max 6 function calls at the same "
                        "abstraction level. Avoid creating meaningless wrapper functions."
                    ),
                    recommendation_type=RecommendationType.REDUCE_FUNCTION_LINES,
                ))
            else:
                errors.append(ArchError.create_warning(
                    message=(
                        f"Function '{func.name}' has {func.line_count} lines "
                        f"(recommended max {MAX_FUNCTION_LINES_WARNING})"
                    ),
                    error_type=ErrorType.FUNCTION_LINES,
                    file_path=relative_path,
                    line_number=func.line_start,
                    recommendation=(
                        "Break down into max 6 smaller functions at the same "
                        "abstraction level. Focus on single responsibility."
                    ),
                    recommendation_type=RecommendationType.REDUCE_FUNCTION_LINES,
                ))

        return errors

    def _check_function_arguments(self, func: FunctionInfo, relative_path: str) -> List[ArchError]:
        """Check function argument count."""
        errors: List[ArchError] = []
        if func.arg_count > MAX_FUNCTION_ARGS:
            errors.append(ArchError.create_warning(
                message=(
                    f"Function '{func.name}' has {func.arg_count} arguments "
                    f"(max {MAX_FUNCTION_ARGS})"
                ),
                error_type=ErrorType.FUNCTION_ARGS,
                file_path=relative_path,
                line_number=func.line_start,
                recommendation=(
                    f"Use max 3 arguments, or 1 object with max {MAX_OBJECT_KEYS} keys. "
                    "Group related parameters meaningfully."
                ),
                recommendation_type=RecommendationType.REDUCE_FUNCTION_ARGS,
            ))
        return errors

    # ------------------------------------------------------------------
    # 4. Object parameter keys
    # ------------------------------------------------------------------

    def check_object_parameter_keys(self, subsystems: List[SubsystemInfo]) -> List[ArchError]:
        """Check object parameters have max 6 keys."""
        errors: List[ArchError] = []
        target_path = self._find_target_path(subsystems)

        for subsystem in subsystems:
            for file_info in subsystem.files:
                if is_test_file(file_info.path) or self._is_type_file(file_info.path):
                    continue
                content = get_file_content(file_info.path)
                if not content:
                    continue

                violations = self.ts_parser.find_object_parameter_violations(
                    content, file_info.path, MAX_OBJECT_KEYS
                )

                try:
                    relative_path = str(file_info.path.relative_to(target_path))
                except ValueError:
                    relative_path = str(file_info.path)

                for line_num, key_count, params_preview in violations:
                    errors.append(ArchError.create_warning(
                        message=(
                            f"Object parameter has {key_count} keys "
                            f"(max {MAX_OBJECT_KEYS})"
                        ),
                        error_type=ErrorType.FUNCTION_ARGS,
                        file_path=relative_path,
                        line_number=line_num,
                        recommendation=(
                            "Group related keys into nested objects or split into "
                            "multiple focused parameters with clear semantic meaning."
                        ),
                        recommendation_type=RecommendationType.REDUCE_FUNCTION_ARGS,
                    ))

        return errors

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_type_file(file_path: Path) -> bool:
        """Check if file is a pure type definition file."""
        name = file_path.name
        return name == "types.ts" or name == "types.tsx" or "/types/" in str(file_path)

    @staticmethod
    def _find_target_path(subsystems: List[SubsystemInfo]) -> Path:
        """Derive the common target path from subsystems."""
        if not subsystems:
            return Path("src")
        # Use the highest-level subsystem path
        shortest = min(subsystems, key=lambda s: len(s.path.parts))
        return shortest.path.parent if shortest.path.parent.name else shortest.path
