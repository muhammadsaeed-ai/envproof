"""Privacy helpers. Values of environment variables are never serialized."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from pathlib import Path


def _normalized(path: str) -> str:
    """Normalize a path without requiring it to exist, resolving aliases when possible."""
    expanded = os.path.expanduser(path)
    try:
        return os.path.normpath(str(Path(expanded).resolve(strict=False)))
    except (OSError, RuntimeError, ValueError):
        try:
            return os.path.normpath(os.path.abspath(expanded))
        except (OSError, RuntimeError, ValueError):
            return os.path.normpath(expanded)


def _is_at_or_below(path: str, base: str) -> bool:
    """Case-aware path containment that works on Windows and POSIX."""
    path_cmp = os.path.normcase(path)
    base_cmp = os.path.normcase(base)
    try:
        return os.path.commonpath([path_cmp, base_cmp]) == base_cmp
    except (OSError, ValueError):
        return path_cmp == base_cmp


def redact_path(
    path: str | os.PathLike[str] | None,
    *,
    project_root: str | os.PathLike[str] | None = None,
    prefix: str | os.PathLike[str] | None = None,
    base_prefix: str | os.PathLike[str] | None = None,
    home: str | os.PathLike[str] | None = None,
) -> str | None:
    """Replace sensitive roots with stable tokens while retaining useful suffixes.

    The longest roots are replaced first, so a virtual environment nested inside a
    home directory is represented as ``$VENV`` rather than leaking its parent.
    Paths outside known roots are still emitted; callers should review exported
    reports before sharing them.
    """
    if path is None:
        return None
    raw = os.fspath(path)
    if raw == "":
        return raw
    normalized = _normalized(raw)
    roots: list[tuple[str, str]] = []
    for candidate, label in (
        (project_root, "$PROJECT"),
        (prefix, "$VENV"),
        (base_prefix, "$BASE_PYTHON"),
        (home, "$HOME"),
    ):
        if candidate is None:
            continue
        try:
            root = _normalized(os.fspath(candidate))
        except (OSError, RuntimeError, ValueError):
            continue
        if root and root not in (os.sep, "."):
            roots.append((root, label))
    roots.sort(key=lambda item: len(item[0]), reverse=True)
    for root, label in roots:
        if _is_at_or_below(normalized, root):
            try:
                relative = os.path.relpath(normalized, root)
            except ValueError:
                relative = "."
            if relative == ".":
                return label
            return label.rstrip("/") + "/" + relative.replace("\\", "/")
    return normalized.replace("\\", "/")


def safe_environment_flags(
    environ: Mapping[str, str] | None = None,
) -> dict[str, bool]:
    """Capture presence only for variables often relevant to Python diagnostics.

    Variable values are intentionally excluded to prevent leaking credentials,
    endpoints, local paths, or other configuration values.
    """
    source = os.environ if environ is None else environ
    names = (
        "PYTHONHOME",
        "PYTHONPATH",
        "PYTHONNOUSERSITE",
        "PYTHONSAFEPATH",
        "VIRTUAL_ENV",
        "CONDA_PREFIX",
        "CONDA_DEFAULT_ENV",
        "UV_PROJECT_ENVIRONMENT",
        "PIP_CONFIG_FILE",
        "PIP_INDEX_URL",
        "PIP_EXTRA_INDEX_URL",
        "CUDA_HOME",
        "CUDA_PATH",
        "LD_LIBRARY_PATH",
        "DYLD_LIBRARY_PATH",
        "CMAKE_PREFIX_PATH",
        "OMP_NUM_THREADS",
    )
    # Do not report whether index URLs were set: that could unnecessarily expose
    # private-index configuration. Treat the presence as a generic pip setting.
    flags = {name: name in source for name in names if name not in {"PIP_INDEX_URL", "PIP_EXTRA_INDEX_URL"}}
    flags["PIP_INDEX_CONFIGURATION_PRESENT"] = any(
        name in source for name in ("PIP_INDEX_URL", "PIP_EXTRA_INDEX_URL", "PIP_CONFIG_FILE")
    )
    return dict(sorted(flags.items()))


def sanitize_path_entries(
    raw_value: str | None,
    *,
    project_root: str,
    prefix: str,
    base_prefix: str,
    home: str,
    limit: int = 40,
) -> list[str]:
    """Return sanitized PATH/PYTHONPATH entries, bounded to avoid huge reports."""
    if not raw_value:
        return []
    entries = raw_value.split(os.pathsep)
    sanitized: list[str] = []
    for entry in entries[:limit]:
        if not entry:
            sanitized.append("<empty-entry>")
            continue
        redacted = redact_path(
            entry,
            project_root=project_root,
            prefix=prefix,
            base_prefix=base_prefix,
            home=home,
        )
        sanitized.append(redacted or "")
    if len(entries) > limit:
        sanitized.append(f"<truncated:{len(entries) - limit}-more>")
    return sanitized


def redact_text(text: str, *, home: str | None = None, project_root: str | None = None) -> str:
    """Redact common absolute path roots from command output before reporting it."""
    result = text
    roots: Iterable[tuple[str | None, str]] = ((project_root, "$PROJECT"), (home, "$HOME"))
    for root, token in sorted(
        ((root, token) for root, token in roots if root),
        key=lambda pair: len(pair[0] or ""),
        reverse=True,
    ):
        assert root is not None
        normalized = _normalized(root)
        result = result.replace(normalized, token)
        result = result.replace(normalized.replace("/", "\\"), token)
    return result
