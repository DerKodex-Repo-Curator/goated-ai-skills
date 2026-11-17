"""Action gates (commit, pull request and its review, spawn, design, security,
conflict resolution, repeated failure) and the closeout gate.

These enforce skill triggers the skills already state (ADR 0003): commit with
`commit-message`, open a pull request with `pr-description` (and, when it is
large, `standards-and-spec-review`), brief a new agent
with `handoff`'s spawn brief or `subagent-driven-development`, design with
`software-design-principles`, review sensitive surfaces with
`code-security-review`, resolve a merge conflict with
`resolving-merge-conflicts`, investigate a check that keeps failing with
`diagnose`, close a code-changing turn with proof, `doc-sync`, `handoff`,
the design red flags, citations of the design references it required, a
review when the branch is large, and `verification-before-completion` when
the work is large, delegated, sensitive, or on a `full` route, and close a
turn that changed setup with `setup-scribe`. The `reference-reads` gate
enforces the reads the installed registry declares for a loaded skill's
references (`reference_reads`).

Every decision is a pure function of the current turn as the transcript
records it, the user's typed overrides for that turn, and what counts from
earlier turns until the next compaction (`SinceCompaction`): skill loads,
design and skill reference reads, and spawn-brief template reads, whose text
is still in the agent's context. So an unchanged retry always gets the same answer
(spec R6), and a hold stops firing as soon as the turn shows compliance.
Everything else counts only within the current turn: skip lines, overrides,
change reads, and checks. Inside a subagent nothing carries over from its
earlier turns. The inputs from outside the transcript include a pull
request's size, which the `pr-review` gate asks git for, and only when its
hold would otherwise fire; the branch's work, which the closeout's Review
and Verification items ask git for only when nothing else met them; which
brief templates the turn's spawns followed, which the hooks record when the
`spawn` gate lets one through; the design skill's section ids, which the
closeout reads from the installed skill only when it checks citations; and
the registry's reference declarations, read only for an edit of a project
file.

Strict holds clear only on proof or a user override. Justified-skip holds also
clear on a `goated-skip: <skill>: <reason>` line in the current turn.

Holds whose step reviews or describes the change (the closeout's design,
docs, and security items, the commit, the pull request, and its review) also
need a change read (spec R7): a finished call, after the skill load or reference
read and after the last code change, that put the change's content in front
of the agent. That is a command printing the diff, or a Read of a file the
turn changed. It shows the agent the change; it cannot prove a review.
"""

from __future__ import annotations

import functools
import os
from collections.abc import Callable
from typing import NamedTuple
import re
import subprocess
import time
from stat import S_ISLNK, S_ISREG

from . import contracts, design_reads, reference_reads, shell
from .gates import (
    COMMAND_TOOLS, STRICT, Hold, goated_skill_name, spawns_a_reader, unseen_line_advice,
)
from .markers import declared_files, parse_reply
from .transcript import Turn, skill_name

JUSTIFIED_SKIP = "justified-skip"

COMMIT_SKILL = "commit-message"
PR_SKILL = "pr-description"
DESIGN_SKILL = "software-design-principles"
SECURITY_SKILL = "code-security-review"
DOC_SYNC_SKILL = "doc-sync"
HANDOFF_SKILL = "handoff"
PROOF_SKILL = "verification-before-completion"
DIAGNOSE_SKILL = "diagnose"
# How many failures in a row of one check command, in one turn, make the repeated-failure hold.
REPEATED_FAILURES = 2
# A trailing pipe into an output filter, whose arguments hold no further pipe.
PIPE_TAIL_RE = re.compile(
    r"\s*\|\s*(?:tail|head|grep|egrep|findstr|more|less|tee|tee-object|select-object|select"
    r"|select-string|sls|out-host|out-string)\b[^|]*$",
    re.IGNORECASE,
)
STDERR_MERGE_RE = re.compile(r"\s*(?:2|\*)>&1$")
# A failed call that never ran: a permission refusal, another hook's denial, or an interruption.
NOT_RUN_RE = re.compile(
    r"(?:The user doesn[’']t want to|Permission for this \w+ was denied|PreToolUse:\S+ hook error"
    r"|\[Request interrupted by user)"
)
# What test runners, linters, and compilers print when they fail.
FAILURE_SIGNS_RE = re.compile(
    r"\b[1-9]\d* (?:failed|failing|errors?|fail)\b|^FAILED\b|^FAIL\b|--- FAIL|npm ERR!"
    r"|^npm error\b|\berror TS\d+|\berror\[E\d+\]|test result: FAILED|^error: ",
    re.MULTILINE,
)

class _LoadErrorSigns(NamedTuple):
    """How one test runner reports a test module it could not load.

    `start` is the runner's own header for one such error; the error's text
    runs to the next line matching `end`. `real_failure` is what the runner
    prints for a failure in a test that did run.
    """

    start: re.Pattern
    end: re.Pattern
    real_failure: re.Pattern


def _signs(start: str, end: str, real_failure: str) -> _LoadErrorSigns:
    return _LoadErrorSigns(*(re.compile(p, re.MULTILINE) for p in (start, end, real_failure)))


# What test runners print when a test module could not be loaded. A run whose
# only failures are such errors, each caused by a missing module or name,
# failed before any test ran: in TDD the first red run is often one, because
# the module under test does not exist yet, and the agent knows why. A module
# that is there but broken (a SyntaxError, a NameError) is the edit-and-crash
# loop the gate exists for, so it counts. Only the runner's own headers count,
# so a test that prints import-error text is a real failure.
LOAD_ERROR_SIGNS = (
    _signs(  # pytest
        r"^_+ ERROR collecting \S.* _+$", r"^(?:_{3,} \S|={3,} )",
        r"^(?:=+ )?[1-9]\d* failed\b|^(?:FAILED|ERROR) \S+::",
    ),
    _signs(  # unittest
        r"^ERROR: \S+ \(unittest\.loader\._FailedTest\b", r"^={20,}$|^Ran \d+ tests? in ",
        r"^FAIL: |^ERROR: (?!\S+ \(unittest\.loader\._FailedTest\b)|^FAILED \(.*\bfailures=[1-9]",
    ),
    _signs(  # jest
        r"^\s*● Test suite failed to run$", r"^\s*●|^\s*(?:FAIL|PASS) |^Test Suites:",
        r"^Tests:.*\b[1-9]\d* failed\b|^\s*● (?!Test suite failed to run$)",
    ),
)
# The lines in a load error's text that name its cause, the last one winning:
# a Python exception line, plain or with pytest's `E` prefix; pytest's own
# line for an import error, which it prints before the traceback, so it
# survives a cut; and jest's missing-module message.
LOAD_ERROR_CAUSE_RE = re.compile(
    r"^(?:E\s+|\s*)(?:(?P<exception>[A-Z]\w*(?:Error|Exception)):"
    r"|(?P<missing>ImportError while importing test module|Cannot find module) ')",
    re.MULTILINE,
)
MISSING_MODULE_EXCEPTIONS = frozenset({"ImportError", "ModuleNotFoundError"})
SETUP_SKILL = "setup-scribe"
REVIEW_SKILL = "standards-and-spec-review"
RED_FLAGS_REFERENCE = "software-design-principles/references/red-flags.md"
# The question `red-flags.md` ends with, which the closeout's red-flags item
# repeats. No hold checks an answer.
RED_FLAGS_QUESTION = "Name one input that would break this change, and say what happens."
# Where a design citation counts besides reply text: the call fields that carry
# route and skip lines (`transcript.LINE_FIELDS`). Named without backticks, so
# the skill-usage mod reads no skill from them.
CITATION_FIELDS = "a shell or agent call's description or a Skill call's args"
# Why a commit-time citation belongs in those fields rather than reply text.
UNSEEN_AT_COMMIT = (
    "Reply text may not be seen at commit: text in the commit's own message is recorded "
    "only after this check, and earlier text can be stored as a summary that drops it."
)

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
# How a hold asks for a change read. No command is backticked: the skill-usage
# mod reads a backticked name as a skill to load.
CHANGE_READ = (
    "print its diff with a git diff or git show command, or Read a file you changed; "
    "a listing of names or counts, such as --stat or --name-only, does not count"
)
# The same, for a turn that changed no file it names, where a Read cannot count.
DIFF_ONLY_READ = (
    "this turn changed no file it can name, so print the diff with a git diff or git "
    "show command; a listing of names or counts, such as --stat or --name-only, does "
    "not count"
)
# Merge conflicts (spec G1). Markers count only at a line start, as git
# writes them, or after the line number a Read result puts there; `=======`
# alone is also a heading underline, so it is not one.
CONFLICT_SKILL = "resolving-merge-conflicts"
CONFLICT_MARKER_RE = re.compile(r"^(?:[ \t]*\d+(?:\t|→))?(?:<{7}|>{7})(?: |\r?$)", re.MULTILINE)
# `git` and any global options before its subcommand, within one simple command.
_GIT = r"(?<![\w-])git(?:\.exe)?\s(?:[^;&|\n]*\s)?"
_GIT_OPERATIONS = r"merge|rebase|cherry-pick|revert"
# A command naming one of the operations the skill covers; a `pull` merges or rebases.
GIT_CONFLICT_COMMAND_RE = re.compile(rf"{_GIT}(?:{_GIT_OPERATIONS}|pull)(?![\w-])")
# A command that ends one, whether the conflict was resolved or given up.
GIT_CONFLICT_END_RE = re.compile(
    rf"{_GIT}(?:{_GIT_OPERATIONS})\s(?:[^;&|\n]*\s)?--(?:abort|quit|continue|skip)(?![\w-])"
)
# The line git prints when one of them stops on a conflict: a merge's, or a
# rebase's, cherry-pick's, or revert's (older git prefixes `error: `).
GIT_CONFLICT_RESULT_RE = re.compile(
    r"^(?:Automatic merge failed|(?:error: )?could not (?:apply|revert) )",
    re.MULTILINE | re.IGNORECASE,
)
# An edit adding at least this many lines is a design change, not a tiny fix.
DESIGN_MIN_LINES = 5
# A pull request, or a branch's work at the closeout, changing at least this
# many lines against its base, added plus deleted, is large enough to review
# before it lands: the threshold `standards-and-spec-review` states (adapter
# README, Large pull requests).
REVIEW_MIN_LINES = 400
# The route intensity whose work always needs `verification-before-completion` (spec R3).
FULL_ROUTE = "full"
# How long the size check's git calls may take in all before it gives up and
# holds nothing.
SIZE_TIMEOUT_SECONDS = 2.0
# How much of an untracked file the branch-size check reads at a time.
UNTRACKED_READ_BYTES = 1 << 20
# Where a pull request merges into when it names no base, in order of preference.
DEFAULT_BASE_REFS = (
    "refs/remotes/origin/HEAD", "refs/remotes/origin/main", "refs/remotes/origin/master",
    "refs/heads/main", "refs/heads/master",
)

