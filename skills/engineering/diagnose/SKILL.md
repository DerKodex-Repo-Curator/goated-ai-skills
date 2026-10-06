---
name: diagnose
description: Use when investigating bugs, failing behavior, flaky tests, build failures, integration failures, performance regressions, or unexpected behavior before proposing or implementing fixes.
metadata:
  goated-category: engineering
---

# Diagnose

## Purpose

Find and prove the cause of a bug, flaky failure, build or integration break, production symptom, or performance regression before fixing it.

Diagnosis ends with evidence and a routed next action; it does not own the fix
cycle. When the user already requested a fix and the cause and correct
public-interface seam are known, continue directly into `tdd`. Ask again only
when the fix would materially change the agreed scope, action reach, risk, or
public contract. When no correct seam exists or repeated fixes keep failing,
route the architecture problem to `review-codebase-architecture`.

## Inputs

- The reported symptom and its evidence: report, failing test, error output, logs, traces, metrics, profiles, or reproduction steps.
- Target-project root, recent changes, configuration, dependency versions, environment facts, and affected entrypoints.
- Safety constraints: production access, user data, destructive repro risk, secret handling, and time limits.
- Available proof tools: tests, commands, scripts, browser automation, fixtures, profilers, query plans, log search, bisection, or human-in-the-loop checks.

## Dependencies

Hard: None.

Soft:
- tdd when the cause is proven and a public-interface seam can carry the regression test
- review-codebase-architecture when no correct seam exists or repeated fixes fail
- code-security-review when the symptom touches a trust boundary or sensitive data
- doc-sync when the diagnosis changes docs or runbooks
- verification-before-completion before proven-cause or implementation-ready claims
- handoff when an unfinished diagnosis needs continuity

Fallback: If companion skills, docs, commands, profilers, production access, or subagents are unavailable, build/request the smallest safe feedback loop, state missing evidence, downgrade claims, and report residual risk.

## Workflow

1. Triage scope and safety:
   - Classify the symptom: functional bug, flaky or timing failure, performance regression, build failure, integration failure, production symptom, or unknown.
   - Identify the blast radius, data sensitivity, environment, urgency, and whether reproduction or instrumentation could be destructive.
   - Ask only for non-discoverable facts that materially change diagnosis: expected behavior, missing access, unsafe repro approval, or the user's tolerance for risk.

2. Build the fastest honest feedback loop:
   - Before hypothesis testing, establish or request the smallest loop that can show the symptom with enough fidelity.
   - Prefer a focused failing test, exact command, CLI fixture, HTTP request script, browser path, captured trace replay, benchmark, profiler run, query plan, differential comparison, bisection, or human-in-the-loop loop.
   - Tighten the loop before continuing: narrow it until it runs in seconds, assert the exact symptom rather than "did not crash", and pin time, randomness, and external state where they vary.
   - For an intermittent symptom, raise the reproduction rate until it is debuggable: repeat the trigger, run it in parallel, add load, or narrow the timing window. Record the rate reached.
   - This step is complete when you can name one command or script you have already run that goes red on this symptom, gives the same verdict each run (or a recorded reproduction rate), finishes quickly, and needs no human. Show the invocation and its redacted output.
   - If no such loop is safe or available, stop before hypothesis testing, list what you tried, request the missing loop or access, and limit any artifact-only diagnosis to explicitly lower-confidence triage.
   - Capture the loop as evidence: command or steps, inputs, environment, observed result, timing, and whether the result is deterministic or intermittent.

3. Confirm the exact symptom:
   - Reproduce the reported failure or verify the provided artifact. Match the user-visible symptom, error, timing, environment, and frequency.
   - If the local symptom differs from the report, diagnose the mismatch first instead of drifting into a different bug.
   - Record expected behavior separately from actual behavior. Treat ambiguous expected behavior as a product or user decision, not a debugging fact.

4. Minimize the confirmed reproduction:
   - Keep the fast, red-capable feedback loop from step 2, then minimize its concrete reproduction before broad hypothesis ranking. Do not assume the first loop that confirms the symptom is already irreducible.
   - Remove or simplify one element at a time and re-confirm the exact symptom. Retain only load-bearing inputs, dependencies, steps, timing conditions, and environmental facts.
   - For every retained element, record why removing it loses symptom fidelity. If its necessity is still uncertain, keep it and record that residual uncertainty instead of presenting it as proven.
   - Do not minimize through a safety boundary or trade away the symptom's error, timing, environment, or frequency. For intermittent, production-only, destructive, or human-in-the-loop cases, use the smallest safe bounded proxy or retain the confirmed loop, label the result lower-confidence, and record what could not be minimized.

5. Observe before fixing:
   - Read errors, stack traces, logs, recent changes, callers, tests, configs, schemas, dependency wiring, and working examples before proposing a fix.
   - Compare expectations to reality at each relevant interface: inputs, state, side effects, timing, outputs, errors, and invariants.
   - Read [Root-Cause Tracing](references/root-cause-tracing.md) when the bad value, event, state, or timing appears downstream from its origin.
   - Leave production behavior, tests, retries, and guards unchanged during observation.

6. Rank falsifiable hypotheses:
   - List 3-5 plausible causes, ordered by evidence, impact, and cheapest falsifying probe.
   - For each hypothesis, state the prediction that would be true if it were the cause and the smallest probe that can confirm or falsify it.
   - Keep "obvious fix" ideas as hypotheses until evidence proves them.
   - Show the ranked list before probing; the user may re-rank it or rule one out at once. Continue with your ranking if they do not respond.
   - If pressure, fatigue, authority, or sunk cost is pushing a shortcut, read [Pressure Scenarios](references/pressure-scenarios.md).

