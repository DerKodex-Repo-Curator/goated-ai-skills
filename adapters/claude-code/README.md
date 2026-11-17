# GOATED Adapter For Claude Code

An optional set of Claude Code hooks that holds writes, spawns, and commands
until the GOATED router and the skills its route requires have loaded since
the last compaction. It also holds commits, pull requests, spawns, design changes,
security-sensitive edits, and writes during a merge conflict until the skill
that owns each has loaded, and
holds the end of a code-changing turn until it has fresh proof. It enforces
the portable contracts in
`skills/agent-workflows/using-goated-ai-skills/SKILL.md`, `stack/AGENTS.md`,
`stack/fixtures/markers/README.md`, and the trigger each skill states; it adds
no rules of its own
([ADR 0003](../../docs/adr/0003-opt-in-framework-enforcement-adapters.md)).

Skills work the same without it. Install it only if you want enforcement.

## Requirements

- Claude Code with command hooks. The snippet uses the exec form (`command`
  plus `args`); see [Shell-form alternative](#shell-form-alternative) if your
  version lacks it.
- Python 3.11 or later on `PATH`. CI tests 3.11 and 3.14. The adapter uses
  only the standard library, so it needs no packages.

## Install

1. Copy this `claude-code/` folder to a stable place, for example next to your
   installed GOATED distribution as `<goated-root>/adapters/claude-code/`.
   Copy the whole folder: `goated_hook.py` imports the `goated_adapter/`
   package beside it. The [`reference-reads`](#registry-references) gate
   reads the installed registry two folders up,
   `<goated-root>/stack/goated-stack.yaml`; if the adapter lives elsewhere,
   set `GOATED_ADAPTER_REGISTRY` to the registry's path. A missing registry
   at the default path turns that gate off quietly; one that does not parse,
   or a path the variable names with no file there, turns it off with a
   warning.
2. Open [`settings.snippet.json`](settings.snippet.json) and replace every
   `<adapter-dir>` with the folder's absolute path. Forward slashes work on
   Windows too.
3. Use `python` as the command on Windows and `python3` on macOS and Linux, or
   give the full path to an interpreter.
4. Merge the four entries under `hooks` into a Claude Code settings file:
   `~/.claude/settings.json` for every project, or a project's
   `.claude/settings.json` for one project. If the file already has a `hooks`
   object, add these entries next to the existing ones rather than replacing
   it.
5. Start a new Claude Code session.

To check the install, start a session and ask the agent to run any shell
command before it has loaded `using-goated-ai-skills`. The call should be
held with a reason that begins `goated-hold: router-first | strict`. If the
GOATED shared policy is not loaded,
the first session start also shows a one-time notice; the
[install guide](../../docs/install.md#load-the-shared-policy-in-claude-code)
shows how to load it.

### Shell-form alternative

Without exec-form support, use a shell command per entry instead of
`command` plus `args`:

```json
{ "type": "command", "command": "python \"<adapter-dir>/goated_hook.py\"" }
```

This works the same but adds the shell's start-up to every call: about 27 ms
per call with Git Bash on the Windows machine measured below.

## Disable

Remove the four adapter entries from the settings file, or move them to a
file Claude Code does not load. Start a new session to be sure the change
applies. Claude Code's `"disableAllHooks": true` also stops the adapter, along
with every other hook you have.

## Remove

1. Remove the four adapter entries from the settings file.
2. Delete the copied `claude-code/` folder.
3. Delete the state folder `goated-claude-code-adapter/` (see [State](#state)).

Skills keep working unchanged.

## What It Holds

The routing rules live in [`goated_adapter/gates.py`](goated_adapter/gates.py)
and the action and closeout rules in
[`goated_adapter/actions.py`](goated_adapter/actions.py). There are two kinds
of hold:

- **strict**: clears only on proof of use or a typed user override;
- **justified-skip**: also clears on a `goated-skip: <skill>: <reason>` line,
  with a reason of three or more words, in the current turn. The reason stays
  in the transcript, where the skill-usage mod reads it.

Route and skip lines are read from the agent's reply text and
from one field
of some built-in tool calls: the `description` of a `Bash`, `PowerShell`,
`Agent`, or `Task` call, and the `args` of a `Skill` call, such as
`Skill(using-goated-ai-skills, args: "goated-route: direct")`. Other tools,
MCP tools included, carry no line, because their `description` is often the
payload, such as an issue or merge-request body. Claude Code can
store reply text as a summary that drops the line (see
[Known Limits](#known-limits)), but it keeps a call's input as written, and
the hook sees the input of the call it judges. A line in a call counts from
that call on, so it covers the call itself, and otherwise follows the same
rules as a line in reply text: the same grammar, outside fenced blocks, the
last route line wins, route lines with no write or spawn between them are one
task, and a line counts only in its own turn and agent. No other field counts,
so file text, edit text, and commands never carry a line, and no typed
[override](#user-overrides) is ever read from a call.

A session started from another session gets that session's brief as its
first prompt. A valid route line on its own line anywhere in that brief,
outside fenced blocks and `<system-reminder>` blocks, is the first turn's
route, as if the new session had written it first; when the brief has
several, the last one wins. It meets `router-first`, as a subagent's parent
brief does, until a prompt you type opens a turn: from then on the router
must load, as in any session. The route's `requires:` skills must still load
in the new session before its first write (`pipeline`), and a later route
line in the turn corrects it as usual. While the brief's route counts, a
`standard` or `full` route also requires orientation
when Claude Code can find `session-start-progressive-disclosure` (a user,
project, or plugin skill): the router selects orientation on such a route
from a brief, and the spawn-brief template says the new session orients
before its first write by reading the sources its brief names or by loading
that skill. Either meets it: the skill loads, or Read calls of three
distinct files finish, anywhere, since the session started or the last
compaction; reads count across turns as loads do, and a failed Read does
not count. The route line never names the skill,
so leaving it out of a corrected line does not drop it; only a corrected
`goated-route: direct` line or a `lightweight` route line does. A typed prompt
or a compaction ends the brief's route, and the requirement with it, so a
typed `skip session-start-progressive-disclosure` is never needed. When an API
error makes the app resend the turn as a host-written `Try again` prompt,
that prompt continues the
turn, with its route and overrides. Only the session's first prompt counts,
and only in the shape the
desktop app records a brief: text opening `Background (from the session that
started this one)` or `Task (from the session that started this one)` after
any `<system-reminder>` blocks, with `turnOrigin` `host_synthetic` and no
`origin`. A route line in a typed prompt, a later prompt, or another
session's message never counts, and a brief never carries an override. The
`handoff` skill's spawn-brief template says where the parent puts the line.
A brief with a route line also marks the session as briefed, for good (one with none does not): typed prompts and
compactions do not end that, and a briefed session meets no closeout Review
item (see the closeout table below).

| Gate | Kind | Holds | Clears when |
| --- | --- | --- | --- |
| `router-first` | strict | Writes, spawns, and commands while the router has not loaded in this session, or since the last compaction; a command made only of [plain reads](#plain-reads) passes, and so does a write whose every file is a scratch file outside the project (see below) | `using-goated-ai-skills` loads; or the session's first prompt is a brief with a route line (see above), until a typed prompt opens a turn |
| `route-line` | strict | The first write or spawn after each user prompt until the current turn has a valid `goated-route:` line; also `goated-route: continue` when [missing or reset state](#failing-open) lost the task; a write whose every file is a scratch file outside the project (see below) passes | A valid route line appears in the turn |
| `pipeline` | strict | Writes and spawns while a `requires:` skill of the current task has not loaded, or, in a session routed by its brief, on a `standard` or `full` route, orientation is unmet while `session-start-progressive-disclosure` is installed (see above); a spawn of a [read-only subagent](#plain-reads) passes, and so does a write whose every file is a scratch file outside the project (see below) | Each listed skill loads, or a corrected route line drops it; the brief's orientation skill loads or three distinct files are read, or a corrected `goated-route: direct` or `lightweight` route line drops it |
| `commit` | strict | A `git commit` command (not `--dry-run`), or an MCP tool that records a commit, named `…__push_files`, `…__create_or_update_file`, `…__delete_file`, `…__git_commit`, `…__create_commit`, `…__commit_changes`, or `…__commit` | `commit-message` [counts as loaded](#loads), and an inline message (or the tool's `message`) passes the [content check](#content-checks); then a [change read](#change-reads) after the last change to any project file, before or after the load; an MCP tool skips that read when the turn changed no project file. Once these are met, the commit meets the [closeout](#closeout-at-commit) |
| `pull-request` | strict | `gh pr create` or `gh pr new`, `glab mr create` or `glab mr new`, or an MCP tool named `…__create_pull_request` or `…__create_merge_request` | `pr-description` [counts as loaded](#loads); then a [change read](#change-reads) after the last change to any project file, before or after the load; an MCP tool skips that read when the turn changed no project file |
| `pr-review` | justified-skip | A pull-request command or tool the `pull-request` gate holds, once that gate passes, when the pull request is [large](#large-pull-requests): 400 or more changed lines of non-test code against its base | `standards-and-spec-review` [counts as loaded](#loads); then a [change read](#change-reads) after the load and the last change to any project file; an MCP tool skips that read when the turn changed no project file |
| `spawn` | strict | Starting an agent or session with a brief, except a [read-only subagent](#plain-reads) | `handoff` loads and `references/spawn-brief.md` is read, or `subagent-driven-development` loads and its implementer or reviewer prompt is read, each in this turn or an earlier one since the last compaction (see [Loads](#loads)); and the brief, on every spawn, passes the [content check](#content-checks) |
| `design` | justified-skip | The turn's first write adding five or more lines to a non-test code file inside the project folder (or any such write while the skill does not count as loaded). A test file never triggers it and is not counted when finding the turn's first such write: in TDD the test comes first and the design happens in the code after it | `software-design-principles` [counts as loaded](#loads), and every [reference the edit's signals select](#design-references) has been read since the last compaction |
| `design-reads` | justified-skip | Any later write to a code or configuration file inside the project folder, once `software-design-principles` [counts as loaded](#loads), whose [signals](#design-references) select a reference not read since the last compaction; a test file edit selects `coding.md` only when it creates the file or adds twenty or more lines. The hold names each file and what selected it | Each required reference is read with the Read tool |
| `reference-reads` | justified-skip | A write by a write tool or a shell command that is not a check, inside the project folder or, for a `gate-fires` signal, anywhere, that fires a signal the installed registry declares for a reference of a skill that [counts as loaded](#loads) (see [Registry references](#registry-references)); `tdd`'s `test-design.md` is required by a test edit that creates the file or adds twenty or more lines, and a shell write meets only the signals that need no added text. The hold names each file by its path under the skill, `<skill>/references/<file>`, and what selected it | Each reference it names is read with the Read tool, in this turn or an earlier one since the last compaction; or a skip line naming its skill, for the turn |
| `review-intake` | justified-skip | A write, by a write tool or a shell command, to a code file inside the project folder, once a [reviewer subagent](#reviewer-subagents) started by `Agent` or `Task` has reported in the turn: its result arrived, or, started in the background, its completion did. A held or failed spawn, any other brief, and a side session trigger nothing. A test file is held like other code; a docs or config file is not | `receiving-code-review` [counts as loaded](#loads), in this turn or an earlier one since the last compaction; or a skip line naming it, for the turn |
| `security` | justified-skip | A write, by a write tool or a shell command, to a security-sensitive path inside the project folder: dependency manifests and lockfiles (`requirements*.txt` included), `.env` and key files, files named for secrets, credentials, or tokens, auth, session, and permission code, migrations and schemas, CI, container, and deployment files. A sensitive word counts only when it stands alone in the path, so `tokenizer.py` and `author.py` are not held, while `api_token.py` and `userAuth.ts` are | `code-security-review` [counts as loaded](#loads) |
| `scripted-edit` | justified-skip | A shell command whose [inline script](#inline-scripts) (`python -c`, `node -e`, a heredoc on `python -`) writes a code file inside the project folder, test files included, or writes a file it names only at run time, which counts as code. The hold asks for the change to be made with a file edit tool, where the `design`, `design-reads`, and `reference-reads` gates can judge it; a script suits only a mechanical rewrite across many files. It comes after the `security` and `review-intake` gates for the same file. Once cleared, the script runs and its files count as changed | A `goated-skip: software-design-principles: <reason>` line in the turn, or the typed override `skip software-design-principles`; loading the skill does not clear it |
| `conflict-resolution` | justified-skip | A write while a merge conflict is open in the turn: an `Edit` or `MultiEdit` whose old text has a `<<<<<<<` or `>>>>>>>` marker at a line start; a write, by a write tool or a shell command such as `git checkout --theirs`, to a file a Read in the turn showed with such a marker; or any write after a git merge, rebase, cherry-pick, revert, or pull whose result in the turn reported a conflict. A finished abort, quit, continue, or skip of that operation, or a finished commit, ends the conflict and drops the Reads before it. Only the turn is read, not the repository, so a conflict opened in an earlier turn is caught only by markers the turn shows: an edit whose old text spans only `=======` and one side, in a file not read this turn, is not held, because `=======` alone is also a heading underline. A conflicting stash pop or apply is not held | `resolving-merge-conflicts` [counts as loaded](#loads) |
| `repeated-failure` | justified-skip | A write, by a write tool or a shell command, once one check command (as the closeout's Proof item recognises checks) has failed twice in a row in the turn. A shell command is held when any of its simple commands writes and is not itself a check, so `sed -i … && pytest` and `pytest \| tee out.txt` are held, while `pytest > out.txt` is a rerun. "The same check" is the same command text run from the same folder, whitespace aside. A leading `cd` to a folder joined by `&&` or `;` names the folder: `cd pkg_a && pytest -q` and `cd pkg_b && pytest -q` are two checks, and `cd <the session folder> && pytest -q` is `pytest -q`. The command text is compared without a trailing pipe into output filters (`tail`, `head`, `grep`, `findstr`, `more`, `less`, `tee`, `Select-Object`, `Select-String`, `Out-Host`, `Out-String`) or a `2>&1` before it; so `pytest -q \| tail -20` and `pytest -q \| tail -40` are one check, and a narrowed rerun such as one test file of a failing suite is another. A piped run fails by what it prints (`N failed`, `N errors`, `FAILED (`, `FAIL`, `npm ERR!`, `error TS…`, `test result: FAILED`, and the like), since the exit code is the filter's; any other run fails by its exit code. A run whose only failures are test modules that could not load a missing module or name neither adds to the count nor resets it, whether or not it looks failed, since in TDD the first red run often fails because the module under test does not exist yet. Only each runner's own report counts: pytest's `ERROR collecting` section showing `ImportError while importing test module` or ending in an `ImportError` or `ModuleNotFoundError`; unittest's `_FailedTest` error ending in one of those; jest's `Test suite failed to run` with `Cannot find module`. A run counts as usual when it also shows a failure in a test that ran (`1 failed, 1 error`), when a module that is there fails to load (a `SyntaxError` or `NameError`: the edit-and-crash loop the gate exists for), or when a test only prints such text. These miss, toward holding: output cut before the runner names the cause (`pytest -q \| tail -3`), ts-jest's `TS2307`, and vitest's `Failed to load url`. The table is `LOAD_ERROR_SIGNS` in `actions.py`. Two kinds of failed run also neither add to the count nor reset it. One is the first run of a check after a finished write to a test file in the turn, by a write tool or a shell command: in TDD that run is meant to fail. A held or failed write excuses nothing, and only that first run is excused. The other is a run whose runner reports fewer failed and errored tests than the check's run before it: pytest's summary line (`3 failed, 1 error in 0.2s`), unittest's `FAILED (failures=…, errors=…)`, jest's `Tests:` line, and cargo's `test result: FAILED`. When either run's count cannot be read, the run counts: output with no summary, a runner that prints no count (`go test`), two runners' summaries in one run, a summary counting no failure (`Tests: 0 total`), or a run showing a test module or suite that could not load (pytest's `ERROR collecting` or `Interrupted: 1 error during collection`, unittest's `_FailedTest`, jest's `Test suite failed to run`), whose tests are missing from its count. The hold shows the check without its `cd`, so `cd "<long path>" && pytest -q` shows `pytest -q`. A pass of the check resets its count; other commands between runs do not. A call that never ran does not count: one the adapter or another hook held, one refused at a permission prompt, or one interrupted | `diagnose` [counts as loaded](#loads) |
| `closeout` | justified-skip | A commit the `commit` gate lets through, or the end of the turn (a `Stop` hook), in a turn that changed code, that changed a security-sensitive file, or that changed setup | Every item below is met or skipped |

The closeout items, each judged against the turn's last code change. A code
change is a write tool's file, or a file a shell command writes (its redirect
target, copy destination, or removed, moved, or edited file), inside the
project folder; a scratch or temp file elsewhere does not count. The `design`,
`design-reads`, `reference-reads`, `review-intake`, `scripted-edit`, and `security` gates use the same rule, so a scratch script outside the
project is not held, except by a `reference-reads` signal of the
`gate-fires` kind. The `conflict-resolution` and `repeated-failure` gates
hold a write wherever its file is, since a worktree with a conflict, or the
code a failing check runs, may sit outside the project folder.
The routing gates `router-first`, `route-line`, and `pipeline` let a write
through when every file it writes is a scratch file, such as a copy into a
temp folder: outside the project by the rule below, inside no git checkout
(no folder at or above it holds a `.git` file or folder), outside your
`~/.claude` folder, and not a folder that holds the project. When any of that
cannot be checked, the file is not scratch. So a write into another repo,
such as a worktree under the temp folder or a sibling checkout, or into
Claude's settings, is routed. A shell command passes only when every simple
command in it is a [plain read](#plain-reads), a `cd`, a command that only
writes, copies, moves, or removes the files it names (`cp`, `mv`, `rm`,
`touch`, `tee`, `ln`, and their PowerShell forms; not `install` or
`rename`), or a plain read with its output redirected into a file, so
`cp a /tmp/x && cat f` passes and `cp a /tmp/x && ./script.sh` is held. A
write with any file that is not scratch, or whose files cannot be named
(`git apply`), is held as before, and so are spawns and commands that write
nothing.

**A file counts as outside the project only when the adapter is certain.**
When in doubt, it is inside. The project's folders are `CLAUDE_PROJECT_DIR`
when Claude Code sets it, the session's working folder (the hook input's
`cwd`), and the nearest folder at or above either that holds a `.git` entry,
so a session that changed folder below its checkout still counts the whole
checkout. A file is outside only when it is under none of them in any way the
path can be read, with symbolic links and junctions resolved too:

- A relative path is taken from the working folder; a shell write target is
  taken from a `cd` before it only as [Shell writes](#shell-writes) says, and
  counts as inside when its folder is unknown.
- A leading `~` or `~/` is your home folder, read both as your profile folder
  and as `HOME`. On Windows, 8.3 short names such
  as `PROGRA~1` are expanded where the folders exist.
- On Windows, a one-letter top folder naming a drive that exists is Git
  Bash's name for that drive (`/c/work` is `C:/work`); it may also be a folder
  on any drive the project's folders use, and each reading is checked. The
  same applies to a project folder given in Git Bash form. On Windows,
  `/tmp/x` is also read as `x` in your temp folder, where Git Bash mounts
  `/tmp`: under `TMP` and under `TEMP`, each that is set, and both must be
  absolute Windows paths, or `/tmp/x` counts as inside. Any other path rooted
  with no drive, such as `/etc/x`, counts as inside: Git Bash mounts `/` as
  its install folder, and you may add mounts of your own.
- These count as inside, since the adapter does not read them: a path holding
  a variable or glob (`$`, `%`, a backtick, `*`, `?`), `~-`, `~+`, or another
  user's `~name`, device paths (`\\?\`, `//?/`, `\\.\`), network paths
  (`\\server\share`), a drive-relative path such as `C:x`, and, on Windows, a
  folder or file name ending in a dot or space.

A shell write whose files the command does not name (`git apply`, `patch`, a
download without an output name, a .NET call) counts as a change to non-test
code, wherever it runs, since where its files are cannot be said. Code a
subagent changed counts too, at the point the parent spawned it; if the subagent ran a
check after its own last change, that change is already proved.

| Item | Needed when | Met by | Skip line names |
| --- | --- | --- | --- |
| Proof | A change not already proved | A check command run after the last code change: a test runner, linter, type checker, or build tool (`pytest`, `python -m unittest`, `npm test`, `cargo test`, `go vet`, `tsc`, `make check`, and the like, also through `uv run` or `npx`), or a script whose name says test, check, lint, verify, validate, or build (`scripts/validate_skills.py`). The check may be a later call, or later in the same shell command as the write (`cp a.py src/a.py && pytest`): every command from the write to the check must be joined by `&&`, `;`, or a newline, none of them an `exit`, `return`, or the like, and neither inside a branch, loop, function, or group (`if`, `( )`, `{ }`); the check must not run in the background (`pytest &`), though a pipe or `\|\|` after it is fine (`pytest 2>&1 \| tee log.txt`). A code file written after the check, or by a .NET call (`[IO.File]::WriteAllText`) anywhere in the command, is not proved by it; another file written after it, such as a log, does not matter. Inline interpreter code (`python -c`, `python -Bc`, `node -pe`, `perl -e`) is not a check; a shell's inline command line (`bash -c`, `pwsh -Command`) is read as a command line, so `bash -c 'npm test'` is a check and `bash -c 'echo tests ok'` is not | `verification-before-completion` |
| Unfinished work | The last check after the change failed | `handoff` counts as loaded | `handoff` |
| Docs | A code file outside the tests changed | `doc-sync` counts as loaded, and a [change read](#change-reads) follows the last code change, before or after the load | `doc-sync` |
| Design red flags | `software-design-principles` loaded in the turn, or counts as loaded and the turn made an edit the `design` gate triggers on (five or more lines added to a non-test code file), so a later turn of small edits meets no Design item | `software-design-principles/references/red-flags.md` is read after the last code change that is not [comment-only](#comment-only-edits), then a [change read](#change-reads) after that read and that change. After a red-flags read in the turn that follows code changes adding five or more lines, later code changes that add fewer than five lines in total, comment-only ones aside, need no second red-flags read, only the change read after the last of them; a read before any such change covers no later change; a change whose added lines are unknown, a shell write or a subagent's, counts as five or more. The item repeats the question `red-flags.md` ends with (name one input that would break this change, and say what happens); no answer is checked | `software-design-principles` |
| Review | The turn changed code, the session was not started from a brief, and the branch's work is [large](#large-branches): 400 or more changed lines against its base in code files outside test paths, counting committed, staged, unstaged, and untracked files that git does not ignore. A session whose first prompt was a brief with a route line from the session that started it meets no Review item for the whole session, typed prompts and compactions included: the starting session reviews the work when it inspects the report and the changed paths (`handoff`'s spawn-brief template). Missing state counts as not briefed | A [reviewer subagent](#reviewer-subagents) that finished after the last code change; or `standards-and-spec-review` counts as loaded and a [change read](#change-reads) follows the load and the last code change | `standards-and-spec-review` |
| Verification | The turn changed code or a security-sensitive file, and one of these holds: the task's route is `full`; a subagent the turn spawned changed code; a security-sensitive file changed; or the branch's work is [large](#large-branches) | `verification-before-completion` counts as loaded | `verification-before-completion`, the Proof item's skip line, so one line answers both |
| Security | `code-security-review` counts as loaded and a security-sensitive file (the `security` gate's paths, code or not) changed | A [change read](#change-reads) after the load and the last sensitive change | `code-security-review` |
| Setup | The turn installed or added a dependency or tool by a command that names a package, in the project or globally, or wrote an env or settings file (see below) | `setup-scribe` counts as loaded, the load before or after the change | `setup-scribe` |

The Setup item is not judged against code changes. A **package install** is a
finished `npm`, `pnpm`, or `bun` `add` or `install`, `yarn add`, `pip install`
(also `python -m pip`), `uv add`, `uv pip install`, `uv tool install`,
`poetry add`, `pipx install`, `conda install`, `cargo add` or `install`,
`go get` or `install`, `gem install`, or `brew`, `apt`, `apt-get`, `winget`,
`choco`, or `scoop` `install`, or `yarn global add`, that names a package. A
bare `npm install`, `pip install -r requirements.txt`, or `pip install -e .`
restores what a manifest records or installs a local path, so it does not
count; a URL, such as `pip install -e git+https://…`, is a package. Each
manager's options that take a value (`--filter`, `--workspace`, `--python`,
`--file`, `--prefix`, `--registry`, `--index-url`, `--target`, and the like;
`PACKAGE_MANAGERS` in `shell.py`) are skipped with their value, so
`pnpm install --filter web` names no package. An **env or settings file** is
`.env` or `.env.*` (`.env.example` included), or a `settings*.json` under
`.claude/` or `.vscode/`, written by a write tool or a shell command. A
**global, machine, or per-user install** (`npm`, `pnpm`, or `bun` with `-g`
or `--global`, `npm --location=global`, `pip install --user`,
`yarn global add`, `uv tool install`, `pipx install`, `cargo install`,
`go install`, `gem install`, every `brew`, `apt`, `apt-get`, `winget`,
`choco`, or `scoop` install, and any install run under `sudo`;
`GLOBAL_INSTALLS` and `GLOBAL_OPTIONS` in `shell.py`) counts wherever it
runs. Any other package install counts unless it goes into a folder
certainly outside the project. That folder is the one a folder option names
(`npm --prefix`, `pnpm --dir` or `-C`, `yarn` or `bun --cwd`,
`uv --project` or `--directory`, `poetry -C` or `--directory`, `go -C`;
`FOLDER_OPTIONS` in `shell.py`), else the one it runs in: one a `cd` in the
same command moved to, as a write's folder is followed (see
[Writes](#what-it-holds)). So `cd /tmp/x && pip install requests` does not
count, `cd /tmp/x && npm install --prefix <project> lodash` does, and so does
one after a `cd` the adapter cannot follow (`cd "$TMPDIR" && …`,
`cd sub && …`). An env or
settings file counts only
inside the project, by the same rule as code changes, so a scratch folder's
`.claude/settings.json` does not, and neither do global settings such as
`~/.claude/settings.json`, unless the project holds your home folder. A
subagent's installs and writes count
toward the parent's closeout; that subagent's own `setup-scribe` load or skip
line meets them, as the parent's does.

Two limits: an install inside `bash -c "…"` or another wrapped command string
is not seen, as with every shell reading here; and an install whose failure
the command hides (`npm install foo || true`) still counts, since the adapter
sees only the whole command's result.

- **Writes** are `Edit`, `Write`, `MultiEdit`, and `NotebookEdit`, and a
  `Bash` or `PowerShell` command that writes files (see
  [Shell writes](#shell-writes)). **Spawns** are `Agent` (or `Task`, its name
  in older Claude Code versions), `mcp__ccd_session__start_session`, and
  `mcp__ccd_session__hand_off_to_session`; they hand work on, so they are held
  like writes. A `start_session` call whose `initiation` is `offer` or
  `own_initiative`, with no `proposal_id` (the field that starts a saved
  proposal), only shows a card: nothing runs until the user starts it, so it
  passes `router-first`, `route-line`, and `pipeline`. An `own_initiative` card carries a brief,
  which runs when the user starts the card, so it still meets the `spawn`
  gate; an `offer` card carries none. Any other `initiation`, or none, a call
  with a `proposal_id`, and `hand_off_to_session` are held as spawns. A
  session tool call with no brief, such as an offer card, is not a spawn for
  the `spawn` gate. **Commands** are `Bash` and `PowerShell`.
  Every other tool, including reads and the Skill tool, is never held.
- **Code** is a file with a programming-language extension such as `.py`,
  `.ts`, `.go`, `.ps1`, or `.sh`; the list is `CODE_EXTENSIONS` in
  `actions.py`. Docs and config files are not code. A **test file** is judged
  by its path inside the project, so a folder above the project, such as
  the `tests` in `D:/tests/myapp/`, makes nothing a test. It is one under a
  `tests/`, `test/`, or `__tests__/` folder at any depth, or a top-level
  `spec/` folder; or one named `test_*`, `*_test.*`, `*_spec.*`, `*.test.*`,
  or `*.spec.*`. So `tests/helpers/factory.py` and `src/app/test_runner.py`
  (named as runners collect tests) are test files, and `src/spec/parser.py`
  is not. A file whose place in the project is unknown, because the project
  is unknown or the path cannot be read for certain, is not a test file. The
  rule is `TEST_PATH_RE` in `design_reads.py`; the `design` gate and the
  closeout's Docs item share it.
- **A task** starts at a route line that is not `continue` and runs through
  later `goated-route: continue` turns. The last route line wins, so a
  corrected line replaces the route at once. A `continue` after such a line
  in the same turn keeps that task. In a session
  with no task yet, such as one started from another session to continue work
  begun there, a turn whose only route lines are `continue` starts a task that
  requires no skills.
  `goated-route: direct` exempts the task from the pipeline gate.
- <a id="loads"></a>**Loads count until the next compaction.** A
  successful load counts from its call until the next compaction or `/clear`,
  in this turn or a later one, for every hold that asks for a load: the
  `pipeline` gate's required skills, the action gates, and the closeout's
  items. That is the point where the skill's text really leaves the agent's
  context; before it, a reload would only repeat text still there. The
  template reads the `spawn` gate asks for count the same way, and so do
  [design references](#design-references) read. The [state](#state) keeps
  the loaded names and the reads; a resumed session keeps them, and missing
  or reset state counts as not loaded.
- **Everything else is per turn.** Route and skip lines, and
  typed overrides, count only in their turn. So do the checks tied to a
  change: [change reads](#change-reads), the red-flags read after the last
  change, and Proof. A hold stops firing as soon as the turn shows
  compliance: once `commit-message` counts as loaded, a commit passes its
  skill check, and still needs this turn's change read.
- **Dropping a required skill.** A `goated-skip` line never clears a strict
  hold. If a route names a skill that does not apply, the agent writes a
  corrected route line without it; the last route line wins, as the shared
  policy says.
- **Compaction** clears the proof: the router and every other skill must
  load again, and the design references and spawn-brief templates be read
  again. The route itself carries over, so `goated-route: continue` still
  works, and keeps the earlier task's `requires:` skills, which must then
  load again. When the work after a compaction is a new task, write its own
  route line; a `direct` or corrected line in a message before the write
  replaces the earlier route at once. A compaction also starts a new turn, so
  the per-turn proof restarts.
- **Proof of use** is a successful Skill-tool load read from the transcript (a
  `Skill` tool call whose result is not an error), or a skill the user invoked
  by typing `/<skill>`. Naming a skill in text is not proof. A load counts by
  its bare name only: `someplugin:tdd` does not satisfy `requires: tdd`. If you
  installed GOATED as a Claude Code plugin, set `GOATED_ADAPTER_SKILL_NAMESPACES`
  to its namespace (comma-separated for several), for example in the settings
  file's `env` block. A **required read** is a `Read` tool call on the
  reference file, under any install folder, whose result is not an error.
- **No free retry.** Every hold is decided from the transcript, so repeating a
  held call unchanged gives the same answer until the proof or skip line
  appears. A held call is recorded as an error, so it never counts as a change
  or a check.

### Large pull requests

`standards-and-spec-review` is for a change "large or risky enough to review
before it lands", and its Activation section gives the number: a branch whose
work against its base is 400 or more changed lines, added plus deleted, in
code files outside test paths. A file counts when its extension is a code
extension (`CODE_EXTENSIONS` in `actions.py`) and its path from the top of
the checkout is not a test path (`is_test_path` in `design_reads.py`, the
rule the Docs item uses); docs, fixtures, configuration, and tests add
nothing. The
`pr-review` gate and the closeout's [Review item](#large-branches) enforce
that threshold, `REVIEW_MIN_LINES` in `actions.py`. Risk, unclear acceptance,
and uncertain conventions, the policy's other reasons, are left to the
router.

The transcript does not hold a branch's size, so this gate and the
closeout's [large-branch](#large-branches) measure are the only places the
adapter runs commands. When a pull-request call would otherwise be held
by `pr-review` (the `pull-request` gate passed, and no load, change read, or
skip line has cleared `pr-review`), the adapter asks git, in the hook's
working folder, which of the candidate refs below exist (`git for-each-ref`),
then measures the first base and head found:

```text
git diff --numstat -z --no-relative --no-ext-diff --no-textconv <base>...<head> --
```

- `<base>` is the branch the pull request merges into: `--base` or `-B` on
  `gh pr create`, `--target-branch` or `-b` on `glab mr create`, or an MCP
  tool's `base` or `target_branch` input, found as `origin/<base>` or else the
  local branch. Without one, it is the first that exists of `origin/HEAD`,
  `origin/main`, `origin/master`, `main`, and `master`.
- `<head>` is the branch it merges from: `--head` or `-H` on `gh`,
  `--source-branch` or `-s` on `glab`, or an MCP tool's `head` or
  `source_branch` input, found as the local branch or else `origin/<head>`.
  Without one, it is the checked-out `HEAD`. Only committed work counts,
  which is what the pull request opens.
- An MCP tool that names an `owner` and `repo` is measured only when they
  match the checkout's `origin` URL (one more git call). Aimed at another
  repository, or from a folder with no `origin`, the tool is not measured:
  this checkout says nothing about that repository's branches.

Values of the command's other options are never read as options, so
`--description "-bump deps"` names no base. Every name reaches git inside a
full ref name (`refs/…`), so none can read as a git option.

When the size cannot be measured, `pr-review` does not hold: no base or head
is found (a head from another fork, `owner:branch`, or a branch not yet
fetched), git is missing or fails, the folder is not a git checkout or is
one the adapter cannot read for certain (so it has no project folders), or
git's calls take longer than two seconds in all. This gate fails open, like the
rest of the adapter: holding on an unknown size would hold every pull request
from a fork or another clone, whatever its size, and a justified-skip hold
that fires without evidence teaches agents to skip it. The cost is in
[Latency](#latency).

#### Large branches

Work is often merged locally with no pull request, so the closeout's Review
and Verification items measure the branch's work as it stands, against the
same base the `pr-review` gate finds without a `--base` (the first that
exists of `origin/HEAD`, `origin/main`, `origin/master`, `main`, and
`master`). That counts the branch's commits since it left the base, staged
and unstaged changes, and every line of each untracked file git does not
ignore, in code files outside test paths only, as for
[Large pull requests](#large-pull-requests); a binary file counts no lines and a symbolic link one, as in
`git diff`, and a link's target is never read. Where the base branch exists
both locally and on `origin`, the branch is measured from the fork point
closer to it, so work merged into a local `main` and not yet pushed does not
count toward the next branch: local merges prefer the local base. The
`pr-review` gate keeps measuring from `origin/<base>` first.

```text
git rev-parse --show-toplevel --symbolic-full-name HEAD
git merge-base HEAD <base> [<the same branch's other ref>]
git diff --numstat -z --no-relative --no-ext-diff --no-textconv <merge-base> --
git ls-files --others --exclude-standard --full-name -z -- :/
```

The size is asked for only in a turn that changed code (or a sensitive file,
for Verification), and only when nothing else has met the item. Because the
branch is measured, not the commit, a large ticket split across commits is
still caught: two 300-line commits raise the Review item at the second. It
also means every later turn on a large branch that changes code, at its
commit or at its `Stop`, raises the item again, until a review in that turn
meets it or a skip line declines it.

Two cases are not measured. A commit in a turn that changed no code, such as
a later turn that only commits earlier work, meets no Review or Verification
item, since both follow the turn's own code change. And git runs in the
hook's working folder, so a commit made elsewhere, with `git -C <dir>` or
after a `cd`, is measured as the hook's folder's branch, or not at all when
that folder is no checkout.

Nothing counts as large when the size cannot be measured: on the base branch
itself, with a detached `HEAD`, with no base found, in a folder that is not a
git checkout, when git fails, or past the same two-second limit. The other
items are unchanged then.

#### Reviewer subagents

A reviewer subagent is a finished `Agent` or `Task` spawn the `spawn` gate
let through whose brief follows `subagent-driven-development`'s reviewer prompt
(`references/reviewer-prompt.md`, read, with its `Review Mode`,
`Review Inputs`, and `Required Report Format` headings). The gate records
which templates each spawn's brief followed, by the call's id, in the
session's [state](#state); a spawn that finished after the turn's last code
change, and whose brief followed the reviewer prompt, meets the Review item.
A spawn started in the background (its result says `async_launched`) has
finished only once its completion arrives later in the turn: a
`<task-notification>` naming the agent's id with a `completed` status, or the
agent's `<agent-message from="<id>">` hand-back, as a prompt or a queued
command.
A side session started with a reviewer brief (`start_session` or
`hand_off_to_session`) is not one: its result arrives at once but says only
that the review started. A subagent briefed any other way, from `handoff`'s
spawn brief or the implementer prompt, is not a review, and the item's text says to use the
reviewer prompt. Whether the review was any good is not judged.

Once a reviewer subagent has reported in the turn, the [`review-intake`](#what-it-holds) gate holds the next write to a
project code file until `receiving-code-review` counts as loaded, as that
skill's Activation states, so the findings are classified before they are
fixed.

### Design references

`software-design-principles` keeps its reasoning in reference files and names,
for each moment of a change, which to read. The `design` and `design-reads`
gates enforce those reads where the skill is loaded, judged from the edit
itself: no line the agent writes declares them. A `goated-design-reads:`
line, which earlier versions asked for, is ignored like other prose.

The rules live in one place,
[`goated_adapter/design_reads.py`](goated_adapter/design_reads.py), with the
test-path rule the closeout shares; only what counts as code, and where a
file sits in the project, stay with the other action gates, which pass in
their answers. They apply to an edit of
a code file, or of a configuration file (`.yaml`, `.yml`, `.toml`, `.json`,
`.env`, `.env.*`, `settings.*`) that is neither a lock file (`*-lock.json`,
`pnpm-lock.yaml`, `npm-shrinkwrap.json`) nor under a test path.

An edit requires the references its signals select. Signals are judged on
what the edit adds: the lines of its new text, or of a
`Write`'s text, that the text it replaces did not hold, indentation aside. A
`Write` over a file on disk is compared with that file. A definition whose
name the old text already defined, as in a signature change, is not new.
Comments and docstrings are left out of the code the error and concurrency
signals read, so `# try the cache, then raise` selects neither.

A **small edit**, one writing fewer than five lines as the `design` gate counts
them (every line of the text it writes, unchanged context and a trailing
newline's empty line included; `DESIGN_MIN_LINES` in `actions.py`),
selects no reference by the kind of file or text it touches: no
`decoupling.md` for a configuration file or the third code file, and no
`readability.md` for a comment or docstring.
`software-design-principles` states this rule; the adapter enforces it.
A test file has its own rule, for `coding.md` only: the edit must create
the file or add twenty or more lines, an added line being one of the text
it writes that the text it replaces did not hold, so a changed line counts
and unchanged context does not (spec R9). The registry states it, as the
`tdd` signal for `test-design.md` (see [Registry
references](#registry-references)), and the adapter reads it from there, so
both references follow one rule. With no registry, or none declaring an
`edit-of-file-kind` signal for `test` files, any test edit that is not small
selects `coding.md`, failing toward holding.
Outside test files, which get no signal read from the code, signals read from
the added code apply at any size: a new code file or public top-level
definition, error handling, and concurrency. An edit whose added lines cannot be
counted, such as a `MultiEdit` with an `edits` entry that is not an edit, is
not small.

| Reference | Selected when the edit |
| --- | --- |
| `process.md` | creates a code file (a `Write`, or an `Edit` with no old text, to a code file no earlier write in the turn made and that is not on disk), or adds a public top-level definition: an unindented line starting with `def`, `async def`, `class`, `function`, `export`, `func`, `fn`, `pub fn`, `public`, `interface`, `struct`, `enum`, `trait`, `impl`, or `defmodule`, whose name does not start with `_`; a shell `export NAME=` is not one |
| `complexity-and-modules.md` | the same as `process.md` |
| `decoupling.md` | is not small, and edits a configuration file or is to the third or later distinct non-test code file the turn edits |
| `readability.md` | the same as `process.md`, or is not small and adds a comment or docstring: a line opening with `#`, `//`, `/*`, `*`, `"""`, `'''`, `-- `, or `<!--`, a line inside a docstring or block comment, or a trailing `#` or `//` comment after two spaces |
| `errors.md` | adds code holding `try`, `except`, `catch`, `raise`, `throw`, `finally`, `defer` as words, or `with open` |
| `coding.md` | edits a test file and creates it or adds twenty or more lines, by the registry's rule above; a test file selects nothing else |
| `concurrency.md` | adds code holding `threading`, `Lock`, `RLock`, `Mutex`, `asyncio`, `synchronized`, `Promise.all`, a word starting `Atomic`, or `go func` |
| `differences.md` | never selected: no tool call shows two rules pulling apart, so the registry declares it advisory |

`red-flags.md` is not among them: the closeout's Design red flags item asks
for it.

A typical change, one new public function with a docstring and error
handling, its caller, and its test, requires five: `process.md`,
`complexity-and-modules.md`, `readability.md`, `errors.md`, and `coding.md`.
Tune the signals from the skill-usage mod's counts.

A reference counts as read after a finished `Read` of a path ending in
`software-design-principles/references/<file>`, in this turn or an earlier
one, until the next compaction: the [state](#state) keeps the names read, a
resumed session keeps them, and a compaction's or `/clear`'s `SessionStart`
clears them, so each reference is required at most once per context window.
The skill's load counts the same way (see [Loads](#loads)).
A shell command printing one does not count. A skip line or a typed `skip
software-design-principles` clears both gates for the turn.

The first substantial non-test code edit of a turn meets `design`, which asks
for what is missing: the load and the reads. A later edit, or any
test file edit once the skill counts as loaded, meets `design-reads`, which
asks only for reads; a test file edit that creates the file or adds twenty
or more lines still requires `coding.md`. A small edit while the skill does not count as loaded is not
held, as before.

The skill's section ids and its Section Index name sections for navigation;
no hold asks for a citation of them.

### Registry references

Every skill's entry in the GOATED registry, `stack/goated-stack.yaml`,
lists each file under its `references/` folder with a signal that makes its
read required, or `advisory` with the reason no signal fits; the registry
schema and `stack/fixtures/reference-reads/README.md` own the shape. The
`reference-reads` gate enforces those signals for the skills that [count as
loaded](#loads), so a skill whose references are never read in practice,
such as `tdd`, is asked for them at the write that needs them.

The rules live in
[`goated_adapter/reference_reads.py`](goated_adapter/reference_reads.py).
The adapter reads the installed registry (see [Install](#install)) on each
write, with its own reader for the registry's plain YAML, since it uses
only the standard library. It judges each write inside the project folder:
one by a write tool (`Edit`, `Write`, `MultiEdit`, `NotebookEdit`), and each
file a shell command names as written when some command in it writes and is
not a check, as the [`repeated-failure`](#what-it-holds) gate counts writes
(`pytest > out.txt` is not judged), and only when the command's folder is
known. A write the gate cannot place in the project, such as `git apply
fix.patch`, `cd $DIR && echo x > tickets/a.md`, or a file outside the project,
meets only the `gate-fires` signals, which the `repeated-failure` gate's own
writes all meet. The edit kinds read the code a write adds, so they fire only
for a code file written by a write tool:

| Kind | Fires when the write |
| --- | --- |
| `edit-adds-pattern` | adds code matching the named pattern, in a file of `file_kind` when the signal gives one. Comments and docstrings are left out, as for the [design signals](#design-references) |
| `edit-of-file-kind` | is of a file of `file_kind` and adds at least `min_added_lines` lines, or, with `new_file: true`, creates the file: a `Write`, or an `Edit` with no old text, to a file no earlier write in the turn made and that is not on disk. The `design-reads` gate judges a test edit for `coding.md` by the registry's one such signal for `test` files (`validate_skills.py` refuses a second), so one rule decides both (see [Design references](#design-references)) |
| `write-under-path` | is of a file under the `path` folder of the project, case aside: the file's path below a project root, as the adapter places files (see [What It Holds](#what-it-holds)), starts with it. So with `docs/specs/`, `docs/specs.md` does not fire it, and a `tickets/` folder outside the project never does. Each project root counts: from a session working in the checkout's root, `src/docs/specs/x.md` does not fire it, but from a session working in `src/`, that folder is a root too, so it does |
| `gate-fires` | comes while the named gate's condition holds, whether or not that gate holds the write: its own skill may be loaded. The adapter observes `repeated-failure` only (`OBSERVED_GATES` in `reference_reads.py`), whose condition is one check failed twice in a row with no pass since, its runs counted as that gate counts them. The schema allows any gate name, so `validate_skills.py` fails on an entry naming another; an installed registry that names one anyway asks for nothing by it |
| `sensitive-category-count` | is to a [security-sensitive](#what-it-holds) file inside the project while the turn's changes to such files, its subagents' included and this write counted, span at least `min_categories` of the `security` gate's categories |

An edit adds the non-blank lines of the text it writes that the text it
replaces did not hold, indentation aside; a `Write` over a file on disk is
compared with that file. So changing one line among four unchanged ones adds
one line, a new four-line file adds four whatever its trailing newline, and
a line the old text already held, such as an existing mock, is not added.

A `test` file is a code file at a test path, as the design gates judge it.
The named patterns are the registry's `reference_patterns`, as the adapter
matches them; so `dispatch` holds no patch, and `retrieve` no retry:

| Pattern | Matches |
| --- | --- |
| `mock-or-patch` | a word starting `mock`, `patch`, `stub`, `spy`, or `fake` (either case), `monkeypatch`, `sinon`, a word ending `Mock` (`MagicMock`), `jest.fn`, or `vi.fn` |
| `sleep-retry-or-timeout` | in any case: a word holding `sleep`, `timeout`, `retry`, `retries`, `retried`, or `retrying` (`asyncio.sleep`, `setTimeout`, `MAX_RETRIES`); `poll`, `polls`, `polled`, `polling`, or `poller` at the end of a word or before an underscore or a capital (`poll_interval`, `pollInterval`); `wait_for` or `waitFor` likewise at a word start (`waitForSelector`, `wait_for_element`); or `setInterval` |

So the first enforced set is: `tdd`'s `mocking-and-seams.md` when a test
edit adds a mock or patch, at any size, its `test-design.md` at a test edit
creating the file or adding twenty or more lines; `diagnose`'s `condition-based-waiting.md` when an edit adds a
sleep, retry, or timeout, and its `root-cause-tracing.md` at a write after
one check failed twice; `code-security-review`'s
`security-review-checklist.md` at a sensitive write once the turn's
sensitive changes span two categories; `write-a-spec`'s `spec-template.md`
before a write under `docs/specs/`; and `spec-to-tickets`'s
`ticket-slicing-templates.md` before a write under `tickets/`. The
registry's other `write-under-path` entries (`docs/adr/`, `docs/setup/`,
`docs/wayfinding/`, `docs/agents/external-docs/`) are enforced the same way.
A reference of these kinds added to the registry later is enforced with no
adapter change, as long as it names a pattern, file kind, and gate listed
here. References declared `existing-rule` keep their own gates
(`design-reads`, `spawn`, and the closeout), and `spawn-with-brief` asks for
nothing yet.

A reference counts as read after a finished `Read` of a path ending in
`<skill>/references/<file>`, in this turn or an earlier one, until the next
compaction, as design references do: the [state](#state) keeps the paths
read. A shell command printing one does not count, nor does a file of the
same name under another skill. A skip line naming the skill, or a typed
`skip <skill>`, clears that skill's references for the turn. A skill that
does not count as loaded is not asked for its references: routing and the
other gates decide whether it loads. When one edit fires references of two
skills, the hold names them all, offers a skip line for each skill, and
names the typed override as `skip <skill>`.

### Shell writes

The adapter splits a command into its simple commands (joined by `;`, `&&`,
`||`, `|`, `&`, newlines, parentheses, braces, or `$(`) and reads each one's
real command word past wrappers (`sudo -u <user>`, `env`, `timeout <n>`,
`nice`, `nohup`, `xargs`, `cmd /c`), a quoted or full path to the program
(`"git"`, `& "C:\…\git.exe"`), and line continuations (`\` in bash, a
backtick in PowerShell). A `Bash` or `PowerShell` command meets the
`route-line` and `pipeline` gates, like an edit, when one of its commands:

- redirects output into a file (`>`, `>>`, `&>`, `>&file`, `2>`), except into a null
  device (`/dev/null`, `$null`, `NUL`) or another stream (`2>&1`);
- runs `tee`, `Tee-Object`, `cp`, `mv`, `rm`, `rmdir`, `touch`, `truncate`,
  `ln`, `unlink`, `shred`, or `patch`;
- edits in place with `sed -i`, `perl -i`, or `ruby -i`;
- runs `Set-Content`, `Add-Content`, `Out-File`, `Clear-Content`, `New-Item`,
  `Copy-Item`, `Move-Item`, `Remove-Item`, `Rename-Item`, `Export-Csv`, or
  `Export-Clixml`, or one of the stock Windows PowerShell 5.1 aliases (`sc`,
  `ac`, `clc`, `del`, `erase`, `copy`, `move`, `ren`, `rd`, `ri`, `mi`, `cpi`,
  `ni`, `rni`), or a .NET `[IO.File]::Write…` style call. In a `PowerShell`
  tool command, a .NET call's text counts wherever it appears, since
  PowerShell can run text in many ways (`& $p`, `Get-Content x | iex`). In a
  `Bash` command, a .NET call's text
  handed only to text tools, which cannot start a program (`cat`, `echo`,
  `printf`, `grep`, `rg`, `head`, `tail`, `sort`, `tee`, `Write-Output`,
  `Select-Object`, and the like; `NO_POWERSHELL` in `shell.py`), is data,
  such as a heredoc fed to `cat`. It is still a write when it holds a `$(` or
  a backtick that may run it, outside a quoted-delimiter heredoc
  (`<<'EOF'`); when it is piped on into any other program
  (`… | pwsh -Command -`); when it is written into a PowerShell script file
  (`.ps1`, `.psm1`, `.psd1`) by a redirect or `tee`, wherever that file is,
  since a later call may run it; and whenever the command names `pwsh`,
  `powershell`, `iex`, or `Invoke-Expression` anywhere, or runs a script
  (`. x.ps1`), which may run text written earlier in it.
  Interpreters (`python -c`, `node -e`) and `git` (an alias or hook) can start
  PowerShell, so text handed to them counts too;
- downloads to a file: `curl -o <file>` (also `-sSLo <file>`) or `curl -O`,
  `wget` unless it writes to standard output, or `Invoke-WebRequest -OutFile`;
- runs `git apply`, `git am`, `git restore`, `git mv`, `git rm`, `git clean`,
  `git checkout -- <path>`, `git checkout <rev> <path>`,
  `git checkout --theirs|--ours <path>`, `git reset --hard`, or
  `git stash pop|apply`;
- runs an [inline script](#inline-scripts) that writes, removes, or renames a
  file.

Text inside quotes, heredoc bodies, PowerShell here-strings, and comments is
ignored, as are comparisons inside a `[[ ]]` test that is the command (after
any `if`, `!`, or other keyword) and arithmetic in `$(( ))`, so
`echo "a > b"`, `[[ $a > $b ]]`, and `ls # a > b` write nothing. Elsewhere
`[[` is a plain word, so `cat [[ a > c ]]` writes `c`. Reads, test
runs, `git status`, and `git checkout <branch>` stay free. Commit and
pull-request commands are recognized the same way, per command, so
`echo gh pr create` opens nothing.

A write target is read from the folder its command runs in, and a `cd` moves
that folder only when the adapter is certain it ran and where it went.
**Only a plain `cd` in the command's leading `&&` chain is followed**: the
first command, or one joined to everything before it by `&&` alone. Plain
means `cd`, `chdir`, `Set-Location`, or `sl` with exactly one folder argument
and no option other than `--` (or `-Path`/`-LiteralPath` naming that folder),
to an absolute path, a drive path, `~` or a path under it, or a path starting
`./` or `../` from a folder already known. So `cd /elsewhere && mv a.py b.py`
moves `/elsewhere/a.py`, outside the project, and `cd ./sub && mv a.py b.py`
moves `sub/a.py`, inside it.

Anything else makes the folder unknown for the rest of the command, and
nothing later makes it known again. Relative targets written from an unknown
folder count as inside the project, so `cd sub && mv a.py b.py` still changes
the project. That is:

- a `cd` to a bare relative name such as `sub`, which bash may find through
  `CDPATH` instead;
- a `cd` to a variable, a glob, a command substitution, `-`, `~-`, `~+`, or
  `+N`, with an option such as `-P`, with more than one argument, and a bare
  `cd`;
- any `pushd`, `popd`, `Push-Location`, or `Pop-Location`, since the folder
  stack can leave the folder unmoved (`pushd -n`) or rotate it (`pushd +1`);
- a command starting with `!`, since a failed `cd` then lets the `&&` after
  it run;
- a `cd` after `;`, a newline, `||`, `|`, or `&`, or that is followed by `|`,
  `||`, or `&`, since it may have failed, never run, or run apart;
- a `cd` inside `( )`, `{ }`, `$( )`, `case`, `if`, a loop, or a PowerShell
  script block;
- any separator other than `&&` after a followed `cd`, since what runs next
  runs even if that `cd` failed.

PowerShell 5.1 has no `&&`, and `;` is not a safe chain, so there a
`Set-Location` before a write leaves the write's relative targets counted as
inside; in PowerShell 7, `Set-Location <absolute path> && …` is followed. Only
a `cd` in the same command is followed, not one in an earlier call.

#### Inline scripts

When a command gives an interpreter its code inline, the adapter reads that
code for calls that write, remove, or rename a file. It reads `python`
(`python3`, `python3.12` and other versions, `py`), `node`, `perl`, `ruby`,
`deno`, and `bun`, each also through `uv run`, `npx`, and the other command
runners a check is read through. The code is given by an inline-code option
(`python -c`, `node -e`/`-p`/`--eval`, `perl -e`/`-E`, `ruby -e`,
`deno eval`, `bun -e`/`--eval`), or reaches standard input when no script is
named (`python -`, `python`, `deno run -`, `bun run -`) from:

- a heredoc or `<<<` here-string on the interpreter (`python - <<'EOF'`,
  `python <<< "…"`);
- a pipe from a text producer: `cat` with no file, fed a heredoc
  (`cat <<'EOF' | python -`); `echo`, `printf`, or `Write-Output` with their
  arguments; or a PowerShell string or here-string alone
  (`@'…'@ | python -`). Text piped from a file (`cat notes.txt | python -`)
  or any other program is not read.

Such a script is a shell write: its files are the string
literals its write calls name, placed as any write target is (a `cd` it
follows applies), and it meets the routing gates, the path gates
(`security`, `review-intake`, `scripted-edit`, `reference-reads`,
`conflict-resolution`, `repeated-failure`), and the closeout. A write call
whose path is not one literal (a variable, an f-string, a concatenation, an
interpolated string) is an unnamed write inside the project, as `git apply`
is. So is a literal holding `$` or a backtick in code the shell may expand
first: code given as an argument, an unquoted heredoc (`<<EOF`), a `<<<`
here-string, or piped text (`python -c "open('$F', 'w')"` writes whatever
`$F` holds). A quoted-delimiter heredoc (`<<'EOF'`) expands nothing, so
there `'$F'` is the file's name. A name an import gives a listed module or
function is followed: `import shutil as s` then `s.move(…)`,
`from os import remove` then `remove(…)`, `from pathlib import Path as P`,
and `const {writeFileSync: w} = require('fs')` or
`import {rmSync as r} from 'fs'`. A script in which no write call is found is not a write, so
`python -c "print(1)"` and a script that opens files only to read them pass
as before. Inline code is never a check; `python -m pytest` still is.

The calls, by language (`WRITE_CALLS` in `script_writes.py`, the one table):

| Language | Write calls |
| --- | --- |
| Python | `open`, `io.open`, `codecs.open`, `gzip.open`, `bz2.open`, `lzma.open` with a mode holding `w`, `a`, `x`, or `+` (a mode that is not a literal counts); `os.open` with a writing flag; `os.remove`, `unlink`, `rmdir`, `removedirs`, `truncate`, `rename`, `renames`, `replace`; `shutil.copy`, `copy2`, `copyfile`, `copytree` (the destination), `move`, `rmtree`; a path's `.write_text`, `.write_bytes`, `.unlink`, `.touch`, `.rmdir` (an unnamed file unless called on `Path("…")`), and `Path("…").rename`, `.replace`, and `.open` with a writing mode |
| JavaScript (`node`, `deno`, `bun`) | `fs` and `fs/promises`: `writeFile`, `appendFile`, `createWriteStream`, `unlink`, `rm`, `rmdir`, `truncate`, `rename`, `copyFile` and `cp` (the destination), `open` with a writing flag, and their `Sync` forms; `Deno.writeTextFile`, `writeFile`, `remove`, `create`, `truncate`, `rename`, `copyFile`, and their `Sync` forms; `Bun.write` |
| Perl | `open` with a `>`, `>>`, or `+` mode, in its three-argument form or in the path of its two-argument form; `unlink`, `rmdir`, `rename`, `rmtree`, `remove_tree`; `File::Copy`'s `copy`/`cp` (the destination) and `move`/`mv` |
| Ruby | `File.write`, `IO.write`, `binwrite`; `File.open` and `File.new` with a `w`, `a`, or `+` mode; `File.delete`, `unlink`, `rename`; `FileUtils.rm` and its forms, `remove…`, `rmdir`, `touch`, `mv`/`move`, and `cp`/`copy`/`install` (the destination) |

The reading is lexical, like the rest: a call spelled inside a string or
comment of the script still counts, toward holding. A name other code also
uses (`open`, `.rename`, `.replace`) counts only where its module, receiver,
or mode says it writes, so `text.replace("a", "b")` and
`window.open(url, "_blank")` do not.

### Plain reads

Before the router loads, `router-first` passes a `Bash` or `PowerShell`
command made only of plain reads, as it passes Read and Grep, so an agent can
look around before it routes. Each simple command must be one of:

- `cat`, `head`, `tail`, `ls`, `dir`, `grep`, `rg` (without `--pre` or
  `--hostname-bin`), or `wc`;
- `pwd`, `echo`, `cut`, `tr`, `stat`, `which`, `true`, or `:`;
- `sort` without `-o`, `-T`, `--output`, `--temporary-directory`, or
  `--compress-program`, which write files or run a program;
- `uniq` with at most one file, since it writes its second, and no `*`,
  `?`, or `[` in any argument, quoted or not, since bash may expand one
  into several files (`uniq *.txt` overwrote the second);
- `diff` without `-l` or `--paginate`, which pipe its output through `pr`;
- `file` without `-C` or `--compile` (which write a magic file), `-z`, `-Z`,
  or `--uncompress` (which run decompressors), or `-m` and `--magic-file`;
- `find` without `-exec`, `-execdir`, `-ok`, `-okdir`, `-delete`, `-fprint`,
  `-fprint0`, `-fprintf`, or `-fls`;
- `git status`, `git diff`, `git log`, `git show`, `git rev-parse`,
  `git ls-files`, or `git blame`;
- `git branch` with only listing options (`-a`, `-r`, `-v`, `-vv`,
  `--show-current`, `--contains`, `--merged`, `--sort`, `--format`, and the
  like) and a pattern only after `--list`, so no name to create (`-l`
  meant `--create-reflog` before git 2.23); an option value given as the
  next word holds no `*`, `?`, or `[`, since a glob there expands into
  several words and one left over is a branch to create
  (`git branch --format *`), while `--format=*` passes;
- `git worktree list`, and `git remote` bare, with `-v`, or as `get-url`;
- `Get-Content`, `Get-ChildItem`, or `Select-String`, or their aliases `gc`,
  `gci`, and `sls`.

A git read has no `--output`, `--ext-diff`, `--textconv`, or
`--show-signature`, and no option before the subcommand but `-C <path>`,
`--no-pager`, or `-P`. GNU tools take a long option by any prefix of its
name and run short options together, so `sort --out=x` and `sort -uo x` are
held as `--output` and `-o` are; `git branch` takes prefixes too, so only
its listing options written in full pass (`--edit` would open an editor as
`--edit-description`). `git remote show` is held: it contacts each remote,
which runs ssh or a credential helper.

The command's first part may be a `cd` to one plain path, with no `$`,
wildcard, or option (`cd sub && ls`): it moves the reads after it and writes
nothing. A `cd` later in the command, `pushd`, and `cd -` are held.

The command word must be the bare name, in any case: `./cat`, `/bin/cat`,
or `cat.cmd` may be any program, so it is held. The commands may be joined by
pipes, `&&`, `||`, `;`, or newlines. The call is held when any part of it is
something else: another or unknown command, a wrapper such as `sudo` or
`xargs` or a variable assignment before the command, any output redirect, a
heredoc, a subshell, group, or script block, a process substitution, or a
background `&`. A redirect into a null device is held too, since a null
device in one shell is a real file in another: `nul` in bash, `/dev/null` in
PowerShell. The one exception is a `Bash` call's redirect of standard error,
or another stream but standard output, into exactly `/dev/null`
(`ls 2>/dev/null`); `ls 2> errors.txt`, `ls > /dev/null`, and the same in
`PowerShell` are held. Duplicating a descriptor (`2>&1`) and an input
redirect (`< a.py`) are fine.

The call is also held when its text holds anything the lexical reading may
not follow as the shell does, even inside quotes: a `$` (variables,
`$(…)` inside double quotes, `${x:=…}`, arithmetic), a backtick, a backslash
(an escape in bash, where `-del\ete` is `-delete`, but a plain character in
PowerShell), `<<<`, a `>&` not followed by a whole descriptor (`>&2` is
fine, `>&2x` writes the file `2x`), any character but printable ASCII, a
newline, or a tab (curly quotes, which PowerShell reads as quotes; a lone
carriage return or U+2028, which it reads as a line break), a PowerShell
block comment `<#`, a PowerShell here-string, `[[` or `]]` (outside command
position a plain word, so a `>` after it redirects), `//`, which starts a
UNC path read over the network, where Windows may send the user's
credentials, `::` before a slash or backslash, a PowerShell provider path
(`FileSystem::\\host\share`) that can do the same, or PowerShell's
stop-parsing token `--%`, after which the rest of the line goes to a native
program unparsed. A backslash and `//` are fine inside a whole single-quoted
argument, which both shells read literally (`grep -n 'def\s+x' a.py`,
`grep 'http://x' src`), unless two slashes or backslashes, in any mix,
appear anywhere in it but right after a URL scheme such as `https:`: a
program may split a path off anywhere (`'-f//host/p'` is `-f` with
`//host/p`), and the adapter cannot tell a pattern from a path, so
`grep '// TODO' a.c` and `grep 'a\\b' a.py` are held. A quote inside a word (`x'\s'`) and double quotes get no exemption. So
a Windows path with backslashes, such as `Get-Content src\a.py`, is held;
`Get-Content 'src\a.py'`, Read, or a forward-slash path passes. When the
analysis cannot tell, the call is held. The lists are
`READ_ONLY_COMMANDS`, `READ_ONLY_REFUSED_ARGS`, `READ_ONLY_REFUSED_OPTIONS`,
the `GIT_READ_*` and `GIT_BRANCH_*` tables, and `NOT_PLAINLY_SPELLED_RE` in
`shell.py`. Once the
router loads, commands are judged as before.

A spawn of a read-only subagent type, `claude-code-guide` (the
`subagent_type` of an `Agent` or `Task` call, matched exactly), delegates
reads, so it passes `pipeline` and `spawn`: Claude Code ships it with Glob,
Grep, Read, WebFetch, and WebSearch only. It still meets `router-first` and
needs a route line in the turn. `Explore` and `Plan` are held like any other
spawn: they keep Bash and PowerShell, and a subagent's own calls meet no
routing gate (see [Subagents](#subagents)). Any other type, a spawn with no
type, and side sessions are held as before. The exemption trusts the name: a
project or user agent file named `claude-code-guide` replaces the built-in,
with whatever tools it lists, and is exempt too. The list is
`READ_ONLY_SUBAGENTS` in `gates.py`.

### Closeout at commit

Agents commit before they report, so a commit meets the closeout first. A
commit, as the `commit` gate sees one (a git commit in a shell command or an
MCP commit tool), that the `commit` gate lets through is held while the turn
has an unmet closeout item: Proof, Unfinished work, Docs, Design red flags,
Review, Verification, Security, or Setup. The hold's first line is the
closeout's, `goated-hold: closeout | justified-skip`, its items are the
closeout's texts, and each item accepts its usual skip line. It opens
`Before committing in this turn`; for a shell commit it adds that the whole
command was held, so a check chained before the commit in the same command
has not run yet and does not count. An MCP commit tool has no command, so
its hold leaves that out. An unmet `commit` hold comes first, unchanged.

The `Stop` closeout stays as a backstop. A commit changes no file, so an
item met before the commit stays met at `Stop`; a turn that never commits
meets the closeout only at `Stop`. A subagent's commit meets no closeout,
since a subagent has none (see [Subagents](#subagents)).

### Change reads

A hold whose step reviews or describes the change needs the change itself in
front of the agent, not only the skill: the closeout's Docs, Design, and
Security items, the commit, the pull request, and its review. A **change read** is a
finished call, made after the last change the step covers, and, for the
steps that review the change with a skill or against the red flags, after
that load or read too. For Docs, the commit, and the pull request, a read
before the skill load counts: a diff read, then a `commit-message` load with
no change between, needs no second read.

| Step | The change read must follow |
| --- | --- |
| Docs | The last code change, before or after the `doc-sync` load |
| Design | The red-flags read and the last code change that is not [comment-only](#comment-only-edits); after a red-flags read that follows five or more changed lines, later changes adding fewer than five lines in total need no second red-flags read, only this change read after them |
| Security | The `code-security-review` load and the last change to a security-sensitive file |
| Commit, pull request | The last change to any project file, code or not, including changes a subagent spawned in the turn made, before or after the skill load |
| Pull-request review | The `standards-and-spec-review` load and that last change |
| Review | The `standards-and-spec-review` load and the last code change |

A change read is one of:

- a command that prints the changes' content to the agent: `git diff`, `git
  show`, a patch log (`git log` or `git whatchanged` with `-p`, `-u`, `-U<n>`,
  `--unified`, `--patch`, or `--patch-with-stat`), `git stash show -p`, `git
  format-patch --stdout`, `gh pr diff`, or `glab mr diff`, under any wrapper
  or through a pipe (`git diff | head`), or with stderr redirected
  (`2>err.txt`). A listing of names or counts does not count: `--stat`,
  `--shortstat`, `--numstat`, `--dirstat`, `--summary`, `--name-only`,
  `--name-status`, `--raw`, `--check`, `-s`, or `--no-patch`, unless a patch
  option asks for the patch too. Neither does `--quiet`, `--output` or
  `--output=<file>`, or standard output redirected into a file
  (`> change.patch`, `1>out.txt`);
- a `Read` of a file the turn changed (any project file, code or not). In a
  turn that changed no file it can name, such as a commit of an earlier turn's
  work, only a printed diff can count, and the hold says so.

A read chained in the same command as the commit, or made in parallel with
the held call, has not finished when the call is judged, so it does not
count. A command whose result is an error does not count either, so a diff
with `--exit-code`, which exits 1 when there are changes, is not a change
read: run it without. Only git and the `gh` and `glab` diffs are read: another
version control system's diff is not seen, so read a changed file instead.

A skip line, where the item accepts one, a typed skill skip, and a commit
message the user typed still clear each hold without a change read. An MCP
tool that commits or opens a pull request passes the change-read step when
the turn changed no project file: it carries the change in its own input,
and outside a git checkout no diff can run and no changed file exists to
read, so the strict hold would have no way out.

A change read can be met by a token read, such as a diff piped through
`head -1`: the rule puts the change in front of the agent, it does not prove
the agent reviewed it. Some forms are counted although they print nothing to
the agent, because the analysis sees the diff but not where its output ends
up: `> /dev/null`, `| Out-Null`, `| wc -l`, `| cat > file`, and
`x=$(git diff)`.

#### Comment-only edits

An `Edit` or `MultiEdit` whose added and removed text is only comments and
docstrings does not move the change point the Design red-flags read must
follow, so fixing a comment the red-flags scan found does not reopen the
item. The rules (`comment_only` in
[`goated_adapter/design_reads.py`](goated_adapter/design_reads.py)) err
toward a change:

- The comment syntax comes from the file's extension. `#` comments: `.py`
  and `.pyi` (with three-quote docstrings), `.rb`, `.sh`, `.bash`, `.zsh`,
  `.pl`, `.r`, `.ps1`, `.psm1`. `//` line comments and `/* */` blocks: `.c`,
  `.h`, `.cc`, `.cpp`, `.cxx`, `.hpp`, `.cs`, `.java`, `.js`, `.jsx`, `.mjs`,
  `.cjs`, `.ts`, `.tsx`, `.go`, `.rs`, `.swift`, `.kt`, `.kts`, `.scala`,
  `.dart`. No edit of any other file is comment-only. So `#define` or
  `#[derive]` in a C-family file, and `a // 2` in Python, are code.
- Each replaced text must hold the same code lines, indentation included,
  as the text replacing it, once comments are left out: a whole line opening
  with the line marker, a `/* */` block with nothing after its close, a
  docstring line opening with three quotes with nothing after its close, and
  a trailing comment after two or more spaces (`x = 1  # note`).
- Text it cannot read for certain counts as a change: a quote before a
  trailing comment, a lone three-quote line (a fragment cannot say whether
  it opens or closes a docstring), code after a block's or docstring's
  close, and any code line holding three quotes or a backtick, which may
  open a string spanning lines. A line opening with `*` outside a block it
  saw is code.
- A `Write`, even of a file that is now only a comment, a notebook edit,
  and a shell write always count as a change.

Proof, Docs, and every other step still count a comment-only edit as a
change.

### Content checks

Only text in the tool input is checked, and only for what the skill's
contract states plainly enough to test without judgement
([`goated_adapter/contracts.py`](goated_adapter/contracts.py)):

- **Commit message.** When the commit itself carries the message inline (`-m`,
  `--message`, a short-flag cluster such as `-am`, the heredoc fed to that
  commit's `-F -`, a heredoc in `-m "$(cat <<'EOF' … EOF)"`, or a PowerShell
  here-string), or an MCP commit tool carries it in `message`, it needs a non-empty subject of at most 72
  characters, a blank line before any body, and no credential-shaped token. A
  message in a file (`-F <path>`), reused from another commit (`-c`, `-C`), or
  from an editor is not checked.
- **Spawn brief.** The brief needs, as Markdown headings, the sections its
  template keeps even for an agent that inherits the conversation:
  `Goal`, `Scope`, and `Done Means` for `handoff`'s spawn brief; `Task`,
  `Ownership`, and `Required Report Format` for the implementer prompt;
  `Review Mode`, `Review Inputs`, and `Required Report Format` for the
  reviewer prompt. A brief passes when it matches a template whose reference
  was read in the turn.
- **Skills line in a brief.** Every spawn brief, including a card's, also
  needs a skills line naming the skills the new agent should read before it
  starts: `goated-skills: <skill>, <skill>`, or
  `goated-skills: none: <reason>` with a reason of three words or more. A
  skill is named by its installed name, bare or with a plugin namespace
  (`goated:tdd`). Like a route line, the line counts only on its own line
  outside code blocks, bare or in one pair of backticks; it may also be a
  `- ` or `* ` list item. `handoff`'s `references/spawn-brief.md` defines
  the line, and the implementer and reviewer prompts carry it. A brief is
  held when it has no such line or its line is malformed, and the hold names
  the problem: a missing line, no skill named, none with too short a reason,
  none mixed with names, an empty or malformed name, a capitalised prefix, or
  no space after it. Whether the named skills are the right ones, and whether
  the agent reads them, is not checked.

### Hold messages

Every hold, whether a denied tool call or a blocked `Stop`, returns a reason
whose first line has one stable format, which the skill-usage mod parses. The
`closeout` gate holds a commit call as well as a `Stop`, with the same first
line, and the mod counts both alike:

```text
goated-hold: <gate> | <kind>
<what the agent must do, in plain words>
```

- `<gate>` is one of `router-first`, `route-line`, `pipeline`, `commit`,
  `pull-request`, `pr-review`, `spawn`, `design`, `design-reads`,
  `reference-reads`, `review-intake`, `scripted-edit`, `security`,
  `conflict-resolution`, `repeated-failure`, or `closeout`.
- `<kind>` is `strict` or `justified-skip`.
- The first line matches
  `^goated-hold: ([a-z]+(?:-[a-z]+)*) \| (strict|justified-skip)$`.
- The lines after it are guidance for the agent and may change between
  releases; do not parse their wording. They backtick each skill they ask
  for by its bare name, which the skill-usage mod reads from them,
  and backtick no other bare word: a file name is quoted, and the grammar's
  words appear backticked only inside a whole line such as
  `goated-skip: <skill>: <reason>`. A test checks every hold text against
  the registry's skill names.
- The closeout hold lists each unmet item on its own line, starting
  `- <Label>: `, with `Proof`, `Unfinished`, `Docs`, `Design`, `Review`,
  `Verification`, `Security`, or `Setup` as the label; the two design items
  share `Design`. Each item names the skill it asks for, backticked or as the
  skill of the skip line it offers: the mod counts an item through that
  skill, so an item that names none is not counted. The Review item names
  the reviewer prompt by its path, so it counts through
  `standards-and-spec-review`. These labels
  are stable: the skill-usage mod counts each closeout hold per item by them,
  so a release keeps them, and a new item takes a label of its own. The
  wording after the label may change.
- Each named skill is a separate requirement, except in the `spawn` hold,
  whose two skills are alternatives: `handoff` or
  `subagent-driven-development`, either of which answers it.
- A hold asks for a load only when the skill does not [count as
  loaded](#loads): it never loaded since the last compaction or `/clear`, or
  the state that kept the load is missing. Inside a
  [subagent](#subagents), where only its current turn counts, the hold asks
  for the load or read in this turn.
- A hold that a route or skip line can clear (`route-line`, `pipeline`,
  `design`, `design-reads`, `reference-reads`, `review-intake`, `scripted-edit`, `security`,
  `conflict-resolution`, `repeated-failure`, `pr-review`) says that a line in reply text may not be
  seen (see [Known Limits](#known-limits)), and to put the line in the held
  call's description, or in the description or Skill `args` of a call made
  in an earlier message of the turn, and make the call again. It then says
  the user can type the matching override. It names those fields without
  backticks, since the mod would read a backticked bare word as a skill.
  That advice is given in full on only one such hold of a turn, holds on
  calls made in parallel included. Every other one in the turn gives one
  sentence instead: put the line in a shell or agent call's description or a
  Skill call's args, or tell the user they can type the override. The hold
  that gives it in full is the first to claim the turn's marker (see
  [State](#state)), one exclusive file create, so of several hooks running at
  once only one can claim it. When the marker cannot be made or read, each
  such hold gives the full advice. The next turn's first such hold gives it
  in full again. The first line, and every hold that never carried the
  advice, stay the same. A subagent's turns claim their own marker, so each
  subagent gives the full advice once per turn, apart from its parent.
- A hold or closeout item that asks for a [change read](#change-reads) once
  its skill has loaded names that skill without backticks, or only in its
  skip line, since no load answers it: the commit, pull-request, and
  pr-review holds name no skill (pr-review's skip line is not backticked
  either), and the closeout offers the skill only as a skip line. Once
  `software-design-principles` has loaded, the `design` hold (asking for
  reads) and the `design-reads` hold name it only in their skip line, and
  backtick each reference by its path,
  `software-design-principles/references/<file>`, which is no bare name; the
  skill-usage mod reads it.
- The `reference-reads` hold names each skill it asks about only in its
  skip line, `goated-skip: <skill>: <reason>`, since the skill is already
  loaded, and backticks each reference by its path under the skill,
  `<skill>/references/<file>`; the skill-usage mod counts each skill's ask
  as read files once each of its references is read.
- Both Design red-flags texts repeat the question `red-flags.md` ends with;
  no hold reads an answer.

Claude Code records a denied call as a `tool_result` with `is_error: true`
whose content carries this reason, and a blocked `Stop` as the reason shown
to the agent. Claude Code 2.1.325 wraps that reason as `Stop hook blocking
error from command: "<command>": <reason>`, so the hold line follows the
wrapper on the same line. The outcome of a hold is read from what follows in the
transcript: the skill load, read, change read, or skip line that cleared it, or the user
override recorded for the turn.

## User Overrides

Overrides come only from prompts a person typed. The user-prompt hook records
the phrases below, and the gates apply them only to the turn that prompt
opened, after checking the transcript's record of who wrote it, and only until
that turn ends with `Stop` (see Subagents for a report arriving later). Text
an agent writes never counts. Matching ignores case, harness `<system-reminder>`
blocks, and text you pasted, which Claude Code wraps as
`<pasted_content id="…">` … `</pasted_content id="…">`: a phrase inside a
pasted report is not an override, while one you type before or after the block
is. A paste ends only at a close tag with its own id, so a close tag or a
nested paste quoted inside it cannot end it early, and a paste with no close
tag runs to the end of the prompt. A phrase negated
just before it, such as "don't skip routing", "never skip tdd", or "no need to
skip doc-sync", is not an override.

| Typed phrase | Effect for that turn |
| --- | --- |
| `skip routing`, `skip the router` | Stands down `router-first`, `route-line`, and `pipeline` |
| `skip <skill>`, `skip the <skill> skill` | Stands down every requirement for that skill: in `pipeline`, in an action gate, or in a closeout item. `skip using-goated-ai-skills` also stands down `router-first`. `<skill>` must be a skill Claude Code can find (user, project, or plugin skills); when none can be found, a GOATED registry skill name. So "skip line" or "skip the first two lines" is not an override. The name may be wrapped in backticks, as in ``skip `tdd` ``, or carry a backtick on one side only |
| `commit message: <text>`, `commit with the message "<text>"`, or a fenced block right after such a phrase | Stands down the `commit` hold for a commit whose inline message has the same subject line (whitespace aside); a commit with another message, or with none inline, is still held. The skill name `commit-message` is not such a phrase |

Claude Code also submits prompts nobody typed in this session:

- **Background results**, such as the `<task-notification>` that reports a
  finished background task, a desktop-app side-session event, or the
  host-written `Try again` the app sends after an API error. They carry
  agent output, so they never yield overrides, and they do not start a new
  turn: the typed prompt's route line and overrides still cover what follows.
- **Requests from elsewhere**, such as a subagent's final report, a message
  from another Claude session, a brief from the session that started this
  one, or any prompt whose recorded origin is not a person. They start a new
  turn, which needs its own route line (`goated-route: continue` when it
  continues the current task; a session's first brief may carry it, see
  [What It Holds](#what-it-holds)), and never carry overrides: not ones they quote,
  and not ones you typed earlier, which covered only the turn your prompt
  opened. The adapter neither records nor announces an override for them.
  The user-prompt hook's input does not say where a prompt came from, so the
  hook recognizes these by their opening text, such as the line `Another
  Claude session sent a message:` that opens both a subagent's report and
  another session's message. The gates check again against the transcript,
  where Claude Code marks such a prompt with `origin.kind` `peer` (and
  `isMeta`), so one whose text the hook misses still applies no override.

A prompt you type that starts with a pasted report or message in that shape
reads as one of those requests, so an override typed after the paste does
not count. Type the override before the pasted text.

Claude Code shows a short notice when the adapter records an override. The
same sentence, `GOATED Claude Code adapter: recorded your override for this
prompt: "<phrase>"`, also goes into the turn's context as the hook's
`additionalContext`. Each phrase is recorded as typed, without backticks; a
commit-message override is recorded as `commit message`, without its text.
A notice reaches a Claude Code mod with no text, so the
[skill-usage mod](skill-usage/README.md) counts overrides from that context.
The phrase set lives in [`goated_adapter/overrides.py`](goated_adapter/overrides.py);
change it and this table together.

## Subagents

A hook call from inside a subagent carries `agent_id`. There:

- the routing gates do not apply, because the parent's brief carries the route;
- the action gates (`commit`, `pull-request`, `pr-review`, `spawn`, `design`,
  `design-reads`, `scripted-edit`, `security`, `conflict-resolution`,
  `repeated-failure`) apply,
  `reference-reads` and `review-intake` aside, judged from
  the subagent's own transcript, which Claude Code keeps in
  `<session-id>/subagents/agent-<agent_id>.jsonl` beside the main one. A
  subagent must load the skill itself: the parent's loads do not count, and
  only its own current turn's loads, template reads, and design references
  count;
- no override applies, because nobody types a subagent's prompts;
- the closeout gate does not run when the subagent stops; the adapter
  registers no `SubagentStop` hook. Instead, code a subagent changed counts
  toward the closeout of the parent turn that spawned it. The parent finds the
  subagent through the `agentId` that Claude Code records in the spawn's
  result.

If the subagent's transcript cannot be found, the call fails open with a
warning; at closeout, its changes are left out, with a warning.

A background subagent's final report can reach the parent in two ways: as a
queued attachment inside the turn, or as a prompt that Claude Code records as
a message from another session (an `isMeta` entry with `turnOrigin: peer`, an
`origin` of kind `peer` whose `from` is the agent's id, and text opening
`Another Claude session sent a message:` then `<agent-message from="<id>">`).
Either way the report continues the turn when the adapter can tie it to a
spawn of this session: the prompt's `origin.from` and its tag name the same
agent, and an earlier spawn result in the main transcript, after the last
compaction and within the read limit, records that agent as its `agentId`.
Then the turn's route line, skip lines, overrides, checks and change reads
all stand, a brief's route does not end, the closeout judges the whole turn,
and the user-prompt hook announces no override and resets nothing.
`review-intake` sees a reviewer's report either way. A report carries no
override of its own. A report that arrives after the turn ended, once the
adapter's `Stop` hook let it end, still continues the turn's route, route and
skip lines, checks and change reads, but the overrides typed in that turn no
longer apply. The user-prompt hook sees no `origin`, so it takes typed text
shaped like such a report for one and records nothing; the gates read the
typed origin from the transcript and open a new turn, to which no override
applies. A prompt the adapter cannot tie to one of its spawns,
such as another session's message, a scheduler's prompt, a report naming an
agent this session never spawned, or a shape the adapter does not know,
opens a new turn as before.

## Session Start Notices

At the first session start the adapter says once, in a notice you see and in
the agent's context, when:

- the GOATED shared policy is not in any instruction file Claude Code loads;
- the `using-goated-ai-skills` skill is not among your user, project, or
  plugin skills. Without it, router-first never clears; type `skip routing` in
  a prompt to proceed, or install the router.

At a session start it also says, once per project, which agent files the
project lacks at its root, naming the onboarding skill that writes each, as
those skills state:

| Missing file | Skill named |
| --- | --- |
| `AGENTS.md`, `CLAUDE.md`, or `.claude/CLAUDE.md` | `agent-instructions-integrator` |
| `docs/agents/context-matrix.md` | `context-matrix-map` |
| `docs/agents/project-standards.md` | `project-standards-calibration` |

The project root is `CLAUDE_PROJECT_DIR` when Claude Code sets it, else the
nearest folder at or above the session's folder holding `.git`, else that
folder. Which skills the notice last named is recorded beside the session
state (see [State](#state)), never inside the project. The notice shows again
only when a file goes missing that it did not name before; a file added back
brings none.

At the next prompt after a session's third declined or unanswered hold, it
says once per session that the `retrospective` skill can turn that friction
into improvements, as that skill states. A hold is declined when a skip
line naming its skill follows it, and unanswered when it is still open at the
next typed prompt. It is answered, and counts as neither, when the same gate
later lets the same action through: an edit of the same file, the same
command, a commit or pull request whatever its message, or a spawn of the
same tool. A closeout hold is answered by any later `Stop` or commit the
closeout lets through. A hold is also answered once every skill it names is
loaded and every reference it names is read. A `scripted-edit` hold names
its skill only in the skip line it offers, since loading that skill does
not clear it; it is answered by a later write tool call that goes through
to a file its script named, or to any file when the script named one only
at run time. One the next typed prompt's
override stands down counts as neither too. A gate counts once per turn,
however often it holds in that turn, and only the main agent's holds count.
Holds still open at a compaction or `/clear` are dropped uncounted, since
reading restarts after the boundary. The notice waits for a prompt you type;
a message from another session or agent does not bring it.

Neither notice blocks a call or a `Stop`.

## Failing Open

The adapter never blocks because of its own failure. It lets the call through
and shows a warning that starts `GOATED Claude Code adapter:` when:

- the hook input is not readable JSON or lacks `session_id` or
  `transcript_path`;
- the transcript, or a subagent's own transcript, cannot be read, or the
  current turn alone is larger than the
  64 MB read limit. Older turns beyond the limit are simply not read, as if
  they had been seen;
- the transcript does not show the prompt the call belongs to (its
  `prompt_id`) within 1.5 seconds. The call itself need not be there: it is
  judged from the hook input (see [Latency](#latency));
- the adapter hits an internal error;
- on macOS and Linux, its state folder is a link, belongs to another user, or
  is writable by others, because planted state there could make holds pass.

Saved state that cannot be read, or has an unexpected shape, is reset with a
warning; a reset can only re-hold, never pass. A missing state file starts
fresh the same way, without a warning. Fresh state cannot tell whether the
session had a task, so `goated-route: continue` stays held until a full route
line starts one, unless the session has just started (a `SessionStart` with
source `startup`) or the adapter has read its transcript from the first turn.
If saving state fails, for
example while a parallel hook has the file open on Windows, the hold decision
still stands and a warning says the state was not saved.

## State

One small JSON file per session in a `goated-claude-code-adapter/` folder:

- on macOS and Linux, under `$XDG_STATE_HOME`, or `~/.local/state` when that
  is not set, rather than the shared `/tmp`, so another local user cannot
  pre-create it;
- on Windows, under the per-user temporary folder (`%TEMP%`);
- anywhere you choose with `GOATED_ADAPTER_STATE_DIR`.

It holds the current task's route, whether missing or reset state lost the
task, whether the session's first prompt was a brief, whether the router loaded, which GOATED skills loaded and which design
references, skill references, and spawn-brief templates were read since the
last compaction
(see [Loads](#loads)), digests of the first three distinct files the Read
tool read since then, which orient a session routed by its brief, which brief templates each spawn
of the latest turn followed when the `spawn` gate let it through (see
[Reviewer subagents](#reviewer-subagents)), the last turn seen, the
latest typed overrides, and the friction count behind the retrospective
notice (see [Session Start Notices](#session-start-notices)): the holds still
open, with the action each held, the skills, references, and skip lines it
names, and how much of its turn came before it, the gates that held in the latest turn, how many
holds were declined or left unanswered, and whether the notice was shown. It
holds no prompt or reply
text beyond the short override phrases and a commit message the user typed.
Beside the state files, a `turn-markers/` folder holds one empty file per
session, and one per subagent of it, named for the turn whose hold gave the
[unseen-line advice](#hold-messages) in full. A new turn's claim replaces it,
and a `SessionStart` after compaction or `/clear` deletes the session's and
its subagents'. An `onboarding-notices/` folder holds one file per project,
named by a digest of the project's path, listing the skills its onboarding
notice last named.
The action and closeout gates keep no state of their own: they read the
current turn, the loads, design and skill references, and templates read
since the last compaction, and, for the closeout's Review item, the
templates recorded for its spawns. Files are not pruned automatically;
deleting the folder between sessions is safe.

## Latency

Measured on 2026-11-16 on Windows 11 with Python 3.13 and an Intel Core
i9-14900K, spawning `goated_hook.py` in exec form, 30 runs each:

| Case | Median | p90 |
| --- | --- | --- |
| Interpreter start alone (`python -c pass`) | 22 ms | 23 ms |
| `UserPromptSubmit` or `SessionStart` | 56 ms | 59 ms |
| `PreToolUse`, 20 KB transcript | 58 ms | 63 ms |
| `PreToolUse`, real 5.3 MB session transcript | 70 ms | 79 ms |
| `PreToolUse`, 88 MB synthetic transcript, 300-call current turn | 70 ms | 78 ms |

The reader reads only the current turn from the end of the file, so
transcript size barely matters. Most of the cost is interpreter start-up and
the `json` and `re` imports. The action and closeout gates (Ticket 031) added
about 4 ms: on the recorded 20 KB fixture, 30 runs each, the median went from
60 to 64 ms. A commit or pull request whose skill has loaded also reads the
transcript of each subagent the turn spawned, as the closeout does, to find
the changes its change read must follow; other calls never read them. That
case was not measured.

The `pr-review` gate's size check (see [Large pull requests](#large-pull-requests))
runs only on a pull-request call that has passed the `pull-request` gate and
that no load or skip line has cleared of `pr-review`. Measured on 2026-11-16
on the same machine with git 2.55, in-process through `run_hook`, 30 runs each:

| Case | Median | p90 |
| --- | --- | --- |
| No checkout at the hook's folder | 3 ms | 3 ms |
| `gh pr create --base main`, 450 changed lines (two git calls) | 34 ms | 36 ms |
| `gh pr create --fill`, 450 changed lines (two git calls) | 35 ms | 39 ms |
| The same, 20,000 changed lines | 40 ms | 44 ms |
| An MCP tool naming `owner` and `repo`, 450 changed lines (three git calls) | 62 ms | 75 ms |

So a pull request's hook call costs about 35 ms more, about 60 ms for an MCP
tool that names its repository, and at most two seconds when git hangs.

The closeout's [large-branch](#large-branches) measure (Ticket 069, five git
calls) runs at a commit or `Stop` in a turn that changed code, while the
Review or Verification item is not otherwise met. Measured on 2026-11-17 the
same way, a `Stop` with only that measure left to run:

| Case | Median | p90 |
| --- | --- | --- |
| No checkout at the hook's folder | 4 ms | 5 ms |
| A branch of 450 changed lines | 58 ms | 61 ms |
| A branch of 20,000 changed lines | 58 ms | 63 ms |

Every other call costs nothing more.

The hook never waits for the call it judges, which it takes from its input:
in an interactive session (Claude Code 2.1.325) the assistant message holding
the call is recorded only after `PreToolUse` returns, and in headless runs it
appeared 54 to 114 ms after the hook started. The only wait is for the entry
of the call's prompt, which is normally already there.

## Known Limits

- The hook sees nothing of the assistant message that makes the call it
  judges. In an interactive session Claude Code records that message only
  after the hook returns, so a route line or skip line written in the same
  message, and sibling calls made alongside it (a Skill load included), do not
  count yet. Only the judged call's own input is seen: a line in its
  `description` counts for it, and a line in a sibling call does not. When
  the hook input has no `tool_use_id`, the judged call is taken to be the
  newest recorded call without a result if its name and input match, so its
  line is counted once.
- Claude Code can store the text of an assistant message that also makes a
  tool call as a rewritten summary, in a thinking block, that drops route and
  skip lines, so the adapter never sees a line written there, and a retry
  cannot bring it back. The holds a line can clear therefore point to the
  call fields the adapter also reads (see [What It Holds](#what-it-holds)).
  Edit and Write calls have no `description`, so a line for one of them goes
  in a call made in an earlier message of the turn, such as the Skill call
  that loads a required skill. If the line is still not seen, the holds
  point the user to the typed override: `skip routing`, or `skip <skill>` for a skip line.
- A brief's route line is recognized only in the shape current desktop-app
  builds record (see [What It Holds](#what-it-holds)). Older builds recorded
  a brief with `turnOrigin` `sdk`; such a brief, one passed to `claude -p`,
  or one in any other shape is a prompt like any other, so its session loads
  the router and writes its own route line. After a compaction
  the brief is gone, so `router-first` needs the router again. Harness
  nudges such as "The user hasn't heard from you in a while" are recorded as
  `attachment` entries and never open a turn.
- A briefed session's orientation counts any three distinct files read with
  the Read tool, whatever they are; the adapter cannot tell whether they are
  the sources the brief names. A file printed by a shell command (`cat`)
  does not count, and two spellings of one path count once only when they
  differ by case or separators on Windows.

- Shell analysis is lexical, not a shell. These forms are not seen, so a
  write in them meets only `router-first` and a commit or pull request in
  them meets no action gate:
  - a command run through another shell or evaluator: `bash -c`, `sh -c`,
    `eval`, `Invoke-Expression`, `Start-Process`, or a heredoc fed to a shell
    (`bash <<'EOF'`); only whether a `bash -c`, `sh -c`, `zsh -c`, or
    `pwsh -Command` line is a check is read;
  - command substitution with backticks, or `$(…)` inside double quotes;
  - a write by a script file run by name (`node build.js`,
    `python tools/gen.py`) or fed from a file (`node < build.js`,
    `cat gen.py | python -`), or by an archive tool (`tar -x`, `unzip`);
  - a write by [inline code](#inline-scripts) through a call its table does
    not list: another program (`subprocess`, `child_process`, `system`), a
    library's own writer (`json.dump` to a path, `pandas` `to_csv`,
    `Pathname#write`), a dynamic call (`getattr`, `eval`), or a name
    renamed other than by an import it reads (`w = fs.writeFileSync`,
    `p = os.remove`, `import fs from 'fs'` then `fs.default.rm`); by an
    interpreter the adapter does not read (`php -r`, `pypy`); or by code
    piped in from a program other than the text producers it reads;
  - git aliases (`git ci`), and `gh api` calls that create a pull request
    (`gh api repos/<owner>/<repo>/pulls`);
  - MCP tools that commit or open pull requests under names other than those
    listed in [What It Holds](#what-it-holds).

  An agent working around the holds this way is the case the next item
  describes.
- A [plain read](#plain-reads) can still run a program that git config
  names, such as `core.fsmonitor` under `git status`, or `diff.external` and
  a `textconv` driver set for the repository, which a plain `git diff`,
  `git show`, `git log -p`, or `git blame` runs too, or a pager such as
  `core.pager` under `git branch` or `git log`. Refusing the `--ext-diff`
  and `--textconv` options does not stop them. A `cd` before a read moves
  it into another repository, whose config then applies, as `git -C` does.
  A passing read can also hang:
  `tail -f` never ends on its own.
- A shell call's result stands for the whole command, not for each command
  in it. A check in the same command as a write proves that write even when
  the command hid the check's failure (`pytest || true`, `pytest; echo done`,
  `pytest | tail`), and the Unfinished item does not see that failure either.
  A write in a subshell (`(cp a.py src/a.py) && pytest`) is not proved by a
  check after the group.
- Two closeout triggers are mechanical stand-ins for judgement. "Behavior or
  interfaces changed" is read as "a non-test code file changed", so a pure
  refactor still asks for `doc-sync` or a skip line. "Work left unfinished" is
  read as "the last check after the change failed"; unfinished work with no
  failing check is not seen.
- The closeout holds the `Stop` even when Claude Code reports that a `Stop`
  hook already blocked once (`stop_hook_active`), because a hold never passes
  on a retry. Each item accepts a skip line, so the agent can always end the
  turn by writing one. The reply being finished is read from the hook input's
  `last_assistant_message`; on a Claude Code version without that field, a
  skip line written only in the final reply may not be seen until the
  transcript catches up.
- Whether a file is inside the project is read from paths, not from a shell
  or the disk's full layout, so the adapter counts a file as outside only when
  it is certain, and every limit here fails toward holding:
  - Git Bash mounts other than `/tmp` (`/` is the Git install folder, and
    any mount you add) are not read, so on Windows a path rooted with no
    drive letter, other than Git Bash's `/c/` drive form and `/tmp`, counts
    as inside the project. `/tmp` is read through `TMP` and `TEMP` as the
    hook sees them, which assumes Git Bash's default `/tmp` mount; a changed
    `/etc/fstab`, or a shell whose `TMP` differs from the hook's, is not seen.
  - `CDPATH` is not read, so a `cd` to a bare relative name makes the folder
    unknown, and the writes after it count as inside.
  - A `cd` is read as bash's default logical `cd -L`: each `..` drops the
    name before it from the text, so `cd /tmp/../c/proj` is in `/c/proj`.
    (`cd -P`, like any `cd` with an option, leaves the folder unknown.) A file
    path with `..` outside a `cd`, such as `> /tmp/../x`, is read physically,
    as the system opens it.
  - A .NET write in a PowerShell script counts when a shell command writes
    the script (a redirect or `tee`), not when the `Write` or `Edit` tool
    does, nor when a script holding it is copied or renamed into place.
  - .NET write text a `Bash` command writes to a file that is not a script,
    and a later call runs, is not seen: for example a later
    `Get-Content x.txt | iex` in the `PowerShell` tool, or Bash
    `pwsh -Command (Get-Content /tmp/x.txt)`. Only the command that writes
    the text is read, and it names no PowerShell.
  - `~` is read both as your profile folder and as `HOME` when that is set
    (Git Bash may point it elsewhere); a `~/...` path inside the project under
    either reading counts as inside. A shell's `HOME` that differs from the
    one Claude Code passes to hooks is not seen.
- The design gate judges size by lines added in the tool input, not by what
  the change does, and the design gates do not see shell writes.
  The design-reads signals are word and shape matches on lines, so a `try` in
  a string selects `errors.md`, and a `NotebookEdit` cell counts all its text
  as added. A `Write`'s file on disk, read to tell what it adds, is the one
  design input outside the transcript. The adapter cannot tell a reference
  read and applied from one read alone, and nothing checks that the agent
  connected a reference to its change.
- The design-reads gate holds only while `software-design-principles`
  counts as loaded: in a session that has not loaded it since the last
  compaction, a turn whose edits are all small is held for no reference at
  all. Inside a subagent, only the subagent's current turn counts: a load or
  reference read in an earlier turn of a continued subagent is required
  again, and the parent's never count for it, nor its for the parent.
- An edit whose added lines cannot be counted, such as one whose new text
  is missing, is not small: the `design` gate treats it as substantial, and
  in a later turn it brings the closeout's Design items.
- A compaction boundary in the transcript drops earlier loads and reads even
  when its `SessionStart` reset never landed, for example after a hook that
  failed open or an adapter installed mid-session.
- A load counts until the next compaction however many turns ago it was,
  when the agent may no longer follow the skill closely. The checks tied to
  a change (change reads, the red-flags read, Proof) still count only in
  their turn. A turn is folded into the state by the hooks that run in it;
  Claude Code runs `Stop` at the end of every turn, so a turn of loads alone
  still counts. If the state file is lost, a load from an earlier turn is
  asked for again. The security gate judges by
  path alone. The conflict-resolution gate reads git's English messages
  (`Automatic merge failed`, `could not apply`, `could not revert`), so a git
  set to another language is not seen.
- The red-flags reread rule counts the lines an edit tool call writes, so
  fixes made by shell writes or a subagent always ask for the red-flags read
  again, and five small fixes spread over a turn ask for it as one six-line
  fix would.
- The `review-intake` gate sees only the turn a reviewer reported in. When
  the review reports, the turn ends to ask the user, and the fixes come in
  the next turn, those fixes are not held. A subagent's own edits are never
  held, since only the main agent records which brief each spawn followed.
- The `reference-reads` gate fails open: with no registry at its path (see
  [Install](#install)), or one it cannot read or parse, it asks for nothing,
  with a warning unless the default registry is simply missing. Its reader
  takes the registry's plain block YAML only. A block scalar (`|`), an
  anchor, a flow mapping, a plain value wrapped onto more lines, a sequence
  not indented under its key, or a key with no value makes the whole
  registry unreadable to it. It takes only `true` and `false` as booleans,
  and reads `True`, `yes`, `on`, `null`, `~`, and `-1` as strings, and a
  quoted value without its escapes. `validate_skills.py`
  fails when this reader and a full YAML parser read the source registry's
  references differently, so such a mismatch is refused and a registry edit
  cannot switch the gate off unnoticed; it also fails when more than one
  reference has an `edit-of-file-kind` signal for `test` files, since the
  design gate reads only one. An installed registry edited by hand is not
  checked. A
  signal value of the wrong type, such as a list for `pattern`, makes the
  registry unreadable too. A signal naming a
  pattern or file kind the adapter does not list asks for nothing. A shell
  write meets only the signals that need no added text (`write-under-path`,
  `gate-fires`, `sensitive-category-count`): the edit kinds read the code a
  write adds, which only a write tool's input shows. A file is created only
  by a write tool's `Write`, or `Edit` with no old text, to a path not on
  disk, so a test file a shell command made earlier in the turn, such as
  `touch tests/test_x.py`, is on disk, and a short `Write` over it asks
  neither gate for `coding.md` or `test-design.md`. It does not run inside a
  [subagent](#subagents). Its patterns match words by their letters, so a word
  that only starts like one, such as `patches` or `spyglass`, or one in a
  string, still selects the reference; the read counts until the next
  compaction, which bounds the cost.
- A restore command, such as `git checkout -- <file>` or `git restore`,
  counts as a change whatever it restores, even content identical to what
  the last check ran on, since the adapter reads commands, not file content.
  So the Proof item asks for a check after it; a rerun of the check, or a
  `goated-skip: verification-before-completion: <reason>` line, answers it.
- The adapter guards against agents skipping skills, not against an agent
  working to defeat it. An agent with shell access could edit the transcript,
  the state file, or the settings that install the hooks. Defending against
  that is out of scope; review what agents change if it matters to you.
- Prompt classification relies on transcript fields and text wrappers seen in
  Claude Code 2.1.3xx (`origin`, `turnOrigin`, `<task-notification>`,
  `Another Claude session sent a message:`, and others). A new kind of
  machine-written prompt with no `origin` and an unknown wrapper would be
  treated as typed. A new wrapper alone, on a prompt the transcript marks with
  a non-person origin, still applies no override, but the user-prompt hook
  would announce one. A subagent's report continues the turn only in the shape
  Subagents describes; a new shape, or a report whose spawn lies before a
  compaction or beyond the read limit, opens a turn, as any machine-written
  prompt does. Until it finds the spawn, the reader goes on reading back for
  it, so a report naming an agent this session never spawned makes each hook
  call of the turns it opens read back to the last compaction or the read
  limit.
- Shared-policy detection looks for the policy's title in the instruction
  files Claude Code reads and in their one-level `@` imports. It does not model
  the setting under which a `CLAUDE.md` stops `AGENTS.md` from loading, it
  stops its parent-folder walk at your home folder, and it opens imports only
  inside the project, your home folder, or the importing file's folder, never
  on a network (UNC) path.
- Hooks for parallel tool calls can race on the state file. Each call
  re-derives its turn from the transcript, so a lost update can cause a repeat
  hold, never a pass. The turn marker that shares the full unseen-line advice
  is claimed atomically, apart from the state file, so this race never
  repeats that advice.
- The Verification item's sensitive-file trigger uses the `security` gate's
  paths, so any change to one, such as an edit of a lockfile or a `.env`
  value, asks for `verification-before-completion` too; its skip line
  answers it.
- The [large-branch](#large-branches) measure counts every untracked code
  file outside test paths that git does not ignore, so an unignored folder of
  generated or vendored code makes a small branch large; its skip line, or a
  `.gitignore` entry, answers that. A branch large only in tests, fixtures,
  docs, or configuration meets no Review item. Test paths are judged from the
  top of the checkout, so in a project below that top a top-level `spec/`
  folder of the project is not a test path.
- A plain `pip install` or `conda install` is judged by the folder it runs
  in, but it installs into the active environment, which may be the
  project's virtual environment though the command ran elsewhere; such an
  install from a scratch folder raises no Setup item.
- A session started from a brief meets no Review item, trusting the
  starting session to review: a brief sent with no review planned leaves a
  large branch unreviewed. Only a brief the adapter recognizes, with a route
  line (see [What It Holds](#what-it-holds)), marks the session.
- The Proof and Verification items name the same skill, so the skill-usage
  mod counts a `verification-before-completion` load as answering both items
  of a hold that lists both, though only Verification asks for the load.

## Measuring It

The optional [skill-usage mod](skill-usage/README.md) in `skill-usage/` shows
the adapter's holds and their outcomes, your overrides, route and skip lines,
reference reads, and subagent activity in a pane beside the chat. It installs
and uninstalls on its own, displays only, and the adapter works the same
without it.

## Tests

`tests/test_claude_code_adapter.py` (routing gates) and
`tests/test_claude_code_adapter_actions.py` (action, shell-write, and closeout
gates) in the GOATED source repo drive the adapter with hook inputs and transcripts in Claude Code's recorded shape,
including the recorded fixtures in `tests/fixtures/claude_code_adapter/`, and
checks the adapter's marker parser against `stack/fixtures/markers/lines.yaml`.
`tests/test_claude_code_adapter_review.py` covers the closeout's Review and
Verification items against scratch git repositories.
