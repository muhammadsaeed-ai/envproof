"""Small local smoke benchmark; reports measured results, never asserts speed claims."""

from __future__ import annotations

import json
import platform
import sys
import tempfile
import time
from pathlib import Path

from envproof.capture import capture_snapshot
from envproof.compare import compare_snapshots


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="envproof-benchmark-") as temporary:
        project = Path(temporary)
        (project / "pyproject.toml").write_text("[project]\nname='benchmark-fixture'\n", encoding="utf-8")
        start = time.perf_counter()
        baseline = capture_snapshot(project, modules=("json", "pathlib"), include_git=False)
        capture_seconds = time.perf_counter() - start
        current = json.loads(json.dumps(baseline))
        current["python"]["version"] = "benchmark-different-version"
        current["python"]["version_info"] = [0, 0, 0]
        start = time.perf_counter()
        findings = compare_snapshots(baseline, current)
        compare_seconds = time.perf_counter() - start
        if not findings:
            raise RuntimeError("Synthetic Python-version drift was not detected")
        print(
            json.dumps(
                {
                    "python": sys.version.split()[0],
                    "implementation": platform.python_implementation(),
                    "platform": platform.platform(),
                    "distribution_records": len(baseline["packages"]),
                    "manifest_records": len(baseline["project"]["files"]),
                    "module_probes": len(baseline["modules"]),
                    "capture_seconds": round(capture_seconds, 6),
                    "compare_seconds": round(compare_seconds, 6),
                    "comparison_findings": len(findings),
                    "method": "single local smoke run; not a statistically rigorous benchmark",
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
