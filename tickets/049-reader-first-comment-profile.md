# Ticket 049: Reader-First Comment Profile

## Parent Spec

`docs/specs/2026-11-16-design-reference-reads.md` (R4; AC4)

## Type

HITL: the maintainer reviews the profile's wording against their own standard
before merge.

## Problem

The skill's default comment guidance ("inside functions, comment only intent
and surprises") is lighter than the reader-first standard some users and
projects want, such as code written for beginner-to-intermediate readers. With
`readability.md` read more often, an agent following the skill can contradict a
user's denser standard.

## What To Build

An opt-in section in `references/readability.md`, id `#reader-first-comments`,
with these rules in plain words:

- Every function, method, class, and type has a short docstring: what it is
  for and the one fact a caller cannot see from the signature, never a restated
  name. One line is enough for something small.
- A field, constant, or parameter whose purpose or unit is not obvious gets its
  own short comment.
- In a long function or script, a comment opens each step, in order: what the
  step achieves and why it happens there.
- A variable that carries state has a comment saying what each value means and
  when it changes.
- An unfamiliar call is explained where it is made: positional arguments,
  fixed values, and library behaviour a reader would not guess.
- A line that looks wrong or surprising says why it is there.
- Comments use short sentences and everyday words; an unfamiliar term is
  explained the first time it appears.
- Comments never narrate syntax.
- A reason is stated only when confirmed in the code; otherwise say the reason
  is not recorded.

Add a short example of that density and voice, written fresh with neutral
names. State when the profile applies: when a user or project asks for it, or
when the code's readers are beginner-to-intermediate programmers. Point rule 12
in `SKILL.md`, the `#comments` section, and the "How many comments" row in
`references/differences.md` to it. The default stays as it is.

## Recommended First Reads

- The parent spec, R4.
- `skills/engineering/software-design-principles/references/readability.md`
  (`#comments`) and `references/differences.md`.
- `AGENTS.md` (Public Boundary).

## Acceptance Criteria

- [ ] `#reader-first-comments` exists, lists the rules above, and has a neutral
      example.
- [ ] Rule 12, `#comments`, and the `differences.md` row name the profile and
      when it applies; the default guidance is unchanged.
- [ ] No private project names or personal context appear.

## Expected Proof

- The repo checks in `AGENTS.md`.
- The maintainer's review of the wording.

## Blocked By

- `tickets/048-design-reference-moment-triggers.md` (same `SKILL.md` and
  section index)

## Scope Exclusions

- Changing the default comment guidance for all users.
- Editing any personal instruction file.
