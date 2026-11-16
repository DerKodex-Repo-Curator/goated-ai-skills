# GOATED Adapter For Claude Code

An optional set of Claude Code hooks that holds writes, spawns, and commands
until the GOATED router and the skills its route requires have loaded in the
current task. It also holds commits, pull requests, spawns, design changes,
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

| Gate | Kind | Holds | Clears when |
| --- | --- | --- | --- |
| `router-first` | strict | Writes, spawns, and commands while the router has not loaded in this session, or since the last compaction | `using-goated-ai-skills` loads |
| `route-line` | strict | The first write or spawn after each user prompt until the current turn has a valid `goated-route:` line; also `goated-route: continue` when [missing or reset state](#failing-open) lost the task | A valid route line appears in the turn |
| `pipeline` | strict | Writes and spawns while a `requires:` skill of the current task has not loaded | Each listed skill loads, or a corrected route line drops it |
| `commit` | strict | A `git commit` command (not `--dry-run`), or an MCP tool that records a commit, named `…__push_files`, `…__create_or_update_file`, `…__delete_file`, `…__git_commit`, `…__create_commit`, `…__commit_changes`, or `…__commit` | `commit-message` loads in the turn, and an inline message (or the tool's `message`) passes the [content check](#content-checks); then a [change read](#change-reads) after the load and the last change to any project file; an MCP tool skips that read when the turn changed no project file |
| `pull-request` | strict | `gh pr create` or `gh pr new`, `glab mr create` or `glab mr new`, or an MCP tool named `…__create_pull_request` or `…__create_merge_request` | `pr-description` loads in the turn; then a [change read](#change-reads) after the load and the last change to any project file; an MCP tool skips that read when the turn changed no project file |
| `spawn` | strict | Starting an agent or session with a brief | `handoff` loads and `references/spawn-brief.md` is read, or `subagent-driven-development` loads and its implementer or reviewer prompt is read, all in the turn; and the brief passes the [content check](#content-checks) |
| `design` | justified-skip | A write adding five or more lines to a code file | `software-design-principles` loads in the turn |
| `security` | justified-skip | A write, by a write tool or a shell command, to a security-sensitive path: dependency manifests and lockfiles (`requirements*.txt` included), `.env` and key files, files named for secrets, credentials, or tokens, auth, session, and permission code, migrations and schemas, CI, container, and deployment files. A sensitive word counts only when it stands alone in the path, so `tokenizer.py` and `author.py` are not held, while `api_token.py` and `userAuth.ts` are | `code-security-review` loads in the turn |
| `conflict-resolution` | justified-skip | A write while a merge conflict is open in the turn: an `Edit` or `MultiEdit` whose old text has a `<<<<<<<` or `>>>>>>>` marker at a line start, or any write, by a write tool or a shell command, after a git merge, rebase, cherry-pick, revert, or pull whose result in the turn reported a conflict. Only the turn is read, not the repository, so a conflict opened in an earlier turn is caught only by its markers. A conflicting stash pop or apply is not held | `resolving-merge-conflicts` loads in the turn |
| `closeout` | justified-skip | The end of a turn that changed code, or that loaded `code-security-review` and changed a security-sensitive file (a `Stop` hook) | Every item below is met or skipped |

The closeout items, each judged against the turn's last code change. A code
change is a write tool's file, or a file a shell command writes (its redirect
target, copy destination, or removed, moved, or edited file), inside the
project folder; a scratch or temp file elsewhere does not count. A shell write
whose files the command does not name (`git apply`, `patch`, a download
without an output name) counts as a change to non-test code. Code a subagent
changed counts too, at the point the parent spawned it; if the subagent ran a
check after its own last change, that change is already proved.

| Item | Needed when | Met by | Skip line names |
| --- | --- | --- | --- |
| Proof | A change not already proved | A check command run after the last code change: a test runner, linter, type checker, or build tool (`pytest`, `python -m unittest`, `npm test`, `cargo test`, `go vet`, `tsc`, `make check`, and the like, also through `uv run` or `npx`), or a script whose name says test, check, lint, verify, validate, or build (`scripts/validate_skills.py`) | `verification-before-completion` |
| Unfinished work | The last check after the change failed | `handoff` loads | `handoff` |
| Docs | A code file outside the tests changed | `doc-sync` loads, then a [change read](#change-reads) after the load and the last code change | `doc-sync` |
| Design red flags | `software-design-principles` loaded in the turn | `software-design-principles/references/red-flags.md` is read after the last change, then a [change read](#change-reads) after that read | `software-design-principles` |
| Security | `code-security-review` loaded in the turn and a security-sensitive file (the `security` gate's paths, code or not) changed | A [change read](#change-reads) after the load and the last sensitive change | `code-security-review` |

- **Writes** are `Edit`, `Write`, `MultiEdit`, and `NotebookEdit`, and a
  `Bash` or `PowerShell` command that writes files (see
  [Shell writes](#shell-writes)). **Spawns** are `Agent` (or `Task`, its name
  in older Claude Code versions), `mcp__ccd_session__start_session`, and
  `mcp__ccd_session__hand_off_to_session`; they hand work on, so they are held
  like writes. A session tool call with no brief, such as an offer card, is not
  a spawn for the `spawn` gate. **Commands** are `Bash` and `PowerShell`.
  Every other tool, including reads and the Skill tool, is never held.
- **Code** is a file with a programming-language extension such as `.py`,
  `.ts`, `.go`, `.ps1`, or `.sh`; the list is `CODE_EXTENSIONS` in
  `actions.py`. Docs and config files are not code. A test file is one under
  `tests/`, `test/`, `spec/`, or `__tests__/`, or named `test_*`, `*_test.*`,
  `*.test.*`, or `*.spec.*`.
- **A task** starts at a route line that is not `continue` and runs through
  later `goated-route: continue` turns. Route lines in one turn with no write
  or spawn that ran between them are one task, corrected: the last one is its
  route. A call the adapter held never ran, and neither did an edit that
  failed; a shell write or spawn that ended in an error counts as run. A
  `continue` after such a line in the same turn keeps that task. In a session
  with no task yet, such as one started from another session to continue work
  begun there, a turn whose only route lines are `continue` starts a task that
  requires no skills.
  `goated-route: direct` exempts the task from the pipeline gate.
- **Loads that count for a task** are the ones made earlier in the turn that
  starts it, unless another task's route line came between the load and the
  task's first route line, plus the loads after it. A load in an earlier turn
  never counts.
- **Action and closeout proof is per turn.** A skill loaded in an earlier
  turn does not cover a commit, spawn, or edit in a later one, even within the
  same task. Within a turn, a hold stops firing as soon as the turn shows
  compliance: after `commit-message` loads, every later commit in that turn
  passes its skill check.
- **Dropping a required skill.** A `goated-skip` line never clears a strict
  hold. If a route names a skill that does not apply, the agent writes a
  corrected route line without it; the last route line wins, as the shared
  policy says.
- **Compaction** clears the proof: the router and the task's required skills
  must load again. The route itself carries over, so `goated-route: continue`
  still works. A compaction also starts a new turn, so action proof restarts.
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

### Shell writes

The adapter splits a command into its simple commands (joined by `;`, `&&`,
`||`, `|`, `&`, newlines, parentheses, braces, or `$(`) and reads each one's
real command word past wrappers (`sudo -u <user>`, `env`, `timeout <n>`,
`nice`, `nohup`, `xargs`, `cmd /c`), a quoted or full path to the program
(`"git"`, `& "C:\…\git.exe"`), and line continuations (`\` in bash, a
backtick in PowerShell). A `Bash` or `PowerShell` command meets the
`route-line` and `pipeline` gates, like an edit, when one of its commands:

- redirects output into a file (`>`, `>>`, `&>`, `2>`), except into a null
  device (`/dev/null`, `$null`, `NUL`) or another stream (`2>&1`);
- runs `tee`, `Tee-Object`, `cp`, `mv`, `rm`, `rmdir`, `touch`, `truncate`,
  `ln`, `unlink`, `shred`, or `patch`;
- edits in place with `sed -i` or `perl -i`;
- runs `Set-Content`, `Add-Content`, `Out-File`, `Clear-Content`, `New-Item`,
  `Copy-Item`, `Move-Item`, `Remove-Item`, `Rename-Item`, `Export-Csv`, or
  `Export-Clixml`, or one of the stock Windows PowerShell 5.1 aliases (`sc`,
  `ac`, `clc`, `del`, `erase`, `copy`, `move`, `ren`, `rd`, `ri`, `mi`, `cpi`,
  `ni`, `rni`), or a .NET `[IO.File]::Write…` style call;
- downloads to a file: `curl -o <file>` (also `-sSLo <file>`) or `curl -O`,
  `wget` unless it writes to standard output, or `Invoke-WebRequest -OutFile`;
- runs `git apply`, `git am`, `git restore`, `git mv`, `git rm`, `git clean`,
  `git checkout -- <path>`, `git checkout <rev> <path>`, `git reset --hard`, or
  `git stash pop|apply`.

Text inside quotes, heredoc bodies, PowerShell here-strings, and comments is
ignored, as are comparisons inside `[[ ]]` and arithmetic in `$(( ))`, so
`echo "a > b"`, `[[ $a > $b ]]`, and `ls # a > b` write nothing. Reads, test
runs, `git status`, and `git checkout <branch>` stay free. Commit and
pull-request commands are recognized the same way, per command, so
`echo gh pr create` opens nothing.

### Change reads

A hold whose step reviews or describes the change needs the change itself in
front of the agent, not only the skill: the closeout's Docs, Design, and
Security items, the commit, and the pull request. A **change read** is a
finished call, made after the item's skill load or red-flags read and after
the last change the step covers:

| Step | The change read must follow |
| --- | --- |
| Docs | The `doc-sync` load and the last code change |
| Design | The red-flags read, which itself follows the last code change |
| Security | The `code-security-review` load and the last change to a security-sensitive file |
| Commit, pull request | The skill load and the last change to any project file, code or not, including changes a subagent spawned in the turn made |

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

### Hold messages

Every hold, whether a denied tool call or a blocked `Stop`, returns a reason
whose first line has one stable format, which the skill-usage mod parses:

```text
goated-hold: <gate> | <kind>
<what the agent must do, in plain words>
```

- `<gate>` is one of `router-first`, `route-line`, `pipeline`, `commit`,
  `pull-request`, `spawn`, `design`, `security`, `conflict-resolution`, or
  `closeout`.
- `<kind>` is `strict` or `justified-skip`.
- The first line matches
  `^goated-hold: ([a-z]+(?:-[a-z]+)*) \| (strict|justified-skip)$`.
- The lines after it are guidance for the agent and may change between
  releases; do not parse their wording. They backtick each skill they ask
  for by its bare name, which is all the skill-usage mod reads from them,
  and backtick no other bare word: a file name is quoted, and the grammar's
  words appear backticked only inside a whole line such as
  `goated-skip: <skill>: <reason>`. A test checks every hold text against
  the registry's skill names.
- Each named skill is a separate requirement, except in the `spawn` hold,
  whose two skills are alternatives: `handoff` or
  `subagent-driven-development`, either of which answers it.
- A hold asks for a load in the current turn. A skill loaded in an earlier
  turn does not answer it.
- A hold or closeout item that asks for a [change read](#change-reads) once
  its skill has loaded names that skill without backticks, or only in its
  skip line, since no load answers it: the commit and pull-request holds name
  no skill, and the closeout offers the skill only as a skip line.

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
writes never counts. Matching ignores case and harness `<system-reminder>`
blocks, and a phrase negated just before it, such as "don't skip routing",
"never skip tdd", or "no need to skip doc-sync", is not an override.

| Typed phrase | Effect for that turn |
| --- | --- |
| `skip routing`, `skip the router` | Stands down `router-first`, `route-line`, and `pipeline` |
| `skip <skill>`, `skip the <skill> skill` | Stands down every requirement for that skill: in `pipeline`, in an action gate, or in a closeout item. `skip using-goated-ai-skills` also stands down `router-first`. `<skill>` must be a skill Claude Code can find (user, project, or plugin skills); when none can be found, a GOATED registry skill name. So "skip line" or "skip the first two lines" is not an override |
| `commit message: <text>`, `commit with the message "<text>"`, or a fenced block right after such a phrase | Stands down the `commit` hold for a commit whose inline message has the same subject line (whitespace aside); a commit with another message, or with none inline, is still held |

Claude Code also submits prompts nobody typed in this session:

- **Background results**, such as the `<task-notification>` that reports a
  finished background task, or a desktop-app side-session event. They carry
  agent output, so they never yield overrides, and they do not start a new
  turn: the typed prompt's route line and overrides still cover what follows.
- **Requests from elsewhere**, such as a subagent's final report, a message
  from another Claude session, a brief from the session that started this
  one, or any prompt whose recorded origin is not a person. They start a new
  turn, which needs its own route line (`goated-route: continue` when it
  continues the current task), and never carry overrides: not ones they quote,
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
`additionalContext`. A notice reaches a Claude Code mod with no text, so the
[skill-usage mod](skill-usage/README.md) counts overrides from that context.
The phrase set lives in [`goated_adapter/overrides.py`](goated_adapter/overrides.py);
change it and this table together.

## Subagents

A hook call from inside a subagent carries `agent_id`. There:

- the routing gates do not apply, because the parent's brief carries the route;
- the action gates (`commit`, `pull-request`, `spawn`, `design`, `security`,
  `conflict-resolution`) apply, judged from the subagent's own transcript, which Claude Code keeps in
  `<session-id>/subagents/agent-<agent_id>.jsonl` beside the main one. A
  subagent must load the skill itself: the parent's loads do not count;
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

It holds the current task's route and loads, whether missing or reset state
lost the task, whether the router loaded, the last turn seen, and the latest
typed overrides. It holds no prompt or reply
text beyond the short override phrases and a commit message the user typed.
The action and closeout gates keep no state: they read the current turn. Files are not pruned automatically;
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
  count yet. The agent then makes the call again in a later message, by which
  time the earlier one is recorded. The route-line hold says so.

- Shell analysis is lexical, not a shell. These forms are not seen, so a
  write in them meets only `router-first` and a commit or pull request in
  them meets no action gate:
  - a command run through another shell or evaluator: `bash -c`, `sh -c`,
    `eval`, `Invoke-Expression`, `Start-Process`, or a heredoc fed to a shell
    (`bash <<'EOF'`);
  - command substitution with backticks, or `$(…)` inside double quotes;
  - a write inside an interpreter or script (`python -c "open(...)"`,
    `node build.js`), or by an archive tool (`tar -x`, `unzip`);
  - git aliases (`git ci`), and `gh api` calls that create a pull request
    (`gh api repos/<owner>/<repo>/pulls`);
  - MCP tools that commit or open pull requests under names other than those
    listed in [What It Holds](#what-it-holds).

  An agent working around the holds this way is the case the next item
  describes.
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
- The design gate judges size by lines added in the tool input, not by what
  the change does, and does not see shell writes. The security gate judges by
  path alone. The conflict-resolution gate reads git's English messages
  (`Automatic merge failed`, `could not apply`, `could not revert`), so a git
  set to another language is not seen.
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
  hold, never a pass.

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
