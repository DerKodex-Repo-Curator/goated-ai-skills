# Hook Friction Round 3: Parallel Waves

Tickets 086 to 097 grouped by which can run at the same time, together
with the tickets of round 2 that had not started when round 3 was planned
(078 to 085) and the tickets of round 4 (099 to 102). The order files
remain the source of truth for blockers:
[low-signal holds](adapter-low-signal-holds-order.md) and
[hold delivery and coverage](adapter-hold-delivery-and-coverage-order.md)
for round 3,
[skill-usage data detail](skill-usage-data-detail-order.md) and
[portable enforcement core](portable-enforcement-core-order.md) for
round 2, and [hook friction round 4](hook-friction-round-4-order.md) for
round 4. A ticket's wave is one after the latest of its blockers' waves.
This one table holds the waves of all three rounds; round 4 has no table
of its own.

This table replaces waves 5 to 10 of
[hook-friction-round-2-waves.md](hook-friction-round-2-waves.md). Waves 1
to 4 there are merged.

Waves 5 to 13 are merged, and so are wave 14 but 084 and 106 of wave 15.
Their tickets were archived under `tickets/archive/` on 2026-11-18: waves
5 to 9 (078, 079 and 086 to 097), and waves 10 to 15 (098, 080 to 083 and
099 to 107). 084 waits for a go-ahead to start, and 085 for 084.

| Wave | Ticket | Round | Area | Type | Blocked by |
| --- | --- | --- | --- | --- | --- |
| 5 | [078](archive/078-skill-usage-reference-counts.md) | 2 | mod | AFK | 068, 076 (merged) |
| 5 | [086](archive/086-adapter-repeated-failure-red-runs.md) | 3 | adapter | AFK | None |
| 5 | [087](archive/087-adapter-routing-orientation-by-reads-and-outside-writes.md) | 3 | adapter and skills | AFK | None |
| 5 | [088](archive/088-adapter-wider-plain-reads.md) | 3 | adapter | AFK | None |
| 5 | [089](archive/089-adapter-design-holds-without-written-text.md) | 3 | adapter, skills, registry and mod | AFK | None |
| 5 | [091](archive/091-adapter-review-size-and-installs.md) | 3 | adapter and skills | AFK | None |
| 5 | [093](archive/093-adapter-inline-script-writes.md) | 3 | adapter and skills | AFK | None |
| 5 | [094](archive/094-adapter-own-subagent-reports-continue-the-turn.md) | 3 | adapter | AFK | None |
| 6 | [090](archive/090-adapter-test-edit-reference-thresholds.md) | 3 | adapter, skills and registry | AFK | 089 |
| 6 | [092](archive/092-adapter-whole-reads-and-read-order.md) | 3 | adapter and mod | AFK | 078, 089, 091 |
| 6 | [097](archive/097-adapter-script-write-paths-by-name-and-folder.md) | 3 | adapter | AFK | 093 |
| 7 | [095](archive/095-adapter-joint-holds-in-one-message.md) | 3 | adapter and mod | AFK | 086 to 094, 097 |
| 8 | [096](archive/096-adapter-early-closeout-note.md) | 3 | adapter | AFK | 095 |
| 9 | [079](archive/079-enforcement-contract-and-event-model.md) | 2 | core | HITL (maintainer accepts the ADR and event model) | its round 2 blockers (merged), and 086 to 096 |
| 10 | [098](archive/098-adapter-contract-gaps.md) | 2 | adapter | AFK | 079 |
| 11 | [080](archive/080-adapter-rules-read-the-event-model.md) | 2 | adapter | AFK | 079, 098 |
| 12 | [081](archive/081-shared-enforcement-core.md) | 2 | core | AFK | 080 |
| 13 | [082](archive/082-neutral-usage-log-and-report.md) | 2 | core | AFK | 078, 081 |
| 13 | [083](archive/083-adapter-guide-and-worked-example.md) | 2 | docs | AFK | 081 |
| 13 | [099](archive/099-core-fixture-data-is-test-data.md) | 4 | core | AFK | 081 |
| 13 | [100](archive/100-core-narrower-reference-triggers.md) | 4 | core and registry | AFK | 081 |
| 13 | [102](archive/102-core-session-messages-continue-the-task.md) | 4 | core | AFK | 081 |
| 14 (ready, not started) | [084](084-pi-agent-adapter.md) | 2 | new adapter | HITL (build decision after research) | 082, 083 |
| 14 (merged) | [101](archive/101-core-read-skips-last-the-task.md) | 4 | core | AFK | 081, 099, 100 |
| 14 (merged) | [103](archive/103-core-shell-pull-request-names-its-repository.md) | 4 | core | AFK | 081 |
| 14 (merged) | [104](archive/104-core-script-receivers-and-posix-nul.md) | 4 | core | AFK | 081 |
| 14 (merged) | [105](archive/105-core-conflicts-opened-by-shell-reads-and-ended-by-commits.md) | 4 | core | AFK | 081 |
| 14 (merged) | [107](archive/107-core-a-reviewer-starts-work.md) | 4 | core | AFK | 081 |
| 15 (merged) | [106](archive/106-core-definition-starts-read-their-keyword.md) | 4 | core | AFK | 081, 101 |
| 15 | [085](085-opencode-adapter.md) | 2 | new adapter | HITL (build decision after research) | 084 |
| 16 (ready now) | [108](108-core-pull-request-options-between-noun-and-verb.md) | 4 | core | AFK | 103 (merged) |
| 17 | [109](109-core-one-pull-request-per-simple-command.md) | 4 | core | AFK | 108 (same lines) |

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
- **Ticket 078 keeps its scope** and runs beside wave 5. It counts
  reference reads in the mod. Ticket 092 makes a partial read not count
  and may change that counting, so 092 waits for 078.
