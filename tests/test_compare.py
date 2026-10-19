from __future__ import annotations

import unittest

from envproof.compare import compare_snapshots, fail_level
from envproof.errors import EnvProofError
from tests.helpers import copy_snapshot


class CompareTests(unittest.TestCase):
    def test_identical_snapshots_have_no_findings(self) -> None:
        left = copy_snapshot()
        right = copy_snapshot()
        self.assertEqual(compare_snapshots(left, right), [])

    def test_detects_python_minor_version_mismatch_as_high(self) -> None:
        left = copy_snapshot()
        right = copy_snapshot()
        right["python"]["version"] = "3.13.0"
        right["python"]["version_info"] = [3, 13, 0]
        findings = compare_snapshots(left, right)
        finding = next(item for item in findings if item["code"] == "PYTHON_VERSION_MISMATCH")
        self.assertEqual(finding["severity"], "high")
        self.assertTrue(fail_level(findings, "high"))
        self.assertTrue(fail_level(findings, "warning"))
        self.assertFalse(fail_level(findings, "never"))

    def test_detects_package_added_removed_and_version_diff(self) -> None:
        left = copy_snapshot()
        right = copy_snapshot()
        right["packages"] = [
            {
                "name": "requests",
                "normalized_name": "requests",
                "version": "2.32.0",
                "location": "$VENV/site-packages",
                "location_kind": "environment-packages",
            },
            {
                "name": "rich",
                "normalized_name": "rich",
                "version": "13.9.0",
                "location": "$VENV/site-packages",
                "location_kind": "environment-packages",
            },
        ]
        codes = {item["code"] for item in compare_snapshots(left, right)}
        self.assertIn("PACKAGE_VERSION_DIFFERS", codes)
        self.assertIn("PACKAGE_MISSING_CURRENT", codes)  # urllib3
        self.assertIn("PACKAGE_ADDED_CURRENT", codes)  # rich

    def test_detects_changed_lockfile_and_import_origin(self) -> None:
        left = copy_snapshot()
        right = copy_snapshot()
        right["project"]["files"][1]["sha256"] = "c" * 64
        right["modules"][0]["origin"] = "$PROJECT/requests.py"
        right["modules"][0]["origin_kind"] = "project"
        codes = {item["code"] for item in compare_snapshots(left, right)}
        self.assertIn("PROJECT_MANIFEST_CHANGED", codes)
        self.assertIn("IMPORT_ORIGIN_CHANGED", codes)

    def test_environment_flag_diff_does_not_show_values(self) -> None:
        left = copy_snapshot()
        right = copy_snapshot()
        right["environment"]["flags"]["PYTHONPATH"] = True
        findings = compare_snapshots(left, right)
        finding = next(item for item in findings if item["code"] == "ENVIRONMENT_FLAGS_DIFFER")
        self.assertIn("PYTHONPATH", repr(finding))
        self.assertNotIn("https://", repr(finding))

    def test_path_order_diff_is_detected(self) -> None:
        left = copy_snapshot()
        right = copy_snapshot()
        right["paths"]["sys_path"].reverse()
        codes = {item["code"] for item in compare_snapshots(left, right)}
        self.assertIn("SYS_PATH_DIFFERS", codes)

    def test_commit_change_only_reported_when_both_commits_present(self) -> None:
        left = copy_snapshot()
        right = copy_snapshot()
        left["project"]["git"]["commit"] = "a" * 40
        right["project"]["git"]["commit"] = "b" * 40
        codes = {item["code"] for item in compare_snapshots(left, right)}
        self.assertIn("GIT_COMMIT_DIFFERS", codes)

    def test_rejects_unsupported_snapshot(self) -> None:
        with self.assertRaises(EnvProofError):
            compare_snapshots({"schema_version": 99}, copy_snapshot())

    def test_findings_are_stably_sorted(self) -> None:
        left = copy_snapshot()
        right = copy_snapshot()
        right["python"]["version_info"] = [3, 13, 0]
        right["python"]["version"] = "3.13.0"
        right["platform"]["system"] = "Windows"
        first = compare_snapshots(left, right)
        second = compare_snapshots(left, right)
        self.assertEqual(first, second)
        self.assertEqual(
            first,
            sorted(
                first,
                key=lambda item: (
                    {"high": 3, "warning": 2, "info": 1}[item["severity"]] * -1,
                    item["code"],
                    item["summary"],
                ),
            ),
        )


if __name__ == "__main__":
    unittest.main()