CODE_EXTENSIONS = frozenset(
    ".py .js .jsx .ts .tsx .mjs .cjs .go .rs .java .kt .kts .swift .c .h .cpp .hpp .cc .cs "
    ".rb .php .scala .ps1 .psm1 .sh .bash .lua .dart .vue .svelte .sql .ex .exs .clj .fs "
    ".zig .r .jl .ipynb".split()
)
DOC_EXTENSIONS = (".md", ".mdx", ".rst", ".adoc", ".txt")
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
# Env and settings files whose change is setup (spec G3): `.env` and `.env.*`,
# and `settings*.json` under `.claude/` or `.vscode/`. They count only inside
# the project (spec R9), so a scratch folder's or `~/.claude`'s settings do not.
SETUP_FILE_RE = re.compile(
    r"(?:^|/)\.env(?:\.[^/]*)?$|(?:^|/)\.(?:claude|vscode)/settings[^/]*\.json$", re.IGNORECASE
)


class SinceCompaction(NamedTuple):
    """What counts from earlier turns until the next compaction (spec R3, R4):
    the GOATED skills loaded (`tdd`), the design references read
    (`errors.md`), the spawn-brief templates read
    (`contracts.BriefTemplate.reference`), and the skill references read
    (`reference_reads.Reference.path`). `spans_turns` is False for a
    subagent, where only its current turn counts, so its holds ask for a
    load or read in this turn; the sets are then empty."""

    loads: frozenset[str] = frozenset()
    references_read: frozenset[str] = frozenset()
    templates_read: frozenset[str] = frozenset()
    spans_turns: bool = False
    skill_references_read: frozenset[str] = frozenset()


class _Proof:
    """What the current turn shows, with what counts from earlier turns
    (`earlier`): loads, skip lines, reads, and user skips. `turn_loads` are
    the turn's own loads; `loads` add the earlier ones. `within` is what a
    hold adds after asking for a load or read: " in this turn" when earlier
    turns do not count, else "". `extra_text` is reply text the transcript
    may not hold yet, such as the reply a Stop is finishing."""

    def __init__(self, turn: Turn, overrides: dict, namespaces: tuple[str, ...],
                 extra_text: str = "", earlier: SinceCompaction = SinceCompaction()) -> None:
        self.turn = turn
        self.namespaces = namespaces
        self.extra_text = extra_text
        self.turn_loads = {goated_skill_name(raw, namespaces) for raw in turn.loads} - {None}
        self.loads = self.turn_loads | earlier.loads
        self.references_read = earlier.references_read | set(design_reads.reads_in(turn.calls))
        self.templates_read = earlier.templates_read | set(contracts.templates_read(turn.calls))
        self.skill_references_read = (earlier.skill_references_read
                                      | set(reference_reads.reads_in(turn.calls)))
        self.within = "" if earlier.spans_turns else " in this turn"
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

    def load_index(self, skill: str) -> int | None:
        """Where in the turn's calls `skill` first loaded: -1 when the prompt
        invoked it as `/<skill>` or it loaded in an earlier turn, None when it
        does not count as loaded."""

        if skill not in self.loads:
            return None
        for index, call in enumerate(self.turn.calls):
            if call.name == "Skill" and call.ok and goated_skill_name(
                skill_name(call.input.get("skill")), self.namespaces
            ) == skill:
                return index
        return -1

    def read_index(self, reference: str, after: int = -1) -> int | None:
        """Where the first finished Read of `reference` after call `after` is, if any."""

        return next((
            index for index, call in enumerate(self.turn.calls)
            if index > after and call.name == "Read" and call.ok
            and _ends_with_path(str(call.input.get("file_path") or ""), reference)
        ), None)


def is_action_tool(tool_name: str) -> bool:
    """True for a tool some action gate may hold (the hook matcher must cover these)."""

    return (
        tool_name in COMMAND_TOOLS or tool_name in SPAWN_BRIEF_FIELDS
        or tool_name in FILE_WRITE_TOOLS or bool(PR_TOOL_RE.match(tool_name))
        or bool(COMMIT_TOOL_RE.match(tool_name))
    )


class Closeout(NamedTuple):
    """What a commit's closeout hold reads besides the turn: `edit_references`,
    `design_ids`, `spawn_templates`, and `intensity`, as `check_closeout`
    takes them."""

    edit_references: dict[str, list[str]]
    design_ids: Callable[[], dict[str, tuple[str, ...]]] | None = None
    spawn_templates: dict[str, list[str]] | None = None
    intensity: str | None = None


def check_action(tool_name: str, tool_input: dict, turn: Turn, overrides: dict,
                 namespaces: tuple[str, ...] = (), project: Project | None = None,
                 subagents: Callable[[], dict] | None = None,
                 earlier: SinceCompaction = SinceCompaction(),
                 closeout: Closeout | None = None,
                 references: Callable[[], tuple] | None = None) -> Hold | None:
    """Return the action hold for this call, if any; the call's own entry is not yet proof.

    `project` says which files are the project's (see `find_project`): only files
    inside it meet the design and security gates, and only changes to them
    are the turn's changes a change read must follow; git measures a pull
    request in its `cwd`. `subagents` returns the turns
    of each subagent this turn spawned, as `check_closeout` takes them; it is
    called only when a commit or pull request needs its change read, since
    reading their transcripts takes time. `earlier` is what counts from
    earlier turns until the next compaction. With `closeout`, a commit whose
    own hold is met is held while the turn has unmet closeout items (Ticket 059);
    without it, as for a subagent, which has no closeout, it is not.
    `references` returns the registry's declared references
    (`reference_reads.load`), called only for an edit of a project file;
    without it, as for a subagent, the `reference-reads` gate holds nothing.
    """

    proof = _Proof(turn, overrides, namespaces, earlier=earlier)
    spawned = functools.cache(subagents) if subagents else dict
    changes = lambda: _Changes(turn, spawned(), project)
    at_commit = lambda by_tool=False: closeout and check_closeout(
        turn, overrides, namespaces, subagents=spawned(), project=project,
        edit_references=closeout.edit_references, design_ids=closeout.design_ids,
        at_commit=True, by_tool=by_tool, earlier=earlier,
        spawn_templates=closeout.spawn_templates, intensity=closeout.intensity,
    )
    cwd = project.cwd if project else None  # Where git measures a pull request's size.
    if tool_name in COMMAND_TOOLS:
        command = shell.analyze(str(tool_input.get("command") or ""), tool_name)
        hold = _conflict_hold(command.write_targets, tool_input, proof) if command.writes else None
        if hold is None and command.commit:
            hold = _commit_hold(command.commit_message, proof, changes) or at_commit()
        if hold is None and command.opens_pr:
            hold = _pr_hold(proof, changes) or _pr_review_hold(
                lambda: changed_lines(cwd, command.pr_base, command.pr_head), proof, changes)
        for target in command.write_targets:
            if _in_project(target, project, target not in command.unplaced_targets):
                hold = hold or _security_hold(_norm(target), proof)
        if command.non_check_writes:
            hold = hold or _repeated_failure_hold(proof)
        return hold
    if PR_TOOL_RE.match(tool_name):
        return _pr_hold(proof, changes, by_tool=True) or _pr_review_hold(
            lambda: _tool_changed_lines(tool_input, cwd), proof, changes, by_tool=True)
    if COMMIT_TOOL_RE.match(tool_name):
        message = tool_input.get("message")
        return _commit_hold(message if isinstance(message, str) else None, proof, changes,
                            by_tool=True) or at_commit(by_tool=True)
    if tool_name in SPAWN_BRIEF_FIELDS:
        brief = str(tool_input.get(SPAWN_BRIEF_FIELDS[tool_name]) or "")
        if not brief.strip() or spawns_a_reader(tool_name, tool_input):
            return None  # A read-only subagent's search brief needs no handoff template.
        return _spawn_hold(brief, proof)
    if tool_name in FILE_WRITE_TOOLS:
        path = _norm(str(tool_input.get(FILE_WRITE_TOOLS[tool_name]) or ""))
        # A conflict is open, and a check keeps failing, wherever the file lives
        # (a worktree may sit outside the project folder), as the shell branch
        # above holds every write target for them.
        hold = _conflict_hold([path], tool_input, proof)
        if hold is None and _in_project(path, project):
            # A scratch file elsewhere is not the project's design or security.
            hold = (_security_hold(path, proof) or _design_hold(path, tool_input, proof, project)
                    or _reference_reads_hold(path, tool_input, proof, project, references))
        return hold or _repeated_failure_hold(proof)
    return None


def _commit_hold(message: str | None, proof: _Proof, changes: Callable[[], "_Changes"],
                 by_tool: bool = False) -> Hold | None:
    """Hold a commit until `commit-message` loads, its inline message (`message`,
    if known) keeps the contract, and the change is read after the turn's last
    project change, before or after the load; `by_tool`: an MCP tool records
    it, not a git command."""

    supplied = proof.overrides.get("commit_message")
    if supplied and message is not None and (
        _subject(message) == _subject(supplied)
    ):
        return None  # The user typed this message (spec R8).
    if not proof.loaded(COMMIT_SKILL):
        return Hold(
            "commit", STRICT,
            f"Load the `{COMMIT_SKILL}` skill with the Skill tool{proof.within} and draft "
            "the message with it, then run the commit again. The whole command was "
            "held, so rerun any steps chained before it too. This hold is strict: a "
            "goated-skip line does not clear it. A commit message the user typed in "
            "their prompt stands it down when the commit uses that message.",
        )
    if COMMIT_SKILL in proof.user_skips:
        return None
    problems = contracts.commit_message_problems(message) if message is not None else []
    if problems:
        return Hold(
            "commit", STRICT,
            # No backticks: this hold asks for a fix, not a load, and backticks name a skill to load.
            f"The commit message breaks the {COMMIT_SKILL} contract: "
            + "; ".join(problems) + ". Fix the message and run the commit again.",
        )
    return _change_read_hold(
        "commit", COMMIT_SKILL, proof, changes(), by_tool,
        "committing it", "check that the message describes it and run the commit again",
    )


