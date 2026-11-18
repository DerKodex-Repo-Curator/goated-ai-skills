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

## Writing An Adapter

[Writing An Adapter](writing-an-adapter.md) shows how to connect another
harness to the core: mapping its tools to call kinds, building the turns,
calling the core, showing a hold, the rules every adapter keeps, and what
to document when a harness cannot support a rule. The
[conformance runner](../scripts/run_conformance.py) plays every scenario
through an adapter by way of a small translator its author writes, and
reports each scenario that fails with the decision it expected and the one
it got:

```bash
uv run python scripts/run_conformance.py path/to/your_translator.py
```

The [worked example](example/README.md) is a toy tool loop with its adapter
and translator. It passes every scenario in the repo's tests.

## Adapters

| Folder | Framework | Status |
| --- | --- | --- |
| [`core/`](core/) | Any, through the event model | The shared rules every adapter calls (Ticket 081) |
| [`example/`](example/README.md) | A toy tool loop, to copy from | The worked example of the adapter guide (Ticket 083); not for install |
| [`claude-code/`](claude-code/README.md) | Claude Code | Routing gates (Ticket 030); action, shell-write, and closeout gates (Ticket 031); calls the shared core (Ticket 081) |
