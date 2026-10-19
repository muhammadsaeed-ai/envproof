"""Factories for small, deterministic snapshot fixtures."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def snapshot() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "tool": {"name": "envproof", "version": "0.1.0"},
        "captured_at": "2026-01-01T00:00:00+00:00",
        "python": {
            "version": "3.12.1",
            "version_info": [3, 12, 1],
            "implementation": "CPython",
            "executable": "$VENV/bin/python",
            "prefix": "$VENV",
            "base_prefix": "$BASE_PYTHON",
            "is_venv": True,
            "cache_tag": "cpython-312",
            "soabi": "cpython-312-x86_64-linux-gnu",
        },
        "platform": {
            "system": "Linux",
            "release": "6.1.0",
            "machine": "x86_64",
            "architecture": "64bit",
            "libc": ["glibc", "2.36"],
        },
        "paths": {
            "sys_path": [
                {"path": "$PROJECT", "kind": "project", "empty_entry": False},
                {"path": "$VENV/lib/python3.12/site-packages", "kind": "environment-packages", "empty_entry": False},
            ],
            "site_packages": ["$VENV/lib/python3.12/site-packages"],
            "python_on_path": {"python": "$VENV/bin/python", "python3": "$BASE_PYTHON/bin/python3"},
            "path_entry_count": 3,
            "path_entries": ["$VENV/bin", "$BASE_PYTHON/bin", "$HOME/.local/bin"],
            "pythonpath_entries": [],
        },
        "environment": {
            "flags": {
                "PYTHONHOME": False,
                "PYTHONPATH": False,
                "VIRTUAL_ENV": True,
                "PIP_INDEX_CONFIGURATION_PRESENT": False,
            }
        },
        "packages": [
            {
                "name": "requests",
                "normalized_name": "requests",
                "version": "2.31.0",
                "location": "$VENV/lib/python3.12/site-packages",
                "location_kind": "environment-packages",
            },
            {
                "name": "urllib3",
                "normalized_name": "urllib3",
                "version": "2.1.0",
                "location": "$VENV/lib/python3.12/site-packages",
                "location_kind": "environment-packages",
            },
        ],
        "project": {
            "root": "$PROJECT",
            "files": [
                {"name": "pyproject.toml", "status": "fingerprinted", "size_bytes": 100, "sha256": "a" * 64},
                {"name": "uv.lock", "status": "fingerprinted", "size_bytes": 500, "sha256": "b" * 64},
            ],
            "git": {"checked": True, "available": True, "in_repo": True, "dirty": False, "commit": None},
        },
        "modules": [
            {
                "name": "requests",
                "found": True,
                "origin": "$VENV/lib/python3.12/site-packages/requests/__init__.py",
                "origin_kind": "third-party",
                "loader": "SourceFileLoader",
                "search_locations": [],
            }
        ],
        "privacy": {
            "environment_values_included": False,
            "source_file_contents_included": False,
            "network_requests_made": False,
            "commit_hash_included_by_request": False,
            "notes": [],
        },
    }


def copy_snapshot() -> dict[str, Any]:
    return deepcopy(snapshot())
