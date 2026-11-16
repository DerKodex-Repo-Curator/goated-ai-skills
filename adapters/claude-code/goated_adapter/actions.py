"""Action gates (commit, pull request, spawn, design, security) and the closeout gate.

These enforce skill triggers the skills already state (ADR 0003): commit with
`commit-message`, open a pull request with `pr-description`, brief a new agent
with `handoff`'s spawn brief or `subagent-driven-development`, design with
`software-design-principles`, review sensitive surfaces with
`code-security-review`, and close a code-changing turn with proof, `doc-sync`,
`handoff`, and the design red flags.

Every decision is a pure function of the current turn as the transcript
records it, plus the user's typed overrides for that turn. So an unchanged
retry always gets the same answer (spec R6), and a hold stops firing as soon
as the turn shows compliance. Proof counts only within the current turn
(spec R7): a skill loaded in an earlier turn does not cover a later action.

Strict holds clear only on proof or a user override. Justified-skip holds also
clear on a `goated-skip: <skill>: <reason>` line in the current turn.
"""

from __future__ import annotations

import os
import re

from . import contracts, shell
from .gates import COMMAND_TOOLS, STRICT, Hold, goated_skill_name
from .markers import parse_reply
from .transcript import Turn

JUSTIFIED_SKIP = "justified-skip"

COMMIT_SKILL = "commit-message"
PR_SKILL = "pr-description"
DESIGN_SKILL = "software-design-principles"
SECURITY_SKILL = "code-security-review"
DOC_SYNC_SKILL = "doc-sync"
HANDOFF_SKILL = "handoff"
PROOF_SKILL = "verification-before-completion"
RED_FLAGS_REFERENCE = "software-design-principles/references/red-flags.md"

# Tools that start another agent, each with the input field that carries the
# brief. A call without a brief (an offer card, or starting a saved proposal)
# hands over no text, so it is not held.
SPAWN_BRIEF_FIELDS = {
    "Agent": "prompt",
    "Task": "prompt",  # The spawn tool's name in older Claude Code versions.
    "mcp__ccd_session__start_session": "prompt",
    "mcp__ccd_session__hand_off_to_session": "remaining_plan",
}
# MCP tools that open a pull or merge request, such as a GitHub server's.
PR_TOOL_RE = re.compile(r"^mcp__.+__create_(?:pull|merge)_request$")
# MCP tools that record a commit, such as a GitHub server's file tools or a git
# server's commit tool; each carries its message in `message`.
COMMIT_TOOL_RE = re.compile(
    r"^mcp__.+__(?:push_files|create_or_update_file|delete_file|git_commit|create_commit"
    r"|commit_changes|commit)$"
)
FILE_WRITE_TOOLS = {"Edit": "file_path", "Write": "file_path", "MultiEdit": "file_path",
                    "NotebookEdit": "notebook_path"}
# An edit adding at least this many lines is a design change, not a tiny fix.
DESIGN_MIN_LINES = 5