def _pr_hold(proof: _Proof, changes: Callable[[], "_Changes"],
             by_tool: bool = False) -> Hold | None:
    if PR_SKILL in proof.user_skips:
        return None
    if proof.loaded(PR_SKILL):
        return _change_read_hold(
            "pull-request", PR_SKILL, proof, changes(), by_tool, "opening the pull request",
            "check that the title and body describe it and open the pull request again",
        )
    return Hold(
        "pull-request", STRICT,
        f"Load the `{PR_SKILL}` skill with the Skill tool{proof.within} and draft the "
        "title and body with it, then open the pull request again. The whole command "
        "was held, so rerun any steps chained before it too. This hold is strict: a "
        "goated-skip line does not clear it.",
    )


def _pr_review_hold(size_of: Callable[[], int | None], proof: _Proof,
                    changes: Callable[[], "_Changes"], by_tool: bool = False) -> Hold | None:
    """Hold a pull request that changes `REVIEW_MIN_LINES` or more lines, as
    `size_of` measures it (None: unknown), until `standards-and-spec-review`
    loads and the change is read after it, or a skip line names it. Checked
    after the `pull-request` gate passes; `size_of` runs only when the turn's
    proof would not already clear it."""

    if proof.skipped(REVIEW_SKILL):
        return None
    hold = None
    if proof.loaded(REVIEW_SKILL):
        hold = _change_read_hold(
            "pr-review", REVIEW_SKILL, proof, changes(), by_tool, "opening the pull request",
            "review it and open the pull request again", review=True,
        )
        if hold is None:
            return None
    size = size_of()
    if size is None or size < REVIEW_MIN_LINES:
        return None
    return hold or Hold(
        "pr-review", JUSTIFIED_SKIP,
        f"This pull request changes {size} lines against its base, {REVIEW_MIN_LINES} or "
        f"more, so it is large enough to review before it lands. Load `{REVIEW_SKILL}` "
        f"with the Skill tool{proof.within} and review the change with it. If size is not "
        "what makes it worth reviewing, such as generated or vendored files, write "
        f"`goated-skip: {REVIEW_SKILL}: <reason>` on its own line instead. Then open the "
        "pull request again. The whole command was held, so rerun any steps chained "
        "before it too. " + unseen_line_advice("skip line", f"skip {REVIEW_SKILL}"),
    )


def _tool_changed_lines(tool_input: dict, cwd: str | None) -> int | None:
    """`changed_lines` for an MCP pull-request tool's input: its `base` or
    `target_branch`, its `head` or `source_branch`, and, for a GitHub-style
    tool, the `owner` and `repo` it is aimed at."""

    def text(*keys: str) -> str | None:
        value = next((tool_input[k] for k in keys if tool_input.get(k)), None)
        return value if isinstance(value, str) else None

    owner, repo = text("owner"), text("repo")
    return changed_lines(cwd, text("base", "target_branch"), text("head", "source_branch"),
                         f"{owner}/{repo}" if owner and repo else None)


class _WorkingTree:
    """The type of `WORKING_TREE`; it has no other value."""

    def __repr__(self) -> str:
        return "WORKING_TREE"


# A `changed_lines` head that is the working tree itself: the branch's
# commits, staged and unstaged changes, and untracked files git does not
# ignore. Not a string, so no branch name a tool supplies can ask for it.
WORKING_TREE = _WorkingTree()


def changed_lines(cwd: str | None, base: str | None, head: str | _WorkingTree | None = None,
                  repository: str | None = None) -> int | None:
    """Lines added plus deleted on `head` since it left `base`, as git in `cwd`
    reports them; None when that cannot be measured.

    `base` is the branch the pull request merges into, found as `origin/<base>`
    or the local branch; without one, the first of `DEFAULT_BASE_REFS` that
    exists. `head` is the branch it merges from, found as the local branch or
    `origin/<head>`; without one, the checked-out `HEAD`. A base or head that
    is in neither place, such as another fork's branch, is unknown.
    `repository` ("owner/repo") is the repository a tool aims at: unless it is
    the checkout's `origin`, this checkout says nothing about its size.

    With `head` as `WORKING_TREE`, the measure is the branch's work as it
    stands (spec R1): the working tree against where the checked-out branch
    left `base`, plus every line of each untracked file git does not ignore.
    A checkout on the base branch itself, or a detached one, has no branch
    work to compare, so it is unknown too.

    Two git calls, three with `repository`, five for the working tree, within
    `SIZE_TIMEOUT_SECONDS` in all. Every name reaches git inside a full ref
    name (`refs/...`), so none reads as an option, and external diff and
    text-conversion programs are switched off, so only git runs.
    """

    if not cwd:
        return None
    deadline = time.monotonic() + SIZE_TIMEOUT_SECONDS
    if repository is not None:
        url = _git(["config", "--get", "remote.origin.url"], cwd, deadline)
        if url is None or not _names_repository(url, repository):
            return None
    working_tree = head is WORKING_TREE
    base_refs = ((f"refs/remotes/origin/{base}", f"refs/heads/{base}") if base
                 else DEFAULT_BASE_REFS)
    head_refs = ((f"refs/heads/{head}", f"refs/remotes/origin/{head}")
                 if isinstance(head, str) and head else ())
    listed = _git(["for-each-ref", "--format=%(refname) %(symref)", *base_refs, *head_refs],
                  cwd, deadline)
    if listed is None:
        return None
    # A pattern also lists refs below it, so match exactly. `origin/HEAD` names
    # the branch it points at, which is the base branch's own name.
    targets = dict((line.split(" ", 1) + [""])[:2] for line in listed.splitlines())
    base_ref = next((ref for ref in base_refs if ref in targets), None)
    head_ref = next((ref for ref in head_refs if ref in targets), None) if head_refs else "HEAD"
    if base_ref is None or head_ref is None:
        return None
    if working_tree:
        # Where a base branch is both local and on `origin`, the branch left
        # whichever is closer to it: work merged locally and not yet pushed
        # leaves `origin/<base>` behind (spec R1).
        name = _branch_name(targets[base_ref] or base_ref)
        bases = dict.fromkeys(
            [base_ref] + [ref for ref in (f"refs/remotes/origin/{name}", f"refs/heads/{name}")
                          if ref in targets])
        return _branch_work_lines(cwd, list(bases), name, deadline)
    stat = _git(["diff", "--shortstat", "--no-ext-diff", "--no-textconv",
                 f"{base_ref}...{head_ref}", "--"], cwd, deadline)
    return None if stat is None else _shortstat_lines(stat)


def _branch_name(ref: str) -> str:
    """A local or `origin` branch's name, from its full ref name."""

    return ref.strip().removeprefix("refs/heads/").removeprefix("refs/remotes/origin/")


def _branch_work_lines(cwd: str, base_refs: list[str], base_branch: str,
                       deadline: float) -> int | None:
    """`changed_lines` with the working tree as its head, once the base is
    found: `base_refs` are the existing refs of the base branch, named
    `base_branch`, and the branch is measured from the fork point closest
    to it among them."""

    branch = _git(["rev-parse", "--symbolic-full-name", "HEAD"], cwd, deadline)
    if branch is None or not branch.startswith("refs/heads/"):
        return None  # Detached, or on a branch with no commit yet.
    if _branch_name(branch) == base_branch:
        return None  # On the base branch: nothing to compare it with.
    # With several bases, git gives the best common ancestor of HEAD and any of
    # them: the fork point no other one descends from, the closest to HEAD.
    fork = _git(["merge-base", "HEAD", *base_refs], cwd, deadline)
    if fork is None:
        return None
    stat = _git(["diff", "--shortstat", "--no-ext-diff", "--no-textconv", fork.strip(), "--"],
                cwd, deadline)
    # `:/` lists from the top of the checkout, with paths relative to `cwd`.
    untracked = _git(["ls-files", "--others", "--exclude-standard", "-z", "--", ":/"],
                     cwd, deadline)
    if stat is None or untracked is None:
        return None
    total = _shortstat_lines(stat)
    for path in filter(None, untracked.split("\0")):
        lines = _text_lines(os.path.join(cwd, path), deadline)
        if lines is None:
            return None
        total += lines
    return total


def _text_lines(path: str, deadline: float) -> int | None:
    """The lines in the file at `path`, as `git diff` would count them added:
    1 for a symbolic link, whose target is never read, and 0 for a binary
    file (one holding a NUL byte), anything else that is not a regular file,
    or one that cannot be read. None when `deadline` passes first; it is
    checked between reads, so a huge file cannot hold the hook past it."""

    lines, last = 0, b"\n"
    try:
        mode = os.lstat(path).st_mode
        if S_ISLNK(mode):
            return 1  # git records a link as one line: its target's path.
        if not S_ISREG(mode):
            return 0
        with open(path, "rb") as text:
            while chunk := text.read(UNTRACKED_READ_BYTES):
                if time.monotonic() > deadline:
                    return None
                if b"\0" in chunk:
                    return 0
                lines += chunk.count(b"\n")
                last = chunk[-1:]
    except OSError:
        return 0  # Gone since git listed it, or unreadable: it adds nothing to see.
    return lines + (last != b"\n")  # A last line with no newline still counts.


def _shortstat_lines(stat: str) -> int:
    """Lines added plus deleted, from `git diff --shortstat` output."""

    return sum(int(n) for n in re.findall(r"(\d+) (?:insertion|deletion)", stat))


def _git(args: list[str], cwd: str, deadline: float) -> str | None:
    """Run git with `args` in `cwd` and return its output; None when it fails,
    is missing, or runs past `deadline`. The C locale keeps git's words
    English, and undecodable bytes are replaced, never raised."""

    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return None
    try:
        result = subprocess.run(
            ["git", "-c", "core.fsmonitor=false", *args],
            cwd=cwd, capture_output=True, encoding="utf-8", errors="replace",
            timeout=remaining,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0", "LC_ALL": "C", "LANG": "C"},
        )
    except (OSError, subprocess.SubprocessError):
        return None  # No git, no such folder, or too slow: the size is unknown.
    return result.stdout if result.returncode == 0 else None


