# Skill-Usage Mod For Claude Code

An optional Claude Code mod that shows, in a pane beside the chat, which
skills load and why, what became of each GOATED adapter hold, and what
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
| Route lines, counted by form (`direct`, `continue`, routed) | `goated-route:` lines in replies, and in the `description` of a `Bash`, `PowerShell`, `Agent` or `Task` call or the `args` of a `Skill` call, as the adapter reads them |
| Turns that write, by whether a route line came before the first write, only after it, or not at all | The main agent's edits and spawns, the calls the adapter holds like writes; a call whose result is an error, such as a held one, did not write |
| Justified skips, with their reasons; a skip declines a justified-skip hold naming that skill in the same turn. The reason of each skip that declined a hold is kept by skill and gate: each path-like word in it (one starting with a drive such as `C:/`, a slash, or `~/`, or holding a backslash) replaced by `<path>`, then cut to 160 characters. Nothing else is stored beside it, and other words, a project name among them, are kept as written | `goated-skip:` lines in replies, and in the same call fields as route lines |
| The adapter's holds by gate and kind, and each held skill's outcome: loaded, files read, declined, overridden by you, ended by a new prompt, unanswered, or waiting | Denied calls whose reason starts `goated-hold: <gate> \| <kind>`, and the blocked `Stop` that carries the closeout hold |
| Closeout items: each item a closeout hold lists, such as Proof, Unfinished, Docs, Design, Security, Setup, or one added later, with its own outcome | The item lines of the closeout hold's text, `- <Label>: …`, at a commit or a `Stop`; the item's skill is the first it backticks, else the skill of the skip line it offers |
| Your overrides, by phrase | The adapter's sentence `recorded your override for this prompt` in its hook context |
| Reads of skills' reference and other supporting files, whether the skill had loaded first, and when in the turn: before its first code change, between two, after the last, or in a turn with no code change | `Read` paths and shell commands; code changes are edit tool calls on a code file, by the main agent or a subagent, that ran |
| Design-reads lines: in how many replies each reference file was declared (a reply's lines add up to one set of files, each counted once), and how many lines declared `none` | `goated-design-reads:` lines in replies, and in the same call fields as route lines |
| Subagent spawns, with type and task, including ones that load no skill | Agent tool calls that ran; a held or failed attempt shows in the log as held but is not counted |
| A subagent's reads of a skill's `SKILL.md` | A subagent's `Read` calls |

Route, skip and design-reads lines are read with the marker grammar in
`stack/fixtures/markers/README.md`, and the mod's tests check that reading
against `lines.yaml` and `design-reads.yaml` there.

A code change is what the adapter counts as one where the mod can see it: an
`Edit`, `Write`, `MultiEdit` or `NotebookEdit` call on a file whose extension
the adapter lists as code. A turn runs from one typed prompt to the next, so a
read's moment settles when the next prompt arrives; until then a read after
the latest change counts as after the last. The mod counts a little
differently from the adapter in these cases:

- It does not see files a shell command writes, nor which files lie outside
  the project.
- It counts a subagent's code change when the subagent makes it, where the
  adapter counts it at the spawn. A background subagent's change that arrives
  after your next prompt counts in that later turn.
- A mod that joins a session late rebuilds the main conversation from its
  history, but not the subagents' calls, so their earlier code changes are
  missed.

Versions of the mod before moments were recorded stored no code changes, so a
session's turns recorded before an upgrade or reload have no moment: their
reads, like reads in summaries stored by those versions, show as not timed.
Only turns whose prompt this version recorded are timed.

Summaries stored by earlier versions of the mod may still show a GOATED
router rule line, start messages, or already loaded counts in All time. Those
stored before the three kinds of unanswered hold were told apart count them
together, as not answered in the pane and not loaded in the report, and have
no closeout items or skip reasons.

Holds reach a session as denied tool calls, and the closeout hold as a
blocked `Stop` or a denied commit. The mod reads each hold's gate and kind from its first line,
and the skills it asks for from the skill names its text backticks, alone or
as the skill of a `goated-skip:` line it offers. The pane counts a held skill
as followed when the agent then loads it (or reads its files). A hold that no
load, read, or skip line answered counts as one of three kinds:

- **Overridden by you**: the prompt after its turn records an override that
  stands it down, as the adapter's override table says: `skip routing` (or
  `skip router`, `skip the routing`, `skip the router`) for the
  `router-first`, `route-line`, and `pipeline` holds, `skip <skill>` (or
  `skip the <skill> skill`, the name backticked or not) for any hold asking
  for that skill, or a typed commit message for the `commit` hold, with any
  spacing the adapter accepts. The override counts only for the turn right
  before its prompt, and only until the agent starts replying.
- **Ended by a new prompt**: your next prompt arrived while it waited, or you
  interrupted the turn.
- **Unanswered**: the turn ended without an answer to it, or the session did.

A Skill call whose result is an error
loaded nothing, so it neither counts as a load nor answers a hold. A
`justified-skip` hold (`design`, `design-reads`, `security`,
`conflict-resolution`, `repeated-failure`, `pr-review`, `closeout`) also counts as declined when a
skip line names the skill in the same turn, before or after the hold; a
`strict` hold (`router-first`, `route-line`, `pipeline`, `commit`,
`pull-request`, `spawn`) never does, because only loading the skill clears
it. In particular:

- An adapter hold asks for a load in the current turn, so a skill loaded in
  an earlier turn shows as loaded only when the agent loads it again, never
  as already loaded.
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
- Once `software-design-principles` has loaded, the adapter's `design` hold
  asks for its design-reads line and the references the edit requires, and
  the `design-reads` hold for a later edit's references; both name the skill
  only in their skip line, backtick each reference by its path, and the
  `design` hold backticks the line's form when it asks for one. Such a hold
  is met, as the adapter judges it, once the agent has used the Read tool on
  each reference it names (a shell command printing one, another of the
  skill's files, or its `SKILL.md` does not count) and written a
  design-reads line if it asked for one. It counts as files read when a read
  came last, and as followed when the line did. Loading the skill again
  answers neither.
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
  the adapter counts a check run, a read of the red-flags file, a citation of
  each design reference the turn required, or a read of the change (its diff,
  or a changed file), not a load. A closeout item whose
  skill already loaded asks for that read of the change, so it names the
  skill only as a skip line.
- A blocked `Stop` does not end the turn, so the closeout hold waits for the
  agent's next move. Every block of the turn joins one closeout row. A block
  that asks again for an item after a load or a skip line means the adapter
  did not accept it, so the item waits again and that skip line no longer
  declines it.
- When the turn ends as an answer after the agent replied to the last block,
  the adapter let the `Stop` through, so each item still waiting counts as
  followed. That covers the items no load answers: a check run for the proof
  item, a fix for unfinished work, or a read of the change for the docs,
  design, and security items. A turn you interrupt, or one an error
  ends, passes nothing. Claude Code ends a turn after nine blocks in a row
  whatever the hook says: then what the last block asked counts as
  unanswered, and what only earlier blocks asked counts as followed.
- The adapter also holds a commit with the closeout's items when one is
  unmet. That hold joins the turn's closeout row and counts as one at `Stop`
  does: what is still waiting when the turn ends as an answer counts as
  followed, since the `Stop` that let the turn end judged every item again.
- Each closeout hold counts once for each item it lists, with that item's
  outcome, which is the outcome of the skill the item names. The labels are
  read from the hold's text, which the adapter keeps stable for this. The
  design red-flags item and the design citations item, which Ticket 075
  names as two items, share the label `Design` and the skill, so the mod
  cannot tell them apart and a hold listing both counts `Design` once.

These rules live in `hooks/holds.ts`, the hold settlement: `hooks/classify.ts`
reads the events and feeds them to it in order, and keeps the rest of a
session's summary.

## The Pane

- **Session**: a picture of where skill loads came from, then lines on how
  the holds went, and route lines, writing turns, adapter
  holds, overrides, and subagents. Below them is an activity log, newest first, with per-hold
  and per-skill tables.
- **All time**: the same totals across every stored session, reread after
  each turn, so sessions running beside this one count as they go. It also
  lists the reasons of the skip lines that declined holds, by skill and hold,
  most given first.
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
References table's heading counts reads made before their skill loaded. Under
each file, the References table counts its reads by moment in their turn.

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
  headings, the `commit` hold for a message that breaks the contract, and
  the `commit`, `pull-request`, and `pr-review` holds that ask, once their
  skill loaded, for a read of the change.
- The nine-block limit is Claude Code's as seen on 2.1.325. If a version
  changes it, a closeout the agent never got past may count as followed.
- A turn that ends as an answer after a blocked `Stop` counts as passed even
  when the adapter failed open on the last `Stop` and judged nothing; the
  mod cannot see that. When the mod rebuilds a session from history, which
  has no turn ends, it passes no closeout: the next prompt closes the turn
  and cannot tell a pass from an interruption, so items still waiting count
  as ended by a new prompt. For the same reason a rebuilt hold left open
  when a later prompt came counts as ended by a new prompt, never as
  unanswered, and since the rebuild carries no overrides, never as
  overridden.
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
- A hold still waiting when the session ends counts as unanswered. That
  includes a session you resume later: the turn it waited in is over.
- A mod reloaded mid-session, such as by a plugin update, keeps the
  session's events, unless the update changes their shape tag (the events
  atom in `hooks/register.tsx`). Then the events recorded before the reload are
  dropped and the session is rebuilt from its history, with that history's
  limits above. A resumed session is not rebuilt: its summary covers only
  what came after the reload, on top of its stored summary, and a hold
  waiting at that moment is dropped with the events.
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

The tests read three generated modules: `tests/marker-fixtures.ts`, from
`stack/fixtures/markers/lines.yaml`; `tests/design-reads-fixtures.ts`, from
`stack/fixtures/markers/design-reads.yaml`; and `tests/adapter-texts.ts`, the
hold reasons and override context the adapter produces when the generator
drives it. In the GOATED source repo, `tests/test_skill_usage_mod.py` fails
when any copy drifts, or when the mod's list of code file extensions differs
from the adapter's. Regenerate the modules with
`uv run python tests/test_skill_usage_mod.py --write` from the repo root.

CI runs that drift check on every change. The `Skill-usage mod` workflow
(`.github/workflows/skill-usage-mod.yml`) runs `claude plugin validate` and
`claude plugin test` on a pinned Claude Code version, only when the mod, the
marker fixtures, or the workflow change. The tests make no model calls and
need no credentials.
