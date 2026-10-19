"""Create two temporary project snapshots and demonstrate a real manifest drift.

Run after installing EnvProof (``python -m pip install -e .``) with
``python examples/demo_drift.py``. The demo reads the current interpreter's real
package metadata but uses synthetic project manifest content and writes no files
outside a temporary directory.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from envproof.capture import capture_snapshot
from envproof.compare import compare_snapshots
from envproof.report import render_findings


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="envproof-demo-") as temporary:
        root = Path(temporary)
        baseline_project = root / "baseline-project"
        current_project = root / "current-project"
        baseline_project.mkdir()
        current_project.mkdir()
        (baseline_project / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")
        (current_project / "requirements.txt").write_text("requests==2.32.0\n", encoding="utf-8")

        baseline = capture_snapshot(baseline_project, modules=("json",), include_git=False)
        current = capture_snapshot(current_project, modules=("json",), include_git=False)
        findings = compare_snapshots(baseline, current)
        print("Controlled scenario: the synthetic requirements file changed between projects.\n")
        print(render_findings(findings, title="EnvProof reproducible drift demo"))
        observed = {finding["code"] for finding in findings}
        if "PROJECT_MANIFEST_CHANGED" not in observed:
            print("Demo verification failed: the expected manifest difference was not detected.")
            return 1
        print("Demo assertion passed: the changed requirements manifest was detected.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