def _names_repository(url: str, repository: str) -> bool:
    """True when the remote `url` (HTTPS or SSH form) is `repository`, "owner/repo"."""

    path = url.strip().lower().rstrip("/").removesuffix(".git")
    wanted = repository.lower()
    return path.endswith("/" + wanted) or path.endswith(":" + wanted)


def _change_read_hold(gate: str, skill: str, proof: _Proof, changes: "_Changes", by_tool: bool,
                      doing: str, then: str, review: bool = False) -> Hold | None:
    """Hold a commit or pull request, whose skill has loaded, until a change read
    follows the turn's last change to any project file, before or after the
    load (Ticket 059). `review`: the hold asks for a review done with `skill`,
    so its read must follow the load too, and it is justified-skip, so a skip
    line naming `skill` clears it.

    An MCP tool (`by_tool`) passes when the turn changed no project file: it
    carries the change in its own input, and outside a git checkout no diff
    can run and no changed file exists to Read, so the strict hold would have
    no way out.
    """

    if by_tool and changes.last_change < 0:
        return None
    since = max(proof.load_index(skill), changes.last_change) if review else changes.last_change
    if changes.read_after(since):
        return None
    how = CHANGE_READ if changes.paths else DIFF_ONLY_READ
    loaded = f", after loading the {skill} skill" if review else ""
    after = (" and" if review else ",") + " after your last change" if changes.last_change >= 0 else ""
    # Not backticked: the skill-usage mod would read a backticked skip line as an ask
    # that only a skip line answers, and count a read that clears this hold as ignored.
    tail = (f"Or write a skip line, goated-skip: {skill}: <reason>, on its own line. "
            + unseen_line_advice("skip line", f"skip {skill}") if review
            else "This hold is strict: a goated-skip line does not clear it.")
    return Hold(
        gate, JUSTIFIED_SKIP if review else STRICT,
        f"Read the change before {doing}{loaded}{after}: "
        f"{how}. Then {then}. The whole command was held, so rerun "
        "any steps chained before it too. A read chained in the same command, or made "
        f"in parallel with this call, has not finished, so it does not count. {tail}",
    )


def _spawn_hold(brief: str, proof: _Proof) -> Hold | None:
    if proof.user_skips & {t.skill for t in contracts.BRIEF_TEMPLATES}:
        return None  # The user typed `skip handoff` or `skip subagent-driven-development`.
    loaded = [t for t in contracts.BRIEF_TEMPLATES if t.skill in proof.loads]
    if not loaded:
        return Hold(
            "spawn", STRICT,
            f"Before starting another agent or session with a brief, load `{HANDOFF_SKILL}` "
            f"with the Skill tool{proof.within}, read its `references/spawn-brief.md`, and "
            "write the brief from that template (Goal, Scope, Done Means, and its skills line "
            "at least). For a "
            "scoped implementation or review task, load `subagent-driven-development` "
            "and fill its implementer or reviewer prompt instead. Nothing was started. "
            "This hold is strict: a goated-skip line does not clear it.",
        )
    read = _templates_read(proof)
    if not read:
        files = " or ".join(f"`{t.reference}`" for t in loaded)
        return Hold(
            "spawn", STRICT,
            f"Read {files} with the Read tool{proof.within} and write the brief from it. "
            "The template is the point of this step, so the skill load alone does not "
            "clear the hold. Nothing was started.",
        )
    problems = []
    if not _matched_templates(brief, proof):
        gaps = "; ".join(
            f"`{t.reference}` needs " + ", ".join(f"`## {h}`" for h in t.missing_headings(brief))
            for t in read
        )
        problems.append(f"The brief lacks headings its template keeps: {gaps}. Add them as "
                        "Markdown headings.")
    line_problem = contracts.skills_line_problem(brief)
    if line_problem:
        # The line's form is defined in handoff's references/spawn-brief.md (Ticket 071).
        problems.append(
            f"The brief {line_problem}. On a line of its own or as a list item, outside "
            "code blocks and not in bold, name the skills the new agent should read "
            "before it starts, by their installed names, bare or with a plugin namespace: "
            "`goated-skills: <skill>, <skill>`, or `goated-skills: none: <reason>` when "
            "none applies. The agent loads each with its skill tool, or reads its SKILL.md "
            "file when it has none."
        )
    if not problems:
        return None
    return Hold("spawn", STRICT, " ".join(problems) + " Then start it again. Nothing was started.")


def _templates_read(proof: _Proof) -> list[contracts.BriefTemplate]:
    """The brief templates whose skill counts as loaded and which were read."""

    return [t for t in contracts.BRIEF_TEMPLATES
            if t.skill in proof.loads and t.reference in proof.templates_read]


def _matched_templates(brief: str, proof: _Proof) -> list[contracts.BriefTemplate]:
    """The templates `brief` follows: loaded, read, and with every heading they keep."""

    return [t for t in _templates_read(proof) if not t.missing_headings(brief)]


def brief_templates(tool_name: str, tool_input: dict, turn: Turn, overrides: dict,
                    namespaces: tuple[str, ...] = (),
                    earlier: SinceCompaction = SinceCompaction()) -> list[str]:
    """The `reference` of each brief template a spawn's brief follows, as the
    `spawn` gate judges it, for the closeout's Review item; [] for a call
    that is no spawn. A brief that follows
    `contracts.REVIEWER_TEMPLATE` starts a reviewer subagent. Call it for a
    call `check_action` let through."""

    if tool_name not in SPAWN_BRIEF_FIELDS:
        return []
    brief = str(tool_input.get(SPAWN_BRIEF_FIELDS[tool_name]) or "")
    proof = _Proof(turn, overrides, namespaces, earlier=earlier)
    return [t.reference for t in _matched_templates(brief, proof)]


def _security_hold(path: str, proof: _Proof) -> Hold | None:
    category = security_category(path)
    if category is None or proof.loaded_or_skipped(SECURITY_SKILL):
        return None
    return Hold(
        "security", JUSTIFIED_SKIP,
        f"\"{path.rsplit('/', 1)[-1]}\" is a security-sensitive surface ({category}). Load "
        f"`{SECURITY_SKILL}` with the Skill tool{proof.within} and review this change with "
        "it. If the change crosses no trust boundary and touches no auth, secrets, "
        "persistence, execution, dependency, or deployment behaviour, write "
        f"`goated-skip: {SECURITY_SKILL}: <reason>` on its own line instead. This edit "
        "was not applied. " + unseen_line_advice("skip line", f"skip {SECURITY_SKILL}"),
    )


def _conflict_hold(paths: list[str], tool_input: dict, proof: _Proof) -> Hold | None:
    """Hold a write to `paths` while a conflict is open in the turn (spec G1):
    the write edits conflict markers, writes a file the turn read with markers
    in it, or follows a git merge, rebase, cherry-pick, revert, or pull whose
    result reported a conflict that no later abort, continue, or commit ended.
    Only the turn is read, never the repository on disk, so a conflict opened
    in an earlier turn is seen only through its markers."""

    if proof.loaded_or_skipped(CONFLICT_SKILL):
        return None
    edits = tool_input.get("edits")
    olds = [tool_input.get("old_string")] + (
        [e.get("old_string") for e in edits if isinstance(e, dict)]
        if isinstance(edits, list) else []
    )
    edits_markers = any(isinstance(old, str) and CONFLICT_MARKER_RE.search(old) for old in olds)
    git_open, marked_files = _open_conflict(proof.turn)
    writes_marked = any(_same_file(marked, path) for marked in marked_files for path in paths)
    if not (edits_markers or git_open or writes_marked):
        return None
    return Hold(
        "conflict-resolution", JUSTIFIED_SKIP,
        "A merge conflict is open in this turn. Load "
        f"`{CONFLICT_SKILL}` with the Skill tool{proof.within} and resolve it from the "
        "intent behind both sides. If this write does not resolve the conflict, write "
        f"`goated-skip: {CONFLICT_SKILL}: <reason>` on its own line instead. This write "
        "was not applied. " + unseen_line_advice("skip line", f"skip {CONFLICT_SKILL}"),
    )


def _open_conflict(turn: Turn) -> tuple[bool, list[str]]:
    """Read the turn's calls in order and return whether a git conflict is still
    open, and the files a Read showed with markers since the last conflict ended.

    A git merge, rebase, cherry-pick, revert, or pull whose result reports a
    conflict opens one (a conflicting stash pop or apply prints none of git's
    stop lines). A finished abort, quit, continue, or skip of one of them, or
    a finished commit, ends it, unless that same call reports a new conflict.
    """

    git_open, marked_files = False, []
    for call in turn.calls:
        if call.name == "Read":
            if call.ok and CONFLICT_MARKER_RE.search(call.output):
                marked_files.append(str(call.input.get("file_path") or ""))
            continue
        if call.name not in COMMAND_TOOLS:
            continue
        command = str(call.input.get("command") or "")
        if GIT_CONFLICT_COMMAND_RE.search(command) and GIT_CONFLICT_RESULT_RE.search(call.output):
            git_open = True
        elif call.ok and (GIT_CONFLICT_END_RE.search(command) or shell.analyze(command).commit):
            git_open, marked_files = False, []
    return git_open, marked_files


