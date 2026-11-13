---
name: tdd
description: Use when implementing or fixing target-project behavior, changing public interfaces, adding regression coverage, or doing test-first development.
metadata:
  goated-category: engineering
---

# Test-Driven Development

## Purpose

Use behavior-first TDD to implement target-project changes with proof. The loop is red, green, refactor: write one focused failing test for observable behavior, make the smallest production change that passes it, then improve design only after the tests are green.

Tests verify behavior through public interfaces, not implementation details.

Choose the smallest stable observable boundary that can prove the behavior.
That may be a unit, property, component, contract, integration, or end-to-end
test. Broader is not automatically stronger: integration tests are appropriate
only when the behavior crosses a real integration boundary. A good test reads
like a specification and survives internal replacement; a test that fails
during a harmless refactor is coupled to implementation.

## Inputs

- User request, bug report, delivery ticket, spec slice, prototype verdict, or scoped behavior change, and the target-project root.
- Source, tests, fixtures, commands, and public interfaces related to the behavior.
- Project context docs, ADRs, standards, and test conventions when they affect naming, interface shape, or expected proof.
- Available test commands and known weak or missing test infrastructure.

## Dependencies

Hard: None.

Soft:
- grill-with-docs when behavior, public interface, or testing priority is materially unclear
- software-design-principles for interface and refactor judgement
- code-refinement after green only when explicitly requested or concrete refinement debt is observed
- verification-before-completion before complete, correct, passing, or review-ready claims

Fallback: If companion skills or docs are unavailable, inspect minimal evidence, use discoverable tests/commands, and state lower confidence plus residual risk.

## Workflow

1. Ground the behavior before writing code:
   - Identify the observable behavior that should change or be protected.
   - Identify the public interface that should prove it, such as a module API, CLI command, HTTP endpoint, UI flow, repository method, service boundary, or user-facing workflow.
   - For a new module or public function, settle the interface before the first test (`software-design-principles` `#design-twice`).
   - Identify the first focused failing test that can prove one behavior.
   - Name tests and interfaces in the project's documented domain language.
   - Proceed when the ticket or spec already makes behavior and interface clear, including any proof surface it names. Ask only when behavior, public interface, or test priorities are materially ambiguous.

2. Plan tests as behaviors, not implementation steps:
   - List behavior candidates in priority order.
   - Select the smallest stable observable boundary that can catch the regression or missing behavior.
   - Choose the first tracer bullet: the smallest end-to-end behavior that proves the path works.
   - Prefer critical paths, regression risks, and complex logic over exhaustive edge-case theater.
   - Read [Test Design](references/test-design.md) when test shape, naming, public-interface proof, or good-vs-bad test judgment matters.
   - Read [Mocking And Seams](references/mocking-and-seams.md) before introducing mocks, fakes, ports, dependency injection, or adapter seams.
   - Read [Deep Modules](references/deep-modules.md) when the interface feels wide, setup-heavy, shallow, or awkward to test.
   - Read [Testing Anti-Patterns](references/testing-anti-patterns.md) when tempted to skip RED, write tests after, change tests to match current behavior, over-mock, or claim completion from weak proof.

3. RED: write one focused failing test:
   - Write one test for one observable behavior through the chosen public interface.
   - When a behavior test is feasible, do not implement production behavior until RED evidence exists.
   - Run the smallest useful test command and confirm it fails for the expected reason.
   - If it passes before implementation, the test is not proving the missing behavior; tighten the setup or choose a better behavior.
   - If no feasible behavior test exists, use the infrastructure fallback and do not describe fallback proof as RED evidence.
   - When automated TDD is genuinely unsuitable, record the practical reason in the work envelope, use the strongest equivalent proof available, and state the residual risk.
   - Capture red evidence: command, failing test name, and failure reason.

4. GREEN: implement only enough code to pass:
   - Change production code only for the current failing behavior.
   - Leave future tests, speculative features, and adjacent cleanup for their own cycle.
   - Change a failing test only when RED evidence shows the test is invalid or the requirement changed.
   - Run the focused test until it passes, then run relevant nearby or existing checks that protect the touched area.
   - Capture green evidence in two parts: focused command and passing result first, then broader checks run or skipped.

5. Repeat vertically:
   - One test, one implementation, then the next: add a behavior only after the current test is green.
   - Let each new test respond to what the previous cycle taught you about behavior, interface shape, fixtures, and design friction.
   - Writing all tests first and all implementation second is horizontal slicing. Bulk tests describe imagined behavior and the shape of things, so they pass when behavior breaks and fail when it is fine.
   - Continue until the ticket or request acceptance criteria, or the agreed behavior set, is covered.

