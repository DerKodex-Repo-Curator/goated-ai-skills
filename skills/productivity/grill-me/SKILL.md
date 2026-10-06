---
name: grill-me
description: Use when the user wants to be grilled, challenged, interviewed, or walked through a non-docs-grounded idea, topic, plan, choice, or decision.
metadata:
  goated-category: productivity
---

# Grill Me

## Purpose

Clarify a user-supplied topic through proportionate challenge, focused
questions, provisional recommendations, and explicit tradeoffs.

Use this skill for general productivity conversations: brainstorming, exploring a question, sharpening an idea, pressure-testing a lightweight plan, or walking through a decision. The grill should expose assumptions, force crisp tradeoffs, and help the user decide the next move without pretending to know project facts.

Use `grill-with-docs` instead when engineering/project context matters, including target-project docs, domain language, standards, ADRs, code behavior, tests, schemas, or other source evidence.

## Inputs

- User's topic, idea, question, notes, lightweight plan, or decision, with the conversation context and excerpts they want treated as in scope.
- Constraints the user states directly, such as audience, deadline, appetite for risk, budget, or preferred tone.

## Dependencies

Hard: None.

Soft:
- grill-with-docs when project context, docs, standards, ADRs, code, tests, schemas, or source evidence matter
- write-a-spec when the clarified topic should become a scoped spec
- prototype when a specific unknown needs a disposable experiment
- writing-plans when the clarified topic is ready for implementation planning

Fallback: If companion skills are unavailable, continue the lightweight interview and label unsourced assumptions.

## Workflow

1. Route the grill:
   - Use `grill-me` when the needed context is the conversation, user-provided notes, and general reasoning.
   - Use `grill-with-docs` when project artifacts or engineering reality matter, including target-project docs, domain language, documented standards, ADRs, code behavior, tests, schemas, or source-grounded implementation facts.
   - If the topic starts general but a question depends on project reality, pause and recommend `grill-with-docs` rather than guessing.
   - If the user explicitly wants to proceed without project discovery, continue but label project-specific claims as assumptions.

2. Select the clarification mode and budget:
   - Honor an explicit user choice; otherwise recommend the least intensive mode that can resolve the material decisions:
     - **focused**: the single highest-risk open decision;
     - **rapid**: one round of no more than three tightly related questions;
     - **recommend-and-proceed**: provisional defaults for reversible, low-risk choices;
     - **deep-dive**: frontier rounds with no preset question limit for fuzzy products, major choices, or decision-complete exploration.
   - Outside deep-dive, derive a soft question budget from workflow intensity: normally one for `lightweight`, up to three for `standard`, and up to five for `full`. Use fewer when conversation evidence or safe defaults already settle the topic.
   - If the remaining decisions exceed the soft budget, summarize progress and ask whether to continue, change mode, defer them, or proceed with named ambiguity.
   - Recommend-and-proceed must stop for explicit human input on irreversible, destructive, security-sensitive, privacy-sensitive, externally binding, or otherwise high-risk decisions.

3. Establish the first framing:
   - Restate the topic and central question in one sentence.
   - Identify the broad interview shape: desired outcome, audience or beneficiary, assumptions, options, constraints, tradeoffs, success criteria, risks, and next move.
   - Note which decisions depend on which, so upstream decisions come first.

4. Ask in frontier rounds:
   - The frontier is every open decision whose prerequisites are already settled. In deep-dive mode, ask the whole frontier as one numbered round, wait for the answers, then recompute the frontier and ask the next round. Rapid mode asks one round within its limit. Focused mode asks only the highest-risk frontier decision.
   - A question whose answer depends on another question still open in the same round belongs to a later round.
   - Include a recommended default in every question.
   - Explain the key tradeoff behind the recommendation without inventing undiscovered project facts.
   - Prefer choices, boundaries, priorities, scenarios, and definitions over vague "tell me more" prompts.
   - When the user uses a fuzzy term, propose a precise meaning and ask them to confirm or correct it.
   - In recommend-and-proceed, label reversible low-risk defaults as provisional rather than confirmed user decisions, then continue within the user's scope.