def _design_hold(path: str, tool_input: dict, proof: _Proof, project: Project | None) -> Hold | None:
    """Hold a project file write until its design is done (spec R5).

    The `design` gate holds a turn's first substantial non-test code edit until
    `software-design-principles` loads, a design-reads line is in the turn,
    and every reference the edit requires is read. The `design-reads` gate
    holds any later edit the design-reads rules apply to, once the skill is
    loaded, until the references it requires are read. `design_reads` says
    which those are. A load or a read counts until the next compaction, a
    design-reads line only in its turn; a skip line or the user's skip of the
    skill clears both gates.
    """

    code, test = is_code(path), is_test(path, project)
    if not design_reads.applies(path, is_code=code, is_test=test) or proof.skipped(DESIGN_SKILL):
        return None
    # A test file is never substantial: in TDD the test comes first, and the
    # design happens in the code after it (Ticket 057).
    substantial = code and not test and not _small_edit(tool_input)
    loaded = proof.loaded(DESIGN_SKILL)
    if not loaded and not substantial:
        return None
    earlier = _project_code_writes(proof.turn, project)
    declared = declared_files(proof.turn.design_reads)
    required = _edit_required(path, tool_input, proof, project, earlier)
    unread = {name: why for name, why in required.items() if name not in proof.references_read}
    needs_line = substantial and not proof.turn.design_reads
    if loaded and not needs_line and not unread:
        return None
    unknown = design_reads.unknown(declared)
    misnamed = (
        " Your design-reads lines name files that are not design references, so they require "
        "nothing: " + ", ".join(f'"{name}"' for name in unknown) + "."
    ) if unknown else ""
    first = substantial and not any(
        not small for p, small in earlier if not is_test(p, project)
    )
    if loaded and not needs_line and not first:
        return Hold(
            "design-reads", JUSTIFIED_SKIP,
            f"This edit of \"{path.rsplit('/', 1)[-1]}\" needs design references not yet read "
            "since the last compaction. Read each with the Read tool before the edit, and "
            f"apply it: {_reference_list(unread)}.{misnamed} If the edit has no design in it, "
            f"write `goated-skip: {DESIGN_SKILL}: <reason>` on its own line instead. This edit "
            "was not applied. " + unseen_line_advice("skip line", f"skip {DESIGN_SKILL}"),
        )
    steps = [] if loaded else [
        f"load `{DESIGN_SKILL}` with the Skill tool{proof.within} and apply its 'Before "
        "changing code' rules"
    ]
    if needs_line:
        malformed = "; ".join(f'"{line}"' for line in proof.turn.malformed_design_reads)
        steps.append(
            "write the skill's design-reads line in this turn, on its own line, naming the "
            "references whose "
            "conditions hold, as `goated-design-reads: <file>, <file>`, or "
            "`goated-design-reads: none: <reason>` when none does"
            + (f" (these lines in this turn do not match the grammar: {malformed})" if malformed else "")
        )
    if unread:
        steps.append(f"read with the Read tool each reference it requires: {_reference_list(unread)}")
    return Hold(
        "design", JUSTIFIED_SKIP,
        f"This is a substantial code change. Before it, {'; '.join(steps)}."
        f"{misnamed} If the edit is mechanical, with no design in it, write "
        f"`goated-skip: {DESIGN_SKILL}: <reason>` on its own line instead. This edit was not "
        "applied. " + unseen_line_advice("design-reads or skip line", f"skip {DESIGN_SKILL}"),
    )


def _reference_reads_hold(path: str, tool_input: dict, proof: _Proof, project: Project | None,
                          references: Callable[[], tuple] | None) -> Hold | None:
    """Hold a project file edit until the skill references its signals select
    are read (registry reference reads spec, R5).

    Only references of a skill that counts as loaded and has no skip line or
    typed skip this turn are judged, and only by the signal kinds judged on
    one edit (`reference_reads.selected`). A reference counts as read after a
    finished Read of it since the last compaction. With no `references`, or a
    registry that declares none, nothing is held.
    """

    declared = [r for r in references() if proof.loaded(r.skill) and not proof.skipped(r.skill)] \
        if references else []
    if not declared:
        return None
    edit = reference_reads.Edit(
        is_code=is_code(path), is_test=is_test(path, project),
        added_code=design_reads.added_code(path, tool_input, project.cwd if project else None),
    )
    unread = [(r, why) for r, why in reference_reads.selected(declared, edit)
              if r.path not in proof.skill_references_read]
    if not unread:
        return None
    skills = list(dict.fromkeys(r.skill for r, _ in unread))
    listing = ", ".join(f"`{r.path}` ({why})" for r, why in unread)
    skip_lines = " or ".join(f"`goated-skip: {skill}: <reason>`" for skill in skills)
    way_out = f"skip {skills[0]}" if len(skills) == 1 else "skip <skill>"
    return Hold(
        "reference-reads", JUSTIFIED_SKIP,
        f"This edit of \"{path.rsplit('/', 1)[-1]}\" needs skill references not yet read since "
        "the last compaction; the GOATED registry declares when each is required. Read each "
        f"with the Read tool before the edit, and apply it: {listing}. If one does not apply "
        f"to this edit, write {skip_lines} on its own line instead, naming its skill. This edit "
        "was not applied. " + unseen_line_advice("skip line", way_out),
    )


def design_references(tool_name: str, tool_input: dict, turn: Turn, overrides: dict,
                      namespaces: tuple[str, ...] = (),
                      project: Project | None = None,
                      earlier: SinceCompaction = SinceCompaction()) -> list[str]:
    """The design references an edit requires, as the design gates judge it,
    for the closeout's citation item: [] unless `software-design-principles`
    is loaded and not skipped and the design-reads rules apply to the edited
    project file. Call it for a call `check_action` let through."""

    if tool_name not in FILE_WRITE_TOOLS:
        return []
    proof = _Proof(turn, overrides, namespaces, earlier=earlier)
    path = _norm(str(tool_input.get(FILE_WRITE_TOOLS[tool_name]) or ""))
    applies = design_reads.applies(path, is_code=is_code(path), is_test=is_test(path, project))
    judged = applies and _in_project(path, project) and proof.loaded(DESIGN_SKILL)
    if not judged or proof.skipped(DESIGN_SKILL):
        return []
    earlier = _project_code_writes(turn, project)
    return list(_edit_required(path, tool_input, proof, project, earlier))


def _edit_required(path: str, tool_input: dict, proof: _Proof, project: Project | None,
                   earlier: list[tuple[str, int]]) -> dict[str, str]:
    """The references an edit of `path` requires, each with why (see
    `design_reads.required`); `earlier` is `_project_code_writes` of the turn."""

    return design_reads.required(
        path, tool_input, is_code=is_code(path), is_test=is_test(path, project),
        small=_small_edit(tool_input), written_before=any(p == path for p, _ in earlier),
        other_code_files=len({p for p, _ in earlier if p != path and not is_test(p, project)}),
        declared=declared_files(proof.turn.design_reads), cwd=project.cwd if project else None,
    )


def _reference_list(references: dict[str, str]) -> str:
    """The references as the holds name them, in the given order. Each path is
    backticked like the closeout's red-flags path; the skill-usage mod reads
    only a bare backticked name as a skill."""

    return ", ".join(f"`{design_reads.SKILL_REFERENCES}{name}` ({why})" for name, why in references.items())


def _project_code_writes(turn: Turn, project: Project | None) -> list[tuple[str, bool]]:
    """Each finished edit tool call on a project code file in the turn: its path
    and whether it is a small edit (`_small_edit`)."""

    writes = []
    for call in turn.calls:
        if call.ok and call.name in FILE_WRITE_TOOLS:
            path = _norm(str(call.input.get(FILE_WRITE_TOOLS[call.name]) or ""))
            if is_code(path) and _in_project(path, project):
                writes.append((path, _small_edit(call.input)))
    return writes


def _repeated_failure_hold(proof: _Proof) -> Hold | None:
    """Hold a write once one check command has failed twice in a row in the turn.

    "The same check" is the same command text, whitespace aside (spec G2),
    without a trailing pipe into output filters (`| tail -20`): a narrowed
    rerun, such as one test file of a failing suite, is another command. A
    pass of that check resets its count; other commands between runs do not.
    Only runs count: a call held, refused, or interrupted never ran. A run
    whose only failures are test modules missing a module (`LOAD_ERROR_SIGNS`)
    neither adds to the count nor resets it, failed or not, since a pipe can
    cut the failure signs from its output.
    """

    if proof.loaded_or_skipped(DIAGNOSE_SKILL):
        return None
    in_a_row: dict[str, int] = {}
    is_check: dict[str, bool] = {}
    for call in proof.turn.calls:
        if call.name not in COMMAND_TOOLS or call.held or NOT_RUN_RE.match(call.output):
            continue
        command = str(call.input.get("command") or "")
        key, piped = _check_key(command)
        load_errors = _load_errors(call.output)
        if load_errors == "missing-module":
            continue
        # A pipe's exit code is its last filter's, so a piped run fails by what it prints.
        failed = (
            bool(load_errors or FAILURE_SIGNS_RE.search(call.output)) if piped else not call.ok
        )
        if not failed and key not in in_a_row:
            continue  # A pass of a command that never failed changes nothing.
        if key not in is_check:
            is_check[key] = shell.analyze(command).is_check
        if is_check[key]:
            in_a_row[key] = in_a_row.get(key, 0) + 1 if failed else 0
    repeated = next((k for k, n in in_a_row.items() if n >= REPEATED_FAILURES), None)
    if repeated is None:
        return None
    shown = repeated if len(repeated) <= 80 else repeated[:77] + "..."
    return Hold(
        "repeated-failure", JUSTIFIED_SKIP,
        # The command is quoted, not backticked: backticks name a skill to load.
        f"The check \"{shown.replace('`', chr(39))}\" has failed {REPEATED_FAILURES} times in "
        f"a row in this turn. Load `{DIAGNOSE_SKILL}` with the Skill tool{proof.within} and "
        "find the root cause before changing more. If the cause is already known, write "
        f"`goated-skip: {DIAGNOSE_SKILL}: <reason>` on its own line instead. This write was "
        "not applied. Rerunning the check is not held, and a pass of it resets the count. "
        + unseen_line_advice("skip line", f"skip {DIAGNOSE_SKILL}"),
    )


def _load_errors(output: str) -> str | None:
    """What a run's output says about test modules that failed to load.

    "missing-module" when it shows at least one, every one it shows was
    caused by a missing module or name, and no test that ran failed; "other"
    when it shows one for any other reason, or beside a real failure; None
    when it shows none. Output cut before a cause reads as "other".
    """

    found, lines = False, output.splitlines()
    for signs in LOAD_ERROR_SIGNS:
        starts = [i for i, line in enumerate(lines) if signs.start.match(line)]
        if not starts:
            continue
        found = True
        if signs.real_failure.search(output):
            return "other"
        for start in starts:
            end = next((i for i in range(start + 1, len(lines)) if signs.end.match(lines[i])),
                       len(lines))
            causes = list(LOAD_ERROR_CAUSE_RE.finditer("\n".join(lines[start + 1:end])))
            last = causes[-1] if causes else None
            if last is None or not (last["missing"] or last["exception"] in MISSING_MODULE_EXCEPTIONS):
                return "other"
    return "missing-module" if found else None


