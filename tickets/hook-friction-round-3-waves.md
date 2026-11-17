# Hook Friction Round 3: Parallel Waves

Tickets 086 to 096 grouped by which can run at the same time, together
with the tickets of round 2 that had not started when round 3 was planned
(078 to 085). The order files remain the source of truth for blockers:
[low-signal holds](adapter-low-signal-holds-order.md) and
[hold delivery and coverage](adapter-hold-delivery-and-coverage-order.md)
for round 3, and
[skill-usage data detail](skill-usage-data-detail-order.md) and
[portable enforcement core](portable-enforcement-core-order.md) for
round 2. A ticket's wave is one after the latest of its blockers' waves.

This table replaces waves 5 to 10 of
[hook-friction-round-2-waves.md](hook-friction-round-2-waves.md). Waves 1
to 4 there are merged.

| Wave | Ticket | Round | Area | Type | Blocked by |
| --- | --- | --- | --- | --- | --- |
| 5 (ready now) | [078](078-skill-usage-reference-counts.md) | 2 | mod | AFK | 068, 076 (merged) |
| 5 | [086](086-adapter-repeated-failure-red-runs.md) | 3 | adapter | AFK | None |
| 5 | [087](087-adapter-routing-orientation-by-reads-and-outside-writes.md) | 3 | adapter and skills | AFK | None |
| 5 | [088](088-adapter-wider-plain-reads.md) | 3 | adapter | AFK | None |
| 5 | [089](089-adapter-design-holds-without-written-text.md) | 3 | adapter, skills, registry and mod | AFK | None |
| 5 | [091](091-adapter-review-size-and-installs.md) | 3 | adapter and skills | AFK | None |
| 5 | [093](093-adapter-inline-script-writes.md) | 3 | adapter and skills | AFK | None |
| 5 | [094](094-adapter-own-subagent-reports-continue-the-turn.md) | 3 | adapter | AFK | None |
| 6 | [090](090-adapter-test-edit-reference-thresholds.md) | 3 | adapter, skills and registry | AFK | 089 |
| 6 | [092](092-adapter-whole-reads-and-read-order.md) | 3 | adapter | AFK | 089, 091 |
| 6 | [095](095-adapter-joint-holds-in-one-message.md) | 3 | adapter and mod | AFK | 086, 087, 088, 089, 091, 093 |
| 7 | [096](096-adapter-early-closeout-note.md) | 3 | adapter | AFK | 095 |
| 8 | [079](079-enforcement-contract-and-event-model.md) | 2 | core | HITL (maintainer accepts the ADR and event model) | its round 2 blockers (merged), and 086 to 096 |
| 9 | [080](080-adapter-rules-read-the-event-model.md) | 2 | adapter | AFK | 079 |
| 10 | [081](081-shared-enforcement-core.md) | 2 | core | AFK | 080 |
| 11 | [082](082-neutral-usage-log-and-report.md) | 2 | core | AFK | 078, 081 |
| 11 | [083](083-adapter-guide-and-worked-example.md) | 2 | docs | AFK | 081 |
| 12 | [084](084-pi-agent-adapter.md) | 2 | new adapter | HITL (build decision after research) | 082, 083 |
| 13 | [085](085-opencode-adapter.md) | 2 | new adapter | HITL (build decision after research) | 084 |

## Decisions Recorded Here

The maintainer decided these on 2026-11-17, when round 3 was planned:

- **Round 3 runs before Ticket 079.** Ticket 079 writes the enforcement
  contract and conformance scenarios from the adapter's rules, and 080
  and 081 then move the rule code. Round 3 changes those rules and that
  code, so it lands first and the contract is written once. Ticket 079's
  "Blocked By" list and its order file name 086 to 096.
- **Tickets 079 to 085 keep their scope.** Two round 3 results reach
  them: the event model's decision must carry several holds (Ticket 095),
  and the contract gains the `scripted-edit` gate (Ticket 093) and loses
  the design-reads line and the citations item (Ticket 089).
- **Ticket 078 is unaffected** and runs beside wave 5. It counts
  reference reads in the mod; Ticket 092 later makes a partial read not
  count, and says so in the mod if the mod counts reads itself.
- **Ticket 071's skills line stays as shipped.** A brief must carry a
  `goated-skills:` line, and `goated-skills: none: <reason>` is its
  justified skip. No ticket.
- **A new code file or public definition still selects three design
  references.** No ticket.
- **Nothing is deferred.** Every item of the wave 4 feedback and of the
  earlier open list is in a ticket, was found already fixed, or is one of
  the two "no ticket" decisions above. Already fixed when checked against
  main: the `Stop` closeout on scratch files outside the project (Ticket
  058), and harness nudges opening turns (they are recorded as
  attachments).

## Where Each Feedback Item Went

| Feedback item | Ticket |
| --- | --- |
| `repeated-failure` counts TDD red runs; shows the `cd` | 086 |
| Briefed-session orientation load is ritual | 087 |
| Routing hold on a write outside the project | 087 |
| `router-first` holding read-only shell; side sessions paying a round trip to look around | 088 |
| Design citations feel like a form; lines for edits need a carrier call | 089, 095 |
| Red-flags reread after a two-line fix | 089 |
| Low-signal test-file triggers; holds on test-only edits | 090 |
| Review and Verification in a delegated wave; branch size counts tests | 091 |
| The setup item firing outside the project | 091 |
| A change read just before a skill load not counted | 092 |
| A partial read counts as read | 092 |
| Interpreter-script writes bypass every write gate | 093 |
| A subagent's report opens a new turn (found while planning) | 094 |
| Several holds on one call fire one at a time | 095 |
| Long repeated hold advice | 095 |
| Closeout timing after the final report | 096 |
| How many references one edit asks for | No ticket (kept) |
| The spawn-brief skills line: strict or justified skip | No ticket (kept) |

## Notes

- Same-wave adapter tickets share `adapters/claude-code/README.md` and
  the regenerated `skill-usage/tests/adapter-texts.ts`. Resolve those at
  merge time by regenerating.
- Tickets 088 and 093 both change the shell reading, in different
  functions.
- Tickets 087, 089, 090, 091 and 093 each change a skill's text. Each
  runs the context comparison; the router has about six words of headroom
  and the shared policy none.
- Ticket 096 adds a hook event to the install snippet. An existing
  install gets the early note only after its settings gain the event.
- 085 could run beside 084, at the cost of some duplicated translation
  code.
