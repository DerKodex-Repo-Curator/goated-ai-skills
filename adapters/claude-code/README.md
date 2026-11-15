# GOATED Adapter For Claude Code

An optional set of Claude Code hooks that holds writes and commands until the
GOATED router and the skills its route requires have loaded in the current
task. It enforces the portable contracts in
`skills/agent-workflows/using-goated-ai-skills/SKILL.md`, `stack/AGENTS.md`,
and `stack/fixtures/markers/README.md`; it adds no rules of its own
([ADR 0003](../../docs/adr/0003-opt-in-framework-enforcement-adapters.md)).

Skills work the same without it. Install it only if you want enforcement.

This release has the **routing gates** (Ticket 030). Commit, PR, spawn,
design, security, and closeout gates arrive in Ticket 031.

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
3. Delete the state folder: `goated-claude-code-adapter/` in the operating
   system's temporary folder, or the folder `GOATED_ADAPTER_STATE_DIR` names.

Skills keep working unchanged.

## What It Holds

The rule table lives in [`goated_adapter/gates.py`](goated_adapter/gates.py).

| Gate | Holds | Clears when | Kind |
| --- | --- | --- | --- |
| `router-first` | Writes and commands while the router has not loaded in this session, or since the last compaction | `using-goated-ai-skills` loads with the Skill tool | strict |
| `route-line` | The first write after each user prompt until the current turn has a valid `goated-route:` line; also `goated-route: continue` when the session has no task to continue | A valid route line appears in the turn | strict |
| `pipeline` | Writes while a `requires:` skill of the current task has not loaded | Each listed skill loads, or has a `goated-skip: <skill>: <reason>` line | justified-skip |

- **Writes** are `Edit`, `Write`, `MultiEdit`, and `NotebookEdit`.
  **Commands** are `Bash` and `PowerShell`. Every other tool, including reads
  and the Skill tool, is never held.
- **A task** starts at the turn whose route line is not `continue` and runs
  through later `goated-route: continue` turns. Loads and skips count for the
  task they happen in. A new route starts a new task, so a load from an
  earlier task never satisfies it. `goated-route: direct` exempts the task from
  the pipeline gate.
- **Proof of use** is a successful Skill-tool load read from the transcript:
  a `Skill` tool call whose result is not an error. Naming a skill in text is
  not proof.
- **No free retry.** Every hold is decided from the transcript, so repeating a
  held call unchanged gives the same answer until the proof appears.

A held call returns its reason to the agent. The first line names the gate and
its kind, and the rest says what to do:

```text
goated-hold: <gate> | <strict|justified-skip>
<what the agent must do>
```

Ticket 031 fixes this as the stable format the skill-usage mod parses.

## User Overrides

The user-prompt hook reads only what the user typed, so text an agent writes
never counts. An override applies to the turn of the prompt that contains it.
Matching ignores case and harness `<system-reminder>` blocks.

| Typed phrase | Effect for that turn |
| --- | --- |
| `skip routing`, `skip the router`, `no routing` | Stands down `router-first`, `route-line`, and `pipeline` |
| `skip <skill>`, `skip the <skill> skill` | Stands down the `pipeline` requirement for that skill; `skip using-goated-ai-skills` also stands down `router-first` |

Claude Code also submits some prompts itself, such as the
`<task-notification>` that reports a finished background task. Those carry
agent output, so they never yield overrides, and they do not start a new turn:
the typed prompt's route line and overrides still cover the work that follows.

Claude Code shows a short notice when the adapter records an override. The
phrase set lives in [`goated_adapter/overrides.py`](goated_adapter/overrides.py);
change it and this table together.

## Subagents

A hook call from inside a subagent carries `agent_id`. The routing gates skip
those calls, because the parent's brief carries the route.

## Failing Open

The adapter never blocks because of its own failure. It lets the call through
and shows a warning that starts `GOATED Claude Code adapter:` when:

- the hook input is not readable JSON or lacks `session_id` or
  `transcript_path`;
- the transcript cannot be read, or the current turn starts more than 64 MB
  from its end;
- the transcript has not caught up with the call being judged. Claude Code
  writes the transcript asynchronously, so the hook waits up to 1.5 seconds
  for the call's own `tool_use` entry first (see [Latency](#latency));
- the adapter hits an internal error.

Unreadable saved state is reset with a warning; a reset can only re-hold, never
pass. On macOS and Linux the adapter also fails open, with a warning, when its
state folder is a link, belongs to another user, or is writable by others,
because planted state there could make holds pass.

## State

One small JSON file per session in `goated-claude-code-adapter/` under the
operating system's temporary folder, or under `GOATED_ADAPTER_STATE_DIR` when
set. It holds the current task's route, loads, and skip reasons, whether the
router loaded, the last turn seen, and the latest typed overrides. It holds no
prompt or reply text beyond the short override phrases.

## Latency

Measured on 2026-11-15 on Windows 11 with Python 3.13 and an Intel Core
i9-14900K, spawning `goated_hook.py` in exec form, 30 runs each:

| Case | Median | p90 |
| --- | --- | --- |
| Interpreter start alone (`python -c pass`) | 22 ms | 24 ms |
| `UserPromptSubmit` or `SessionStart` | 53 ms | 55 ms |
| `PreToolUse`, 20 KB transcript | 54 ms | 60 ms |
| `PreToolUse`, real 2.9 MB session transcript | 69 ms | 71 ms |
| `PreToolUse`, 88 MB synthetic transcript, 300-call current turn | 64 ms | 68 ms |

The reader reads only the current turn from the end of the file, so
transcript size barely matters. Most of the cost is interpreter start-up and
the `json` and `re` imports.

In live headless sessions on the same machine (Claude Code 2.1.325), the call
being judged was never yet in the transcript when the hook started. Its entry
appeared 54 to 114 ms later, over 7 main-agent calls, so a held-or-passed
`PreToolUse` call costs roughly the figures above plus that wait. The 1.5-second
budget leaves headroom before the hook fails open.

## Known Limits

- A file written through `Bash` or `PowerShell` meets only `router-first`.
  Telling reading commands from writing ones is not reliable from a command
  string.
- Shared-policy detection looks for the policy's title in the instruction
  files Claude Code reads and in their one-level `@` imports. It does not model
  the setting under which a `CLAUDE.md` stops `AGENTS.md` from loading, and it
  stops its parent-folder walk at your home folder.
- Hooks for parallel tool calls can race on the state file. Each call
  re-derives its turn from the transcript, so a lost update can cause a repeat
  hold, never a pass.

## Tests

`tests/test_claude_code_adapter.py` in the GOATED source repo drives the
adapter with hook inputs and transcripts in Claude Code's recorded shape,
including the recorded fixtures in `tests/fixtures/claude_code_adapter/`, and
checks the adapter's marker parser against `stack/fixtures/markers/lines.yaml`.
