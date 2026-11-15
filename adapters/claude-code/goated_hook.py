"""Command that Claude Code runs for each GOATED adapter hook event.

Reads one hook input from stdin, prints the adapter's JSON output, and always
exits 0: holds are expressed as JSON decisions, and adapter failures let the
action through with a visible warning.
"""

import sys

from goated_adapter import Config, run_hook


def main() -> int:
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    output = run_hook(raw, Config.from_environment())
    if output:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
