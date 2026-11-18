"""Run a conformance scenario against today's Claude Code adapter (Ticket 079).

A scenario (`stack/fixtures/enforcement/`) is written in the event model's
terms and names no harness. This module is the bridge: it maps each step to
what Claude Code records and the hook it runs, using the synthetic sessions of
`claude_code_adapter_support`, and maps each hook's output back to a decision.
It also builds the event-model request each judged step stands for, so the
caller can check the scenario against the schema. Tickets 080 and 081 replace
this bridge with the core itself.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import NamedTuple

from claude_code_adapter_support import (
    REPO_ROOT, Session, git_branch_with_change, parse, reason,
)

REGISTRY = REPO_ROOT / "stack" / "goated-stack.yaml"

HOLD_LINE = re.compile(r"^goated-hold: ([a-z]+(?:-[a-z]+)*) \| (strict|justified-skip)$", re.M)
# A closeout item's line, as the contract's Hold Messages section defines it.
ITEM_LABEL = re.compile(r"^- ([A-Z][a-z]+): ", re.M)
ADAPTER_NAME = "GOATED Claude Code adapter"
FAIL_OPEN = "so this action was allowed without checks."
# Notices that mean the adapter could not judge: never expected unless named.
FAILURE_NOTICES = frozenset({"fail_open", "warning"})
OVERRIDE_RECORDED = "recorded your override"
BRIEF_OPENING = "Background (from the session that started this one):"
SESSION_SOURCES = {"new": "startup", "resumed": "resume", "after_compaction": "compact",
                   "cleared": "clear"}
# Claude Code tools for the call kinds that have one tool each.
COMMIT_TOOL = "mcp__git__git_commit"
PULL_REQUEST_TOOL = "mcp__github__create_pull_request"
OTHER_TOOL = "WebFetch"
START_SESSION = "mcp__ccd_session__start_session"
# A built-in agent type with no write, edit, or shell tool.
READ_ONLY_AGENT = "claude-code-guide"


class Result(NamedTuple):
    """What a run found: each step whose decision differed, and the request
    each judged step stands for."""

    failures: list[str]
    requests: list[dict]


def run_scenario(root: Path, scenario: dict) -> Result:
    """Run `scenario` in a fresh synthetic session under `root`."""

    return _Run(root, scenario).run()


class _Run:
    def __init__(self, root: Path, scenario: dict) -> None:
        self.s = Session(root)
        self.s.project.mkdir(parents=True, exist_ok=True)
        self.scenario = scenario
        self.turns: list[dict] = []
        self.failures: list[str] = []
        self.requests: list[dict] = []
        self.outside = root / "outside"
        # The repo's registry, where an installed adapter finds its distribution's.
        self.s.config.registry_path = REGISTRY
        setup = scenario.get("setup", {})
        for skill in setup.get("installed_skills", []):
            folder = self.s.config.home / ".claude" / "skills" / skill
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "SKILL.md").write_text(f"---\nname: {skill}\n---\n", encoding="utf-8")
        if "branch_changed_lines" in setup:
            git_branch_with_change(self.s.project, setup["branch_changed_lines"])

    def run(self) -> Result:
        for number, step in enumerate(self.scenario["steps"], 1):
            self.number = number
            if "prompt" in step:
                self._prompt(step)
            elif "reply" in step:
                self.s.say(step["reply"])
                self._entry({"type": "reply_text", "text": step["reply"]})
            elif "call" in step:
                self._call(step)
            elif "compaction" in step:
                self.s.compact()
                self.turns.append({"key": f"t{len(self.turns) + 1}",
                                   "opener": {"type": "compaction"}, "entries": []})
            elif "turn_end" in step:
                self._turn_end(step)
            elif "session_start" in step:
                event = {"type": "session_start", "source": step["session_start"]}
                output = parse(self.s.hook("SessionStart",
                                           source=SESSION_SOURCES[step["session_start"]]))
                self._judged(step.get("expect"), event, _decision(output, "context"))
            else:
                raise ValueError(f"step {number}: the bridge cannot run {sorted(step)}")
        return Result(self.failures, self.requests)

    # Steps --------------------------------------------------------------

    def _prompt(self, step: dict) -> None:
        prompt = step["prompt"]
        text = self._expand(prompt["text"])
        for n, pasted in enumerate(prompt.get("pasted", []), 1):
            text += f'\n<pasted_content id="p{n}">\n{pasted}\n</pasted_content id="p{n}">'
        author, continues = prompt["author"], step.get("continues", False)
        if author == "person" and not continues:
            output = self.s.prompt(text)
        elif author == "session" and prompt.get("starts_session"):
            output = self.s.prompt(f"{BRIEF_OPENING}\n\n{text}", origin=None,
                                   turnOrigin="host_synthetic", promptSource="sdk")
        elif author == "session" and not continues:
            output = self.s.peer(text)
        elif author == "host" and continues:
            output = self.s.notify(text)
        else:
            raise ValueError(f"step {self.number}: the bridge cannot record a "
                             f"{'continuing ' if continues else ''}{author} prompt")
        if continues:
            self._entry(prompt)
        else:
            self.turns.append({"key": f"t{len(self.turns) + 1}", "opener": prompt,
                               "entries": []})
        self._judged(step.get("expect"), {"type": "prompt_submitted"},
                     _decision(parse(output), "context"))

    def _call(self, step: dict) -> None:
        call = step["call"]
        tool, tool_input = self._tool(call)
        tool_id, output = self.s._judge(tool, tool_input)
        self._judged(step.get("expect", {"decision": "allow"}),
                     {"type": "pending_call", "call": call}, _decision(output, "tool"))
        held = reason(output)
        result = ({"ok": False, "held": True, "output": held} if held
                  else step.get("result", {"ok": True}))
        if "expect_after" in step:
            response = {"success": True} if result["ok"] else {"error": "failed"}
            after = parse(self.s.hook("PostToolUse", tool_name=tool, tool_input=tool_input,
                                      tool_use_id=tool_id, tool_response=response))
            self._judged(step["expect_after"],
                         {"type": "finished_call", "call": call, "result": result},
                         _decision(after, "context"))
        self._record(tool_id, call, result)
        self._entry({"type": "call", "call": call, "result": result})

    def _turn_end(self, step: dict) -> None:
        output = parse(self.s.hook("Stop", stop_hook_active=False, last_assistant_message=""))
        decision = _decision(output, "stop")
        self._judged(step.get("expect", {"decision": "allow"}), {"type": "turn_end"}, decision)
        if decision["decision"] == "allow":
            self._entry({"type": "turn_ended"})

    # Claude Code's side -------------------------------------------------

    def _tool(self, call: dict) -> tuple[str, dict]:
        """The Claude Code tool and input that make `call`."""

        kind, line = call["kind"], call.get("line_text")
        # Claude Code reads a line only from a shell or agent call's
        # description and a Skill call's args; anything else cannot carry one.
        if line is not None and not (kind in ("shell_command", "skill_load")
                                     or (kind == "spawn" and call["starts_now"])):
            raise ValueError(f"step {self.number}: Claude Code has no field to carry "
                             f"line_text on a {kind} call")
        if kind == "file_write":
            path, edits = self._expand(call["path"]), call["edits"]
            if call.get("whole_file"):
                return "Write", {"file_path": path, "content": edits[0]["added"]}
            pairs = [{"old_string": e["removed"], "new_string": e["added"]} for e in edits]
            if len(pairs) == 1:
                return "Edit", {"file_path": path, **pairs[0]}
            return "MultiEdit", {"file_path": path, "edits": pairs}
        if kind == "shell_command":
            tool_input = {"command": self._expand(call["command"])}
            if line:
                tool_input["description"] = line
            if call.get("background"):
                tool_input["run_in_background"] = True
            return ("PowerShell" if call["shell"] == "powershell" else "Bash"), tool_input
        if kind == "skill_load":
            return "Skill", {"skill": call["skill"], **({"args": line} if line else {})}
        if kind == "file_read":
            return "Read", {"file_path": self._expand(call["path"]),
                            **({} if call["whole"] else {"limit": 20})}
        if kind == "spawn":
            if not call["starts_now"]:
                initiation = "own_initiative" if call["brief"] else "offer"
                return START_SESSION, {"initiation": initiation, "title": "Task",
                                       "prompt": call["brief"]}
            tool_input = {"prompt": call["brief"],
                          "subagent_type": READ_ONLY_AGENT if call.get("read_only")
                          else "general-purpose"}
            if line:
                tool_input["description"] = line
            return "Agent", tool_input
        if kind == "commit":
            return COMMIT_TOOL, {"message": call.get("message")}
        if kind == "pull_request":
            return PULL_REQUEST_TOOL, {"title": "Change", "body": "What changed."}
        return OTHER_TOOL, {"url": "https://example.invalid"}

    def _record(self, tool_id: str, call: dict, result: dict) -> None:
        """Record the call's result as Claude Code does, for its kind."""

        text = result.get("output") or ("ok" if result["ok"] else "Exit code 1\nfailed")
        extra = None
        agent = result.get("agent")
        if call["kind"] == "skill_load" and result["ok"]:
            extra = {"toolUseResult": {"success": True, "commandName": call["skill"]}}
        elif agent:
            extra = {"toolUseResult": {
                "status": "async_launched" if agent.get("background") else "completed",
                "agentId": agent["id"]}}
        self.s._tool_result(tool_id, text, is_error=not result["ok"], extra=extra)
        if call["kind"] == "skill_load" and result["ok"]:
            self.s._append({"type": "user", "isMeta": True, "sourceToolUseID": tool_id,
                            "message": {"role": "user", "content": [
                                {"type": "text",
                                 "text": f"Base directory for this skill: {call['skill']}"}]}})

    def _expand(self, text: str) -> str:
        """Fill the placeholder `{outside}`: a folder outside the project and
        any checkout, as a scratch file's folder is."""

        return text.replace("{outside}", self.outside.as_posix())

    # The event model's side ---------------------------------------------

    def _entry(self, entry: dict) -> None:
        if not self.turns:
            raise ValueError(f"step {self.number}: an entry before any prompt")
        self.turns[-1]["entries"].append(entry)

    def _judged(self, expect: dict | None, event: dict, got: dict) -> None:
        """Record the request this step stands for, and compare its decision
        with `expect`; with no `expect`, the step is not checked."""

        self.requests.append({
            "event_model": 1,
            "session": {"id": self.s.session_id, "agent": {"role": "main"}},
            "project": {"folders": [self.s.project.as_posix()],
                        "working_folder": self.s.cwd.as_posix(),
                        "home": self.s.config.home.as_posix()},
            "turns": copy.deepcopy(self.turns),
            "event": event,
        })
        if expect is None:
            # Unchecked, but an adapter that could not judge never passes.
            expect = {"decision": got["decision"], "holds": [
                {"gate": gate, "kind": kind} for gate, kind in got["holds"]]}
        holds = expect.get("holds", [])
        wanted = {"decision": expect["decision"],
                  "holds": [(h["gate"], h["kind"]) for h in holds]}
        found = {"decision": got["decision"], "holds": got["holds"]}
        labels = next((h["items"] for h in holds if "items" in h), None)
        if labels is not None:
            wanted["items"], found["items"] = sorted(labels), got["items"]
        if "notices" in expect:
            wanted["notices"] = sorted(expect["notices"])
            found["notices"] = sorted(got["notices"])
        else:
            wanted["failures"] = []
            found["failures"] = sorted(FAILURE_NOTICES.intersection(got["notices"]))
        if wanted != found:
            self.failures.append(
                f"step {self.number} ({event['type']}): expected {wanted}, got {got}")


