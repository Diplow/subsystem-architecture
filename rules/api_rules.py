#!/usr/bin/env python3
"""
API route logging rules.

Checks that all route.ts files under api subsystems use withApiLogging.
"""

import re
from pathlib import Path
from typing import List

from ..models import ArchError, ErrorType, RecommendationType, SubsystemInfo
from ..utils.path_utils import PathHelper


class ApiRuleChecker:
    """Checker for API route logging rules."""

    def __init__(self, path_helper: PathHelper, file_cache):
        self.path_helper = path_helper
        self.file_cache = file_cache

    def check_api_route_logging(self, subsystems: List[SubsystemInfo]) -> List[ArchError]:
        """Check that all route handlers in api subsystems use withApiLogging."""
        errors = []

        api_subsystems = [
            s for s in subsystems
            if s.subsystem_type == "api" and not self._is_boundary_subsystem(s)
        ]

        for subsystem in api_subsystems:
            route_files = list(subsystem.path.rglob("route.ts"))
            for route_file in route_files:
                errors.extend(self._check_route_file(route_file, subsystem))

        return errors

    def _is_boundary_subsystem(self, subsystem: SubsystemInfo) -> bool:
        """Check if subsystem is a boundary type (e.g. auth)."""
        return subsystem.dependencies.get("type") == "boundary"

    def _check_route_file(self, route_file: Path, subsystem: SubsystemInfo) -> List[ArchError]:
        """Check a single route.ts file for withApiLogging usage."""
        errors = []
        content = self.file_cache.get_file_info(route_file).content
        if not content:
            return errors

        http_methods = ["GET", "POST", "PUT", "DELETE"]
        exported_methods = re.findall(
            r"export\s+(?:async\s+)?function\s+(GET|POST|PUT|DELETE)\b", content
        )

        if not exported_methods:
            return errors

        file_path = route_file.relative_to(self.path_helper.target_path)

        for method_name in exported_methods:
            errors.append(ArchError.create_error(
                message=(
                    f"❌ API route handler '{method_name}' in {file_path} "
                    f"is not wrapped with withApiLogging"
                ),
                error_type=ErrorType.API_ROUTE_LOGGING,
                subsystem=str(subsystem.path),
                file_path=str(file_path),
                recommendation=(
                    f"Wrap route handlers with withApiLogging in {file_path}: "
                    f"const handlers = withApiLogging(\"/api/...\", {{ {method_name}: async (...) => {{ ... }} }}); "
                    f"export const {{ {method_name} }} = handlers;"
                ),
                recommendation_type=RecommendationType.WRAP_API_WITH_LOGGING,
            ))

        return errors