CODE_EXTENSIONS = frozenset(
    ".py .js .jsx .ts .tsx .mjs .cjs .go .rs .java .kt .kts .swift .c .h .cpp .hpp .cc .cs "
    ".rb .php .scala .ps1 .psm1 .sh .bash .lua .dart .vue .svelte .sql .ex .exs .clj .fs "
    ".zig .r .jl .ipynb".split()
)
DOC_EXTENSIONS = (".md", ".mdx", ".rst", ".adoc", ".txt")
TEST_PATH_RE = re.compile(
    r"(?:^|/)(?:tests?|spec|__tests__)/|(?:^|/)test_[^/]*$|_test\.[^/.]+$|\.(?:test|spec)\.[^/.]+$",
    re.IGNORECASE,
)
# Security-sensitive surfaces, by path. The first matching category is named.
# Paths are lowercased with camelCase humps split by `_` first, and words must
# stand alone between `/`, `.`, `_`, or `-`, so `tokenizer.py` and `author.py`
# are not secrets or auth, while `api_token.py` and `userAuth.ts` are.
_ALONE = r"(?<![a-z0-9])(?:{})(?![a-z0-9])"
SECURITY_CATEGORIES = (
    ("dependencies", re.compile(
        r"(?:^|/)(?:package(?:-lock)?\.json|pnpm-lock\.yaml|yarn\.lock|requirements[^/]*\.(?:txt|in)"
        r"|pyproject\.toml|poetry\.lock|uv\.lock|pipfile(?:\.lock)?|cargo\.(?:toml|lock)"
        r"|go\.(?:mod|sum)|gemfile(?:\.lock)?|composer\.(?:json|lock)|[^/]+\.csproj)$")),
    ("secrets", re.compile(
        r"(?:^|/)\.env(?:\.[^/]*)?$|\.(?:pem|key|p12|pfx)$|(?:^|/)id_(?:rsa|ed25519|ecdsa)|"
        + _ALONE.format(r"secrets?|credentials?|tokens?|api_?keys?"))),
    ("auth", re.compile(_ALONE.format(
        r"auth|authn|authz|authenticat\w*|authoriz\w*|oauth2?|login|logout|signin|jwt"
        r"|passwords?|permissions?|rbac|acls?|polic(?:y|ies)|sessions?"))),
    ("persistence", re.compile(r"(?:^|/)migrations?/|(?:^|/)schema\.(?:sql|prisma)$|\.sql$")),
    ("deploy-and-ci", re.compile(
        r"(?:^|/)dockerfile|docker-compose|(?:^|/)\.github/workflows/|\.gitlab-ci|(?:^|/)terraform/"
        r"|\.tf$|(?:^|/)k8s/|(?:^|/)helm/|serverless\.ya?ml$")),
)
# Only dependency manifests among docs-like files (`requirements.txt`) are sensitive.
ALWAYS_CHECKED_CATEGORIES = frozenset({"dependencies"})


class _Proof:
    """What the current turn shows: loads, skip lines, reads, and user skips."""

    def __init__(self, turn: Turn, overrides: dict, namespaces: tuple[str, ...],
                 extra_text: str = "") -> None:
        self.turn = turn
        self.loads = {goated_skill_name(raw, namespaces) for raw in turn.loads} - {None}
        self.skips = {skip["skill"] for skip in turn.skips}
        if extra_text:
            self.skips |= {skip["skill"] for skip in parse_reply(extra_text).skips}
        self.user_skips = set(overrides.get("skills") or ())
        self.overrides = overrides

    def loaded(self, skill: str) -> bool:
        return skill in self.loads or skill in self.user_skips

    def skipped(self, skill: str) -> bool:
        return skill in self.skips or skill in self.user_skips

    def loaded_or_skipped(self, skill: str) -> bool:
        return self.loaded(skill) or skill in self.skips

    def read(self, reference: str, after: int = -1) -> bool:
        return any(
            index > after and call.name == "Read" and call.ok
            and _ends_with_path(str(call.input.get("file_path") or ""), reference)
            for index, call in enumerate(self.turn.calls)
        )


def is_action_tool(tool_name: str) -> bool:
    """True for a tool some action gate may hold (the hook matcher must cover these)."""

    return (
        tool_name in COMMAND_TOOLS or tool_name in SPAWN_BRIEF_FIELDS
        or tool_name in FILE_WRITE_TOOLS or bool(PR_TOOL_RE.match(tool_name))
        or bool(COMMIT_TOOL_RE.match(tool_name))
    )


