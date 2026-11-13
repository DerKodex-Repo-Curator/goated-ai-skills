---
name: writing-plans
description: Use when an approved ticket, scoped task, spec slice, or implementation request needs a just-in-time executable plan before code, docs, or configuration changes.
metadata:
  goated-category: engineering
---

# Writing Plans

## Purpose

Turn approved work into an executable implementation plan immediately before implementation.

Use this skill after intent is scoped enough to act, but before editing. The plan is fresh, source-grounded, and usable by a new agent or engineer without session history. It names exact paths, commands, evidence, stop conditions, and closeout gates only after inspecting the current project.

Issues, PRDs, tickets, and roadmap notes carry stable intent, acceptance criteria, blockers, and source links. Volatile details such as exact file paths, local commands, expected failures, implementation order, and verification evidence belong in a just-in-time plan.

## Inputs

- Approved ticket, spec slice, scoped user request, accepted architecture plan, prototype verdict, or review finding.
- Target-project root path and current working-tree state when available.
- Relevant project docs, local delivery tickets, standards, context artifacts, ADRs, source files, tests, schemas, commands, and previous verification evidence.
- User constraints about plan location, tracked versus local artifacts, implementation route, risk tolerance, subagent use, or required closeout.
- Known unavailable tools, skipped evidence, blockers, or decisions that must not be guessed.

## Dependencies

Hard: None.

Soft:
- grill-with-docs when scope, artifact policy, success criteria, or tradeoffs are unclear
- spec-to-tickets when a scoped spec still needs delivery tickets or a broad target needs slicing
- prototype when risky implementation choices need disposable evidence first
- design-codebase-architecture when module, interface, dependency, or architecture strategy is unsettled
- software-design-principles for module ownership and interface shape
- tdd when implementation changes behavior, public interfaces, or regressions
- subagent-driven-development for larger, riskier, or parallelizable implementation when available
- code-refinement after implementation only for an explicit request or observed refinement debt
- standards-and-spec-review when issue fit, acceptance coverage, or project standards need review
- code-security-review when trust boundaries, auth, user data, persistence, execution, or unsafe config may be affected
- doc-sync when behavior, interfaces, architecture, standards, configuration, tests, or docs may have changed
- verification-before-completion before complete/ready plan, route, or closeout claims

Fallback: If companion skills, docs, commands, subagents, or source evidence are unavailable, inspect minimal evidence, narrow the plan, mark assumptions/residual risk, and avoid unverifiable exact claims.

## Workflow

1. Confirm the planning target:
   - Identify the exact ticket, spec slice, request, or approved artifact being converted into a plan.
   - Confirm it is ready for implementation planning. If the work is not scoped, route to `grill-with-docs`, `write-a-spec`, `spec-to-tickets`, `prototype`, or `design-codebase-architecture` instead of writing an assumption-heavy plan.
   - Check that the target is small enough to implement as one focused vertical slice. If it is broad, narrow the plan to the first user-verifiable tracer bullet and defer the rest, or route back to `spec-to-tickets`.
2. Choose the plan mode:
   - Use **inline** for focused, single-session work. Hold the ordered steps in the work envelope or conversation without creating a tracked artifact.
   - Use **durable** for resumable, delegated, architectural, or multi-surface work. Write a tracked plan using the target project's existing convention; if no convention exists, choose a clear project-local plans or architecture path and state it before writing.
   - Existing project conventions and explicit user artifact instructions win.
   - Keep the only resumable implementation context in a tracked location, not ignored local state.
   - If an inline plan grows into durable work, promote it in place: reuse fresh discovery and evidence, preserve settled decisions and executable steps, and add only the durability context now needed rather than restarting discovery.

3. Inspect before writing exact steps:
   - Read the originating artifact and the smallest useful current source, test, docs, config, or schema evidence.
   - Discover likely edit paths, public interfaces, test surfaces, commands, and documentation surfaces from the project itself.
   - Write exact file paths, commands, snippets, expected failures, expected outputs, and review claims only after this inspection.
   - If multiple plausible paths remain after inspection and the choice changes behavior or risk, ask the user or narrow the plan to the verified path.

4. Pick the execution route:
   - Use **direct execution** for tiny, low-risk, docs-only, mechanical, or obvious changes.
   - Use **`tdd`** for behavior changes, bug fixes, regressions, public interfaces, module seams, or any implementation that should be proven by tests.
   - Use **`subagent-driven-development`** for larger, risky, review-heavy, or parallelizable work when that skill and subagents are available.
   - If `subagent-driven-development` is unavailable, keep the plan single-agent-compatible and split work into sequential checkpoints with review gates.

