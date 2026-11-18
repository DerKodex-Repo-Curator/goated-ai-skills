# Ticket 079: The Enforcement Contract, Event Model And Conformance Scenarios

## Parent Spec

`docs/specs/2026-11-17-portable-enforcement-core.md` (R1, R2, R3, R6, R11;
AC1, AC2, AC6)

## Type

HITL. The maintainer accepts the ADR and reviews the event model before
anything is built on it.

## Problem

GOATED's enforcement rules can only be used from Claude Code. Many are
stated only in the Claude Code adapter's code and README, there is no
harness-neutral description of a turn, a call or a decision, and the
adapter's tests are written against Claude Code's transcript shape. An
adapter for another harness has nothing to build on or be checked against.

## What To Build

- **ADR.** Record the decision: one shared core with thin adapters, the
  event model as the seam, and two ways to call the core (a Python import
  and a JSON command). State how it stays inside ADR 0002's exclusions and
  under ADR 0003's rules. Index it in `docs/adr/README.md`.
- **Enforcement contract.** One document under `stack/` that states every
  enforced rule in harness-neutral words: each gate, what it holds, what
  clears it, the closeout items, the hold line's format, the line grammar
  and where lines may be written, and the fail-open rules. Cite rules a
  skill, the shared policy or the registry owns; do not copy them. Move
  harness-neutral rule text out of the Claude Code README, which keeps
  what is specific to Claude Code and links to the contract.
- **Event model.** A versioned schema under `stack/schemas/` for the
  pending call, the turn so far, the project, and the decision, as the
  spec's R3 and R4 describe. Call kinds, not tool names. Design it against
  Claude Code, a plain API tool loop, and what public documentation shows
  of Pi Agent and OpenCode, and note in the ADR anything one of them
  cannot supply.
- **Conformance scenarios.** Scenario files under `stack/fixtures/` that
  hold a sequence of events and the expected decision at each step. Cover
  each gate holding, each way it clears, and a near miss. Name no harness.
- **A check that they are true today.** A test helper translates each
  scenario into the Claude Code adapter's input and asserts the adapter
  gives the expected decision, so the scenarios describe current
  behaviour before any code moves.
- **Standard.** `AGENTS.md` says a rule change updates the contract and a
  conformance scenario in the same change. A check fails when a gate the
  adapter can return is missing from the contract.

## Recommended First Reads

- The parent spec, all of it.
- `docs/adr/0002-v2-integrated-stack-foundation.md` and
  `docs/adr/0003-opt-in-framework-enforcement-adapters.md`.
- `adapters/claude-code/README.md`: What It Holds, Hold messages, User
  Overrides, Failing Open.
- `adapters/claude-code/goated_adapter/transcript.py` (`Turn`, `Call`) and
  `gates.py` (`Hold`), for what the rules read today.
- `stack/fixtures/markers/README.md`, for how a portable grammar and its
  fixtures are kept.
- `tests/claude_code_adapter_support.py`.

## Acceptance Criteria

- [x] The ADR is accepted by the maintainer and indexed.
- [x] Every gate and closeout item in the Claude Code README's tables
      appears in the contract, and a check fails when a gate the adapter
      can return is missing from it.
- [x] The event model's schema validates every scenario, and a request of
      an unknown version is rejected by the schema.
- [x] The decision schema carries one or more holds in firing order, and
      a scenario covers a joint hold.
- [x] The scenarios cover each gate holding, each way it clears, and a
      near miss, and name no harness or harness tool.
- [x] Every scenario passes against the Claude Code adapter through the
      test helper.
- [x] The maintainer's review of the event model is recorded in this
      ticket's closeout.

## Expected Proof

- The scenario tests and the contract check.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.
- The recorded maintainer decisions.

## Blocked By