def check_action(tool_name: str, tool_input: dict, turn: Turn, overrides: dict,
                 namespaces: tuple[str, ...] = ()) -> Hold | None:
    """Return the action hold for this call, if any; the call's own entry is not yet proof."""

    proof = _Proof(turn, overrides, namespaces)
    if tool_name in COMMAND_TOOLS:
        command = shell.analyze(str(tool_input.get("command") or ""))
        hold = _commit_hold(command.commit_message, proof) if command.commit else None
        if hold is None and command.opens_pr:
            hold = _pr_hold(proof)
        for target in command.write_targets:
            hold = hold or _security_hold(_norm(target), proof)
        return hold
    if PR_TOOL_RE.match(tool_name):
        return _pr_hold(proof)
    if COMMIT_TOOL_RE.match(tool_name):
        message = tool_input.get("message")
        return _commit_hold(message if isinstance(message, str) else None, proof)
    if tool_name in SPAWN_BRIEF_FIELDS:
        brief = str(tool_input.get(SPAWN_BRIEF_FIELDS[tool_name]) or "")
        return _spawn_hold(brief, proof) if brief.strip() else None
    if tool_name in FILE_WRITE_TOOLS:
        path = _norm(str(tool_input.get(FILE_WRITE_TOOLS[tool_name]) or ""))
        return _security_hold(path, proof) or _design_hold(path, tool_input, proof)
    return None


def _commit_hold(message: str | None, proof: _Proof) -> Hold | None:
    """Hold a commit until `commit-message` loads; `message` is its inline text, if known."""

    supplied = proof.overrides.get("commit_message")
    if supplied and message is not None and (
        _subject(message) == _subject(supplied)
    ):
        return None  # The user typed this message (spec R8).
    if not proof.loaded(COMMIT_SKILL):
        return Hold(
            "commit", STRICT,
            f"Load the `{COMMIT_SKILL}` skill with the Skill tool in this turn and draft "
            "the message with it, then run the commit again. The whole command was "
            "held, so rerun any steps chained before it too. This hold is strict: a "
            "`goated-skip` line does not clear it. A commit message the user typed in "
            "their prompt stands it down when the commit uses that message.",
        )
    if message is None or COMMIT_SKILL in proof.user_skips:
        return None
    problems = contracts.commit_message_problems(message)
    if not problems:
        return None
    return Hold(
        "commit", STRICT,
        f"The commit message breaks the `{COMMIT_SKILL}` contract: "
        + "; ".join(problems) + ". Fix the message and run the commit again.",
    )


def _pr_hold(proof: _Proof) -> Hold | None:
    if proof.loaded(PR_SKILL):
        return None
    return Hold(
        "pull-request", STRICT,
        f"Load the `{PR_SKILL}` skill with the Skill tool in this turn and draft the "
        "title and body with it, then open the pull request again. The whole command "
        "was held, so rerun any steps chained before it too. This hold is strict: a "
        "`goated-skip` line does not clear it.",
    )


def _spawn_hold(brief: str, proof: _Proof) -> Hold | None:
    if proof.user_skips & {t.skill for t in contracts.BRIEF_TEMPLATES}:
        return None  # The user typed `skip handoff` or `skip subagent-driven-development`.
    loaded = [t for t in contracts.BRIEF_TEMPLATES if t.skill in proof.loads]
    if not loaded:
        return Hold(
            "spawn", STRICT,
            f"Before starting another agent or session with a brief, load `{HANDOFF_SKILL}` "
            "with the Skill tool in this turn, read its `references/spawn-brief.md`, and "
            "write the brief from that template (Goal, Scope, Done Means at least). For a "
            "scoped implementation or review task, load `subagent-driven-development` "
            "and fill its implementer or reviewer prompt instead. Nothing was started. "
            "This hold is strict: a `goated-skip` line does not clear it.",
        )
    read =[t for t in loaded if proof.read(t.reference)]
    if not read:
        files = " or ".join(f"`{t.reference}`" for t in loaded)
        return Hold(
            "spawn", STRICT,
            f"Read {files} with the Read tool in this turn and write the brief from it. "
            "The template is the point of this step, so the skill load alone does not "
            "clear the hold. Nothing was started.",
        )
    if any(not t.missing_headings(brief) for t in read):
        return None
    gaps = "; ".join(
        f"`{t.reference}` needs " + ", ".join(f"`## {h}`" for h in t.missing_headings(brief))
        for t in read
    )
    return Hold(
        "spawn", STRICT,
        f"The brief lacks headings its template keeps: {gaps}. Add them as Markdown "
        "headings and start it again. Nothing was started.",
    )


