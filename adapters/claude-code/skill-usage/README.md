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
| Turns that write, by whether a route line came before the first write, only after it, or not at all | The main agent's edits and spawns, the calls the adapter holds like writes; a call whose result is an error, such as a held one, did not write |
| Justified skips, with their reasons; a skip declines a justified-skip hold or a hook nudge naming that skill in the same turn | `goated-skip:` lines in replies |
| The adapter's holds by gate and kind, and each held skill's outcome: loaded, files read, already loaded, declined, not loaded, or waiting | Denied calls whose reason starts `goated-hold: <gate> \| <kind>`, and the blocked `Stop` that carries the closeout hold |
| Your overrides, by phrase | The adapter's sentence `recorded your override for this prompt` in its hook context |
| Reads of skills' reference and other supporting files, and whether the skill had loaded first | `Read` paths and shell commands |
| Subagent spawns, with type and task, including ones that load no skill | Agent tool calls that ran; a held or failed attempt shows in the log as held but is not counted |
| A subagent's start message, and its reads of a skill's `SKILL.md` | SubagentStart hook context; a subagent's `Read` calls |
| Whether the router loaded before any other tool | The session-start router rule of earlier hand-written hooks |

Both route and skip lines are read with the marker grammar in
`stack/fixtures/markers/README.md`, and the mod's tests check that reading
against `lines.yaml` there.

The mod also reads the hold and nudge messages of the hand-written hooks some
installs ran before the adapter (`ROUTE CHECK`, `DESIGN HOLD`, `COMMIT CHECK`,
and others in `hooks/classify.ts`). It will keep reading them until the
adapter replaces those hooks.

Holds reach a session as denied tool calls, and the closeout hold as a
blocked `Stop`. The mod reads each hold's gate and kind from its first line,
and the skills it asks for from the skill names its text backticks, alone or
as the skill of a `goated-skip:` line it offers. The pane counts a held skill
as followed when the agent then loads it (or reads its files), and as not
loaded when the turn ends without that. A Skill call whose result is an error
loaded nothing, so it neither counts as a load nor answers a hold. A
`justified-skip` hold (`design`, `security`, `closeout`) also counts as
declined when a skip line names the skill in the same turn, before or after
the hold; a `strict` hold (`router-first`, `route-line`, `pipeline`,
`commit`, `pull-request`, `spawn`) never does, because only loading the skill
clears it. In particular:

- An adapter hold asks for a load in the current turn, so a skill loaded in
  an earlier turn shows as loaded only when the agent loads it again, never
  as already loaded. ("Already loaded" is for the earlier hand-written hooks,
  which asked once a session.)
- A `router-first` hold asks for the router, and a `route-line` hold asks
  for a route line.
- Claude Code records a call only after its hold returns, so the adapter does
  not yet see a route line or skill load written in the same reply as the
  held call, and the agent only has to make the call again. A hold that the
  held call's own reply already answered counts as followed. A route line or
  load in an earlier reply does not count, and nor does a `continue` route
  line while there is no task to continue, which the adapter holds as well.
- A `pipeline` hold also counts as followed for a skill that a corrected route
  line drops, as the hold tells the agent to do.
- A `spawn` hold names two ways to write the brief, `handoff` or
  `subagent-driven-development`. It counts once: its row shows "handoff or
  subagent-driven-development" until the agent loads one, then names that one.
- A call's hold that holds again in the same turn, asking for nothing its
  gate's earlier holds did not, is one row marked `×N` and counts once in the
  rates; the adapter holds count each time. That covers the agent retrying a
  held call, and a retry held again because the adapter had not yet seen the
  load or skip line written beside it. What the earlier holds asked and the
  repeat no longer does was met.
- A skill a hold offers only as a skip line, such as
  `verification-before-completion` for the closeout's proof item, is answered
  by a skip line or by the adapter letting the turn end, never by loading it:
  the adapter counts a check run, or a read of the red-flags file, not a load.
- A blocked `Stop` does not end the turn, so the closeout hold waits for the
  agent's next move. Every block of the turn joins one closeout row. A block
  that asks again for an item after a load or a skip line means the adapter
  did not accept it, so the item waits again and that skip line no longer
  declines it.
- When the turn ends as an answer after the agent replied to the last block,
  the adapter let the `Stop` through, so each item still waiting counts as
  followed. That covers the items no load answers, a check run for the proof
  item or a fix for unfinished work. A turn you interrupt, or one an error
  ends, passes nothing. Claude Code ends a turn after nine blocks in a row
  whatever the hook says: then what the last block asked counts as not
  loaded, and what only earlier blocks asked counts as followed.

## The Pane

- **Session**: a picture of where skill loads came from, then lines on how
  the holds went, the router rule, and route lines, writing turns, adapter
  holds, overrides, and subagents. Below them is an activity log, newest first, with per-hold
  and per-skill tables.
- **All time**: the same totals across every stored session, reread after
  each turn, so sessions running beside this one count as they go.
- **Unused**: your own skills by how often they loaded, and those that never
  have.

In the picture, each node around the core is a cause of skill loads, with its
count beneath: **Your /cmd** (you typed a slash command), **You asked** (your
message named the skill), **Router** (a route line required it), **Agent** (the
main agent chose it), **Subagents** (a subagent chose it), and **Hooks** (it
loaded after a hook held a call). **References** instead counts reads of
skills' supporting files. The ring around the core fills with the share of
settled holds that were handled.

On the Session picture only, a badge on a node's corner counts single cases
this session:

- Hooks, red: holds not followed.
- Hooks, amber edge, breathing: holds still waiting.
- References, pink edged amber: reads made before their skill loaded.
- Subagents, blue: subagents started.

All time draws no badges; its lines and tables carry those totals, and the
References table's heading counts reads made before their skill loaded.

In the tables, each hook's bar is split by what became of its holds:
followed in green, declined with a reason in pale green, not followed in red.
Its rate is the share **handled**, followed or declined, of the holds that
settled, so a justified skip never lowers it. Each skill's and reference
file's bar is its count to scale beside the table's largest; a count has no
limit, so none is drawn as a ring that fills.

`/skill-usage` opens the pane, `/skill-usage report` prints the All time and
Unused tabs as markdown, and `/skill-usage preview` plays every animation once.

## Requirements

- The Claude Code CLI or desktop app with mod (function-hook plugin) support.
  The mod was built and tested on Claude Code 2.1.325. The plugin API is
  marked early access and may change between releases.

## Install

1. Find the mod's folder: `adapters/claude-code/skill-usage/` in your GOATED
   clone or download (`<goated-root>` below). The marketplace points at this
   folder, so leave it in place, or copy it somewhere stable first and use
   that path.
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

2. Uninstalling leaves the stored summaries behind. To delete them too,
   delete the mod's store file,
   `~/.claude/plugins/store/skill-usage_goated-skill-usage-<id>.json`.
3. If you copied the folder somewhere for the install, delete that copy.

## Stored Data

The mod keeps one summary per session in its own plugin store: counts,
skill names, hold gates, override phrases, reference file paths within
skills, and skip reasons. It keeps no prompt or reply text beyond those
phrases and reasons. It keeps the 300 most recent sessions one by one and
folds older ones into a single total under the key `older`, so All time
still counts them. Within a session, the event list lives in session state
and is capped at 5,000 events.

Summaries saved by earlier versions of the mod still read: fields added since
are optional, so an older summary simply has none of them.

Claude Code keeps the store in one file per plugin and marketplace, under
`~/.claude/plugins/store/` as `<plugin>_<marketplace>-<id>.json`. So
installing this mod as `skill-usage@goated-skill-usage` **starts All time
afresh**, even if another copy of the mod ran before. To carry the old
history over:

1. Install this copy and start one session, so its store file exists.
2. Quit every Claude Code session.
3. Copy the old copy's store file (`skill-usage_<old-marketplace>-<id>.json`)
   over the new one, keeping the new file's name. The session from step 1 is
   lost; the older ones read as before.

This has not been tested end to end. Keep a backup of both files.

## Known Limits

- A hold is read only as far as its `goated-hold:` first line and the skill
  names it backticks allow. A hold that names no skill counts by gate and
  kind with no per-skill result, and its row says what it asked for instead:
  the `spawn` holds that ask for a template read or for missing brief
  headings, and the `commit` hold for a message that breaks the contract.
- The nine-block limit is Claude Code's as seen on 2.1.325. If a version
  changes it, a closeout the agent never got past may count as followed.
- A turn that ends as an answer after a blocked `Stop` counts as passed even
  when the adapter failed open on the last `Stop` and judged nothing; the
  mod cannot see that. When the mod rebuilds a session from history, which
  has no turn ends, it passes no closeout: the next prompt closes the turn
  and cannot tell a pass from an interruption, so items still waiting count
  as not loaded.
- Overrides reach the mod through the adapter's `UserPromptSubmit` hook
  context. A notice reaches a mod as a row with no text, so the notice
  itself is not read. When the mod loads mid-session, the history it
  rebuilds from does not carry `UserPromptSubmit` hook context, so earlier
  overrides go uncounted. Both were checked on Claude Code 2.1.325.
- A slash command counts as a prompt only when it loads a skill. Other
  commands, such as `/skill-usage` or `/compact`, run without a model turn,
  so neither they nor their output start a turn in the pane.
- A writing turn runs from one typed prompt to the next. A message from
  another session that starts a new turn for the adapter joins the running
  turn here, and so does a background result, as it does for the adapter.
- Only the subagent start message of the hand-written hooks
  (`DELEGATED AGENT`) is recognized; the adapter does not send one yet.
- A hold still waiting when the session ends counts as not followed. That
  includes a session you resume later: the turn it waited in is over. A mod
  reloaded mid-turn, such as by a plugin update, starts its events afresh, so
  a hold waiting at that moment also counts as not followed, even if the agent
  follows it a moment later.
- Two sessions folding the same old sessions into the `older` total at the
  same moment can count them twice. Folding happens only past 300 sessions.
- A session already folded into `older` and then resumed counts twice: its
  own key is gone, so the mod rebuilds it from history and stores it again,
  while `older` still holds its earlier sum, which keeps no per-session
  parts to take back. Only a session older than the 300 most recent can be
  folded.
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

The tests in `tests/goated-adapter.test.tsx` read two generated modules:
`tests/marker-fixtures.ts`, from `stack/fixtures/markers/lines.yaml`, and
`tests/adapter-texts.ts`, the hold reasons and override context the adapter
produces when the generator drives it. In the GOATED source repo,
`tests/test_skill_usage_mod.py` fails when either copy drifts. Regenerate it with
`uv run python tests/test_skill_usage_mod.py --write` from the repo root.

CI runs that drift check on every change. The `Skill-usage mod` workflow
(`.github/workflows/skill-usage-mod.yml`) runs `claude plugin validate` and
`claude plugin test` on a pinned Claude Code version, only when the mod, the
marker fixtures, or the workflow change. The tests make no model calls and
need no credentials.
