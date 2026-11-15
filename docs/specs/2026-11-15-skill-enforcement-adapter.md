# Skill Enforcement: Descriptions, Router Map, And An Opt-In Claude Code Adapter

## Status

Approved by the maintainer on 2026-11-15, after a grill the same day settled
every decision below. It depends on
[ADR 0003](../adr/0003-opt-in-framework-enforcement-adapters.md), accepted
alongside it.

## Mode

Full. The work crosses skills, shared policy, a new framework adapter, a
measurement tool, and a product-boundary ADR.

## Problem

Agents running the GOATED stack skip the skills meant to guide them. In one
observed incident a hook asked an agent to load `handoff`; the agent repeated
the held action unchanged, which the hook lets through, and never read the
skill. It had done the same with the commit and design holds.

An analysis of the maintainer's personal hook trial
(`~/.claude/hooks/goated-hooks.ps1`, outside this repo) and of skill-usage data
from 14 sessions found:

- **Holds advertise their own bypass.** Route, design, security, and PR holds
  tell the agent to repeat the action unchanged and that it will pass.
- **No check proves a skill was used.** Every gate tests only whether a skill
  name was recorded as loaded at some point in the session. A morning load of
  `commit-message` satisfies an evening commit. Requested reference files are
  never checked; 4 reference reads occurred across 14 sessions. The end-of-turn
  check is satisfied when the reply merely names the missing skill. Hooks
  receive the transcript path and never read it.
- **Enforcement sits at the wrong end.** The delivery pipeline starts with
  orientation, clarification, spec, plan, and `tdd`; none is enforced. Only
  `commit-message` is, plus side checks for design, security, PR, and spawn.
- **Holds fire after compliance.** The commit hold fired 30 times when
  `commit-message` was already loaded, teaching agents that holds are noise to
  retry past.
- **Skills cannot be found on their own.** About ten descriptions trigger only
  when the user asks or explicitly requests, including `commit-message` and `pr-description`, which agents
  need when they act on their own. Others use GOATED-internal vocabulary that
  ordinary prompts never match.
- **The shared policy is not loaded.** `stack/AGENTS.md` is installed but
  nothing in the maintainer's Claude Code setup imports it, so the router runs
  its fallback.
- **The router names gates, not skills.** Its gate table says "clarification"
  or "writing plan"; the gate-to-skill mapping exists only in
  `docs/how-to-use.md`, which is not installed.
- 20 of 40 skills were never loaded. The data set is small and mostly from this
  repo.

The affected people are GOATED users who want the stack applied reliably, and
the maintainer, who cannot currently tell whether a skill shaped the work.

## Goals

- An agent that meets a moment the stack covers loads the right skill, in the
  turn it applies, without a free bypass.
- Skills are discoverable from their descriptions when agents act on their own,
  in every framework, without hooks.
- The router's choice of route is visible to hooks as a machine-readable line.
- The maintainer can measure, per session, which skills were required, loaded,
  read, and justifiably skipped.
- Skills stay standalone and framework-agnostic; enforcement is an opt-in layer.

## Non-Goals

- No enforcement for frameworks other than Claude Code in this spec. The
  adapter shape must allow later ones.
- No registry schema field for invocation topology. The 2026-07-27 NO-GO in
  `docs/invocation-topology-decision-report.md` stands.
- No change that makes any skill depend on the adapter or on this repo's root
  files.
- No standalone, non-GOATED release of the skill-usage mod. That remains a
  separate later project.
- No automatic installer. The adapter installs by documented manual steps.

## Requirements

### R1: Skill descriptions fire on agent-side moments

Rewrite descriptions that trigger only on user requests, or that use
stack-internal vocabulary, so they also name the agent-side moment or symptom
when the skill applies. For example, `commit-message` applies before any agent
commit, not only when the user asks for one. Skills that should stay
user-requested only, such as `caveman` and `grill-me`, keep that wording
deliberately. Each description still follows `skills/README.md`: it is for
discovery only and holds no workflow steps.

### R2: Shared policy actually loads

The Claude Code install documentation shows how to load `stack/AGENTS.md` into
the instruction file Claude Code applies (for example, an import from the user
or project `CLAUDE.md`). The adapter detects at session start when the shared
policy is not loaded and says so once.

### R3: Router gate-to-skill map

The router names the specialist skill or skills for each gate, so an installed
router no longer depends on `docs/how-to-use.md` for that mapping. It stays
inside the 300-line soft cap.

### R4: Route line

At the end of routing, the router emits one machine-readable line:

- `goated-route: direct` for tiny work that needs no specialist skill;
- `goated-route: <lightweight|standard|full> | requires: <skill>, <skill>` when
  specialist skills must load before the first write;
- `goated-route: continue` on a later prompt that continues the current task.

