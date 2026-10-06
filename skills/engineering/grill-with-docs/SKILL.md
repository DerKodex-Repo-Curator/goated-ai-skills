---
name: grill-with-docs
description: Use when important target-project work needs docs-grounded clarification, pressure testing, success criteria, or scope decisions before implementation.
metadata:
  goated-category: engineering
---

# Grill With Docs

## Purpose

Clarify important work by challenging the user's intent against the target project's documented language, standards, ADRs, code behavior, tests, and available facts.

Use this skill before costly or ambiguous work so the agent and user reach shared understanding before implementation. The goal is not to interrogate every request; it is to find the decisions that would otherwise become rework.

## Inputs

- User request, plan, draft spec, architecture idea, ticket or remote issue, or feature description, and the target-project root.
- Project context docs, `docs/agents/context-matrix.md`, `docs/agents/project-standards.md`, ADRs, specs, tickets, contributor docs, and agent instructions when present.
- Source files, tests, schemas, commands, or runtime behavior that can answer factual questions.
- User constraints, preferences, deadlines, risk tolerance, and intended audience when not discoverable from project files.

## Dependencies

Hard: None.

Soft:
- project-context-calibration when language, boundaries, or architecture vocabulary need broader curation than one settled term
- project-standards-calibration when standards or enforcement need durable capture
- prototype when a disposable experiment would settle a live decision
- doc-sync when settled decisions require documentation follow-up after the grill
- verification-before-completion before complete, checked, or implementation-ready claims

Fallback: If docs or companion skills are unavailable, inspect minimal evidence and state lower confidence before asking questions.

## Workflow

1. Decide whether clarification is needed:
   - Use this gate when unresolved intent, scope, success criteria, tradeoffs, or project-language conflicts materially block safe progress.
   - Do not activate it solely because work is cross-file, public-facing, part of onboarding, or described by a spec or legacy PRD.
   - Skip it when current evidence and accepted intent already make the next action safe and clear. Routine skips stay internal unless explaining one helps the user.

2. Gather project facts first:
   - If a context matrix exists, use it to pick the first project sources to read.
   - Read standards, ADRs, glossary/context docs, relevant specs, issue files, and nearby source or tests only as needed.
   - If project language, glossary/context docs, `CONTEXT.md`, `CONTEXT-MAP.md`, ownership, boundaries, or cross-context meaning affects the grill, read [references/context-docs.md](references/context-docs.md).
   - If a settled decision may be costly to reverse, surprising without context, and tradeoff-driven, read [references/adr-capture.md](references/adr-capture.md) before recommending ADR capture.
   - Inspect code, docs, tests, config, or command definitions before asking anything they can answer.
   - Stop gathering when the remaining uncertainty is a decision, tradeoff, preference, or missing product intent.

3. Select the clarification mode and budget:
   - Honor an explicit user choice; otherwise recommend the least intensive mode that can resolve the material decisions:
     - **focused**: the single highest-risk open decision;
     - **rapid**: one round of no more than three tightly related questions;
     - **recommend-and-proceed**: state provisional defaults and continue for reversible, low-risk choices;
     - **deep-dive**: frontier rounds through the material decision tree, without a preset question limit, for major architecture, fuzzy products, or decision-complete work.
   - Outside deep-dive, derive a soft question budget from workflow intensity: normally one for `lightweight`, up to three for `standard`, and up to five for `full`. Use fewer questions when evidence or safe defaults settle the work.
   - If the remaining decisions do not fit the budget, summarize progress and ask whether to continue, change mode, defer them, or proceed with named ambiguity.
   - In recommend-and-proceed, never default an irreversible, destructive, security-sensitive, privacy-sensitive, externally binding, or otherwise high-risk decision. Stop for an explicit human choice.

4. Identify the decision tree:
   - Restate the likely goal and why the work matters.
   - List the decision branches that materially affect design, scope, behavior, testing, docs, migration, rollout, or user experience.
   - Include scenario probes when they would clarify lifecycle, ownership, identity, cardinality, partial vs whole operations, failure states, or cross-context effects.
   - Note which decisions depend on which, so upstream decisions are resolved before dependent details.

5. Ask in frontier rounds:
   - The frontier is every open decision whose prerequisites are already settled. In deep-dive mode, ask the whole frontier as one numbered round, wait for the answers, then recompute the frontier and ask the next round. Rapid mode asks one round within its limit. Focused mode asks only the highest-risk frontier decision.
   - A question whose answer depends on another question still open in the same round belongs to a later round.
   - A lookup still in progress blocks only the questions that depend on it; ask the rest of the frontier now.
   - Include a recommended default and the evidence or rationale behind it in every decision-shaping question.
   - When the user uses vague or overloaded terms, propose a precise term and ask them to confirm or correct it.
   - In recommend-and-proceed, record reversible low-risk defaults as provisional rather than confirmed user decisions, then continue within the approved scope.

