"""What a `Bash` or `PowerShell` command does, as far as the gates care.

`analyze` reads one command string and answers: does it write files, and
which; is it a `git commit`, and with what inline message; does it open a pull
request; and does it run a check that proves a change. This module is the
only place that knows shell syntax; the gates see `ShellCommand` objects.

The command is split into segments (simple commands joined by `;`, `&&`,
`||`, `|`, `&`, newlines, parentheses, braces, or `$(`), with quotes, escapes,
line continuations, comments, heredocs, PowerShell here-strings, `[[ ]]`
tests, and arithmetic understood well enough that `echo "a > b"`,
`[[ $a > $b ]]`, and `ls # a > b` write nothing. Each segment's real command
word is found past wrappers such as `sudo -u x`, `env`, `timeout 60`, `nice`,
`xargs`, and `cmd /c`. It is still a lexical reading, not a shell: a command
run through `bash -c`, `eval`, `Invoke-Expression`, backticks, a heredoc fed to
a shell, or a git alias is not seen. The adapter README lists these limits.
"""

from __future__ import annotations

import re

NULL_TARGETS = frozenset({"/dev/null", "$null", "nul", "/dev/stderr", "/dev/stdout"})
DOTNET_WRITE_RE = re.compile(
    r"\[(?:system\.)?io\.(?:file|directory)\]::(?:write|append|copy|move|delete|create|replace)",
    re.IGNORECASE,
)
# A bash escape outside quotes; elsewhere a backslash is kept, so Windows paths survive.
ESCAPABLE = frozenset(" \t\"'\\$`;&|<>(){}#*?[]~!")
SEPARATORS = frozenset(";|&\n(){}")

# Write commands, by how their file arguments are read. Bash first, then
# PowerShell cmdlets and the aliases Windows PowerShell 5.1 ships.
TARGETS_ARE_ARGS = frozenset(
    {
        "rm", "rmdir", "touch", "truncate", "tee", "unlink", "shred", "ln",
        "mv", "move", "ren", "rename",
        "del", "erase", "rd", "ri", "remove-item", "mi", "move-item", "rni", "rename-item",
        "tee-object", "clear-content", "clc", "new-item", "ni",
    }
)
TARGET_IS_LAST_ARG = frozenset({"cp", "copy", "cpi", "copy-item", "install"})
# PowerShell cmdlets whose first positional argument, or -Path, is the file.
TARGET_IS_PATH_PARAM = frozenset(
    {"set-content", "sc", "add-content", "ac", "out-file", "export-csv", "export-clixml"}
)
PS_PATH_PARAMS = frozenset({"-path", "-literalpath", "-filepath", "-destination", "-outfile"})
PS_VALUE_PARAMS = PS_PATH_PARAMS | frozenset(
    {"-value", "-encoding", "-itemtype", "-name", "-include", "-exclude", "-filter",
     "-delimiter", "-inputobject", "-newname", "-uri", "-method"}
)
# Writes whose files cannot be read from the command line.
UNKNOWN_TARGET_COMMANDS = frozenset({"patch"})
DOWNLOADERS = frozenset({"curl", "wget", "invoke-webrequest", "iwr", "invoke-restmethod", "irm"})
GIT_UNKNOWN_TARGET_SUBCOMMANDS = frozenset({"apply", "am", "clean"})
GIT_GLOBAL_WITH_VALUE = frozenset({"-c", "-C", "--git-dir", "--work-tree", "--namespace"})
# Change reads (spec R7): git subcommands that print the changes' content by
# default, the options that ask for it explicitly, and the options that print
# names, counts, nothing, or into a file instead (matched as prefixes, so
# `--stat=80` counts as `--stat`).
GIT_PATCH_BY_DEFAULT = frozenset({"diff", "show"})
GIT_PATCH_FLAGS_RE = re.compile(r"-p|-u|-U\d*|--patch(?:-with-(?:stat|raw))?|--unified(?:=\d+)?")
GIT_NO_PATCH_FLAGS = (
    "--stat", "--shortstat", "--numstat", "--dirstat", "--compact-summary", "--summary",
    "--name-only", "--name-status", "--no-patch", "--check", "--raw",
)
# Options that print nothing to the agent, even beside a patch option.
GIT_SILENT_FLAGS_RE = re.compile(r"--quiet|--output(?:=.*)?")
# `gh pr diff` and `glab mr diff` print a pull or merge request's patch.
FORGE_DIFFS = {"gh": "pr", "glab": "mr"}