5. Pressure-test the topic in dependency order:
   - Use concrete scenarios to test assumptions, edge cases, failure states, audience fit, timing, reversibility, opportunity cost, and success measures.
   - Challenge contradictions in the user's stated goals, constraints, preferences, or answers.
   - For brainstorming, keep narrowing options until the user has a stronger direction or a clear reason to keep exploring.

6. Keep a running brief:
   - Track the clarified topic, central question, assumptions, unresolved questions, recommended next action, and decisions separated into `settled`, `provisional`, `deferred`, and `conflicting`.
   - In deep-dive mode, summarize those four decision states after each coherent decision cluster, when the tree changes materially, or before context becomes hard to retain.
   - Separate confirmed user decisions from agent recommendations.
   - Keep assumptions explicit when they are based only on conversation context.
   - Keep the brief in the conversation; write docs, specs, tickets, prototypes, or implementation files only when the user asks for that next step.

7. Route prototypes only for decision evidence:
   - Recommend `prototype` only when a disposable experiment would distinguish live options more reliably than further discussion.
   - State one decision question and the evidence the prototype must return. Do not frame it as production work or use it to answer a human-only decision.
   - Skip prototyping when conversation evidence already settles the choice.

8. Stop at shared understanding:
   - Stop when the frontier is empty and the topic is resolved enough for the next action, or when a remaining blocker needs another stakeholder, more reflection, or project evidence.
   - When a remaining decision belongs to someone outside the conversation, read [Stakeholder Questionnaire](references/stakeholder-questionnaire.md) and offer to draft one.
   - Recommend the next direct action or companion skill, such as continuing the brainstorm, making a choice, `write-a-spec`, `prototype`, `spec-to-tickets`, `writing-plans`, implementing directly when tiny and clear, or switching to `grill-with-docs`.
   - If the user chooses to proceed with known ambiguity, name the residual risk clearly.

## Output Contract

During the grill, follow the selected mode and label provisional recommendations. Each question in a round uses this shape, numbered when the round has more than one:

```markdown
Q<n>. <one focused decision question>
Recommended default: <one sentence>.
Tradeoff: <why this default is useful, and what it costs>.
```

In integrated use, update the shared envelope with the mode, question budget, settled/provisional/deferred/conflicting decisions, remaining questions, prototype verdict or route signal, and next action. Do not emit a second full task closeout. Standalone use returns this compact working brief:

```markdown
## Clarified Topic

- Topic: <one sentence>
- Central question or goal: <one sentence>
- Success criteria: <observable outcomes>
- Constraints: <known constraints or "none stated">
- Non-goals: <excluded areas>

## Key Tradeoffs

| Tradeoff | Recommendation | Cost |
| --- | --- | --- |

## Decisions

| Decision | State | Outcome | Rationale or tradeoff |
| --- | --- | --- | --- |

## Assumptions

- <assumption confirmed by the user, provisionally accepted, or explicitly still uncertain>

## Unresolved Questions

| Question | Owner | Needed before |
| --- | --- | --- |

## Recommended Next Action

- <direct next step or companion skill>
```

If `grill-with-docs` is the better fit, say why and name the artifacts or project facts that would change the quality of the answer.

## Delegation

Main owns the interview, decision ordering, recommendations, and final synthesis. Delegate only bounded non-project-fact work: alternate decision-tree branches, hypothetical stress tests, comparison of user-provided options, or summaries of provided excerpts. Require inputs inspected, assumptions, tradeoffs, and candidate questions rather than conclusions; without delegation, reason sequentially. Project docs, code, tests, standards, and ADRs belong to `grill-with-docs`.

## Guardrails

- Put in one round only decisions that do not depend on each other's answers.
- Label project-specific claims as assumptions; switch to `grill-with-docs` when project artifacts, source evidence, or target-project terminology would change the answer.
- Confirm agent recommendations with the user or label them as recommendations; they are not user decisions.
- Keep lightweight alignment lightweight: a spec, ticket breakdown, prototype, or implementation session starts only when the user asks for it.
- Prefer concrete scenarios, observable success criteria, and named tradeoffs over abstract brainstorming.

## References

- [Stakeholder Questionnaire](references/stakeholder-questionnaire.md) - read when a remaining decision belongs to someone outside the conversation.
