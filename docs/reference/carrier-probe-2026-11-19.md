# Carrier Probe: How Claude Code Judges The Calls Of One Message

Ticket 119, phase 4 (spec `docs/specs/2026-11-19-hook-friction-round-6.md`,
R10, decision W1). This finding changes no rule. Round 5's Q1 carrier rule
stands until the maintainer decides on the recommendation below.

## Questions

1. In what order does the harness judge the calls of one assistant message?
2. Is session state written while judging one call visible when the next
   call of the same message is judged?

## Answer

Both answers depend on whether Claude Code may run the call alongside
others (whether the tool is "concurrency safe"):

| Calls in one message | Order of `PreToolUse` hooks | State from an earlier call's hook | Transcript at the hook |
| --- | --- | --- | --- |
| Read-only calls (`echo` in Bash; one run, all three `echo`) | All started at once, in message order, about 0.2 s apart; each ran its full 2 s alongside the others | Not visible: all three read the counter before any wrote it | Shows none of the message's calls |
| File writes (`Write`), and a Bash command that writes a file | One at a time, in message order; each hook starts about 0.1 s to 1 s after the one before ends, and after any read-only call before it has run | Visible: each read the counter the one before wrote | From the second write on, shows every call of the message, its fields included |

So for the calls the routing and design gates hold (writes, and commands
that write), the harness judges them one after another in message order,
and both the core's saved state and the transcript already hold what the
earlier calls of the message carried. In run 3, the `Write` after a Bash
call whose description held `goated-route: direct` met no `route-line`
hold; in the control run 2, each `Write` with no line met `router-first`
and `route-line`. Run 4 repeated this with a writing Bash command after a
read-only one. In run 2 the second and third holds came back in their short
"Still unmet" form, so the adapter's turn markers written while judging the
first write were read when judging the second.

In the one run of read-only calls, they were judged together, so nothing
written while judging one reached another; that rests on a single run of
three `echo` calls. The routing gates let plain reads through, so
this matters only for a line carried on a read-only call that a later
read-only call would need, which no gate asks for.

## Recommendation

A route or skip line carried on one call can count for the later calls of
its message that the gates judge, because those are judged after it. Today
that already happens through the transcript, though the hold text says
otherwise ("a call in the same message is not seen yet"). Recommended
follow-ups, each needing the maintainer's decision:

- Correct the carrier advice in the hold text (Ticket 121 owns hold text):
  a line in an earlier call's field of the same message counts for a later
  write in it, so the agent need not wait for a later message.
- Replace the adapter test
  `SameMessageCallTests.test_a_line_in_a_sibling_call_of_the_same_message_is_not_seen_yet`,
  which simulates sibling calls judged before any of the message is
  recorded, with one in the order this probe observed. Today it passes only
  because it simulates the older belief.
- Keep the rule from depending on the order alone: probe again after a
  Claude Code upgrade, since the order is the harness's behavior, not a
  documented promise. Four runs with one model on one version is a small
  sample.

## Setup

- Claude Code 2.1.325 on Windows 11, model `haiku`, `claude -p`, no
  `/clear`, each run a new session.
- A scratch project outside the repo (a `git init` folder with one file),
  with `--setting-sources project` so no user settings or hooks loaded, and
  `--settings probe-settings.json` registering two hooks:
  - the adapter's hooks from this ticket's worktree
    (`adapters/claude-code/goated_hook.py`) on `SessionStart`,
    `UserPromptSubmit`, `PreToolUse` (`Edit|Write|Bash|PowerShell`), and
    `Stop`, with `GOATED_ADAPTER_STATE_DIR` set to a scratch folder and
    `GOATED_USAGE_LOG=off`;
  - a probe hook on every `PreToolUse` that recorded, as one JSON line:
    its start and end times, the `tool_use_id`, the command, the value of a
    shared counter file it read at its start, and the `tool_use` ids the
    transcript showed. It then slept 2 s, wrote the counter plus one, and
    allowed the call.
- Each run's stream (`--output-format stream-json --verbose`) gave the
  message id of every call, so the calls of each run are shown to share one
  message.

## Not Covered

- No message mixing a write, a read, and a write, so whether a read between
  two writes splits their order is not shown.
- No write before a read in one message.
- No `Edit`, `MultiEdit`, `NotebookEdit`, or `PowerShell` tool; only `Write`
  and `Bash`.
- One run per shape, with one model on one Claude Code version.

## Probe Files

To repeat the probe, put these two files in a scratch folder outside any
checkout, with the project folder beside them, and replace `<probe-dir>`
and `<adapter-dir>` with absolute paths.

`<probe-dir>/probe_hook.py`, the probe hook (it writes `probe.log` and
`counter.txt` beside itself):

