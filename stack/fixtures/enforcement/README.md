# Enforcement Conformance Scenarios

Each file here holds scenarios for the
[enforcement contract](../../enforcement-contract.md), written in the terms
of the [event model](../../schemas/enforcement-event-model.schema.json)
(`$defs/scenario_file`). A scenario is a sequence of steps: prompts, replies,
calls with their results, compactions, turn ends, and session starts. A
judged step carries the decision it must get: `allow` or `hold`, the holds by
gate and kind in firing order, and, when given, exactly the notices it
carries. Hold text is guidance and is never compared.

Rules for every scenario:

- **Name no harness.** Calls have kinds, never a harness's tool names, and
  no text names a harness or its hooks. A test checks this.
- **Every call is judged.** A call step with no `expect` must be allowed, so
  a scenario's history passes the gates as a real session's would.
- **Say what it covers.** `covers` lists a gate holding, a way it clears (a
  clear way the contract's Gates table names), or a near miss. A test fails
  when a gate the contract names lacks a scenario that holds, one for each
  clear way, or a near miss.
- **Placeholders.** `{outside}` is a folder outside the project and any
  checkout, as a scratch file's or an installed skill's folder is.
- **Setup** describes the project, not the harness: skills installed, or a
  branch of a given size.

The repo proves every scenario against the Claude Code adapter through
`tests/claude_code_scenarios.py`, which translates each step into that
adapter's hook input and its output back into a decision. An adapter for
another harness runs the same files through its own translation.

| File | Gates |
| --- | --- |
| [`routing.yaml`](routing.yaml) | `router-first`, `route-line`, `pipeline`, and a joint hold |
| [`handing-on.yaml`](handing-on.yaml) | `commit`, `pull-request`, `pr-review`, `spawn` |
| [`writes.yaml`](writes.yaml) | `design`, `design-reads`, `reference-reads`, `review-intake`, `security`, `scripted-edit`, `conflict-resolution`, `repeated-failure` |
| [`closeout.yaml`](closeout.yaml) | `closeout`, at a commit and at the turn's end, and the closeout note |
