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
   package beside it.
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

Route, skip and design-reads lines are read from the agent's reply text and
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
`standard` or `full` route also requires `session-start-progressive-disclosure`
when Claude Code can find that skill (a user, project, or plugin skill): the
router selects orientation on such a route from a brief, and the spawn-brief
template says the new session loads it first. The route line never names it,
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

| Gate | Kind | Holds | Clears when |
| --- | --- | --- | --- |
| `router-first` | strict | Writes, spawns, and commands while the router has not loaded in this session, or since the last compaction; a command made only of [plain reads](#plain-reads) passes | `using-goated-ai-skills` loads; or the session's first prompt is a brief with a route line (see above), until a typed prompt opens a turn |
| `route-line` | strict | The first write or spawn after each user prompt until the current turn has a valid `goated-route:` line; also `goated-route: continue` when [missing or reset state](#failing-open) lost the task | A valid route line appears in the turn |
| `pipeline` | strict | Writes and spawns while a `requires:` skill of the current task has not loaded, or, in a session routed by its brief, on a `standard` or `full` route, an installed `session-start-progressive-disclosure` has not loaded (see above); a spawn of a [read-only subagent](#plain-reads) passes | Each listed skill loads, or a corrected route line drops it; the brief's orientation skill loads, or a corrected `goated-route: direct` or `lightweight` route line drops it |
| `commit` | strict | A `git commit` command (not `--dry-run`), or an MCP tool that records a commit, named `…__push_files`, `…__create_or_update_file`, `…__delete_file`, `…__git_commit`, `…__create_commit`, `…__commit_changes`, or `…__commit` | `commit-message` [counts as loaded](#loads), and an inline message (or the tool's `message`) passes the [content check](#content-checks); then a [change read](#change-reads) after the last change to any project file, before or after the load; an MCP tool skips that read when the turn changed no project file. Once these are met, the commit meets the [closeout](#closeout-at-commit) |
| `pull-request` | strict | `gh pr create` or `gh pr new`, `glab mr create` or `glab mr new`, or an MCP tool named `…__create_pull_request` or `…__create_merge_request` | `pr-description` [counts as loaded](#loads); then a [change read](#change-reads) after the last change to any project file, before or after the load; an MCP tool skips that read when the turn changed no project file |
| `pr-review` | justified-skip | A pull-request command or tool the `pull-request` gate holds, once that gate passes, when the pull request is [large](#large-pull-requests): 400 or more changed lines against its base | `standards-and-spec-review` [counts as loaded](#loads); then a [change read](#change-reads) after the load and the last change to any project file; an MCP tool skips that read when the turn changed no project file |
| `spawn` | strict | Starting an agent or session with a brief, except a [read-only subagent](#plain-reads) | `handoff` loads and `references/spawn-brief.md` is read, or `subagent-driven-development` loads and its implementer or reviewer prompt is read, each in this turn or an earlier one since the last compaction (see [Loads](#loads)); and the brief, on every spawn, passes the [content check](#content-checks) |
| `design` | justified-skip | The turn's first write adding five or more lines to a non-test code file inside the project folder (or any such write while the skill does not count as loaded). A test file never triggers it and is not counted when finding the turn's first such write: in TDD the test comes first and the design happens in the code after it | `software-design-principles` [counts as loaded](#loads), a valid [design-reads line](#design-references) is in the turn, and every [reference the edit requires](#design-references) has been read since the last compaction |
| `design-reads` | justified-skip | Any later write to a code or configuration file inside the project folder, once `software-design-principles` [counts as loaded](#loads), whose [signals or the turn's design-reads lines](#design-references) require a reference not read since the last compaction. The hold names each file and what selected it | Each required reference is read with the Read tool |
| `security` | justified-skip | A write, by a write tool or a shell command, to a security-sensitive path inside the project folder: dependency manifests and lockfiles (`requirements*.txt` included), `.env` and key files, files named for secrets, credentials, or tokens, auth, session, and permission code, migrations and schemas, CI, container, and deployment files. A sensitive word counts only when it stands alone in the path, so `tokenizer.py` and `author.py` are not held, while `api_token.py` and `userAuth.ts` are | `code-security-review` [counts as loaded](#loads) |
| `conflict-resolution` | justified-skip | A write while a merge conflict is open in the turn: an `Edit` or `MultiEdit` whose old text has a `<<<<<<<` or `>>>>>>>` marker at a line start; a write, by a write tool or a shell command such as `git checkout --theirs`, to a file a Read in the turn showed with such a marker; or any write after a git merge, rebase, cherry-pick, revert, or pull whose result in the turn reported a conflict. A finished abort, quit, continue, or skip of that operation, or a finished commit, ends the conflict and drops the Reads before it. Only the turn is read, not the repository, so a conflict opened in an earlier turn is caught only by markers the turn shows: an edit whose old text spans only `=======` and one side, in a file not read this turn, is not held, because `=======` alone is also a heading underline. A conflicting stash pop or apply is not held | `resolving-merge-conflicts` [counts as loaded](#loads) |
| `repeated-failure` | justified-skip | A write, by a write tool or a shell command, once one check command (as the closeout's Proof item recognises checks) has failed twice in a row in the turn. A shell command is held when any of its simple commands writes and is not itself a check, so `sed -i … && pytest` and `pytest \| tee out.txt` are held, while `pytest > out.txt` is a rerun. "The same check" is the same command text, whitespace aside, without a trailing pipe into output filters (`tail`, `head`, `grep`, `findstr`, `more`, `less`, `tee`, `Select-Object`, `Select-String`, `Out-Host`, `Out-String`) or a `2>&1` before it; so `pytest -q \| tail -20` and `pytest -q \| tail -40` are one check, and a narrowed rerun such as one test file of a failing suite is another. A piped run fails by what it prints (`N failed`, `N errors`, `FAILED (`, `FAIL`, `npm ERR!`, `error TS…`, `test result: FAILED`, and the like), since the exit code is the filter's; any other run fails by its exit code. A run whose only failures are test modules that could not load a missing module or name neither adds to the count nor resets it, whether or not it looks failed, since in TDD the first red run often fails because the module under test does not exist yet. Only each runner's own report counts: pytest's `ERROR collecting` section showing `ImportError while importing test module` or ending in an `ImportError` or `ModuleNotFoundError`; unittest's `_FailedTest` error ending in one of those; jest's `Test suite failed to run` with `Cannot find module`. A run counts as usual when it also shows a failure in a test that ran (`1 failed, 1 error`), when a module that is there fails to load (a `SyntaxError` or `NameError`: the edit-and-crash loop the gate exists for), or when a test only prints such text. These miss, toward holding: output cut before the runner names the cause (`pytest -q \| tail -3`), ts-jest's `TS2307`, and vitest's `Failed to load url`. The table is `LOAD_ERROR_SIGNS` in `actions.py`. A pass of the check resets its count; other commands between runs do not. A call that never ran does not count: one the adapter or another hook held, one refused at a permission prompt, or one interrupted | `diagnose` [counts as loaded](#loads) |
| `closeout` | justified-skip | A commit the `commit` gate lets through, or the end of the turn (a `Stop` hook), in a turn that changed code, that loaded `code-security-review` and changed a security-sensitive file, or that changed setup | Every item below is met or skipped |

The closeout items, each judged against the turn's last code change. A code
change is a write tool's file, or a file a shell command writes (its redirect
target, copy destination, or removed, moved, or edited file), inside the
project folder; a scratch or temp file elsewhere does not count. The `design`,
`design-reads`, and `security` gates use the same rule, so a scratch script outside the
project is not held. The `conflict-resolution` and `repeated-failure` gates
hold a write wherever its file is, since a worktree with a conflict, or the
code a failing check runs, may sit outside the project folder.

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
| Design red flags | `software-design-principles` loaded in the turn, or counts as loaded and the turn made an edit the `design` gate triggers on (five or more lines added to a non-test code file), so a later turn of small edits meets no Design item | `software-design-principles/references/red-flags.md` is read after the last code change that is not [comment-only](#comment-only-edits), then a [change read](#change-reads) after that read. The item repeats the question `red-flags.md` ends with (name one input that would break this change, and say what happens); no answer is checked | `software-design-principles` |
| Design citations | The Design red flags item applies, and the turn's edits required a [design reference](#design-references) | The turn cites a section of each required reference as `file#id`, such as `errors.md#crash-early`, in its reply text, the reply being finished included, or in a call field that carries route and skip lines: a shell or agent call's `description` or a Skill call's `args`, the commit call being judged included (see [Design references](#design-references)) | `software-design-principles` |
| Security | `code-security-review` counts as loaded and a security-sensitive file (the `security` gate's paths, code or not) changed | A [change read](#change-reads) after the load and the last sensitive change | `code-security-review` |
| Setup | The turn installed or added a dependency or tool by a command that names a package, or wrote an env or settings file (see below) | `setup-scribe` counts as loaded, the load before or after the change | `setup-scribe` |

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
package install counts wherever it runs; an env or settings file counts only
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
- **Everything else is per turn.** Route, skip, and design-reads lines, and
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
before it lands", and the shared policy loads it "when diff size … warrants
it". Neither gives a number. The `pr-review` gate's 400 changed lines, added
plus deleted, is this adapter's mechanical stand-in for "large", as the
`design` gate's five added lines are for a substantial edit; it is
`REVIEW_MIN_LINES` in `actions.py`. Risk, unclear acceptance, and uncertain
conventions, the policy's other reasons, are left to the router.

The transcript does not hold a branch's size, so this gate is the one place
the adapter runs commands. When a pull-request call would otherwise be held
by `pr-review` (the `pull-request` gate passed, and no load, change read, or
skip line has cleared `pr-review`), the adapter asks git, in the hook's
working folder, which of the candidate refs below exist (`git for-each-ref`),
then measures the first base and head found:

```text
git diff --shortstat --no-ext-diff --no-textconv <base>...<head> --
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

### Design references

`software-design-principles` keeps its reasoning in reference files and names,
for each moment of a change, which to read; it asks the agent to write a
design-reads line, `goated-design-reads: <file>, <file>` or
`goated-design-reads: none: <reason>`, whose grammar
`stack/fixtures/markers/README.md` owns. The `design` and `design-reads` gates
enforce those reads where the skill is loaded.

The rules live in one place,
[`goated_adapter/design_reads.py`](goated_adapter/design_reads.py), with the
test-path rule the closeout shares; only what counts as code, and where a
file sits in the project, stay with the other action gates, which pass in
their answers. They apply to an edit of
a code file, or of a configuration file (`.yaml`, `.yml`, `.toml`, `.json`,
`.env`, `.env.*`, `settings.*`) that is neither a lock file (`*-lock.json`,
`pnpm-lock.yaml`, `npm-shrinkwrap.json`) nor under a test path.

An edit requires the references the turn's valid design-reads lines name
(their union) plus those its signals select. `red-flags.md`, which the
closeout requires, adds nothing; any other name that is not a reference
(`proces.md`) requires nothing, and a hold quotes it as not a design
reference.

Signals are judged on what the edit adds: the lines of its new text, or of a
`Write`'s text, that the text it replaces did not hold, indentation aside. A
`Write` over a file on disk is compared with that file. A definition whose
name the old text already defined, as in a signature change, is not new.
Comments and docstrings are left out of the code the error and concurrency
signals read, so `# try the cache, then raise` selects neither.

A **small edit**, one writing fewer than five lines as the `design` gate counts
them (every line of the text it writes, unchanged context and a trailing
newline's empty line included; `DESIGN_MIN_LINES` in `actions.py`),
selects no reference by the kind of file or text it touches: no `coding.md`
for a test file, no `decoupling.md` for a configuration file or the third
code file, and no `readability.md` for a comment or docstring.
`software-design-principles` states this rule; the adapter enforces it.
Outside test files, which get no signal read from the code, signals read from
the added code apply at any size: a new code file or public top-level
definition, error handling, and concurrency. A design-reads line
still requires every reference it names. An edit whose added lines cannot be
counted, such as a `MultiEdit` with an `edits` entry that is not an edit, is
not small. A small edit that requires nothing adds nothing for the closeout's
Design citations item to ask for.

| Reference | Selected when the edit |
| --- | --- |
| `process.md` | creates a code file (a `Write` to a code file no earlier write in the turn made and that is not on disk), or adds a public top-level definition: an unindented line starting with `def`, `async def`, `class`, `function`, `export`, `func`, `fn`, `pub fn`, `public`, `interface`, `struct`, `enum`, `trait`, `impl`, or `defmodule`, whose name does not start with `_`; a shell `export NAME=` is not one |
| `complexity-and-modules.md` | the same as `process.md` |
| `decoupling.md` | is not small, and edits a configuration file or is to the third or later distinct non-test code file the turn edits |
| `readability.md` | the same as `process.md`, or is not small and adds a comment or docstring: a line opening with `#`, `//`, `/*`, `*`, `"""`, `'''`, `-- `, or `<!--`, a line inside a docstring or block comment, or a trailing `#` or `//` comment after two spaces |
| `errors.md` | adds code holding `try`, `except`, `catch`, `raise`, `throw`, `finally`, `defer` as words, or `with open` |
| `coding.md` | is not small and edits a test file; a test file selects nothing else |
| `concurrency.md` | adds code holding `threading`, `Lock`, `RLock`, `Mutex`, `asyncio`, `synchronized`, `Promise.all`, a word starting `Atomic`, or `go func` |
| `differences.md` | never selected; only a design-reads line requires it |

A typical change, one new public function with a docstring and error
handling, its caller, and its test, requires five: `process.md`,
`complexity-and-modules.md`, `readability.md`, `errors.md`, and `coding.md`.
Tune the signals from the skill-usage mod's counts.

A reference counts as read after a finished `Read` of a path ending in
`software-design-principles/references/<file>`, in this turn or an earlier
one, until the next compaction: the [state](#state) keeps the names read, a
resumed session keeps them, and a compaction's or `/clear`'s `SessionStart`
clears them, so each reference is required at most once per context window.
The skill's load counts the same way (see [Loads](#loads)), while the
design-reads line counts only in its turn.
A shell command printing one does not count. A skip line or a typed `skip
software-design-principles` clears both gates for the turn.

The first substantial non-test code edit of a turn meets `design`, which asks
for what is missing: the load, the line, and the reads. A later edit, or any
test file edit once the skill counts as loaded, meets `design-reads`, which
asks only for reads; a test file edit that is not small still requires
`coding.md`. A small edit while the skill does not count as loaded is not
held, as before.

At closeout, the Design citations item asks for a citation of each reference
the turn required, whether read in this turn or an earlier one: the turn
cites at least one section id of each, with how it shaped the change or why
it did not apply, as the skill's citation convention asks.
The turn's required set is what the `design` and `design-reads` gates
required of its edits: when the skill is loaded and a gate lets an edit of a
project file through, the adapter records that edit's required references in
its [state](#state), by the call's `tool_use_id`, and the closeout unions
those of the turn's edits that finished. An edit made before the skill
loaded, an edit a hold or the user stopped, and an edit whose hook input
names no `tool_use_id` add nothing.

A citation is `<file>#<id>`, bare, backticked, or after a path
(`references/errors.md#crash-early`), anywhere in the turn's reply text,
inside a quote or a code block too, or in the call fields that carry
[route and skip lines](#what-it-holds): the `description` of a shell or
agent call and the `args` of a Skill call. Any call of the turn counts, a
held call and the commit call being judged included, so a commit held for a
missing citation passes when made again with the citation in its
`description`. Claude Code can store the text of a message that makes a
tool call as a summary that drops the citation (see
[Known Limits](#known-limits)), and before a commit every message makes one.
No other field counts: a command, an edit's or a file's text, and an MCP
tool's `description` carry no citation. Its id must be a section id that file
declares in an `<!-- id: #name -->` comment in the installed skill's
`references/`, so an id of another reference, or a bare `#crash-early`, does
not count. An id whose `##` heading groups `###` sections, such as
`#errors`, names a part of the file, not a section, so it does not count
either; the remaining ids are the ones the skill's Section Index lists, which
a test checks. The ids come from those files, not from a copy in the adapter:
a user skill is looked for first, then project skills, then plugin skills,
the newest cached version first. The item names each uncited reference,
points to the Section Index for its ids, and names the call fields without
backticks, as the unseen-line advice does. At commit the report is not
written yet, and reply text may not be seen, so a shell commit is asked for
the citation in its own description, or in a call made in an earlier
message. An MCP commit tool carries no citation in any field, so it is asked
for one in such an earlier call. At `Stop` the item asks for it in the reply. Whether a citation says anything
useful is not judged.

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
- edits in place with `sed -i` or `perl -i`;
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
  `git stash pop|apply`.

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

### Plain reads

Before the router loads, `router-first` passes a `Bash` or `PowerShell`
command made only of plain reads, as it passes Read and Grep, so an agent can
look around before it routes. Each simple command must be one of:

- `cat`, `head`, `tail`, `ls`, `dir`, `grep`, `rg` (without `--pre` or
  `--hostname-bin`), or `wc`;
- `find` without `-exec`, `-execdir`, `-ok`, `-okdir`, `-delete`, `-fprint`,
  `-fprint0`, `-fprintf`, or `-fls`;
- `git status`, `git diff`, `git log`, or `git show`, without `--output`,
  `--ext-diff`, `--textconv`, or `--show-signature`, and with no option before
  the subcommand but `-C <path>`, `--no-pager`, or `-P`;
- `Get-Content`, `Get-ChildItem`, or `Select-String`, or their aliases `gc`,
  `gci`, and `sls`.

The command word must be the bare name, in any case: `./cat`, `/bin/cat`,
or `cat.cmd` may be any program, so it is held. The commands may be joined by
pipes, `&&`, `||`, `;`, or newlines. The call is held when any part of it is
something else: another or unknown command, a wrapper such as `sudo` or
`xargs` or a variable assignment before the command, any output redirect, a
heredoc, a subshell, group, or script block, a process substitution, or a
background `&`. A redirect into a null device is held too, since a null
device in one shell is a real file in another: `nul` in bash, `/dev/null` in
PowerShell. Duplicating a descriptor (`2>&1`) and an input redirect
(`< a.py`) are fine.

The call is also held when its text holds anything the lexical reading may
not follow as the shell does, even inside quotes: a `$` (variables,
`$(…)` inside double quotes, `${x:=…}`, arithmetic), a backtick, a backslash
(an escape in bash, where `-del\ete` is `-delete`, but a plain character in
PowerShell), `<<<`, a `>&` not followed by a whole descriptor (`>&2` is
fine, `>&2x` writes the file `2x`), any character but printable ASCII, a
newline, or a tab (curly quotes, which PowerShell reads as quotes; a lone
carriage return or U+2028, which it reads as a line break), a PowerShell
block comment `<#`, a PowerShell here-string, `[[` or `]]` (outside command
position a plain word, so a `>` after it redirects), or `//`, which starts a
UNC path read over the network, where Windows may send the user's
credentials. So a Windows path with backslashes, such as
`Get-Content src\a.py`, is held; Read or a forward-slash path passes. When
the analysis cannot tell, the call is held. The lists are
`READ_ONLY_COMMANDS`, `READ_ONLY_REFUSED_ARGS`, `GIT_READ_SUBCOMMANDS`,
`GIT_READ_REFUSED_ARGS`, and `NOT_PLAINLY_SPELLED_RE` in `shell.py`. Once the
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
Design citations, Security, or Setup. The hold's first line is the
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
| Design | The red-flags read, which itself follows the last code change that is not [comment-only](#comment-only-edits) |
| Security | The `code-security-review` load and the last change to a security-sensitive file |
| Commit, pull request | The last change to any project file, code or not, including changes a subagent spawned in the turn made, before or after the skill load |
| Pull-request review | The `standards-and-spec-review` load and that last change |

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
  `pull-request`, `pr-review`, `spawn`, `design`, `design-reads`, `security`,
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
  `- <Label>: `, with `Proof`, `Unfinished`, `Docs`, `Design`, `Security`,
  or `Setup` as the label; the two design items share `Design`. Each item
  names the skill it asks for, backticked or as the skill of the skip line
  it offers: the mod counts an item through that skill, so an item that
  names none is not counted. These labels
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
  `design`, `design-reads`, `security`, `conflict-resolution`,
  `repeated-failure`, `pr-review`) says that a line in reply text may not be
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
  `software-design-principles` has loaded, the `design` hold (asking for the
  design-reads line or reads) and the `design-reads` hold name it only in
  their skip line, and backtick each reference by its path,
  `software-design-principles/references/<file>`, which is no bare name. A
  `design` hold that asks for the line backticks its form,
  `goated-design-reads: <file>, <file>`; the skill-usage mod reads both.
- The closeout's Design citations item names where a citation counts, the
  call fields without backticks, like the unseen-line advice. Its
  commit-time text asks for the citation in a shell commit's own description
  or, for an MCP commit tool, in an earlier call's field, not in a report not
  yet written, and says why reply text may not be seen; its `Stop` text asks
  for it in the reply.
  Both Design red-flags texts repeat the question `red-flags.md` ends with;
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
opened, after checking the transcript's record of who wrote it. Text an agent
writes never counts. Matching ignores case, harness `<system-reminder>`
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
  `design-reads`, `security`, `conflict-resolution`, `repeated-failure`) apply, judged from
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

## Session Start Notices

At the first session start the adapter says once, in a notice you see and in
the agent's context, when:

- the GOATED shared policy is not in any instruction file Claude Code loads;
- the `using-goated-ai-skills` skill is not among your user, project, or
  plugin skills. Without it, router-first never clears; type `skip routing` in
  a prompt to proceed, or install the router.

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
task, whether the router loaded, which GOATED skills loaded and which design
references and spawn-brief templates were read since the last compaction
(see [Loads](#loads)), which references each edit of the latest turn
required when the design gates judged it, the last turn seen, and the latest
typed overrides. It holds no prompt or reply
text beyond the short override phrases and a commit message the user typed.
Beside the state files, a `turn-markers/` folder holds one empty file per
session, and one per subagent of it, named for the turn whose hold gave the
[unseen-line advice](#hold-messages) in full. A new turn's claim replaces it,
and a `SessionStart` after compaction or `/clear` deletes the session's and
its subagents'.
The action and closeout gates keep no state of their own: they read the
current turn, the loads, design references, and templates read since the
last compaction, and, for the closeout's citation item, the references
recorded for the turn's edits. Files are not pruned automatically;
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
  cannot bring it back. The holds a line can clear, design-reads included, therefore point to the
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

- Shell analysis is lexical, not a shell. These forms are not seen, so a
  write in them meets only `router-first` and a commit or pull request in
  them meets no action gate:
  - a command run through another shell or evaluator: `bash -c`, `sh -c`,
    `eval`, `Invoke-Expression`, `Start-Process`, or a heredoc fed to a shell
    (`bash <<'EOF'`); only whether a `bash -c`, `sh -c`, `zsh -c`, or
    `pwsh -Command` line is a check is read;
  - command substitution with backticks, or `$(…)` inside double quotes;
  - a write inside an interpreter or script (`python -c "open(...)"`,
    `node build.js`), including an interpreter fed a script on stdin
    (`python - <<'EOF'`, `node < build.js`), or by an archive tool
    (`tar -x`, `unzip`);
  - git aliases (`git ci`), and `gh api` calls that create a pull request
    (`gh api repos/<owner>/<repo>/pulls`);
  - MCP tools that commit or open pull requests under names other than those
    listed in [What It Holds](#what-it-holds).

  An agent working around the holds this way is the case the next item
  describes.
- A [plain read](#plain-reads) can still run a program that git config
  names, such as `core.fsmonitor` under `git status`, or `diff.external` and
  a `textconv` driver set for the repository, which a plain `git diff`,
  `git show`, or `git log -p` runs too. Refusing the `--ext-diff` and
  `--textconv` options does not stop them. A passing read can also hang:
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
  the change does, and the design gates do not see shell writes. A design-reads
  line in the held call's own message is not visible yet, like a skip line.
  The design-reads signals are word and shape matches on lines, so a `try` in
  a string selects `errors.md`, and a `NotebookEdit` cell counts all its text
  as added. A `Write`'s file on disk, read to tell what it adds, is the one
  design input outside the transcript. A design-reads line names files, never
  a reason per file, so the adapter cannot tell a reference read and applied
  from one read alone.
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
- The Design citations item fails open: with no installed
  `software-design-principles` found, it asks for nothing, and a reference
  whose file cannot be read, or that declares no section, needs no citation.
  There is no closeout inside a subagent, and the parent does not record a
  subagent's edits, so a subagent's design edits need no citation. A citation
  in a reply that also makes a tool call can be lost the way a route line
  is, so the item points to the call fields too.
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
  would announce one.
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
