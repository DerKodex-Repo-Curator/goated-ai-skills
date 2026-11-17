// Turns conversation content into neutral events (live rows and the history a
// late-loading mod reads go through the same rules), then labels why each skill
// loaded; whether hook nudges were followed is `holds.ts`'s, which `summarize`
// feeds. Pure: no engine calls, so tests can feed it events and messages.
//
// The hook text read is the GOATED Claude Code adapter's: its holds start
// `goated-hold: <gate> | <kind>` (adapters/claude-code/README.md in the GOATED
// repo), and `OVERRIDE_NOTICE` matches its override sentence.

import type {
  AllTime,
  CloseoutItem,
  Counts,
  DesignReadCounts,
  DesignReads,
  EarlierHolds,
  HoldKind,
  Measures,
  Origin,
  Outcome,
  RefMoment,
  RefMoments,
  Refs,
  Route,
  SessionSummary,
  SideSessionKind,
  SkipReasons,
  SubagentCounts,
  TimelineEntry,
  UsageEvent,
  WritingTurns,
} from '../types'
import { bump, holdSettlement, ROUTE_LINE, stamp, storedReason } from './holds'

export const ROUTER = 'using-goated-ai-skills'
export { ROUTE_LINE }
/**
 * The version of the data this mod records: each summary is stamped with it, and the events atom's shape tag is
 * `events-<version>`, so a change to what is recorded bumps both. 4: Ticket 076 added routed skills, side sessions, the
 * project key and the stamp itself; earlier versions, which stored no stamp, were 1 to 3.
 */
export const DATA_VERSION = 4
/**
 * The first data version whose holds count as current. Summaries stamped earlier, or not at all, keep their holds apart
 * under earlier versions, since their gates may carry names the adapter has since retired, such as `design-hold`.
 */
const CURRENT_HOLDS_SINCE = 4
const isEarlierVersion = (summary: SessionSummary) => (summary.version ?? 0) < CURRENT_HOLDS_SINCE
/** Subagent counts before any subagent did anything. */
export const NO_SUBAGENTS: Readonly<SubagentCounts> = { spawns: 0, starts: 0, bodyReads: 0 }
/** Writing-turn counts before any turn wrote. */
export const NO_WRITING_TURNS: Readonly<WritingTurns> = { routed: 0, late: 0, none: 0 }
/** Design-reads counts before any line was written, each a fresh object to add into. */
const noDesignReads = (): DesignReadCounts => ({ files: {}, none: 0 })

export const ORIGINS: readonly Origin[] = ['user-slash', 'user-named', 'hook-nudged', 'router-routed', 'self-initiated', 'subagent']
export const OUTCOMES: readonly Outcome[] = ['followed', 'read files', 'already loaded', 'declined', 'overridden', 'new prompt', 'unanswered', 'ignored', 'pending']

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

/** Skills mentioned by name in free text, backticked, slashed or as a whole word. */
export function skillsNamed(text: string, skills: readonly string[]): string[] {
  return skills.filter(s => new RegExp(`(?<![\\w-])/?${escape(s)}(?![\\w-])`).test(text))
}

