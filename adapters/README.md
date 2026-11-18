# Framework Enforcement Adapters

This folder holds **opt-in enforcement adapters** under
[ADR 0003](../docs/adr/0003-opt-in-framework-enforcement-adapters.md): layers
for one agent framework that a user installs on purpose to hold actions until
the skill the GOATED stack requires has loaded.

Every adapter follows the ADR's five rules:

1. **Opt-in only.** No skill, the shared policy, or the registry needs an
   adapter. Skills keep their standalone fallbacks.
2. **Enforce portable contracts, never define them.** Adapters enforce what
   the router, the skills, and the shared policy already say, such as the
   `goated-route:` and `goated-skip:` lines in
   [`stack/fixtures/markers/`](../stack/fixtures/markers/README.md).
3. **No free bypass.** A hold passes only on proof of use, a justified skip
   where the hold allows one, or an override the user typed.
4. **Fail open, visibly.** An adapter that cannot read its inputs lets the
   action through and says so.
5. **Tested in this repo.** Adapter logic runs in the repo's unit tests and CI.

The validator checks the boundary: adapter code imports only the Python
standard library and the shared core, the core imports no adapter, and no
skill file refers to an adapter.

## The Shared Core

[`core/`](core/) holds the rules every adapter calls
([ADR 0004](../docs/adr/0004-portable-enforcement-core.md)): the gates, the
closeout, shell reading, the line grammar, the content checks, and the
overrides, as the [enforcement contract](../stack/enforcement-contract.md)
states them. It knows no harness. It reads the
[event model](../stack/schemas/enforcement-event-model.schema.json) and keeps
the session facts that outlast a request (the task's route, the briefed flag,
turn markers, friction counts, spawn brief templates, the latest typed
overrides), keyed by the session id the adapter supplies, in a folder the
adapter may choose. A session id made only of lowercase letters, digits,
`_` and `-`, at most 128 of them, names its state file as it is; any other
is named by a readable prefix and a digest of the whole id, so two ids never
share a file. Standard library only, Python 3.11 or later.

An adapter translates its harness's events into the model and the core's
decision back into the harness's output, in one of two ways:

- **The command**, for a harness in any language: run
  `python <goated-root>/adapters/core/goated_judge.py`, write one request as
  JSON on standard input, and read one decision as JSON on standard output.
  `--state-dir DIR` (or `GOATED_CORE_STATE_DIR`) sets where state lives,
  `--registry PATH` (or `GOATED_CORE_REGISTRY`) the installed registry, and
  `GOATED_CORE_SKILL_NAMESPACES` the plugin namespaces whose `ns:skill`
  loads count. Send each turn since the last compaction, the event, and a
  `prompt_submitted` event for each prompt, which records its overrides. A
  request it cannot read, or of an unknown version, is answered `allow`
  with a `fail_open` notice, and the command exits 0.
- **The Python call**, for a Python harness, which saves a process per call:
  put `adapters/core/` on `sys.path` and call
  `goated_core.request.decide(request, settings)` with the same request as a
  parsed value; it returns the same decision. An adapter that builds the
  model's objects itself, as the Claude Code adapter does, calls
  `goated_core.judge` instead and fills the hold texts' wording slots
  (`goated_core/wording.py`) in its harness's words; `decide` and the command
  fill them with neutral words, so their decisions never carry a slot.

The [conformance scenarios](../stack/fixtures/enforcement/README.md) run
through both ways in the repo's tests (`tests/test_enforcement_core.py`,
with the runner in `tests/core_scenarios.py`), and must give the same
decision each way.

## The Usage Log

The core appends what each event showed to a local usage log, so a session
in any harness leaves the same record (Ticket 082): each hold with its gate,
kind and what it asks for, what became of it, each skill load with its
cause, each route and skip line, each reference read, and code changes and
turn ends. Each entry carries the log's version, the session id, a project
key and the adapter's name. It holds what the
[skill-usage mod](claude-code/skill-usage/README.md) stores and nothing
more: no prompt text, hold text, file content or project path. The format,
JSON Lines of one entry each, is
[`stack/schemas/usage-log.schema.json`](../stack/schemas/usage-log.schema.json).

- **Where it lives.** The caller sets it: `--usage-log PATH` on the command,
  `GOATED_USAGE_LOG` for the command and the Claude Code adapter, or
  `UsageLog(path, adapter)` in `Settings.usage_log` for the Python call
  (None keeps no log). `off`, as either value, keeps none. The command and
  `decide` keep no log unless one is named, so another harness, a test, or
  the worked example never writes into the user's own log by default. The
  Claude Code adapter, which a user installs on purpose, logs by default to
  a per-user file, never in a project folder:
  `%LOCALAPPDATA%\goated\usage-log.jsonl` on Windows (the per-user temp
  folder's `goated` when that is unset), else
  `$XDG_STATE_HOME/goated/usage-log.jsonl`, else
  `~/.local/state/goated/usage-log.jsonl`. The folder is made private to the
  user, and on POSIX one that is a link, another user's, or writable by
  others is refused. Project keys and file digests are salted with
  `usage-log-salt`, made once beside it. The command names its adapter
  from `GOATED_CORE_ADAPTER`, `core` when unset; the Claude Code adapter
  writes as `claude-code`.
- **Many writers.** Each event's lines go in one write under a lock file on
  the whole log, `usage-log.jsonl.lock`, so hooks of parallel sessions and
  processes never lose or mix a line. A lock left by a stopped process is
  broken after ten seconds.
- **Never in the way.** A log that cannot be written leaves the decision
  as it was and adds one `warning` notice per session. Nothing is sent
  anywhere.
- **Reading it.** A line that is no entry (not JSON, not an object, or
  missing a field its type needs) is passed over and counted; only an entry
  of a version the reader does not know refuses the log.
- **The report.** `python <goated-root>/adapters/core/goated_usage_report.py
  [--log PATH] [--project KEY] [--project-folder PATH] [--adapter NAME]`
  prints a Markdown summary: the projects by key with their sessions, loads
  by skill and cause, holds by gate and outcome, closeout items, route
  lines, reference reads, and how many lines were skipped.
  `--project-folder` finds a folder's key with the log's salt. A log with an
  entry of a version it does not know is refused: the reason goes to
  standard error and the command exits 1.
- **Size.** The log is never trimmed: each entry is about 200 bytes, so a
  short session adds a few kilobytes and a long one tens, and the
  skill-usage mod reads it whole at each session start.
  Delete it, or point `GOATED_USAGE_LOG` elsewhere, to start afresh.
- **Outcomes** are the core's own settlement (`goated_core/friction.py`):
  answered, declined, stood down by an override, or unanswered, one per
  gate and turn however often the gate held. The skill-usage mod settles
  holds by its own finer rules and reads the log's other entries.

## Adapters

| Folder | Framework | Status |
| --- | --- | --- |
| [`core/`](core/) | Any, through the event model | The shared rules every adapter calls (Ticket 081); the usage log and its report (Ticket 082) |
| [`claude-code/`](claude-code/README.md) | Claude Code | Routing gates (Ticket 030); action, shell-write, and closeout gates (Ticket 031); calls the shared core (Ticket 081) |
