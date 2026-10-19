"""Capture a bounded, JSON-safe fingerprint of a live Python environment."""

from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.metadata as metadata
import json
import os
import platform
import re
import shutil
import site
import subprocess
import sys
import sysconfig
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from envproof import SCHEMA_VERSION, __version__
from envproof._output import atomic_write_text
from envproof.errors import EnvProofError
from envproof.privacy import redact_path, safe_environment_flags, sanitize_path_entries

MAX_MANIFEST_BYTES = 5 * 1024 * 1024
MAX_DISTRIBUTIONS = 50_000
MAX_MODULES = 100
MODULE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Only these known manifest/config files are fingerprinted. File contents are
# never included in a snapshot; dotenv files and arbitrary project files are
# deliberately excluded because they commonly contain secrets.
KNOWN_PROJECT_FILES = {
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "tox.ini",
    "uv.lock",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
    "pdm.lock",
    "hatch.toml",
    "pixi.toml",
    "environment.yml",
    "environment.yaml",
    "conda.yml",
    "conda.yaml",
    "runtime.txt",
    ".python-version",
    ".tool-versions",
    "Dockerfile",
    "Containerfile",
    "Makefile",
}


def normalize_distribution_name(name: str) -> str:
    """Normalize a distribution name using Python packaging's common rules."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _roots(project_root: Path) -> dict[str, str]:
    return {
        "project_root": str(project_root),
        "prefix": str(Path(sys.prefix).resolve()),
        "base_prefix": str(Path(sys.base_prefix).resolve()),
        "home": str(Path.home().resolve()),
    }


def _safe_path(path: str | os.PathLike[str] | None, roots: dict[str, str]) -> str | None:
    return redact_path(
        path,
        project_root=roots["project_root"],
        prefix=roots["prefix"],
        base_prefix=roots["base_prefix"],
        home=roots["home"],
    )


def _is_under(path: str, root: str) -> bool:
    try:
        path_cmp = os.path.normcase(os.path.abspath(path))
        root_cmp = os.path.normcase(os.path.abspath(root))
        return os.path.commonpath([path_cmp, root_cmp]) == root_cmp
    except (OSError, ValueError):
        return False


def _classify_path(path: str, project_root: Path, roots: dict[str, str]) -> str:
    if not path:
        return "empty"
    normalized = os.path.abspath(path)
    if _is_under(normalized, str(project_root)):
        return "project"
    # Site-packages must be recognized before their containing Python prefix.
    if "site-packages" in normalized.casefold() or "dist-packages" in normalized.casefold():
        if _is_under(normalized, roots["prefix"]):
            return "environment-packages"
        if roots["prefix"] != roots["base_prefix"] and _is_under(normalized, roots["base_prefix"]):
            return "base-packages"
        return "third-party"
    stdlib_roots = {value for key, value in sysconfig.get_paths().items() if key in {"stdlib", "platstdlib"} and value}
    if any(_is_under(normalized, root) for root in stdlib_roots):
        return "standard-library"
    if _is_under(normalized, roots["prefix"]):
        return "environment"
    if _is_under(normalized, roots["base_prefix"]):
        return "base-python"
    return "external"


def _distribution_inventory(project_root: Path, roots: dict[str, str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        distributions: Iterable[metadata.Distribution] = metadata.distributions()
        for index, dist in enumerate(distributions):
            if index >= MAX_DISTRIBUTIONS:
                raise EnvProofError(
                    f"The environment reports more than {MAX_DISTRIBUTIONS:,} distributions; "
                    "refusing to create an unbounded snapshot."
                )
            name = dist.metadata.get("Name") or "<unknown>"
            try:
                version = dist.version
            except Exception:  # malformed installed metadata should not break diagnosis
                version = "<unreadable>"
            try:
                location = str(dist.locate_file(""))
            except Exception:
                location = ""
            records.append(
                {
                    "name": name,
                    "normalized_name": normalize_distribution_name(name),
                    "version": version,
                    "location": _safe_path(location, roots),
                    "location_kind": _classify_path(location, project_root, roots) if location else "unknown",
                }
            )
    except EnvProofError:
        raise
    except Exception as exc:
        raise EnvProofError(f"Could not inspect installed distribution metadata: {exc}") from exc
    records.sort(key=lambda item: (item["normalized_name"], item["version"], item["location"] or ""))
    return records


def _project_file_fingerprints(project_root: Path) -> list[dict[str, Any]]:
    names = set(KNOWN_PROJECT_FILES)
    try:
        for item in project_root.iterdir():
            if item.is_file() and item.name.startswith("requirements") and item.suffix.lower() in {".txt", ".in"}:
                names.add(item.name)
    except OSError as exc:
        raise EnvProofError(f"Cannot list project directory {project_root}: {exc}") from exc

    output: list[dict[str, Any]] = []
    for name in sorted(names, key=str.casefold):
        candidate = project_root / name
        try:
            if not candidate.is_file():
                continue
            # Don't hash symlink targets outside the selected project root.
            if candidate.is_symlink():
                try:
                    resolved = candidate.resolve(strict=True)
                    if os.path.commonpath([str(resolved), str(project_root)]) != str(project_root):
                        output.append({"name": name, "status": "external-symlink-skipped"})
                        continue
                except (OSError, ValueError):
                    output.append({"name": name, "status": "unreadable"})
                    continue
            size = candidate.stat().st_size
            if size > MAX_MANIFEST_BYTES:
                output.append({"name": name, "status": "too-large", "size_bytes": size})
                continue
            hasher = hashlib.sha256()
            bytes_read = 0
            too_large = False
            with candidate.open("rb") as handle:
                while True:
                    chunk = handle.read(min(64 * 1024, MAX_MANIFEST_BYTES + 1 - bytes_read))
                    if not chunk:
                        break
                    bytes_read += len(chunk)
                    if bytes_read > MAX_MANIFEST_BYTES:
                        too_large = True
                        break
                    hasher.update(chunk)
            if too_large:
                output.append({"name": name, "status": "too-large", "size_bytes": bytes_read})
            else:
                output.append(
                    {
                        "name": name,
                        "status": "fingerprinted",
                        "size_bytes": bytes_read,
                        "sha256": hasher.hexdigest(),
                    }
                )
        except OSError:
            output.append({"name": name, "status": "unreadable"})
    return output


def _module_resolution(name: str, project_root: Path, roots: dict[str, str]) -> dict[str, Any]:
    if not MODULE_NAME_RE.fullmatch(name):
        raise EnvProofError(
            f"Invalid module name {name!r}. Supply a top-level import name such as 'json' or 'requests' "
            "without dots. This avoids importing parent packages while inspecting resolution."
        )
    try:
        # Bypass sys.modules so an earlier import by EnvProof itself cannot hide
        # a local shadowing file. PathFinder resolves top-level names without
        # executing the target module's code.
        spec = importlib.machinery.BuiltinImporter.find_spec(name)
        if spec is None:
            spec = importlib.machinery.FrozenImporter.find_spec(name)
        if spec is None:
            spec = importlib.machinery.PathFinder.find_spec(name, sys.path)
    except (ImportError, AttributeError, ValueError, OSError) as exc:
        return {"name": name, "found": False, "error_type": type(exc).__name__}
    if spec is None:
        return {"name": name, "found": False, "error_type": None}
    origin = spec.origin
    safe_origin = _safe_path(origin, roots) if origin not in (None, "built-in", "frozen") else origin
    search_locations = []
    if spec.submodule_search_locations is not None:
        search_locations = [
            safe for safe in (_safe_path(value, roots) for value in spec.submodule_search_locations) if safe is not None
        ]
    origin_kind = "unknown"
    if origin in (None, "built-in", "frozen"):
        origin_kind = str(origin or "namespace")
    elif origin and (origin == "built-in" or origin == "frozen"):
        origin_kind = origin
    elif str(safe_origin).startswith("$PROJECT"):
        origin_kind = "project"
    elif "site-packages" in str(safe_origin).casefold() or "dist-packages" in str(safe_origin).casefold():
        origin_kind = "third-party"
    elif any(
        _is_under(str(origin), root)
        for root in {
            value
            for key, value in sysconfig.get_paths().items()
            if key in {"stdlib", "platstdlib"} and value
        }
    ):
        origin_kind = "standard-library"
    else:
        origin_kind = "external"
    return {
        "name": name,
        "found": True,
        "origin": safe_origin,
        "origin_kind": origin_kind,
        "loader": type(spec.loader).__name__ if spec.loader is not None else None,
        "search_locations": search_locations,
    }


def _git_state(project_root: Path, include_commit: bool) -> dict[str, Any]:
    """Use fixed, read-only Git commands; never invoke a shell or arbitrary command."""
    git = shutil.which("git")
    if git is None:
        return {"checked": False, "available": False}

    def run(args: list[str]) -> subprocess.CompletedProcess[str] | None:
        try:
            return subprocess.run(
                [git, "-c", "core.fsmonitor=false", "-C", str(project_root), *args],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=2.0,
                shell=False,
                stdin=subprocess.DEVNULL,
                env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
            )
        except (OSError, subprocess.TimeoutExpired):
            return None

    inside = run(["rev-parse", "--is-inside-work-tree"])
    if inside is None or inside.returncode != 0 or inside.stdout.strip() != "true":
        return {"checked": True, "available": True, "in_repo": False}
    status = run(["status", "--porcelain", "--untracked-files=no"])
    status_checked = status is not None and status.returncode == 0
    result: dict[str, Any] = {
        "checked": True,
        "available": True,
        "in_repo": True,
        "status_checked": status_checked,
        "dirty": bool(status.stdout.strip()) if status_checked and status is not None else None,
    }
    if include_commit:
        commit = run(["rev-parse", "--verify", "HEAD"])
        result["commit"] = commit.stdout.strip() if commit and commit.returncode == 0 else None
    else:
        result["commit"] = None
    return result


def capture_snapshot(
    project: str | os.PathLike[str] = ".",
    *,
    modules: Iterable[str] = (),
    include_commit: bool = False,
    include_git: bool = True,
) -> dict[str, Any]:
    """Capture current interpreter and project evidence without reading source files."""
    raw_project = Path(project).expanduser()
    try:
        project_root = raw_project.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise EnvProofError(f"Project path does not exist or cannot be resolved: {raw_project!r}") from exc
    if not project_root.is_dir():
        raise EnvProofError(f"Project path is not a directory: {project_root}")

    module_names = list(dict.fromkeys(modules))
    if len(module_names) > MAX_MODULES:
        raise EnvProofError(f"At most {MAX_MODULES} module names may be inspected per snapshot.")
    roots = _roots(project_root)
    py_path_value = os.environ.get("PYTHONPATH")
    path_value = os.environ.get("PATH", "")
    site_paths: list[str] = []
    try:
        site_paths.extend(str(p) for p in site.getsitepackages())
    except (AttributeError, OSError):
        pass
    try:
        user_site = site.getusersitepackages()
        if isinstance(user_site, str):
            site_paths.append(user_site)
        else:
            site_paths.extend(str(value) for value in user_site)
    except (AttributeError, OSError):
        pass

    sys_path = []
    for raw in sys.path:
        if raw == "":
            absolute = str(Path.cwd())
            original = ""
        else:
            absolute = raw
            original = raw
        sys_path.append(
            {
                "path": _safe_path(absolute, roots),
                "kind": _classify_path(absolute, project_root, roots),
                "empty_entry": original == "",
            }
        )

    path_python = shutil.which("python")
    path_python3 = shutil.which("python3")
    extension_suffix = sysconfig.get_config_var("EXT_SUFFIX")
    extension_suffix = str(extension_suffix) if extension_suffix else None

    git = _git_state(project_root, include_commit) if include_git else {"checked": False, "available": False}
    snapshot: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "tool": {"name": "envproof", "version": __version__},
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": {
            "version": platform.python_version(),
            "version_info": [sys.version_info.major, sys.version_info.minor, sys.version_info.micro],
            "implementation": platform.python_implementation(),
            "compiler": platform.python_compiler(),
            "executable": _safe_path(sys.executable, roots),
            "prefix": _safe_path(sys.prefix, roots),
            "base_prefix": _safe_path(sys.base_prefix, roots),
            "is_venv": sys.prefix != sys.base_prefix,
            "cache_tag": getattr(sys.implementation, "cache_tag", None),
            "soabi": sysconfig.get_config_var("SOABI"),
            "extension_suffix": extension_suffix,
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "architecture": platform.architecture()[0],
            "libc": list(platform.libc_ver()),
        },
        "paths": {
            "sys_path": sys_path,
            "site_packages": [path for path in (_safe_path(item, roots) for item in site_paths) if path],
            "python_on_path": {
                "python": _safe_path(path_python, roots),
                "python3": _safe_path(path_python3, roots),
            },
            "path_entry_count": len(path_value.split(os.pathsep)) if path_value else 0,
            "path_entries": sanitize_path_entries(
                path_value,
                project_root=roots["project_root"],
                prefix=roots["prefix"],
                base_prefix=roots["base_prefix"],
                home=roots["home"],
            ),
            "pythonpath_entries": sanitize_path_entries(
                py_path_value,
                project_root=roots["project_root"],
                prefix=roots["prefix"],
                base_prefix=roots["base_prefix"],
                home=roots["home"],
            ),
        },
        "environment": {"flags": safe_environment_flags()},
        "packages": _distribution_inventory(project_root, roots),
        "project": {
            "root": "$PROJECT",
            "files": _project_file_fingerprints(project_root),
            "git": git,
        },
        "modules": [_module_resolution(name, project_root, roots) for name in module_names],
        "privacy": {
            "environment_values_included": False,
            "source_file_contents_included": False,
            "network_requests_made": False,
            "commit_hash_included_by_request": bool(include_commit and git.get("in_repo") and git.get("commit")),
            "notes": [
                "Environment variable values are never captured.",
                "Project file contents are never captured; selected manifest files are represented "
                "by size and SHA-256 only.",
                "Known home, project, interpreter and virtual-environment roots are redacted where possible.",
                "Review path and manifest metadata before sharing snapshots externally.",
            ],
        },
    }
    return snapshot


def write_snapshot(snapshot: dict[str, Any], output: str | os.PathLike[str], *, force: bool = False) -> Path:
    """Validate and write JSON atomically, refusing accidental overwrite by default."""
    validate_snapshot(snapshot)
    try:
        serialized = json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    except (TypeError, ValueError) as exc:
        raise EnvProofError("Snapshot contains values that cannot be represented as JSON.") from exc
    return atomic_write_text(output, serialized, force=force, label="snapshot")


MAX_SNAPSHOT_BYTES = 20 * 1024 * 1024


def load_snapshot(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Load a bounded EnvProof JSON snapshot without executing its contents."""
    source = Path(path).expanduser()
    try:
        with source.open("rb") as handle:
            raw = handle.read(MAX_SNAPSHOT_BYTES + 1)
        if len(raw) > MAX_SNAPSHOT_BYTES:
            raise EnvProofError(f"Snapshot is larger than {MAX_SNAPSHOT_BYTES // (1024 * 1024)} MiB: {source}")
        text = raw.decode("utf-8")
        data = json.loads(text)
    except EnvProofError:
        raise
    except FileNotFoundError as exc:
        raise EnvProofError(f"Snapshot not found: {source}") from exc
    except (OSError, RecursionError, ValueError) as exc:
        raise EnvProofError(f"Cannot read valid JSON from {str(source)!r}: {exc}") from exc
    validate_snapshot(data, source)
    return data


