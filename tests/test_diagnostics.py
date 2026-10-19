from __future__ import annotations

import unittest

from envproof.diagnostics import audit_snapshot
from tests.helpers import copy_snapshot


class DiagnosticTests(unittest.TestCase):
    def test_detects_pythonhome_and_pythonpath_presence(self) -> None:
        current = copy_snapshot()
        current["environment"]["flags"]["PYTHONHOME"] = True
        current["environment"]["flags"]["PYTHONPATH"] = True
        codes = {item["code"] for item in audit_snapshot(current)}
        self.assertIn("PYTHONHOME_SET", codes)
        self.assertIn("PYTHONPATH_SET", codes)

    def test_detects_virtual_env_mismatch(self) -> None:
        current = copy_snapshot()
        current["python"]["is_venv"] = False
        current["environment"]["flags"]["VIRTUAL_ENV"] = True
        codes = {item["code"] for item in audit_snapshot(current)}
        self.assertIn("VIRTUAL_ENV_INTERPRETER_MISMATCH", codes)

    def test_detects_standard_library_shadowing(self) -> None:
        current = copy_snapshot()
        current["modules"] = [
            {"name": "json", "found": True, "origin": "$PROJECT/json.py", "origin_kind": "project"}
        ]
        codes = {item["code"] for item in audit_snapshot(current)}
        self.assertIn("STDLIB_MODULE_SHADOWED_BY_PROJECT", codes)

    def test_local_first_party_import_is_informational(self) -> None:
        current = copy_snapshot()
        current["modules"] = [
            {"name": "my_app", "found": True, "origin": "$PROJECT/my_app.py", "origin_kind": "project"}
        ]
        findings = audit_snapshot(current)
        self.assertIn("MODULE_RESOLVES_INSIDE_PROJECT", {item["code"] for item in findings})
        self.assertEqual(
            next(item for item in findings if item["code"] == "MODULE_RESOLVES_INSIDE_PROJECT")["severity"],
            "info",
        )

    def test_no_known_hazards_returns_empty_list(self) -> None:
        current = copy_snapshot()
        current["modules"] = []
        self.assertEqual(audit_snapshot(current), [])


if __name__ == "__main__":
    unittest.main()
