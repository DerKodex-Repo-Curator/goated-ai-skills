# Ticket 081: A Shared Core Any Harness Can Call

## Parent Spec

`docs/specs/2026-11-17-portable-enforcement-core.md` (R4, R5, R11; AC3,
AC4, AC5)

## Type

AFK.

## Problem

After Ticket 080 the adapter's rules read only the event model, but they
still live inside the Claude Code adapter, and the only way to run them is
Claude Code's hook entry point. A harness in another language, or a custom
API loop, cannot call them.

## What To Build

- **The core.** The rule modules and the session state move into a package
  at `adapters/core/`, which depends on the event model alone.
- **Two ways in.**
  - A Python call: events in, decision out.
  - A command that reads one JSON request on standard input and writes one
    JSON decision on standard output: allow, or a hold with its gate, kind
    and text, plus any notices. A request of an unknown version, or one
    the core cannot read, is answered with allow and a visible reason, as
    the fail-open rule requires.
- **State.** The core keeps session state keyed by a session id the caller
  supplies, in a location the caller may set.
- **Claude Code adapter.** It keeps the transcript reader, the hook entry
  point and the translation layer, and calls the core. Its install steps,
  behaviour and hold texts do not change.
- Update `AGENTS.md`'s "Where Work Lives": `adapters/` holds one subfolder
  per framework plus `core/`, the shared rules every adapter calls. The
  validator's boundary check, that adapter code imports only the standard
  library, covers the core, which an adapter may also import.
- Update `adapters/README.md` to list the core and how an adapter uses it,
  and the Claude Code README's Install, State and Tests sections.
- **Finish moving the rule text.** Ticket 079 thinned the Claude Code
  README only in part. Move the detection tables (code extensions, check
  commands, security path words, package managers, shell reading, comment
  syntax, content checks, branch size) into `stack/enforcement-contract.md`
  with the rule code, drop its Detection Detail citations of the README,
  and reduce the README's gate and closeout tables to Claude Code detail.
- **Retarget the contract check.** `tests/test_enforcement_contract.py`
  reads the gates, kinds and closeout labels from
  `adapters/claude-code/goated_adapter/`; point it at `adapters/core/`.
- **What Ticket 080 left for this one.**
  - *Hold-text slots.* The rules leave harness wording as slots
    (`goated_adapter/wording.py`: a name and arguments between two
    private-use characters), which only the Claude Code translation fills.
    Either publish that slot grammar and each slot's meaning in
    `stack/enforcement-contract.md` or the event model's schema, so another
    adapter can fill them, or have the core render neutral text and drop the
    slots from its output. The JSON command's decision text must not carry
    an unfilled slot either way.
  - *State bound to Claude Code.* Decide, as the state moves to the core:
    the saved override record's `prompt_id` (`state.py`, allowed by the
    purity check by name); `hooks._overrides_for`, which ties overrides to
    Claude Code's prompt ids; and `hooks._load_state`, which reads a shell
    saved as a tool name (`Bash`, `PowerShell`) as its shell kind. Then
    drop `state.py`'s allowance from
    `tests/test_claude_code_adapter_rule_purity.py`, which checks the core's
    modules too.

## Recommended First Reads

- The parent spec, R4, R5, Architecture and Constraints.
- The adapter as Ticket 080 left it.
- `adapters/claude-code/goated_hook.py` and `settings.snippet.json`.
- `adapters/claude-code/goated_adapter/state.py`.
- `adapters/README.md`.

## Acceptance Criteria

- [x] The core's package imports nothing from the Claude Code adapter and
      names no Claude Code tool; a check enforces it.
- [x] The command and the Python call return the same decision for every
      conformance scenario.
- [x] An unreadable request and an unknown version are each answered with
      allow and a reason.
- [x] The Claude Code adapter's existing tests pass with no change to
      expected outcomes or hold texts, and an existing install keeps
      working with no change to the user's settings.
- [x] Two sessions with different ids keep separate state.
- [x] `AGENTS.md` and `adapters/README.md` describe `adapters/core/`.
- [x] The contract holds the detection tables and cites no adapter README;
      the Claude Code README's gate and closeout tables keep only Claude
      Code detail.
- [x] The contract check reads the gates, kinds and closeout labels from
      `adapters/core/`.

## Expected Proof

- The conformance scenarios, run through both ways in.
- The existing adapter tests.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.
- A live check: one real Claude Code session after the move.

## Blocked By

- `tickets/archive/080-adapter-rules-read-the-event-model.md`

## Scope Exclusions

- The log and report command (Ticket 082).
- The guide and worked example (Ticket 083).
- Packaging or publishing the core outside this repo.

## Decisions On What Ticket 080 Left

- *Hold-text slots: the core renders neutral text.* The rules still write
  `wording` slots, and `goated_core.judge`, the call an adapter that builds
  the model's objects itself uses, returns them unfilled, so the Claude
  Code adapter fills them in its own words as before. `request.decide` and
  the command fill every slot with `wording.neutral` before answering, so
  no JSON decision carries one, and the slot grammar stays a detail of the
  Python call (`goated_core/wording.py`) rather than a published contract.
  Publishing it would have made every adapter in another language fill
  slots it has no reason to know; no Claude Code text changes.
- *State bound to Claude Code: the key is the caller's.* The override record
  is keyed by `prompt`, an opaque key the caller gives for the prompt that
  opened the turn; `judge.overrides_for` matches it. Claude Code passes its
  `prompt_id`, the request call the turn's key. State that an adapter from
  before this ticket saved in Claude Code's words (the `prompt_id` key, a
  shell saved as `Bash` or `PowerShell`) is upgraded as it loads by
  `translation.upgrade_state`, which the adapter passes to the core's state
  store, so a session that spans the upgrade behaves as before.
  `state.py`'s allowance is gone from the purity check, which now covers
  every core module.

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `c6d7237` (`5d060ea`, `b371d17`, `c6556b9`, `39e0f52`,
  follow-ups `6000536`, `d492453`).
- Decisions: as recorded above, on what Ticket 080 left.
- Exercised in later sessions; no separate live-check record.
