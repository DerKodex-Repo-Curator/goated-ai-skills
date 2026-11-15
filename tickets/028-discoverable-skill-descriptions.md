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

## Draft Closeout (Pending Maintainer Approval)

Status: implemented on 2026-11-15; awaiting the maintainer's approval of the
wording before the ticket closes. Only `description` frontmatter changed. No
skill body, frontmatter field, router map, route line, or shared policy was
touched, and no fixture under `stack/fixtures/` pins description text.

### Reviewed And Kept User-Requested Only

- `caveman`: a reply-style preference that only the user can choose.
- `grill-me`: an interview the user opts into; agent-side clarification
  belongs to `grill-with-docs`.
- `goated-prompt`: prompt crafting is a user deliverable; briefs for agents a
  session starts belong to `handoff`'s spawn-brief mode.
- `retrospective`: user-initiated reflection on a session; agent-started
  retrospectives would add process nobody asked for.
- `learning-capture`: writes to the user's knowledge notes, which should not
  happen unprompted; documentation drift is `doc-sync`'s job.
- `architecture-design-map`: the map is a requested deliverable; agent-side
  orientation belongs to `session-start-progressive-disclosure`.
- `code-refinement`: unchanged because it already names an agent-side symptom
  (refinement debt observed in a recent change).

The remaining descriptions already name agent-side moments or symptoms in
ordinary vocabulary and were left unchanged.

### Points For The Maintainer To Confirm

- `commit-message` and `pr-description` now fire before every agent commit and
  every PR or MR, not only on user request.
- `using-goated-ai-skills` now fires at the start of each new task before the
  first edit or command. Only its description line changed; its body, gate
  map, and route line stay with Ticket 029.
- `standards-and-spec-review` now names "large or risky enough to review
  before it lands" as its agent-side moment.

### Before And After

| Skill | Before | After |
| --- | --- | --- |
| `commit-message` | Use when the user asks to draft or revise a Git commit message. | Use before any Git commit, whether the user asked for it or the agent is committing its own work, and when the user asks to draft or revise a commit message. |
| `pr-description` | Use when the user asks to draft or revise a pull request or merge request description. | Use before opening or updating a pull request or merge request, whether the user asked for it or the agent is opening it, and when the user asks to draft or revise a PR or MR description. |
| `using-goated-ai-skills` | Use when an installed GOATED stack should select or revise a proportionate route for delivery, onboarding, source maintenance, installation, durable-knowledge retrieval, prompt work, or a tiny direct task. | Use at the start of each new task before the first edit or command, when it is unclear which installed skill applies, or when scope changes mid-task; selects a proportionate route for delivery, onboarding, maintenance, installation, knowledge retrieval, research, prompt work, or a tiny direct task. |
| `agent-instructions-integrator` | Use when integrating installed GOATED skills into a target project, creating or updating agent instructions, or routing agents to durable project artifacts. | Use when creating or updating a project's agent instruction files such as AGENTS.md or CLAUDE.md, wiring installed skills into a project, or pointing agents to the project's durable docs and artifacts. |
| `context-matrix-map` | Use when onboarding or refreshing a project after discovery shows a durable source-routing or repeated retrieval problem. | Use when agents in a project keep searching for the same sources, read the wrong docs first, or lack a map of which files to load for which kind of task, typically found while onboarding or refreshing a project. |
| `project-context-calibration` | Use when onboarding or refreshing a project after discovery shows durable confusion about project boundaries, vocabulary, or artifact meanings. | Use when project terms, boundaries, or artifact meanings are ambiguous, contested, or used inconsistently, or a context or glossary file is missing or stale, typically found while onboarding or refreshing a project. |
| `project-standards-calibration` | Use when onboarding or refreshing a project after discovery shows a durable standards, convention, enforcement, or preference gap. | Use when a project's coding standards, conventions, commands, or enforcement are undocumented, contradictory, or ignored by agents, typically found while onboarding or refreshing a project. |
| `framework-agnostic-skill-creator` | Use when creating a new GOATED skill from clarified intent or porting, adapting, sanitizing, or publishing an existing skill, command, prompt, workflow, or agent instruction for portable GOATED use. | Use when creating a new skill or SKILL.md from clarified intent, or porting, adapting, sanitizing, or publishing an existing skill, command, prompt, workflow, or agent instruction as a portable, framework-agnostic skill. |
| `wayfinder` | Use when branching uncertainty spans multiple focused sessions, later decisions depend on earlier evidence, and the complete route to a named planning destination cannot yet be specified responsibly. | Use when a planning question is too branching to settle in one session, because it needs several focused sessions, later decisions depend on earlier evidence, and the full route to the planning destination cannot yet be specified responsibly. |
| `verification-before-completion` | Use the full verification controller for complex, high-risk, delegated, multi-surface, or explicitly audited completion claims; narrow work verifies directly from shared policy. | Use before claiming that complex, high-risk, delegated, multi-surface, or explicitly audited work is done, fixed, or passing; narrow work can verify directly without it. |
| `standards-and-spec-review` | Use when diff size, risk, acceptance ambiguity, scope fit, or uncertain project conventions justify a standards and/or spec review. | Use when a change is large or risky enough to review before it lands, its acceptance criteria or scope fit are ambiguous, or project conventions are uncertain enough to justify a standards and/or spec review. |
| `doc-sync` | Use when behavior, interfaces, architecture, standards, configuration, tests, or public docs may have documentation drift. | Use after changing behavior, interfaces, architecture, standards, configuration, or tests, or whenever README, guides, or other docs may have drifted from the code. |
| `grill-with-docs` | Use when important target-project work needs docs-grounded clarification, pressure testing, success criteria, or scope decisions before implementation. | Use before implementing important project work whose intent, success criteria, scope, or tradeoffs are unclear or conflict with the project's docs, and the gaps must be clarified and pressure-tested against those docs. |
| `tdd` | Use when implementing or fixing target-project behavior, changing public interfaces, adding regression coverage, or doing test-first development. | Use when implementing or fixing code behavior, changing public interfaces, adding regression coverage, or doing test-first development. |
| `setup-scribe` | Use when project-dependent installation, environment changes, application or machine settings, manual setup, setup backfill, reproducibility drift, or replay automation would otherwise be lost or become stale. | Use after installing project dependencies or tools, changing environment variables, application or machine settings, or doing manual setup steps that must be recorded to stay reproducible, or when recorded setup has drifted or is ready to automate. |
