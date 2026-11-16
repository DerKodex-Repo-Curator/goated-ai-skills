# Design References Read At Their Moment

## Status

Approved by the maintainer on 2026-11-16 in a grill-with-docs session. Ticket
ready. Builds on
[the software design principles spec](2026-11-13-software-design-principles.md),
[the skill enforcement spec](2026-11-15-skill-enforcement-adapter.md) (R7,
change reads) and
[ADR 0003](../adr/0003-opt-in-framework-enforcement-adapters.md).

## Mode

Compact.

## Problem

`software-design-principles` keeps short rules in `SKILL.md` and the reasoning
behind them in nine reference files. Rules cite section ids such as
`#design-twice`, and the reasoning is meant to be read at the moment it
applies: before changing code, while writing it, and before reporting done.

In real use only one reference is ever read. Across the skill-usage mod's
store, 39 sessions loaded the skill and every one of the 32 reference reads was
`references/red-flags.md`. Across session transcripts, 47 sessions loaded it
and 43 read a reference, again only `red-flags.md`. The other eight files had
no reads at all. `red-flags.md` is read because it is the one file `SKILL.md`
names unconditionally and the adapter's closeout Design item requires.

The causes:

- The rules are complete one-liners, and the workflow says to read a reference
  "only when you need the reasoning", a need an agent rarely feels.
- A section id names no file; finding it takes a lookup in the index table that
  nothing prompts.
- Most loads (40 of 52 in the store) come from the adapter's pre-edit `design`
  hold, at the first substantial edit, when the "before" moment has passed.
- Skills that cite this one (`tdd`, `design-codebase-architecture`,
  `review-codebase-architecture`, `writing-plans`, `code-refinement`) cite bare
  ids.
- Reading is not applying. Real use showed `red-flags.md` read and then judged
  from memory instead of the diff (fixed by Ticket 041's change read). The
  maintainer's experience is that written instructions alone are not followed
  reliably, so the reads must be enforced where the adapter is installed.

Separately, the maintainer keeps a reader-first commenting standard in personal
instructions. It asks for more comments than the skill's default ("inside
functions, comment only intent and surprises"), and once `readability.md` is
read more often the two will conflict more often.

## Goals

- Each reference is read at the moment it serves, in sessions that change code
  with the skill loaded.
- A read reference visibly shapes the work: the reply cites a section id from
  it and says how it applied.
- The cost stays bounded: a reference is required at most once per context
  window.
- The skill alone, without the adapter, tells the agent which file to read at
  which moment.
- The mod shows when each reference is read relative to the code changes, so
  signals can be tuned from data.

## Non-Goals

- Changing Ticket 041's change read or the closeout's `red-flags.md` read.
- Reorganising the references by moment, or merging them into `SKILL.md`.
- Judging citation quality. The adapter checks that an id is cited, not that
  the reasoning is good.
- Changing the maintainer's personal instruction files.
- Changing the skill's default comment density for everyone.

## Requirements

### R1: Moment triggers in `SKILL.md`

Each moment in the Rules ("Before changing code", "While writing code",
"Before reporting the work as done") lists the references to read now, each as
a condition and a file. Every reference is linked to at least one moment.
`differences.md` is linked to its condition, two rules pulling apart, at any
moment. The section index gains a "Read when" column. The workflow step that
says to read a reference only when the reasoning is needed is replaced by the
triggers. Rule citations name the file, as `file#id` or a link, so a citation
is a pointer. `SKILL.md` stays under its 300-line soft cap.

### R2: Portable declaration and citation contract

`SKILL.md` defines two portable conventions that work without any adapter:

- **Design-reads line.** At the start of design work in a turn, the agent
  writes, on its own line, `goated-design-reads: <file>, <file>` naming the
  references its triggers select. For a change with no design in it, it writes
  `goated-design-reads: none: <reason>`. It writes the line again when the work
  changes.
- **Citations.** The reply that reports the work cites at least one section id
  from each reference read for it, saying how it shaped the change or why it
  did not apply.

### R3: Citing skills point at files

Skills that cite this skill's section ids (`tdd`,
`design-codebase-architecture`, `review-codebase-architecture`,
`writing-plans`, `code-refinement`) name the reference file with the id.
Without this skill installed, each keeps its own fallback.

### R4: Reader-first comment profile

`readability.md` gains an opt-in section, `#reader-first-comments`, holding a
denser, beginner-friendly commenting standard: a short docstring on every
function, method, class, and type; comments on non-obvious fields, state
variables, and unfamiliar calls; a comment opening each step of a long
function; plain words; reasons stated only when confirmed in the code. Its
example is neutral, not taken from any private project. It applies when a user
or project asks for it, or when the code's readers are beginner-to-intermediate
programmers. Rule 12 and the "How many comments" row in `differences.md` name
it. The default stays as it is for everyone else.

### R5: Adapter: references read at their moment

In the Claude Code adapter, where the skill is loaded and a code change
qualifies:

