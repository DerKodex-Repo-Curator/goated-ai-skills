---
name: review-codebase-architecture
description: Use when reviewing existing source and docs for architecture quality, improvement opportunities, shallow modules, tight coupling, weak seams, or hard-to-test structure without designing or implementing the replacement architecture.
metadata:
  goated-category: engineering
---

# Review Codebase Architecture

## Purpose

Review a target project's existing source and docs to find architecture improvement opportunities before implementation begins. Prefer deeper modules: small, meaningful interfaces that hide real behavior, improve locality, and give callers and tests more leverage.

This skill is review-only. It ranks opportunities, explains tradeoffs, and emits one appropriate next-step signal. It does not prescribe a complete replacement architecture, implement refactors, rewrite code, update tests, or mutate project architecture.

## Inputs

- User request, target-project root, architecture concern, and requested scope.
- Project context docs, context matrix, standards profile, architecture map, ADRs, specs, and tickets when present.
- Source, manifests, entrypoints, dependency construction, adapters, tests, fixtures, and test commands related to the review scope.
- Commit history, prior refactor notes, recorded rejections, known pain points, flaky areas, or user examples of hard-to-change code.

## Dependencies

Hard: None.

Soft:
- architecture-design-map when a descriptive current-state map is needed before ranking improvements
- design-codebase-architecture when an accepted finding needs prescriptive design
- software-design-principles for red-flag names and the reasoning behind a finding
- code-refinement when a candidate is only scoped behavior-preserving cleanup
- tdd when a selected improvement moves into implementation and test design
- write-a-spec or spec-to-tickets when a chosen direction needs planning or delivery slices
- verification-before-completion before complete, evidence-backed, or downstream-ready claims

Fallback: If companion skills or durable docs are unavailable, inspect minimal project evidence, keep confidence lower, and separate facts from assumptions.
## Architecture Language

Use target-project names for concrete modules and flows. Keep these review terms hot-path:

- **Module / interface / implementation**: compare caller/test knowledge with behavior hidden behind the module.
- **Depth, leverage, locality**: judge whether a smaller interface gives more capability and concentrates change and proof.
- **Deep vs shallow module**: reward cohesive hidden behavior; flag pass-through modules that leak caller choreography.
- **Deletion test**: if removing the module makes complexity reappear across callers, it likely earns its place.
- **Port**: project-shaped interface at a real seam; require production/test/local variation before recommending it.
- **False seam / adapter**: flag indirection when behavior does not really vary or callers still know internals.
- **Interface-as-test-surface**: prefer proof through caller-visible behavior; private/mock-heavy tests may expose weak shape.

## Workflow

1. Confirm scope and mode:
   - Identify the target-project root from the request, current directory, repository metadata, or manifests.
   - Classify the work as broad architecture scan, focused subsystem review, testability review, dependency/seam review, or RFC-prep review.
   - For a broad scan with no named direction, scope by recent change first: deepening pays off where the code keeps changing. Read a stretch of commit history, for example `git log --oneline --stat`, start with the areas that recur, and widen only when changes are scattered.
   - Ask only when the target root, review scope, or required output cannot be inferred safely.

2. Gather evidence before judging:
   - Use `docs/agents/context-matrix.md` when present to choose first-read and second-read sources.
   - Read relevant context docs, ADRs, architecture maps, standards, specs or legacy PRDs, tickets or remote issues, manifests, entrypoints, package indexes, imports/callers, representative source, tests, fixtures, and dependency construction code.
   - Trace actual calls, imports, data flow, configuration, routes, job wiring, or test setup instead of relying on folder names alone.
   - Check recorded rejections first: ADRs, out-of-scope records, or earlier review notes that already declined a direction. Raise such a direction again only when the friction is strong enough to reopen the decision, and say that it reopens it.
   - Record commands run, commands skipped, missing evidence, stale docs, inferred relationships, and contradictions.

3. Find candidate architecture friction:
   - Look for shallow pass-through modules, thin layers, wrappers that mostly forward calls, and modules that fail the deletion test.
   - Look for tightly coupled concepts, behavior split across callers, repeated caller choreography, primitive clusters, and modules that require many public calls to prove one behavior.
   - Look for information leakage, where one design decision is known in several modules, and temporal decomposition, where modules mirror execution order (`complexity-and-modules.md#information-hiding` in `software-design-principles`).
   - Look for hard-to-test areas: noisy setup, internal patching, private-state assertions, call-order tests, dependency construction hidden too deep, or tests coupled to implementation details.
   - Look for false seams: ports/adapters with only one real implementation, interfaces added only for tests, or seams that leak internal ordering and configuration back to callers.
   - Look for dependency shapes that block deepening: in-process logic, local-substitutable dependencies, remote-owned services, and true external services.
   - Read [Deepening Interface Patterns](references/deepening-interface-patterns.md) when using review vocabulary, classifying dependency/seam shape, moving tests to an interface, comparing alternatives, or applying report tags.

