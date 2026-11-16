# Ticket 047: Adapter Records Overrides From Other Agents' Messages

## Parent Spec

`docs/specs/2026-11-15-skill-enforcement-adapter.md` (R8, user overrides
come only from the user; AC4)

## Type

AFK.

## Problem

In real use on 2026-11-16 a subagent's review report arrived in the main
session as a new prompt. The report quoted phrases such as
`skip commit-message`. The adapter's prompt hook answered with "recorded your
override for this prompt" and listed those phrases, though nobody typed them.

The prompt hook classifies a prompt from its text alone
(`prompt_text_kind`). It treats text that starts with
`<cross-session-message` as written by another session. Real messages from
another agent or session reach the prompt hook wrapped differently:

```text
Another Claude session sent a message:
<agent-message from="...">
[Subagent hand-back] ...
```

or the same first line followed by `<cross-session-message from="...">`. Neither
starts with a known prefix, so the hook classifies both as typed, parses
overrides from them, stores them in the session state, and announces them.

The gates do not apply them. `_overrides_for` asks the transcript, whose entry
for such a prompt has `origin.kind` `peer` (with `handback: true` for a
subagent's report), and the transcript reader treats any origin other than
`human` as not typed. What goes wrong is that the agent is told "recorded your
override", which reads as the user's wish. The skill-usage mod also counts
the sentence as a user override, so its override figures are wrong. And the
adapter tests model a peer message as starting with `<cross-session-message`,
a shape real messages do not have, so they missed this.

## What To Build

- The prompt hook records and announces overrides only for a prompt a
  person typed. A message from another agent or session, in every wrapper
  Claude Code uses, starts a turn with no overrides and no "recorded your
  override" sentence. Use any structured field the hook input carries about
  where the prompt came from before falling back to the text.
- The test helpers record peer and subagent hand-back prompts in the shape
  Claude Code actually writes: the wrapper's first line, the
  `origin.kind: "peer"` entry fields, and `handback` for a subagent's report.
- A regression test shows that a peer message quoting a skill skip, a
  routing skip, or a commit message neither announces an override nor stands
  down any hold. A typed prompt with the same words still does both.
- The adapter README's override section says which prompt sources can carry
  overrides.

## Recommended First Reads

- Spec R8 and AC4.
- The adapter README (`adapters/claude-code/README.md`): User Overrides, and
  what it says about prompts from other sessions and subagents.
- `adapters/claude-code/goated_adapter/transcript.py` (`prompt_text_kind`,
  the prefix lists, and how a transcript entry's origin is judged),
  `goated_adapter/hooks.py` (`_user_prompt_submit`, `_overrides_for`), and
  `goated_adapter/overrides.py`.
- The `peer` helper in `tests/claude_code_adapter_support.py`, and the
  override tests in the adapter test files.

## Acceptance Criteria

- [ ] A prompt in the recorded shape of a subagent hand-back, or of a message
      from another session, that contains a skill skip phrase produces no
      override in the hook's output or in the stored state.
- [ ] With such a prompt opening the turn, a hold that a typed override
      would clear still holds.
- [ ] A typed prompt with the same words still records, announces, and
      applies the override.
- [ ] The peer test helper uses the real wrapper shape, and existing tests
      still pass with it.
- [ ] The README's override section names which prompts can carry overrides.

## Expected Proof

- Adapter tests driving the hook entry point with recorded-shape prompts and
  transcripts, for both a hand-back and a cross-session message.
- `uv run python -m unittest discover -s tests` on Python 3.11 and 3.14,
  `uv run python scripts/validate_skills.py`, and `claude plugin test .` in the
  mod folder.
- A live check: a subagent report that quotes a skill skip phrase brings no
  "recorded your override" sentence.

## Blocked By

- `tickets/041-adapter-review-holds-read-the-change.md` (same files)

## Scope Exclusions

- The override phrase set itself, and how typed overrides apply.
- The skill-usage mod's override counts already stored from such messages:
  they stay as recorded.
