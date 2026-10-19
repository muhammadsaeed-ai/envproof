"""Deterministic local checks derived only from captured evidence."""

from __future__ import annotations

import sys
from typing import Any

from envproof.capture import validate_snapshot
from envproof.compare import SEVERITY_ORDER


def audit_snapshot(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Return explainable local diagnostic clues; do not claim definitive causes."""
    validate_snapshot(snapshot)
    findings: list[dict[str, Any]] = []

    def add(code: str, severity: str, summary: str, evidence: list[str], explanation: str, next_step: str) -> None:
        findings.append(
            {
                "code": code,
                "severity": severity,
                "summary": summary,
                "evidence": evidence,
                "explanation": explanation,
                "next_step": next_step,
            }
        )

    python = snapshot.get("python", {})
    flags = snapshot.get("environment", {}).get("flags", {})
    if flags.get("PYTHONHOME"):
        add(
            "PYTHONHOME_SET",
            "warning",
            "PYTHONHOME is set",
            ["EnvProof captured that PYTHONHOME is present; its value was not recorded."],
            "PYTHONHOME overrides Python's normal prefix discovery and can lead to unexpected standard-library or environment paths.",
            "Confirm that PYTHONHOME is intentionally configured for this process; unset it for a controlled test if appropriate.",
        )
    if flags.get("PYTHONPATH"):
        add(
            "PYTHONPATH_SET",
            "warning",
            "PYTHONPATH is set",
            ["EnvProof captured that PYTHONPATH is present; its value was not recorded."],
            "PYTHONPATH injects additional import search paths and can make local behavior differ from a clean install.",
            "Inspect the configured directories and rerun with PYTHONPATH unset in an isolated shell if appropriate.",
        )
    if flags.get("VIRTUAL_ENV") and not python.get("is_venv"):
        add(
            "VIRTUAL_ENV_INTERPRETER_MISMATCH",
            "warning",
            "VIRTUAL_ENV is set, but this interpreter does not identify itself as running in a virtual environment",
            ["VIRTUAL_ENV is present", f"sys.prefix differs from sys.base_prefix: {python.get('is_venv')}"],
            "The shell may have an activation variable left over while invoking a different Python executable.",
            "Check the actual interpreter with 'python -c \"import sys; print(sys.executable)\"' and invoke pip as 'python -m pip'.",
        )

    paths = snapshot.get("paths", {})
    resolution = paths.get("python_on_path", {})
    executable = python.get("executable")
    resolved_python = resolution.get("python")
    if executable and resolved_python and executable != resolved_python:
        add(
            "PYTHON_EXECUTABLE_PATH_MISMATCH",
            "warning",
            "The active interpreter differs from the first 'python' found on PATH",
            [f"Active interpreter: {executable}", f"PATH resolution: {resolved_python}"],
            "Scripts run through the shell may use a different interpreter from the one currently executing this audit.",
            "Use the active interpreter explicitly and verify that IDE, terminal and CI use the intended environment.",
        )

    sys_path = paths.get("sys_path", [])
    base_packages = [
        item.get("path") for item in sys_path
        if isinstance(item, dict) and item.get("kind") == "base-packages" and item.get("path")
    ]
    if python.get("is_venv") and base_packages:
        add(
            "BASE_ENV_PACKAGES_ON_SYS_PATH",
            "warning",
            "Base Python package directories appear on sys.path inside a virtual environment",
            [f"Detected directories: {', '.join(str(item) for item in base_packages[:5])}"],
            "System-site-package access or path injection can allow global packages to mask undeclared project dependencies.",
            "Check whether the virtual environment was created with system-site-packages or whether PYTHONPATH injects paths.",
        )

    modules = snapshot.get("modules", [])
    stdlib_names = getattr(sys, "stdlib_module_names", frozenset())
    for module in modules:
        if not isinstance(module, dict) or not module.get("found"):
            continue
        name = module.get("name")
        origin = str(module.get("origin") or "")
        if name in stdlib_names and origin.startswith("$PROJECT/"):
            add(
                "STDLIB_MODULE_SHADOWED_BY_PROJECT",
                "high",
                f"Project appears to shadow Python's standard-library module {name}",
                [f"Import origin: {origin}"],
                "A project file or directory has the same top-level name as a standard-library module and may be imported instead.",
                f"Rename the local {name!r} file or package and remove stale __pycache__ files if present, then rerun the import check.",
            )
        if origin.startswith("$PROJECT/") and name not in stdlib_names:
            # Informational only: a project-local module can be intentional.
            add(
                "MODULE_RESOLVES_INSIDE_PROJECT",
                "info",
                f"Module {name} resolves inside the project directory",
                [f"Import origin: {origin}"],
                "This is normal for first-party modules, but unexpected for third-party dependencies.",
                "If this import was expected to come from an installed dependency, check for name collisions and editable-install configuration.",
            )

    packages = snapshot.get("packages", [])
    grouped: dict[str, list[dict[str, Any]]] = {}
    for package in packages:
        if isinstance(package, dict) and package.get("normalized_name"):
            grouped.setdefault(str(package["normalized_name"]), []).append(package)
    for name, records in sorted(grouped.items()):
        if len(records) > 1:
            versions = sorted(str(record.get("version", "?")) for record in records)
            locations = sorted({str(record.get("location", "?")) for record in records})
            add(
                "DUPLICATE_DISTRIBUTION_RECORDS",
                "warning",
                f"Multiple installed distribution records found for {name}",
                [f"Versions: {', '.join(versions)}", f"Locations: {', '.join(locations[:4])}"],
                "Overlapping package directories or stale metadata can make imports and package inspection ambiguous.",
                "Inspect the reported install locations and remove stale installations only after identifying the owning environment.",
            )

    git = snapshot.get("project", {}).get("git", {})
    if git.get("in_repo") and git.get("dirty"):
        add(
            "GIT_WORKTREE_DIRTY",
            "info",
            "Tracked working-tree changes were present at capture time",
            ["EnvProof stores only a dirty/clean indicator; it does not capture changed file names or contents."],
            "Local edits can explain why a test behaves differently from a clean CI checkout.",
            "Review your local Git diff and reproduce from a clean checkout if a baseline comparison is needed.",
        )

    findings.sort(key=lambda item: (-SEVERITY_ORDER.get(item["severity"], 0), item["code"], item["summary"]))
    return findings
