# Ticket 121: Hold Text, Small Fixes And Log Detail

## Parent Spec

`docs/specs/2026-11-19-hook-friction-round-6.md` (R11, R12, R14, R15;
AC12, AC13, AC14)

## Type

AFK. Decisions Z, Y2 and Y4 (the maintainer, 2026-11-19).

## What To Build

The finishing pass of round 6: hold messages that open with what to do,
three small fixes, and the log detail the next round needs. It runs after
Tickets 118 to 120 so it rewrites the final hold texts once. One agent can
do this in four phases; each phase lands green.

- **Phase 1, hold text (R11).**
  - Each hold, and each closeout item, opens with its clearing action;
    conditions and caveats follow. The hold's first line
    (`goated-hold: <gate> | <kind>`) and each item's `- <Label>:` opening
    stay as the contract fixes them.
  - A malformed route line is quoted with its reason, such as "nothing may
    follow the line".
  - A read-only-looking command held as a write names the part that made
    it one.
  - A hold on a file edit says that other calls of the same message may
    have landed, and to read the file before sending the edit again.
- **Phase 2, temp paths are outside (R12).** A script write whose path is
  built from the system temp folder (such as Python's `tempfile`, or an
  environment temp variable) counts as outside the project, so
  `scripted-edit` does not hold it.
- **Phase 3, log detail (R15).** The usage log records each notice by
  kind, and for each hold the class of file it was about (code, test,
  docs, configuration, or other). It never records a path, prompt text or
  file content. The usage report shows both. A new field bumps the
  usage-log schema. The skill-usage pane keeps reading its own store; if
  it shows the new detail, it does so from that store.
- **Phase 4, spawn brief lines (R14).** The spawn-brief template gains a
  Checks line (what the agent runs, what the starter runs after merging)
  and a Shared-with line (other agents that may change the same files).
  Neither is a required heading: the `spawn` gate still passes a brief
  without them.

Hold-text and rule changes live in the shared core at
`adapters/core/goated_core/`, with the contract's Hold Messages, Hold
Text, Shell Reading and Project Folders And Scratch Files sections and
conformance scenarios changing with them. Phase 4 changes
`skills/agent-workflows/handoff/references/spawn-brief.md`; its registry
entry is unchanged because no reference file is added or renamed.

## Recommended First Reads

- The parent spec: R11, R12, R14, R15 and decisions Y and Z.
- `stack/enforcement-contract.md`: Hold Messages, Hold Text, Shell Reading
  (script writes and read-only commands), and Project Folders And Scratch
  Files.
- `tickets/archive/111-core-one-clearing-section-per-message.md` and
  `tickets/archive/112-core-scripted-edit-names-unknown-kinds.md`.
- The core's `wording.py`, the shared hold texts in `gates.py`, and
  `usage_log.py` with `stack/schemas/usage-log.schema.json`.
- The adapter's generated text fixture and how its test regenerates it.
- `skills/agent-workflows/handoff/references/spawn-brief.md`.

## Acceptance Criteria

- [ ] Each hold text in the adapter's text fixture opens with an
      imperative action, and each closeout item opens with one after its
      label.
- [ ] A route line with trailing text is quoted with the reason it does
      not match.
- [ ] A held read-only-looking command names the part that made it a
      write.
- [ ] A hold on a file edit carries the sentence about calls that may have
      landed.
- [ ] An inline script writing under the system temp folder meets no
      `scripted-edit` hold; the same script writing a run-time path inside
      the project does.
- [ ] A log written by a held edit carries a file class and no path, and a
      notice entry by kind; the usage report shows both; the log's schema
      validates.
- [ ] The template carries both lines, and the `spawn` gate passes a brief
      without them.
- [ ] The contract states each rule, and conformance scenarios cover the
      changed holds and a near miss.
- [ ] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The adapter's generated text fixture and the core's hold-text tests.
- The conformance scenarios through the core.
- The usage-log tests and its schema.
- The repo checks in `AGENTS.md`.

## Blocked By

- `tickets/118-core-design-reads-never-refuse-an-edit.md`
- `tickets/119-core-routing-and-orientation-for-continued-work.md`
- `tickets/120-core-commit-time-holds-in-one-pass.md`

All three are ordering: each changes hold or notice text that phase 1
reorders.

## Scope Exclusions

- Changing what any hold requires.
- Accepting trailing text after a route line.
- A dedicated tool or field for route and skip lines.
- Matching the skill-usage pane's keys to the log's.