The line belongs to the router's portable output contract, so it is useful
without hooks. Its exact grammar is fixed in the architecture step.

### R5: Opt-in Claude Code enforcement adapter

The repo ships an optional Claude Code adapter, enabled only by a user who
installs it. It enforces:

- **Router first.** The first write or command of a session, and of each new
  task after compaction, is held until the router has loaded. Reads stay free.
- **Route line per task.** The first write after a new user prompt needs a
  route line in the current turn. A continuation writes
  `goated-route: continue`.
- **Pipeline gates.** Writes are held until the skills listed in the current
  route's `requires:` have loaded for this task. `direct` exempts the task.
- **Action gates.** Commit, PR creation, and spawning an agent or session are
  held strictly. Design and security holds accept a justified skip.
- **Closeout.** After a turn that changed code: fresh proof is required, plus
  `doc-sync` when behavior or interfaces changed and `handoff` when work is left
  unfinished. Each accepts a justified skip.

### R6: No free retry

No hold lets an unchanged repeat through.

- A **strict** hold blocks until the skill has loaded.
- A **justified-skip** hold also passes when the current turn contains a line
  of the form `goated-skip: <skill>: <reason>` naming that skill. The reason is
  recorded.
- A hold does not fire again once the skill has been applied for that action,
  so compliance stops further prompting.

### R7: Proof of use

- **Baseline:** a successful Skill-tool load of the skill in the current turn,
  confirmed from the transcript.
- **Required references:** where a reference is the point of the step, it must
  also have been read. Initially that is `handoff`'s `references/spawn-brief.md`
  for spawns and `software-design-principles`' `references/red-flags.md` at
  closeout.
- **Content checks**, only where the text is in the tool input: a spawn brief
  carries its template's required sections, and a commit message follows the
  `commit-message` contract.

### R8: User overrides come only from the user

A user-prompt hook records explicit overrides from text the user typed, such as
a supplied commit message, "skip routing", or skipping a named skill. A matching
hold stands down for that turn. An agent's own text never counts as an
override. The phrase set is documented with the adapter.

### R9: Subagents

Inside subagents the action gates (commit, PR, design, security) apply.
Router-first, route-line, and pipeline gates do not: the parent's brief carries
the route.

### R10: Implementation

The adapter's hooks are Python standard library only, run on Windows, macOS,
and Linux, and are covered by the repo's existing unit-test suite and CI.

### R11: Measurement

The skill-usage mod moves into the repo as an optional part of the Claude Code
adapter. It is updated to record:

- route lines;
- holds, by strict or justified-skip type, and their outcomes;
- justified skips with their reasons;
- user overrides;
- required-reference reads;
- subagent spawns, the subagent start message, and subagent reads of skill
  bodies.

Today a subagent that loads no skill leaves the Subagents node blank.

## Acceptance Criteria

- [ ] AC1: Every description changed under R1 names an agent-side moment or
      symptom, and keeps any deliberate user-only wording. The validator passes.
- [ ] AC2: Following the documented steps on a fresh Claude Code setup loads
      `stack/AGENTS.md`. Leaving it unloaded produces the adapter's one-time
      notice.
- [ ] AC3: The router names a skill for every gate, emits a route line in each
      of the three forms, and stays under 300 lines.
- [ ] AC4: Hook unit tests feed recorded hook inputs and transcript fixtures,
      and show:
      - router-first, route-line, and pipeline holds fire and clear as R5
        describes;
      - an unchanged retry never passes any hold;
      - a `goated-skip` line passes only justified-skip holds;
      - a load in an earlier turn does not satisfy a later action;
      - a required reference that was not read keeps the hold;
      - a malformed spawn brief or commit message is held;
      - a user-typed override stands a hold down;
      - the same text written by the agent does not;
      - subagents get only action gates.
- [ ] AC5: The adapter passes those tests on Python 3.11 and 3.14 in CI and
      uses only the standard library.
- [ ] AC6: The repo's skill validator and the context comparison still pass,
      and no skill references the adapter as a hard dependency.
- [ ] AC7: The mod, in the repo, shows a subagent spawn and every event type
      R11 lists in its own tests and in one live session.
- [ ] AC8: Install docs cover enabling, disabling, and removing the adapter and
      the mod.
- [ ] AC9: After several real sessions with the adapter installed, the mod
      shows all of the following, and the maintainer records keep, revise, or
      revert:
      - zero holds passed without the skill loading or a logged justified skip
        or user override;
      - every hook-required skill loaded in the turn it applied;
      - a route line on every turn that writes.

## Proof Surface

- AC4 and AC5: the Python adapter's hook entry points, driven with recorded
  hook inputs and transcript fixtures.