def _security_hold(path: str, proof: _Proof) -> Hold | None:
    category = security_category(path)
    if category is None or proof.loaded_or_skipped(SECURITY_SKILL):
        return None
    return Hold(
        "security", JUSTIFIED_SKIP,
        f"`{path.rsplit('/', 1)[-1]}` is a security-sensitive surface ({category}). Load "
        f"`{SECURITY_SKILL}` with the Skill tool in this turn and review this change with "
        "it. If the change crosses no trust boundary and touches no auth, secrets, "
        "persistence, execution, dependency, or deployment behaviour, write "
        f"`goated-skip: {SECURITY_SKILL}: <reason>` on its own line instead, then make the "
        "edit again. This edit was not applied.",
    )


def _design_hold(path: str, tool_input: dict, proof: _Proof) -> Hold | None:
    if not is_code(path) or added_lines(tool_input) < DESIGN_MIN_LINES:
        return None
    if proof.loaded_or_skipped(DESIGN_SKILL):
        return None
    return Hold(
        "design", JUSTIFIED_SKIP,
        f"This is a substantial code change. Load `{DESIGN_SKILL}` with the Skill tool in "
        "this turn and apply its 'Before changing code' rules to it. If the edit is "
        f"mechanical, with no design in it, write `goated-skip: {DESIGN_SKILL}: <reason>` "
        "on its own line instead, then make the edit again. This edit was not applied.",
    )


# Closeout ---------------------------------------------------------------------

def check_closeout(turn: Turn, overrides: dict, namespaces: tuple[str, ...] = (),
                   final_text: str = "", subagents: dict | None = None,
                   cwd: str | None = None) -> Hold | None:
    """Return the closeout hold for a turn about to end, if any.

    A turn that changed code needs, after its last code change, a check
    command (proof). It also needs `doc-sync` when non-test code changed,
    `handoff` when the last check after the change failed (work left
    unfinished), and a read of the design red flags after the change when
    `software-design-principles` was loaded. Each item accepts a skip line;
    `final_text` is the reply being finished, which may not be in the
    transcript yet.

    `subagents` maps the agent id of each subagent this turn spawned to its
    turns. Their code changes count as made at the spawn; a subagent that ran
    a check after its own last change has already proved them. Only files
    inside `cwd`, the project folder, count; a scratch file elsewhere does not.
    """

    changes = list(_code_changes(turn, subagents or {}, cwd))
    if not changes:
        return None
    last = changes[-1].index
    unproven = [c.index for c in changes if not c.proven]
    proof = _Proof(turn, overrides, namespaces, final_text)
    items = []
    checks = _checks(turn.calls[max(unproven, default=last) + 1 :])
    # Loading a verification skill is not proof; a check run, or a skip, is.
    if unproven and not checks and not proof.skipped(PROOF_SKILL):
        items.append(
            "- Proof: no test, lint, build, or check command ran after the last code "
            "change. Run the relevant check, or, if none can run, write "
            f"`goated-skip: {PROOF_SKILL}: <reason>` and tell the user it is unverified."
        )
    if checks and not checks[-1].ok and not proof.loaded_or_skipped(HANDOFF_SKILL):
        items.append(
            "- Unfinished: the last check after the change failed. Fix it, or load "
            f"`{HANDOFF_SKILL}` and leave a handoff for what remains, or write "
            f"`goated-skip: {HANDOFF_SKILL}: <reason>`."
        )
    non_test = any(not TEST_PATH_RE.search(path) for change in changes for path in change.paths)
    if non_test and not proof.loaded_or_skipped(DOC_SYNC_SKILL):
        items.append(
            f"- Docs: code changed. Load `{DOC_SYNC_SKILL}` and check whether durable docs "
            "now drift, or, if behavior and interfaces did not change, write "
            f"`goated-skip: {DOC_SYNC_SKILL}: <reason>`."
        )
    if DESIGN_SKILL in proof.loads and not proof.read(RED_FLAGS_REFERENCE, after=last) and (
        not proof.skipped(DESIGN_SKILL)
    ):
        items.append(
            f"- Design: read `{RED_FLAGS_REFERENCE}` with the Read tool after your last "
            "change and scan the diff against it, or write "
            f"`goated-skip: {DESIGN_SKILL}: <reason>`."
        )
    if not items:
        return None
    return Hold(
        "closeout", JUSTIFIED_SKIP,
        "Before finishing this turn, which changed code:\n" + "\n".join(items)
        + "\nA skip line must name the skill and give a reason of three or more words.",
    )