def _check_key(command: str) -> tuple[str, bool]:
    """A check command's identity, whitespace aside and without a trailing pipe
    into output filters, and whether such a pipe was removed."""

    key = " ".join(command.split())
    bare = key
    while (shorter := PIPE_TAIL_RE.sub("", bare)) != bare:
        bare = shorter
    piped = bare != key
    return (STDERR_MERGE_RE.sub("", bare) if piped else bare), piped


# Closeout ---------------------------------------------------------------------

def check_closeout(turn: Turn, overrides: dict, namespaces: tuple[str, ...] = (),
                   final_text: str = "", subagents: dict | None = None,
                   project: Project | None = None,
                   edit_references: dict[str, list[str]] | None = None,
                   design_ids: Callable[[], dict[str, tuple[str, ...]]] | None = None,
                   at_commit: bool = False, by_tool: bool = False,
                   earlier: SinceCompaction = SinceCompaction(),
                   spawn_templates: dict[str, list[str]] | None = None,
                   intensity: str | None = None) -> Hold | None:
    """Return the closeout hold for a turn about to end, if any; `at_commit`:
    for a commit the turn is about to make, which must meet it first, made by
    an MCP commit tool when `by_tool`, which has no command to rerun and no
    field that carries a citation.

    A turn that changed code needs, after its last code change, a check
    command (proof), in a later call or later in the same shell command. It
    also needs `doc-sync` when non-test code changed, `handoff` when the
    last check after the change failed (work left unfinished), and a read
    of the design red flags after the change, with a citation of a section of
    each design reference the turn's edits required, when `_designing` says
    the Design items apply. A turn that changed a security-sensitive file,
    code or not, while `code-security-review` counts as loaded, needs a
    security review. A load counts until the next compaction (`earlier`).
    The doc-sync, design, and security items each also need a change read: doc-sync's after the last code change, the
    design item's after its red-flags read, which follows the last code change
    that is not comment-only, and security's after its load and the last
    sensitive change. A turn
    that installed a package it names, or wrote an env or settings file, needs
    `setup-scribe` loaded at any point in the turn (Setup). Each item accepts
    a skip line; `final_text` is the reply being finished, which
    may not be in the transcript yet.

    `subagents` maps the agent id of each subagent this turn spawned to its
    turns. Their code changes count as made at the spawn; a subagent that ran
    a check after its own last change has already proved them. Only files
    inside `project` count (see `find_project`); a scratch file elsewhere does not.
    `edit_references` maps the tool_use_id of each edit the design gates
    judged in this turn to the references it required (`design_references`);
    the finished ones among them are the turn's required set. A subagent's
    edits are not in it, so they need no citation. `design_ids` returns each
    reference's section ids from the installed skill
    (`design_reads.section_ids`); it is called only when citations are
    checked, and a reference it leaves out needs none.

    A turn that changed code on a branch whose work against its base is
    `REVIEW_MIN_LINES` or more (`changed_lines` with `WORKING_TREE`, asked
    only when the item is not already met) needs a review (spec R1);
    `spawn_templates` maps the tool_use_id of each spawn the `spawn` gate let
    through in this turn to the templates its brief followed
    (`brief_templates`), which names its reviewer subagents. A turn that
    changed code or a sensitive file needs `verification-before-completion`
    (spec R3) when `intensity`, the task's route intensity, is `full`, a
    subagent changed code, a sensitive file changed, or the branch is large.
    """

    changes = _Changes(turn, subagents or {}, project)
    proof = _Proof(turn, overrides, namespaces, final_text, earlier)
    branch_size = functools.cache(
        lambda: changed_lines(project.cwd if project else None, None, WORKING_TREE))
    items = (
        _code_items(changes, proof, edit_references or {}, design_ids, at_commit, by_tool)
        + _review_item(changes, proof, spawn_templates or {}, branch_size)
        if changes.code else []
    )
    items += _verification_item(changes, proof, intensity, branch_size)
    sensitive = changes.sensitive
    if sensitive and SECURITY_SKILL in proof.loads and not proof.skipped(SECURITY_SKILL):
        last_sensitive = sensitive[-1][0]
        if not changes.read_after(max(proof.load_index(SECURITY_SKILL), last_sensitive)):
            categories = ", ".join(dict.fromkeys(category for _, category in sensitive))
            items.append(
                f"- Security: a security-sensitive file changed ({categories}). After loading "
                f"the {SECURITY_SKILL} skill and after the last sensitive change, read the "
                f"change itself and review it: {CHANGE_READ}. Or, if it crosses no trust "
                f"boundary, write `goated-skip: {SECURITY_SKILL}: <reason>`."
            )
    setup_item = _setup_item(turn, subagents or {}, proof, project)
    if setup_item:
        items.append(setup_item)
    if not items:
        return None
    what = (
        "changed setup" if items == [setup_item]
        else "changed code" if changes.code else "changed a security-sensitive file"
    )
    when = "committing in" if at_commit else "finishing"
    rerun = (
        "\nThe whole command was held, so rerun any steps chained before it too. A check "
        "chained before the commit in the same command has not run yet, so it does not count."
    ) if at_commit and not by_tool else ""
    return Hold(
        "closeout", JUSTIFIED_SKIP,
        f"Before {when} this turn, which {what}:\n" + "\n".join(items)
        + "\nA skip line must name the skill and give a reason of three or more words." + rerun,
    )


def _code_items(changes: "_Changes", proof: _Proof, edit_references: dict[str, list[str]],
                design_ids: Callable[[], dict[str, tuple[str, ...]]] | None,
                at_commit: bool, by_tool: bool) -> list[str]:
    """The closeout items a code change needs: proof, a handoff for a failed
    check, doc-sync, the design red flags, and the design citations, each with
    what is missing; `at_commit` and `by_tool`, as `check_closeout` takes
    them, say where a citation can still be written."""

    code = changes.code
    last = code[-1].index
    unproven = [c.index for c in code if not c.proven]
    items = []
    checks = _checks(proof.turn.calls[max(unproven, default=last) + 1 :])
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
    non_test = any(
        not is_test(path, changes.project) for change in code for path in change.code_paths
    )
    if non_test and not proof.skipped(DOC_SYNC_SKILL):
        loaded = proof.load_index(DOC_SYNC_SKILL)
        if loaded is None:
            items.append(
                f"- Docs: code changed. Load `{DOC_SYNC_SKILL}`, then read the change itself "
                f"and check whether durable docs now drift: {CHANGE_READ}. Or, if behavior "
                f"and interfaces did not change, write `goated-skip: {DOC_SYNC_SKILL}: <reason>`."
            )
        elif not changes.read_after(last):
            # The skill is loaded, so it is named only in the skip line: no load answers this.
            # A read before the load counts (Ticket 059): the load adds nothing to see.
            items.append(
                f"- Docs: after your last code change, read the change itself and check "
                f"whether durable docs now drift: {CHANGE_READ}. Or write "
                f"`goated-skip: {DOC_SYNC_SKILL}: <reason>`."
            )
    if _designing(proof, changes.project) and not proof.skipped(DESIGN_SKILL):
        # Fixing a comment the red-flags scan found needs no second scan (Ticket 059).
        designed = max((c.index for c in code if not c.comment_only), default=-1)
        flags = proof.read_index(RED_FLAGS_REFERENCE, after=designed)
        if flags is None:
            items.append(
                f"- Design: read `{RED_FLAGS_REFERENCE}` with the Read tool after your last "
                f"code change (an edit of comments only aside), then read the change itself "
                f"and scan it against them: {CHANGE_READ}. Then answer their closing "
                f"question: {RED_FLAGS_QUESTION} "
                f"Or write `goated-skip: {DESIGN_SKILL}: <reason>`."
            )
        elif not changes.read_after(flags):
            items.append(
                "- Design: after reading the red flags, read the change itself and scan it "
                f"against them, not your memory of it: {CHANGE_READ}. Then answer their "
                f"closing question: {RED_FLAGS_QUESTION} Or write "
                f"`goated-skip: {DESIGN_SKILL}: <reason>`."
            )
        uncited = _uncited_references(proof, edit_references, design_ids)
        if uncited:
            if not at_commit:
                where = f"Put the citations in your reply, or in {CITATION_FIELDS}."
            elif by_tool:
                where = (
                    f"This tool's fields carry no citation, so put them in {CITATION_FIELDS} "
                    f"made in an earlier message, then make the commit again. {UNSEEN_AT_COMMIT}"
                )
            else:
                where = (
                    "Put the citations in this commit call's description and make the call "
                    f"again, or in {CITATION_FIELDS} made in an earlier message. "
                    + UNSEEN_AT_COMMIT
                )
            items.append(
                "- Design: cite a section of each design reference this turn required, as "
                "file#id, with how it shaped the change or why it did not apply; the Section "
                f"Index in the skill's SKILL.md lists each file's ids. {where} Not yet "
                f"cited: {', '.join(uncited)}. Or write `goated-skip: {DESIGN_SKILL}: <reason>`."
            )
    return items


def _review_item(changes: "_Changes", proof: _Proof, spawn_templates: dict[str, list[str]],
                 branch_size: Callable[[], int | None]) -> list[str]:
    """The Review item for a turn that changed code (spec R1), or [] when the
    branch's work is not large, cannot be measured, or the item is met: by a
    reviewer subagent started after the last code change that has finished
    (one started in the background once its completion arrived in the turn),
    by the skill loaded and a change read after both the load and that
    change, or by a skip line. `branch_size` runs only when nothing else met it."""

    if proof.skipped(REVIEW_SKILL):
        return []
    last = changes.code[-1].index
    if any(
        index > last and call.ok and call.name in SPAWN_BRIEF_FIELDS
        and contracts.REVIEWER_TEMPLATE.reference in spawn_templates.get(call.tool_id, ())
        and (not call.launched_async or call.agent_id in proof.turn.finished_agents)
        for index, call in enumerate(proof.turn.calls)
    ):
        return []
    loaded = proof.load_index(REVIEW_SKILL)
    if loaded is not None and changes.read_after(max(loaded, last)):
        return []
    size = branch_size()
    if size is None or size < REVIEW_MIN_LINES:
        return []
    # The template is named by its path: the skill-usage mod reads a bare backticked
    # name as a skill the item asks for, and this item's skill is the review skill.
    reviewer = (
        "Or, after your last code change, start a reviewer subagent briefed from "
        f"`{contracts.REVIEWER_TEMPLATE.reference}`, the reviewer prompt; a brief from any "
        "other template is not a review."
    )
    size_text = (
        f"this branch's work is {size} lines against its base, {REVIEW_MIN_LINES} or more, "
        "counting committed, staged, unstaged, and untracked files that git does not ignore"
    )
    skip = (f"Or, if size is not what makes it worth reviewing, such as generated or vendored "
            f"files, write `goated-skip: {REVIEW_SKILL}: <reason>`.")
    if loaded is None:
        return [f"- Review: {size_text}. Load `{REVIEW_SKILL}`, then read the change itself "
                f"and review it: {CHANGE_READ}. {reviewer} {skip}"]
    # The skill is loaded, so it is named only in the skip line: no load answers this.
    return [f"- Review: {size_text}. After loading the {REVIEW_SKILL} skill and after your "
            f"last code change, read the change itself and review it: {CHANGE_READ}. "
            f"{reviewer} {skip}"]


