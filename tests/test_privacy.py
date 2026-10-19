from __future__ import annotations

import os
import unittest

from envproof.privacy import redact_path, safe_environment_flags, sanitize_path_entries


class PrivacyTests(unittest.TestCase):
    def test_redacts_home_prefix_and_project_roots(self) -> None:
        rendered = redact_path(
            "/home/alice/work/app/.venv/lib/python/site-packages",
            project_root="/home/alice/work/app",
            prefix="/home/alice/work/app/.venv",
            base_prefix="/usr/local/python",
            home="/home/alice",
        )
        self.assertEqual(rendered, "$VENV/lib/python/site-packages")
        self.assertNotIn("alice", rendered or "")

    def test_environment_values_are_never_returned(self) -> None:
        env = {
            "PYTHONPATH": "/private/code",
            "API_TOKEN": "super-secret",
            "PIP_INDEX_URL": "https://user:pass@example.invalid/simple",
        }
        flags = safe_environment_flags(env)
        joined = repr(flags)
        self.assertNotIn("super-secret", joined)
        self.assertNotIn("example.invalid", joined)
        self.assertTrue(flags["PYTHONPATH"])
        self.assertTrue(flags["PIP_INDEX_CONFIGURATION_PRESENT"])
        self.assertNotIn("PIP_INDEX_URL", flags)

    def test_unknown_environment_keys_are_not_captured(self) -> None:
        flags = safe_environment_flags({"DATABASE_URL": "postgres://private", "PRIVATE_TOKEN": "x"})
        self.assertNotIn("DATABASE_URL", flags)
        self.assertNotIn("PRIVATE_TOKEN", flags)
        self.assertFalse(flags["PYTHONPATH"])

    def test_path_entries_are_bounded_and_redacted(self) -> None:
        value = os.pathsep.join(["/home/alice/a", "/home/alice/b", "/opt/python"])
        output = sanitize_path_entries(
            value,
            project_root="/home/alice/a/project",
            prefix="/opt/python/venv",
            base_prefix="/opt/python",
            home="/home/alice",
            limit=2,
        )
        self.assertEqual(len(output), 3)
        self.assertNotIn("alice", repr(output))
        self.assertEqual(output[-1], "<truncated:1-more>")

    def test_redact_none_and_empty(self) -> None:
        self.assertIsNone(redact_path(None))
        self.assertEqual(redact_path(""), "")


if __name__ == "__main__":
    unittest.main()