def _decision(output: dict, shape: str) -> dict:
    """The decision a hook's output stands for. `shape` names where the hook
    puts a hold: `tool` (a denied call), `stop` (a blocked end), or `context`
    (a hook that never holds). `items` are the closeout hold's item labels."""

    if shape == "tool":
        text = reason(output)
    elif shape == "stop":
        text = str(output.get("reason", "")) if output.get("decision") == "block" else ""
    else:
        text = ""
    specific = output.get("hookSpecificOutput") or {}
    context = specific.get("additionalContext", "")
    notices = []
    if context:
        if specific.get("hookEventName") == "PostToolUse":
            notices.append("closeout_note")
        elif OVERRIDE_RECORDED in context:
            notices.append("override_recorded")
        else:
            notices.append("session_notice")
    notices += _warnings(output.get("systemMessage", ""), context)
    holds, items = [], []
    found = list(HOLD_LINE.finditer(text))
    for n, match in enumerate(found):
        holds.append((match[1], match[2]))
        if match[1] == "closeout":
            section = text[match.end():found[n + 1].start() if n + 1 < len(found) else None]
            items = sorted(set(ITEM_LABEL.findall(section)))
    return {"decision": "hold" if text else "allow", "holds": holds, "items": items,
            "notices": notices}


def _warnings(message: str, context: str) -> list[str]:
    """The notice kinds the user-facing message adds. It repeats the hook's
    context notices, sentence parts joined by "; ", and adds any warnings;
    only a part the context does not hold is a warning."""

    if not message:
        return []
    if message.endswith(FAIL_OPEN):
        return ["fail_open"]
    body = message.removeprefix(f"{ADAPTER_NAME}: ").removesuffix(".")
    extra = [part for part in body.split("; ") if part.rstrip(".") not in context]
    return ["warning"] if extra else []
