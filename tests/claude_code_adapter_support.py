"""Test support for the Claude Code adapter: synthetic sessions in the real shape.

`Session` writes a transcript JSONL whose entries follow the shape Claude Code
records (user prompts, assistant text and tool_use blocks, tool_result entries,
meta skill bodies, compaction boundaries), and builds the matching hook inputs.
All content is synthetic.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ADAPTER_DIR = REPO_ROOT / "adapters" / "claude-code"
if str(ADAPTER_DIR) not in sys.path:
    sys.path.insert(0, str(ADAPTER_DIR))

from goated_adapter import Config, run_hook  # noqa: E402

ROUTER = "using-goated-ai-skills"


class Session:
    """One synthetic Claude Code session: a transcript file plus hook calls."""

    def __init__(self, root: Path, session_id: str = "session-1") -> None:
        self.root = root
        self.session_id = session_id
        self.transcript = root / f"{session_id}.jsonl"
        self.transcript.write_text("", encoding="utf-8")
        self.config = Config(
            state_dir=root / "state",
            home=root / "home",
            lag_wait_seconds=0.0,
        )
        # Inside the fake home, so instruction-file lookups never leave the
        # temporary folder.
        self.project = root / "home" / "work" / "project"
        self.prompt_id: str | None = None
        self._last_uuid: str | None = None
        self._counter = 0

    # Transcript writers -------------------------------------------------

    def _append(self, entry: dict) -> None:
        entry.setdefault("uuid", str(uuid.uuid4()))
        entry.setdefault("parentUuid", self._last_uuid)
        entry.setdefault("isSidechain", False)
        entry.setdefault("sessionId", self.session_id)
        if self.prompt_id and entry.get("type") in {"user", "assistant"}:
            entry.setdefault("promptId", self.prompt_id)
        self._last_uuid = entry["uuid"]
        with self.transcript.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def raw_line(self, text: str) -> None:
        with self.transcript.open("a", encoding="utf-8") as handle:
            handle.write(text + "\n")

    def prompt(self, text: str, *, hook: bool = True) -> str:
        """Record a typed user prompt; run the user-prompt hook first."""

        self.prompt_id = str(uuid.uuid4())
        output = ""
        if hook:
            output = self.hook(
                "UserPromptSubmit", prompt=text, prompt_id=self.prompt_id
            )
        self._append(
            {"type": "user", "message": {"role": "user", "content": text}}
        )
        return output

    def notify(self, result: str) -> str:
        """Record a background-task notification, which Claude Code submits as a prompt."""

        self.prompt_id = str(uuid.uuid4())
        text = (
            "<task-notification> <task-id>a1</task-id> <status>completed</status> "
            f"<result>{result}</result> </task-notification>"
        )
        output = self.hook("UserPromptSubmit", prompt=text, prompt_id=self.prompt_id)
        self._append(
            {
                "type": "user",
                "promptSource": "system",
                "turnOrigin": "task_notification",
                "origin": {"kind": "task-notification", "producer": "session-task"},
                "message": {"role": "user", "content": text},
            }
        )
        return output

    def say(self, text: str) -> None:
        self._append(
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": text}],
                },
            }
        )

    def _tool_use(self, name: str, tool_input: dict) -> str:
        self._counter += 1
        tool_use_id = f"toolu_{self._counter:04d}"
        self._append(
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": tool_use_id,
                            "name": name,
                            "input": tool_input,
                        }
                    ],
                },
            }
        )
        return tool_use_id

    def _tool_result(
        self, tool_use_id: str, content: str, *, is_error: bool = False, extra=None
    ) -> None:
        entry = {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": content,
                        "is_error": is_error,
                    }
                ],
            },
        }
        if extra:
            entry.update(extra)
        self._append(entry)

    def load(self, skill: str, *, success: bool = True) -> None:
        """Record a Skill tool call and its result, as Claude Code does."""

        tool_use_id = self._tool_use("Skill", {"skill": skill})
        if success:
            self._tool_result(
                tool_use_id,
                f"Launching skill: {skill}",
                extra={"toolUseResult": {"success": True, "commandName": skill}},
            )
            self._append(
                {
                    "type": "user",
                    "isMeta": True,
                    "sourceToolUseID": tool_use_id,
                    "message": {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Base directory for this skill: {skill}"}
                        ],
                    },
                }
            )
        else:
            self._tool_result(
                tool_use_id, f"<tool_use_error>Unknown skill: {skill}</tool_use_error>",
                is_error=True,
            )

    def compact(self) -> str:
        """Record a compaction boundary and run the compact SessionStart hook."""

        self._append(
            {"type": "system", "subtype": "compact_boundary", "content": "Conversation compacted"}
        )
        self._append(
            {
                "type": "user",
                "isCompactSummary": True,
                "message": {"role": "user", "content": "Summary of earlier work."},
            }
        )
        return self.hook("SessionStart", source="compact")

    # Hook calls ---------------------------------------------------------

    def hook(self, event: str, **fields) -> str:
        payload = {
            "session_id": self.session_id,
            "transcript_path": str(self.transcript),
            "cwd": str(self.project),
            "hook_event_name": event,
        }
        if self.prompt_id and "prompt_id" not in fields:
            payload["prompt_id"] = self.prompt_id
        payload.update(fields)
        return run_hook(json.dumps(payload), self.config)

    def call(self, tool: str, tool_input: dict | None = None, **fields) -> dict:
        """Record a tool_use and run PreToolUse for it; return parsed output."""

        tool_input = tool_input or default_input(tool)
        tool_use_id = self._tool_use(tool, tool_input)
        output = self.hook(
            "PreToolUse",
            tool_name=tool,
            tool_input=tool_input,
            tool_use_id=tool_use_id,
            **fields,
        )
        self._tool_result(tool_use_id, "ok")
        return parse(output)


def default_input(tool: str) -> dict:
    if tool in {"Bash", "PowerShell"}:
        return {"command": "echo hi"}
    if tool in {"Read", "Write", "Edit"}:
        return {"file_path": "notes.md", "content": "x"}
    return {}


def parse(output: str) -> dict:
    return json.loads(output) if output.strip() else {}


def decision(output: dict) -> str:
    """Return "deny" for a hold, "pass" for anything that lets the call run."""

    specific = output.get("hookSpecificOutput", {})
    return "deny" if specific.get("permissionDecision") == "deny" else "pass"


def reason(output: dict) -> str:
    return output.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
