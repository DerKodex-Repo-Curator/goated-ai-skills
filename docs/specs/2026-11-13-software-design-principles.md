# Software Design Principles Skill

## Status

Approved by the maintainer on 2026-11-13 for the experimental branch
`update/software-design-principles`, cut from `update/lean-skills`. Not yet
accepted for `main`.

## Mode

Compact.

## Problem

The stack tells agents how to plan, prove, review, and verify work, but its
design guidance is thin and scattered. Deep modules appear in four places.
Naming and comment guidance is three sentences of shared policy. Nothing asks
an agent to compare two designs, give each design decision one owner, choose an
error strategy, avoid settings that dodge a decision, or avoid code it cannot
explain.

The maintainer wrote a Software Design Field Guide that merges two books by
theme, in the maintainer's own words. At about 14,500 words it is too large to
load in every session.

## Goals

- Agents apply the guide's core rules by default when they design, change, or
  review code.
- The guide's checks run at the moments that already exist in the stack:
  architecture design, architecture review, planning, test-first work, and
  refinement.
- The always-on cost stays close to zero.
- Each rule has one home. Other skills point to it by section id.

## Non-Goals

- No enforcement hook, router gate, registry schema change, or new route
  signal.
- No design gate in `standards-and-spec-review` or
  `verification-before-completion`.
- No change to `agent-instructions-integrator`.
- No numbered restatement of either book's full tip or principle list, and no
  quoted passages from the books.
- No change to the maintainer's personal instruction files or the installed
  copy.
- No commits, pushes, installs, or acceptance into `main`.

## Requirements

### R1: New skill

`software-design-principles` (engineering). `SKILL.md` holds the operating
rules, three checklists (before starting, while coding, before reporting done),
a section-id index, and the precedence statement. `references/` holds the
red-flag table and the reasoning, split by theme:

- `red-flags.md`
- `complexity-and-modules.md` (includes the glossary)
- `decoupling.md`
- `errors.md`
- `readability.md`
- `process.md`
- `coding.md`
- `concurrency.md`
- `differences.md`

The guide's sections on careers, learning, communication, estimating, tools,
teams, and ethics are left out, as are the full tip and principle lists.
Sub-headings that were empty in the agent edition are filled in plain words
from the maintainer's full edition.

The skill is reached by description and by soft dependencies. Its defaults
yield to system, user, and project instructions and to a project's own
standards. Every "do not overdo it" limit in the guide is kept.

### R2: Always-on text

The readability paragraph in `stack/AGENTS.md` is rewritten in place to state
the goal, the two threats, the per-edit rules, and a pointer to the skill. The
shared policy stays within its 1,200-word target.

### R3: Gates in existing skills

- `design-codebase-architecture`: two interface sketches that differ in kind
  where the interface choice matters, with the rejected one recorded; a check
  that each design decision has one owning module.
- `review-codebase-architecture`: information leakage and temporal
  decomposition named as friction to look for.
- `writing-plans`: the plan names the owning module and points to the
  before-starting checklist.
- `tdd`: for a new module or public function, settle the interface before the
  first test; the refactor step holds the change to "looks designed for it".
- `code-refinement`: the red-flag names are the vocabulary for concrete debt.

`writing-plans`, `tdd`, and `code-refinement` do not grow in word count. Each
gate is a soft dependency with a local one-line fallback.

### R4: Decisions recorded

- Test ordering: `tdd` governs. Production behavior still waits for a failing
  test. The guide adds a design moment before the first test; it does not
  permit tests after.
- Comment quantity: the skill defaults to an interface comment on every public
  class and function, and yields to project and user instructions.
- Fixing flaws on sight: the stack's scope rule governs. Out-of-scope flaws
  are noted, not fixed.
- Design it twice applies to important design decisions, not to every new
  function.
- Unclear requirements: the shared policy's clarification modes govern.
- Enforcement hook: declined. Hooks are framework-specific and a standing
  non-goal of the stack.

### R5: Human edition

The full HTML edition is stored at
`docs/reference/software-design-field-guide.html` as a companion for people. It
is not part of the installable skill.

## Acceptance Criteria

- [ ] AC1: The skill is implemented, registered, covered by a fixture,
      self-contained, and listed in the public catalogue.
- [ ] AC2: `SKILL.md` is under the 1,500-word decomposition threshold and
      states that its defaults yield to system, user, and project instructions.
- [ ] AC3: The shared policy is at or under 1,200 words.
- [ ] AC4: Each R3 gate is present in the named skill, and `writing-plans`,
      `tdd`, and `code-refinement` have not grown in word count.
- [ ] AC5: A unit test proves that every section id cited by any skill or by
      the shared policy exists in the new skill's files, and that every id in
      the skill's index resolves to the file it names.
- [ ] AC6: The validator, the unit tests, and the V1/V2 context comparison
      pass, with every route at or above the 10% floor.
- [ ] AC7: Test edits to existing assertions are limited to numeric and count
      pins.
- [ ] AC8: After a period of real use, the maintainer records keep, revise, or
      revert.

## Constraints

- Individually installed skills keep a standalone fallback; no skill gains a
  hard dependency on the new one.
- Skills point to the new skill by name and section id. They do not link into
  its files or copy its text.
- The guide's rules are guidelines for judgement and stay worded that way.

## Open Questions

- Does the narrower description load the skill when it should, and stay out of
  tiny mechanical edits? Owner: GOATED maintainer, after the trial period.
  There is no live evaluation harness, so the repository's checks cannot
  answer this.

## Sources

- `AGENTS.md` and `skills/README.md` — maintainer contract and lean schema.
- `docs/specs/2026-10-06-lean-skills-update.md` — word-budget constraints and
  the precedent for adding skills on a trial branch.
- The maintainer's Software Design Field Guide, agent edition and full
  edition, dated 2026-11.
