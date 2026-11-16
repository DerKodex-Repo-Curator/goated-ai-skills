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
- [x] The maintainer has recorded a decision on running the mod's tests in CI.

## Decisions

Recorded 2026-11-16 by the maintainer:

- **CI.** The Python drift check of the mod's marker fixtures runs with the
  unit tests on every change. A separate `Skill-usage mod` workflow runs
  `claude plugin validate` and `claude plugin test` on a pinned Claude Code
  version, only when the mod, `stack/fixtures/markers/`, or the workflow
  change. The pin is bumped deliberately because the plugin API is early
  access. The tests make no model calls and passed locally with no
  credentials.
- **Overrides.** A probe on Claude Code 2.1.325 showed that a hook's notice
  reaches a mod as a `hook-context` row named `hook_system_message` with no
  text, and no other mod API exposes it. The adapter should also send its
  override sentence as hook context, which mods receive with text, so that the
  adapter stays the one owner of what counts as an override. That adapter
  change is in Ticket 034. Until then the mod counts no overrides live.
- **Writing turns.** The mod counts turns that write (the main agent's edits
  and spawns) by whether a route line came before the first write, only
  after it, or not at all. A turn runs from one typed prompt to the next.

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
