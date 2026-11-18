# Ticket 106: Definition Starts Read Their Keyword

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-4.md` (addendum R11; AC13,
AC7, AC8)

## Type

AFK. The rule moves toward what the contract already says it is for, a
public top-level definition; no option is open.

## What To Build

An added line counts as a public top-level definition, for `process.md`,
`complexity-and-modules.md` and the other design references that are "the
same as `process.md`", only:

- in a code file, never in a configuration file, so a YAML `class: foo`
  or `async: true` key defines nothing;
- where `async` comes before `def`, `function` or `fn`, so
  `async_helper = 1` is not one and neither is `async` alone;
- where `pub` (or `pub(crate)` and its forms) comes before a definition
  keyword: `fn`, `struct`, `enum`, `trait`, `type`, `const`, `static`,
  `mod`, `union`, `impl`, `async fn`, `unsafe fn` or `extern`, so
  `pub use x;` re-exports and defines nothing.

The other keywords and the name rule (its first word that is not a
keyword, not starting with `_`, not defined in the replaced text) keep
today's behaviour.

The rule lives in the shared core at `adapters/core/goated_core/`:
`design_reads.DEFINITION_START_RE`, `_definition`, and where the
definition check runs for a configuration file. The contract and a
conformance scenario change with the code, as `AGENTS.md` requires:

- `stack/enforcement-contract.md`, the design references table: the
  `process.md` row, whose last sentence today states the loose match, and
  any row that repeats it;
- `stack/fixtures/enforcement/writes.yaml` (or the file holding the
  design-reads scenarios): a `pub use` line and a YAML `class:` key that
  select no `process.md`, beside a `pub fn` that does.

## Recommended First Reads

- The parent spec's addendum, R11.
- `stack/enforcement-contract.md`, the `design-reads` row and the design
  references table.
- The core's `design_reads.py`: `DEFINITION_START_RE`, `_definition`,
  `_signals`, `applies` and `_is_config`.
- `tickets/099-core-fixture-data-is-test-data.md` and
  `tickets/100-core-narrower-reference-triggers.md`, which change the same
  module.

## Acceptance Criteria

- [ ] An added `pub use x;`, `async_helper = 1` or `async` line in a code
      file selects no `process.md`.
- [ ] An added `class: foo` key in a YAML file selects no `process.md`.
- [ ] `pub fn run()`, `pub(crate) struct S`, `async def run()`,
      `async function run()` and `class Run:` still do.
- [ ] The contract states the rule, and a conformance scenario covers a
      hold and each near-miss kind.
- [ ] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The conformance scenarios through the core.
- The core's design-reads tests, with the new lines.
- The repo checks in `AGENTS.md`.

## Blocked By

- `tickets/081-shared-enforcement-core.md` (merged)

## Overlaps

- **Same module as 099 and 100.** Ticket 099 edits `design_reads.applies`
  and `_is_config` and the `design-reads` row; Ticket 100 edits
  `design_reads._signals`, the `design-reads` row and the `readability.md`
  row ("the same as `process.md`"). Land after both, or coordinate.

## Scope Exclusions

- Whether `pub(crate)` is public: it counts, as today.
- JavaScript `export { a } from "b"` and other re-export forms.
- Indented definitions, and a code file being created.