# Wrappers that run the next word as the command, with the options of each
# that take a value.
WRAPPERS = {
    "sudo": {"-u", "-g", "-h", "-p", "-C", "-D", "-r", "-t", "-U"},
    "doas": {"-u", "-C"},
    "env": {"-u", "-C", "-S"},
    "nice": {"-n"},
    "ionice": {"-c", "-n", "-p"},
    "timeout": {"-s", "-k"},
    "nohup": set(),
    "command": set(),
    "builtin": set(),
    "exec": {"-a"},
    "time": {"-f", "-o"},
    "stdbuf": {"-i", "-o", "-e"},
    "xargs": {"-I", "-n", "-P", "-L", "-d", "-E", "-s", "-a"},
}

# Check commands: tools that are checks by name, and runners whose first
# argument decides.
CHECK_TOOLS = frozenset(
    {
        "pytest", "py.test", "tox", "nox", "jest", "vitest", "mocha", "ava", "eslint", "ruff",
        "flake8", "pylint", "mypy", "pyright", "tsc", "ctest", "phpunit", "rspec",
        "shellcheck", "golangci-lint", "invoke-pester", "bats", "pre-commit",
    }
)
CHECK_MODULES = frozenset(
    {"pytest", "unittest", "mypy", "ruff", "tox", "nox", "pyright", "flake8", "pylint", "doctest"}
)
SUBCOMMAND_CHECKS = {
    "cargo": {"test", "check", "clippy", "build", "nextest"},
    "go": {"test", "vet", "build"},
    "dotnet": {"test", "build"},
    "npm": {"test", "t"},
    "pnpm": {"test", "t"},
    "yarn": {"test"},
    "bun": {"test"},
    "deno": {"test", "check", "lint"},
}
SCRIPT_RUNNERS = frozenset({"npm", "pnpm", "yarn", "bun"})
TARGET_RUNNERS = frozenset({"make", "just", "task", "rake", "mvn", "mvnw", "gradle", "gradlew"})
COMMAND_RUNNERS = {  # runner -> subcommand that runs the rest as a command ("" for none)
    "uv": "run", "poetry": "run", "pipenv": "run", "pdm": "run", "hatch": "run",
    "bundle": "exec", "npx": "", "pnpx": "", "bunx": "",
}
INTERPRETERS = frozenset(
    {"python", "python3", "py", "node", "bash", "sh", "zsh", "pwsh", "powershell", "ruby",
     "perl", "php"}
)
CHECK_WORD_RE = re.compile(
    r"(?<![a-z0-9])(?:test|tests|check|checks|validate|verify|lint|typecheck|build|ci)(?![a-z0-9])",
    re.IGNORECASE,
)


class ShellCommand:
    """The facts the gates need about one shell command.

    `writes` says it writes, copies, moves, or deletes files. `write_targets`
    are the files it names as written (redirect targets, copy destinations,
    removed or moved files, in-place edits), each joined to any `cd` before
    it in the command that can be followed (see `_change_directory`).
    `unplaced_targets` are the relative ones written from a folder the
    command left unknown, so where they are cannot be said. `unknown_writes` says some
    write's files cannot be read from the command (`git apply`, `patch`, a
    download without an output name). `commit` is True for a `git commit`
    that records one (not `--dry-run`); `commit_message` is its message when
    that commit carries it inline, else None. `opens_pr` covers
    `gh pr create|new` and `glab mr create|new`. `is_check` says it runs a
    test, lint, build, or check. `prints_changes` says it prints changes'
    content to the agent: a git diff or show, a patch log, or patches on
    stdout; a listing of names or counts (`--stat`, `--name-only`) does not.
    Only git is read; another version control system's diff is not seen.
    """

    __slots__ = (
        "writes", "write_targets", "unplaced_targets", "unknown_writes", "commit",
        "commit_message", "opens_pr", "is_check", "prints_changes",
    )

    def __init__(self) -> None:
        self.writes = False
        self.write_targets: list[str] = []
        self.unplaced_targets: list[str] = []
        self.unknown_writes = False
        self.commit = False
        self.commit_message: str | None = None
        self.opens_pr = False
        self.is_check = False
        self.prints_changes = False


