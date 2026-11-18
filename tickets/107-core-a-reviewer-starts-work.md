# Ticket 107: A Reviewer Starts Work

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-4.md` (addendum R12; AC14,
AC7, AC8)

## Type

AFK.

## What To Build

A reviewer agent is a finished spawn that starts work now (`starts_now`)
and is not `separate`, that no gate held, and whose brief follows
`subagent-driven-development`'s reviewer prompt. A spawn that only
proposes work ran nothing, so it neither meets the closeout's Review item
nor opens the `review-intake` gate, whatever its brief. The routing gates
already pass such a spawn because it runs nothing; this aligns the
reviewer check with them.

Today `actions._reviewer_returned` tests `call.ok`, the spawn kind,
`not call.separate`, the reviewer template and the report's arrival, but
not `starts_now`. The rule lives in the shared core at
`adapters/core/goated_core/`. The contract and a conformance scenario
change with the code, as `AGENTS.md` requires:

- `stack/enforcement-contract.md`, Reviewer Agents: the first sentence,
  which today says "whether it `starts_now` is not checked";
- `stack/fixtures/enforcement/writes.yaml` (the `review-intake`
  scenarios) or `closeout.yaml` (the Review item): a proposed spawn with a
  reviewer brief that meets no Review item, beside a started one that
  does.

## Recommended First Reads

- The parent spec's addendum, R12.
- `stack/enforcement-contract.md`: Terms (Spawn), Reviewer Agents, and the
  `Review` closeout row.
- The core's `_reviewer_returned` and its callers in `actions.py`.
- The event model's spawn fields `starts_now` and `separate`.

## Acceptance Criteria

- [ ] A finished spawn with `starts_now` false, not `separate`, and a
      reviewer brief meets no Review item and opens no `review-intake`
      hold.
- [ ] The same spawn with `starts_now` true still does both.
- [ ] The contract states the rule, and a conformance scenario covers the
      reviewer and the proposed-spawn near miss.
- [ ] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The conformance scenarios through the core.
- The core's reviewer tests, with a proposed spawn.
- The repo checks in `AGENTS.md`.

## Blocked By

- `tickets/081-shared-enforcement-core.md` (merged)

## Overlaps

- Ticket 102 edits `actions._closeout_items` (the Proof text) and
  `closeout.yaml`; this ticket edits `_reviewer_returned`, which the
  Review item calls. Different functions; the scenario file may be
  shared.

## Scope Exclusions

- How a harness sets `starts_now` or `separate`.
- Whether a review was any good, and the reviewer template's headings.
