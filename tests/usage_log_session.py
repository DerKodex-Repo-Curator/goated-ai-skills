"""One recorded Claude Code session, seen two ways (Ticket 082).

`recorded_session()` drives the Claude Code adapter through a synthetic
session with the core's usage log on, and keeps both what the skill-usage
mod would hear of it and what the log holds:

- `steps`: the conversation rows Claude Code hands the mod (`session.append`)
  and its turn ends (`turn.complete`), in order, in the shape
  `hooks/classify.ts` reads (`Row`), with each hold's text as the adapter
  gave it;
- `log`: the usage log's entries for the same session.

The mod's tests read both from the generated `tests/usage-log-session.ts`
and check that the mod counts the same from either. Paths in the rows are
the project's own as the session wrote them, made relative so the module
does not change from run to run; the log's project key is replaced by a
fixed one for the same reason. All content is synthetic.
"""

from __future__ import annotations

import itertools
import json
import sys
import tempfile
from pathlib import Path

from claude_code_adapter_support import ROUTER, Session, parse, reason

REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_DIR = REPO_ROOT / "adapters" / "core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from goated_core import usage_log  # noqa: E402

# Skip reasons whose masking the core and the mod must agree on: each is
# generated with the core's result, which the mod's tests compare with theirs.
REASON_CASES = (
    "see `src/export.py` first",
    'the file "docs/a/b.md" is old',
    "nothing (a/b/c) needed",
    "read https://example.com/x today",
    "edit src/x.ts, then stop",
    "and/or ~5 words stay",
    "C:\\work\\x and ~/notes and /tmp/y",
    "[x/y.md], <a/b/c> and 'q/r.txt'!",
    "a/b is kept, a.b too, and a/b. too",
    "x" * 170,
)

# The command a blocked Stop names, as Claude Code quotes it.
STOP_COMMAND = "python /tools/goated-adapter/goated_hook.py"
PROJECT_KEY = "0123456789"


class _Recording:
    """A Session whose every step is also kept as the mod would see it."""

    def __init__(self, root: Path) -> None:
        self.session = Session(root, "recorded-session")
        clock = itertools.count(1)
        self.log_path = root / "logs" / "usage-log.jsonl"
        # A fixed salt, so the file digests, which it salts, are the same each run.
        self.log_path.parent.mkdir(mode=0o700)
        (self.log_path.parent / usage_log.SALT_NAME).write_text("0" * 32, encoding="utf-8")
        self.session.config.usage_log = usage_log.UsageLog(
            self.log_path, "claude-code", clock=lambda: float(next(clock)))
        self.steps: list[dict] = []

    def _row(self, door: str, content: list[dict]) -> None:
        self.steps.append({"row": {"door": door, "message": {"content": content}}})

    def _relative(self, value):
        if not isinstance(value, str):
            return value
        project = str(self.session.project)
        return value.replace(project + "\\", "").replace(project + "/", "").replace("\\", "/")

    def prompt(self, text: str) -> None:
        output = parse(self.session.prompt(text))
        self._row("prompt", [{"type": "text", "text": text}])
        context = output.get("hookSpecificOutput", {}).get("additionalContext")
        if context:
            self._row("hook-context", [{"type": "text", "text": context}])

    def say(self, text: str) -> None:
        self.session.say(text)
        self._row("response", [{"type": "text", "text": text}])

    def _tool(self, name: str, tool_input: dict, run) -> None:
        """Run one call through the session and record its use and result."""

        output = run()
        tool_id = f"toolu_{self.session._counter:04d}"
        shown = {k: self._relative(v) for k, v in tool_input.items()}
        self._row("response", [{"type": "tool_use", "id": tool_id, "name": name, "input": shown}])
        held = reason(output) if isinstance(output, dict) else ""
        content = f"PreToolUse:{name} hook error: {held}" if held else "ok"
        self._row("tool-result", [{"type": "tool_result", "tool_use_id": tool_id,
                                   "content": content, "is_error": bool(held)}])

    def call(self, name: str, tool_input: dict) -> None:
        self._tool(name, tool_input, lambda: self.session.call(name, tool_input))

    def load(self, skill: str) -> None:
        self._tool("Skill", {"skill": skill}, lambda: self.session.load(skill))

    def read(self, path: str) -> None:
        self._tool("Read", {"file_path": path}, lambda: self.session.read(path))

    def stop(self) -> bool:
        """End the turn: a blocked Stop's reason reaches the mod as hook
        context; a let-through one ends the turn as an answer."""

        output = parse(self.session.hook("Stop", stop_hook_active=False,
                                         last_assistant_message=""))
        if output.get("decision") == "block":
            text = (f"<system-reminder>\nStop hook blocking error from command: "
                    f"\"{STOP_COMMAND}\": {output['reason']}\n</system-reminder>")
            self._row("hook-context", [{"type": "text", "text": text}])
            return False
        self.steps.append({"turnEnd": "answer"})
        return True

    def log(self) -> list[dict]:
        return [{**e, "project": PROJECT_KEY if e.get("project") else None}
                for e in usage_log.read_log(self.log_path).entries]


def recorded_session() -> dict:
    """The recorded session's mod rows and turn ends (`steps`), and its log,
    as the entries (`log`) and as the file's text (`logText`); and each of
    `REASON_CASES` with the reason the core keeps (`reasonCases`)."""

    with tempfile.TemporaryDirectory() as tmp:
        r = _Recording(Path(tmp))
        export = str(r.session.project / "src" / "export.py")
        edit = {"file_path": export, "old_string": "limit = 1", "new_string": "limit = 2"}

        # Turn one: routing holds the edit, the route asks for two skills, the
        # person named one; a reference is read; the closeout holds the end
        # until the agent skips its items.
        r.prompt("Add CSV export, test-first with tdd.")
        r.call("Edit", edit)
        r.load(ROUTER)
        r.say("goated-route: standard | requires: tdd, doc-sync")
        r.call("Edit", edit)
        r.load("tdd")
        r.load("doc-sync")
        r.read("/opt/agent/.claude/skills/tdd/references/test-design.md")
        r.call("Edit", edit)
        if not r.stop():
            r.say("goated-skip: verification-before-completion: the change has no test "
                  "yet and the next turn adds one\n"
                  "goated-skip: software-design-principles: one constant changes with no "
                  "design in it\n"
                  "goated-skip: doc-sync: no durable docs describe the export limit")
            r.stop()

        # Turn two: an override typed by the person, and a plain end.
        r.prompt("Skip routing and show the diff.")
        r.say("goated-route: direct")
        r.stop()
        log = r.log()
        text = "".join(json.dumps(entry, ensure_ascii=False) + "\n" for entry in log)
        return {"steps": r.steps, "log": log, "logText": text,
                "reasonCases": [[reason, usage_log.stored_reason(reason)]
                                for reason in REASON_CASES]}


if __name__ == "__main__":
    found = recorded_session()
    for step in found["steps"]:
        print(json.dumps(step)[:220])
    print()
    for entry in found["log"]:
        print(json.dumps({k: v for k, v in entry.items()
                          if k not in ("log", "adapter", "session", "project")}))
