# Ticket 114: Large Writes Land And Read After

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-5.md` (R5; AC7, AC5, AC6)

## Type

AFK. Decision L, option 1 as narrowed at review: it keeps the `design`
gate's hold for the skill's load and holds writes whose lines cannot be
counted (the maintainer chose and then confirmed it, 2026-11-18). At this
ticket's review the maintainer chose to let a first substantial edit land
too once the skill is loaded (2026-11-19: "Land it too").

## What To Build

A large write is never composed twice because a read gate held it.
`design-reads` and `reference-reads` hold a file or shell write only when
it adds fewer than thirty lines, counted as each gate counts them today.
A write whose lines cannot be counted (a shell write showing no text,
such as a heredoc holding `$(...)` or a program's output) counts as under
thirty and is held, so Tickets 093 and 097's coverage of shell writes
stays. A write adding thirty or more is applied and passes with a new
`reads_owed` notice naming each reference its signals select.

What a landed write still needs becomes a new closeout item, `Reads`. It
is met when each named reference is read whole or a lasting skip covers
it, and a change read of the file follows the reads. It holds a commit and
the turn's end as the other items do. Its skip line names the skill whose
references it asks for; a skip of it lasts as a skip of the gate it stands
for does (round 4's R4). A write under thirty lines is held as today.

The `design` gate still holds until `software-design-principles` loads
before the first substantial edit, and the reads it asks for with the
load stay a hold. Once the skill counts as loaded, a first substantial
edit of thirty or more counted lines, which `design` would hold for
reads alone, lands and owes its reads like any other (decided at review,
2026-11-19). A shell write counts only the lines it writes into the
files the gate judges, and the Reads item's change read is of the landed
file itself or a printed diff.

**Notice kind.** `reads_owed` is new, not a reuse: `closeout_note` is once
per turn after the first write, and `skip_carried` names a skip. So the
event model's notice enum gains it and its version moves to 4, and the
contract's Notices section lists it.

**Skill texts.** `software-design-principles`'s step 2 ("Read now") and
`skills/README.md`'s description of registry reference signals say that,
for a large edit already written, the reads may follow it before the
closeout, and the edit is revised after them. Run the context comparison.

The rules live in the shared core at `adapters/core/goated_core/`: where
`actions.py` judges a write against `design-reads` and `reference-reads`,
`_closeout_items`, and session state for what landed writes still need.
The contract changes with the code, as `AGENTS.md` requires: the
`design-reads` and `reference-reads` rows, the Closeout Items table (a new
stable label), Notices, and Hold Messages if they list labels; the event
model schema; and conformance scenarios under `stack/fixtures/enforcement/`
(a test fails when a closeout item lacks scenarios). Adapters that list
notice kinds follow the version bump.

**`shell.py`'s pull request reading:** not touched.

## Recommended First Reads

- The parent spec, R5 and decision L.
- `stack/enforcement-contract.md`: the `design`, `design-reads` and
  `reference-reads` rows, Holds, Closeout Items, Notices, and how lasting
  skips work.
- `stack/schemas/enforcement-event-model.schema.json`, the notice enum and
  version.
- The core's `actions.py` (`_design_hold`, `_reference_reads_hold`,
  `_closeout_items`) and `state.py` (`lasting_skips`).
- `tests/test_enforcement_contract.py`, for what a new closeout item needs.
- `tickets/archive/101-core-read-skips-last-the-task.md`, which added the
  last notice kind and its version bump.

## Acceptance Criteria

- [ ] With `software-design-principles` loaded, a 40-line edit whose
      signals select an unread reference is applied, with a `reads_owed`
      notice naming the reference.
- [ ] The turn's end and a commit then meet the `Reads` item until the
      reference is read whole and a change read of the file follows; a
      skip line naming the skill clears it.
- [ ] The same holds for a large write meeting `reference-reads` (a
      registry signal).
- [ ] A 29-line edit, and a shell write whose text the command does not
      show, are held as today.
- [ ] A large first edit with the skill not loaded still meets `design`;
      with the skill loaded it lands owing its reads.
- [ ] The event model is at version 4 with `reads_owed`, and the contract
      states the rule, the item and the notice; conformance scenarios
      cover the hold, the landed write, each way the item clears, and the
      near misses.
- [ ] The repo checks in `AGENTS.md` pass, including the context
      comparison.

## Expected Proof

- The conformance scenarios through the core.
- The core's gate and closeout tests; the Claude Code adapter's tests
  through its hook.
- The repo checks in `AGENTS.md`.

## Blocked By

- None.

## Overlaps

- Ticket 113 changes the same contract rows; it waits for this one.
- Ticket 116 changes `_closeout_items`; it waits for this one.
- Ticket 111 changes how holds share a message, not which hold fires.

## Scope Exclusions

- Announcing references before a write (option L2).
- The `design` gate's hold for the skill's load, and strict gates
  (`pipeline`, `commit`, `security`).
- `scripted-edit`, whose script is short and steered to a file edit tool.
