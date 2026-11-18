"""A toy agent harness: the thing an adapter plugs into (Ticket 083).

It stands in for a real tool loop, such as a custom API loop. It has its own
tool names and its own transcript, knows nothing of GOATED, and offers
hooks: one before each tool runs, one after, one when a prompt arrives, one
when the agent ends its turn, and one when a session starts. A hook answers
with a `HookAnswer`: whether to block, and messages to show the agent. The
agent is whatever drives the loop's methods; `run_turn` drives them from a
script, so no model is needed. Nothing runs for real: each tool is a
function the loop's owner supplies.

The transcript is a list of dicts, oldest first, one per thing that
happened:

- `{"role": "user", "text", "author", "pasted", "starts_session", "mid_turn"}`:
  a prompt. `author` is `person`, `session` (another agent session) or
  `host` (the harness itself); `mid_turn` marks one that arrived while the
  agent was still working.
- `{"role": "assistant", "text"}`: the agent's reply text.
- `{"role": "tool", "id", "name", "args", "output"}`: a tool use and its
  `ToolOutput`, as a dict.
- `{"role": "skill", "name"}`: a person invoked a skill by name.
- `{"role": "agent_done", "agent_id"}`: a background agent finished.
- `{"role": "compacted"}`: the loop compacted the conversation.
- `{"role": "end"}`: the agent ended its turn.
- `{"role": "harness", "text"}`: a hook's message to the agent.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field


@dataclass
class ToolOutput:
    """What a tool use returned. `ran` is False when it never started;
    `blocked` when a hook stopped it; `agent` is the agent a delegation
    started, as `{"id", "background"}`."""

    ok: bool = True
    text: str = ""
    ran: bool = True
    blocked: bool = False
    agent: dict | None = None


@dataclass
class HookAnswer:
    """A hook's answer: block the action or not, and what to show the agent."""

    block: bool = False
    messages: list[str] = field(default_factory=list)


Tool = Callable[[dict], ToolOutput]


class Hooks:
    """The hooks a loop calls; each allows and says nothing by default."""

    def at_session_start(self, loop: ToolLoop, source: str) -> HookAnswer:
        return HookAnswer()

    def on_prompt(self, loop: ToolLoop) -> HookAnswer:
        """After a prompt is in the transcript, before the agent sees it."""
        return HookAnswer()

    def before_tool(self, loop: ToolLoop, use: dict) -> HookAnswer:
        """Before `use` runs and before it is in the transcript."""
        return HookAnswer()

    def after_tool(self, loop: ToolLoop, use: dict) -> HookAnswer:
        """After `use` ran and is in the transcript with its output."""
        return HookAnswer()

    def at_turn_end(self, loop: ToolLoop) -> HookAnswer:
        """When the agent ends its turn; a block makes it carry on."""
        return HookAnswer()


class ToolLoop:
    """One agent session: a transcript, tools by name, and hooks."""

    def __init__(self, tools: dict[str, Tool], hooks: Hooks | None = None) -> None:
        self.tools = tools
        self.hooks = hooks or Hooks()
        self.transcript: list[dict] = []
        self._uses = 0

    def start_session(self, source: str = "new") -> HookAnswer:
        """Start (`new`), resume (`resumed`), or restart the session after a
        compaction (`after_compaction`) or a clear (`cleared`)."""

        return self._shown(self.hooks.at_session_start(self, source))

    def submit(self, text: str, author: str = "person", pasted: Iterable[str] = (),
               starts_session: bool = False, mid_turn: bool = False) -> HookAnswer:
        """A prompt arrives. A block withdraws it from the transcript."""

        self.transcript.append({"role": "user", "text": text, "author": author,
                                "pasted": list(pasted), "starts_session": starts_session,
                                "mid_turn": mid_turn})
        answer = self.hooks.on_prompt(self)
        if answer.block:
            self.transcript.pop()
        return self._shown(answer)

    def say(self, text: str) -> None:
        self.transcript.append({"role": "assistant", "text": text})

    def use_tool(self, name: str, args: dict) -> ToolOutput:
        """The agent uses a tool. A blocking `before_tool` answer stops it,
        and the agent gets the hook's messages as the tool's output."""

        self._uses += 1
        use = {"role": "tool", "id": f"use{self._uses}", "name": name, "args": dict(args)}
        answer = self.hooks.before_tool(self, use)
        if answer.block:
            output = ToolOutput(ok=False, text="\n\n".join(answer.messages), blocked=True)
            self.transcript.append({**use, "output": asdict(output)})
            return output
        self._shown(answer)
        output = self.tools[name](use["args"])
        self.transcript.append({**use, "output": asdict(output)})
        self._shown(self.hooks.after_tool(self, self.transcript[-1]))
        return output

    def invoke_skill(self, name: str) -> None:
        self.transcript.append({"role": "skill", "name": name})

    def agent_finished(self, agent_id: str) -> None:
        self.transcript.append({"role": "agent_done", "agent_id": agent_id})

    def compact(self) -> None:
        self.transcript.append({"role": "compacted"})

    def end_turn(self) -> HookAnswer:
        """The agent ends its turn. Unless a hook blocks, the turn is over."""

        answer = self.hooks.at_turn_end(self)
        if not answer.block:
            self.transcript.append({"role": "end"})
        return self._shown(answer)

    def run_turn(self, prompt: str, agent: Callable[[ToolLoop], bool]) -> None:
        """Submit `prompt`, then let `agent` act until it ends a turn that
        no hook blocks. `agent(loop)` takes one or more steps through the
        loop's methods and returns True when it wants to end the turn."""

        self.submit(prompt)
        while True:
            if agent(self) and not self.end_turn().block:
                return

    def _shown(self, answer: HookAnswer) -> HookAnswer:
        """Show the agent each message of `answer`."""

        self.transcript.extend({"role": "harness", "text": m} for m in answer.messages)
        return answer
