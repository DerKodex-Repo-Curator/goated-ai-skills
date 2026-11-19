"""The worked example adapter: GOATED enforcement for the toy loop (Ticket 083).

An adapter is a translation layer and nothing more. For each hook the toy
loop (`toy_loop.py`) calls, this one builds an event-model request
(`stack/schemas/enforcement-event-model.schema.json`) from the loop's
transcript, asks the shared core (`adapters/core/`) for a decision, and
turns the decision into the loop's answer: a block with the hold text for a
hold, and the notices as messages the agent sees. Every rule lives in the
core; this file only maps.

Copy it as a starting point for a harness of your own; the guide,
`adapters/writing-an-adapter.md`, walks through each part. It asks the core
by the Python call; `command_judge` asks it by the JSON command instead,
as a harness written in another language would.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from toy_loop import HookAnswer, Hooks, ToolLoop

CORE_DIR = Path(__file__).resolve().parents[1] / "core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

try:
    from goated_core.request import EVENT_MODEL, decide, settings_from_environment
    from goated_core.usage_log import UsageLog
except ImportError as exc:  # The core is not beside this adapter: fail open, visibly.
    decide = None
    EVENT_MODEL = 5
    MISSING_CORE = exc.name or str(exc)

NAME = "GOATED example adapter"
# The adapter's name in the core's usage log, so its entries are told apart
# from another harness's.
LOG_NAME = "toy-loop-example"
# What only this harness can say about where a route or skip line goes: the
# toy loop keeps reply text whole, so a line there counts.
WHERE_LINES_GO = ("In this loop, a route or skip line goes on its own line in your reply "
                  "text; write it there, then use the tool again.")

Judge = Callable[[dict], dict]


def python_judge(state_dir: Path | None = None, log_path: Path | None = None) -> Judge:
    """Ask the core by the Python call, keeping its state under `state_dir`
    (by default where `GOATED_CORE_STATE_DIR` or the core's default says).
    The core logs each event to `log_path` as `LOG_NAME`; with none, or
    `off`, it keeps no log, whatever the environment names."""

    if decide is None:
        return lambda request: _fail_open(f"it could not import {MISSING_CORE}")
    # The core reads the path, `off` included; only the adapter's name is ours.
    settings = settings_from_environment(str(state_dir) if state_dir else None,
                                         log_path=str(log_path) if log_path else "off")
    if settings.usage_log is not None:
        settings.usage_log = UsageLog(settings.usage_log.path, LOG_NAME)
    return lambda request: decide(request, settings)


def command_judge(state_dir: Path | None = None, log_path: Path | None = None) -> Judge:
    """Ask the core by its JSON command, one process per request, with the
    same state folder and log as `python_judge`."""

    command = [sys.executable, str(CORE_DIR / "goated_judge.py"),
               "--usage-log", str(log_path) if log_path else "off"]
    if state_dir:
        command += ["--state-dir", str(state_dir)]
    environment = {**os.environ, "GOATED_CORE_ADAPTER": LOG_NAME}

    def judge(request: dict) -> dict:
        try:
            done = subprocess.run(command, input=json.dumps(request).encode("utf-8"),
                                  capture_output=True, check=True, timeout=60,
                                  env=environment)
            return json.loads(done.stdout.decode("utf-8"))
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            return _fail_open(f"it could not run the core's command ({type(exc).__name__})")

    return judge


def _fail_open(why: str) -> dict:
    """The decision this adapter gives when it cannot ask the core."""

    return {"event_model": EVENT_MODEL, "decision": "allow", "holds": [], "notices": [
        {"kind": "fail_open", "text": f"{NAME}: {why}, so this action was allowed without "
                                      "checks."}]}


# Each toy tool as the call kind it is, built from the tool's arguments.
# A tool missing here is judged as `other`, which no write gate judges, so
# map every tool that writes, runs commands, or hands work on.
TOOL_CALLS: dict[str, Callable[[dict], dict]] = {
    "edit_file": lambda a: {"kind": "file_write", "path": a["path"],
                            "edits": [{"removed": e["old"], "added": e["new"]}
                                      for e in a["edits"]],
                            **({"creates": True} if a.get("create") else {})},
    "write_file": lambda a: {"kind": "file_write", "path": a["path"], "whole_file": True,
                             "edits": [{"removed": None, "added": a["content"]}]},
    "read_file": lambda a: {"kind": "file_read", "path": a["path"],
                            "whole": a.get("lines") is None},
    "shell": lambda a: {"kind": "shell_command", "command": a["command"],
                        "shell": "powershell" if a.get("powershell") else "posix",
                        **({"background": True} if a.get("background") else {})},
    "use_skill": lambda a: {"kind": "skill_load", "skill": a["name"]},
    "delegate": lambda a: {"kind": "spawn", "brief": a["task"],
                           "starts_now": a.get("start", True),
                           **{k: True for k in ("read_only", "separate") if a.get(k)}},
    "git_commit": lambda a: {"kind": "commit", "message": a.get("message")},
    "open_pull_request": lambda a: {"kind": "pull_request",
                                    **{k: a[t] for k, t in (("base", "base"), ("head", "head"),
                                                            ("repository", "repo")) if t in a}},
}


def call_for(use: dict) -> dict:
    """The event model's call for one tool use from the transcript."""

    build = TOOL_CALLS.get(use["name"])
    call = build(use["args"]) if build else {"kind": "other"}
    return {**call, "id": use["id"]}


def result_for(output: dict) -> dict:
    """The event model's result for a tool use's `ToolOutput`, as a dict."""

    result = {"ok": output["ok"], "output": output["text"]}
    if output["blocked"]:
        result["held"] = True
    elif not output["ran"]:
        result["ran"] = False
    if output["agent"]:
        result["agent"] = dict(output["agent"])
    return result


def turns_from(transcript: list[dict], leave_out: str | None = None) -> list[dict]:
    """The event model's turns since the last compaction, from the loop's
    transcript, leaving out the tool use whose id is `leave_out` (the call
    being judged, which the request carries as its event).

    A prompt opens a turn unless it arrived mid-turn; a compaction opens a
    turn of its own. The hooks' own messages to the agent are not events.
    Each turn's key is its opener's place in the transcript, which never
    changes, so the core can tell the turns apart across requests.
    """

    starts = [n for n, item in enumerate(transcript) if item["role"] == "compacted"]
    turns: list[dict] = []
    for n in range(starts[-1] if starts else 0, len(transcript)):
        item = transcript[n]
        role = item["role"]
        if role == "compacted" or (role == "user" and not item["mid_turn"]):
            opener = {"type": "compaction"} if role == "compacted" else _prompt(item)
            turns.append({"key": f"m{n}", "opener": opener, "entries": []})
            continue
        entry = _entry(item, leave_out)
        if entry is not None and turns:
            turns[-1]["entries"].append(entry)
    return turns


def _prompt(item: dict) -> dict:
    prompt = {"type": "prompt", "author": item["author"], "text": item["text"]}
    if item["pasted"]:
        prompt["pasted"] = list(item["pasted"])
    if item["starts_session"]:
        prompt["starts_session"] = True
    return prompt


def _entry(item: dict, leave_out: str | None) -> dict | None:
    role = item["role"]
    if role == "user":
        return _prompt(item)
    if role == "assistant":
        return {"type": "reply_text", "text": item["text"]}
    if role == "tool":
        if item["id"] == leave_out:
            return None
        return {"type": "call", "call": call_for(item), "result": result_for(item["output"])}
    if role == "skill":
        return {"type": "skill_invoked", "skill": item["name"]}
    if role == "agent_done":
        return {"type": "agent_finished", "agent_id": item["agent_id"]}
    if role == "end":
        return {"type": "turn_ended"}
    return None  # A hook's message to the agent.


class GoatedAdapter(Hooks):
    """The toy loop's hooks, each asking the core.

    `project` is the project folder the session works in, `home` the
    agent's home folder, and `session_id` stays the same for the whole
    session, so the core's saved facts follow it. `installed_skills` lists
    the skills the harness has installed, or is None when it cannot tell.
    `agent` is the event model's `session.agent`. `judge` asks the core; by
    default the Python call. `decisions` keeps each (event type, decision)
    the core gave, oldest first, for a log or a test.
    """

    def __init__(self, project: Path, home: Path, session_id: str,
                 installed_skills: list[str] | None = None, agent: dict | None = None,
                 judge: Judge | None = None) -> None:
        self.project = {"folders": [Path(project).as_posix()],
                        "working_folder": Path(project).as_posix(),
                        "home": Path(home).as_posix(),
                        "agent_folders": [(Path(home) / ".toy-loop").as_posix()],
                        "installed_skills": installed_skills}
        self.session = {"id": session_id, "agent": agent or {"role": "main"}}
        self.judge = judge or python_judge()
        self.decisions: list[tuple[str, dict]] = []

    def at_session_start(self, loop: ToolLoop, source: str) -> HookAnswer:
        return self._answer(loop, {"type": "session_start", "source": source}, can_block=False)

    def on_prompt(self, loop: ToolLoop) -> HookAnswer:
        # A person's typed overrides count only once this event records them.
        return self._answer(loop, {"type": "prompt_submitted"}, can_block=False)

    def before_tool(self, loop: ToolLoop, use: dict) -> HookAnswer:
        return self._answer(loop, {"type": "pending_call", "call": call_for(use)})

    def after_tool(self, loop: ToolLoop, use: dict) -> HookAnswer:
        event = {"type": "finished_call", "call": call_for(use),
                 "result": result_for(use["output"])}
        return self._answer(loop, event, leave_out=use["id"], can_block=False)

    def at_turn_end(self, loop: ToolLoop) -> HookAnswer:
        return self._answer(loop, {"type": "turn_end"})

    def _answer(self, loop: ToolLoop, event: dict, leave_out: str | None = None,
                can_block: bool = True) -> HookAnswer:
        """Ask the core about `event` and answer the loop: on a hold, block
        with every hold in one message, as the contract's Hold Messages
        section lays it out; show each notice as the core wrote it."""

        request = {"event_model": EVENT_MODEL, "session": self.session, "project": self.project,
                   "turns": turns_from(loop.transcript, leave_out), "event": event}
        decision = self.judge(request)
        self.decisions.append((event["type"], decision))
        notices = [notice["text"] for notice in decision["notices"]]
        if decision["decision"] != "hold" or not can_block:
            return HookAnswer(messages=notices)
        held = "\n\n".join(f"goated-hold: {h['gate']} | {h['kind']}\n{h['text']}"
                           for h in decision["holds"])
        return HookAnswer(block=True, messages=[f"{held}\n\n{WHERE_LINES_GO}", *notices])
