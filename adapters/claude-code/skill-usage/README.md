# Skill-Usage Mod For Claude Code

An optional Claude Code mod that shows, in a pane beside the chat, which
skills load and why, what became of each GOATED hold and hook nudge, and what
subagents did. It is the measurement tool for the
[GOATED Claude Code adapter](../README.md). It displays only and enforces
nothing.

You can install it without the adapter; it then shows skill loads, reference
reads, and any route and skip lines agents write. Skills work the same with or
without it.

## What It Records

| Record | Read from |
| --- | --- |
| Skill loads and why each loaded: your `/command`, your prompt naming it, a hook, the router's route, the agent, or a subagent | Skill tool calls and slash commands |
| Route lines, counted by form (`direct`, `continue`, routed) | `goated-route:` lines in replies |
| Turns that write, by whether a route line came before the first write, only after it, or not at all | The main agent's edits and spawns, the calls the adapter holds like writes |
| Justified skips, with their reasons; a skip declines a justified-skip hold or a hook nudge naming that skill in the same turn | `goated-skip:` lines in replies |
| The adapter's holds by gate and kind, and each held skill's outcome: loaded, files read, already loaded, declined, not loaded, or waiting | Denied calls whose reason starts `goated-hold: <gate> \| <kind>` |
| Your overrides, by phrase | The adapter's sentence `recorded your override for this prompt` in hook context (see [Known Limits](#known-limits)) |
| Reads of skills' reference and other supporting files, and whether the skill had loaded first | `Read` paths and shell commands |
| Subagent spawns, with type and task, including ones that load no skill | Agent tool calls |
| A subagent's start message, and its reads of a skill's `SKILL.md` | SubagentStart hook context; a subagent's `Read` calls |
| Whether the router loaded before any other tool | The session-start router rule of earlier hand-written hooks |

Both route and skip lines are read with the marker grammar in
`stack/fixtures/markers/README.md`, and the mod's tests check that reading
against `lines.yaml` there.

The mod also reads the hold and nudge messages of the hand-written hooks some
installs ran before the adapter (`ROUTE CHECK`, `DESIGN HOLD`, `COMMIT CHECK`,
and others in `hooks/classify.ts`). It will keep reading them until the
adapter replaces those hooks.

Holds reach a session as denied tool calls. The pane counts a hold as
followed when the agent then loads the skill (or reads its files), and as not
loaded when the turn ends without that. A `justified-skip` hold also counts as
declined when a skip line names the skill in the same turn; a `strict` hold
never does, because only loading the skill clears it. A `router-first` hold
asks for the router, and a `route-line` hold asks for a route line.

## The Pane

- **Session**: a picture of where skill loads came from, then lines on how
  the holds went, the router rule, and route lines, writing turns, adapter
  holds, overrides, and subagents. Below them is an activity log, newest first, with per-hold
  and per-skill tables.
- **All time**: the same totals across stored sessions.
- **Unused**: your own skills by how often they loaded, and those that never
  have.

`/skill-usage` opens the pane, `/skill-usage report` prints the All time and
Unused tabs as markdown, and `/skill-usage preview` plays every animation once.

## Requirements

- The Claude Code CLI or desktop app with mod (function-hook plugin) support.
  The mod was built and tested on Claude Code 2.1.325. The plugin API is
  marked early access and may change between releases.

## Install

1. Copy this `skill-usage/` folder to a stable place, for example next to the
   adapter as `<goated-root>/adapters/claude-code/skill-usage/`.
2. Add the folder as a local marketplace and install the mod from it:

   ```bash
   claude plugin marketplace add "<goated-root>/adapters/claude-code/skill-usage"
   ```

   ```bash
   claude plugin install skill-usage@goated-skill-usage
   ```

3. Start a new Claude Code session. The pane opens at session start.

To try it for one session without installing, start Claude Code with
`claude --plugin-dir "<goated-root>/adapters/claude-code/skill-usage"`.

To check the install, run `/skill-usage report` in a session. It should print
a report that starts `# Skill usage:`.

## Disable

```bash
claude plugin disable skill-usage@goated-skill-usage
```

`claude plugin enable skill-usage@goated-skill-usage` turns it back on. Start
a new session to be sure the change applies.

## Remove

1. Uninstall the mod and remove its marketplace:

   ```bash
   claude plugin uninstall skill-usage@goated-skill-usage
   ```

   ```bash
   claude plugin marketplace remove goated-skill-usage
   ```

2. Delete the copied `skill-usage/` folder.

## Stored Data

The mod keeps one summary per session in its own plugin store: counts,
skill names, hold gates, override phrases, reference file paths within
skills, and skip reasons. It keeps no prompt or reply text beyond those
phrases and reasons. It keeps the 300 most recent sessions. Within a session,
the event list lives in session state and is capped at 5,000 events.

Summaries saved by earlier versions of the mod still read: fields added since
are optional, so an older summary simply has none of them.

The All time tab reads only the store of the installed plugin. Claude Code
may key that store by the plugin's install, so moving from another copy of
this mod to this one may start All time afresh. Check the tab after
switching, and keep the old copy installed but disabled if you want to
compare.

## Known Limits

- The adapter's justified-skip holds and its action and closeout holds are
  read only as far as their `goated-hold:` first line and backticked skill
  names allow.
- Overrides are not counted yet. The adapter shows your override as a notice,
  and a notice reaches a mod as a row with no text (checked on Claude Code
  2.1.325). The mod reads the same sentence from the adapter's hook context,
  which mods do receive with text, but the adapter does not send it there
  yet. When the mod loads mid-session, the history it rebuilds from has no
  hook context either, so earlier overrides go uncounted.
- A writing turn runs from one typed prompt to the next. A message from
  another session that starts a new turn for the adapter joins the running
  turn here, and so does a background result, as it does for the adapter.
- Only the subagent start message of the hand-written hooks
  (`DELEGATED AGENT`) is recognized; the adapter does not send one yet.
- The mod judges nothing. Whether a skip reason is specific to the action is
  for you to read in the log.

## Tests

From this folder:

```bash
claude plugin test .
```

```bash
claude plugin validate .
```

The tests in `tests/goated-adapter.test.tsx` read the marker fixtures through
`tests/marker-fixtures.ts`, generated from `stack/fixtures/markers/lines.yaml`.
In the GOATED source repo, `tests/test_skill_usage_mod.py` fails when that copy
drifts. Regenerate it with
`uv run python tests/test_skill_usage_mod.py --write` from the repo root.

CI runs that drift check on every change. The `Skill-usage mod` workflow
(`.github/workflows/skill-usage-mod.yml`) runs `claude plugin validate` and
`claude plugin test` on a pinned Claude Code version, only when the mod, the
marker fixtures, or the workflow change. The tests make no model calls and
need no credentials.