def validate_snapshot(data: Any, source: Path | None = None) -> None:
    """Validate fields consumed by comparisons and renderers.

    Validation is deliberately structural: snapshot values are evidence and are
    never interpreted as code or trusted as proof of root cause.
    """
    label = str(source) if source is not None else "snapshot"
    if not isinstance(data, dict):
        raise EnvProofError(f"Invalid {label}: top-level JSON value must be an object.")
    schema = data.get("schema_version")
    if type(schema) is not int or schema != SCHEMA_VERSION:
        raise EnvProofError(
            f"Unsupported {label} schema_version {schema!r}; EnvProof supports schema version {SCHEMA_VERSION}."
        )

    required_objects = ("python", "platform", "paths", "environment", "project", "privacy")
    for key in required_objects:
        if not isinstance(data.get(key), dict):
            raise EnvProofError(f"Invalid {label}: field {key!r} must be an object.")
    for key in ("packages", "modules"):
        value = data.get(key)
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            raise EnvProofError(f"Invalid {label}: field {key!r} must be a list of objects.")

    python = data["python"]
    if not isinstance(python.get("version"), str):
        raise EnvProofError(f"Invalid {label}: 'python.version' must be a string.")
    version_info = python.get("version_info")
    if version_info is not None and (
        not isinstance(version_info, list)
        or len(version_info) < 2
        or not all(type(item) is int and item >= 0 for item in version_info)
    ):
        raise EnvProofError(f"Invalid {label}: 'python.version_info' must be a list of non-negative integers.")

    paths = data["paths"]
    if not isinstance(paths.get("sys_path", []), list):
        raise EnvProofError(f"Invalid {label}: 'paths.sys_path' must be a list.")
    if not isinstance(paths.get("python_on_path", {}), dict):
        raise EnvProofError(f"Invalid {label}: 'paths.python_on_path' must be an object.")
    if not isinstance(data["environment"].get("flags", {}), dict):
        raise EnvProofError(f"Invalid {label}: 'environment.flags' must be an object.")
    if not isinstance(data["project"].get("files", []), list):
        raise EnvProofError(f"Invalid {label}: 'project.files' must be a list.")
    if not all(isinstance(item, dict) for item in data["project"].get("files", [])):
        raise EnvProofError(f"Invalid {label}: each 'project.files' entry must be an object.")
    if not isinstance(data["project"].get("git", {}), dict):
        raise EnvProofError(f"Invalid {label}: 'project.git' must be an object.")

    git = data["project"].get("git", {})
    for field in ("checked", "available", "in_repo", "dirty", "status_checked"):
        if field in git and git[field] is not None and type(git[field]) is not bool:
            raise EnvProofError(f"Invalid {label}: 'project.git.{field}' must be a boolean or null.")
    if "commit" in git and git["commit"] is not None and not isinstance(git["commit"], str):
        raise EnvProofError(f"Invalid {label}: 'project.git.commit' must be a string or null.")

    for index, package in enumerate(data["packages"]):
        for field in ("name", "normalized_name", "version"):
            if field in package and not isinstance(package[field], str):
                raise EnvProofError(f"Invalid {label}: packages[{index}].{field} must be a string.")
    for index, module in enumerate(data["modules"]):
        if "name" in module and not isinstance(module["name"], str):
            raise EnvProofError(f"Invalid {label}: modules[{index}].name must be a string.")
        if "found" in module and type(module["found"]) is not bool:
            raise EnvProofError(f"Invalid {label}: modules[{index}].found must be a boolean.")