6. Refactor after green:
   - Read [Refactor After Green](references/refactor-after-green.md) before non-trivial cleanup.
   - Improve names, duplication, structure, locality, and interface shape only while tests are passing.
   - Leave the change looking designed in, not patched on; prefer deeper modules that hide real complexity (`software-design-principles` `#refactoring`).
   - Keep ordinary local refactoring inside this TDD cycle. Load `code-refinement` only for an explicit cleanup request or observed debt such as confusing names, duplication, excessive branching, shallow indirection, unnecessary abstraction, or difficult local reasoning.
   - Run tests after each meaningful refactor step.

7. Close the loop:
   - Summarize test intent, red evidence, green evidence, refactor notes, and residual risk.
   - Note weak or missing test infrastructure honestly.
   - Recommend follow-up only when it is directly connected to untested behavior, missing infrastructure, or acceptance risk.
   - Pass the TDD evidence packet to `verification-before-completion` before making completion, correctness, passing, or review-ready claims; for drafts, analysis-only work, or fallback proof, verify only the claim being made and report residual risk.

## Output Contract

In integrated use, return only material evidence, change, risk, and route
deltas. Do not repeat the full work envelope or produce a competing final
closeout.

During or after TDD work, report:

- Behavior: the observable behavior or regression protected.
- Public interface: the interface, command, route, component, service, adapter, or workflow used as the test surface.
- Test intent: the focused behavior test added or changed, with why it proves the requirement.
- Red evidence: command, failing test name, and expected failure reason before implementation, or an explicit fallback reason when RED is not feasible.
- Green evidence: focused command and passing result, plus separate broader nearby or existing checks run after implementation.
- Cycle notes: confirmation that work proceeded one vertical slice at a time, or an explicit reason when it could not.
- Refactor notes: cleanup performed after green, interface friction found, deep-module opportunities addressed or deferred, and tests rerun.
- Files changed: production code, tests, fixtures, docs, or config touched.
- Residual risk: skipped checks, weak or missing test infrastructure, uncovered behavior, flaky tests, environment limits, or follow-up needed.

If test infrastructure is weak or missing, report:

```markdown
## TDD Infrastructure Fallback

- Desired behavior proof: <observable behavior and public interface>
- Existing test support found: <tests, commands, fixtures, or "none">
- Smallest useful proof added or used: <test, characterization, harness, manual check, or "none">
- Why a stronger test was not added now: <tooling gap, missing harness, unsafe setup, time/risk, or scope>
- Residual risk: <what remains unproved>
- Recommended next step: <focused test infrastructure follow-up or none>
```

## Delegation

Main owns behavior, public-interface judgment, scope, and implementation.
Delegate only bounded interface or test discovery, coupling review, one owned
slice after red, or disjoint verification. Require paths, changes, commands,
red/green evidence, assumptions, and status; resolve concerns before
continuing, and narrow or stop on `BLOCKED`. Without delegation, run the same
cycle sequentially.

## Guardrails

- Prove behavior through a caller-facing interface. Private helpers, internal collaborators, call counts, storage queries, and log scrapes are not proof when a public interface can show the behavior.
- Mock only true external edges, time, randomness, filesystem, network calls, or dependencies that cannot safely run locally. Introduce a port or adapter only at a real seam where behavior varies across production and test.
- Take expected values from an independent source: a known-good literal, a worked example, or the spec. An assertion that recomputes the value the way the code does cannot fail.
- A test written after the implementation counts as TDD only when you also show it fails against the missing or broken behavior.
- Keep behavior tests as strict as the requirement; replace an implementation-detail test only when new public-interface proof covers the same behavior.
- Keep test-only methods, flags, and hooks out of production code; use test utilities or a real public interface.
- Build broad test infrastructure, fixture frameworks, CI changes, or new dependencies only when the current ticket or request calls for that foundation. When infrastructure is weak, use the smallest honest proof and report residual risk.
- Use synthetic data in tests and fixtures, never credentials or real user data.

## References

Linked support files, read at the workflow gates above: [Test Design](references/test-design.md), [Mocking And Seams](references/mocking-and-seams.md), [Deep Modules](references/deep-modules.md), [Refactor After Green](references/refactor-after-green.md), and [Testing Anti-Patterns](references/testing-anti-patterns.md).
