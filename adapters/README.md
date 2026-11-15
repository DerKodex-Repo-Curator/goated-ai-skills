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
standard library, and no skill file refers to an adapter.

## Adapters

| Folder | Framework | Status |
| --- | --- | --- |
| [`claude-code/`](claude-code/README.md) | Claude Code | Routing gates (Ticket 030); action and closeout gates follow in Ticket 031 |
