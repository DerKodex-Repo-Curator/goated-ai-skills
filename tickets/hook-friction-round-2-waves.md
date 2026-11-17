# Hook Friction Round 2: Parallel Waves

Tickets 061 to 085 grouped by which can run at the same time. The five
order files remain the source of truth for blockers:
[written-line holds](adapter-written-line-holds-order.md),
[registry reference reads](registry-reference-reads-order.md),
[skill placement](skill-placement-gates-order.md),
[skill-usage data detail](skill-usage-data-detail-order.md) and
[portable enforcement core](portable-enforcement-core-order.md). A ticket's
wave is one after the latest of its blockers' waves.

| Wave | Ticket | Area | Type | Blocked by |
| --- | --- | --- | --- | --- |
| 1 (ready now) | [061](061-adapter-design-closeout-citations-and-question.md) | adapter | AFK | None |
| 1 | [062](062-adapter-unseen-line-advice-once-across-parallel-holds.md) | adapter | AFK | None |
| 1 | [063](063-adapter-design-reads-small-edits.md) | adapter | AFK | None |
| 1 | [064](064-adapter-session-cards-pass-routing.md) | adapter | AFK | None |
| 1 | [066](066-registry-declares-every-reference.md) | registry | HITL (maintainer reviews the reference classification) | None |
| 1 | [071](071-spawn-briefs-name-skills.md) | skills | AFK | None |
| 1 | [074](074-design-principles-soft-dependency-audit.md) | skills | HITL (maintainer reviews the skill list) | None |
| 1 | [075](075-skill-usage-hold-detail.md) | mod | AFK | None |
| 1 | [077](077-undocumented-override-phrases.md) | mod | AFK | None |
| 2 | [065](065-adapter-loads-count-until-compaction.md) | adapter | AFK | 061, 062, 064 |
| 2 | [076](076-skill-usage-routes-sessions-projects-versions.md) | mod | AFK | 075 |
| 3 | [067](067-adapter-reference-reads-gate-edit-signals.md) | adapter | AFK | 063, 065, 066 |
| 3 | [069](069-adapter-closeout-review-and-verification.md) | adapter | AFK | 065 |
| 3 | [070](070-adapter-review-intake-hold.md) | adapter | AFK | 065 |
| 3 | [072](072-orientation-and-plans-in-routes.md) | adapter and skills | AFK | 065, 071 |
| 4 | [068](068-adapter-reference-reads-turn-signals.md) | adapter | AFK | 067 |
| 4 | [073](073-notices-for-retrospective-and-onboarding.md) | adapter | AFK | 072 |
| 5 | [078](078-skill-usage-reference-counts.md) | mod | AFK | 068, 076 |
| 5 | [079](079-enforcement-contract-and-event-model.md) | core | HITL (maintainer accepts the ADR and event model) | 065, 068, 069, 070, 072, 073 |
| 6 | [080](080-adapter-rules-read-the-event-model.md) | adapter | AFK | 079 |
| 7 | [081](081-shared-enforcement-core.md) | core | AFK | 080 |
| 8 | [082](082-neutral-usage-log-and-report.md) | core | AFK | 078, 081 |
| 8 | [083](083-adapter-guide-and-worked-example.md) | docs | AFK | 081 |
| 9 | [084](084-pi-agent-adapter.md) | new adapter | HITL (build decision after research) | 082, 083 |
| 10 | [085](085-opencode-adapter.md) | new adapter | HITL (build decision after research) | 084 |

## Notes

- Same-wave adapter tickets share `adapters/claude-code/README.md` and the
  regenerated `skill-usage/tests/adapter-texts.ts`. Resolve those at merge
  time by regenerating.
- 085 could run beside 084, at the cost of some duplicated translation
  code.
