from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from envproof.capture import _git_state, capture_snapshot, load_snapshot, write_snapshot
from envproof.errors import EnvProofError


class CaptureTests(unittest.TestCase):
    def test_capture_has_required_sections_and_sorted_packages(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            (project / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            snapshot = capture_snapshot(project, include_git=False)
        self.assertEqual(snapshot["schema_version"], 1)
        for key in ("python", "platform", "paths", "environment", "packages", "project", "modules", "privacy"):
            self.assertIn(key, snapshot)
        packages = snapshot["packages"]
        self.assertEqual(
            packages,
            sorted(packages, key=lambda x: (x["normalized_name"], x["version"], x["location"] or "")),
        )
        self.assertIn("pyproject.toml", [item["name"] for item in snapshot["project"]["files"]])

    def test_capture_does_not_include_environment_values_or_dotenv_contents(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            (project / "pyproject.toml").write_text("[project]\nname='private-project-name'\n", encoding="utf-8")
            (project / ".env").write_text("API_TOKEN=not-for-sharing\n", encoding="utf-8")
            with patch.dict(os.environ, {"PRIVATE_TOKEN": "ultra-secret-value", "PYTHONPATH": str(project)}):
                snapshot = capture_snapshot(project, include_git=False)
        serialized = json.dumps(snapshot)
        self.assertNotIn("ultra-secret-value", serialized)
        self.assertNotIn("not-for-sharing", serialized)
        self.assertNotIn("private-project-name", serialized)
        self.assertNotIn(".env", [item["name"] for item in snapshot["project"]["files"]])
        self.assertTrue(snapshot["environment"]["flags"]["PYTHONPATH"])
        self.assertFalse(snapshot["privacy"]["environment_values_included"])

    def test_capture_manifest_hash_changes_with_content_without_content_capture(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            manifest = project / "requirements.txt"
            manifest.write_text("example-package==1.2.3\n", encoding="utf-8")
            one = capture_snapshot(project, include_git=False)
            manifest.write_text("example-package==1.2.4\n", encoding="utf-8")
            two = capture_snapshot(project, include_git=False)
        one_manifest = next(item for item in one["project"]["files"] if item["name"] == "requirements.txt")
        two_manifest = next(item for item in two["project"]["files"] if item["name"] == "requirements.txt")
        self.assertNotEqual(one_manifest["sha256"], two_manifest["sha256"])
        self.assertNotIn("example-package==1.2.3", json.dumps(one))

    def test_module_lookup_does_not_execute_module_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            marker = project / "executed.txt"
            (project / "probe_noexec.py").write_text(
                f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n", encoding="utf-8"
            )
            with patch("envproof.capture.sys.path", [str(project.resolve()), *list(__import__("sys").path)]):
                snapshot = capture_snapshot(project, modules=["probe_noexec"], include_git=False)
            result = snapshot["modules"][0]
            self.assertTrue(result["found"])
            self.assertTrue(str(result["origin"]).startswith("$PROJECT/"))
            self.assertFalse(marker.exists(), "module code must not execute during origin inspection")

    def test_invalid_module_names_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(EnvProofError, "top-level import name"):
                capture_snapshot(temp, modules=["package.submodule"], include_git=False)
            with self.assertRaisesRegex(EnvProofError, "Invalid module name"):
                capture_snapshot(temp, modules=["../escape"], include_git=False)

    def test_missing_project_is_actionable_error(self) -> None:
        with self.assertRaisesRegex(EnvProofError, "does not exist"):
            capture_snapshot("/unlikely/path/envproof-does-not-exist", include_git=False)

    def test_snapshot_write_refuses_overwrite_unless_forced(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "snapshot.json"
            snapshot = capture_snapshot(temp, include_git=False)
            write_snapshot(snapshot, path)
            with self.assertRaisesRegex(EnvProofError, "already exists"):
                write_snapshot(snapshot, path)
            write_snapshot(snapshot, path, force=True)
            self.assertEqual(load_snapshot(path)["schema_version"], 1)

    def test_snapshot_loader_rejects_invalid_json_and_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            malformed = Path(temp) / "bad.json"
            malformed.write_text("{nope", encoding="utf-8")
            with self.assertRaisesRegex(EnvProofError, "valid JSON"):
                load_snapshot(malformed)
            malformed.write_text('{"schema_version": 99}', encoding="utf-8")
            with self.assertRaisesRegex(EnvProofError, "Unsupported"):
                load_snapshot(malformed)

    def test_snapshot_loader_bounds_actual_read_not_only_file_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            oversized = Path(temp) / "oversized.json"
            oversized.write_bytes(b"{" + b" " * 64 + b"}")
            with patch("envproof.capture.MAX_SNAPSHOT_BYTES", 32):
                with self.assertRaisesRegex(EnvProofError, "larger than"):
                    load_snapshot(oversized)

    def test_capture_rejects_invalid_path_without_traceback(self) -> None:
        with self.assertRaisesRegex(EnvProofError, "cannot be resolved"):
            capture_snapshot("\x00", include_git=False)

    def test_git_status_failure_is_unknown_not_clean_and_disables_fsmonitor(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            inside_repo = subprocess.CompletedProcess(args=["git"], returncode=0, stdout="true\n", stderr="")
            failed_status = subprocess.CompletedProcess(args=["git"], returncode=128, stdout="", stderr="failed")
            with (
                patch("envproof.capture.shutil.which", return_value="/usr/bin/git"),
                patch("envproof.capture.subprocess.run", side_effect=[inside_repo, failed_status]) as run,
            ):
                state = _git_state(Path(temp), include_commit=False)

        self.assertTrue(state["in_repo"])
        self.assertFalse(state["status_checked"])
        self.assertIsNone(state["dirty"])
        for call in run.call_args_list:
            self.assertFalse(call.kwargs["shell"])
            self.assertEqual(call.kwargs["env"]["GIT_OPTIONAL_LOCKS"], "0")
            self.assertIn("core.fsmonitor=false", call.args[0])

    def test_write_snapshot_rejects_malformed_document(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(EnvProofError, "field .python."):
                write_snapshot({"schema_version": 1}, Path(temp) / "invalid.json")

    def test_snapshot_loader_rejects_malformed_nested_types(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "malformed.json"
            snapshot = capture_snapshot(temp, include_git=False)
            snapshot["python"]["version_info"] = "3.13.5"
            path.write_text(json.dumps(snapshot), encoding="utf-8")
            with self.assertRaisesRegex(EnvProofError, "version_info"):
                load_snapshot(path)

    def test_manifest_file_size_limit_is_reported_without_reading_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            file = project / "pyproject.toml"
            file.write_bytes(b"x" * (5 * 1024 * 1024 + 1))
            snapshot = capture_snapshot(project, include_git=False)
            item = next(item for item in snapshot["project"]["files"] if item["name"] == "pyproject.toml")
            self.assertEqual(item["status"], "too-large")


if __name__ == "__main__":
    unittest.main()
