# Adapter Skill-Activation Gates Delivery Order

Source spec: `docs/specs/2026-11-16-adapter-skill-activation-gates.md`

1. `tickets/035-adapter-merge-conflict-gate.md`
   - Blocked by: `tickets/archive/033-adapter-real-use-trial.md`
   - Enables: `resolving-merge-conflicts` at the moment a conflict is open.
2. `tickets/036-adapter-repeated-failure-gate.md`
   - Blocked by: `tickets/archive/033-adapter-real-use-trial.md`
   - Enables: `diagnose` after a check keeps failing.
3. `tickets/037-adapter-setup-closeout-item.md`
   - Blocked by: `tickets/archive/033-adapter-real-use-trial.md`
   - Enables: `setup-scribe` when a turn changed setup.
4. `tickets/038-adapter-large-pull-request-review.md`
   - Blocked by: `tickets/archive/033-adapter-real-use-trial.md`,
     `tickets/041-adapter-review-holds-read-the-change.md`
   - Enables: `standards-and-spec-review` before a large pull request.

The four tickets touch the same adapter files (`actions.py`, the README's
gate tables, the generated hold texts) and the mod's gate names, so they run
one after another in this order, not in parallel. Tickets 041–046, from the
skill-enforcement order, edit the same files and run before 035. Ticket
037 adds an item to the closeout gate rather than a new gate.

## Ready Frontier

- None until `tickets/046-adapter-pipeline-after-compaction.md` lands. Ticket
  033 recorded a revise decision on 2026-11-16, which keeps the adapter
  installed and counts as the keep decision these tickets wait for.

## Coverage

- AC1 (fires on its trigger, silent on a near miss) → 035, 036, 037, 038
- AC2 (a load, a skip line and an override clear it) → 035, 036, 037, 038
- AC3 (the mod names it and records its outcome) → 035, 036, 037, 038
- AC4 (checked against real use) → the maintainer's next stretch of real
  use after 038
