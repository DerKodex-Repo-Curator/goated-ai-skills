# Ticket 041: Adapter Review Holds Need A Read Of The Change

## Parent Spec

`docs/specs/2026-11-15-skill-enforcement-adapter.md` (R7, change reads;
AC10)

## Type

AFK.

## Problem

In real use with the adapter installed, a closeout hold asked for
`software-design-principles`' red flags. The agent read `red-flags.md`, the
hold cleared, and the agent judged the change against what it remembered
writing, not the diff. Asked afterwards, it reread the diff and found a real
bug. The adapter counts a review skill as followed once it loads or its
reference is read; nothing checks that the agent then looked at the change.
The skills already ask for it: `software-design-principles` says to reread
the diff, and `doc-sync`, `code-security-review`, `commit-message`, and
`pr-description` each say to inspect it.

## What To Build

A **change read** requirement on the holds whose step reviews or describes
the change. A change read is a finished call, made after both the skill load
or reference read and the last code change it covers, that puts the change's
content in front of the agent:

- a command that prints the changes themselves, such as a git diff, show, or
  patch log (a listing of names or a summary, such as `--stat`,
  `--name-only`, `--name-status`, or `--quiet`, does not count); or
- a Read of a file the turn changed.

It applies to:

| Hold | Today it clears when | It also needs |
| --- | --- | --- |
| closeout, Design item | `red-flags.md` is read after the last change | a change read after that read |
| closeout, Docs item | `doc-sync` loads | a change read after the load and the last change |
| closeout, new Security item | (no item today) | when `code-security-review` loaded this turn and a security-sensitive file changed: a change read after the load and the last sensitive change |
| commit | `commit-message` loads and the message passes its contract | a change read after the load |
| pull-request | `pr-description` loads | a change read after the load |

A skip line, where the hold already accepts one, and a typed user override
still clear each item as today. A commit message the user typed still stands
the commit hold down. The holds that do not review the change (router-first,
route-line, pipeline, spawn, the pre-edit design and security holds, the
closeout Proof and Unfinished items) stay as they are.

Hold texts name the change read in plain words. They must not put a command
in backticks, because the skill-usage mod reads a backticked name as a skill
to load. Each hold keeps its first line and kind.

## Recommended First Reads

- The spec's R6 and R7, and AC10.
- The adapter README (`adapters/claude-code/README.md`): What It Holds,
  Hold messages, User Overrides, State, Latency.
- The action and closeout gates in `adapters/claude-code/goated_adapter/actions.py`,
  the command analysis in `goated_adapter/shell.py`, and their tests in
  `tests/test_claude_code_adapter_actions.py`.
- How the skill-usage mod reads a closeout hold's asks and settles them
  (`adapters/claude-code/skill-usage/hooks/classify.ts`), and the hold-text
  generator `tests/test_skill_usage_mod.py`. If ticket 039 has landed, its
  settlement module instead.

## Acceptance Criteria

- [ ] A turn that changed code, loaded `software-design-principles`, read
      `red-flags.md` after the change, and then ended without a change read
      is held at closeout; the same turn with a diff printed after the
      red-flags read is not.
- [ ] A change read made before the red-flags read, or before the last code
      change, does not count.
- [ ] A `--stat` or name-only listing does not count; a Read of a changed
      file does.
- [ ] The Docs item, the new Security item, the commit hold, and the
      pull-request hold each hold without a change read after their load and
      clear with one.
- [ ] Skip lines, typed overrides, and a user-typed commit message clear
      them as before; the other holds' behaviour is unchanged.
- [ ] Hold texts backtick only skill names, and each hold keeps its first
      line, `goated-hold: <gate> | <kind>`.
- [ ] The adapter README's tables name the change read for each item, and
      say that it can be met by a token read: it puts the change in front of
      the agent, it does not prove a review.
- [ ] `tests/adapter-texts.ts` is regenerated, and the skill-usage mod's feed
      names the change read among what settled a hold.

## Expected Proof

- Adapter tests driving the hook with recorded-shape transcripts: each item
  held without a change read, cleared with one, and the order and listing
  near misses above.
- `uv run python -m unittest discover -s tests` on Python 3.11 and 3.14,
  `uv run python scripts/validate_skills.py`,
  `uv run python scripts/compare_v1_v2_context.py`, and `claude plugin test .`
  in the mod folder.
- A live check: one real turn that reads the red flags and is then held until
  it reads the diff.

## Blocked By

- `tickets/archive/033-adapter-real-use-trial.md` (the trial's keep decision)

## Scope Exclusions

- Judging whether the agent reviewed well: the adapter can only make it
  look at the change.
- The planned `pr-review` gate: ticket 038 adds it and applies this
  ticket's change read to it.
- The other adapter issues logged during the 033 trial, unless the trial's
  revise decision folds them into this ticket.
