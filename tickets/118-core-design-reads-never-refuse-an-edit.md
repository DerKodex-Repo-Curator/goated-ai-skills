# Ticket 118: Design Reads Never Refuse An Edit

## Parent Spec

`docs/specs/2026-11-19-hook-friction-round-6.md` (R1; AC1, AC2, AC14)

## Type

AFK. Decision S, option 1 (the maintainer, 2026-11-19). It reverses round
5's narrowed L1, under which a design read still refused an edit shorter
than a large write.

## What To Build

An edit that selects a design or registry reference lands at any size, and
the reference is owed. Today only a write of 30 or more lines lands
(Ticket 114); a shorter one is refused until the reference is read whole,
and when the refused edit is one of several sent in one message, its
siblings land and leave the file half-changed.

One agent can do this in two phases.

- **Phase 1, every edit lands.** The `design-reads` and `reference-reads`
  gates stop refusing a file edit. Every selected reference that has not
  been read whole since the last compaction joins the turn's owed reads,
  as a large write's references do today. The closeout Reads item
  collects them at a commit and at the end of the turn, and stays a
  justified skip. The `design` gate (load `software-design-principles`
  before code) is unchanged.
- **Phase 2, one notice per turn.** The turn's first landed edit that owes
  a read carries a notice listing the owed references. A later edit's
  notice names only references it newly adds, and says nothing when it
  adds none. A reference already read is never listed.

Which references a trigger selects, and how long a read counts, do not
change.

The rules live in the shared core at `adapters/core/goated_core/`. The
contract's Holds, Gates, Closeout Items and Design Reference Signals
sections, and conformance scenarios under `stack/fixtures/enforcement/`,
change with the code, as `AGENTS.md` requires. A lasting skip (Ticket 101)
must still cover a reference it covered before, now at the Reads item.

## Recommended First Reads

- The parent spec: R1, the Problem's first two items, decision S and the
  Deferred list.
- `stack/enforcement-contract.md`: Holds, Gates, Closeout Items (the Reads
  row), Design Reference Signals and Registry Reference Signals.
- `tickets/archive/114-core-large-writes-land-and-read-after.md` and
  `tickets/archive/101-core-read-skips-last-the-task.md`.
- The core's write judging and owed reads in `actions.py`, and
  `design_reads.py` and `reference_reads.py`.

## Acceptance Criteria

- [x] A 3-line edit adding a public function lands with a notice naming
      its references and meets no hold.
- [x] A commit in that turn is held by the Reads item until the owed
      references are read whole or declined with a skip line; the turn's
      end is held the same way.
- [x] A second edit selecting the same references adds no notice text; one
      selecting a new reference names only that one.
- [x] Four edits judged one after another, each selecting a reference, all
      land.
- [x] A reference read whole earlier in the context window is not owed.
- [x] A lasting skip for a reference still clears it at the Reads item.
- [x] The `design` gate behaves as before.
- [x] The contract states the rule, and conformance scenarios cover the
      landed edit, the Reads hold, each way it clears, and a near miss.
- [x] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The conformance scenarios through the core.
- The core's write and closeout tests; the Claude Code adapter's tests
  through its hook, including its generated text fixture.
- The repo checks in `AGENTS.md`.

## Blocked By

- None.

## Scope Exclusions

- Fewer references for a small definition, and section reads (deferred in
  the spec).
- Writes made by a shell command or an inline script.
- The words of the Reads item beyond what the new rule needs: Ticket 121
  reorders hold text.
