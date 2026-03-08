#!/usr/bin/env python3
"""Calculate next version based on pyproject.toml floor and PyPI current version.

This script implements the floor-based auto-versioning logic:
- The version in pyproject.toml defines the minimum floor for Major.Minor
- Patch version is auto-incremented based on the current PyPI version

Usage:
    # Show version calculation
    python scripts/calculate_version.py

    # Output for CI (sets GITHUB_OUTPUT)
    python scripts/calculate_version.py --ci

Examples:
    pyproject.toml    PyPI current    Result
    ─────────────────────────────────────────
    0.1.0             0.0.28          0.1.0    (floor higher → use floor)
    0.1.0             0.1.5           0.1.6    (same floor → patch++)
    1.0.0             0.9.99          1.0.0    (major bump → use floor)
    1.20.0            1.19.28         1.20.0   (minor bump → use floor)
"""

from __future__ import annotations

import json
import os
import re
import sys
import tomllib
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple


class Version(NamedTuple):
    """Semantic version components."""

    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def parse_version(version: str) -> Version:
    """Parse semantic version string to Version tuple.

    Args:
        version: Version string (e.g., "1.2.3")

    Returns:
        Version tuple with major, minor, patch components

    Raises:
        ValueError: If version format is invalid
    """
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise ValueError(f"Invalid version format: {version}")
    return Version(int(match.group(1)), int(match.group(2)), int(match.group(3)))


def get_floor_version(pyproject_path: Path | None = None) -> str:
    """Read version from pyproject.toml.

    Args:
        pyproject_path: Path to pyproject.toml (default: project root)

    Returns:
        Version string from pyproject.toml
    """
    if pyproject_path is None:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def get_pypi_version(package_name: str) -> str | None:
    """Query current version from PyPI.

    Args:
        package_name: Name of the package on PyPI

    Returns:
        Current version string or None if not found
    """
    try:
        url = f"https://pypi.org/pypi/{package_name}/json"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "unifiedui-sdk-versioning/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            return data["info"]["version"]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None  # Package not yet published
        raise
    except Exception as e:
        print(f"Warning: Could not query PyPI: {e}", file=sys.stderr)
        return None


def calculate_next_version(floor: str, current: str | None) -> str:
    """Calculate next version based on floor and current PyPI version.

    Args:
        floor: Version from pyproject.toml (minimum floor for major.minor)
        current: Current version on PyPI (or None if not published)

    Returns:
        Next version to publish
    """
    if current is None:
        return floor

    floor_v = parse_version(floor)
    current_v = parse_version(current)

    # Floor Major.Minor is higher → use floor (reset patch)
    if (floor_v.major, floor_v.minor) > (current_v.major, current_v.minor):
        return floor

    # Same or lower Major.Minor → increment patch from current
    return str(Version(current_v.major, current_v.minor, current_v.patch + 1))


@dataclass
class VersionResult:
    """Result of version calculation."""

    floor: str
    current: str | None
    next: str
    package_name: str


def get_version_info(package_name: str = "unifiedui-sdk") -> VersionResult:
    """Get complete version information.

    Args:
        package_name: Name of the package on PyPI

    Returns:
        VersionResult with floor, current, and next versions
    """
    floor = get_floor_version()
    current = get_pypi_version(package_name)
    next_version = calculate_next_version(floor, current)

    return VersionResult(
        floor=floor,
        current=current,
        next=next_version,
        package_name=package_name,
    )


def main() -> None:
    """Main entry point."""
    package_name = "unifiedui-sdk"
    result = get_version_info(package_name)

    ci_mode = "--ci" in sys.argv

    print(f"📦 Package: {result.package_name}")
    print(f"📋 Floor version (pyproject.toml): {result.floor}")
    print(f"🌐 Current version (PyPI): {result.current or 'not published'}")
    print(f"🚀 Next version: {result.next}")

    if ci_mode:
        # Output for GitHub Actions
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a") as f:
                f.write(f"floor={result.floor}\n")
                f.write(f"current={result.current or ''}\n")
                f.write(f"version={result.next}\n")
            print(f"\n✅ Wrote outputs to GITHUB_OUTPUT")
        else:
            # Fallback for older GitHub Actions syntax
            print(f"\n::set-output name=floor::{result.floor}")
            print(f"::set-output name=current::{result.current or ''}")
            print(f"::set-output name=version::{result.next}")


if __name__ == "__main__":
    main()
