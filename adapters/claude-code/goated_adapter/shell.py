"""What a `Bash` or `PowerShell` command does, as far as the gates care.

`analyze` reads one command string and answers: does it write files, is it a
`git commit` (and with what inline message), does it open a pull request, and
is it a check that proves a change. This module is the only place that knows
shell syntax; the gates see `ShellCommand` objects.

The analysis is lexical, not a shell parser. Quoted text, heredoc bodies, and
PowerShell here-strings are blanked before matching, so `echo "a > b"` is not
a redirect. It recognizes the common forms agents use; a command that hides a
write inside an interpreter (`python -c "open(...)"`) is not seen. That limit
is documented in the adapter README.
"""

from __future__ import annotations

import re

# Heredoc: `<<EOF`, `<<-EOF`, `<<'EOF'`, `<<"EOF"`, body up to a line holding
# only the word.
HEREDOC_RE = re.compile(
    r"<<-?[ \t]*(['\"]?)([A-Za-z_]\w*)\1([^\n]*)\n(.*?)(?:\n[ \t]*\2[ \t]*(?=\n|$)|\Z)",
    re.DOTALL,
)
HERESTRING_RE = re.compile(r"@(['\"])\r?\n(.*?)\r?\n\1@", re.DOTALL)
SINGLE_RE = re.compile(r"'[^']*'")
DOUBLE_RE = re.compile(r'"(?:[^"\\`]|\\.|`.)*"', re.DOTALL)

SEGMENT_SPLIT_RE = re.compile(r"\$\(|&&|\|\||[;&|\n(){}]")
# A redirect that writes: `>`, `>>`, `>|`, `&>`, `2>`, `*>`, but not `>&1`,
# `2>&1`, `->`, `=>`, or a redirect into a null device.
REDIRECT_RE = re.compile(r"(?:^|(?<=[^<>=\-&|0-9*]))(?:[0-9*]|&)?>>?\|?[ \t]*(?!&)([^\s;&|)]+)")
NULL_TARGETS = frozenset({"/dev/null", "$null", "nul", "/dev/stderr", "/dev/stdout"})
DOTNET_WRITE_RE = re.compile(
    r"\[(?:system\.)?io\.(?:file|directory)\]::(?:write|append|copy|move|delete|create|replace)",
    re.IGNORECASE,
)

# Command words whose job is to write, copy, move, or delete files. Bash first,
# then PowerShell cmdlets and the aliases Windows PowerShell ships.
WRITE_COMMANDS = frozenset(
    {
        "cp", "mv", "rm", "rmdir", "touch", "tee", "truncate", "ln", "unlink", "shred",
        "set-content", "add-content", "out-file", "clear-content", "new-item", "copy-item",
        "move-item", "remove-item", "rename-item", "tee-object",
        "del", "erase", "copy", "move", "ren", "rename", "rd", "ri", "mi", "cpi", "ni", "rni",
    }
)
IN_PLACE_COMMANDS = frozenset({"sed", "perl"})
GIT_WRITE_SUBCOMMANDS = frozenset({"apply", "am", "restore", "mv", "rm", "clean"})
# Words that only start another command, so the real command word follows.
PREFIX_WORDS = frozenset({"sudo", "env", "command", "nohup", "time", "exec", "xargs", "&", "."})
GIT_GLOBAL_WITH_VALUE = frozenset({"-c", "-C", "--git-dir", "--work-tree", "--namespace"})

# Reading a file never proves a change, even when its name says "test".
READ_COMMANDS = frozenset(
    {
        "cat", "less", "more", "head", "tail", "grep", "rg", "ls", "find", "echo", "printf",
        "git", "get-content", "type", "gc", "select-string", "wc", "diff", "sed", "awk",
        "test-path", "get-childitem", "dir", "cd", "set-location", "pwd", "which",
        "get-command",
    }
)
# Word edges include `_` and `-`, so `validate_skills.py` and `run-tests` count.
CHECK_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:test|tests|pytest|unittest|tox|nox|vitest|jest|mocha|lint|eslint|"
    r"ruff|flake8|mypy|pyright|tsc|typecheck|clippy|check|build|validate|verify)(?![A-Za-z0-9])",
    re.IGNORECASE,
)
PR_RE = re.compile(r"\b(?:gh[ \t]+pr[ \t]+create|glab[ \t]+mr[ \t]+create)\b", re.IGNORECASE)


class ShellCommand:
    """The facts the gates need about one shell command.

    `writes` says it writes, copies, moves, or deletes files. `commit` is True
    for a `git commit`; `commit_message` is its message when the command
    carries it inline (`-m`, `--message`, a heredoc on `-F -`, or a PowerShell
    here-string), else None. `opens_pr` covers `gh pr create` and
    `glab mr create`. `is_check` says it runs a test, lint, build, or check.
    `words` are the command's unquoted words, for path checks.
    """

    __slots__ = ("writes", "commit", "commit_message", "opens_pr", "is_check", "words")

    def __init__(self) -> None:
        self.writes = False
        self.commit = False
        self.commit_message: str | None = None
        self.opens_pr = False
        self.is_check = False
        self.words: list[str] = []


