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
and the design red flags, and close a turn that changed setup with
`setup-scribe`.

Every decision is a pure function of the current turn as the transcript
records it, plus the user's typed overrides for that turn. So an unchanged
retry always gets the same answer (spec R6), and a hold stops firing as soon
as the turn shows compliance. Proof counts only within the current turn
(spec R7): a skill loaded in an earlier turn does not cover a later action.
The one input from outside the transcript is a pull request's size, which
the `pr-review` gate asks git for, and only when its hold would otherwise
fire.

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

import os
from collections.abc import Callable
from typing import NamedTuple
import re
import subprocess
import time

from . import contracts, design_reads, shell
from .gates import COMMAND_TOOLS, STRICT, Hold, goated_skill_name, unseen_line_advice
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
SETUP_SKILL = "setup-scribe"
REVIEW_SKILL = "standards-and-spec-review"
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
# A pull request changing at least this many lines against its base, added
# plus deleted, is large enough to review before it lands: the adapter's
# stand-in for the skill's "large" (adapter README, Large pull requests).
REVIEW_MIN_LINES = 400
# How long the size check's git calls may take in all before it gives up and
# holds nothing.
SIZE_TIMEOUT_SECONDS = 2.0
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
# Env and settings files whose change is setup (spec G3): `.env` and `.env.*`,
# and `settings*.json` under `.claude/` or `.vscode/`. They count only inside
# the project (spec R9), so a scratch folder's or `~/.claude`'s settings do not.
SETUP_FILE_RE = re.compile(
    r"(?:^|/)\.env(?:\.[^/]*)?$|(?:^|/)\.(?:claude|vscode)/settings[^/]*\.json$", re.IGNORECASE
)


class _Proof:
    """What the current turn shows: loads, skip lines, reads, and user skips."""

    def __init__(self, turn: Turn, overrides: dict, namespaces: tuple[str, ...],
                 extra_text: str = "") -> None:
        self.turn = turn
        self.namespaces = namespaces
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

    def load_index(self, skill: str) -> int | None:
        """Where in the turn's calls `skill` first loaded: -1 when the prompt
        invoked it as `/<skill>`, None when it did not load."""

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

    def read(self, reference: str, after: int = -1) -> bool:
        return self.read_index(reference, after) is not None


def is_action_tool(tool_name: str) -> bool:
    """True for a tool some action gate may hold (the hook matcher must cover these)."""

    return (
        tool_name in COMMAND_TOOLS or tool_name in SPAWN_BRIEF_FIELDS
        or tool_name in FILE_WRITE_TOOLS or bool(PR_TOOL_RE.match(tool_name))
        or bool(COMMIT_TOOL_RE.match(tool_name))
    )


def check_action(tool_name: str, tool_input: dict, turn: Turn, overrides: dict,
                 namespaces: tuple[str, ...] = (), project: Project | None = None,
                 subagents: Callable[[], dict] | None = None,
                 references_read: frozenset[str] = frozenset()) -> Hold | None:
    """Return the action hold for this call, if any; the call's own entry is not yet proof.

    `project` says which files are the project's (see `find_project`): only files
    inside it meet the design and security gates, and only changes to them
    are the turn's changes a change read must follow; git measures a pull
    request in its `cwd`. `subagents` returns the turns
    of each subagent this turn spawned, as `check_closeout` takes them; it is
    called only when a commit or pull request needs its change read, since
    reading their transcripts takes time. `references_read` names the design
    references (`errors.md`) read in earlier turns since the last compaction;
    the turn's own reads count too.
    """

    proof = _Proof(turn, overrides, namespaces)
    changes = lambda: _Changes(turn, subagents() if subagents else {}, project)
    cwd = project.cwd if project else None  # Where git measures a pull request's size.
    if tool_name in COMMAND_TOOLS:
        command = shell.analyze(str(tool_input.get("command") or ""), tool_name)
        hold = _conflict_hold(command.write_targets, tool_input, proof) if command.writes else None
        if hold is None and command.commit:
            hold = _commit_hold(command.commit_message, proof, changes)
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
                            by_tool=True)
    if tool_name in SPAWN_BRIEF_FIELDS:
        brief = str(tool_input.get(SPAWN_BRIEF_FIELDS[tool_name]) or "")
        return _spawn_hold(brief, proof) if brief.strip() else None
    if tool_name in FILE_WRITE_TOOLS:
        path = _norm(str(tool_input.get(FILE_WRITE_TOOLS[tool_name]) or ""))
        # A conflict is open, and a check keeps failing, wherever the file lives
        # (a worktree may sit outside the project folder), as the shell branch
        # above holds every write target for them.
        hold = _conflict_hold([path], tool_input, proof)
        if hold is None and _in_project(path, project):
            # A scratch file elsewhere is not the project's design or security.
            hold = _security_hold(path, proof) or _design_hold(
                path, tool_input, proof, project, references_read)
        return hold or _repeated_failure_hold(proof)
    return None


