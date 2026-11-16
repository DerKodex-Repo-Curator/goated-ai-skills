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
6. `tickets/archive/034-skill-usage-mod-action-holds.md`
   - Status: Completed, merged and archived on 2026-11-16.
   - Blocked by: `tickets/archive/031-claude-code-adapter-action-and-closeout-gates.md`,
     `tickets/archive/032-skill-usage-mod-in-repo.md`
   - Enables: measurement of every hold for the trial.
7. `tickets/archive/033-adapter-real-use-trial.md`
   - Status: Completed, merged and archived on 2026-11-16 (decision: revise).
   - Blocked by: `tickets/archive/028-discoverable-skill-descriptions.md`,
     `tickets/archive/034-skill-usage-mod-action-holds.md`
   - Enables: the maintainer's keep, revise, or revert decision.
8. `tickets/archive/039-skill-usage-hold-settlement-module.md`
   - Status: Completed, merged and archived on 2026-11-16.
   - Blocked by: `tickets/archive/033-adapter-real-use-trial.md` (its legacy removal)
   - Enables: hold-outcome fixes in one module instead of inside `summarize`.
9. `tickets/archive/040-skill-usage-all-time-picture-badges.md`
   - Status: Completed, merged and archived on 2026-11-16.
   - Blocked by: none. It changes only what the pane draws, not what the mod
     counts, so it landed during the 033 trial.
   - Enables: an All time picture without per-case badges, and Session badges
     whose colours each mean one thing.
10. `tickets/archive/041-adapter-review-holds-read-the-change.md`
   - Status: Completed, merged and archived on 2026-11-16.
   - Blocked by: `tickets/archive/033-adapter-real-use-trial.md` (its keep decision)
   - Enables: review holds that clear only after the agent reads the change,
     not on a skill load alone; ticket 038 builds on it.
11. `tickets/047-adapter-overrides-from-other-agents.md`
   - Blocked by: `tickets/archive/041-adapter-review-holds-read-the-change.md`
   - Enables: overrides recorded and announced only for a prompt a person
     typed, never for a message from another agent or session.
12. `tickets/042-adapter-fresh-session-routing.md`
   - Blocked by: `tickets/047-adapter-overrides-from-other-agents.md`
   - Enables: `continue` in a session with no task, and loads earlier in the
     turn counting for the task it starts.
13. `tickets/043-adapter-out-of-project-holds.md`
   - Blocked by: `tickets/042-adapter-fresh-session-routing.md`
   - Enables: no design, security, or closeout holds for files outside the
     project.
14. `tickets/044-adapter-closeout-same-command-check.md`
   - Blocked by: `tickets/043-adapter-out-of-project-holds.md`
   - Enables: a check in the same command as the write proving it.
15. `tickets/045-route-and-skip-lines-before-the-call.md`
   - Blocked by: `tickets/044-adapter-closeout-same-command-check.md`
   - Enables: route and skip lines the adapter can see on the first try.
16. `tickets/046-adapter-pipeline-after-compaction.md`
   - Blocked by: `tickets/045-route-and-skip-lines-before-the-call.md`
   - Enables: the last route line winning after a compaction.

Tickets 041–046 are the trial's revise fixes (spec, Trial Result), and 047
fixes an R8 gap found in real use after the trial. They edit
the same adapter files and hold texts, so they run one after another, and all
of them run before Ticket 035 in
`tickets/adapter-skill-activation-gates-order.md`. The trial's revise decision
counts as the keep decision those tickets are blocked on.

Tickets 028 and 029 ran in parallel and were merged on 2026-11-15. Ticket 032
was split on 2026-11-16 so it can run alongside 031: 031 works in
`adapters/claude-code/goated_adapter/` and 032 in the mod's own folder, so
their write scopes do not overlap. Ticket 034 needs both.

Tickets 051 and 052 from `tickets/design-reference-reads-order.md` edit the
same adapter files, so they follow 046 and come before Ticket 035. Ticket 050
there edits the mod after 047.

## Ready Frontier

- `tickets/047-adapter-overrides-from-other-agents.md`

Then 042 to 046, one after another.

## Coverage

- AC1 → 028
- AC2 → 029 (docs), 030 (detection)
- AC3 → 029
- AC4 → 030 (routing gates, overrides, subagents, fail-open), 031 (action and
  closeout gates, content checks, shell writes), 047 (overrides only from a
  typed prompt)
- AC5 → 030, 031
- AC6 → 028, 029, 030
- AC7 → 032 (routing holds, lines, skips, overrides, references, subagents),
  034 (action and closeout holds, live check)
- AC8 → 030 (adapter), 032 (mod)
- AC9 → 033
- AC10 → 041
- AC11 → 042, 043, 044, 045, 046
