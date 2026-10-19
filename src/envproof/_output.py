"""Safe, atomic output writing shared by the snapshot and CLI layers."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from envproof.errors import EnvProofError


def atomic_write_text(
    output: str | os.PathLike[str],
    content: str,
    *,
    force: bool = False,
    label: str = "output",
) -> Path:
    """Write UTF-8 text atomically, refusing clobbering unless explicitly allowed.

    A temporary file is created beside the target so publication stays on one
    filesystem. Without ``force``, a hard-link publish provides atomic
    no-clobber behavior even if another process creates the target concurrently.
    """
    target = Path(output).expanduser()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError) as exc:
        raise EnvProofError(f"Cannot create output directory {str(target.parent)!r}: {exc}") from exc

    target_path = target.absolute()
    if os.path.lexists(target_path) and not force:
        raise EnvProofError(f"Output already exists: {str(target)!r}. Use --force to replace it.")

    descriptor: int | None = None
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.envproof-",
            suffix=".tmp",
            dir=str(target_path.parent),
        )
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            descriptor = None
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())

        if force:
            os.replace(temporary, target_path)
        else:
            try:
                os.link(temporary, target_path)
            except FileExistsError as exc:
                raise EnvProofError(f"Output already exists: {str(target)!r}. Use --force to replace it.") from exc
            except (OSError, ValueError) as exc:
                raise EnvProofError(
                    f"Cannot safely create {label} at {str(target)!r} without overwrite protection: {exc}. "
                    "Choose a filesystem that supports hard links or use --force only if replacement is intended."
                ) from exc
            temporary.unlink()
        return target_path
    except EnvProofError:
        raise
    except (OSError, ValueError) as exc:
        raise EnvProofError(f"Could not write {label} {str(target)!r}: {exc}") from exc
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
