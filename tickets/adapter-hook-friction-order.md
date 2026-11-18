# Adapter Hook Friction Delivery Order

Source spec: `docs/specs/2026-11-17-adapter-hook-friction.md`

1. `tickets/archive/054-adapter-overrides-pasted-text-and-commit-skip.md`
   - Status: Completed, merged and archived on 2026-11-17.
   - Blocked by: None
   - Enables: overrides only from the user's own words; a typed
     `skip commit-message` that works.
2. `tickets/archive/055-adapter-routing-lets-reads-through.md`
   - Status: Completed, merged and archived on 2026-11-17.
   - Blocked by: None
   - Enables: shell reads before routing and cheap read-only research
     subagents.
3. `tickets/archive/056-adapter-route-from-side-session-brief.md`
   - Status: Completed, merged and archived on 2026-11-18.
   - Blocked by: None
   - Enables: briefed side sessions with no router round trip.
4. `tickets/archive/057-adapter-tdd-friction.md`
   - Status: Completed, merged and archived on 2026-11-17.
   - Blocked by: None
   - Enables: TDD's planned red runs and test-first edits with no hold meant
     for other work.
5. `tickets/archive/058-adapter-closeout-outside-project-files.md`
   - Status: Completed, merged and archived on 2026-11-17.
   - Blocked by: None
   - Enables: no closeout items for files outside the project.
6. `tickets/archive/059-adapter-closeout-reads-and-commit-timing.md`
   - Status: Completed, merged and archived on 2026-11-18.
   - Blocked by: `tickets/archive/054-adapter-overrides-pasted-text-and-commit-skip.md`,
     `tickets/archive/052-adapter-design-citations-at-closeout.md`
   - Enables: closeout work before the final report, with no re-reads after
     a load or a comment-only fix.
7. `tickets/archive/060-adapter-unseen-line-advice-once-per-turn.md`
   - Status: Completed, merged and archived on 2026-11-18.
   - Blocked by: 054, 055, 057 and 059
   - Enables: shorter repeat holds.

Tickets were combined where splitting bought no parallel work, separate
proof or approval: changes in the same function, or tiny changes verified in
one run.

Tickets 054 to 058 touch different functions. Their overlaps are the adapter
README and, for 054, 057 and 058, `actions.py`, which can be resolved at
merge time, as in earlier waves. Ticket 059 changes the commit hold that 054
changes, and the closeout items Ticket 052 changes, so it runs after both.
Ticket 052 is in `tickets/design-reference-reads-order.md` and can start
now. Ticket 060 changes the advice text that most other holds carry, so it
runs last.

## Ready Frontier

- None. Every ticket in this order is completed and archived.

## Coverage

- AC1 (closeout at commit) → 059
- AC2 (change reads in any order) → 059
- AC3 (comment-only edits) → 059
- AC4 (import errors) → 057
- AC5 (read-only commands) → 055
- AC6 (a route from the brief) → 056
- AC7 (attachments open no turn) → 056
- AC8 (test edits and design) → 057
- AC9 (advice once per turn) → 060
- AC10 (Setup in the project) → 058
- AC11 (scratch files) → 058
- AC12 (pasted text) → 054
- AC13 (a typed commit skip) → 054
- AC14 (052 note) → the planning change, plus a criterion in 059
- AC15 (read-only subagents) → 055
- AC16 (kept holds unchanged) → every ticket
- AC17 (repo checks) → every ticket
