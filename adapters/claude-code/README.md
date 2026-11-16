# GOATED Adapter For Claude Code

An optional set of Claude Code hooks that holds writes, spawns, and commands
until the GOATED router and the skills its route requires have loaded in the
current task. It enforces the portable contracts in
`skills/agent-workflows/using-goated-ai-skills/SKILL.md`, `stack/AGENTS.md`,
and `stack/fixtures/markers/README.md`; it adds no rules of its own
([ADR 0003](../../docs/adr/0003-opt-in-framework-enforcement-adapters.md)).

Skills work the same without it. Install it only if you want enforcement.

This release has the **routing gates** (Ticket 030). Commit, PR, spawn-brief,
design, security, shell-write, and closeout gates arrive in Ticket 031.

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
4. Merge the three entries under `hooks` into a Claude Code settings file:
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

Remove the three adapter entries from the settings file, or move them to a
file Claude Code does not load. Start a new session to be sure the change
applies. Claude Code's `"disableAllHooks": true` also stops the adapter, along
with every other hook you have.

## Remove

1. Remove the three adapter entries from the settings file.
2. Delete the copied `claude-code/` folder.
3. Delete the state folder `goated-claude-code-adapter/` (see [State](#state)).

Skills keep working unchanged.

## What It Holds

The rule table lives in [`goated_adapter/gates.py`](goated_adapter/gates.py).
Every gate is strict: a hold clears only on proof of use or a typed user
override.

| Gate | Holds | Clears when |
| --- | --- | --- |
| `router-first` | Writes, spawns, and commands while the router has not loaded in this session, or since the last compaction | `using-goated-ai-skills` loads |
| `route-line` | The first write or spawn after each user prompt until the current turn has a valid `goated-route:` line; also `goated-route: continue` when the session has no task to continue | A valid route line appears in the turn |
| `pipeline` | Writes and spawns while a `requires:` skill of the current task has not loaded | Each listed skill loads, or a corrected route line drops it |

- **Writes** are `Edit`, `Write`, `MultiEdit`, and `NotebookEdit`.
  **Spawns** are `Agent`, `mcp__ccd_session__start_session`, and
  `mcp__ccd_session__hand_off_to_session`; they hand work on, so they are held
  like writes. **Commands** are `Bash` and `PowerShell`. Every other tool,
  including reads and the Skill tool, is never held.
- **A task** starts at the turn whose route line is not `continue` and runs
  through later `goated-route: continue` turns. Only loads after the route line
  that starts a task count for it, so a load from an earlier task never
  satisfies a new one, even within one turn. `goated-route: direct` exempts the
  task from the pipeline gate.
- **Dropping a required skill.** A `goated-skip` line does not clear a routing
  hold. If a route names a skill that does not apply, the agent writes a
  corrected route line without it; the last route line wins, as the shared
  policy says.
- **Compaction** clears the proof: the router and the task's required skills
  must load again. The route itself carries over, so `goated-route: continue`
  still works.
- **Proof of use** is a successful Skill-tool load read from the transcript (a
  `Skill` tool call whose result is not an error), or a skill the user invoked
  by typing `/<skill>`. Naming a skill in text is not proof. A load counts by
  its bare name only: `someplugin:tdd` does not satisfy `requires: tdd`. If you
  installed GOATED as a Claude Code plugin, set `GOATED_ADAPTER_SKILL_NAMESPACES`
  to its namespace (comma-separated for several), for example in the settings
  file's `env` block.
- **No free retry.** Every hold is decided from the transcript, so repeating a
  held call unchanged gives the same answer until the proof appears.

A held call returns its reason to the agent. The first line names the gate and
its kind, and the rest says what to do:

```text
goated-hold: <gate> | strict
<what the agent must do>
```

Ticket 031 adds justified-skip holds and fixes this as the stable format the
skill-usage mod parses.

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
| `skip <skill>`, `skip the <skill> skill` | Stands down the `pipeline` requirement for that skill; `skip using-goated-ai-skills` also stands down `router-first` |

Claude Code also submits prompts nobody typed in this session:

- **Background results**, such as the `<task-notification>` that reports a
  finished background task, or a desktop-app side-session event. They carry
  agent output, so they never yield overrides, and they do not start a new
  turn: the typed prompt's route line and overrides still cover what follows.
- **Requests from elsewhere**, such as a message from another Claude session,
  a brief from the session that started this one, or any prompt whose recorded
  origin is not a person. They start a new turn, which needs its own route
  line, and never carry overrides.

Claude Code shows a short notice when the adapter records an override. The
phrase set lives in [`goated_adapter/overrides.py`](goated_adapter/overrides.py);
change it and this table together.

## Subagents

A hook call from inside a subagent carries `agent_id`. The routing gates skip
those calls, because the parent's brief carries the route.

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
- the transcript cannot be read, or the current turn alone is larger than the
  64 MB read limit. Older turns beyond the limit are simply not read, as if
  they had been seen;
- the transcript has not caught up with the call being judged. Claude Code
  writes the transcript asynchronously, so the hook waits up to 1.5 seconds
  for the call's own `tool_use` entry first (see [Latency](#latency));
- the adapter hits an internal error;
- on macOS and Linux, its state folder is a link, belongs to another user, or
  is writable by others, because planted state there could make holds pass.

Saved state that cannot be read, or has an unexpected shape, is reset with a
warning; a reset can only re-hold, never pass. If saving state fails, for
example while a parallel hook has the file open on Windows, the hold decision
still stands and a warning says the state was not saved.

## State

One small JSON file per session in a `goated-claude-code-adapter/` folder:

- on macOS and Linux, under `$XDG_STATE_HOME`, or `~/.local/state` when that
  is not set, rather than the shared `/tmp`, so another local user cannot
  pre-create it;
- on Windows, under the per-user temporary folder (`%TEMP%`);
- anywhere you choose with `GOATED_ADAPTER_STATE_DIR`.

It holds the current task's route and loads, whether the router loaded, the
last turn seen, and the latest typed overrides. It holds no prompt or reply
text beyond the short override phrases. Files are not pruned automatically;
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
the `json` and `re` imports.

In live headless sessions on the same machine (Claude Code 2.1.325), the call
being judged was never yet in the transcript when the hook started. Its entry
appeared 54 to 114 ms later, over 7 main-agent calls, so a held-or-passed
`PreToolUse` call costs roughly the figures above plus that wait. The 1.5-second
budget leaves headroom before the hook fails open.

## Known Limits

- Until Ticket 031, a file written through `Bash` or `PowerShell` meets only
  `router-first`. Ticket 031 holds shell commands that write files like edits.
- The adapter guards against agents skipping skills, not against an agent
  working to defeat it. An agent with shell access could edit the transcript,
  the state file, or the settings that install the hooks. Defending against
  that is out of scope; review what agents change if it matters to you.
- Prompt classification relies on transcript fields and text wrappers seen in
  Claude Code 2.1.3xx (`origin`, `turnOrigin`, `<task-notification>`,
  `<cross-session-message>`, and others). A new kind of machine-written prompt
  with no `origin` and an unknown wrapper would be treated as typed.
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

`tests/test_claude_code_adapter.py` in the GOATED source repo drives the
adapter with hook inputs and transcripts in Claude Code's recorded shape,
including the recorded fixtures in `tests/fixtures/claude_code_adapter/`, and
checks the adapter's marker parser against `stack/fixtures/markers/lines.yaml`.
