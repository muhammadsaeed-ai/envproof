from __future__ import annotations

import json
import unittest

from envproof.report import render_findings, render_json, render_markdown_report
from tests.helpers import copy_snapshot


class ReportTests(unittest.TestCase):
    def test_markdown_report_omits_secrets_and_truncates_package_list(self) -> None:
        current = copy_snapshot()
        current["environment"]["flags"]["PRIVATE_TOKEN"] = True
        current["packages"] = [
            {"name": f"package-{index}", "version": "1.0", "location_kind": "third-party"} for index in range(5)
        ]
        report = render_markdown_report(current, max_packages=2)
        self.assertIn("Showing 2 of 5", report)
        self.assertIn("Variable values are deliberately omitted", report)
        self.assertNotIn("private-secret", report)

    def test_render_findings_empty_and_nonempty(self) -> None:
        self.assertIn("No diagnostic differences", render_findings([]))
        finding = {
            "code": "EXAMPLE",
            "severity": "warning",
            "summary": "Example finding",
            "evidence": ["evidence"],
            "explanation": "why",
            "next_step": "do this",
        }
        rendered = render_findings([finding])
        self.assertIn("Example finding", rendered)
        self.assertIn("Suggested next step", rendered)

    def test_json_renderer_is_valid_json(self) -> None:
        data = {"hello": "world", "count": 2}
        self.assertEqual(json.loads(render_json(data)), data)


if __name__ == "__main__":
    unittest.main()
