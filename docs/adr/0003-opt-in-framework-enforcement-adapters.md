# ADR 0003: Opt-In Framework Enforcement Adapters

## Status

Accepted on 2026-11-15, with the spec
[Skill Enforcement](../specs/2026-11-15-skill-enforcement-adapter.md).

This ADR supersedes only the "hooks or prompt injection"
exclusion that [ADR 0002](0002-v2-integrated-stack-foundation.md) carried
forward from [ADR 0001](0001-v1-runtime-bootstrap-and-adapter-automation.md).
It also supersedes ADR 0001's exclusion of hook-based skill activation. Every
other exclusion in ADRs 0001 and 0002 remains in force:

- runtime bootstrap that a user did not opt into;
- generated plugin manifests;
- installer or adapter-repair automation;
- automatic framework detection;
- executable orchestration.

## Context

ADR 0001 kept GOATED a portable skill library and excluded hooks because they
are framework-specific and would turn the product into runtime plugin
distribution. ADR 0002 kept that exclusion.

Real use since then shows that text alone does not make agents load skills.
Agents skip the router and specialist skills even when a session-start rule
calls them mandatory. A personal hook trial outside this repo raised skill
loading, but its holds could be bypassed by repeating the held action, and it
never checked that a skill was used in the turn it applied. Without
enforcement, the stack's pipeline is advisory, and the maintainer cannot tell
whether a skill shaped the work.

Portability is still the product's core value. A user who installs skills
alone, or uses a framework without hooks, must lose nothing.

## Decision

GOATED may ship **opt-in enforcement adapters**: framework-specific layers
that a user installs deliberately, which use that framework's hooks to:

- hold actions until the skill the stack requires has loaded;
- check proof of use from the session transcript;
- record what happened for measurement.

Rules for every adapter:

1. **Opt-in only.** Nothing in a skill, the shared policy, or the registry
   requires an adapter. Skills keep their standalone fallbacks.
2. **Enforce portable contracts, never define them.** Adapters enforce
   behavior that skills, the router, and the shared policy already describe in
   framework-agnostic text, such as the route line and skip line. They do not
   add rules found nowhere else.
3. **No free bypass.** A hold passes only on proof of use, a justified skip
   recorded in the agent's output where the hold allows one, or an explicit
   override typed by the user.
4. **Fail open, visibly.** If an adapter cannot read its inputs, it lets the
   action through and says so. It never silently blocks.
5. **Tested in this repo.** Adapter logic is covered by the repo's test suite
   and CI.

The first adapter targets Claude Code. Adapters for other frameworks need
their own ticket, but not a new ADR, provided they follow these rules.

## Consequences

Positive:

- users who want reliable skill use can opt into it;
- portable changes the adapter depends on help every framework: discoverable
  descriptions, the router's skill map, and the route line;
- skill usage becomes measurable.

Costs and constraints:

- the repo now owns framework-specific code and must track hook and transcript
  format changes;
- adapter rules must stay in step with the router and shared policy, so a
  change to either needs an adapter check;
- a mis-triggered hold can block legitimate work. Justified skips, user
  overrides, and uninstalling are the escape routes.