```python
"""Carrier probe hook (ticket 119, phase 4). Not part of the repo.

For each PreToolUse it records, as one JSON line in probe.log beside this file:
when the hook started and ended, the tool_use_id, which tool_use ids of the
current assistant message the transcript already shows, and the value of a
shared counter file it read at its start. It then sleeps, so overlapping hook
runs are visible, and writes counter + 1. It always allows the call.
"""

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG = HERE / "probe.log"
COUNTER = HERE / "counter.txt"
SLEEP = float(os.environ.get("PROBE_SLEEP", "2"))


def transcript_tool_ids(path: str) -> list[str]:
    ids = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                message = entry.get("message") or {}
                content = message.get("content")
                if entry.get("type") == "assistant" and isinstance(content, list):
                    ids += [c.get("id") for c in content if c.get("type") == "tool_use"]
    except OSError:
        pass
    return ids


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    start = time.time()
    seen = int(COUNTER.read_text()) if COUNTER.exists() else 0
    ids = transcript_tool_ids(payload.get("transcript_path", ""))
    time.sleep(SLEEP)
    COUNTER.write_text(str(seen + 1))
    record = {
        "event": payload.get("hook_event_name"),
        "tool": payload.get("tool_name"),
        "tool_use_id": payload.get("tool_use_id"),
        "command": (payload.get("tool_input") or {}).get("command"),
        "pid": os.getpid(),
        "start": round(start, 3),
        "end": round(time.time(), 3),
        "counter_seen": seen,
        "transcript_tool_ids": ids[-6:],
    }
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`<probe-dir>/project/probe-settings.json`:

```json
{
 "env": {"GOATED_ADAPTER_STATE_DIR": "<probe-dir>/state", "GOATED_USAGE_LOG": "off"},
 "hooks": {
  "SessionStart": [{"hooks": [{"type": "command", "command": "python", "args": ["<adapter-dir>/goated_hook.py"]}]}],
  "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "python", "args": ["<adapter-dir>/goated_hook.py"]}]}],
  "PreToolUse": [
   {"matcher": ".*", "hooks": [{"type": "command", "command": "python", "args": ["<probe-dir>/probe_hook.py"]}]},
   {"matcher": "Edit|Write|Bash|PowerShell", "hooks": [{"type": "command", "command": "python", "args": ["<adapter-dir>/goated_hook.py"]}]}
  ],
  "Stop": [{"hooks": [{"type": "command", "command": "python", "args": ["<adapter-dir>/goated_hook.py"]}]}]
 }
}
```

`<adapter-dir>` is `adapters/claude-code` in the checkout under test.

## Commands

Run from the scratch project, each with
`--model haiku --setting-sources project --settings probe-settings.json --output-format stream-json --verbose --max-budget-usd 0.3`:

1. `claude -p "Make exactly three Bash tool calls, all three in one single assistant message (parallel tool use), with these commands: echo one ; echo two ; echo three. Then reply with the word DONE and nothing else." --allowedTools "Bash(echo:*)"`
2. `claude -p "Make exactly three Write tool calls, all three in one single assistant message (parallel tool use): write a.txt containing 1, b.txt containing 2, c.txt containing 3. If a call is refused, do not retry; reply with the word DONE and nothing else." --allowedTools "Write"`
3. `claude -p "In one single assistant message, make two tool calls in parallel, in this order: (1) a Bash call with command 'echo routed' whose description field is exactly the two lines 'goated-route: direct' and 'Print a word'; (2) a Write call writing d.txt containing 4. Do not retry anything that is refused. Then reply with the word DONE and nothing else." --allowedTools "Write" "Bash(echo:*)"`
4. `claude -p "In one single assistant message, make two Bash tool calls in parallel, in this order: (1) command 'echo routed' whose description field is exactly the two lines 'goated-route: direct' and 'Print a word'; (2) command 'echo 5 > e.txt' with description 'Write a file'. Do not retry anything that is refused. Then reply with the word DONE and nothing else." --allowedTools "Bash(echo:*)"`

## Recorded Output

The probe hook's records (times in seconds; "counter" is the value read at
the hook's start; "ids" is how many of the message's calls the transcript
showed):

| Run | Call | Start | End | Counter | Ids | Adapter |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Bash `echo one` | 275.188 | 277.190 | 0 | 0 | allowed |
| 1 | Bash `echo two` | 275.371 | 277.373 | 0 | 0 | allowed |
| 1 | Bash `echo three` | 275.552 | 277.554 | 0 | 0 | allowed |
| 2 | Write `a.txt` | 310.467 | 312.469 | 1 | 0 | `router-first`, `route-line` |
| 2 | Write `b.txt` | 312.569 | 314.572 | 2 | 3 | `router-first`, `route-line`, short form |
| 2 | Write `c.txt` | 314.668 | 316.671 | 3 | 3 | `router-first`, `route-line`, short form |
| 3 | Bash `echo routed` with the line | 353.370 | 355.373 | 4 | 0 | allowed |
| 3 | Write `d.txt` | 356.168 | 358.170 | 5 | 2 | `router-first` only |
| 4 | Bash `echo routed` with the line | 404.141 | 406.143 | 6 | 0 | allowed |
| 4 | Bash `echo 5 > e.txt` | 407.137 | 409.139 | 7 | 2 | `router-first` only |

Start and end times drop the shared leading digits (`1795121`). In run 1
the results came back in the order three, one, two, so the commands also
ran together. The router never loaded in these sessions, so every write met
`router-first`; only `route-line` tells whether the line was seen.