4. Rank opportunities:
   - Prefer candidates with strong source evidence, repeated pain across callers/tests, meaningful public-interface leverage, and a small next slice.
   - Separate high-confidence opportunities from speculative ideas, taste preferences, broad rewrites, and candidates blocked by missing evidence.
   - Include rejected or deferred candidates when they looked plausible but failed the evidence, deletion, locality, seam, or test-surface checks.

5. Sketch deepening directions without implementing:
   - Describe what behavior should move behind a smaller interface, what callers/tests would stop needing to know, and which dependencies should remain internal or become ports.
   - For strong candidates, optionally compare interface alternatives: minimal, flexible, caller-optimized, and ports/adapters designs.
   - Recommend an RFC-style handoff when the candidate crosses public interfaces, data ownership, service/package boundaries, deployment topology, security posture, multi-team ownership, migration/deprecation strategy, or multiple viable interface designs.

6. Report and route the next step:
   - Return the ranked review inline unless the user requested a durable artifact.
   - Recommend `architecture-design-map` when a current-state map is missing and would reduce uncertainty.
   - Recommend `design-codebase-architecture` when an accepted finding needs prescriptive module, interface, ownership, data-flow, dependency, or migration design.
   - Recommend `code-refinement` when a plausible architecture concern turns out to be scoped behavior-preserving cleanup.
   - Recommend `write-a-spec`, `spec-to-tickets`, or an RFC when the chosen direction needs planning before implementation.
   - Recommend `tdd` when the next step is a focused implementation slice with behavior proof through the new or existing interface.
   - Emit only the next signal justified by the selected finding.
   - When the user rejects a candidate for a reason a future review would need, offer to record it in the project's decision convention so it is not suggested again.
   - Use `verification-before-completion` before claiming the ranking is complete, evidence-backed, or ready for downstream work; for lightweight scans, verify only the recommendation claim being made and state skipped areas.

## Output Contract

Return a compact review shaped like this:

```markdown
## Review Scope

- Mode: <broad scan, focused subsystem, testability, dependency/seam, or RFC-prep>
- Target root: <path or inferred project>
- Evidence inspected: <files, docs, commands, tests, assumptions>
- Commands run or skipped: <commands and reasons>

## Ranked Opportunities

1. <opportunity title> - <Strong, Worth exploring, or Speculative>
   - Source evidence: <paths, callers, tests, commands, docs>
   - Current friction: <what callers/tests/maintainers must know today>
   - Dependency/seam shape: <in-process, local-substitutable, remote-owned, true external, false seam, or unknown>
   - Deepening direction: <what behavior/interface should change at a high level>
   - Tradeoffs: <costs, migration risk, compatibility, test impact>
   - Confidence: <high, medium, or low with reason>
   - Suggested next slice: <small review, prototype, TDD slice, spec/ticket, or RFC>
   - RFC trigger: <none or reason>

## Cross-Cutting Themes

- <repeated architecture pattern, dependency issue, or test-surface issue>

## Deferred Or Rejected Candidates

- <candidate and why it was not recommended now>

## Assumptions And Skipped Areas

- <missing evidence, skipped commands, stale docs, or unresolved scope>

## Recommended Next Step

- <one recommended route>
```

For an RFC-style handoff, include the chosen problem, source evidence, public interfaces affected, viable interface designs, migration/deprecation concerns, test strategy, open decisions, and the smallest reversible next slice.

## Delegation

Main owns scope, evidence standards, ranking, and recommendations. Delegate
only bounded caller or test traces, one-area friction scans, seam checks, or
one interface alternative. Require paths, commands, evidence, candidate
friction and seam shape, assumptions, and status, not a recommendation;
resolve concerns before ranking, and narrow or stop on `BLOCKED`. Without
delegation, explore sequentially.

## Guardrails

- This skill reviews only. Route accepted design work to `design-codebase-architecture`; leave production code, tests, formatters, and migrations untouched.
- Rank only findings backed by target-project evidence. Speculative rewrites, taste, folder-layout impressions, and ecosystem habits are not findings.
- Judge shallowness by interface complexity, caller knowledge, the deletion test, and hidden behavior, not by size.
- Recommend a port, adapter, or seam only where behavior genuinely varies across it or the dependency category justifies it.
- In a proposed direction, replace implementation-detail tests only when equivalent interface-level coverage exists.
- Mark inferred, stale, missing, weak, or conflicting evidence clearly.
- Create durable artifacts, ADRs, specs, or tickets only when the user separately asks for them.

## References

Linked support file, read at the workflow gate above: [Deepening Interface Patterns](references/deepening-interface-patterns.md).
