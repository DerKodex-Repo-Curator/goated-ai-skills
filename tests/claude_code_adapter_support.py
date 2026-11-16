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
# A Windows-style install path, so the reader's path matching covers backslashes.
SPAWN_BRIEF_PATH = "D:\\goated\\skills\\handoff\\references\\spawn-brief.md"
BRIEF = (
    "## Goal\n\nAudit the exporter.\n\n## Scope\n\n- Work in: src/export/\n\n"
    "## Done Means\n\n- A list of findings.\n"
)


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
        # A subagent writes its own sidechain transcript, but its hook input
        # names the parent's transcript.
        self.sidechain = False
        self.hook_transcript = self.transcript

    def subagent(self, agent_id: str) -> "Session":
        """A subagent of this session, writing where Claude Code puts its transcript."""

        agent = Session.__new__(Session)
        agent.__dict__.update(self.__dict__)
        folder = self.root / self.session_id / "subagents"
        folder.mkdir(parents=True, exist_ok=True)
        agent.transcript = folder / f"agent-{agent_id}.jsonl"
        agent.transcript.write_text("", encoding="utf-8")
        agent.sidechain = True
        agent.prompt_id = None
        agent._last_uuid = None
        agent._counter = 1000
        return agent

    # Transcript writers -------------------------------------------------

    def _append(self, entry: dict) -> None:
        entry.setdefault("uuid", str(uuid.uuid4()))
        entry.setdefault("parentUuid", self._last_uuid)
        entry.setdefault("isSidechain", self.sidechain)
        entry.setdefault("sessionId", self.session_id)
        if self.prompt_id and entry.get("type") == "user":
            # Claude Code records promptId on user entries only.
            entry.setdefault("promptId", self.prompt_id)
        self._last_uuid = entry["uuid"]
        with self.transcript.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def raw_line(self, text: str) -> None:
        with self.transcript.open("a", encoding="utf-8") as handle:
            handle.write(text + "\n")

    def prompt(self, text: str, *, hook: bool = True, **fields) -> str:
        """Record a typed user prompt; run the user-prompt hook first.

        By default the entry carries `origin.kind: human`, as the desktop app
        records typed prompts. Pass `origin=None` for the bare shape `claude -p`
        records, or other `fields` to imitate prompts Claude Code writes itself.
        """

        self.prompt_id = str(uuid.uuid4())
        output = ""
        if hook:
            output = self.hook(
                "UserPromptSubmit", prompt=text, prompt_id=self.prompt_id
            )
        entry = {"type": "user", "origin": {"kind": "human"}, "turnOrigin": "human"}
        entry.update(fields)
        if entry.get("origin") is None:
            entry.pop("origin")
        entry["message"] = {"role": "user", "content": text}
        self._append(entry)
        return output

    def slash(self, skill: str, args: str = "") -> str:
        """Record a skill the user invoked by typing `/<skill>`, as Claude Code does."""

        text = (
            f"<command-message>{skill}</command-message>\n"
            f"<command-name>/{skill}</command-name>\n"
            f"<command-args>{args}</command-args>"
        )
        output = self.prompt(text)
        self._append(
            {
                "type": "user",
                "isMeta": True,
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Base directory for this skill: {skill}"}
                    ],
                },
            }
        )
        return output

    def peer(self, text: str) -> str:
        """Record a message another Claude session sent, which nobody typed here."""

        return self.prompt(
            f'<cross-session-message from="local_peer" from-name="Peer">\n{text}\n'
            "</cross-session-message>",
            origin=None,
            promptSource="sdk",
            turnOrigin="sdk",
        )

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

    def read(self, path: str, *, success: bool = True) -> None:
        """Record a finished Read tool call, as Claude Code does."""

        tool_use_id = self._tool_use("Read", {"file_path": path})
        self._tool_result(tool_use_id, "file text" if success else "File does not exist.",
                          is_error=not success)

    def run(self, command: str, *, success: bool = True, tool: str = "Bash") -> dict:
        """Run a shell command through PreToolUse, then record its result."""

        tool_input = {"command": command}
        tool_use_id = self._tool_use(tool, tool_input)
        output = self.hook(
            "PreToolUse", tool_name=tool, tool_input=tool_input, tool_use_id=tool_use_id
        )
        held = parse(output).get("hookSpecificOutput", {}).get("permissionDecision") == "deny"
        ok = success and not held
        self._tool_result(tool_use_id, "ok" if ok else "Exit code 1\nfailed", is_error=not ok)
        return parse(output)

    def brief_with_handoff(self) -> None:
        """Load `handoff` and read its spawn-brief template, as the spawn hold asks."""

        self.load("handoff")
        self.read(SPAWN_BRIEF_PATH)

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
            "transcript_path": str(self.hook_transcript),
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
        # Claude Code records a held call as an error result carrying the reason.
        held = reason(parse(output))
        self._tool_result(tool_use_id, held or "ok", is_error=bool(held))
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