def analyze(command: str) -> ShellCommand:
    """Return what `command` does; never raises on odd input."""

    result = ShellCommand()
    directory: str | None = ""
    for segment in _segments(command):
        directory = _add_segment(result, segment, directory)
        if segment.after not in AND_THEN and directory != "":
            directory = None  # What runs next runs even if a `cd` before it failed.
    if DOTNET_WRITE_RE.search(command):
        result.writes = result.unknown_writes = True
    return result


def _add_segment(result: ShellCommand, segment: "_Segment", directory: str | None) -> str | None:
    """Add one segment's facts to `result`, its write targets taken from
    `directory` (see `_change_directory`); return the directory later
    segments run in."""

    targets = [t for t in segment.redirects if t.lower() not in NULL_TARGETS]
    unknown = False
    prints = False
    name, original, args = _resolve(segment.words)
    next_directory = directory
    if name in CHANGE_DIRECTORY:
        followed = segment.chained and segment.after in AND_THEN
        next_directory = _change_directory(name, args, directory) if followed else None
    elif name in TARGETS_ARE_ARGS:
        targets += _ps_paths(args) if name.count("-") else _positional(args)
    elif name in TARGET_IS_LAST_ARG:
        positional = _ps_paths(args) if name.count("-") else _positional(args)
        targets += positional[-1:]
    elif name in TARGET_IS_PATH_PARAM:
        targets += _ps_paths(args)[:1]
    elif name in ("sed", "perl") and _edits_in_place(args):
        targets += _in_place_files(name, args)
    elif name in DOWNLOADERS:
        output, writes = _download_target(name, args)
        targets += [output] if output else []
        unknown = writes and not output
    elif name in UNKNOWN_TARGET_COMMANDS:
        unknown = True
    elif name == "git":
        sub, rest = _git_subcommand(args)
        git_targets, git_unknown = _git_writes(sub, rest)
        targets += git_targets
        unknown = git_unknown
        if sub == "commit" and "--dry-run" not in rest:
            result.commit = True
            message = _commit_message(rest, segment.heredocs)
            if message is not None:
                result.commit_message = message
        if _git_prints_changes(sub, rest):
            prints = True
    elif name in FORGE_DIFFS:
        rest = _skip_options(args, {"-R", "--repo"})
        noun = FORGE_DIFFS[name]
        if rest[:1] == [noun] and rest[1:2] in (["create"], ["new"]):
            result.opens_pr = True
        if rest[:2] == [noun, "diff"] and "--name-only" not in rest:
            prints = True
    # Output redirected into a file never reached the agent; a stderr redirect leaves it.
    if prints and not [t for t in segment.out_redirects if t.lower() not in NULL_TARGETS]:
        result.prints_changes = True
    if _is_check(name, original, args):
        result.is_check = True
    for target in filter(None, targets):
        if directory is None and not _is_absolute(target):
            result.unplaced_targets.append(target)
        result.write_targets.append(_from_directory(directory, target))
    if targets or unknown:
        result.writes = True
    if unknown:
        result.unknown_writes = True
    return next_directory


# Directory changes ---------------------------------------------------------------
#
# A write target is relative to the folder its segment runs in. A `cd` earlier
# in the same command moves that folder, so `cd /elsewhere && mv a b` writes
# `/elsewhere/a`. Only a `cd` that is certain to have run, and to name its
# folder, is followed: one in the command's leading `&&` chain (see
# `_Segment.chained`), not run in a pipeline or the background, to a plain path.
# The directory is "" before any `cd`, a path once one is followed, and None,
# for the rest of the command, once a `cd` cannot be followed or a separator
# other than `&&` follows a `cd` that was. Relative targets written from an
# unknown directory are unplaced: the gates count them as inside the project.

