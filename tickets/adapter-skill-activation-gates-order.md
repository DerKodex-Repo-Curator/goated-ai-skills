# Adapter Skill-Activation Gates Delivery Order

Source spec: `docs/specs/2026-11-16-adapter-skill-activation-gates.md`

1. `tickets/archive/035-adapter-merge-conflict-gate.md`
   - Status: Completed, merged and archived on 2026-11-17.
   - Blocked by: `tickets/archive/033-adapter-real-use-trial.md`
   - Enables: `resolving-merge-conflicts` at the moment a conflict is open.
2. `tickets/archive/036-adapter-repeated-failure-gate.md`
   - Status: Completed, merged and archived on 2026-11-17.
   - Blocked by: `tickets/archive/033-adapter-real-use-trial.md`
   - Enables: `diagnose` after a check keeps failing.
3. `tickets/archive/037-adapter-setup-closeout-item.md`
   - Status: Completed, merged and archived on 2026-11-17.
   - Blocked by: `tickets/archive/033-adapter-real-use-trial.md`
   - Enables: `setup-scribe` when a turn changed setup.
4. `tickets/archive/038-adapter-large-pull-request-review.md`
   - Status: Completed, merged and archived on 2026-11-17.
   - Blocked by: `tickets/archive/033-adapter-real-use-trial.md`,
     `tickets/archive/041-adapter-review-holds-read-the-change.md`
   - Enables: `standards-and-spec-review` before a large pull request.

The four tickets touch the same adapter files (`actions.py`, the README's
gate tables, the generated hold texts) and the mod's gate names, but none
depends on another or on the other adapter tickets: each adds its own gate or
closeout item. On 2026-11-16 the maintainer chose to run them in parallel and
resolve the additive overlaps at merge time, instead of queueing them behind
Ticket 052. Ticket 037 adds an item to the closeout gate rather than a new
gate. Ticket 033 recorded a revise decision on 2026-11-16, which keeps the
adapter installed and counts as the keep decision these tickets wait for.

## Ready Frontier

- None. All four tickets are completed and archived; AC4 waits for the
  maintainer's next stretch of real use.

## Coverage

- AC1 (fires on its trigger, silent on a near miss) → 035, 036, 037, 038
- AC2 (a load, a skip line and an override clear it) → 035, 036, 037, 038
- AC3 (the mod names it and records its outcome) → 035, 036, 037, 038
- AC4 (checked against real use) → the maintainer's next stretch of real
  use after 038
