# Ticket 028: Discoverable Skill Descriptions

## Parent Spec

`docs/specs/2026-11-15-skill-enforcement-adapter.md` (R1)

## Type

HITL. The maintainer reviews the rewritten descriptions before the ticket
closes, because each one changes when frameworks auto-load a skill.

## What To Build

Rewrite the skill descriptions that agents cannot match on their own:

- descriptions that trigger only when the user asks or explicitly requests;
- descriptions written in stack-internal vocabulary that ordinary prompts
  never contain.

Each rewritten description also names the agent-side moment or symptom when the
skill applies. For example, `commit-message` should apply before any agent
commit, and `pr-description` before any PR is opened. Skills that should stay
user-requested only, such as `caveman` and `grill-me`, keep that wording, and
the decision is recorded in the ticket closeout. This slice helps every
framework, with or without hooks.

## Recommended First Reads

- `skills/README.md` — description rules: discovery only, no workflow steps,
  and no new frontmatter fields.
- The spec's Problem section — the evidence and the list of user-gated
  descriptions.
- `stack/goated-stack.yaml` and `stack/fixtures/`, in case a fixture pins
  description text.

## Acceptance Criteria

- [ ] Every user-gated or stack-vocabulary description has been reviewed:
      rewritten to name an agent-side moment, or deliberately kept user-only
      with a one-line reason.
- [ ] No description gains workflow steps or new frontmatter fields.
- [ ] The validator, the unit tests, and the V1/V2 context comparison pass.
- [ ] The maintainer has approved the wording.

## Expected Proof

- Validator, unit-test, and context-comparison output.
- A before/after table of the changed descriptions for maintainer review.

## Blocked By

- None

## Scope Exclusions

- Skill bodies, the router map, and the route line (Ticket 029).
- Any hook or adapter work.
