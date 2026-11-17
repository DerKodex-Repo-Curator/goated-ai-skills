---
name: retrospective
description: Use when the user asks for a retrospective on an agent work session, after a wave of delegated tickets is merged, or when recurring agent mistakes or friction should become improvements to the project's checks, standards, or instructions.
metadata:
  goated-category: agent-workflows
---

# Retrospective

## Purpose

Review a work session and propose changes to the agent's environment so the
same mistake or friction does not recur. The subject is the environment, not
the code that was written: checks, standards, instruction files, navigation
aids, tooling, and access to information.

This skill proposes. It makes no project change itself.

An installed enforcement adapter may suggest it once per session, at the
prompt after three holds were declined by a skip line or left unanswered:
neither obeyed nor stood down by the user before their next prompt.

## Inputs

- The session to review: the current conversation by default, or a session, log, or transcript the user names.
- What went wrong or was slow: corrections from the user, failed checks, rework, long searches, expensive tool calls.
- The project's check commands, CI configuration, standards profile, and agent instruction files.
- Review findings or feedback from the same work, when available.
- Usage numbers from a skill-usage tool, when one recorded the sessions: which holds were followed, declined, or left unanswered, and the skip reasons given.

## Dependencies

Hard: None.

Soft:
- project-standards-calibration when an accepted proposal changes a standard or its enforcement level
- agent-instructions-integrator when an accepted proposal changes an agent instruction file
- learning-capture when the user wants a reusable lesson recorded rather than an environment change

Fallback: Without access to a session record or project checks, work from what
the user reports, label each proposal's evidence as reported rather than
observed, and say what could not be inspected.

## Workflow

1. Establish the evidence:
   - Read the session's primary record: what was asked, what the agent did, and where it was corrected, failed, or stalled.
   - Read the project's existing check commands and CI first. A check that exists but is not wired in, or is silently broken, is the finding; do not propose a duplicate.
   - This step is complete when each candidate below points to a specific moment in the session.

2. Look for candidates in each category:
   - **Navigation:** the agent took long to find a file or missed a hidden dependency between files. Candidate: a short pointer where the agent would look first.
   - **Automated checks:** the agent made a mistake a linter, type check, test, or file-layout check could have caught. A project with no check running before commit or in CI is itself a candidate.
   - **Standards:** review missed something, or a written rule was unclear or wrong. Classify the violation first. A mechanical one, such as a fixed pattern, a banned call, an import shape, or a file location, gets a deterministic check. Keep written standards for judgment calls that no check can make.
   - **Instruction files:** a steering instruction is large, stale, or changes nothing compared with the agent's default. Candidate: move it to a standard or a check, shorten it, or delete it.
   - **Tool economy:** a tool call was expensive, repeated, or returned far more than was needed.
   - **Information access:** something the agent needed was not available to it, such as server logs, a read-only view of an external service, or a test database.

3. Shape each candidate as a proposal:
   - State the observed moment, the proposed change, where it would live, and the cheapest form that would work given the project's language and existing checks.
   - Prefer a deterministic check over a written rule, and a written rule read at review time over an always-loaded instruction. The implementing agent has the most to hold in context; the reviewer has the least.
   - Drop a candidate that rests on a single unlucky moment with no reason to expect it again.

4. Present and route:
   - List proposals in order of severity: how costly the original problem was and how likely it is to recur.
   - Wait for the user to accept, change, or reject each one.
   - Route accepted proposals: standards and enforcement to `project-standards-calibration`, instruction files to `agent-instructions-integrator`, and new checks or tooling to ordinary implementation under the project's normal approval.

## Output Contract

Return the proposals, most severe first:

```markdown
## Retrospective

- Session reviewed: <current conversation, or the named record>
- Evidence basis: <observed in the record | reported by the user>

| # | Category | Observed | Proposed change | Form | Where |
| --- | --- | --- | --- | --- | --- |
| 1 | <category> | <the moment in the session> | <what to change> | <check, standard, pointer, tooling, access> | <file or system> |

## Not Proposed

- <candidate dropped and why, or "None">
```

In integrated use, return the proposals and any route delta to the main agent
rather than a competing task closeout.

## Delegation

Main owns the judgment of what recurs and the ordering by severity. Delegate
only bounded reads of a session record, the project's check configuration, or
one instruction file, and require inspected paths and the specific moments
found. Without delegation, read them sequentially.

## Guardrails

- Propose only; edits to checks, standards, hooks, CI, or instruction files happen through the routed skill or ordinary implementation after the user accepts.
- Tie every proposal to a moment in the session. General best practice with no observed cause is not a finding.
- Recommend the smallest form that prevents the recurrence.
- Keep credentials and private session content out of the proposals; quote only the lines that carry the point.
