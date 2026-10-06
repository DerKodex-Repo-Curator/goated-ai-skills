---
name: spec-to-tickets
description: Use when an approved spec or scoped delivery contract should become one or more dependency-aware, fresh-agent-ready local tickets.
metadata:
  goated-category: engineering
---

# Spec To Tickets

## Purpose

Turn an approved spec into portable vertical delivery tickets. A ticket is a
dependency-aware work unit that a fresh agent can start without hidden chat
history. A remote issue is one possible representation of a ticket; this skill
creates local artifacts only.

Keep one coherent vertical slice as one ticket. Create multiple tickets only
when the work has independently verifiable slices, real dependencies, different
approval needs, or useful resumability.

## Inputs

- Approved spec or equivalent scoped delivery contract.
- Existing local ticket convention, numbering, active tickets, and order file.
- Relevant architecture decisions, source links, acceptance criteria,
  constraints, blockers, and scope exclusions.
- Existing work-envelope approval, scope, action reach, and evidence.

## Dependencies

Hard: An approved, slice-ready spec or equivalent durable contract.

Soft:
- `write-a-spec` when intent, acceptance criteria, or blockers are incomplete
- `design-codebase-architecture` when slice boundaries depend on unsettled
  module or interface strategy
- `writing-plans` after a ticket is selected for implementation
- `verification-before-completion` before claiming a ticket set is ready

Fallback: If the contract is not slice-ready, report the exact gaps and route
back to clarification or `write-a-spec`. Do not create assumption-heavy tickets.

## Workflow

1. **Confirm slicing readiness.**
   - Verify the source contract, acceptance criteria, non-goals, constraints,
     decisions, and known blockers.
   - Stop when a missing product or architecture decision would materially
     change ticket boundaries.
   - Reuse current evidence; refresh only stale or too-shallow entries.

2. **Discover the local convention.**
   - Reuse an established ticket directory, numbering, headings, and archive
     policy.
   - Otherwise use `tickets/NNN-<short-title>.md`.
   - For multiple tickets, use `tickets/<spec-slug>-order.md`. Do not create an
     order file for one ticket.

3. **Slice vertically unless a wide refactor qualifies.**
   - Prefer user-, operator-, or maintainer-verifiable outcomes that include
     the implementation and proof needed for that outcome.
   - Avoid layer-only, test-only, docs-only, or broad setup tickets unless they
     are a necessary narrow foundation with a named dependent slice. The main
     case is prefactoring: when a small behavior-preserving change would make
     the slice easy, make it its own first ticket and block the slice on it.
   - Size each ticket for one fresh agent session. If its reads, change, and
     proof would not fit one context window, split it.
   - Keep tightly coupled changes together when splitting them would create
     unusable intermediate states or duplicate coordination.
   - Use `wide-refactor` only when one mechanical change's blast radius
     prevents any green vertical slice; file count alone does not qualify.
     Apply [Ticket Slicing Templates](references/ticket-slicing-templates.md)
     for expand, migrate, contract, and exception rules.
   - Order tickets so every blocker appears before its dependents.

4. **Make every ticket fresh-agent-ready.**
   - Include the parent spec, outcome to build, recommended first reads,
     acceptance criteria, expected proof, blockers, user stories when useful,
     and scope exclusions.
   - Link durable decisions and relevant source areas rather than relying on
     chat or ignored notes. Describe the outcome by behavior and interface so
     the ticket survives file moves; first reads are orientation and may have
     moved.
   - State `AFK` only when no human decision, credential, external access,
     review, or approval gate is required; otherwise use `HITL` and name the
     gate.
   - Exclude exact implementation steps, commands, file inventories, and code
     snippets that belong in a just-in-time `writing-plans` pass.

5. **Apply batch approval correctly.**
   - Present the proposed single ticket or complete ordered ticket batch before
     writing when current consent does not already cover the write.
   - Reuse an approved batch while its scope and action reach remain unchanged.
   - Ask again only when ticketing expands the approved scope or action reach,
     or the host requires it.
   - Local ticket approval never authorizes remote publication.

6. **Write and review as one set.**
   - Write tickets in dependency order and generate the order file from the
     complete approved set.
   - In every multi-ticket order output, report the ready frontier: exactly the
     uncompleted tickets whose blockers are complete. Recalculate it whenever
     completion or blockers change.
   - Check coverage from every spec acceptance criterion to at least one
     ticket, blocker consistency, portable links, duplicate scope, and
     fresh-agent readiness.
   - Return `scope-changed` if slicing exposes missing or expanded contract
     scope and `documentation-impact` when durable tickets are written.

## Output Contract

Use [Ticket Slicing Templates](references/ticket-slicing-templates.md), then
return:

- source spec and slicing-readiness result;
- slicing strategy and single- or multi-ticket rationale;
- ordered ticket paths and dependency graph;
- order-file path or explicit single-ticket skip;
- ready frontier for multi-ticket sets;
- acceptance-criteria coverage;
- approval reused, requested, or invalidated;
- fresh-agent-ready review result;
- changes, risks, route signals, and skipped checks.

## Delegation

The main agent owns slice boundaries, dependencies, approval interpretation,
coverage, and final writes. Delegate only non-overlapping candidate slices,
source-link discovery, or a fresh-agent review. Require inspected sources,
proposed paths, blockers, coverage, assumptions, and status. Without
delegation, run the same passes sequentially.

## Guardrails

- Slice only from a settled, current contract.
- Keep exact implementation plans out of durable tickets.
- Use the canonical planning skill names; old names stay aliases, not folders.
- Leave historical PRDs and archived issue artifacts unchanged.
- Do not create remote issues, labels, milestones, assignees, or project-board
  state without separate authorization.

## References

Use [Ticket Slicing Templates](references/ticket-slicing-templates.md) for
proposal, ticket, and multi-ticket order shapes.