# A plain folder change, and its aliases: the only one followed.
FOLLOWED_CHANGE = frozenset({"cd", "chdir", "set-location", "sl"})
# Every folder change. The folder stacks are never followed: `pushd -n` does not
# move, `pushd +1` rotates, and `popd` returns to a folder the command does not name.
CHANGE_DIRECTORY = FOLLOWED_CHANGE | {"pushd", "popd", "push-location", "pop-location"}
# Separators after which the next command runs only if this one succeeded ("":
# the command's end).
AND_THEN = ("&&", "")
DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")
# Characters a shell expands, so a path holding one names no folder for certain.
EXPANDED_CHARS = frozenset("$`%*?[{(")


def _change_directory(name: str, args: list[str], directory: str | None) -> str | None:
    """Return the directory after `name args`, a `cd` certain to have run in
    `directory`, or None when that folder cannot be named."""

    if directory is None or name not in FOLLOWED_CHANGE:
        return None
    path = _change_target(name, args)
    if path is None or not _plain(path):
        return None
    if not _is_absolute(path) and not _explicitly_relative(path):
        return None  # Bash may find a bare name such as `sub` through CDPATH instead.
    return _from_directory(directory, path)


def _change_target(name: str, args: list[str]) -> str | None:
    """The one folder argument of a `cd` or `Set-Location` that has no other
    argument or option (bar `--`, or `-Path`/`-LiteralPath` naming the folder),
    else None. A `-` or `+` argument, such as `cd -` or `cd +1`, is not a folder."""

    rest = args
    if name in ("cd", "chdir") and args[:1] == ["--"]:
        rest = args[1:]
    elif name in ("set-location", "sl") and args:
        option, colon, value = args[0].partition(":")
        if option.lower() in ("-path", "-literalpath"):
            rest = [value] + args[1:] if colon else args[1:]
    if len(rest) != 1 or rest[0][:1] in ("-", "+", ""):
        return None
    return rest[0]


def _explicitly_relative(path: str) -> bool:
    return path in (".", "..") or path.startswith(("./", "../", ".\\", "..\\"))


def _plain(path: str) -> bool:
    """True when `path` names one folder as written: no expansion, and `~`
    only as the user's home (`~-`, `~+`, and `~user` name others)."""

    if any(ch in EXPANDED_CHARS for ch in path):
        return False
    return not path.startswith("~") or path == "~" or path[1] in "/\\"


def _from_directory(directory: str | None, path: str) -> str:
    """`path` as seen from where the command started, when it was written in `directory`."""

    if not directory or _is_absolute(path):
        return path
    return directory.rstrip("/\\") + "/" + path


def _is_absolute(path: str) -> bool:
    return path.startswith(("/", "\\", "~")) or bool(DRIVE_RE.match(path))


# Tokenizing --------------------------------------------------------------------


# Words that open or continue a compound command, which runs its parts only on
# a condition, and `!`, which inverts a command's status: after `! cd x`, an
# `&&` runs exactly when the `cd` failed.
SHELL_KEYWORDS = frozenset(
    {"if", "then", "else", "elif", "do", "while", "until", "for", "select", "!"}
)


class _Segment:
    """One simple command: its words, the files it redirects output into
    (`out_redirects`: those that take its standard output), the bodies of
    heredocs it opened, and `after`, the separator that ended it ("" at the
    command's end). `chained` says it is in the command's leading `&&` chain:
    every separator before it is `&&`, and no compound command, group, or
    script block (`if`, a loop, `case`, `( )`, `{ }`, `$( )`) opened before
    or at it."""

    __slots__ = ("words", "redirects", "out_redirects", "heredocs", "after", "chained")

    def __init__(self) -> None:
        self.words: list[str] = []
        self.redirects: list[str] = []
        self.out_redirects: list[str] = []
        self.heredocs: list[str] = []
        self.after = ""
        self.chained = False