- AC7 and AC9: the skill-usage pane in the Claude Code desktop app.

## Constraints

- ADR 0003 must be accepted before any adapter code lands. Until then, ADR
  0001/0002 exclude hooks.
- Skills remain standalone (ADR 0002): a skill installed without the adapter
  behaves as it does today apart from its rewritten description and, for the
  router, the route line and skill map.
- `description` fields stay discovery-only; no new top-level frontmatter fields
  (`skills/README.md`).
- Public boundary: no private paths, names, or personal data in the adapter,
  mod, docs, or fixtures (`AGENTS.md`).
- Hooks must stay fast enough not to be noticed on every tool call. They read
  only the current turn's part of the transcript.
- The mod's tests run on Claude Code's mod test runner (`claude-code/testing`),
  which the repo's CI does not have.

## Open Questions

- Where the adapter and mod live in the repo (for example `adapters/claude-code/`
  as a new top-level folder recorded in `AGENTS.md`). Decided in the
  architecture step. Recommended: a new top-level `adapters/` folder, since the
  mod is not stack policy.
- Whether the adapter's rule table (which moments hold for which skills) lives
  in the adapter or in the registry. Recommended: the adapter, to avoid a
  registry schema change; revisit when a second framework arrives.
- How the mod's tests run in CI, if at all. Owner: maintainer, at the mod
  ticket.
- The exact route-line and skip-line grammar. Settled in architecture, with
  fixtures.

## Architecture

Accepted seams:

- **Skills stay framework-agnostic.** R1 descriptions, R3 router map, and R4
  route line are portable text changes.
- **Adapter.** The adapter is a Claude Code layer. It reads hook input and the
  current turn of the transcript, keeps per-session state, and returns hold or
  pass decisions.
- **Mod.** The mod reads the same transcript and the adapter's hold messages,
  and only displays; it never enforces.
- **One parser.** One documented contract defines hold-message and marker
  formats (`goated-route`, `goated-skip`, hold names), so the adapter and the
  mod stay in step.

## Rollout

1. Land the portable changes (R1–R4) first; they help with or without hooks.
2. Land the adapter and mod. Install the adapter on the maintainer's machine
   in place of `goated-hooks.ps1` and the router-nudge script, which stay
   untouched until the adapter's tests pass.
3. Run several real sessions and judge them against AC9.
4. Rollback is uninstalling the adapter: skills keep working, and the old
   personal scripts can be restored from the maintainer's machine.

## Migration

- The personal PowerShell hooks are retired, not moved; their behavior is
  re-specified here. Their cooldown rules (once-per-session design tip,
  red-flags every third turn) are re-evaluated against R6 rather than copied.
- The installed mod's existing all-time history is kept if the new store can
  read it, and otherwise restarts with a note.

## Analytics

The mod is the measurement tool; AC9 states the targets. Never-loaded skills
are tracked with no target.

## Risks

- **Over-blocking.** A wrong trigger blocks legitimate work. Mitigations:
  justified skips on non-strict holds, user overrides, `direct` routes, and
  uninstalling the adapter. Owner: maintainer, at AC9.
- **Throwaway skip reasons.** Agents may write empty justifications. Mitigation:
  the mod lists every skip reason for review. Owner: maintainer.
- **Route-line ceremony.** One line per writing turn adds noise. Mitigation:
  `continue` is one short line; revisit at AC9.
- **Transcript format drift.** Claude Code may change its transcript JSONL.
  Mitigation: the parser is isolated and tested against fixtures, and fails
  open with a visible warning instead of blocking everything.
- **Hook latency on Windows.** Mitigation: Python start-up plus tail-reading
  the transcript; measure during the adapter ticket.

## Sources

- `docs/how-to-use.md:26-28` — hooks and automatic activation are currently out
  of scope; `:604-627` holds the gate-to-skill mapping.
- `docs/adr/0001-v1-runtime-bootstrap-and-adapter-automation.md:40`,
  `docs/adr/0002-v2-integrated-stack-foundation.md:64` — the hook exclusions
  ADR 0003 supersedes.
- `docs/specs/2026-11-13-software-design-principles.md` (R4) — enforcement hook
  previously declined.
- `docs/invocation-topology-decision-report.md` — NO-GO on registry invocation
  metadata; unaffected.
- `skills/README.md` — description and frontmatter rules.
- `skills/agent-workflows/using-goated-ai-skills/SKILL.md` — gate table,
  checkpoints, and output contract that R3 and R4 extend.
- `stack/AGENTS.md:3-5` — the shared policy must be explicitly loaded.
- `.github/workflows/` and `pyproject.toml` — CI runs on Python 3.11 and 3.14
  with uv.
- Maintainer's hook trial and skill-usage data (outside the repo, not linked):
  source of the problem evidence above.
