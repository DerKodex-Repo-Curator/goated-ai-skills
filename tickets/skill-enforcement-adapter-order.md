# Skill Enforcement Adapter Delivery Order

Source spec: `docs/specs/2026-11-15-skill-enforcement-adapter.md`
Decision record: `docs/adr/0003-opt-in-framework-enforcement-adapters.md`

1. `tickets/archive/028-discoverable-skill-descriptions.md`
   - Status: Completed and archived on 2026-11-15.
   - Blocked by: None
   - Enables: skills found from their descriptions in any framework; the
     trial in 033.
2. `tickets/archive/029-router-skill-map-and-route-line.md`
   - Status: Completed and archived on 2026-11-15.
   - Blocked by: None
   - Enables: the portable route and skip contracts the adapter enforces.
3. `tickets/archive/030-claude-code-adapter-routing-gates.md`
   - Status: Completed, merged and archived on 2026-11-16.
   - Blocked by: `tickets/archive/029-router-skill-map-and-route-line.md`
   - Enables: router-first, route-line, and pipeline enforcement, and the
     adapter base for 031 and 032.
4. `tickets/archive/031-claude-code-adapter-action-and-closeout-gates.md`
   - Status: Completed, merged and archived on 2026-11-16.
   - Blocked by: `tickets/archive/030-claude-code-adapter-routing-gates.md`
   - Enables: action and closeout enforcement, and the stable hold format for
     034.
5. `tickets/archive/032-skill-usage-mod-in-repo.md`
   - Status: Completed, merged and archived on 2026-11-16.
   - Blocked by: `tickets/archive/030-claude-code-adapter-routing-gates.md`
   - Enables: the mod in the repo, measuring routing holds, route lines,
     skips, overrides, references, and subagents; the base for 034.
6. `tickets/034-skill-usage-mod-action-holds.md`
   - Blocked by: `tickets/archive/031-claude-code-adapter-action-and-closeout-gates.md`,
     `tickets/archive/032-skill-usage-mod-in-repo.md`
   - Enables: measurement of every hold for the trial.
7. `tickets/033-adapter-real-use-trial.md`
   - Blocked by: `tickets/archive/028-discoverable-skill-descriptions.md`,
     `tickets/034-skill-usage-mod-action-holds.md`
   - Enables: the maintainer's keep, revise, or revert decision.

Tickets 028 and 029 ran in parallel and were merged on 2026-11-15. Ticket 032
was split on 2026-11-16 so it can run alongside 031: 031 works in
`adapters/claude-code/goated_adapter/` and 032 in the mod's own folder, so
their write scopes do not overlap. Ticket 034 needs both.

## Ready Frontier

- `tickets/034-skill-usage-mod-action-holds.md`

## Coverage

- AC1 → 028
- AC2 → 029 (docs), 030 (detection)
- AC3 → 029
- AC4 → 030 (routing gates, overrides, subagents, fail-open), 031 (action and
  closeout gates, content checks, shell writes)
- AC5 → 030, 031
- AC6 → 028, 029, 030
- AC7 → 032 (routing holds, lines, skips, overrides, references, subagents),
  034 (action and closeout holds, live check)
- AC8 → 030 (adapter), 032 (mod)
- AC9 → 033