def _segments(command: str) -> list[_Segment]:
    text = command
    segments: list[_Segment] = []
    current = _Segment()
    word: list[str] | None = None
    redirect_next = False  # the next word is a redirect target
    redirect_stdout = False  # that redirect takes standard output
    in_test = False  # inside [[ ]], where < and > compare
    pending: list[tuple[str, bool, _Segment]] = []  # heredocs waiting for their body
    chain = True  # every separator so far is `&&`
    i, n = 0, len(text)

    def end_word() -> None:
        nonlocal word, redirect_next, in_test
        if word is None:
            return
        value = "".join(word)
        word = None
        if redirect_next:
            current.redirects.append(value)
            if redirect_stdout:
                current.out_redirects.append(value)
            redirect_next = False
            return
        if value == "[[":
            in_test = True
        elif value == "]]":
            in_test = False
        current.words.append(value)

    def end_segment(after: str = "") -> None:
        """End the current segment at separator `after`."""

        nonlocal current, in_test, chain
        end_word()
        if current.words or current.redirects or current.heredocs:
            if current.words[:1] and current.words[0] in SHELL_KEYWORDS:
                chain = False
            current.chained = chain
            current.after = after
            segments.append(current)
        if after not in AND_THEN:
            chain = False
        current = _Segment()
        in_test = False

    while i < n:
        c = text[i]
        continuation = c in "\\`" and re.match(r"[\\`]\r?\n", text[i : i + 3])
        if continuation:
            # A bash `\` or PowerShell backtick line continuation, outside quotes.
            end_word()
            i += continuation.end()
        elif c in " \t\r":
            end_word()
            i += 1
        elif c == "\n":
            end_word()
            i += 1
            for delimiter, strip_tabs, owner in pending:
                body, i = _heredoc_body(text, i, delimiter, strip_tabs)
                owner.heredocs.append(body)
            pending = []
            end_segment("\n")
        elif c == "#" and word is None:
            end = text.find("\n", i)
            i = n if end < 0 else end
        elif c == "'":
            end = text.find("'", i + 1)
            end = n if end < 0 else end
            word = (word or []) + list(text[i + 1 : end])
            i = end + 1
        elif c == '"':
            value, i = _double_quoted(text, i + 1)
            word = (word or []) + list(value)
        elif c == "@" and word is None and text[i + 1 : i + 2] in ("'", '"') and (
            text[i + 2 : i + 3] in ("\n", "\r")
        ):
            quote = text[i + 1]
            start = text.find("\n", i) + 1
            end = text.find("\n" + quote + "@", start - 1)
            end = n if end < 0 else end
            word = list(text[start:end].rstrip("\r"))
            i = min(n, end + 3)
        elif c == "\\" and i + 1 < n and text[i + 1] in ESCAPABLE:
            word = (word or []) + [text[i + 1]]
            i += 2
        elif text.startswith("$((", i) or (text.startswith("((", i) and word is None):
            i = _skip_arithmetic(text, i + (1 if c == "$" else 0))
            word = (word or []) + ["0"]
        elif text.startswith("${", i):
            end = text.find("}", i)
            end = n if end < 0 else end
            word = (word or []) + list(text[i : end + 1])
            i = end + 1
        elif text.startswith("<<", i) and not text.startswith("<<<", i) and not in_test:
            end_word()
            match = re.match(r"<<(-?)[ \t]*(['\"]?)([A-Za-z_][\w.-]*)\2", text[i:])
            if match:
                pending.append((match.group(3), bool(match.group(1)), current))
                i += match.end()
            else:
                i += 2
        elif c in "<>" and not in_test:
            fd_prefix = word is not None and all(ch.isdigit() or ch in "&*" for ch in word)
            fd = "".join(word) if fd_prefix and word is not None else ""
            if fd_prefix:
                word = None
            end_word()
            i = _redirect(text, i, c)
            if c == ">" and not text.startswith("&", i):
                redirect_next = True
                redirect_stdout = fd in ("", "1", "&", "*")
            elif text.startswith("&", i):
                i = _skip_fd(text, i)
            else:
                redirect_next = False
                word = None
                # An input redirect's file is read, not written: drop it.
                while i < n and text[i] in " \t":
                    i += 1
                while i < n and text[i] not in " \t\n;|&()<>":
                    i += 1
        elif c == "&" and text.startswith(">", i + 1):
            end_word()
            i += 1  # `&>file`: the `>` is handled next
            word = ["&"]
        elif c == "$" and text.startswith("(", i + 1):
            end_segment("$(")
            i += 2
        elif c in SEPARATORS:
            separator = text[i : i + 2] if text.startswith(("&&", "||"), i) else c
            end_segment(separator)
            i += len(separator)
        else:
            word = (word or []) + [c]
            i += 1
    end_segment()
    return segments


