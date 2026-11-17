# Ticket 053: Adapter Reads Route And Skip Lines From Tool Input

## Parent Spec

`docs/specs/2026-11-15-skill-enforcement-adapter.md` (Trial Result; AC11)

## Type

HITL: the maintainer chooses where the line goes in a tool call, because it
changes what the portable contract asks of an agent.

## Problem

Ticket 045 found that in Claude Code, the text of a message that makes a tool
call can be saved as a `thinking` block holding a rewritten summary, and the
summary drops `goated-route:` and `goated-skip:` lines. The adapter reads only
`text` blocks, so it never sees those lines. In one ticket session the agent
wrote a route line four times, beside different calls, and every later write
was held; only a prompt the user typed (`skip routing`) got past it. A retry
cannot help when the first message was not saved as text, and a message with
no tool call ends the turn, so the next prompt starts a new task.

Ticket 045 changes only wording and records the limit. This ticket gives the
agent a place for the line that the adapter always sees.

## What To Build

- The adapter also reads route and skip lines from the input of a tool call,
  which the PreToolUse hook receives before the call runs and which the
  transcript keeps as written. Candidates to settle with the maintainer:
  - the arguments of the router's `Skill` call, such as
    `Skill(using-goated-ai-skills, args: "goated-route: ...")`;
  - the `description` of a shell call;
  - any string field of any tool input, matched by the line grammar.
- A line read from tool input counts from that call on, as a line in reply
  text does: the same grammar, the same last-line-wins and task rules, and
  the same per-turn scope. It covers the call that carries it.
- Overrides stay prompt-only (Ticket 047); a tool input never carries one.
- The router's output contract and the shared policy say where to put the
  line when a framework judges calls as they are made, in framework-neutral
  words; the line in reply text stays valid.
- Update the README (What It Holds, Hold messages, Known Limits) and the hold
  texts, and teach the skill-usage mod to count lines read from tool input.

## Recommended First Reads

- `tickets/archive/045-route-and-skip-lines-before-the-call.md`, whose
  closeout records the evidence.
- `adapters/claude-code/goated_adapter/transcript.py` (how turns and lines
  are read), `gates.py`, and `hooks.py` (PreToolUse input).
- `stack/fixtures/markers/README.md` (Marker Line Grammar).
- `skills/agent-workflows/using-goated-ai-skills/SKILL.md` (Output Contract)
  and `stack/AGENTS.md` (Routing And Checkpoints).
- The skill-usage mod's marker reading in
  `adapters/claude-code/skill-usage/hooks/classify.ts`.

## Acceptance Criteria

- [ ] A route line in the chosen tool-input place satisfies the route-line
      gate for that call and later calls in the turn, with no text line.
- [ ] A skip line there clears a justified-skip hold the same way.
- [ ] A line in tool input of a subagent, a peer turn, or an earlier turn
      follows the same rules as a text line in those places.
- [ ] No override is read from tool input.
- [ ] The router, shared policy, README and hold texts say where the line
      may go; `tests/adapter-texts.ts` is regenerated.
- [ ] The mod counts lines from tool input with the existing marker events.

## Expected Proof

- Adapter tests with recorded-shape transcripts for each criterion and its
  near miss, including a message whose text block is a summary without the
  line.
- A live check in a scratch project: a route line placed only in tool input
  lets the next write pass.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, and
  `claude plugin test .` in the mod folder.

## Blocked By

- `tickets/archive/045-route-and-skip-lines-before-the-call.md` (it settles the
  wording and the Known Limits entry this ticket extends)
- `tickets/archive/046-adapter-pipeline-after-compaction.md` (same routing files)

## Scope Exclusions

- Changing Claude Code's transcript format.
- Accepting overrides from anything but a typed prompt.

## Closeout

Completed, merged and archived on 2026-11-17.

- Merged as `d6bd3e0` (`5ddbdae`, review fixes `8d3dcfb`). The maintainer
  chose two places for the line: the `description` of a Bash, PowerShell,
  Agent or Task call, and the `args` of a Skill call. MCP tools and other
  tools carry no line, since their `description` is often the payload, such
  as an issue or merge-request body.
- A line in a call counts from that call on and follows the text-line rules;
  a call counts once, by id, or by name and input when the hook gives no id.
  No override is read from a call. The merge with Ticket 051 also counts
  `goated-design-reads:` lines from the same fields, in the adapter and the
  mod.
- Live check with a cheap model in a scratch project: a route line only in
  the router Skill call's `args` let the next Write pass; without it the
  Write was held.
- Every check passed on main after the merge: the validator, the unit tests on Python 3.14 and 3.11, the V1/V2 context comparison, `claude plugin test` (164 pass), and the TypeScript check with only the 5 known errors in `tests/register.test.tsx`.
- The installed router and shared policy were synced from main after the
  merge.
