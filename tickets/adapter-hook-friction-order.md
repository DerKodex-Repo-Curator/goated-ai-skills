# Adapter Hook Friction Delivery Order

Source spec: `docs/specs/2026-11-17-adapter-hook-friction.md`

1. `tickets/054-adapter-overrides-pasted-text-and-commit-skip.md`
   - Blocked by: None
   - Enables: overrides only from the user's own words; a typed
     `skip commit-message` that works.
2. `tickets/055-adapter-router-first-read-only-commands.md`
   - Blocked by: None
   - Enables: shell reads before routing.
3. `tickets/056-adapter-route-from-side-session-brief.md`
   - Blocked by: None
   - Enables: briefed side sessions with no router round trip.
4. `tickets/057-adapter-repeated-failure-ignores-import-errors.md`
   - Blocked by: None
   - Enables: TDD's planned red runs without a diagnose hold.
5. `tickets/058-adapter-design-gate-skips-test-files.md`
   - Blocked by: None
   - Enables: the design gate at the first implementation edit.
6. `tickets/059-adapter-closeout-outside-project-files.md`
   - Blocked by: None
   - Enables: no closeout items for files outside the project.
7. `tickets/060-adapter-read-only-subagents-pass-spawn-gates.md`
   - Blocked by: `tickets/055-adapter-router-first-read-only-commands.md`
   - Enables: cheap read-only research subagents.
8. `tickets/061-adapter-change-reads-without-rereads.md`
   - Blocked by: `tickets/054-adapter-overrides-pasted-text-and-commit-skip.md`,
     `tickets/052-adapter-design-citations-at-closeout.md`
   - Enables: no re-reads after a load or a comment-only fix.
9. `tickets/062-adapter-closeout-items-at-commit.md`
   - Blocked by: `tickets/061-adapter-change-reads-without-rereads.md`,
     `tickets/052-adapter-design-citations-at-closeout.md`
   - Enables: closeout work before the final report.
10. `tickets/063-adapter-unseen-line-advice-once-per-turn.md`
    - Blocked by: 054, 055, 057, 058, 060, 061 and 062
    - Enables: shorter repeat holds.

Tickets 054 to 059 touch different functions. Their overlaps are the
adapter README and, for 054 and 059, `actions.py`, which can be resolved at
merge time, as in earlier waves. The blockers mark real overlap in the same
function: 060 after 055 in `check_routing`, and 061 then 062 in the commit
hold and closeout items, after 054 and Ticket 052. Ticket 052 is in
`tickets/design-reference-reads-order.md` and can start now. Ticket 063
changes the advice text every other hold carries, so it runs last.

## Ready Frontier

- `tickets/054-adapter-overrides-pasted-text-and-commit-skip.md`
- `tickets/055-adapter-router-first-read-only-commands.md`
- `tickets/056-adapter-route-from-side-session-brief.md`
- `tickets/057-adapter-repeated-failure-ignores-import-errors.md`
- `tickets/058-adapter-design-gate-skips-test-files.md`
- `tickets/059-adapter-closeout-outside-project-files.md`
- Outside this order, `tickets/052-adapter-design-citations-at-closeout.md`
  is also ready, and it blocks 061 and 062.

## Coverage

- AC1 (closeout at commit) → 062
- AC2 (change reads in any order) → 061
- AC3 (comment-only edits) → 061
- AC4 (import errors) → 057
- AC5 (read-only commands) → 055
- AC6 (a route from the brief) → 056
- AC7 (attachments open no turn) → 056
- AC8 (test edits and design) → 058
- AC9 (advice once per turn) → 063
- AC10 (Setup in the project) → 059
- AC11 (scratch files) → 059
- AC12 (pasted text) → 054
- AC13 (a typed commit skip) → 054
- AC14 (052 note) → this planning change, plus 062's criterion
- AC15 (read-only subagents) → 060
- AC16 (kept holds unchanged) → every ticket
- AC17 (repo checks) → every ticket