def _double_quoted(text: str, i: int) -> tuple[str, int]:
    out: list[str] = []
    n = len(text)
    while i < n and text[i] != '"':
        if text[i] in "\\`" and i + 1 < n and text[i + 1] in '"\\$`':
            out.append(text[i + 1])
            i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out), i + 1


def _heredoc_body(text: str, i: int, delimiter: str, strip_tabs: bool) -> tuple[str, int]:
    lines = []
    while i < len(text):
        end = text.find("\n", i)
        end = len(text) if end < 0 else end
        line = text[i:end].rstrip("\r")
        i = end + 1
        if (line.lstrip("\t") if strip_tabs else line).strip() == delimiter:
            return "\n".join(lines), i
        lines.append(line)
    return "\n".join(lines), len(text)


def _skip_arithmetic(text: str, i: int) -> int:
    depth = 0
    while i < len(text):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return i


def _redirect(text: str, i: int, c: str) -> int:
    i += 1
    if c == ">" and i < len(text) and text[i] in ">|":
        i += 1
    return i


def _skip_fd(text: str, i: int) -> int:
    i += 1  # the `&` of `>&1` or `2>&-`
    while i < len(text) and (text[i].isdigit() or text[i] == "-"):
        i += 1
    return i


# Reading a segment ------------------------------------------------------------


def _resolve(words: list[str]) -> tuple[str, str, list[str]]:
    """Return the real command word (bare and lowercased), as written, and its arguments."""

    i = 0
    while i < len(words):
        word = words[i]
        name = _bare(word)
        if re.match(r"^[A-Za-z_]\w*=", word) or word in ("{", "}", "!") or word in SHELL_KEYWORDS:
            i += 1
        elif name in WRAPPERS:
            i += 1
            takes_value = WRAPPERS[name]
            while i < len(words) and (words[i].startswith("-") or "=" in words[i]):
                i += 2 if words[i] in takes_value else 1
            if name == "timeout" and i < len(words):
                i += 1  # the duration
        elif name == "cmd" and i + 1 < len(words) and words[i + 1].lower() in ("/c", "/k"):
            i += 2
            while i < len(words) and words[i].startswith("/") and len(words[i]) == 2:
                i += 1
        else:
            return name, word, words[i + 1 :]
    return "", "", []


