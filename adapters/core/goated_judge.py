"""The GOATED enforcement core as a command: one JSON request on standard
input, one JSON decision on standard output (ADR 0004).

    python goated_judge.py [--state-dir DIR] [--registry PATH] < request.json

The request and the decision are the event model's
(`stack/schemas/enforcement-event-model.schema.json`); the answer is the one
`goated_core.request.decide` gives. `--state-dir` and `--registry` win over
the environment variables `decide`'s settings read. A request the core
cannot read is answered with `allow` and a `fail_open` notice, so the
command prints a decision and exits 0 for any input; it exits 2 only for
arguments it does not know.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from goated_core.request import decide, fail_open, settings_from_environment  # noqa: E402

USAGE = "usage: goated_judge.py [--state-dir DIR] [--registry PATH] < request.json"


def main(argv: list[str]) -> int:
    options = {}
    words = list(argv)
    while words:
        flag = words.pop(0)
        if flag not in ("--state-dir", "--registry") or not words:
            sys.stderr.write(USAGE + "\n")
            return 2
        options[flag] = words.pop(0)
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    try:
        request = json.loads(raw)
    except ValueError as exc:
        decision = fail_open(f"it could not read the request (not JSON: {exc.msg})")
    else:
        decision = decide(request, settings_from_environment(
            options.get("--state-dir"), options.get("--registry")))
    sys.stdout.write(json.dumps(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