class _Change:
    """A finished call that changed code: where in the turn, which files, and
    whether a subagent already proved it."""

    __slots__ = ("index", "paths", "proven")

    def __init__(self, index: int, paths: list[str], proven: bool = False) -> None:
        self.index = index
        self.paths = paths
        self.proven = proven


# Stands for files a shell write changed without naming them (`git apply`).
UNNAMED_FILES = "<files the command does not name>"


def _code_changes(turn: Turn, subagents: dict, cwd: str | None):
    """Yield a `_Change` for each finished call that changed code, in order."""

    for index, call in enumerate(turn.calls):
        if call.ok and call.agent_id in subagents and call.name in SPAWN_BRIEF_FIELDS:
            calls = [c for sub_turn in subagents[call.agent_id] for c in sub_turn.calls]
            changed = [_changed_paths(c, cwd) for c in calls]
            if any(changed):
                last = max(i for i, paths in enumerate(changed) if paths)
                proven = bool(_checks(calls[last + 1 :]))
                yield _Change(index, [p for paths in changed for p in paths], proven)
            continue
        paths = _changed_paths(call, cwd)
        if paths:
            yield _Change(index, paths)


def _changed_paths(call, cwd: str | None) -> list[str]:
    """The project code files one finished call changed; only real write targets count."""

    if not call.ok:
        return []
    if call.name in FILE_WRITE_TOOLS:
        targets = [str(call.input.get(FILE_WRITE_TOOLS[call.name]) or "")]
        unnamed = False
    elif call.name in COMMAND_TOOLS:
        command = shell.analyze(str(call.input.get("command") or ""))
        targets, unnamed = command.write_targets, command.unknown_writes
    else:
        return []
    paths = [_norm(t) for t in targets if is_code(_norm(t)) and _in_project(t, cwd)]
    return paths + ([UNNAMED_FILES] if unnamed else [])


def _in_project(path: str, cwd: str | None) -> bool:
    """True for a relative path, or one under `cwd`; decided without touching the disk."""

    if not cwd or not (os.path.isabs(path) or path.startswith(("/", "\\"))):
        return True
    root = os.path.normcase(os.path.abspath(cwd))
    full = os.path.normcase(os.path.abspath(path))
    return full == root or full.startswith(root.rstrip(os.sep) + os.sep)


def _checks(calls) -> list:
    return [
        call for call in calls
        if call.name in COMMAND_TOOLS and shell.analyze(str(call.input.get("command") or "")).is_check
    ]


# Paths and edits ----------------------------------------------------------------

def is_code(path: str) -> bool:
    dot = path.rfind(".")
    return dot > path.rfind("/") and path[dot:].lower() in CODE_EXTENSIONS


def security_category(path: str) -> str | None:
    if not path:
        return None
    lowered = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", _norm(path)).lower()
    is_doc = lowered.endswith(DOC_EXTENSIONS)
    for name, pattern in SECURITY_CATEGORIES:
        if (not is_doc or name in ALWAYS_CHECKED_CATEGORIES) and pattern.search(lowered):
            return name
    return None


def added_lines(tool_input: dict) -> int:
    texts = [tool_input.get("content"), tool_input.get("new_string"), tool_input.get("new_source")]
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        texts += [e.get("new_string") for e in edits if isinstance(e, dict)]
    return sum(len(t.split("\n")) for t in texts if isinstance(t, str) and t)


def _subject(message: str) -> str:
    return " ".join(message.strip().split("\n", 1)[0].split())


def _norm(path: str) -> str:
    return path.replace("\\", "/")


def _ends_with_path(path: str, suffix: str) -> bool:
    path = _norm(path).lower()
    return path == suffix or path.endswith("/" + suffix)