def analyze(command: str) -> ShellCommand:
    """Return what `command` does; never raises on odd input."""

    result = ShellCommand()
    blank = _blank_quoted(command)
    result.words = [w for w in re.split(r"[\s;&|()<>]+", _blank_quoted(command, keep_text=True)) if w]
    if any(t.lower() not in NULL_TARGETS for t in REDIRECT_RE.findall(blank)):
        result.writes = True
    if DOTNET_WRITE_RE.search(blank):
        result.writes = True
    result.opens_pr = bool(PR_RE.search(blank))
    for segment in SEGMENT_SPLIT_RE.split(blank):
        words = _command_words(segment)
        if not words:
            continue
        name = words[0]
        if name in WRITE_COMMANDS:
            result.writes = True
        elif name in IN_PLACE_COMMANDS and _edits_in_place(words[1:]):
            result.writes = True
        elif name == "git":
            sub, rest = _git_subcommand(words[1:])
            if _git_writes(sub, rest):
                result.writes = True
            if sub == "commit":
                result.commit = True
        if name not in READ_COMMANDS and CHECK_RE.search(segment):
            result.is_check = True
    if result.commit:
        result.commit_message = commit_message(command)
    return result


def _blank_quoted(command: str, keep_text: bool = False) -> str:
    """Blank heredoc bodies, here-strings, and quoted strings.

    With `keep_text`, quotes are removed but their text kept, so a quoted path
    still counts as a word.
    """

    def heredoc(match: re.Match) -> str:
        return "<<" + match.group(2) + match.group(3) + "\n"

    text = HEREDOC_RE.sub(heredoc, command)
    text = HERESTRING_RE.sub("''", text)
    if keep_text:
        return SINGLE_RE.sub(lambda m: m.group(0)[1:-1], DOUBLE_RE.sub(lambda m: m.group(0)[1:-1], text))
    return SINGLE_RE.sub("''", DOUBLE_RE.sub('""', text))


def _command_words(segment: str) -> list[str]:
    """Return the segment's words with the real command word first, lowercased.

    Prefix words, `VAR=value` assignments, and a prefix's own options (as in
    `xargs -0 rm`) are dropped, and a path or `.exe` suffix is stripped.
    """

    words = segment.split()
    while words and (
        words[0].lower() in PREFIX_WORDS or re.match(r"^[A-Za-z_]\w*=", words[0])
        or (words[0].startswith("-") and len(words) > 1)
    ):
        words = words[1:]
    if not words:
        return []
    name = words[0].replace("\\", "/").rsplit("/", 1)[-1].lower()
    if name.endswith(".exe"):
        name = name[:-4]
    return [name, *words[1:]]


def _edits_in_place(args: list[str]) -> bool:
    for arg in args:
        if arg == "--in-place" or arg.startswith("--in-place="):
            return True
        if arg.startswith("-") and not arg.startswith("--") and "i" in arg[1:].split(".", 1)[0]:
            return True
    return False


def _git_subcommand(args: list[str]) -> tuple[str, list[str]]:
    index = 0
    while index < len(args) and args[index].startswith("-"):
        index += 2 if args[index] in GIT_GLOBAL_WITH_VALUE else 1
    if index >= len(args):
        return "", []
    return args[index].lower(), args[index + 1 :]


def _git_writes(sub: str, rest: list[str]) -> bool:
    if sub in GIT_WRITE_SUBCOMMANDS:
        return True
    if sub == "checkout":
        return "--" in rest
    if sub == "reset":
        return "--hard" in rest
    if sub == "stash":
        return bool(rest) and rest[0] in {"pop", "apply"}
    return False


# Commit messages ------------------------------------------------------------

MESSAGE_OPTION_RE = re.compile(r"(?:^|\s)(?:-m|--message)(?:=|[ \t]*)")
FILE_STDIN_RE = re.compile(r"(?:^|\s)(?:-F|--file)(?:=|[ \t]*)-(?=\s|$)")


def commit_message(command: str) -> str | None:
    """Return the message a `git commit` command carries inline, or None.

    Several `-m` options join as paragraphs, as git joins them. A heredoc fed
    to `-F -`, or inside `-m "$(cat <<'EOF' ... EOF)"`, gives its body. A
    message in a file, or one git would ask for in an editor, is not in the
    command, so the answer is None.
    """

    heredoc = HEREDOC_RE.search(command)
    if heredoc and (FILE_STDIN_RE.search(command) or "$(cat" in command):
        return heredoc.group(4).strip("\n")
    parts = []
    for match in MESSAGE_OPTION_RE.finditer(command):
        value = _read_value(command, match.end())
        if value is None:
            return None
        parts.append(value)
    return "\n\n".join(parts) if parts else None


def _read_value(text: str, start: int) -> str | None:
    """Read one shell word starting at `start`: quoted, here-string, or bare."""

    rest = text[start:]
    here = re.match(r"@(['\"])\r?\n(.*?)\r?\n\1@", rest, re.DOTALL)
    if here:
        return here.group(2)
    if rest.startswith("'"):
        end = rest.find("'", 1)
        return rest[1:end] if end > 0 else None
    if rest.startswith('"'):
        match = re.match(r'"((?:[^"\\`]|\\.|`.)*)"', rest, re.DOTALL)
        if not match:
            return None
        value = match.group(1)
        if "$(" in value:
            return None  # A command substitution other than a heredoc: not knowable.
        return re.sub(r'\\(["\\$`])', r"\1", value)
    match = re.match(r"[^\s;&|]+", rest)
    return match.group(0) if match else None
