# Ticket 054: Overrides Ignore Pasted Text, And A Typed Commit Skip Works

## Parent Spec

`docs/specs/2026-11-17-adapter-hook-friction.md` (R11, R12; AC12, AC13)

## Type

AFK.

## Problem

Override phrases are parsed from the whole typed prompt, with only harness
`<system-reminder>` blocks removed. So a phrase inside text the user pasted,
such as agent feedback that mentions `skip commit-message`, is recorded as
an override.

That recorded override still didn't release the commit hold. The commit hold
checks whether `commit-message` has loaded before it looks at the user's
skips, so a typed `skip commit-message` never clears it. The README's
override table says `skip <skill>` stands down every requirement for that
skill. The pull request and spawn holds already check skips first.

## What To Build

- Text inside a `<pasted_content …>…</pasted_content>` block yields no
  override phrase. A phrase typed outside the block still counts, whether it
  comes before or after the block.
- A typed `skip commit-message` stands down the whole commit hold, its load
  step included, so the code matches the README.
- Update the README's User Overrides section to mention pasted blocks.

## Recommended First Reads

- The parent spec, R11 and R12.
- `adapters/claude-code/goated_adapter/overrides.py` (`parse_overrides`).
- `adapters/claude-code/goated_adapter/actions.py` (`_commit_hold`, and
  `_pr_hold` for the order the other holds use).
- `adapters/claude-code/README.md`: User Overrides.

## Acceptance Criteria

- [ ] `skip commit-message` inside a pasted block records no override. The
      same phrase typed after the block does.
- [ ] `skip routing` and a `commit message:` phrase inside a pasted block are
      ignored too.
- [ ] A typed `skip commit-message` lets a commit through with no load.
      Without it, the commit is still held at the load step.
- [ ] The skill-usage mod still counts the override from the hook's context.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.

## Blocked By

- None.

## Scope Exclusions

- Overrides from anything but a typed prompt (Ticket 047 stands).
- Other harness wrappers.
