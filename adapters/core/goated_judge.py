"""The GOATED enforcement core as a command: one JSON request on standard
input, one JSON decision on standard output (ADR 0004).

    python goated_judge.py [--state-dir DIR] [--registry PATH] [--usage-log PATH]
        < request.json

The request and the decision are the event model's
(`stack/schemas/enforcement-event-model.schema.json`); the answer is the one
`goated_core.request.decide` gives. `--state-dir`, `--registry` and
`--usage-log` win over the environment variables `decide`'s settings read.
The usage log (`stack/schemas/usage-log.schema.json`) gets each event's
entries only when `--usage-log` or `GOATED_USAGE_LOG` names it (`off` keeps
none), and `goated_usage_report.py` summarises it. A request the core
cannot read is answered with `allow` and a `fail_open` notice, so the
command prints a decision and exits 0 for any input; it exits 2 only for
arguments it does not know.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from goated_core.request import decide, fail_open, settings_from_environment  # noqa: E402

USAGE = ("usage: goated_judge.py [--state-dir DIR] [--registry PATH] [--usage-log PATH] "
         "< request.json")
FLAGS = ("--state-dir", "--registry", "--usage-log")


def main(argv: list[str]) -> int:
    options = {}
    words = list(argv)
    while words:
        flag = words.pop(0)
        if flag not in FLAGS or not words:
            sys.stderr.write(USAGE + "\n")
            return 2
        options[flag] = words.pop(0)
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        try:
            request = json.loads(raw)
        except (ValueError, RecursionError) as exc:
            # Not JSON, or JSON the parser itself refuses: an integer past
            # Python's digit limit, or nesting past its recursion limit.
            reason = getattr(exc, "msg", None) or str(exc) or type(exc).__name__
            decision = fail_open(f"it could not read the request (not JSON it can parse: "
                                 f"{reason})")
        else:
            decision = decide(request, settings_from_environment(
                options.get("--state-dir"), options.get("--registry"),
                options.get("--usage-log")))
        text = json.dumps(decision)
    except Exception as exc:  # noqa: BLE001 - the command must answer every input, failing open
        text = json.dumps(fail_open(f"it hit an internal error ({type(exc).__name__})"))
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
