from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from envproof.cli import main


class CLITests(unittest.TestCase):
    def invoke(self, args: list[str]) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(args)
        return code, out.getvalue(), err.getvalue()

    def test_version_option(self) -> None:
        code, out, err = self.invoke(["--version"])
        self.assertEqual(code, 0)
        self.assertIn("EnvProof 0.1.0", out)
        self.assertEqual(err, "")

    def test_end_to_end_capture_report_compare_and_ci_exit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "project"
            project.mkdir()
            (project / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
            first = root / "first.json"
            second = root / "second.json"
            report = root / "report.md"

            code, out, err = self.invoke(["capture", str(project), "--output", str(first), "--no-git"])
            self.assertEqual((code, err), (0, ""), out + err)
            self.assertTrue(first.exists())

            code, out, err = self.invoke(["report", str(first), "--output", str(report)])
            self.assertEqual((code, err), (0, ""), out + err)
            self.assertIn("EnvProof diagnostic report", report.read_text(encoding="utf-8"))

            first_obj = json.loads(first.read_text(encoding="utf-8"))
            first_obj["python"]["version_info"] = [0, 0, 0]
            first_obj["python"]["version"] = "0.0.0"
            second.write_text(json.dumps(first_obj), encoding="utf-8")
            code, out, err = self.invoke(["compare", str(first), str(second), "--format", "json", "--fail-on", "high"])
            self.assertEqual(code, 1)
            self.assertEqual(err, "")
            payload = json.loads(out)
            self.assertTrue(any(item["code"] == "PYTHON_VERSION_MISMATCH" for item in payload["findings"]))

    def test_help_returns_zero_from_programmatic_entrypoint(self) -> None:
        code, out, err = self.invoke(["--help"])
        self.assertEqual(code, 0)
        self.assertIn("Capture and compare", out)
        self.assertEqual(err, "")

    def test_invalid_output_path_is_reported_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            code, out, err = self.invoke(["capture", temp, "--output", "\x00", "--no-git"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("error:", err)
        self.assertNotIn("Traceback", err)

    def test_markdown_audit_has_valid_heading(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            code, out, err = self.invoke(["audit", temp, "--format", "markdown", "--no-git"])
        self.assertEqual((code, err), (0, ""), err)
        self.assertTrue(out.startswith("# EnvProof local audit\n\n"))
        self.assertNotIn("===================", out)

    def test_output_overwrite_requires_force(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "one.json"
            code, _, err = self.invoke(["capture", temp, "-o", str(output), "--no-git"])
            self.assertEqual(code, 0, err)
            code, _, err = self.invoke(["capture", temp, "-o", str(output), "--no-git"])
            self.assertEqual(code, 2)
            self.assertIn("Use --force", err)

    def test_audit_json_output_is_parseable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            code, out, err = self.invoke(["audit", temp, "--format", "json", "--no-git"])
            self.assertEqual((code, err), (0, ""), err)
            payload = json.loads(out)
            self.assertEqual(payload["mode"], "audit")
            self.assertIn("findings", payload)

    def test_invalid_manifest_path_returns_nonzero_and_safe_message(self) -> None:
        code, out, err = self.invoke(["capture", "/definitely/not/a/project", "-o", "/tmp/never.json"])
        self.assertEqual(code, 2)
        self.assertIn("error:", err)
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
