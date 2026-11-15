# Ticket 032: Skill-Usage Mod In Repo With Enforcement Measurement

## Parent Spec

`docs/specs/2026-11-15-skill-enforcement-adapter.md` (R11, AC7, mod part of
AC8)

## Type

HITL. The maintainer must:

- provide or confirm the mod's current source;
- decide how the mod's tests run in CI;
- check one live session in the pane.

## What To Build

Bring the skill-usage Claude Code mod into the repo as an optional part of the
Claude Code adapter, made public-safe, and extend it to measure the redesign.
It should record:

- route lines;
- holds, by strict or justified-skip type, and their outcomes;
- justified skips with their reasons;
- user overrides;
- required-reference reads;
- subagent spawns, the subagent start message, and subagent reads of skill
  bodies.

Today a spawned subagent that loads no skill leaves the Subagents node blank.
Retire markers for hold texts the adapter no longer emits. Keep the existing
all-time history if the new store can read it; otherwise start fresh with a
note.

## Recommended First Reads

- The spec's R11 and Analytics sections.
- The hold-message and marker formats documented by Tickets 029 and 031.
- The mod's current source, which the maintainer points to at the start of
  the ticket. Its classifier owns hold parsing and which skill a path belongs
  to.

## Acceptance Criteria

- [ ] The mod lives in the repo next to the adapter, with no private paths,
      names, or data.
- [ ] Mod tests cover every R11 event type, including a subagent spawn that
      loads no skill.
- [ ] One live session shows a subagent spawn, a hold, a justified skip, and a
      route line in the pane.
- [ ] Install and remove docs for the mod exist.
- [ ] The maintainer has recorded a decision on running the mod's tests in CI.

## Expected Proof

- Mod test output.
- A screenshot or description of the live pane.

## Blocked By

- `tickets/031-claude-code-adapter-action-and-closeout-gates.md`

## Scope Exclusions

- A standalone, non-GOATED release of the mod.
- Enforcement logic. The mod displays only.