def _commit_hold(message: str | None, proof: _Proof, changes: Callable[[], "_Changes"],
                 by_tool: bool = False) -> Hold | None:
    """Hold a commit until `commit-message` loads, its inline message (`message`,
    if known) keeps the contract, and the change is read after the load;
    `by_tool`: an MCP tool records it, not a git command."""

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
        f"Load the `{PR_SKILL}` skill with the Skill tool in this turn and draft the "
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
            "review it and open the pull request again", skippable=True,
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
        "with the Skill tool in this turn and review the change with it. If size is not "
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


def changed_lines(cwd: str | None, base: str | None, head: str | None = None,
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

    Two git calls, three with `repository`, within `SIZE_TIMEOUT_SECONDS` in
    all. Every name reaches git inside a full ref name (`refs/...`), so none
    reads as an option, and external diff and text-conversion programs are
    switched off, so only git runs.
    """

    if not cwd:
        return None
    deadline = time.monotonic() + SIZE_TIMEOUT_SECONDS
    if repository is not None:
        url = _git(["config", "--get", "remote.origin.url"], cwd, deadline)
        if url is None or not _names_repository(url, repository):
            return None
    base_refs = ((f"refs/remotes/origin/{base}", f"refs/heads/{base}") if base
                 else DEFAULT_BASE_REFS)
    head_refs = (f"refs/heads/{head}", f"refs/remotes/origin/{head}") if head else ()
    listed = _git(["for-each-ref", "--format=%(refname)", *base_refs, *head_refs], cwd, deadline)
    if listed is None:
        return None
    found = set(listed.split())  # A pattern also lists refs below it, so match exactly.
    base_ref = next((ref for ref in base_refs if ref in found), None)
    head_ref = next((ref for ref in head_refs if ref in found), None) if head else "HEAD"
    if base_ref is None or head_ref is None:
        return None
    stat = _git(["diff", "--shortstat", "--no-ext-diff", "--no-textconv",
                 f"{base_ref}...{head_ref}", "--"], cwd, deadline)
    if stat is None:
        return None
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
                      doing: str, then: str, skippable: bool = False) -> Hold | None:
    """Hold a commit or pull request, whose skill has loaded, until a change read
    follows both that load and the turn's last change to any project file;
    `skippable`: the hold is justified-skip, so a skip line naming `skill` clears it.

    An MCP tool (`by_tool`) passes when the turn changed no project file: it
    carries the change in its own input, and outside a git checkout no diff
    can run and no changed file exists to Read, so the strict hold would have
    no way out.
    """

    if by_tool and changes.last_change < 0:
        return None
    if changes.read_after(max(proof.load_index(skill), changes.last_change)):
        return None
    how = CHANGE_READ if changes.paths else DIFF_ONLY_READ
    after = " and after your last change" if changes.last_change >= 0 else ""
    # Not backticked: the skill-usage mod would read a backticked skip line as an ask
    # that only a skip line answers, and count a read that clears this hold as ignored.
    tail = (f"Or write a skip line, goated-skip: {skill}: <reason>, on its own line. "
            + unseen_line_advice("skip line", f"skip {skill}") if skippable
            else "This hold is strict: a goated-skip line does not clear it.")
    return Hold(
        gate, JUSTIFIED_SKIP if skippable else STRICT,
        f"Read the change before {doing}, after loading the {skill} skill{after}: "
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
            "with the Skill tool in this turn, read its `references/spawn-brief.md`, and "
            "write the brief from that template (Goal, Scope, Done Means at least). For a "
            "scoped implementation or review task, load `subagent-driven-development` "
            "and fill its implementer or reviewer prompt instead. Nothing was started. "
            "This hold is strict: a goated-skip line does not clear it.",
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
        f"\"{path.rsplit('/', 1)[-1]}\" is a security-sensitive surface ({category}). Load "
        f"`{SECURITY_SKILL}` with the Skill tool in this turn and review this change with "
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
        f"`{CONFLICT_SKILL}` with the Skill tool in this turn and resolve it from the "
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


def _design_hold(path: str, tool_input: dict, proof: _Proof, project: Project | None,
                 references_read: frozenset[str]) -> Hold | None:
    """Hold a project file write until its design is done (spec R5).

    The `design` gate holds a turn's first substantial code edit until
    `software-design-principles` loads, a design-reads line is in the turn,
    and every reference the edit requires is read. The `design-reads` gate
    holds any later edit the design-reads rules apply to, once the skill is
    loaded, until the references it requires are read. `design_reads` says
    which those are. A read counts until the next compaction; a skip line or
    the user's skip of the skill clears both gates.
    """

    code, test = is_code(path), bool(TEST_PATH_RE.search(path))
    if not design_reads.applies(path, is_code=code, is_test=test) or proof.skipped(DESIGN_SKILL):
        return None
    substantial = code and added_lines(tool_input) >= DESIGN_MIN_LINES
    loaded = proof.loaded(DESIGN_SKILL)
    if not loaded and not substantial:
        return None
    earlier = _project_code_writes(proof.turn, project)
    declared = declared_files(proof.turn.design_reads)
    required = design_reads.required(
        path, tool_input, is_code=code, is_test=test,
        written_before=any(p == path for p, _ in earlier),
        other_code_files=len({p for p, _ in earlier if p != path and not TEST_PATH_RE.search(p)}),
        declared=declared, cwd=project.cwd if project else None,
    )
    read = references_read | set(design_reads.reads_in(proof.turn.calls))
    unread = {name: why for name, why in required.items() if name not in read}
    needs_line = substantial and not proof.turn.design_reads
    if loaded and not needs_line and not unread:
        return None
    unknown = design_reads.unknown(declared)
    misnamed = (
        " Your design-reads lines name files that are not design references, so they require "
        "nothing: " + ", ".join(f'"{name}"' for name in unknown) + "."
    ) if unknown else ""
    first = substantial and not any(lines >= DESIGN_MIN_LINES for _, lines in earlier)
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
        f"load `{DESIGN_SKILL}` with the Skill tool and apply its 'Before changing code' rules"
    ]
    if needs_line:
        malformed = "; ".join(f'"{line}"' for line in proof.turn.malformed_design_reads)
        steps.append(
            "write the skill's design-reads line on its own line, naming the references whose "
            "conditions hold, as `goated-design-reads: <file>, <file>`, or "
            "`goated-design-reads: none: <reason>` when none does"
            + (f" (these lines in this turn do not match the grammar: {malformed})" if malformed else "")
        )
    if unread:
        steps.append(f"read with the Read tool each reference it requires: {_reference_list(unread)}")
    return Hold(
        "design", JUSTIFIED_SKIP,
        f"This is a substantial code change. Before it, in this turn, {'; '.join(steps)}."
        f"{misnamed} If the edit is mechanical, with no design in it, write "
        f"`goated-skip: {DESIGN_SKILL}: <reason>` on its own line instead. This edit was not "
        "applied. " + unseen_line_advice("design-reads or skip line", f"skip {DESIGN_SKILL}"),
    )


def _reference_list(references: dict[str, str]) -> str:
    """The references as the holds name them, in the given order. Each path is
    backticked like the closeout's red-flags path; the skill-usage mod reads
    only a bare backticked name as a skill."""

    return ", ".join(f"`{design_reads.SKILL_REFERENCES}{name}` ({why})" for name, why in references.items())


def _project_code_writes(turn: Turn, project: Project | None) -> list[tuple[str, int]]:
    """Each finished edit tool call on a project code file in the turn: its path
    and how many lines it added."""

    writes = []
    for call in turn.calls:
        if call.ok and call.name in FILE_WRITE_TOOLS:
            path = _norm(str(call.input.get(FILE_WRITE_TOOLS[call.name]) or ""))
            if is_code(path) and _in_project(path, project):
                writes.append((path, added_lines(call.input)))
    return writes


def _repeated_failure_hold(proof: _Proof) -> Hold | None:
    """Hold a write once one check command has failed twice in a row in the turn.

    "The same check" is the same command text, whitespace aside (spec G2),
    without a trailing pipe into output filters (`| tail -20`): a narrowed
    rerun, such as one test file of a failing suite, is another command. A
    pass of that check resets its count; other commands between runs do not.
    Only runs count: a call held, refused, or interrupted never ran.
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
        # A pipe's exit code is its last filter's, so a piped run fails by what it prints.
        failed = bool(FAILURE_SIGNS_RE.search(call.output)) if piped else not call.ok
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
        f"a row in this turn. Load `{DIAGNOSE_SKILL}` with the Skill tool in this turn and "
        "find the root cause before changing more. If the cause is already known, write "
        f"`goated-skip: {DIAGNOSE_SKILL}: <reason>` on its own line instead. This write was "
        "not applied. Rerunning the check is not held, and a pass of it resets the count. "
        + unseen_line_advice("skip line", f"skip {DIAGNOSE_SKILL}"),
    )


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
                   project: Project | None = None) -> Hold | None:
    """Return the closeout hold for a turn about to end, if any.

    A turn that changed code needs, after its last code change, a check
    command (proof), in a later call or later in the same shell command. It
    also needs `doc-sync` when non-test code changed, `handoff` when the
    last check after the change failed (work left unfinished), and a read
    of the design red flags after the change when
    `software-design-principles` was loaded. A turn that loaded
    `code-security-review` and changed a security-sensitive file, code or
    not, needs a security review. The doc-sync, design, and security items
    each also need a change read after their load or red-flags read. A turn
    that installed a package it names, or wrote an env or settings file, needs
    `setup-scribe` loaded at any point in the turn (Setup). Each item accepts
    a skip line; `final_text` is the reply being finished, which
    may not be in the transcript yet.

    `subagents` maps the agent id of each subagent this turn spawned to its
    turns. Their code changes count as made at the spawn; a subagent that ran
    a check after its own last change has already proved them. Only files
    inside `project` count (see `find_project`); a scratch file elsewhere does not.
    """

    changes = _Changes(turn, subagents or {}, project)
    proof = _Proof(turn, overrides, namespaces, final_text)
    items = _code_items(changes, proof) if changes.code else []
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
    return Hold(
        "closeout", JUSTIFIED_SKIP,
        f"Before finishing this turn, which {what}:\n" + "\n".join(items)
        + "\nA skip line must name the skill and give a reason of three or more words.",
    )


