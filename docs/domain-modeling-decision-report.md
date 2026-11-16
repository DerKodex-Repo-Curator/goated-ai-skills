# Active Domain Modeling Decision Report

## Decision Summary

- Report date: 2026-11-16.
- Scope: Ticket 023 and parent-spec R7/AC8.
- Audience: GOATED maintainer and any future domain-modeling proposal.
- Document type: overlap evaluation with live pressure scenarios.
- Evaluation recommendation: **NO-GO** for a separate `domain-modeling` skill.
- Maintainer decision: **NO-GO**.
- Decision date: 2026-11-16.
- Production changes made by this ticket: **none**.

No scenario showed a settled term or consequential decision being lost under
the current stack. Every scenario ended in one of the behaviors a
`domain-modeling` skill would aim for, and none produced the ceremony a new
skill could add. The remedy R7 describes, narrow term and ADR deltas written
the moment they settle, already exists as the "refine current skills" option:
`grill-with-docs` step 7 and its two references gained exactly that inline
write in the lean-skills update (Ticket 025, 2026-10-06). That update's spec
records it as the Ticket 023 refinement branch, with use of it counting as
evidence here rather than as this decision.

A new skill would add catalog and routing cost, and it would overlap three
current owners, to cover a gap these scenarios did not reproduce.

## Decision Record

The maintainer selected **NO-GO** on 2026-11-16 after reviewing this report.

- No `domain-modeling` skill is added.
- `grill-with-docs` remains the owner of active term and ADR capture through
  its inline single-delta write and its two references.
- Ticket 024 is not authorized and closes without implementation.
- Accepted residual uncertainty: the scenarios were single short runs on one
  model with a prominent glossary. Reopen only with real-use evidence that a
  settled term or consequential decision went missing from durable docs.

## Scope And Evidence Standard

The question under test: does GOATED lose settled terminology or
consequential domain decisions during delivery because ownership is split
across onboarding, clarification, specification, and architecture workflows?

Evidence labels follow
`skills/agent-workflows/framework-agnostic-skill-creator/references/skill-evaluation.md`:

- **Source reading**: what current skill text says each owner does.
- **Live task run**: a fresh agent performing a realistic delivery request
  against a disposable project, with the resulting files inspected.

No decision exercise is reported as a live run. Static fixtures were not used
as behavioral proof.

## Ownership Matrix

Source reading of current skill text on `main` at commit `f46db50`.

| Owner | Trigger | Read behavior | Candidate update | Write behavior | Approval | Output |
| --- | --- | --- | --- | --- | --- | --- |
| `project-context-calibration` | Terms, boundaries, or artifact meanings ambiguous, contested, or inconsistent; context file missing or stale; usually onboarding or refresh | Shared onboarding evidence, context matrix, existing `CONTEXT.md`, then narrow discovery | Boundaries, domain language, durable artifacts, architecture vocabulary | Creates or incrementally refreshes root `CONTEXT.md`; preserves accurate content | Onboarding artifact budget and current consent | `CONTEXT.md` plus envelope delta |
| `grill-with-docs` | Unclear or doc-conflicting intent, scope, success criteria, or tradeoffs that block safe progress | Context matrix, standards, ADRs, context docs, specs, source, tests; `references/context-docs.md` and `references/adr-capture.md` when language or a costly decision is involved | Single settled term, single ADR-worthy decision, other candidate durable updates | Writes one term or one decision at once in the project's existing place when consent covers it; otherwise lists candidates; routes broader curation onward | Current covering consent; no new context doc unless asked | Working brief with Candidate Durable Updates |
| `write-a-spec` | Fuzzy product or delivery intent needs a spec | Smallest relevant source, docs, decisions | Spec decisions and open questions | Writes the spec; no context or ADR writes | Spec scope consent | Compact or full spec |
| `design-codebase-architecture` | Clarified brief needs a source-grounded blueprint | `CONTEXT.md`, ADRs, standards, maps, source | RFC/ADR triggers | Design-only; routes ADR capture to companions | Not applicable (no writes) | Blueprint naming ADR triggers |
| `review-codebase-architecture` | Review of existing architecture quality | Context docs, ADRs, recorded rejections | Findings; reopened decisions flagged | Creates ADRs only when separately asked | User request | Review report |
| `doc-sync` | After behavior, interface, architecture, or standards change | Docs searched for changed names, schema terms, and architecture vocabulary | Required and recommended doc updates | Minimal edits to required docs; updates an ADR when a convention exists; reports the need otherwise | Implementation-mode consent | Doc-sync delta |

Gaps the matrix shows on paper:

- No owner triggers on a term being *coined during implementation* when
  nothing is blocked; `grill-with-docs` triggers only on blocking ambiguity,
  and `doc-sync` triggers only after the change.
- The ADR-capture rule (hard to reverse, surprising, tradeoff-driven) lives in
  `grill-with-docs/references/adr-capture.md`, while `doc-sync` and the
  architecture skills say "ADR" without linking that rule.

The scenarios below test whether these gaps cause loss in practice.

## Pressure Scenario Packet

Reusable inputs. Each scenario runs as a fresh agent against its own copy of
the fixture, with standing consent to edit project files, no git, and an
instruction to stop and report any question that needs the user. Briefs carry
the user request verbatim and do not mention terminology, glossaries, ADRs,
or GOATED.

### Fixture: `shoplite`

A small Python order library with:

- `CONTEXT.md` (GOATED shape) defining Customer (stored as `Account`),
  Reservation (stock set aside for a *paid* order), Order, Cancellation
  (before shipment only), and Return, plus an ADR path convention
  `docs/adr/NNNN-title.md`.
- `docs/adr/0001-cancel-only-before-shipment.md`.
- `shoplite/accounts.py`: `Account` is a signed-in customer.
- `shoplite/billing.py`: `BillingAccount` is an invoiced company, and a
  module-level `accounts` registry with a comment that billing code calls these
  "accounts" throughout.
- `shoplite/orders.py`: `Order.total: float` in dollars; `reserve_stock`;
  `cancel_order` that also cancels `shipped` orders, contradicting ADR 0001;
  `list_orders(account_id, page=0, page_size=20)`.
- `tests/test_orders.py`: two passing tests.

### Scenarios

| ID | Pressure | User request (verbatim) | Good outcome | Loss or ceremony signal |
| --- | --- | --- | --- | --- |
| S1 | Newly coined term | "Add holds. A hold is when a customer grabs stock for 15 minutes before they've paid, so nobody else can buy it out from under them. It's not the same as what we do for paid orders. Add a `place_hold` function and a way to release expired holds, with tests." | Hold implemented; Hold recorded as distinct from Reservation in the project's existing glossary | Hold left undefined, or merged into Reservation, or a context rebuild |
| S2 | Overloaded language | "Finance wants a function that lists every account with its order count, for the monthly report. Add `account_order_counts()` and a test." | Ambiguity between customer `Account` and `BillingAccount` surfaced before implementing | Silent guess at one meaning |
| S3 | Code-versus-glossary contradiction | "Support wants to know why orders get cancelled. Make `cancel_order` take a required `reason` string and keep it on the order. Update the tests." | Request done; the shipped-order contradiction with ADR 0001 and `CONTEXT.md` surfaced for a decision | Silent edit of either side, or contradiction missed |
| S4 | Reversible design choice | "The order history page feels sparse. Bump the default page size for `list_orders` to 50, and let's call the second argument `page_number` instead of `page` since that's clearer." | Change made with no ADR or context write | ADR or glossary entry for a reversible choice |
| S5 | ADR-worthy decision | "We got bitten by float rounding on refunds again. We talked it over and we're done with float dollars: from now on all money in shoplite is an integer number of cents, everywhere, and we won't support fractional cents even though the tax team asked for it. Make the change." | Change made; ADR in the existing convention recording the rejected alternative; narrow context delta | Decision left only in code or chat |

## Observed Current-Stack Results

Live task runs on 2026-11-16: one fresh Claude Code general-purpose subagent
per scenario (Opus 5.5), started from a session with this maintainer's
installed GOATED skills and shared policy. Whether the Claude Code enforcement
adapter's holds also applied inside the subagents was not confirmed; no
subagent loaded the router. Each fixture copy's diff
and test result were checked by the coordinating agent, not taken from the
subagent's report.

| ID | Skills loaded | Files changed | Observed outcome | Verdict |
| --- | --- | --- | --- | --- |
| S1 | `tdd` | `orders.py`, new `tests/test_holds.py`, `CONTEXT.md` | Added one Hold row stating it is unpaid, expires, and is "not a Reservation"; updated the date; no other context edits. Raised hold-to-order conversion as an open question. Tests pass. | GREEN |
| S2 | none | none | Stopped before coding; explained the customer `Account` versus `BillingAccount` readings and why they yield different numbers; recommended a reading; suggested a Billing account context row once answered. | GREEN |
| S3 | none | `orders.py`, `tests/test_orders.py` | Implemented `reason`; did not change shipped-order behavior; reported the contradiction with ADR 0001 and `CONTEXT.md` as an open question. Tests pass. | GREEN |
| S4 | none | `orders.py`, `tests/test_orders.py` | Made the change; no ADR or context write; noted the keyword rename can break outside callers. Also spotted the S3 contradiction in passing and reported it without fixing. Tests pass. | GREEN, no ceremony |
| S5 | none | `orders.py`, `tests/test_orders.py`, new `docs/adr/0002-money-as-integer-cents.md`, `CONTEXT.md` | Wrote a short ADR in the existing convention, including the rejected fractional-cents request, and one Money context row. Tests pass. | GREEN |

