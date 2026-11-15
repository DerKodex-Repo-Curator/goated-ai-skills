# Ticket 029: Router Skill Map, Route Line, And Skip Line

## Parent Spec

`docs/specs/2026-11-15-skill-enforcement-adapter.md` (R2 docs part, R3, R4,
and the portable half of R6)

## Type

AFK.

## What To Build

Make the router's decision visible and portable:

- The router's gate table names the specialist skill or skills for each gate,
  so an installed router no longer depends on `docs/how-to-use.md` for that
  mapping.
- The router's output contract gains the route line in its three forms:
  `direct`, `<intensity> | requires: <skills>`, and `continue`.
- The shared policy defines the justified-skip line (`goated-skip: <skill>:
  <reason>`) as a portable convention: how an agent states that a skill does
  not apply.
- Fix the exact grammar of both lines in one place, and add fixtures that
  later adapter and mod tickets can parse.
- The Claude Code install docs show how to make Claude Code load
  `stack/AGENTS.md`.

Under ADR 0003, adapters enforce these contracts but never define them, so this
ticket must land before the adapter.

## Recommended First Reads

- `skills/agent-workflows/using-goated-ai-skills/SKILL.md` — gate table,
  checkpoints, and output contract.
- `docs/how-to-use.md` "Practical Routing Rules" — the current gate-to-skill
  mapping.
- `stack/AGENTS.md` — the shared policy and its word budget. It measured
  1,199 words against a 1,200-word target on 2026-11-15, so the skip-line text
  needs matching cuts elsewhere.
- `docs/install.md` — the Claude Code install section.
- `docs/adr/0003-opt-in-framework-enforcement-adapters.md`

## Acceptance Criteria

- [ ] Every gate in the router names its skill or skills. The router stays
      under 300 lines.
- [ ] The router's output contract specifies the route line in all three forms,
      with its grammar.
- [ ] The shared policy defines the skip line, stays within its word target,
      and says skips need a specific reason.
- [ ] Fixtures exist for valid and invalid route and skip lines.
- [ ] The install docs show a working way to load the shared policy in Claude
      Code.
- [ ] The router still works standalone without the shared policy, and its
      compact fallback covers the route line.
- [ ] The validator, the unit tests, and the context comparison pass.

## Expected Proof

- Validator, unit-test, and context-comparison output.
- One manual routing run showing a route line in the reply.

## Blocked By

- None

## Scope Exclusions

- Parsing or enforcing the lines (Tickets 030 and 031).
- Description rewrites (Ticket 028).