- **Ticket 095 waits for every other round 3 ticket but 096.** It
  restructures the dispatch and the hold message that 086 to 093 change,
  and its turn marker resets on the turn boundaries 094 changes. That
  moved 095 to wave 7 and each later ticket one wave on.
- **Ticket 097 was added after wave 5 merged.** The new `scripted-edit`
  gate held a markdown edit whose script named its file in a variable.
  The maintainer asked for a follow-up: a name bound once to a string
  literal is read as that literal, and an unnamed write in a folder
  certainly outside the project is placed there. It runs in wave 6. It
  shares no function with 090 or 092, which do not touch the reading of
  inline scripts. Ticket 095 waits for it, and 079 through 095.
- **Ticket 098 was added by Ticket 079's review (2026-11-18).** Where the
  adapter is looser than the contract (orientation by partial reads, the
  design gates and shell writes, a subagent's commit), the contract states
  today's behaviour and marks each gap, and 098 fixes the code before 080
  moves it. That moved 080 to wave 11 and each later ticket one wave on.
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

## Round 4 (planned 2026-11-18)

Round 4 comes from the agents of Tickets 079, 095, 096 and 098.

- **It runs after Ticket 081.** Each rule changes once, in the shared core
  at `adapters/core/`, not in the Claude Code adapter that 080 and 081
  are moving.
- **Wave 13 runs 099, 100 and 102 beside 082 and 083.** None of them
  touches the usage log or the guide. 099 and 100 both edit the design
  gates' code (`applies` and `_signals`, different functions) and the
  same contract rows; resolve at merge time.
- **Ticket 101 waits for 099 and 100.** It changes how long skips of the
  same two gates last, on the same rows; once their narrower triggers
  land, the need for it can be judged again.
- **084 and 085 do not wait for round 4.** They call the core, so a rule
  change reaches them without a change of theirs.
- **The maintainer's decisions (2026-11-18),** each the recommended
  option in the
  [round 4 spec](../docs/specs/2026-11-18-hook-friction-round-4.md#decisions):
  - C2 (Ticket 101): a skip that clears a `design-reads` or
    `reference-reads` hold lasts until the task ends or the context
    compacts, for the same references and kind of file only; a later
    hold it covers passes with a notice.
  - D1.2 (Ticket 102): another session's message opens a new turn whose
    route is `continue`, with no override, and with proof, checks and
    skip lines starting empty.
  - D2.1 (Ticket 102): text only; the Proof text names the waiting case,
    and the existing verification skip line clears it.
- **The gap tickets (103 to 107) join wave 14 (2026-11-18).** Ticket 081
  left seven rule gaps documented in the contract; the spec's addendum
  ticketed six of them (`git pull --abort` is not a git option). The
  overlaps they had with 099, 100 and 102 went when wave 13 merged.
  The maintainer chose E1, F1 and G1 for 104 and 105.
- **Ticket 106 waits for 101.** Both change how the `design-reads` gate
  behaves in `design_reads.py` and its contract row; running them apart
  avoids a merge clash in the same rules.

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
| `scripted-edit` holds a script that names its file in a variable (found in use after 093) | 097 |
| A subagent's report opens a new turn (found while planning) | 094 |
| Several holds on one call fire one at a time | 095 |
| Long repeated hold advice | 095 |
| Closeout timing after the final report | 096 |
| How many references one edit asks for | No ticket (kept) |
| The spawn-brief skills line: strict or justified skip | No ticket (kept) |
| Round 4: `design-reads` treats fixture YAML as configuration | 099 |
| Round 4: the mocking reference fires on the bare word `patch` or `MagicMock` in data | 100 |
| Round 4: `readability.md` and the Design item for a docstring-only edit | 100 |
| Round 4: a skip line lasts one turn, so it repeats | 101 (decision C2) |
| Round 4: `route-line` holds after a lead's or peer's message | 102 (decision D1.2) |
| Round 4: Proof asked while a session waits on another | 102 (decision D2.1) |
| Round 4: the `true` carrier call for a line | No ticket (kept) |

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