### RED Evidence

No actual loss or ceremony was observed. The only RED candidates are
hypothetical:

- The ownership gap for terms coined mid-implementation (S1) did not cause
  loss: the agent recorded the term without loading any GOATED skill.
- Ceremony risk (S4) did not occur.

Agents reached these outcomes mostly without loading a GOATED skill, so the
results show the base model plus the visible project convention is enough in
these cases. They do not show that `grill-with-docs` caused the behavior. They
do show that a new skill would have had nothing to correct here.

## Remedies Compared

| Remedy | What it would change | Invocation value | Context cost | Overlap risk | Write boundary | Standalone behavior |
| --- | --- | --- | --- | --- | --- | --- |
| A. Refine current skills (already landed) | `grill-with-docs` inline single-term and single-ADR write with formats in its references | Reached whenever clarification runs | Zero added catalog entries; two existing references | Low; one owner for the procedure | One term or one decision; existing place; covering consent | Works when `grill-with-docs` is installed alone |
| B. Reference primitive | Lift the term and ADR capture rules into a shared reference that `doc-sync` and the architecture skills also link | Adds the ADR rule where those skills currently say only "ADR" | Small; each linking skill gains a pointer | Low to moderate; must avoid copying | Same as A | Each skill needs its own copy or link; installed-alone skills cannot link across folders, so this would mean duplication |
| C. New `domain-modeling` skill | Independently invokable skill for active term and decision modeling, as upstream | Only if users or the router would call it apart from clarification; no scenario showed that need | One more catalog description and router branch for every session | High; overlaps `grill-with-docs`, `project-context-calibration`, and `doc-sync` triggers | Narrow by spec R7 | Self-contained, but duplicates A's procedure |

Upstream comparison (summarized, not copied): the upstream `domain-modeling`
skill triggers on discussing terminology or editing a glossary or ADR, flags
glossary conflicts, sharpens overloaded terms, stress-tests with scenarios,
checks claims against code, writes glossary entries inline as terms resolve,
and offers ADRs only under the same three-part test GOATED uses. Every one of
those behaviors already appears in `grill-with-docs` and its references.

## Evaluation Recommendation

**NO-GO** for remedy C. Keep remedy A as the owner, and close Ticket 024
without implementation.

- Invocation value: no scenario needed a separate entry point; the one paper
  gap (S1) did not cause loss.
- Context cost: a new description loads into every session's catalog and adds
  a router branch, for no observed gain.
- Overlap risk: high; three current skills would share its triggers.
- Write boundary: the narrow write already exists in `grill-with-docs`.
- Standalone behavior: an installed-alone `grill-with-docs` already carries
  the formats it needs.

Remedy B is not recommended now. Self-contained installs mean a shared
reference becomes copied text in each skill, and no scenario showed `doc-sync`
or the architecture skills misjudging an ADR.

Reopen this question only with real-use evidence of loss, such as a term or
decision missing from durable docs after a long or compacted session, or a
weaker model failing these scenarios.

## Acceptance And Residual Risk

| Ticket 023 criterion | Evidence |
| --- | --- |
| Ownership mapped by trigger, read, candidate update, write, approval, output | Ownership Matrix |
| Scenarios cover new term, overloaded language, code-versus-glossary contradiction, reversible choice, ADR-worthy decision | Scenarios S1 to S5 |
| RED evidence separates actual loss or ceremony from hypothetical concern | RED Evidence |
| Remedies compare refinement, reference primitive, and new skill | Remedies Compared |
| Recommendation states invocation value, context cost, overlap risk, write boundary, standalone behavior | Evaluation Recommendation |
| Maintainer records go, revise, or no-go | Decision Record: NO-GO on 2026-11-16 |

Residual risk:

- One run per scenario on one model and host; variance is not measured.
- Short sessions on a seven-file fixture with a prominent `CONTEXT.md`. Loss
  is more likely in long sessions, after context compaction, or where the
  glossary is buried or absent.
- The scenarios ran beside this maintainer's GOATED setup, so they measure the
  current stack as one maintainer uses it, not an installed-alone skill.
- The subagents were told to stop rather than ask, which may make them more
  cautious than an interactive session.
