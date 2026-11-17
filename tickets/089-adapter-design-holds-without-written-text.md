# Ticket 089: Design Holds Check No Written Text

## Parent Spec

`docs/specs/2026-11-17-adapter-low-signal-holds.md` (R6, R7, R8, R15; AC7,
AC8, AC9, AC16, AC17)

## Type

AFK.

## Problem

Two design holds still check text the agent wrote:

- The `design` gate asks for a `goated-design-reads:` line before the
  turn's first substantial code edit. The edit's signals already select
  the references to read, so the line only declares them again.
- The closeout's Design citations item asks for a `file#id` citation of
  each reference the turn's edits required. It is checked for presence
  only.

An edit call has no field for either, so agents make an empty shell call
to carry them. The agents said the value came from the reads and from the
red-flags question, not from the line or the citations.

The closeout's Design red-flags item also asks for the red-flags read
again after any code change, a two-line fix included.

## What To Build

- **No design-reads line.** The `design` gate asks for the
  `software-design-principles` load and the references the edit's signals
  select. No gate reads a `goated-design-reads:` line, and one an agent
  still writes is ignored without an error.
- **Remove the line everywhere it is defined or read:**
  `software-design-principles` (its workflow step and grammar), the marker
  grammar and fixtures under `stack/fixtures/markers/`, the marker
  validation, the registry and schema where they name it, the adapter, and
  the skill-usage mod's parsing, display and README.
- **Advisory reference.** A design reference no signal selects
  (`differences.md`) is declared advisory in the registry, with its
  reason, as `skills/README.md` describes.
- **No citations.** Remove the closeout's Design citations item and the
  citation convention in `software-design-principles`. Section ids and the
  Section Index stay as navigation. The adapter stops recording which
  references each edit required.
- **Red-flags reread.** After a red-flags read in the turn, later code
  changes that add fewer than five lines in total, comment-only changes
  aside, do not ask for the read again. The change read after the last
  change is still required. `software-design-principles` states the
  five-line rule beside its small-edit rule.
- Keep the Design red-flags item's question and what else it requires.
- The skill stays inside its context budget; the removed text should
  shrink it.
- Update the README's Design references section, the `design` row, the
  closeout table, Hold messages and Known Limits, and regenerate the hold
  texts for the skill-usage mod.

## Recommended First Reads

- The parent spec: Problem, R6 to R8, Constraints, Risks.
- `skills/engineering/software-design-principles/SKILL.md`: the workflow
  steps that name the line and the citations, and the Section Index.
- `adapters/claude-code/goated_adapter/design_reads.py`: `required`,
  `_signals`, the line parsing and `design_ids`.
- `adapters/claude-code/goated_adapter/actions.py`: `_design_hold`,
  `_code_items`, `_designing`, `_uncited_references`, `design_references`.
- `adapters/claude-code/goated_adapter/state.py`: `record_design_edit`;
  `hooks.py` where it is called.
- `stack/fixtures/markers/README.md`, `design-reads.yaml`, and
  `scripts/validation/markers.py`.
- `adapters/claude-code/skill-usage/hooks/` (`classify.ts`, `holds.ts`,
  `meaning.ts`, `view.tsx`) and its tests' design-reads fixtures.
- `adapters/claude-code/README.md`: Design references.
- Tickets 051, 052 and 061, for what the line and citations were for.

## Acceptance Criteria

- [ ] A substantial first edit with the design skill loaded and its
      selected references read passes with no line in the turn.
- [ ] The same edit with a reference unread is held, and the hold asks for
      the read and for no line.
- [ ] A written `goated-design-reads:` line changes no decision.
- [ ] A closeout after design edits lists no citations item.
- [ ] `software-design-principles` asks for no line and no citation, and
      its Section Index still lists every section id.
- [ ] The marker fixtures, the validators and the registry checks pass
      with the design-reads grammar gone and `differences.md` advisory.
- [ ] After the red-flags read and a change read, a two-line code fix asks
      only for a change read. A six-line fix, or three two-line fixes,
      asks for the red-flags read again.
- [ ] The mod's tests pass, and it still counts every `design`,
      `design-reads` and `closeout` hold.
- [ ] Existing tests pass unchanged except where one asserted the line or
      the citations; each such change is named in the closeout.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- The skill, marker and registry validators and the context comparison.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, and the mod's
  tests.

## Blocked By

None.

## Scope Exclusions

- Which signals select which references. A new code file or public
  definition still selects three.
- Test-file thresholds (Ticket 090).
- The red-flags question and the diff reread, which stay.
- Route and skip lines and their grammar.
