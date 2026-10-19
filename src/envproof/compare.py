"""Evidence-based, deterministic comparison of two EnvProof snapshots."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from envproof.capture import validate_snapshot
from envproof.errors import EnvProofError

SEVERITY_ORDER = {"high": 3, "warning": 2, "info": 1}


def _finding(
    code: str,
    severity: str,
    summary: str,
    evidence: list[str],
    explanation: str,
    next_step: str,
) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "summary": summary,
        "evidence": evidence,
        "explanation": explanation,
        "next_step": next_step,
    }


def _package_map(snapshot: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    mapped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for package in snapshot.get("packages", []):
        name = package.get("normalized_name")
        if not isinstance(name, str) or not name:
            raw_name = package.get("name")
            if not isinstance(raw_name, str) or not raw_name:
                continue
            name = raw_name.casefold().replace("_", "-").replace(".", "-")
        mapped[name].append(package)
    for records in mapped.values():
        records.sort(key=lambda item: (str(item.get("version", "")), str(item.get("location", ""))))
    return dict(mapped)


def _file_map(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for entry in snapshot.get("project", {}).get("files", []):
        name = entry.get("name")
        if isinstance(name, str):
            result[name] = entry
    return result


def _path_values(snapshot: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for item in snapshot.get("paths", {}).get("sys_path", []):
        if isinstance(item, dict):
            values.append(str(item.get("path", "")))
        elif isinstance(item, str):
            values.append(item)
    return values


def compare_snapshots(left: dict[str, Any], right: dict[str, Any]) -> list[dict[str, Any]]:
    """Compare a baseline (left) with a current/failing environment (right).

    Findings are deterministic and include the evidence behind each clue. They
    are not proofs of root cause; the caller should corroborate them with a
    reproduction or a test.
    """
    for label, snapshot in (("baseline", left), ("current", right)):
        try:
            validate_snapshot(snapshot)
        except EnvProofError as exc:
            raise EnvProofError(f"Invalid {label} snapshot: {exc}") from exc

    findings: list[dict[str, Any]] = []
    left_python = left.get("python", {})
    right_python = right.get("python", {})
    left_version = left_python.get("version_info", [])
    right_version = right_python.get("version_info", [])
    if left_version and right_version:
        if list(left_version[:2]) != list(right_version[:2]):
            findings.append(
                _finding(
                    "PYTHON_VERSION_MISMATCH",
                    "high",
                    "Python major/minor versions differ",
                    [f"Baseline: {left_python.get('version')}", f"Current: {right_python.get('version')}"],
                    "Python minor versions can change syntax support, standard-library behavior, ABI compatibility and dependency resolution.",
                    "Reproduce under the same Python major/minor version before investigating subtler differences.",
                )
            )
        elif list(left_version[:3]) != list(right_version[:3]):
            findings.append(
                _finding(
                    "PYTHON_PATCH_VERSION_DIFFERS",
                    "warning",
                    "Python patch versions differ",
                    [f"Baseline: {left_python.get('version')}", f"Current: {right_python.get('version')}"],
                    "Patch-level differences are usually lower risk than minor-version differences, but runtime bug fixes can affect behavior.",
                    "Try the same patch release if the failure appears runtime-specific.",
                )
            )
    elif left_python.get("version") != right_python.get("version"):
        findings.append(
            _finding(
                "PYTHON_VERSION_DIFFERS",
                "warning",
                "Python version information differs",
                [f"Baseline: {left_python.get('version')}", f"Current: {right_python.get('version')}"],
                "The snapshots do not contain comparable version tuples, but their recorded version strings differ.",
                "Capture both environments again with a supported EnvProof version if this distinction matters.",
            )
        )

    if left_python.get("implementation") != right_python.get("implementation"):
        findings.append(
            _finding(
                "PYTHON_IMPLEMENTATION_DIFFERS",
                "high",
                "Python implementations differ",
                [f"Baseline: {left_python.get('implementation')}", f"Current: {right_python.get('implementation')}"],
                "CPython, PyPy and other implementations can differ in ABI, extension support and runtime behavior.",
                "Repeat the failing workflow with the baseline implementation, or verify that all dependencies support the current implementation.",
            )
        )

    left_platform = left.get("platform", {})
    right_platform = right.get("platform", {})
    if left_platform.get("system") != right_platform.get("system") or left_platform.get(
        "machine"
    ) != right_platform.get("machine"):
        findings.append(
            _finding(
                "PLATFORM_DIFFERS",
                "warning",
                "Operating system or machine architecture differs",
                [
                    f"Baseline: {left_platform.get('system')} / {left_platform.get('machine')}",
                    f"Current: {right_platform.get('system')} / {right_platform.get('machine')}",
                ],
                "Native wheels, binary extensions, filesystem semantics and system libraries may vary across platforms.",
                "Check platform-specific dependencies and any native libraries used by the failing code.",
            )
        )
    elif left_platform.get("release") != right_platform.get("release"):
        findings.append(
            _finding(
                "OS_RELEASE_DIFFERS",
                "info",
                "Operating-system releases differ",
                [f"Baseline: {left_platform.get('release')}", f"Current: {right_platform.get('release')}"],
                "Different OS releases may ship different system libraries or security updates.",
                "Investigate this only if the failure relates to OS integration or native dependencies.",
            )
        )

    if left_python.get("is_venv") != right_python.get("is_venv"):
        findings.append(
            _finding(
                "VIRTUAL_ENVIRONMENT_STATUS_DIFFERS",
                "warning",
                "Only one environment appears to be a virtual environment",
                [
                    f"Baseline virtual environment: {left_python.get('is_venv')}",
                    f"Current virtual environment: {right_python.get('is_venv')}",
                ],
                "Isolation differences can expose or hide globally installed packages.",
                "Use an explicitly selected virtual environment for both runs and compare package inventories again.",
            )
        )

    left_paths = _path_values(left)
    right_paths = _path_values(right)
    if left_paths != right_paths:
        left_only = [value for value in left_paths if value not in right_paths]
        right_only = [value for value in right_paths if value not in left_paths]
        findings.append(
            _finding(
                "SYS_PATH_DIFFERS",
                "warning",
                "Python import search paths differ",
                [
                    f"Baseline entries: {len(left_paths)}; current entries: {len(right_paths)}",
                    f"Entries only in baseline: {', '.join(left_only[:5]) or 'none'}",
                    f"Entries only in current: {', '.join(right_only[:5]) or 'none'}",
                ],
                "Import order and path injection can cause Python to resolve a module from a different directory.",
                "Inspect sys.path ordering, editable installs, PYTHONPATH, and any local files that shadow package names.",
            )
        )

    left_resolution = left.get("paths", {}).get("python_on_path", {})
    right_resolution = right.get("paths", {}).get("python_on_path", {})
    for executable in ("python", "python3"):
        a = left_resolution.get(executable)
        b = right_resolution.get(executable)
        if a != b:
            findings.append(
                _finding(
                    "PATH_PYTHON_RESOLUTION_DIFFERS",
                    "warning",
                    f"{executable} resolves to different executables on PATH",
                    [f"Baseline: {a or 'not found'}", f"Current: {b or 'not found'}"],
                    "A shell command may invoke a different interpreter than the one used to capture the snapshot.",
                    "Use 'python -m pip' with the intended interpreter and check which executable your shell resolves.",
                )
            )
            break

    left_flags = left.get("environment", {}).get("flags", {})
    right_flags = right.get("environment", {}).get("flags", {})
    changed_flags = [
        key for key in sorted(set(left_flags) | set(right_flags)) if left_flags.get(key) != right_flags.get(key)
    ]
    if changed_flags:
        findings.append(
            _finding(
                "ENVIRONMENT_FLAGS_DIFFER",
                "warning",
                "Relevant environment-variable presence differs",
                [f"Changed flags (values intentionally omitted): {', '.join(changed_flags[:12])}"],
                "Variables such as PYTHONPATH or PYTHONHOME can alter import resolution. EnvProof records presence only and never stores their values.",
                "Check the listed variable names in both environments using your normal secure configuration process.",
            )
        )

    left_packages = _package_map(left)
    right_packages = _package_map(right)
    left_names = set(left_packages)
    right_names = set(right_packages)
    for name in sorted(left_names - right_names):
        versions = ", ".join(record.get("version", "?") for record in left_packages[name])
        findings.append(
            _finding(
                "PACKAGE_MISSING_CURRENT",
                "warning",
                f"Package present in baseline but missing from current environment: {name}",
                [f"Baseline version(s): {versions}"],
                "A missing dependency can cause import errors or change optional behavior.",
                f"Confirm whether {name} is required by this project and whether the current environment was fully synchronized.",
            )
        )
    for name in sorted(right_names - left_names):
        versions = ", ".join(record.get("version", "?") for record in right_packages[name])
        findings.append(
            _finding(
                "PACKAGE_ADDED_CURRENT",
                "info",
                f"Package present only in current environment: {name}",
                [f"Current version(s): {versions}"],
                "Extra packages can mask undeclared dependencies or alter plugin discovery and import behavior.",
                f"Check whether {name} is intentionally installed for this project or leaked from a shared environment.",
            )
        )
    for name in sorted(left_names & right_names):
        left_records = left_packages[name]
        right_records = right_packages[name]
        left_versions = sorted(str(record.get("version", "?")) for record in left_records)
        right_versions = sorted(str(record.get("version", "?")) for record in right_records)
        if left_versions != right_versions:
            findings.append(
                _finding(
                    "PACKAGE_VERSION_DIFFERS",
                    "warning",
                    f"Installed package version differs: {name}",
                    [f"Baseline: {', '.join(left_versions)}", f"Current: {', '.join(right_versions)}"],
                    "Dependency versions can change behavior, transitive dependencies, native extensions and accepted inputs.",
                    f"Compare the lockfile or constraints for {name}; test the current environment with the baseline version before changing code.",
                )
            )
        left_locations = sorted((str(x.get("location_kind")), str(x.get("location"))) for x in left_records)
        right_locations = sorted((str(x.get("location_kind")), str(x.get("location"))) for x in right_records)
        if left_locations != right_locations and left_versions == right_versions:
            findings.append(
                _finding(
                    "PACKAGE_LOCATION_DIFFERS",
                    "info",
                    f"Package install location differs: {name}",
                    [
                        f"Baseline locations: {', '.join(loc for _, loc in left_locations)}",
                        f"Current locations: {', '.join(loc for _, loc in right_locations)}",
                    ],
                    "A different package location may indicate editable installs, path contamination or a different virtual environment.",
                    f"Inspect import resolution for modules provided by {name} if an import behaves unexpectedly.",
                )
            )
        if len(left_records) > 1 or len(right_records) > 1:
            findings.append(
                _finding(
                    "DUPLICATE_DISTRIBUTION_METADATA",
                    "warning",
                    f"Multiple distribution records found for {name}",
                    [f"Baseline records: {len(left_records)}; current records: {len(right_records)}"],
                    "Duplicate metadata can indicate overlapping site-packages directories or stale installations.",
                    "Inspect sys.path and the listed install locations; do not remove files until the owning environment is identified.",
                )
            )

    left_files = _file_map(left)
    right_files = _file_map(right)
    for name in sorted(set(left_files) | set(right_files), key=str.casefold):
        a = left_files.get(name)
        b = right_files.get(name)
        if a is None:
            findings.append(
                _finding(
                    "PROJECT_MANIFEST_ADDED",
                    "warning",
                    f"Project manifest/configuration file exists only in current snapshot: {name}",
                    [f"Current state: {b.get('status')}" if b else ""],
                    "A different project or dependency manifest can change package installation and runtime configuration.",
                    f"Confirm that {name} is expected to be present in this environment and is version-controlled where appropriate.",
                )
            )
        elif b is None:
            findings.append(
                _finding(
                    "PROJECT_MANIFEST_MISSING",
                    "warning",
                    f"Project manifest/configuration file missing from current snapshot: {name}",
                    [f"Baseline state: {a.get('status')}"],
                    "The current checkout may not have the same dependency or tool configuration as the baseline.",
                    f"Check the checkout, generated-file process and project root for {name}.",
                )
            )
        elif (a.get("status"), a.get("sha256"), a.get("size_bytes")) != (
            b.get("status"),
            b.get("sha256"),
            b.get("size_bytes"),
        ):
            lockfiles = {"uv.lock", "poetry.lock", "pdm.lock", "pipfile.lock", "pyproject.toml", "requirements.txt"}
            severity = "high" if name.lower() in lockfiles else "warning"
            findings.append(
                _finding(
                    "PROJECT_MANIFEST_CHANGED",
                    severity,
                    f"Project manifest/configuration changed: {name}",
                    [
                        f"Baseline SHA-256: {a.get('sha256', a.get('status'))}",
                        f"Current SHA-256: {b.get('sha256', b.get('status'))}",
                    ],
                    "Changed project metadata or lockfiles can alter the dependency set or test configuration.",
                    f"Review the version-control diff for {name} and rerun the environment synchronization step.",
                )
            )

    left_modules = {str(m.get("name")): m for m in left.get("modules", []) if m.get("name")}
    right_modules = {str(m.get("name")): m for m in right.get("modules", []) if m.get("name")}
    for name in sorted(set(left_modules) | set(right_modules)):
        a = left_modules.get(name)
        b = right_modules.get(name)
        if a is None or b is None:
            findings.append(
                _finding(
                    "MODULE_NOT_CAPTURED_ON_BOTH_SIDES",
                    "info",
                    f"Import-resolution evidence is incomplete for module {name}",
                    [f"Captured in baseline: {a is not None}", f"Captured in current snapshot: {b is not None}"],
                    "Only modules requested during capture can be compared.",
                    f"Recapture both environments with --module {name} to compare its import origin.",
                )
            )
        elif (a.get("found"), a.get("origin"), a.get("origin_kind")) != (
            b.get("found"),
            b.get("origin"),
            b.get("origin_kind"),
        ):
            findings.append(
                _finding(
                    "IMPORT_ORIGIN_CHANGED",
                    "high",
                    f"Import resolution changed for module {name}",
                    [
                        f"Baseline: {'found at ' + str(a.get('origin')) if a.get('found') else 'not found'}",
                        f"Current: {'found at ' + str(b.get('origin')) if b.get('found') else 'not found'}",
                    ],
                    "The same import name resolves differently, which can indicate module shadowing, different installations or missing dependencies.",
                    f"Inspect the reported origin and sys.path order; check for local files named {name}.py or directories named {name}.",
                )
            )

    left_git = left.get("project", {}).get("git", {})
    right_git = right.get("project", {}).get("git", {})
    if left_git.get("in_repo") != right_git.get("in_repo"):
        findings.append(
            _finding(
                "GIT_REPOSITORY_STATUS_DIFFERS",
                "info",
                "Git repository detection differs",
                [
                    f"Baseline is in a Git repository: {left_git.get('in_repo')}",
                    f"Current is in a Git repository: {right_git.get('in_repo')}",
                ],
                "Snapshots may have been captured from a source checkout versus a copied folder or installed package.",
                "Ensure both snapshots describe the intended source revision.",
            )
        )
    elif (
        left_git.get("in_repo")
        and right_git.get("in_repo")
        and left_git.get("dirty") is not None
        and right_git.get("dirty") is not None
        and left_git.get("dirty") != right_git.get("dirty")
    ):
        findings.append(
            _finding(
                "GIT_WORKTREE_STATE_DIFFERS",
                "warning",
                "One working tree has tracked changes while the other does not",
                [f"Baseline dirty: {left_git.get('dirty')}", f"Current dirty: {right_git.get('dirty')}"],
                "Uncommitted edits can explain why two otherwise similar environments behave differently.",
                "Inspect tracked changes in both working trees; file names and contents are intentionally not captured.",
            )
        )
    left_commit = left_git.get("commit")
    right_commit = right_git.get("commit")
    if left_commit and right_commit and left_commit != right_commit:
        findings.append(
            _finding(
                "GIT_COMMIT_DIFFERS",
                "warning",
                "Source commit differs between snapshots",
                [f"Baseline commit: {left_commit}", f"Current commit: {right_commit}"],
                "Different code revisions may explain the behavior even when Python environments match.",
                "Reproduce on the same commit before attributing the failure to environment drift.",
            )
        )

    findings.sort(key=lambda item: (-SEVERITY_ORDER.get(item["severity"], 0), item["code"], item["summary"]))
    return findings


def fail_level(findings: list[dict[str, Any]], threshold: str) -> bool:
    """Return whether findings meet a CLI failure threshold."""
    if threshold == "never":
        return False
    if threshold not in {"high", "warning"}:
        raise EnvProofError(f"Unsupported failure threshold: {threshold}")
    target = SEVERITY_ORDER[threshold]
    return any(SEVERITY_ORDER.get(finding.get("severity", "info"), 0) >= target for finding in findings)
