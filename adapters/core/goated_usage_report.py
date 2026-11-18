"""A summary of the GOATED usage log as a command (Ticket 082).

    python goated_usage_report.py [--log PATH] [--project KEY] [--adapter NAME]

Prints the Markdown summary `goated_core.usage_report.report` gives: skill
loads by skill and cause, holds by gate and outcome, closeout items, route
lines, and reference reads. `--log` (or `GOATED_USAGE_LOG`) names the log,
by default the core's per-user log; `--project` and `--adapter` keep one
project's key or one adapter's entries. A log that cannot be read, or of a
version this report does not know, is refused: the reason goes to standard
error and the command exits 1. Unknown arguments exit 2.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from goated_core.usage_log import LogUnreadable, path_from_environment, read_entries  # noqa: E402
from goated_core.usage_report import report  # noqa: E402

USAGE = "usage: goated_usage_report.py [--log PATH] [--project KEY] [--adapter NAME]"
FLAGS = ("--log", "--project", "--adapter")


def main(argv: list[str]) -> int:
    options = {}
    words = list(argv)
    while words:
        flag = words.pop(0)
        if flag not in FLAGS or not words:
            sys.stderr.write(USAGE + "\n")
            return 2
        options[flag] = words.pop(0)
    path = path_from_environment(options.get("--log"))
    try:
        entries = read_entries(path)
    except LogUnreadable as exc:
        sys.stderr.write(f"goated_usage_report: {exc}\n")
        return 1
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(report(entries, options.get("--project"), options.get("--adapter")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