def _verification_item(changes: "_Changes", proof: _Proof, intensity: str | None,
                       branch_size: Callable[[], int | None]) -> list[str]:
    """The Verification item (spec R3) for a turn that changed code or a
    sensitive file, or [] when no trigger holds or `verification-before-completion`
    counts as loaded or is skipped. Its skip line is the Proof item's too.
    `branch_size` runs only when no other trigger holds."""

    if not (changes.code or changes.sensitive) or proof.loaded_or_skipped(PROOF_SKILL):
        return []
    triggers = []
    if intensity == FULL_ROUTE:
        triggers.append(f"the task's route is {FULL_ROUTE}")
    if any(change.by_subagent for change in changes.code):
        triggers.append("a subagent changed code")
    if changes.sensitive:
        triggers.append("a security-sensitive file changed")
    if not triggers:
        size = branch_size()
        if size is None or size < REVIEW_MIN_LINES:
            return []
        triggers.append(f"this branch's work is {size} lines against its base")
    return [
        f"- Verification: {', and '.join(triggers)}, so verify the work before claiming it "
        f"is done. Load `{PROOF_SKILL}` and follow it. Or write "
        f"`goated-skip: {PROOF_SKILL}: <reason>`, which also answers the proof item."
    ]


def _designing(proof: _Proof, project: Project | None) -> bool:
    """Whether the turn's Design items apply: it loaded
    `software-design-principles`, or, with the skill loaded in an earlier
    turn, it made an edit the `design` gate triggers on (spec R3), so a later
    turn of small edits meets no Design item."""

    if DESIGN_SKILL in proof.turn_loads:
        return True
    return DESIGN_SKILL in proof.loads and any(
        not small and not is_test(path, project)
        for path, small in _project_code_writes(proof.turn, project)
    )


def _uncited_references(proof: _Proof, edit_references: dict[str, list[str]],
                        design_ids: Callable[[], dict[str, tuple[str, ...]]] | None) -> list[str]:
    """The references the turn's finished design edits required that it
    cites no section of, in the skill's order. A citation counts in reply
    text, the reply being finished included, and in the call fields that
    carry route and skip lines, held calls and the call being judged included."""

    required = {
        name for call in proof.turn.calls if call.ok
        for name in edit_references.get(call.tool_id, ())
    }
    if not required or design_ids is None:
        return []
    ids = design_ids()
    cited = design_reads.citations([*proof.turn.texts, *proof.turn.call_texts, proof.extra_text])
    return [
        name for name in design_reads.REFERENCES
        if name in required and name in ids
        and not any(f"{name}#{section}" in cited for section in ids[name])
    ]


def _setup_item(turn: Turn, subagents: dict, proof: _Proof, project: Project | None) -> str:
    """The Setup item, or "" when the turn changed no setup or met it.

    The turn's own `setup-scribe` load or skip line meets every setup change,
    its subagents' included; a subagent's own load or skip line meets only the
    changes that subagent made, as its own check proves its own code.
    """

    if proof.loaded_or_skipped(SETUP_SKILL):
        return ""
    calls = list(turn.calls) + [
        call for sub_turns in subagents.values() if not _setup_met(sub_turns, proof.namespaces)
        for sub_turn in sub_turns for call in sub_turn.calls
    ]
    setup = _setup_changes(calls, project)
    if not setup:
        return ""
    return (
        f"- Setup: this turn {setup}. Load `{SETUP_SKILL}` and record the setup so it "
        "can be repeated, or, if it leaves nothing to record, write "
        f"`goated-skip: {SETUP_SKILL}: <reason>`."
    )


def _setup_met(sub_turns: list[Turn], namespaces: tuple[str, ...]) -> bool:
    """True when a subagent loaded `setup-scribe` or wrote a skip line naming it."""

    return any(
        goated_skill_name(raw, namespaces) == SETUP_SKILL for t in sub_turns for raw in t.loads
    ) or any(skip["skill"] == SETUP_SKILL for t in sub_turns for skip in t.skips)


def _setup_changes(calls, project: Project | None) -> str:
    """What setup the finished `calls` changed, as a phrase for the Setup item
    ('installed a package', 'wrote ".env"'), or "".

    A package install counts wherever it ran; a setup file counts only inside
    `project` (see `_in_project`), so a scratch folder's settings do not.
    """

    installed, files = False, []
    for call in calls:
        if not call.ok:
            continue
        if call.name in FILE_WRITE_TOOLS:
            targets = [str(call.input.get(FILE_WRITE_TOOLS[call.name]) or "")]
            unplaced = []
        elif call.name in COMMAND_TOOLS:
            command = shell.analyze(str(call.input.get("command") or ""), call.name)
            installed = installed or command.installs_package
            targets, unplaced = command.write_targets, command.unplaced_targets
        else:
            continue
        for target in targets:
            name = _norm(target).rsplit("/", 1)[-1]
            if (SETUP_FILE_RE.search(_norm(target)) and name not in files
                    and _in_project(target, project, target not in unplaced)):
                files.append(name)
    # Names are quoted, not backticked: the skill-usage mod reads a backticked name as a skill.
    done = (["installed a package"] if installed else []) + (
        ["wrote " + ", ".join(f'"{name}"' for name in files)] if files else []
    )
    return " and ".join(done)


class _Change:
    """A finished call that changed files: where in the turn, which project
    files, which of them are code, whether it is already proved: by a check
    later in the same command, or by a subagent's own check, whether it
    is an edit that changed only comments and docstrings
    (`design_reads.comment_only`), and whether a spawned subagent made it."""

    __slots__ = ("index", "paths", "code_paths", "proven", "comment_only", "by_subagent")

    def __init__(self, index: int, paths: list[str], proven: bool = False,
                 comment_only: bool = False, by_subagent: bool = False) -> None:
        self.index = index
        self.paths = paths
        self.code_paths = [p for p in paths if _is_code_change(p)]
        self.proven = proven
        self.comment_only = comment_only
        self.by_subagent = by_subagent


class _Changes:
    """What one turn changed, and whether a later call read the change.

    `code` lists the changes to code, in order; `sensitive` lists each change
    to a security-sensitive file as (call index, category), in order;
    `last_change` is the call index of the last change to any project file,
    or -1; `paths` are the changed files a Read can name. Changes a spawned
    subagent made count as made at its spawn.
    """

    def __init__(self, turn: Turn, subagents: dict, project: Project | None) -> None:
        self.turn = turn
        self.project = project
        changes = list(_changes(turn, subagents, project))
        self.code = [c for c in changes if c.code_paths]
        self.sensitive = [
            (c.index, category) for c in changes for path in c.paths
            if (category := security_category(path)) is not None
        ]
        self.last_change = changes[-1].index if changes else -1
        self.paths = [p for c in changes for p in c.paths if p != UNNAMED_FILES]

    def read_after(self, after: int) -> bool:
        """True when a finished call after call `after` printed the diff or read
        a file the turn changed; the caller picks the change it must follow."""

        return any(
            index > after and call.ok and self._shows_change(call)
            for index, call in enumerate(self.turn.calls)
        )

    def _shows_change(self, call) -> bool:
        if call.name in COMMAND_TOOLS:
            return shell.analyze(str(call.input.get("command") or "")).prints_changes
        if call.name == "Read":
            read = str(call.input.get("file_path") or "")
            return any(_same_file(read, path) for path in self.paths)
        return False


# Stands for files a shell write changed without naming them (`git apply`).
UNNAMED_FILES = "<files the command does not name>"


def _is_code_change(path: str) -> bool:
    return path == UNNAMED_FILES or is_code(path)


def _changes(turn: Turn, subagents: dict, project: Project | None):
    """Yield a `_Change` for each finished call that changed project files, in order."""

    for index, call in enumerate(turn.calls):
        if call.ok and call.agent_id in subagents and call.name in SPAWN_BRIEF_FIELDS:
            calls = [c for sub_turn in subagents[call.agent_id] for c in sub_turn.calls]
            changed = [_changed_paths(c, project) for c in calls]
            if any(changed):
                code = [i for i, paths in enumerate(changed) if any(map(_is_code_change, paths))]
                proven = bool(code) and (
                    _proves_itself(calls[code[-1]], project)
                    or bool(_checks(calls[code[-1] + 1 :]))
                )
                yield _Change(index, [p for paths in changed for p in paths], proven,
                              by_subagent=True)
            continue
        paths = _changed_paths(call, project)
        if paths:
            yield _Change(index, paths, _proves_itself(call, project),
                          call.name in FILE_WRITE_TOOLS and design_reads.comment_only(
                              str(call.input.get(FILE_WRITE_TOOLS[call.name]) or ""), call.input))


def _changed_paths(call, project: Project | None) -> list[str]:
    """The project files one finished call changed; only real write targets count."""

    if not call.ok:
        return []
    if call.name in FILE_WRITE_TOOLS:
        targets = [str(call.input.get(FILE_WRITE_TOOLS[call.name]) or "")]
        unnamed, unplaced = False, []
    elif call.name in COMMAND_TOOLS:
        command = shell.analyze(str(call.input.get("command") or ""), call.name)
        targets, unnamed = command.write_targets, command.unknown_writes
        unplaced = command.unplaced_targets
    else:
        return []
    paths = [_norm(t) for t in targets if t and _in_project(t, project, t not in unplaced)]
    return paths + ([UNNAMED_FILES] if unnamed else [])