// A path from a skills folder on (absolute, or relative such as `skills/x/...`), up to whitespace, a quote or shell punctuation.
const SKILL_PATH = /(?<![\w.-])skills[\\/]([^\s"'`|;&<>()]+)/g
// Folders a skill keeps its supporting files in; the folder above one is the skill.
const SUPPORT_DIRS = new Set(['references', 'reference', 'scripts', 'templates', 'assets', 'examples', 'docs'])
const isSkillMd = (name: string | undefined) => name?.toUpperCase() === 'SKILL.MD'

/**
 * Every path into a skill folder that a file path or shell command names, as
 * the skill and the parts below it. The one place that decides which skill a
 * path belongs to: the folder holding a SKILL.md or a supporting folder, so a
 * category folder above the skill (`skills/<category>/<skill>/…`) is not taken
 * for it; otherwise the first folder under `skills`.
 */
function skillPaths(text: string): { skill: string; below: string[] }[] {
  return [...text.matchAll(SKILL_PATH)].flatMap(m => {
    const parts = (m[1] ?? '').split(/[\\/]/).filter(Boolean)
    const support = parts.findIndex((p, i) => i > 0 && SUPPORT_DIRS.has(p))
    const at = isSkillMd(parts.at(-1)) && parts.length > 1 ? parts.length - 2 : support > 0 ? support - 1 : 0
    const skill = parts[at] ?? ''
    // A file beside the skill folders, such as skills/README.md, belongs to no skill.
    return /^[\w-]+$/.test(skill) ? [{ skill, below: parts.slice(at + 1) }] : []
  })
}

/** Skill folders a file path or shell command reaches into: a SKILL.md, a folder or a supporting file. */
export function skillsInPath(text: string): string[] {
  return [...new Set(skillPaths(text).map(p => p.skill))]
}

/**
 * The supporting files of skills a file path or shell command reads, each as
 * its skill and its path within the skill (`references/x.md`). A skill's own
 * SKILL.md, a folder and a glob are not reads of a supporting file.
 */
export function skillFiles(text: string): { skill: string; file: string }[] {
  const found = new Map<string, { skill: string; file: string }>()
  for (const { skill, below } of skillPaths(text)) {
    const file = below.join('/')
    const name = below.at(-1) ?? ''
    if (!file || /[*?]/.test(file) || !/\.\w+$/.test(name) || isSkillMd(name)) continue
    found.set(`${skill}/${file}`, { skill, file })
  }
  return [...found.values()]
}

/** Skills whose SKILL.md, the skill's body, a file path or shell command names. */
function skillBodies(text: string): string[] {
  return [...new Set(skillPaths(text).flatMap(p => (p.below.length === 1 && isSkillMd(p.below[0]) ? [p.skill] : [])))]
}

// The hold line, exactly as adapters/claude-code/README.md ("Hold messages") documents it.
const ADAPTER_HOLD = /^goated-hold: ([a-z]+(?:-[a-z]+)*) \| (strict|justified-skip)$/
// How Claude Code wraps a hold's reason (2.1.325): a denied call's errored result starts `PreToolUse:<Tool> hook error: `,
// and a blocked Stop arrives, live and in history alike, as a reminder whose first line is this sentence.
const CALL_HELD = /^\S+ hook error: /
const STOP_BLOCKED = /^Stop hook blocking error from command: ".*": (goated-hold: .*)$/
const BACKTICKED_SKILL = /`([a-z0-9]+(?:-[a-z0-9]+)*)`/g
// The design references a design hold asks to read, each backticked by its path, and the design-reads line it asks for.
const DESIGN_REFERENCE = /`software-design-principles\/references\/([a-z0-9]+(?:-[a-z0-9]+)*\.md)`/g
const ASKS_DESIGN_LINE = /`goated-design-reads: /
// The skill references a reference-reads hold asks to read, each backticked by its path under the skill.
const SKILL_REFERENCE = /`([a-z0-9]+(?:-[a-z0-9]+)*\/references\/[a-z0-9]+(?:-[a-z0-9]+)*\.md)`/g
// The skip line a justified-skip hold offers, backticked whole: its skill is asked for too, as for the closeout's proof item.
const OFFERED_SKIP = /`goated-skip: ([a-z0-9]+(?:-[a-z0-9]+)*): /g
// A closeout item's line, `- <Label>: <what it asks>`, whose label the adapter keeps stable (adapters/claude-code/README.md).
const CLOSEOUT_ITEM = /^- ([A-Z][A-Za-z ]*): (.*)$/
/** The grammar's own words, which adapters before Ticket 034 backticked in hold texts; they are no skills. */
const MARKER_WORDS = new Set(['goated-hold', 'goated-route', 'goated-skip'])
/**
 * What an adapter hold asks for: the router, a route line, or every skill its
 * text backticks, alone or as the skill of a skip line it offers, in the order
 * they appear. The adapter backticks only skill names and whole marker lines,
 * so the names are taken as they stand, whether or not the session's skill
 * listing has loaded.
 */
function adapterHoldNamed(gate: string, body: string): { named: string[]; skipOnly: string[]; refs?: string[]; needsLine?: true; items?: CloseoutItem[] } {
  if (gate === 'router-first') return { named: [ROUTER], skipOnly: [] }
  if (gate === 'route-line') return { named: [ROUTE_LINE], skipOnly: [] }
  if (gate === 'closeout') {
    const items = itemsListed(body)
    if (items.length > 0) return { ...namedIn(gate, body), items }
  }
  return namedIn(gate, body)
}

/**
 * The items a closeout hold's text lists, each with the skill its line names: the first it backticks, else the skill of
 * the skip line it offers. An item listed twice under one label and skill, such as the two design items, is one.
 */
function itemsListed(body: string): CloseoutItem[] {
  const items: CloseoutItem[] = []
  for (const line of body.split(/\r?\n/)) {
    const item = CLOSEOUT_ITEM.exec(line)
    if (!item) continue
    const label = item[1] ?? ''
    const { named } = namedIn('closeout', item[2] ?? '')
    const skill = named[0]
    if (skill && !items.some(i => i.label === label && i.skill === skill)) items.push({ label, skill })
  }
  return items
}

/** What a hold's text asks for by the skills it backticks, alone or in an offered skip line, and the design reads. */
function namedIn(gate: string, body: string): { named: string[]; skipOnly: string[]; refs?: string[]; needsLine?: true } {
  // Only the design gates, by file name, and the reference-reads gate, by path under the skill, ask for reference
  // reads; the closeout's red-flags path is another kind of ask.
  const asked = gate === 'reference-reads' ? SKILL_REFERENCE : gate === 'design' || gate === 'design-reads' ? DESIGN_REFERENCE : null
  const refs = asked ? [...body.matchAll(asked)].flatMap(m => (m[1] ? [m[1]] : [])) : []
  const design = { ...(refs.length > 0 ? { refs } : {}), ...(ASKS_DESIGN_LINE.test(body) ? { needsLine: true as const } : {}) }
  const names = (re: RegExp) => [...body.matchAll(re)].flatMap(m => (m[1] && !MARKER_WORDS.has(m[1]) ? [{ skill: m[1], at: m.index ?? 0 }] : []))
  const loads = names(BACKTICKED_SKILL)
  const named = [...new Set([...loads, ...names(OFFERED_SKIP)].sort((a, b) => a.at - b.at).map(n => n.skill))]
  // A skill offered only as a skip line asks for something no load gives: a check run for the closeout's proof item,
  // a read of the red-flags file for its design item.
  return { named, skipOnly: named.filter(skill => !loads.some(n => n.skill === skill)), ...design }
}

/**
 * The adapter hold a piece of hook output carries, unwrapped from Claude
 * Code's wrapper: the first line of an errored tool result (`isErrorResult`),
 * or the reason of a blocked Stop. A hold line anywhere else, such as in a
 * failing command's output or another hook's context, is not one.
 */
function adapterHold(text: string, isErrorResult: boolean): { gate: string; kind: HoldKind; body: string; isStop: boolean } | null {
  let lines = text.trimStart().split(/\r?\n/)
  if (!isErrorResult) {
    if (lines[0]?.trim() !== '<system-reminder>') return null
    lines = lines.slice(1)
  }
  const first = (lines[0] ?? '').trim()
  const reason = isErrorResult ? first.replace(CALL_HELD, '') : STOP_BLOCKED.exec(first)?.[1]
  const hold = reason === undefined ? null : ADAPTER_HOLD.exec(reason)
  return hold ? { gate: hold[1] ?? '', kind: hold[2] as HoldKind, body: lines.slice(1).join('\n'), isStop: !isErrorResult } : null
}

/**
 * The adapter hold in one piece of hook output, as a nudge with the skills it
 * names; none when the output carries no hold. Its `hook` is its gate;
 * `isStop`: it held a `Stop`, not a call; `skipOnly`: the named skills it
 * offers only as a skip line, which no load answers; `refs` and `needsLine`:
 * the design references and design-reads line a design hold asks for, or the
 * skill references a reference-reads hold asks for, by path under the skill.
 * `holdsOnly`: the text is an errored tool result.
 */
export function hookNudges(text: string, holdsOnly = false): { hook: string; named: string[]; holdKind: HoldKind; isStop?: true; skipOnly?: string[]; refs?: string[]; needsLine?: true; items?: CloseoutItem[] }[] {
  const hold = adapterHold(text, holdsOnly)
  if (!hold) return []
  const { named, skipOnly, ...design } = adapterHoldNamed(hold.gate, hold.body)
  return [{ hook: hold.gate, named, holdKind: hold.kind, ...(hold.isStop ? { isStop: true as const } : {}), ...(skipOnly.length > 0 ? { skipOnly } : {}), ...design }]
}

/**
 * The events of one piece of hook output: a nudge for the adapter hold it
 * carries, if any. `agent`: the subagent the hook spoke to; `holdsOnly`: the
 * text is an errored tool result.
 */
export function hookEvents(text: string, t: number, opts: { agent?: string; holdsOnly?: boolean } = {}): UsageEvent[] {
  const ofAgent = opts.agent ? { agent: opts.agent } : {}
  return hookNudges(text, opts.holdsOnly).map((n): UsageEvent => ({ kind: 'nudge', t, ...n, ...(opts.agent ? { isSubagent: true as const } : {}), ...ofAgent }))
}

// The adapter's sentence when it records overrides you typed, each phrase quoted; its other notices share the prefix.
// The notice row itself reaches a mod with no text, so the sentence is read wherever hook context carries it.
const OVERRIDE_NOTICE = /GOATED Claude Code adapter: recorded your override for this prompt: ((?:"[^"]*"(?:, )?)+)/

/** The overrides an adapter sentence in hook output says it recorded, as one event; none for any other text. */
export function overrideEvents(text: string, t: number): UsageEvent[] {
  const quoted = OVERRIDE_NOTICE.exec(text)?.[1]
  if (!quoted) return []
  const phrases = [...quoted.matchAll(/"([^"]*)"/g)].flatMap(m => (m[1] ? [m[1].toLowerCase()] : []))
  return phrases.length > 0 ? [{ kind: 'override', t, phrases }] : []
}

/** A skill's bare name: `plugin:skill` and `skill` are the same skill. */
export const short = (skill: string) => skill.split(':').pop() ?? skill

/**
 * The events of one message the person sent: a prompt, plus a skill load when
 * it is a slash command naming a skill. Any other slash command, such as
 * /compact or this mod's own /skill-usage, runs in Claude Code without a
 * model turn, so it is no prompt, and neither is its output.
 */
export function promptEvents(text: string, skills: readonly string[], t: number): UsageEvent[] {
  if (text.trimStart().startsWith('<local-command-')) return []
  const command = /<command-name>\/?([\w:.-]+)<\/command-name>/.exec(text)?.[1]
  if (!command) return [{ kind: 'prompt', t, named: skillsNamed(text, skills), isTimed: true }]
  if (!skills.includes(short(command))) return []
  return [
    { kind: 'prompt', t, named: [], isTimed: true },
    { kind: 'load', t, skill: short(command), via: 'slash', isSubagent: false },
  ]
}

/** The skill a Skill call names, as the adapter reads it: `/tdd write the test` is `tdd`, and `plugin:tdd` is `tdd`. */
const skillArgument = (value: unknown) => short(String(value ?? '').trim().replace(/^\/+/, '').split(/\s+/)[0] ?? '')

// The tools that start a subagent; `Task` is the Agent tool's older name.
const SPAWN_TOOLS = new Set(['Agent', 'Task'])
// The tools that start a side session, as the adapter names them (`SPAWN_TOOLS` in goated_adapter/gates.py).
const START_SESSION = 'mcp__ccd_session__start_session'
const HAND_OFF = 'mcp__ccd_session__hand_off_to_session'
// What the adapter holds like a write (adapters/claude-code/README.md): edits, and spawns, which hand work on.
const WRITE_TOOLS = new Set(['Edit', 'Write', 'MultiEdit', 'NotebookEdit', ...SPAWN_TOOLS, START_SESSION, HAND_OFF])
// The `initiation` values of a `start_session` call that only shows a card, unless it starts a saved proposal
// (`proposal_id`): the adapter's `CARD_INITIATIONS`.
const CARD_INITIATIONS = new Set(['offer', 'own_initiative'])

/** What a call to a session tool does, as the adapter's `shows_a_card` judges it: shows a card, or starts a session; null for any other tool. */
function sideSessionKind(name: string, input: Record<string, unknown>): SideSessionKind | null {
  if (name === HAND_OFF) return 'start'
  if (name !== START_SESSION) return null
  const initiation = input.initiation
  return typeof initiation === 'string' && CARD_INITIATIONS.has(initiation) && input.proposal_id == null ? 'card' : 'start'
}

// What the adapter counts as a code file, by extension: its `CODE_EXTENSIONS` (goated_adapter/actions.py), copied
// here because the mod cannot import it. tests/test_skill_usage_mod.py fails when the two lists differ.
const CODE_EXTENSIONS = new Set(
  '.py .js .jsx .ts .tsx .mjs .cjs .go .rs .java .kt .kts .swift .c .h .cpp .hpp .cc .cs .rb .php .scala .ps1 .psm1 .sh .bash .lua .dart .vue .svelte .sql .ex .exs .clj .fs .zig .r .jl .ipynb'.split(' '),
)
// The edit tools and the input naming the file each changes: the adapter's `FILE_WRITE_TOOLS`.
const FILE_EDIT_TOOLS: Record<string, string> = { Edit: 'file_path', Write: 'file_path', MultiEdit: 'file_path', NotebookEdit: 'notebook_path' }

/** Whether a path names a code file, as the adapter's `is_code` judges it: by the extension of its last part. */
function isCodeFile(path: string): boolean {
  const p = path.replace(/\\/g, '/')
  const dot = p.lastIndexOf('.')
  return dot > p.lastIndexOf('/') && CODE_EXTENSIONS.has(p.slice(dot).toLowerCase())
}

/**
 * The one input field of each built-in tool that may carry route and skip
 * lines: one that describes the call rather than holds its payload, which
 * Claude Code keeps as written even when it saves the reply's text as a
 * summary that drops the lines. Other tools, MCP tools included, carry none,
 * since their `description` is often the payload, such as an issue body. The
 * adapter keeps the same table (`LINE_FIELDS` in goated_adapter/transcript.py).
 */
const LINE_FIELDS: Readonly<Record<string, string>> = { Bash: 'description', PowerShell: 'description', Agent: 'description', Task: 'description', Skill: 'args' }

/** The text of a tool call that may carry route and skip lines, or ''. */
function callLineText(name: string, input: Record<string, unknown>): string {
  const field = Object.hasOwn(LINE_FIELDS, name) ? LINE_FIELDS[name] : undefined
  const value = field ? input[field] : undefined
  return typeof value === 'string' ? value : ''
}

/**
 * The events of one assistant message's tool calls: the route and skip lines
 * each call carries, before that call's own events; skill loads, subagent
 * spawns, writes, code changes, reads into a skill's folder, reads of a
 * skill's supporting files. A subagent's calls count only as its own lines,
 * skill loads, spawns, code changes, supporting-file reads and reads of a
 * SKILL.md (`body`); `agent` names that subagent.
 */
export function toolUseEvents(
  uses: readonly { id?: string; name: string; input: Record<string, unknown> }[],
  isSubagent: boolean,
  t: number,
  agent?: string,
): UsageEvent[] {
  const events: UsageEvent[] = []
  const ofAgent = isSubagent && agent ? { agent } : {}
  for (const { id, name, input } of uses) {
    const ofCall = id ? { id } : {}
    events.push(...markerEvents(callLineText(name, input), t, isSubagent ? agent : undefined))
    if (name === 'Skill') {
      events.push({ kind: 'load', t, ...ofCall, skill: skillArgument(input.skill), via: 'tool', isSubagent })
      continue
    }
    if (SPAWN_TOOLS.has(name)) {
      const spawn = { agentType: String(input.subagent_type || 'general-purpose'), description: String(input.description ?? '') }
      events.push({ kind: 'spawn', t, ...ofCall, ...spawn, ...(isSubagent ? { isSubagent: true as const } : {}), ...ofAgent })
    }
    const edited = FILE_EDIT_TOOLS[name]
    if (edited && isCodeFile(String(input[edited] ?? ''))) events.push({ kind: 'change', t, ...ofCall, ...(isSubagent ? { isSubagent: true as const } : {}) })
    const target = String((name === 'Read' ? input.file_path : input.command) ?? '')
    const refs: UsageEvent[] = skillFiles(target).map(f => ({ kind: 'ref', t, ...f, ...(name === 'Read' ? { isReadTool: true as const } : {}), ...(isSubagent ? { isSubagent: true as const } : {}) }))
    if (isSubagent) {
      for (const skill of skillBodies(target)) events.push({ kind: 'body', t, skill, isSubagent: true, ...ofAgent })
      events.push(...refs)
      continue
    }
    const reached = skillsInPath(target)
    if (reached.length > 0) events.push({ kind: 'read', t, skills: reached })
    events.push(...refs)
    if (WRITE_TOOLS.has(name)) events.push({ kind: 'write', t, ...ofCall })
    const shows = sideSessionKind(name, input)
    if (shows) events.push({ kind: 'side-session', t, ...ofCall, tool: name, shows })
  }
  return events
}

// The GOATED marker grammar: stack/fixtures/markers/README.md in the GOATED repo, whose lines.yaml the tests read.
const SKILL = '[a-z0-9]+(?:-[a-z0-9]+)*'
const ROUTE_RE = new RegExp(`^goated-route:[ \\t]+(?:(direct|continue)|(lightweight|standard|full)[ \\t]+\\|[ \\t]+requires:[ \\t]+(${SKILL}(?:[ \\t]*,[ \\t]*${SKILL})*))$`)
const SKIP_RE = new RegExp(`^goated-skip:[ \\t]+(${SKILL}):[ \\t]+(\\S.*)$`)
const FILE = `${SKILL}\\.md`
const DESIGN_READS_RE = new RegExp(`^goated-design-reads:[ \\t]+(?:none:[ \\t]+(\\S.*)|(${FILE}(?:[ \\t]*,[ \\t]*${FILE})*))$`)
// A candidate marker line, compared case-insensitively: one that fails the grammar is malformed.
const MARKER_PREFIX = /^goated-(route|skip|design-reads):/i
const FENCE = /^(```|~~~)/
/** The grammar's floor for a reason: at least three words. */
const MIN_REASON_WORDS = 3
const isReason = (reason: string) => reason.split(/\s+/).length >= MIN_REASON_WORDS

type Skip = { skill: string; reason: string }

// The line breaks Python's `str.splitlines` splits on, so the mod cuts a reply into lines as the repo's readers do.
const LINE_BREAK = /\r\n|[\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029]/

/**
 * A stripped line unwrapped from one pair of enclosing single backticks, then
 * stripped again: `candidate_line` in the repo's Python marker readers.
 */
function candidateLine(trimmed: string): string {
  return trimmed.length > 2 && trimmed.startsWith('`') && trimmed.endsWith('`') && trimmed[1] !== '`' ? trimmed.slice(1, -1).trim() : trimmed
}

function readRoute(line: string): Route | null {
  const m = ROUTE_RE.exec(line)
  if (!m) return null
  if (m[1]) return { form: m[1] as 'direct' | 'continue' }
  const requires = (m[3] ?? '').split(',').map(s => s.trim())
  if (new Set(requires).size !== requires.length) return null
  return { form: 'route', intensity: m[2] as 'lightweight' | 'standard' | 'full', requires }
}

function readSkip(line: string): Skip | null {
  const m = SKIP_RE.exec(line)
  const reason = m?.[2]?.trim() ?? ''
  if (!m?.[1] || !isReason(reason)) return null
  return { skill: m[1], reason }
}

function readDesignReads(line: string): DesignReads | null {
  const m = DESIGN_READS_RE.exec(line)
  if (!m) return null
  if (m[2]) {
    const files = m[2].split(',').map(s => s.trim())
    return new Set(files).size === files.length ? { form: 'files', files } : null
  }
  const reason = m[1]?.trim() ?? ''
  return isReason(reason) ? { form: 'none', reason } : null
}

/**
 * The marker lines of one reply, as the grammar reads them: the winning route
 * (the last valid route line), every skip line, every design-reads line, and
 * each candidate line that starts like a marker but fails the grammar. Only
 * whole lines outside fenced code count, each unwrapped from at most one pair
 * of backticks.
 */
export function markerLines(text: string): { route: Route | null; skips: Skip[]; designReads: DesignReads[]; malformed: string[] } {
  let route: Route | null = null
  const skips: Skip[] = []
  const designReads: DesignReads[] = []
  const malformed: string[] = []
  let isInFence = false
  for (const raw of text.split(LINE_BREAK)) {
    const trimmed = raw.trim()
    if (FENCE.test(trimmed)) {
      isInFence = !isInFence
      continue
    }
    if (isInFence) continue
    const line = candidateLine(trimmed)
    const kind = MARKER_PREFIX.exec(line)?.[1]?.toLowerCase()
    if (kind === 'route') {
      const found = readRoute(line)
      if (found) route = found
      else malformed.push(line)
    } else if (kind === 'skip') {
      const found = readSkip(line)
      if (found) skips.push(found)
      else malformed.push(line)
    } else if (kind === 'design-reads') {
      const found = readDesignReads(line)
      if (found) designReads.push(found)
      else malformed.push(line)
    }
  }
  return { route, skips, designReads, malformed }
}

/**
 * The marker events of one reply: its winning route, then each skip line, then
 * its design-reads lines as one event, declaring the union of their files (a
 * later line adds files and never removes any). `agent`: the subagent that
 * wrote it.
 */
export function markerEvents(text: string, t: number, agent?: string): UsageEvent[] {
  const { route, skips, designReads } = markerLines(text)
  const loop = agent ? { isSubagent: true as const, agent } : {}
  const files = [...new Set(designReads.flatMap(d => (d.form === 'files' ? d.files : [])))]
  const noneReasons = designReads.flatMap(d => (d.form === 'none' ? [d.reason] : []))
  return [
    ...(route ? [{ kind: 'route' as const, t, ...route, ...loop }] : []),
    // A reason is kept masked and cut, here where it enters the stored events, so no fuller text is kept anywhere.
    ...skips.map(k => ({ kind: 'skip' as const, t, skill: k.skill, reason: storedReason(k.reason), ...loop })),
    ...(designReads.length > 0 ? [{ kind: 'design-reads' as const, t, files, noneReasons, ...loop }] : []),
  ]
}

/** A message of the main conversation in Messages API form, as `$.session.messages({ as: 'api' })` gives it. */
export type HistoryMessage = { role: 'user' | 'assistant'; content: readonly { type: string; [field: string]: unknown }[] }

// In history, hook output arrives as reminder text such as "SessionStart hook
// additional context: …" or "Stop hook feedback: …"; holds as errored tool results.
const HOOK_TEXT = /\bhook (additional context|feedback|blocking error)\b/i
// Text the person did not type: reminders, skill bodies, notices and the like.
const NOT_TYPED = /^(<|Base directory for this skill|\(Re-invocation of|Another Claude session|\[Request interrupted|\[Image)/
const COMPACT_SUMMARY = /^This session is being continued from a previous conversation/

/** The text of a message's content, whether a string or blocks, nested tool results included. */
export function textOf(content: unknown): string {
  if (typeof content === 'string') return content
  if (!Array.isArray(content)) return ''
  return content.map(b => (b && typeof b === 'object' ? textOf((b as { text?: unknown }).text ?? (b as { content?: unknown }).content) : '')).join('\n')
}

/**
 * Rebuilds a session's events from its history, for a mod that loaded after
 * the session began. History carries no times, so every event takes `t` and
 * is marked `isEarlier`. Within a user message the prompt comes first, so the
 * hook output a prompt triggers counts as part of its turn, as it does live.
 */
export function historyEvents(messages: readonly HistoryMessage[], skills: readonly string[], t: number): UsageEvent[] {
  const events: UsageEvent[] = []
  let lastBoundary: 'response' | 'results' | undefined
  for (const message of messages) {
    if (message.role === 'assistant') {
      const uses = toolUses(message.content)
      const add = toolUseEvents(uses, false, t)
      if (lastBoundary !== 'response') events.push({ kind: 'response', t })
      lastBoundary = 'response'
      events.push(...markerEvents(textOf(message.content.filter(b => b.type === 'text')), t), ...add)
      continue
    }
    const opening: UsageEvent[] = []
    const after: UsageEvent[] = []
    for (const b of message.content) {
      if (b.type === 'tool_result') {
        if (b.is_error) after.push(...refusalEvents(b, t))
        continue
      }
      if (b.type !== 'text') continue
      const text = String(b.text ?? '').trim()
      if (HOOK_TEXT.test(text)) after.push(...hookEvents(text, t))
      else if (COMPACT_SUMMARY.test(text)) opening.push({ kind: 'compact', t })
      else if (text.includes('<command-name>') || (text && !NOT_TYPED.test(text))) {
        // A message can hold several typed blocks; it is still one prompt.
        if (!opening.some(e => e.kind === 'prompt')) opening.push(...promptEvents(text, skills, t))
      }
    }
    events.push(...opening, ...after)
    const isAnswered = message.content.some(b => b.type === 'tool_result') || after.some(isStopHold)
    if (isAnswered && lastBoundary !== 'results') {
      events.push({ kind: 'results', t })
      lastBoundary = 'results'
    }
  }
  return events.map(e => ({ ...e, isEarlier: true as const }))
}

/** The tool calls in a reply's content blocks, each with its tool_use id. */
function toolUses(blocks: readonly { type: string; [field: string]: unknown }[]) {
  return blocks
    .filter(b => b.type === 'tool_use')
    .map(b => ({ ...(typeof b.id === 'string' ? { id: b.id } : {}), name: String(b.name), input: (b.input ?? {}) as Record<string, unknown> }))
}

/**
 * The events of one errored tool result: the holds its text carries, then the
 * refusal of its call, which did not run. `agent`: the subagent it belongs to.
 */
function refusalEvents(block: { [field: string]: unknown }, t: number, agent?: string): UsageEvent[] {
  const id = block.tool_use_id
  return [...hookEvents(textOf(block.content), t, { agent, holdsOnly: true }), ...(typeof id === 'string' ? [{ kind: 'refused' as const, t, id }] : [])]
}

/** Whether an event is an adapter hold on a `Stop`: the closeout's, which the reply after it answers. */
const isStopHold = (e: UsageEvent) => e.kind === 'nudge' && e.isStop === true

/** One conversation row as `session.append` carries it, as far as the mod reads it. */
export type Row = {
  door: string
  agentId?: string
  message: { type?: string; content: readonly { type: string; [field: string]: unknown }[]; name?: string; isMeta?: boolean }
}

// The attachment rows that carry hook output; other hook_* rows repeat it.
const HOOK_ATTACHMENTS = new Set(['hook_additional_context', 'hook_blocking_error'])
const OBSERVED_DOORS = new Set(['prompt', 'command', 'response', 'tool-result', 'compaction'])
const isHookRow = (row: Row) => row.door === 'hook-context' || (row.door === 'attachment' && HOOK_ATTACHMENTS.has(row.message.name ?? ''))

/** Whether a row can carry events at all. Every row of the conversation passes the mod, so the rest cost nothing. */
export const isObservedRow = (row: Row) => OBSERVED_DOORS.has(row.door) || isHookRow(row)

/**
 * The events of one conversation row: the person's prompts and slash
 * commands; a reply's route and skip lines, skill loads, spawns, writes and
 * skill-file reads; hook messages, holds and override sentences; and
 * compactions; and the main agent's round-trip boundaries. `seen`: the kind
 * of the session's last event, and its last round-trip boundary.
 *
 * Claude Code hands a mod one row per content block, with no id tying a
 * reply's rows together, so a reply's first row marks where it begins.
 *
 * A hook's notice to you (`hook_system_message`) comes in by the
 * `hook-context` door with no text (Claude Code 2.1.325), so it yields
 * nothing: the adapter's override sentence is read from its hook context.
 */
export function rowEvents(
  row: Row,
  skills: readonly string[],
  t: number,
  seen: { lastKind?: UsageEvent['kind']; lastBoundary?: 'response' | 'results' },
): UsageEvent[] {
  const isMain = !row.agentId
  const blocks = row.message.content
  // A local command's output comes in as a system row by the command door.
  if (row.door === 'prompt' || row.door === 'command') return isMain && !row.message.isMeta && row.message.type !== 'system' ? promptEvents(textOf(blocks), skills, t) : []
  if (row.door === 'response') {
    const uses = toolUses(blocks)
    const begins: UsageEvent[] = isMain && seen.lastBoundary !== 'response' ? [{ kind: 'response', t }] : []
    return [...begins, ...markerEvents(textOf(blocks.filter(b => b.type === 'text')), t, row.agentId), ...toolUseEvents(uses, !isMain, t, row.agentId)]
  }
  if (isHookRow(row)) {
    const text = textOf(blocks)
    const heard = hookEvents(text, t, { agent: row.agentId })
    // A blocked Stop hands the agent its reason as tool results do, so it ends the reply's round trip.
    const ends = isMain && heard.some(isStopHold) && seen.lastBoundary !== 'results' ? [{ kind: 'results' as const, t }] : []
    return [...heard, ...(isMain ? overrideEvents(text, t) : []), ...ends]
  }
  if (row.door === 'tool-result') {
    const refusals = blocks.flatMap(b => (b.type === 'tool_result' && b.is_error ? refusalEvents(b, t, row.agentId) : []))
    const isResult = isMain && blocks.some(b => b.type === 'tool_result')
    return [...refusals, ...(isResult && seen.lastBoundary !== 'results' ? [{ kind: 'results' as const, t }] : [])]
  }
  // A compaction appends a boundary and a summary: count it once.
  if (row.door === 'compaction' && isMain && seen.lastKind !== 'compact') return [{ kind: 'compact', t }]
  return []
}

/**
 * Folds a session's events into what loaded and why, what became of each
 * nudge, and a readable timeline. A nudge still open at the end is `pending`
 * while the session runs; once it has ended (`isFinal`) it was `unanswered`.
 * What became of each hold is the hold settlement's (`hooks/holds.ts`); this
 * keeps loads, routes, references and when in their turn each was read,
 * design-reads lines, writing turns and subagents.
 */
export function summarize(events: readonly UsageEvent[], isFinal = false): SessionSummary & { timeline: TimelineEntry[] } {
  const loads: SessionSummary['loads'] = {}
  const lastUsed: Record<string, number> = {}
  const refs: Refs = {}
  let refsUnloaded = 0
  const refMoments: RefMoments = {}
  const measures: Required<Omit<Measures, 'holds' | 'closeoutItems' | 'skipReasons'>> = {
    routes: {},
    routeSkills: {},
    sideSessions: {},
    writingTurns: { ...NO_WRITING_TURNS },
    overrides: {},
    subagents: { ...NO_SUBAGENTS },
    designReads: noDesignReads(),
  }
  const holds = holdSettlement()
  // The running typed-prompt turn: whether the main agent wrote a route line yet, and, once it wrote, how that write stood.
  // A turn ends only at the next typed prompt, so a background result that wakes the agent stays in the turn, as the adapter treats it.
  let isTurnRouted = false
  let turnWrites: keyof WritingTurns | null = null
  // Writes whose calls may yet be refused, by tool_use id, each with whether a route line came before it; a refused one never wrote.
  const pendingWrites = new Map<string, boolean>()
  const tallyWritingTurn = () => {
    const [firstRouted] = pendingWrites.values()
    if (turnWrites === null && firstRouted !== undefined) turnWrites = firstRouted ? 'routed' : isTurnRouted ? 'late' : 'none'
    if (turnWrites) measures.writingTurns[turnWrites] += 1
    isTurnRouted = false
    turnWrites = null
    pendingWrites.clear()
  }
  // Calls whose result was an error: a Skill call loaded nothing, an edit changed nothing. A refusal arrives after its
  // call, so it is looked up ahead.
  const refusedCalls = new Set(events.flatMap(e => (e.kind === 'refused' ? [e.id] : [])))
  // The running turn's reference reads, each with how many code changes came before it, and the turn's code changes so
  // far. A read's moment depends on changes still to come, so the reads settle when the turn ends. Only a turn whose
  // prompt this version recorded is timed: an earlier version stored no code changes, and a log trimmed mid-turn lost
  // its turn's prompt, so those reads count in `refs` with no moment.
  let isTurnTimed = false
  let turnReads: { skill: string; file: string; changesBefore: number }[] = []
  let turnChanges = 0
  const settleReadMoments = () => {
    for (const r of turnReads) {
      const counts = ((refMoments[r.skill] ??= {})[r.file] ??= {})
      const moment = momentOf(r.changesBefore, turnChanges)
      counts[moment] = (counts[moment] ?? 0) + 1
    }
    turnReads = []
    turnChanges = 0
  }
  // Spawn log rows by tool_use id, so a refusal of the call marks its row held and takes it out of the count.
  const spawnRows = new Map<string, { isHeld?: true }>()
  const timeline: TimelineEntry[] = []
  let loaded = new Set<string>()
  let turnNamed = new Set<string>()
  let turnRouter = false

  for (const e of events) {
    if ((e.kind === 'load' || e.kind === 'change' || e.kind === 'side-session') && e.id && refusedCalls.has(e.id)) continue
    const holdRow = holds.observe(e)
    if (holdRow) timeline.push(holdRow)
    switch (e.kind) {
      case 'prompt':
        tallyWritingTurn()
        settleReadMoments()
        isTurnTimed = e.isTimed === true
        turnNamed = new Set(e.named)
        turnRouter = false
        timeline.push({ ...stamp(e), kind: 'prompt' })
        break
      case 'load': {
        // A hook asking for the skill outranks who loaded it, for a subagent as for the agent; the log row keeps that a subagent did.
        const origin: Origin =
          e.via === 'slash' ? 'user-slash'
          : e.isSubagent ? (holds.wasAsked(e.skill) ? 'hook-nudged' : 'subagent')
          : turnNamed.has(e.skill) ? 'user-named'
          : holds.wasAsked(e.skill) ? 'hook-nudged'
          : turnRouter && e.skill !== ROUTER ? 'router-routed'
          : 'self-initiated'
        bump(loads, e.skill, origin)
        lastUsed[e.skill] = e.t
        timeline.push({ ...stamp(e), kind: 'load', skill: e.skill, origin, ...(e.isSubagent ? { isSubagent: true as const } : {}) })
        if (e.skill === ROUTER) turnRouter = true
        loaded.add(e.skill)
        break
      }
      case 'body':
        measures.subagents.bodyReads += 1
        timeline.push({ ...stamp(e), kind: 'body', skill: e.skill, isSubagent: true })
        break
      case 'route': {
        measures.routes[e.form] = (measures.routes[e.form] ?? 0) + 1
        if (e.form === 'route') for (const skill of e.requires) bump(measures.routeSkills, skill, e.intensity)
        if (!e.agent) {
          isTurnRouted = true
          if (turnWrites === 'none') turnWrites = 'late'
        }
        const route: Route = e.form === 'route' ? { form: e.form, intensity: e.intensity, requires: e.requires } : { form: e.form }
        timeline.push({ ...stamp(e), kind: 'route', ...route, ...(e.isSubagent ? { isSubagent: true as const } : {}) })
        break
      }
      case 'design-reads':
        for (const file of e.files) measures.designReads.files[file] = (measures.designReads.files[file] ?? 0) + 1
        measures.designReads.none += e.noneReasons.length
        timeline.push({ ...stamp(e), kind: 'design-reads', files: e.files, noneReasons: e.noneReasons, ...(e.isSubagent ? { isSubagent: true as const } : {}) })
        break
      case 'override':
        for (const phrase of e.phrases) measures.overrides[phrase] = (measures.overrides[phrase] ?? 0) + 1
        timeline.push({ ...stamp(e), kind: 'override', phrases: e.phrases })
        break
      case 'spawn': {
        measures.subagents.spawns += 1
        const spawnRow: TimelineEntry & { kind: 'spawn' } = { ...stamp(e), kind: 'spawn', agentType: e.agentType, description: e.description, ...(e.isSubagent ? { isSubagent: true as const } : {}) }
        timeline.push(spawnRow)
        if (e.id) spawnRows.set(e.id, spawnRow)
        break
      }
      case 'subagent-start':
        measures.subagents.starts += 1
        timeline.push({ ...stamp(e), kind: 'subagent-start' })
        break
      case 'ref': {
        const files = (refs[e.skill] ??= {})
        files[e.file] = (files[e.file] ?? 0) + 1
        const isLoaded = loaded.has(e.skill)
        if (!isLoaded) refsUnloaded += 1
        if (isTurnTimed) turnReads.push({ skill: e.skill, file: e.file, changesBefore: turnChanges })
        timeline.push({ ...stamp(e), kind: 'ref', skill: e.skill, file: e.file, isLoaded, ...(e.isSubagent ? { isSubagent: true as const } : {}) })
        break
      }
      case 'change':
        turnChanges += 1
        break
      case 'write':
        if (e.id) pendingWrites.set(e.id, isTurnRouted)
        // A write with no call id (events kept before ids were recorded) cannot be refused, so it counts at once.
        else turnWrites ??= isTurnRouted ? 'routed' : 'none'
        break
      case 'side-session':
        bump(measures.sideSessions, e.tool, e.shows)
        break
      case 'refused': {
        pendingWrites.delete(e.id)
        const spawned = spawnRows.get(e.id)
        if (spawned && !spawned.isHeld) {
          spawned.isHeld = true
          measures.subagents.spawns -= 1
        }
        break
      }
      case 'compact':
        loaded = new Set()
        timeline.push({ ...stamp(e), kind: 'compact' })
        break
    }
  }
  const { nudges, holds: held, closeoutItems, skipReasons } = holds.finish(isFinal)
  tallyWritingTurn()
  settleReadMoments()

  return { loads, nudges, lastUsed, refs, refsUnloaded, refMoments, ...measures, holds: held, closeoutItems, skipReasons, timeline, router: 'off', version: DATA_VERSION }
}

/**
 * A read's moment in a turn that made `changes` code changes, `changesBefore` of them before the read. While the turn
 * is open, a read after its latest change counts as after the last; a later change makes it between.
 */
function momentOf(changesBefore: number, changes: number): RefMoment {
  if (changes === 0) return 'no-change'
  if (changesBefore === 0) return 'before'
  return changesBefore === changes ? 'after' : 'between'
}

function addFlat(into: Record<string, number | undefined>, from: Record<string, number | undefined> | undefined) {
  for (const [key, n] of Object.entries(from ?? {})) into[key] = (into[key] ?? 0) + (n ?? 0)
}

/** Adds `from`'s measures into `into`, either of which may predate them. */
function addMeasures(into: Measures, from: Measures) {
  addFlat((into.routes ??= {}), from.routes)
  if (from.routeSkills) addCounts((into.routeSkills ??= {}), from.routeSkills)
  if (from.sideSessions) addCounts((into.sideSessions ??= {}), from.sideSessions)
  addFlat((into.writingTurns ??= { ...NO_WRITING_TURNS }), from.writingTurns)
  addFlat((into.holds ??= {}), from.holds)
  addFlat((into.overrides ??= {}), from.overrides)
  addFlat((into.subagents ??= { ...NO_SUBAGENTS }), from.subagents)
  const reads = (into.designReads ??= noDesignReads())
  addFlat(reads.files, from.designReads?.files)
  reads.none += from.designReads?.none ?? 0
  if (from.closeoutItems) addCounts((into.closeoutItems ??= {}), from.closeoutItems)
  addSkipReasons(into, from.skipReasons)
}

function addCounts<K extends string>(into: Record<string, Counts<K>>, from: Record<string, Counts<K>>) {
  for (const [row, counts] of Object.entries(from)) {
    for (const [key, n] of Object.entries(counts) as [K, number][]) {
      const target = (into[row] ??= {})
      target[key] = (target[key] ?? 0) + n
    }
  }
}

/** Adds `from`'s reference reads into `into`: by file, before their skill loaded, and by moment. Either may predate any of them. */
function addReads(into: Pick<SessionSummary, 'refs' | 'refsUnloaded' | 'refMoments'>, from: Pick<SessionSummary, 'refs' | 'refsUnloaded' | 'refMoments'>) {
  for (const [skill, files] of Object.entries(from.refs ?? {})) addFlat(((into.refs ??= {})[skill] ??= {}), files)
  into.refsUnloaded = (into.refsUnloaded ?? 0) + (from.refsUnloaded ?? 0)
  for (const [skill, files] of Object.entries(from.refMoments ?? {})) addCounts(((into.refMoments ??= {})[skill] ??= {}), files)
}

function addLastUsed(into: Record<string, number>, from: Record<string, number>) {
  for (const [skill, t] of Object.entries(from)) into[skill] = Math.max(into[skill] ?? 0, t)
}

// The module runs without DOM or Node globals, so no structuredClone.
const copy = <T>(value: T): T => JSON.parse(JSON.stringify(value))

const noTotal = (): AllTime => ({ sessions: 0, loads: {}, nudges: {}, router: {}, lastUsed: {} })

/**
 * Adds one session's summary to the running all-time totals, and to its project's when it carries a project key. The
 * holds of a summary stored by an earlier version go under `earlier`, not into the current counts.
 */
export function addSession(total: AllTime | null, s: SessionSummary): AllTime {
  const out = addInto(total ? copy(total) : noTotal(), s)
  if (s.project) {
    const byProject = (out.byProject ??= {})
    byProject[s.project] = addInto(byProject[s.project] ?? noTotal(), s)
  }
  return out
}

/** The totals of the project `key` stands for, or of every project for null; empty for a key with no sessions. */
export function forProject(all: AllTime, key: string | null): AllTime {
  return key === null ? all : (all.byProject?.[key] ?? noTotal())
}

/** Adds one session's summary into `out`, in place, and returns it. */
function addInto(out: AllTime, summary: SessionSummary): AllTime {
  out.sessions += 1
  addCounts(out.loads, summary.loads)
  out.router[summary.router] = (out.router[summary.router] ?? 0) + 1
  addLastUsed(out.lastUsed, summary.lastUsed)
  addReads(out, summary)
  if (!isEarlierVersion(summary)) {
    addCounts(out.nudges, summary.nudges)
    addMeasures(out, summary)
    return out
  }
  // Everything keyed by a gate, or tied to one, stays apart: its gate names may be retired ones.
  const { holds, closeoutItems, skipReasons, ...gateFree } = summary
  addEarlier(out, { sessions: 1, nudges: summary.nudges, ...(holds ? { holds } : {}), ...(closeoutItems ? { closeoutItems } : {}), ...(skipReasons ? { skipReasons } : {}) })
  addMeasures(out, gateFree)
  return out
}

/** Adds the earlier versions' gate-keyed data `from` into `into`'s, in place. */
function addEarlier(into: AllTime, from: EarlierHolds | undefined) {
  if (!from) return
  const earlier = (into.earlier ??= { sessions: 0, nudges: {} })
  earlier.sessions += from.sessions
  addCounts(earlier.nudges, from.nudges)
  if (from.holds) addFlat((earlier.holds ??= {}), from.holds)
  if (from.closeoutItems) addCounts((earlier.closeoutItems ??= {}), from.closeoutItems)
  addSkipReasons(earlier, from.skipReasons)
}

/** Adds skip reasons `from` into `into`'s, in place: by skill, then gate, then reason. */
function addSkipReasons(into: { skipReasons?: SkipReasons }, from: SkipReasons | undefined) {
  for (const [skill, gates] of Object.entries(from ?? {})) addCounts(((into.skipReasons ??= {})[skill] ??= {}), gates)
}

/** Adds the totals `from` into a copy of `into`: the same sums `addSession` makes, for many sessions at once. */
function addTotals(into: AllTime | null, from: AllTime | null): AllTime | null {
  if (!from) return into
  if (!into) return copy(from)
  const out = copy(into)
  out.sessions += from.sessions
  addCounts(out.loads, from.loads)
  addCounts(out.nudges, from.nudges)
  addFlat(out.router, from.router)
  addLastUsed(out.lastUsed, from.lastUsed)
  addReads(out, from)
  addMeasures(out, from)
  addEarlier(out, from.earlier)
  for (const [key, project] of Object.entries(from.byProject ?? {})) {
    const byProject = (out.byProject ??= {})
    byProject[key] = addTotals(byProject[key] ?? null, project) ?? noTotal()
  }
  return out
}

/**
 * The all-time totals of the stored sessions other than `exclude` (the running
 * one, which the pane adds live), plus `older`, the total of sessions folded
 * before. Only the newest `cap` others stay stored one by one: the rest are `folded`
 * into the new `older`, so a session past the cap still counts. The caller
 * stores `older` and then removes the folded keys.
 */
export function allTimeOf(
  stored: readonly (readonly [key: string, value: { t: number; summary: SessionSummary }])[],
  older: AllTime | null,
  cap: number,
  exclude: string,
): { total: AllTime | null; older: AllTime | null; folded: string[] } {
  // The running session is never folded, even an old one resumed: it is stored again at its next turn.
  const newest = stored.filter(([key]) => key !== exclude).sort(([, a], [, b]) => b.t - a.t)
  const sum = (list: typeof newest) => list.reduce<AllTime | null>((acc, [, v]) => addSession(acc, closeOpen(v.summary)), null)
  const past = newest.slice(cap)
  const nextOlder = addTotals(older, sum(past))
  return { total: addTotals(nextOlder, sum(newest.slice(0, cap))), older: nextOlder, folded: past.map(([key]) => key) }
}

/**
 * One session's summary from two stretches of it: what was stored before a
 * resume (`earlier`) and what was observed since. The router status is the
 * earlier one's, which only a summary stored by an earlier version sets. The
 * version is the older stretch's, none if either has none, since the merged
 * counts are only as current as their oldest part; the project is the later
 * one's, which this version read.
 */
export function mergeSummaries(earlier: SessionSummary | null, later: SessionSummary): SessionSummary {
  if (!earlier) return later
  const out = copy(earlier)
  if (out.version === undefined || later.version === undefined) delete out.version
  else out.version = Math.min(out.version, later.version)
  if (later.project) out.project = later.project
  addCounts(out.loads, later.loads)
  addCounts(out.nudges, later.nudges)
  addLastUsed(out.lastUsed, later.lastUsed)
  addReads(out, later)
  addMeasures(out, later)
  return out
}

/**
 * A stored summary whose session is over, or whose events are gone (a resume
 * starts them afresh): a nudge still waiting in it can no longer settle, so it
 * counts as unanswered, as it would have at a clean end.
 */
export function closeOpen(s: SessionSummary): SessionSummary {
  const out = copy(s)
  for (const c of [...Object.values(out.nudges), ...Object.values(out.closeoutItems ?? {})]) {
    if (!c.pending) continue
    c.unanswered = (c.unanswered ?? 0) + c.pending
    delete c.pending
  }
  return out
}

export const total = (counts: Counts<string> | undefined) => Object.values(counts ?? {}).reduce<number>((sum, n) => sum + (n ?? 0), 0)
