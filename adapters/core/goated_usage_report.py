"""A summary of the GOATED usage log as a command (Ticket 082).

    python goated_usage_report.py [--log PATH] [--project KEY]
        [--project-folder PATH] [--adapter NAME]

Prints the Markdown summary `goated_core.usage_report.report` gives: skill
loads by skill and cause, holds by gate and outcome, closeout items, route
lines, reference reads, the projects by key, and how many lines were
skipped as no entry. `--log` (or `GOATED_USAGE_LOG`) names the log, by
default the core's per-user log. `--project` keeps one project's key;
`--project-folder` keeps the project at that folder, keyed with the log's
salt; `--adapter` keeps one adapter's entries. A log that cannot be read,
or with an entry of a version this report does not know, is refused: the
reason goes to standard error and the command exits 1. Unknown arguments,
or a log of `off`, exit 2.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from goated_core.usage_log import (  # noqa: E402
    LogUnreadable, path_from_environment, project_key_of_log, read_log,
)
from goated_core.usage_report import report  # noqa: E402

USAGE = ("usage: goated_usage_report.py [--log PATH] [--project KEY] [--project-folder PATH] "
         "[--adapter NAME]")
FLAGS = ("--log", "--project", "--project-folder", "--adapter")


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
    if path is None:
        sys.stderr.write("goated_usage_report: the usage log is off, so there is none to read\n")
        return 2
    try:
        reading = read_log(path)
    except LogUnreadable as exc:
        sys.stderr.write(f"goated_usage_report: {exc}\n")
        return 1
    project = options.get("--project")
    if "--project-folder" in options:
        # A folder the log has never seen still filters, to nothing.
        project = project_key_of_log(path, options["--project-folder"]) or "(no key)"
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(report(reading.entries, project, options.get("--adapter"),
                            skipped=reading.skipped))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