- **Required set.** The references required for a change are the ones the
  agent's design-reads line declares plus the ones the adapter detects:

  | Reference | Detected when |
  | --- | --- |
  | `process.md` | a new code file, or a new top-level definition in added lines (`def`, `class`, `function`, `export`, `func`, `fn`, `public`, and the like) |
  | `complexity-and-modules.md` | the same signals as `process.md` |
  | `decoupling.md` | a configuration file is edited (`.yaml`, `.toml`, `.json`, `.env`, `settings.*`), or the turn has edited three or more code files |
  | `readability.md` | added lines contain a comment or docstring, or a new top-level definition |
  | `errors.md` | added lines contain error-handling tokens (`try`, `except`, `catch`, `raise`, `throw`, `finally`, `with open`, `defer`) |
  | `coding.md` | a test file is edited |
  | `concurrency.md` | added lines contain concurrency tokens (`threading`, `Lock`, `Mutex`, `asyncio`, `Promise.all`, `synchronized`, `Atomic`, `go func`) |
  | `differences.md` | never detected; declaration only |

  `red-flags.md` stays with the closeout and is not part of this set.
- **Pre-edit.** The existing `design` hold, which fires on the first
  substantial code edit of a turn, also needs the design-reads line in the turn
  and a read of every required reference.
- **Mid-turn.** A later code edit whose signals require a reference not yet
  read is held by a new `design-reads` hold, `justified-skip`, naming the file
  and the signal that selected it.
- **Cooldown.** A reference read counts for the rest of the session until the
  next compaction. After a compaction it is required again. A reference is
  never required twice in one context window.
- **Escape.** A skip line (`goated-skip: software-design-principles: <reason>`)
  and the existing overrides clear these holds as they clear `design`.
- **Out of the project.** These holds follow the `design` gate's rules for
  files outside the project.

### R6: Adapter: citations at closeout

The closeout Design item also needs, in the turn's text, at least one section
id from each reference in the turn's required set. A missing citation names
the reference. A cited id with a reason it did not apply satisfies it. The
adapter takes each file's ids from the skill's own files, not from a copy. The
`red-flags.md` read and the change read stay as they are.

### R7: Mod: when each reference is read

The skill-usage mod records each reference read with its moment in the turn:
before the turn's first code change, between code changes, or after the last.
It shows per-reference counts by moment. Its view of holds includes
`design-reads`, and it records design-reads lines, including `none`
declarations.

## Acceptance Criteria

- [ ] AC1: `SKILL.md` names, for each moment, the references to read and their
      conditions; every reference is linked to at least one moment; the file
      stays under 300 lines and the validator passes.
- [ ] AC2: `SKILL.md` defines the design-reads line and the citation
      convention, and both make sense with no adapter installed.
- [ ] AC3: The citing skills name the reference file with each id they cite.
- [ ] AC4: `readability.md` holds `#reader-first-comments` with a neutral
      example; rule 12 and `differences.md` name it; the default is unchanged.
- [ ] AC5: With the adapter, a first substantial edit with no design-reads line,
      or with an unread required reference, is held; with both, it passes. A
      detected reference already read since the last compaction is not
      required again; after a compaction it is.
- [ ] AC6: A later edit that trips a signal for an unread reference is held by
      `design-reads`; an edit that trips none, or only read ones, is not.
- [ ] AC7: The closeout Design item holds when a required reference has no
      cited id in the turn's text and clears when each has one.
- [ ] AC8: The mod shows reference reads by moment and the `design-reads`
      hold, and records design-reads declarations.
- [ ] AC9: In the maintainer's next stretch of real use after AC5 to AC8, the
      mod shows reads of references other than `red-flags.md`, most before or
      between code changes. The maintainer judges whether any signal is too
      noisy and tunes or removes it.

## Proof Surface

The skill files and the repo validator for AC1 to AC4; the adapter's tests and
hold texts for AC5 to AC7; the mod's tests and pane for AC8; the mod's store in
real use for AC9.

## Constraints

- ADR 0003: the skill must work without the adapter; the adapter enforces the
  skill's portable contract, and no skill depends on it.
- The adapter work edits the same files and hold texts as Tickets 047 and 042
  to 046 and needs 046's compaction handling, so it runs after 046 and before
  Ticket 035. The mod work edits the mod after 047.
- Public boundary: no private project names, transcript content, or personal
  context in tracked files; only counts from the store and transcripts.
- `SKILL.md` soft cap of 300 lines; references linked directly from it.

## Risks

- **Loose signals.** The comment signal fires on most edits, which makes
  `readability.md` an effective once-per-window read; others may fire on near
  misses. Mitigation: the cooldown, a cite-and-dismiss answer, and AC9's
  tuning.
- **Context cost.** All eight references once per context window are about
  1,300 lines. Mitigation: the cooldown caps it; most turns need fewer.
- **Box-ticking citations.** An id can be cited without real use. Mitigation:
  the citation must say how it applied; the maintainer samples in AC9.
- **Under-declaring.** The agent can declare `none`. Mitigation: detection
  still adds its files; the mod counts `none` declarations.

## Sources

- `skills/engineering/software-design-principles/SKILL.md`: rules, workflow
  step 3, section index.
- `skills/engineering/software-design-principles/references/`: each file's
  "Read this when" opening.
- `adapters/claude-code/goated_adapter/actions.py` and
  `adapters/claude-code/README.md`: the `design` hold and the closeout Design
  item.
- `tickets/skill-enforcement-adapter-order.md` and
  `tickets/adapter-skill-activation-gates-order.md`: queued adapter work.
- The skill-usage mod's store and session transcripts: counts only.
