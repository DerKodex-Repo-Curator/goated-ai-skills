"""No test run writes into the user's own usage log (Ticket 082).

`usage_log_guard` points `GOATED_USAGE_LOG` at a temporary file for the
whole run. These tests fail when it is not in force, when the installed
configurations would still reach the per-user default, or when a test file
that can reach the log imports none of the modules that load the guard.
"""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

from usage_log_guard import GUARDED_LOG, PREFIX

TESTS = Path(__file__).resolve().parent
REPO_ROOT = TESTS.parent
for folder in (REPO_ROOT / "adapters" / "core", REPO_ROOT / "adapters" / "claude-code"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from goated_adapter import Config  # noqa: E402
from goated_core import request as core_request  # noqa: E402
from goated_core import usage_log  # noqa: E402

# What a test file can reach the log through, and the modules that load the guard.
REACHES_LOG = re.compile(r"goated_hook\.py|goated_judge\.py|from_environment\(|run_hook\(|"
                         r"goated_core|goated_adapter")
GUARDING = ("claude_code_adapter_support", "core_scenarios", "enforcement_support",
            "usage_log_guard")


class UsageLogGuardTests(unittest.TestCase):
    def test_the_run_logs_to_a_temporary_file_never_the_default(self) -> None:
        self.assertIn(PREFIX, str(GUARDED_LOG))
        self.assertTrue(GUARDED_LOG.is_relative_to(Path(tempfile.gettempdir()).resolve())
                        or GUARDED_LOG.is_relative_to(Path(tempfile.gettempdir())))
        self.assertNotEqual(GUARDED_LOG, usage_log.default_path())

    def test_the_installed_configurations_log_to_the_guarded_file(self) -> None:
        self.assertEqual(Config.from_environment().usage_log.path, GUARDED_LOG)
        self.assertEqual(core_request.settings_from_environment().usage_log.path, GUARDED_LOG)

    def test_every_test_file_that_can_reach_the_log_loads_the_guard(self) -> None:
        unguarded = []
        for path in sorted(TESTS.glob("*.py")):
            if path.stem in GUARDING:
                continue
            source = path.read_text(encoding="utf-8")
            imports = re.findall(r"^\s*(?:from|import)\s+(\w+)", source, re.MULTILINE)
            if REACHES_LOG.search(source) and not set(imports) & set(GUARDING):
                unguarded.append(path.name)
        self.assertEqual(unguarded, [], "import a test support module, or usage_log_guard")


if __name__ == "__main__":
    unittest.main()