- `tickets/065-adapter-loads-count-until-compaction.md`
- `tickets/068-adapter-reference-reads-turn-signals.md`
- `tickets/069-adapter-closeout-review-and-verification.md`
- `tickets/070-adapter-review-intake-hold.md`
- `tickets/072-orientation-and-plans-in-routes.md`
- `tickets/073-notices-for-retrospective-and-onboarding.md`
- `tickets/077-undocumented-override-phrases.md`
- `tickets/086-adapter-repeated-failure-red-runs.md`
- `tickets/087-adapter-routing-orientation-by-reads-and-outside-writes.md`
- `tickets/088-adapter-wider-plain-reads.md`
- `tickets/089-adapter-design-holds-without-written-text.md`
- `tickets/090-adapter-test-edit-reference-thresholds.md`
- `tickets/091-adapter-review-size-and-installs.md`
- `tickets/092-adapter-whole-reads-and-read-order.md`
- `tickets/093-adapter-inline-script-writes.md`
- `tickets/094-adapter-own-subagent-reports-continue-the-turn.md`
- `tickets/095-adapter-joint-holds-in-one-message.md`
- `tickets/096-adapter-early-closeout-note.md`

These settle the rules the contract states and change the README it is
drawn from. Ticket 077 may change the override parsing that Tickets 080
and 081 then refactor and move. Tickets 086 to 096 are hook-friction
round 3 (`tickets/hook-friction-round-3-waves.md`): they change gates and
hold delivery, so the contract is written after them. Ticket 095 makes
one decision carry several holds, which the event model must allow.

## Scope Exclusions

- Moving any rule code.
- New rules.
- Adapters for other harnesses.

## Closeout

### Maintainer's event-model review, 2026-11-18

The maintainer accepted ADR 0004, Orca addition included, and settled the
event model's open questions through the lead session's questions, which
rested on the Orca research in commit `46f9836`:

1. **Turn shape:** one ordered list of entries.
2. **Requests carry the turns, not an event stream; the core keeps session
   facts by session id** (option (a), clarified on 2026-11-18). Each request
   carries every turn since the last compaction. The core keeps only the
   facts that outlast those turns: the route and its `requires:` skills
   across a compaction, the briefed flag, the turn markers, the friction
   counts, and the spawn brief templates.
3. **Hold text:** the core returns the rule text; each adapter adds its
   harness's wording, such as the unseen-line advice and the shell carrier.
4. **Prompt text:** the adapter strips blocks its harness inserted and moves
   pasted text into `pasted`; the core never parses a harness's tags.
5. **The end of a turn** is the `turn_end` event.
6. **Shell kinds, option (a):** an adapter may label a harness-specific
   shell command with a kind such as `spawn`, for example Orca's
   `orca orchestration worker-start`. The core still parses git and gh
   commit and pull-request commands itself.
7. **Gate names:** the schema checks only their shape. The contract owns
   the list, and the contract check compares it with the gates the adapter
   can return.
8. **No turn-end hold:** a harness that cannot hold a turn's end, such as
   Pi, delivers the closeout as a continue request and documents the gap.
9. **Versioning:** a whole-number `event_model` that every change bumps.
10. **Scenarios** live under `stack/fixtures/enforcement/`.

### Review, 2026-11-18

Two reviewers compared the contract with the code and the scenarios with
the spec. Fixed on this branch:

- The contract states the real firing order, that `pr-review` is judged
  with `pull-request`, that `review-intake` follows only a reviewer
  template's brief, and that the design gates judge file writes only.
- Where the adapter is looser than the contract, the maintainer decided
  that the contract and scenarios state today's behaviour and mark each
  gap, and that [Ticket 098](098-adapter-contract-gaps.md) fixes the code
  before 080: (a) orientation counts partial reads, (b) the design gates
  never judge a shell write, (c) a subagent's commit meets no closeout.
  Scenarios with `case: gap` pin (a) and (b); (c) needs a subagent-role
  scenario, which the runner gains in Ticket 080.
- Every scenario that says a gate clears now shows the same call held
  without the clearing step, and a test enforces it. A fail-open or
  warning notice nobody expected fails the step. Each closeout hold names
  its items, pinning all eight labels. The runner raises on a line field
  Claude Code cannot carry, and no longer misreads a mirrored notice as a
  warning. Expectations are as strict as decisions, and only a session
  start may have no turns.
- The contract check follows forwarded gate names and keyword arguments,
  fails on any it cannot read, and checks each gate's kind and clear ways
  and the exact closeout labels. The harness-name guard covers tool and
  hook names as whole words.

**Partial thinning.** The Claude Code README now links the contract for
the hold kinds, the gate list, the hold format and the override phrases,
but keeps its gate and closeout tables as Claude Code detail, and the
contract cites the README's detection tables. Ticket 081 moves those
tables into the contract with the rule code and retargets the contract
check to `adapters/core/`.
