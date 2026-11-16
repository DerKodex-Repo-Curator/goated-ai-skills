# Ticket 032: Skill-Usage Mod In Repo

## Parent Spec

`docs/specs/2026-11-15-skill-enforcement-adapter.md` (R11 and AC7 in part, the
mod part of AC8)

Split on 2026-11-16 (maintainer decision) so that moving the mod can run
alongside Ticket 031. Reading 031's action and closeout holds is
[Ticket 034](034-skill-usage-mod-action-holds.md).

## Type

HITL. The maintainer must:

- provide or confirm the mod's current source;
- decide how the mod's tests run in CI;
- check one live session in the pane.

## What To Build

Bring the skill-usage Claude Code mod into the repo as an optional part of the
Claude Code adapter, made public-safe, and have it measure everything that
exists before Ticket 031:

- **Routing.** It records route lines (`goated-route:`) and the routing holds
  the merged adapter emits (router-first, route-line, required-skills), along
  with their outcomes.
- **Overrides.** It records user overrides, using the notice the adapter shows.
- **Skips.** It keeps recording justified skips (`goated-skip:` lines) as the
  `declined` outcome, with their reasons. The installed mod already does this
  as of 2026-11-16, along with settling nudges when a turn ends.
- **References.** It records reads of required reference files.
- **Subagents.** It records subagent spawns, including one that loads no
  skill, which today leaves the Subagents node blank. It also records the
  subagent start message and subagent reads of skill bodies.

The mod's skip-line and route-line reading must agree with the marker grammar.
Test it against `stack/fixtures/markers/lines.yaml`, so the copies of the
grammar in the adapter, the mod and the maintainer's personal hooks cannot
drift apart unnoticed. Keep the existing all-time history if the new store can
read it; otherwise start fresh with a note. Keep the hold texts of the
maintainer's personal hooks readable until Ticket 033 replaces those hooks.

## Recommended First Reads

- The spec's R11 and Analytics sections.
- `stack/fixtures/markers/README.md` and `lines.yaml`, the line grammar.
- `adapters/claude-code/README.md` and `goated_adapter/gates.py`, for the
  merged adapter's hold and notice texts.
- The mod's current source, which the maintainer points to at the start of the
  ticket. Its classifier owns hold parsing and which skill a path belongs to.

## Acceptance Criteria

- [ ] The mod lives in the repo next to the adapter, with no private paths,
      names, or data.
- [ ] Mod tests cover:
  - [ ] route lines;
  - [ ] the merged adapter's routing holds and their outcomes;
  - [ ] user overrides;
  - [ ] justified skips;
  - [ ] required-reference reads;
  - [ ] a subagent spawn that loads no skill;
  - [ ] the subagent start message.
- [ ] A test checks the mod's line reading against
      `stack/fixtures/markers/lines.yaml`.
- [ ] One live session shows a subagent spawn, a justified skip, and a route
      line in the pane.
- [ ] Install and remove docs for the mod exist.
- [ ] The maintainer has recorded a decision on running the mod's tests in CI.

## Expected Proof

- Mod test output.
- A screenshot or description of the live pane.

## Blocked By

- None. Ticket 030 is merged.

## Scope Exclusions

- Reading Ticket 031's action and closeout hold formats (Ticket 034).
- Changes to `adapters/claude-code/goated_adapter/`, which Ticket 031 is
  editing in parallel.
- A standalone, non-GOATED release of the mod.
- Enforcement logic. The mod displays only.
