"""Command that Claude Code runs for each GOATED adapter hook event.

Reads one hook input from stdin, prints the adapter's JSON output, and always
exits 0: holds are expressed as JSON decisions, and adapter failures let the
action through with a visible warning, including a shared core
(`adapters/core/`) that cannot be found beside this adapter.
"""

import json
import sys

try:
    from goated_adapter import Config, run_hook
except ImportError as exc:  # The shared core, or this package, is missing.
    Config = run_hook = None
    MISSING = exc.name or str(exc)


def main() -> int:
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    if run_hook is None:
        sys.stdout.write(json.dumps({"systemMessage": (
            f"GOATED Claude Code adapter: it could not import {MISSING}, so this action was "
            "allowed without checks. Keep the adapters/core/ folder beside "
            "adapters/claude-code/, as the install steps place it.")}))
        return 0
    output = run_hook(raw, Config.from_environment())
    if output:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