def _code_items(changes: "_Changes", proof: _Proof) -> list[str]:
    """The closeout items a code change needs: proof, a handoff for a failed
    check, doc-sync, and the design red flags, each with what is missing."""

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
        not TEST_PATH_RE.search(path) for change in code for path in change.code_paths
    )
    if non_test and not proof.skipped(DOC_SYNC_SKILL):
        loaded = proof.load_index(DOC_SYNC_SKILL)
        if loaded is None:
            items.append(
                f"- Docs: code changed. Load `{DOC_SYNC_SKILL}`, then read the change itself "
                f"and check whether durable docs now drift: {CHANGE_READ}. Or, if behavior "
                f"and interfaces did not change, write `goated-skip: {DOC_SYNC_SKILL}: <reason>`."
            )
        elif not changes.read_after(max(loaded, last)):
            # The skill is loaded, so it is named only in the skip line: no load answers this.
            items.append(
                f"- Docs: after loading the {DOC_SYNC_SKILL} skill and after your last code "
                f"change, read the change itself and check whether durable docs now drift: "
                f"{CHANGE_READ}. Or write `goated-skip: {DOC_SYNC_SKILL}: <reason>`."
            )
    if DESIGN_SKILL in proof.loads and not proof.skipped(DESIGN_SKILL):
        flags = proof.read_index(RED_FLAGS_REFERENCE, after=last)
        if flags is None:
            items.append(
                f"- Design: read `{RED_FLAGS_REFERENCE}` with the Read tool after your last "
                f"change, then read the change itself and scan it against them: {CHANGE_READ}. "
                f"Or write `goated-skip: {DESIGN_SKILL}: <reason>`."
            )
        elif not changes.read_after(flags):
            items.append(
                "- Design: after reading the red flags, read the change itself and scan it "
                f"against them, not your memory of it: {CHANGE_READ}. Or write "
                f"`goated-skip: {DESIGN_SKILL}: <reason>`."
            )
    return items


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
    files, which of them are code, and whether it is already proved: by a
    check later in the same command, or by a subagent's own check."""

    __slots__ = ("index", "paths", "code_paths", "proven")

    def __init__(self, index: int, paths: list[str], proven: bool = False) -> None:
        self.index = index
        self.paths = paths
        self.code_paths = [p for p in paths if _is_code_change(p)]
        self.proven = proven


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
                yield _Change(index, [p for paths in changed for p in paths], proven)
            continue
        paths = _changed_paths(call, project)
        if paths:
            yield _Change(index, paths, _proves_itself(call, project))


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
    rooted = path.startswith(("/", "\\", "~")) or (os.name == "nt" and DRIVE_RE.match(path))
    if not rooted:
        path = project.cwd.rstrip("/\\") + "/" + path
    drives = {os.path.splitdrive(root)[0] for root in project.roots}
    readings = _readings(path, drives)
    if readings is None or _under_any(readings, project.roots):
        return True
    # A link may lead into the project from outside it, or out of a root.
    return _under_any(_resolved(readings), _resolved(project.roots))


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