5. Write executable steps:
   - Name exact files or source areas to inspect or edit, and why each matters.
   - When behavior is involved, start with the smallest end-to-end behavior path that can be proved through a public interface.
   - Avoid layer-by-layer batches such as schema-only, API-only, UI-only, or tests-only work unless they are narrow foundations with a named dependent slice and concrete verification.
   - When module shape matters, name the owning module, public interface, seam, or test surface the plan preserves or improves (`software-design-principles` checklist "Before you start").
   - Name the command or manual check for each meaningful proof step, plus the evidence expected from it.
   - For TDD work, include red, green, refactor, and rerun checkpoints rather than a single bulk test phase.
   - Include conditional closeout steps: `code-refinement` only for an explicit cleanup request or observed debt, standards/spec review and security review when relevant, documentation sync, and final verification.
   - Do not include issue closure, archive moves, completion status edits, or similar lifecycle cleanup unless the plan first satisfies verification and any required review gate for that action.
   - Include stop conditions for missing source evidence, unexpected test results, broad scope drift, unsafe commands, unclear product choices, or repeated verification failures.
   - Keep steps ordered so each one produces evidence needed by the next.
   - End with one justified next-step signal, such as direct execution, `tdd`, or `subagent-driven-development`; do not rebuild the remaining delivery pipeline.

6. Review the plan before execution:
   - Read [Plan Review Checklist](references/plan-review-checklist.md) for non-trivial, risky, delegated, resumable, or durable plans.
   - Check that every acceptance criterion has a planned proof path.
   - Remove placeholders, vague verbs, stale assumptions, and broad "do the rest" language.
   - Make the plan no more detailed than the work needs.

7. Execute or hand off:
   - If the user asked for implementation and the plan is ready, proceed through the chosen route.
   - If the user asked only for a plan, stop after the plan and state assumptions, skipped inspection, and residual risk.
   - If another agent or future session will execute it, include enough source links, current-state evidence, commands, and stop conditions to avoid depending on hidden chat history.

## Output Contract

For most work, return a compact plan shaped like this:

```markdown
## Implementation Plan

- Plan target: <ticket, spec slice, or request>
- Plan mode and location: <inline in envelope/conversation | durable tracked path>
- Source inspected: <paths, commands, docs, tests, schemas, and skipped evidence if any>
- Execution route: <direct execution | tdd | subagent-driven-development | sequential fallback>
- Slice shape: <smallest vertical behavior path | narrow foundation with rationale | not vertical because...>
- Module/interface focus: <public interface, deep module, seam, test surface, or "not architecture-relevant">
- Assumptions: <verified assumptions or "None">
- Stop conditions: <conditions that should pause execution>

### Steps

1. <Inspect/edit/run step with exact path or command and expected evidence>
2. <Next step>
3. <Review/doc-sync/verification closeout step>

### Residual Risk

- <skipped evidence, unavailable commands, unclear product choices, or "Low">
```

For tiny tasks, a shorter inline checklist is enough if it names the target, route, evidence, and closeout.

For durable plan files, write the same sections to the file and summarize the plan location, route, assumptions, and next-step signal in chat.

## Delegation

Main owns the target, artifact policy, route, final plan, and communication.
Delegate only bounded path/test/command discovery, acceptance coverage,
placeholder and safety review, closeout-surface discovery, or route
stress-testing. Delegates return inspected and skipped evidence, assumptions,
risk, confidence, status, and recommended changes; resolve concerns or missing
context before execution, narrow, clarify, or stop on `BLOCKED`, and review
sequentially without delegation.

## Guardrails

- Plan broad setup, scaffolding, or multi-behavior milestones only as a narrow foundation that is required, named, and verifiable.
- Prefer a deeper module, smaller public interface, or clearer test surface over shallow pass-through abstractions.
- Write every step as a concrete action; `TODO`, "handle edge cases", "write tests", "etc.", "similar to above", and "finish implementation" are placeholders, not steps.
- Plan `tdd` for behavior changes even when the edit looks small.
- When routing to subagents, the main agent keeps ownership of integration, review, and final claims.
- Do not prescribe branch, worktree, commit, PR, issue tracker, or agent-tool mechanics unless the target project or user request provides them.
- Keep credentials, private notes, and real user or client data out of tracked plans.

## References

Linked support file, read at the workflow gate above: [Plan Review Checklist](references/plan-review-checklist.md).