class Project(NamedTuple):
    """Where the project is: `roots`, the folders whose files count as the
    project's, in comparable form, and `cwd`, the session's folder as the
    hook input names it, which relative paths start from."""

    roots: tuple[str, ...]
    cwd: str


def find_project(cwd: str | None, project_dir: str | None = None) -> Project | None:
    """Return the project for a hook input's `cwd`, or None, when every file
    counts as inside: `cwd` is missing, or a folder below cannot be read for certain.

    A file is outside only when it is outside every root, so each candidate
    root is one: `project_dir` (Claude Code's `CLAUDE_PROJECT_DIR`), `cwd`,
    each in every reading it could have (see `_readings`), and the nearest
    folder at or above each that holds a `.git` entry. So a session that
    changed folder below its checkout still has the whole checkout.
    """

    if not cwd:
        return None
    roots: list[str] = []
    for folder in filter(None, (project_dir, cwd)):
        readings = _readings(folder, drives=())
        if readings is None:
            return None
        roots += readings
    roots += [top for top in map(_git_top, roots) if top]
    return Project(tuple(dict.fromkeys(roots)), cwd)


def _git_top(folder: str) -> str | None:
    while True:
        if os.path.exists(os.path.join(folder, ".git")):
            return folder
        parent = os.path.dirname(folder)
        if parent == folder:
            return None
        folder = parent


def _in_project(path: str, project: Project | None, placed: bool = True) -> bool:
    """True unless `path` is certainly outside the project: when in doubt, inside.

    With no project, every path is inside, and so is a relative path that is
    not `placed` (a shell wrote it from a folder the command left unknown).
    A relative path is taken from the session's folder. A path is outside
    only when none of its readings (see `_readings`) is a root or under one,
    even with symbolic links and junctions resolved in both; a path with no
    certain reading is inside. Touches the disk only to expand Windows 8.3
    short names and, for a path that looks outside, to resolve links.
    """

    if project is None or not placed:
        return True
    readings = _project_readings(path, project)
    if readings is None or _under_any(readings, project.roots):
        return True
    # A link may lead into the project from outside it, or out of a root.
    return _under_any(_resolved(readings), _resolved(project.roots))


def is_test(path: str, project: Project | None) -> bool:
    """Whether `path` is a test file, judged by its path inside the project
    (`design_reads.is_test_path`), so folders above the project do not count.
    A file whose place in the project is unknown is not a test file."""

    return design_reads.is_test_path(_path_in_project(path, project))


def _path_in_project(path: str, project: Project | None) -> str | None:
    """`path` below the outermost project root holding it, with `/` separators
    and in comparable form, or None: no project, no certain reading, or
    outside every root. A path reached only through a link is outside."""

    readings = _project_readings(path, project) if project else None
    inside = [
        full[len(root.rstrip(os.sep)) + 1:]
        for full in readings or () for root in project.roots
        if full.startswith(root.rstrip(os.sep) + os.sep)
    ]
    return max(inside, key=len).replace(os.sep, "/") if inside else None


def _project_readings(path: str, project: Project) -> list[str] | None:
    """`_readings` of `path`, a relative one taken from the session's folder."""

    rooted = path.startswith(("/", "\\", "~")) or (os.name == "nt" and DRIVE_RE.match(path))
    if not rooted:
        path = project.cwd.rstrip("/\\") + "/" + path
    return _readings(path, {os.path.splitdrive(root)[0] for root in project.roots})


def _under_any(paths, roots) -> bool:
    return any(
        full == root or full.startswith(root.rstrip(os.sep) + os.sep)
        for full in paths for root in roots
    )


def _resolved(paths) -> list[str]:
    return [os.path.normcase(os.path.realpath(path)) for path in paths]


DRIVE_RE = re.compile(r"^[A-Za-z]:")
ABSOLUTE_WINDOWS_RE = re.compile(r"^[A-Za-z]:[\\/]")
# Git Bash names a Windows drive as a one-letter top folder: `/c/Users` is `C:/Users`.
GIT_BASH_DRIVE_RE = re.compile(r"^/([A-Za-z])(?=/|$)")
# Characters a shell or Windows expands, so a path holding one names no file for certain.
EXPANDED_CHARS = frozenset("$`%*?")


def _readings(path: str, drives) -> list[str] | None:
    """Every file absolute `path` may name, in comparable form, or None when
    it cannot be read for certain.

    None for a path a shell expands (a variable, a glob), one under `~-`,
    `~+`, or another user's `~name`, and the Windows forms this does not
    normalize: device paths (`\\\\?\\`, `//?/`, `\\\\.\\`), network paths, a
    drive-relative `C:x`, and a name ending in a dot or space. A leading `~`
    is the user's home, read as both the profile folder and `HOME`.

    On Windows, a path rooted with no drive is None unless Git Bash reads it
    for certain (see `_git_bash_mounts`). Such a path may also be a folder on
    any of `drives` or the process's own drive, so those are readings too.
    """

    if any(ch in EXPANDED_CHARS for ch in path):
        return None
    if path.startswith("~"):
        if path != "~" and path[1] not in "/\\":
            return None
        # `HOME`, which Git Bash sets, may differ from the profile folder Python reads.
        home = os.environ.get("HOME") or ""
        if home.startswith("~"):
            return None
        homes = {os.path.expanduser("~"), home or os.path.expanduser("~")}
        each = [_readings(home + path[1:], drives) for home in sorted(homes)]
        return None if None in each else [r for readings in each for r in readings]
    slashed = path.replace("\\", "/")
    if slashed.startswith("//"):
        return None
    readings = [path]
    if os.name == "nt":
        if DRIVE_RE.match(slashed) and slashed[2:3] != "/":
            return None
        if any(part.endswith((".", " ")) and part not in (".", "..")
               for part in slashed.split("/")):
            return None  # Windows drops a name's trailing dots and spaces, not always alike.
        if slashed.startswith("/"):
            mounted = _git_bash_mounts(slashed)
            if not mounted:
                return None
            on_drives = set(drives) | {os.path.splitdrive(os.getcwd())[0]}
            readings = [d + slashed for d in sorted(on_drives)] + mounted
    return [_comparable(reading) for reading in readings]


def _git_bash_mounts(slashed: str) -> list[str]:
    """The Windows paths Git Bash may read rooted `slashed` as, or [] when
    that is not certain.

    `/c/x` is `C:/x` when drive C exists. `/tmp/x` is `x` in the user's temp
    folder, which Git Bash mounts on `/tmp`; Windows takes that folder from
    `TMP` or else `TEMP`, so each that is set is a reading, and both must
    be absolute Windows paths. Git Bash also mounts `/` on its install folder,
    and a user may add mounts, so no other rooted path is certain.
    """

    drive = GIT_BASH_DRIVE_RE.match(slashed)
    if drive:
        root = drive.group(1).upper() + ":"
        return [root + (slashed[2:] or "/")] if os.path.exists(root + "/") else []
    if slashed != "/tmp" and not slashed.startswith("/tmp/"):
        return []
    temps = [value for value in map(os.environ.get, ("TMP", "TEMP")) if value]
    if not temps or not all(
        ABSOLUTE_WINDOWS_RE.match(t) and not any(ch in EXPANDED_CHARS for ch in t) for t in temps
    ):
        return []
    return [t.rstrip("/\\") + slashed[len("/tmp"):] for t in temps]


def _comparable(path: str) -> str:
    return os.path.normcase(_long_path(os.path.abspath(path)))


def _long_path(path: str) -> str:
    """On Windows, absolute `path` with its 8.3 short names (`PROGRA~1`)
    expanded, as far as its folders exist; elsewhere, or with no `~`, as is."""

    if os.name != "nt" or "~" not in path:
        return path
    import ctypes  # Only Windows short names need it; most hook calls never get here.

    buffer = ctypes.create_unicode_buffer(32768)
    head, missing = path, []
    while True:
        if ctypes.windll.kernel32.GetLongPathNameW(head, buffer, len(buffer)):
            return os.path.join(buffer.value, *reversed(missing))
        parent, name = os.path.split(head)
        if not name or parent == head:
            return path  # No part of it exists, so nothing can be expanded.
        missing.append(name)
        head = parent


def _proves_itself(call, project: Project | None) -> bool:
    """True when a shell call ran a check after each code file it wrote in
    the project (see `ShellCommand.unchecked_targets`).

    The call's result stands for the whole command, so a check that failed
    still counts when the command hid its status (`pytest || true`,
    `pytest; echo done`, `pytest | tail`); the Unfinished item then cannot
    see the failure either.
    """

    if call.name not in COMMAND_TOOLS:
        return False
    command = shell.analyze(str(call.input.get("command") or ""), call.name)
    return not command.unchecked_unknown_writes and not any(
        is_code(_norm(target)) for target in command.unchecked_targets
        if target and _in_project(target, project, target not in command.unplaced_targets)
    )


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


def _small_edit(tool_input: dict) -> bool:
    """Whether an edit adds fewer than `DESIGN_MIN_LINES` lines, as
    `added_lines` counts them. An edit whose added lines cannot be counted, an
    `edits` entry that is not an edit or an input with no text it writes, is
    not small."""

    edits = tool_input.get("edits")
    if isinstance(edits, list):
        countable = all(isinstance(e, dict) and isinstance(e.get("new_string"), str) for e in edits)
    else:
        countable = any(isinstance(tool_input.get(key), str) for key in ("content", "new_string", "new_source"))
    return countable and added_lines(tool_input) < DESIGN_MIN_LINES


def _subject(message: str) -> str:
    return " ".join(message.strip().split("\n", 1)[0].split())


def _norm(path: str) -> str:
    return path.replace("\\", "/")


def _same_file(read: str, changed: str) -> bool:
    """True when two paths, either relative, name the same file; judged from
    the text alone, so a relative path matches any file it ends."""

    a, b = (_norm(p).lower().removeprefix("./") for p in (read, changed))
    return bool(a and b) and (a == b or a.endswith("/" + b) or b.endswith("/" + a))


def _ends_with_path(path: str, suffix: str) -> bool:
    path = _norm(path).lower()
    return path == suffix or path.endswith("/" + suffix)
