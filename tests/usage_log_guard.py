"""Keeps every test run's usage log out of the user's own (Ticket 082).

Importing this module points `GOATED_USAGE_LOG` at a file in a temporary
folder for the whole test process, and every process it starts inherits it,
so a test that drives the Claude Code adapter's installed configuration, a
hook command, or the core's command never writes into the per-user default
log. The test support modules import it; `tests/test_usage_log_guard.py`
fails when a test file that can reach the log imports none of them, or
when the guard is not in force. A test that names its own log still does.
"""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile
from pathlib import Path

LOG_ENV = "GOATED_USAGE_LOG"
PREFIX = "goated-test-usage-log-"

# A log the developer's own shell names is replaced too: tests never write to
# a real log. One a parent test process set up is kept.
if PREFIX not in os.environ.get(LOG_ENV, ""):
    _FOLDER = tempfile.mkdtemp(prefix=PREFIX)
    atexit.register(shutil.rmtree, _FOLDER, ignore_errors=True)
    os.environ[LOG_ENV] = str(Path(_FOLDER) / "usage-log.jsonl")

GUARDED_LOG = Path(os.environ[LOG_ENV])