6. Challenge against docs and project reality:
   - Compare user statements with documented standards, ADRs, glossary/context language, source behavior, tests, and known constraints.
   - Surface contradictions directly and ask which source should win.
   - Use concrete scenarios and edge cases to test boundaries between concepts.
   - Call out when a decision would conflict with existing standards, may qualify for ADR capture, or need follow-up documentation.

7. Capture decisions as they settle:
   - Keep a running summary of clarified goal, success criteria, scope, non-goals, assumptions, and decisions separated into `settled`, `provisional`, `deferred`, and `conflicting`.
   - In deep-dive mode, summarize those four decision states after each coherent decision cluster, when the tree changes materially, or before context becomes hard to retain.
   - Note which project sources support or contradict each decision.
   - When one project term or ADR-worthy decision settles and current consent covers the project write, record that single delta at once in the place the project already keeps it, using the formats in the two references above. Without covering consent, or when the project has no such place, list it as a candidate durable update instead.
   - Keep each write to one term or one decision. Route broader context curation to `project-context-calibration` and standards or enforcement updates to `project-standards-calibration`.
   - List remaining candidate durable updates for context docs, ADRs, standards docs, specs, or doc-sync follow-up.

8. Route prototypes only for decision evidence:
   - Route to `prototype` only when running, clicking, toggling, or inspecting a disposable experiment would distinguish live options more reliably than further discussion or existing evidence.
   - State one decision question and the evidence needed from the prototype. Do not frame the prototype as production implementation or use it to postpone a required human decision.

9. Stop at shared understanding:
   - Stop when the frontier is empty and implementation can begin safely, the next skill should take over, or a blocker needs user or stakeholder input.
   - When a remaining decision belongs to someone outside the session, read [Stakeholder Questionnaire](references/stakeholder-questionnaire.md) and offer to draft one.
   - Recommend the next direct action or skill, such as `prototype`, `write-a-spec`, `design-codebase-architecture`, `writing-plans`, `tdd`, or `doc-sync`.
   - Use `verification-before-completion` before claiming the brief is complete, checked, or ready for implementation.
   - If the user decides to proceed with known ambiguity, name the risk clearly.

## Output Contract

During the grill, follow the selected mode, number the questions in each round, and label provisional recommendations. In integrated use, update the shared envelope with the mode, question budget, settled/provisional/deferred/conflicting decisions, remaining questions, evidence, prototype verdict or route signal, and next action. Do not emit a second full task closeout. Standalone use returns this compact working brief:

```markdown
## Clarified Work

- Goal: <one sentence>
- Success criteria: <observable outcomes>
- Scope: <included areas>
- Non-goals: <excluded areas>
- Affected sources: <docs, code, tests, ADRs, standards, or "not yet verified">

## Decisions

| Decision | State | Outcome | Evidence or rationale |
| --- | --- | --- | --- |

## Assumptions

- <confirmed or still-active assumption>

## Remaining Questions

- <question, owner, and when it must be answered>

## Candidate Durable Updates

- Include candidates such as context docs, ADRs, standards docs, specs, or doc-sync follow-up, and mark any delta already written; if none, say `None`.

| Artifact or workflow | Candidate update | Evidence or rationale | Recommended owner or next skill |
| --- | --- | --- | --- |

## Next Step

- <recommended direct action or next skill>
```

## Delegation

Main owns the interview, decision order, recommendations, and stop point.
Delegate only bounded source discovery, contradiction checks, or terminology
collection. Require paths, commands, evidence, assumptions, and candidate
questions or contradictions, not conclusions. Without delegation, gather
evidence sequentially.

## Guardrails

- Put in one round only decisions that do not depend on each other's answers.
- Label undocumented guesses as assumptions, not project facts.
- Write durable docs only as the single settled term or decision that current consent covers; anything broader stays a candidate update.
- Use the project's existing context and decision conventions. None of `CONTEXT.md`, `CONTEXT-MAP.md`, or an ADR directory is required.
- Keep private notes, credentials, and client data out of tracked outputs.
- Prefer concrete scenarios, observable success criteria, and named tradeoffs over abstract brainstorming.

## References

Linked support files, read at the workflow gates above: [references/context-docs.md](references/context-docs.md), [references/adr-capture.md](references/adr-capture.md), and [Stakeholder Questionnaire](references/stakeholder-questionnaire.md).