def _bare(word: str) -> str:
    name = word.replace("\\", "/").rsplit("/", 1)[-1].lower()
    for suffix in (".exe", ".cmd", ".bat"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _positional(args: list[str]) -> list[str]:
    out = []
    after_dashes = False
    for arg in args:
        if arg == "--" and not after_dashes:
            after_dashes = True
        elif after_dashes or not arg.startswith("-"):
            out.append(arg)
    return out


def _ps_paths(args: list[str]) -> list[str]:
    """PowerShell-style arguments: -Path values first, then positional ones."""

    named, positional = [], []
    i = 0
    while i < len(args):
        arg = args[i]
        low = arg.lower()
        if low.startswith("-") and len(arg) > 1:
            param, _, attached = low.partition(":")
            if param in PS_VALUE_PARAMS:
                value = args[i][len(param) + 1 :] if attached else (
                    args[i + 1] if i + 1 < len(args) else ""
                )
                if param in PS_PATH_PARAMS and value:
                    named.append(value)
                i += 1 if attached else 2
                continue
            i += 1
            continue
        positional.append(arg)
        i += 1
    return named + positional


def _skip_options(args: list[str], takes_value: set[str]) -> list[str]:
    i = 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if args[i] in takes_value else 1
    return args[i:]


def _edits_in_place(args: list[str]) -> bool:
    for arg in args:
        if arg == "--in-place" or arg.startswith("--in-place="):
            return True
        if arg.startswith("-") and not arg.startswith("--") and "i" in arg[1:].split(".", 1)[0]:
            return True
    return False


def _in_place_files(name: str, args: list[str]) -> list[str]:
    script_given = any(a in ("-e", "-f", "--expression", "--file") or (
        a.startswith("-") and not a.startswith("--") and a[-1:] in "ef") for a in args)
    files, skip_next = [], False
    for arg in args:
        if skip_next:
            skip_next = False
            continue
        if arg in ("-e", "-f", "--expression", "--file") or (
            arg.startswith("-") and not arg.startswith("--") and arg[-1:] in "ef"
        ):
            skip_next = True
            continue
        if not arg.startswith("-"):
            files.append(arg)
    return files if script_given or name == "perl" else files[1:]


def _download_target(name: str, args: list[str]) -> tuple[str | None, bool]:
    """Return (output file or None, whether it writes) for a download command.

    curl writes with `-o <file>` (also at the end of a cluster such as
    `-sSLo <file>`) or `-O`; wget writes by default, to `-O <file>` when given;
    PowerShell's Invoke-WebRequest, and its `curl` and `wget` aliases, write
    with `-OutFile <file>`.
    """

    out_flag = "O" if name == "wget" else "o"
    for i, arg in enumerate(args):
        value = args[i + 1] if i + 1 < len(args) else None
        if arg.lower() == "-outfile":
            return value, True
        option, eq, attached = arg.partition("=")
        if option in ("--output", "--output-document"):
            value = attached if eq else value
            return (None, False) if value == "-" else (value, True)
        if arg.startswith("-") and arg.endswith(out_flag + "-"):
            return None, False  # `wget -qO-`: to stdout
        if arg.startswith("-") and not arg.startswith("--") and arg[1:].isalpha():
            if arg.endswith(out_flag):
                return (None, False) if value == "-" else (value, True)
            if name == "curl" and "O" in arg:
                return None, True
        if arg in ("--remote-name", "--remote-name-all"):
            return None, True
    return None, name == "wget"


def _git_subcommand(args: list[str]) -> tuple[str, list[str]]:
    index = 0
    while index < len(args) and args[index].startswith("-"):
        index += 2 if args[index] in GIT_GLOBAL_WITH_VALUE else 1
    if index >= len(args):
        return "", []
    return args[index].lower(), args[index + 1 :]


def _git_writes(sub: str, rest: list[str]) -> tuple[list[str], bool]:
    """Return (files written, whether others are written that the command does not name)."""

    if sub in GIT_UNKNOWN_TARGET_SUBCOMMANDS:
        return [], True
    if sub in ("mv", "rm"):
        return _positional(rest), False
    if sub == "restore":
        return [a for a in _positional(_drop_values(rest, {"-s", "--source"}))], False
    if sub == "checkout":
        if "--" in rest:
            return rest[rest.index("--") + 1 :], False
        if any(a in ("-b", "-B", "--orphan") for a in rest):
            return [], False
        positional = _positional(rest)
        if "--theirs" in rest or "--ours" in rest:
            return positional, False  # One side of a conflict: every positional is a path.
        # `git checkout <rev> <path>...` restores files; `git checkout <branch>` does not.
        return positional[1:], False
    if sub == "reset":
        return [], "--hard" in rest
    if sub == "stash":
        return [], bool(rest) and rest[0] in {"pop", "apply"}
    return [], False


def _git_prints_changes(sub: str, rest: list[str]) -> bool:
    """True when `git <sub> <rest>` prints changes' content: a diff or show
    without a listing-only option, a log, whatchanged, or stash show with a
    patch option, or format-patch to stdout."""

    if any(GIT_SILENT_FLAGS_RE.fullmatch(a) for a in rest):
        return False
    patch = any(GIT_PATCH_FLAGS_RE.fullmatch(a) for a in rest)
    if sub == "stash":
        return rest[:1] == ["show"] and patch
    if sub in GIT_PATCH_BY_DEFAULT:
        listing = any(a == "-s" or a.startswith(GIT_NO_PATCH_FLAGS) for a in rest)
        return patch or not listing
    if sub in ("log", "whatchanged"):
        return patch
    return sub == "format-patch" and "--stdout" in rest


def _drop_values(args: list[str], takes_value: set[str]) -> list[str]:
    out, skip = [], False
    for arg in args:
        if skip:
            skip = False
        elif arg in takes_value:
            skip = True
        else:
            out.append(arg)
    return out


# Checks -------------------------------------------------------------------------


def _is_check(name: str, original: str, args: list[str]) -> bool:
    if not name:
        return False
    if name in CHECK_TOOLS:
        return True
    if name in SUBCOMMAND_CHECKS and args[:1] and args[0].lower() in SUBCOMMAND_CHECKS[name]:
        return True
    if name in SCRIPT_RUNNERS:
        rest = args[1:] if args[:1] and args[0] in ("run", "run-script") else args
        return bool(rest) and bool(CHECK_WORD_RE.fullmatch(rest[0]) or CHECK_WORD_RE.search(rest[0]))
    if name in TARGET_RUNNERS:
        return any(CHECK_WORD_RE.fullmatch(a) for a in args if not a.startswith("-"))
    if name in COMMAND_RUNNERS:
        sub = COMMAND_RUNNERS[name]
        rest = args
        if sub:
            if not args or args[0] != sub:
                return False
            rest = args[1:]
        rest = _skip_options(rest, {"--with", "--python", "-p", "--extra", "--group",
                                     "--package", "--project", "--directory", "-e", "--env"})
        return bool(rest) and _is_check(_bare(rest[0]), rest[0], rest[1:])
    if name in INTERPRETERS:
        if "-m" in args:
            index = args.index("-m")
            return index + 1 < len(args) and args[index + 1] in CHECK_MODULES
        for flag in ("-File", "-file", "-f"):
            if flag in args and args.index(flag) + 1 < len(args):
                return _is_check_script(args[args.index(flag) + 1])
        scripts = [a for a in args if not a.startswith("-")]
        return bool(scripts) and _is_check_script(scripts[0])
    if "/" in original.replace("\\", "/") or "." in name:
        return _is_check_script(original)
    return False


def _is_check_script(path: str) -> bool:
    stem = path.replace("\\", "/").rsplit("/", 1)[-1].rsplit(".", 1)[0]
    return bool(CHECK_WORD_RE.search(stem))


# Commit messages ------------------------------------------------------------------

SUBSTITUTED_HEREDOC_RE = re.compile(
    r"^\$\(\s*cat\s*<<-?\s*(['\"]?)([A-Za-z_][\w.-]*)\1[ \t]*\r?\n(.*?)\r?\n[ \t]*\2[ \t]*\r?\n?\s*\)\s*$",
    re.DOTALL,
)
# Short options of `git commit` that take a value.
COMMIT_VALUE_FLAGS = "mFcCt"


def _commit_message(args: list[str], heredocs: list[str]) -> str | None:
    """Return the message a `git commit` segment carries inline, or None.

    Several `-m` options join as paragraphs, as git joins them, and a cluster
    such as `-am` counts. A heredoc fed to `-F -`, or inside
    `-m "$(cat <<'EOF' ... EOF)"`, gives its body. A message in a file, reused
    from another commit (`-c`, `-C`), or written in an editor is not in the
    command, so the answer is None.
    """

    parts: list[str] = []
    stdin = False
    i = 0
    while i < len(args):
        arg = args[i]
        nxt = args[i + 1] if i + 1 < len(args) else None
        if arg == "--":
            break
        if arg.startswith("--"):
            option, eq, value = arg.partition("=")
            if option in ("--message", "--file", "--reuse-message", "--reedit-message"):
                if not eq:
                    value, i = nxt or "", i + 1
                if option == "--message":
                    parts.append(value)
                elif option == "--file" and value == "-":
                    stdin = True
                else:
                    return None
        elif arg.startswith("-") and len(arg) > 1:
            for k, flag in enumerate(arg[1:], 1):
                if flag not in COMMIT_VALUE_FLAGS:
                    continue
                value = arg[k + 1 :]
                if not value:
                    value, i = nxt or "", i + 1
                if flag == "m":
                    parts.append(value)
                elif flag == "F" and value == "-":
                    stdin = True
                elif flag in "FcC":
                    return None
                break
        i += 1
    if stdin:
        return heredocs[0].strip("\n") if heredocs else None
    resolved = []
    for part in parts:
        match = SUBSTITUTED_HEREDOC_RE.match(part)
        if match:
            resolved.append(match.group(3))
        elif "$(" in part:
            return None  # Another command substitution: not knowable.
        else:
            resolved.append(part)
    return "\n\n".join(resolved) if resolved else None
