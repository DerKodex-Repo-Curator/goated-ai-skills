# Hook Friction Round 4 Delivery Order

Source spec: `docs/specs/2026-11-18-hook-friction-round-4.md`

Parallel waves, with round 2's remaining tickets:
[hook-friction-round-3-waves.md](hook-friction-round-3-waves.md)

1. `tickets/099-core-fixture-data-is-test-data.md`
   - Blocked by: `tickets/081-shared-enforcement-core.md`
   - Enables: fixture edits with no configuration reference.
2. `tickets/100-core-narrower-reference-triggers.md`
   - Blocked by: `tickets/081-shared-enforcement-core.md`
   - Enables: the mocking reference for mocks in code, and short
     comment-only edits with no design reads.
3. `tickets/102-core-session-messages-continue-the-task.md`
   - Decisions: D1 option 2 and D2 option 1 (the maintainer, 2026-11-18).
   - Blocked by: `tickets/081-shared-enforcement-core.md`
   - Enables: a peer's message continuing the work without a held write.
4. `tickets/101-core-read-skips-last-the-task.md`
   - Decision: C option 2 (the maintainer, 2026-11-18).
   - Blocked by: `tickets/081-shared-enforcement-core.md`, 099, 100
   - Enables: a reasoned skip of a read written once per task.

Every ticket waits for Ticket 081, so each rule changes once, in
`adapters/core/`. Ticket 101 also waits for 099 and 100: they narrow the
triggers of the same two gates and edit the same contract rows, and with
them landed the remaining need for lasting skips can be judged again.

## Ready Frontier

None. Ticket 081 is not complete.

## Coverage

- AC1 (fixture data) → 099
- AC2 (mocking pattern) → 100
- AC3 (short comment-only edits) → 100
- AC4 (lasting skips) → 101
- AC5 (another session's message) → 102
- AC6 (waiting on another session) → 102
- AC7 (contract and scenarios) → every ticket
- AC8 (repo checks) → every ticket