7. Probe one hypothesis at a time:
   - Add the narrowest instrumentation, command, log, assertion, trace, breakpoint, metric, profile, query plan, or comparison needed for one prediction.
   - Change one variable at a time. After each probe, record the result and update the ranking.
   - Mark every temporary log, flag, or script with one unique tag for this diagnosis, such as `DIAG-a4f2`, so cleanup is a single search.
   - For flaky or async symptoms, read [Condition-Based Waiting](references/condition-based-waiting.md) before changing waits, retries, sleeps, polling, or timeouts.
   - For performance symptoms, measure the baseline first, then use profiling, query plans, benchmarks, bisection, allocation or I/O measurement, or differential traces before proposing optimization.

8. Prove root cause and route the next action:
   - Root cause is proven only when evidence explains the exact symptom and the symptom changes predictably when the cause or triggering condition changes.
   - Build a compact evidence packet: repro loop, key observations, hypotheses rejected, confirming probe, cause, affected interface, and residual uncertainty.
   - If a correct public-interface seam exists, route to `tdd` with the desired regression behavior and suggested first failing test.
   - If the original request already includes the fix, reuse the diagnosis packet and continue.
   - If no correct seam exists, tests would need private internals, or repeated fixes failed, route to `review-codebase-architecture` before implementation; the missing seam is itself a finding.
   - If the diagnosis changes docs or runbooks, route to `doc-sync`. If it touches trust boundaries or sensitive data, route to `code-security-review`.

9. Cleanup and verify closeout:
   - Remove temporary logs, scripts, harnesses, probes, flags, and test-only hooks; search for the diagnosis tag to confirm none remain.
   - State the confirmed cause where the next debugger will find it: the commit message, pull request text, or ticket for the fix.
   - If any diagnostic artifact must remain, document why, who owns it, how it is controlled, and when to remove it.
   - Use `verification-before-completion` before claiming the cause is proven, diagnosis is complete, the fix is ready, or the work is safe to hand to implementation.
   - Report residual risk plainly: unreproduced paths, environment differences, skipped probes, unavailable access, weak measurement, flaky evidence, or unverified assumptions.

## Output Contract

Return a diagnosis packet shaped like this:

```markdown
## Diagnosis Scope

- Symptom: <reported and confirmed symptom>
- Safety constraints: <production, data, destructive repro, secret, or access constraints>
- Feedback loop: <command, test, script, benchmark, trace, manual loop, or missing loop>

## Repro Evidence

- Expected: <expected behavior>
- Actual: <actual behavior>
- Frequency and environment: <deterministic/intermittent, versions, inputs, timing>
- Evidence: <logs, command output, profile, trace, screenshot, metrics, or source reads>

## Minimized Reproduction

- Retained elements: <load-bearing inputs, dependencies, steps, timing, and environment with reasons>
- Residual uncertainty: <elements retained without proven necessity, or none>
- Fidelity and safety: <exact symptom preserved, bounded proxy, or lower-confidence fallback>

## Hypotheses And Probes

| Rank | Hypothesis | Prediction | Probe | Result |
| --- | --- | --- | --- | --- |
| 1 | <cause candidate> | <what would be observed> | <instrumentation or command> | <confirmed/falsified/pending> |

## Root-Cause Result

- Cause: <proven cause, not proven, or still uncertain>
- Proof: <evidence that ties cause to exact symptom>
- Rejected causes: <important falsified hypotheses>
- Performance evidence: <baseline, profile, benchmark, query plan, bisection, or not applicable>
- Cleanup: <removed artifacts or remaining controlled artifacts>
- Routed next action: <tdd, review-codebase-architecture, verification-before-completion, handoff, or user decision>
- Residual risk: <remaining uncertainty>
```

## Delegation

Main owns symptom framing, hypotheses, root-cause judgment, and fix direction.
Delegate only bounded reproduction, one trace or comparison, profiling or
bisection evidence, or cleanup checks. Require paths, commands, evidence,
assumptions, and status; check important evidence before relying on it, and
narrow or stop on `BLOCKED`. Without delegation, run the same probes
sequentially.

## Guardrails

- Prove the cause before fixing; a likely fix stays a hypothesis until a probe confirms it.
- Minimize a confirmed reducible reproduction before ranking hypotheses, unless safety or symptom fidelity requires a recorded lower-confidence fallback.
- Probe and fix in separate steps so each result has one explanation.
- Keep failing tests intact; they are the symptom's evidence.
- Redact secrets, credentials, and private data before sharing or persisting evidence.
- Do not add production instrumentation, enable verbose logs, alter live config, or run destructive repro steps without explicit approval, scope, duration, and rollback.
- Fix flakes with observed readiness conditions or bounded polling, not arbitrary sleeps.

## References

Workflow-gated support files: [Root-Cause Tracing](references/root-cause-tracing.md), [Condition-Based Waiting](references/condition-based-waiting.md), and [Pressure Scenarios](references/pressure-scenarios.md).

- [Defense In Depth](references/defense-in-depth.md) - read after root cause is proven and the likely fix needs layered prevention, containment, detection, or recovery; route implementation through `tdd`.
