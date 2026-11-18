"""The worked example's translator for the conformance runner (Ticket 083).

    uv run python scripts/run_conformance.py adapters/example/conformance_translator.py

The runner plays each scenario's steps, written in the event model's terms,
through this translator. It does what a person and an agent would do in the
toy loop: submit prompts, write replies, use tools. The example adapter sits
in the loop as its hooks. The translator then reads back what the loop did
and showed the agent: whether it blocked, and the `goated-hold:` lines in
what it showed, so a hold the adapter fails to deliver fails the scenario.
Notice kinds come from the adapter's record of the core's decision, and
count only when the loop showed their text.

It maps each call kind to the toy tool that makes it, the inverse of the
adapter's `TOOL_CALLS`, and raises on a call it cannot make faithfully
rather than dropping part of it.
"""

from __future__ import annotations

import re

from goated_example_adapter import GoatedAdapter, python_judge
from toy_loop import HookAnswer, ToolLoop, ToolOutput

HOLD_LINE = re.compile(r"^goated-hold: ([a-z]+(?:-[a-z]+)*) \| (strict|justified-skip)$", re.M)
# The fields every call kind may carry that no toy tool can.
UNSUPPORTED = ("line_text", "action")


def make_translator(setup: dict) -> Translator:
    return Translator(setup)


class Translator:
    """One scenario's session in the toy loop, with the example adapter."""

    def __init__(self, setup: dict, adapter: GoatedAdapter | None = None) -> None:
        self.adapter = adapter or GoatedAdapter(
            setup["project"], setup["home"], "conformance-session",
            installed_skills=setup["installed_skills"], agent=setup["agent"],
            judge=python_judge(setup["state_dir"]))
        self.result: dict = {"ok": True}
        self.loop = ToolLoop({name: self._run for name in TOOLS}, self.adapter)

    def prompt(self, prompt: dict, continues: bool) -> dict:
        return self._read(lambda: self.loop.submit(
            prompt["text"], prompt["author"], prompt.get("pasted", ()),
            prompt.get("starts_session", False), mid_turn=continues))

    def reply(self, text: str) -> None:
        self.loop.say(text)

    def call(self, call: dict, result: dict) -> tuple[dict, dict | None]:
        name, args = tool_use_for(call)
        self.result = result
        seen, shown = len(self.adapter.decisions), len(self.loop.transcript)
        output = self.loop.use_tool(name, args)
        made = self.adapter.decisions[seen:]
        before = next(d for kind, d in made if kind == "pending_call")
        if output.blocked:
            return self._decision(True, [output.text], before), None
        messages = [item["text"] for item in self.loop.transcript[shown:]
                    if item["role"] == "harness"]
        after = next((d for kind, d in made if kind == "finished_call"), None)
        # Before the call ran, the loop showed only the pending decision's notices.
        before_texts = {n["text"] for n in before["notices"]}
        return (self._decision(False, [m for m in messages if m in before_texts], before),
                after and self._decision(False, messages, after))

    def skill_invoked(self, skill: str) -> None:
        self.loop.invoke_skill(skill)

    def agent_finished(self, agent_id: str) -> None:
        self.loop.agent_finished(agent_id)

    def compaction(self) -> None:
        self.loop.compact()

    def turn_end(self) -> dict:
        return self._read(self.loop.end_turn)

    def session_start(self, source: str) -> dict:
        return self._read(lambda: self.loop.start_session(source))

    def _run(self, args: dict) -> ToolOutput:
        """Every toy tool: return what the scenario says the call returns."""

        agent = self.result.get("agent")
        return ToolOutput(ok=self.result["ok"], text=self.result.get("output", ""),
                          ran=self.result.get("ran", True),
                          agent=dict(agent) if agent else None)

    def _read(self, act) -> dict:
        """Run `act`, a loop method that answers with a `HookAnswer`, and
        read the answer as a decision."""

        seen = len(self.adapter.decisions)
        answer: HookAnswer = act()
        return self._decision(answer.block, answer.messages, self.adapter.decisions[seen][1])

    @staticmethod
    def _decision(blocked: bool, shown: list[str], recorded: dict) -> dict:
        """The decision the loop's behaviour shows: held when it blocked,
        with the holds whose lines it showed; the recorded notices whose
        text it showed."""

        text = "\n\n".join(shown)
        starts = list(HOLD_LINE.finditer(text))
        holds = [{"gate": m[1], "kind": m[2],
                  "text": text[m.end():starts[n + 1].start() if n + 1 < len(starts) else None]}
                 for n, m in enumerate(starts)]
        if blocked != bool(holds):
            raise AssertionError(f"the loop {'blocked' if blocked else 'did not block'} but "
                                 f"showed {len(holds)} hold lines")
        notices = [n for n in recorded["notices"] if n["text"] in text]
        return {"decision": "hold" if blocked else "allow", "holds": holds, "notices": notices}


TOOLS = ("edit_file", "write_file", "read_file", "shell", "use_skill", "delegate",
         "git_commit", "open_pull_request", "fetch")


def tool_use_for(call: dict) -> tuple[str, dict]:
    """The toy tool and arguments that make `call`, an event-model call."""

    present = [key for key in UNSUPPORTED if key in call]
    if present:
        raise ValueError(f"no toy tool carries {present}")
    kind = call["kind"]
    if kind == "file_write" and call.get("whole_file"):
        [edit] = call["edits"]
        if edit["removed"] is not None or call.get("creates"):
            raise ValueError("a whole-file write says only what it adds")
        return "write_file", {"path": call["path"], "content": edit["added"]}
    if kind == "file_write":
        return "edit_file", {"path": call["path"], "create": call.get("creates", False),
                             "edits": [{"old": e["removed"], "new": e["added"]}
                                       for e in call["edits"]]}
    if kind == "file_read":
        return "read_file", {"path": call["path"],
                             **({} if call["whole"] else {"lines": [1, 10]})}
    if kind == "shell_command":
        return "shell", {"command": call["command"],
                         "powershell": call["shell"] == "powershell",
                         "background": call.get("background", False)}
    if kind == "skill_load":
        return "use_skill", {"name": call["skill"]}
    if kind == "spawn":
        return "delegate", {"task": call["brief"], "start": call["starts_now"],
                            "read_only": call.get("read_only", False),
                            "separate": call.get("separate", False)}
    if kind == "commit":
        return "git_commit", {"message": call.get("message")}
    if kind == "pull_request":
        return "open_pull_request", {**{k: call[k] for k in ("base", "head") if k in call},
                                     **({"repo": call["repository"]}
                                        if "repository" in call else {})}
    if kind == "other":
        return "fetch", {"url": "https://example.invalid/"}
    raise ValueError(f"no toy tool makes a {kind} call")
