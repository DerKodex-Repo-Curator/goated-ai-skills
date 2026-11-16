// Turns conversation content into neutral events (live rows and the history a
// late-loading mod reads go through the same rules), then labels why each skill
// loaded and whether hook nudges were followed. Pure: no engine calls, so tests
// can feed it events and messages.
//
// Two kinds of hook text are read. The GOATED Claude Code adapter's holds start
// `goated-hold: <gate> | <kind>` (adapters/claude-code/README.md in the GOATED
// repo), and `OVERRIDE_NOTICE` matches its override sentence. `LEGACY_MARKERS`
// are the messages of the hand-written hooks some installs ran before the
// adapter; they stay readable until the adapter replaces them, and must change
// with those hooks while they do.

import type {
  AllTime,
  Counts,
  HoldKind,
  Measures,
  NudgedSkill,
  Origin,
  Outcome,
  Refs,
  Route,
  RouteForm,
  RouterStatus,
  SessionSummary,
  SubagentCounts,
  TimelineEntry,
  UsageEvent,
  WritingTurns,
} from '../types'

export const ROUTER = 'using-goated-ai-skills'
/** The route hold asks for whichever specialist the route chose, not a named one. */
export const ANY_SPECIALIST = '(any specialist)'
/** The adapter's route-line hold asks for a route line, which no skill load settles. */
export const ROUTE_LINE = '(route line)'
/** Subagent counts before any subagent did anything. */
export const NO_SUBAGENTS: Readonly<SubagentCounts> = { spawns: 0, starts: 0, bodyReads: 0 }
/** Writing-turn counts before any turn wrote. */
export const NO_WRITING_TURNS: Readonly<WritingTurns> = { routed: 0, late: 0, none: 0 }

// Hand-written hook messages, the first match winning within one paragraph of hook output.
// `subagent-start` is a SubagentStart hook's contract for a subagent: recorded as its start, not as a nudge.
const LEGACY_MARKERS: ReadonlyArray<readonly [string, string]> = [
  ['DELEGATED AGENT', 'subagent-start'],
  ['MANDATORY SESSION RULE', 'router-rule'],
  ['ROUTE CHECK', 'route-hold'],
  ['DESIGN HOLD', 'design-hold'],
  ['SECURITY HOLD', 'security-hold'],
  ['DESIGN CHECK (new code file', 'design-new-file'],
  ['DESIGN CHECK', 'design'],
  ['SECURITY SIGNAL', 'security'],
  ['COMMIT CHECK', 'commit-hold'],
  ['PR CHECK', 'pr-hold'],
  ['SPAWN BRIEF HOLD', 'spawn-hold'],
  ['MERGE CONFLICT', 'merge-conflict'],
  ['REPEATED FAILURE', 'diagnose'],
  ['CLOSEOUT CHECK', 'closeout'],
]
// Holds arrive as a denied tool call (an errored tool result), not as context.
const LEGACY_HOLDS = new Set(['route-hold', 'design-hold', 'security-hold', 'commit-hold', 'pr-hold', 'spawn-hold'])

export const ORIGINS: readonly Origin[] = ['user-slash', 'user-named', 'hook-nudged', 'router-routed', 'self-initiated', 'subagent']
export const OUTCOMES: readonly Outcome[] = ['followed', 'read files', 'already loaded', 'declined', 'ignored', 'pending']

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

/**
 * Skills a hook message names. The GOATED hooks backtick every skill they name,
 * so only backticked names count: plain words such as "run the commit again"
 * must not match a skill called `run`.
 */
export function skillsBackticked(text: string, skills: readonly string[]): string[] {
  const ticked = new Set([...text.matchAll(/`([\w:.-]+)`/g)].flatMap(m => (m[1] ? [m[1].split(':').pop() ?? m[1]] : [])))
  return skills.filter(s => ticked.has(s))
}

// The hold line, exactly as adapters/claude-code/README.md ("Hold messages") documents it.
const ADAPTER_HOLD = /^goated-hold: ([a-z]+(?:-[a-z]+)*) \| (strict|justified-skip)$/
// How Claude Code wraps a hold's reason (2.1.325): a denied call's errored result starts `PreToolUse:<Tool> hook error: `,
// and a blocked Stop arrives, live and in history alike, as a reminder whose first line is this sentence.
const CALL_HELD = /^\S+ hook error: /
const STOP_BLOCKED = /^Stop hook blocking error from command: ".*": (goated-hold: .*)$/
const BACKTICKED_SKILL = /`([a-z0-9]+(?:-[a-z0-9]+)*)`/g
// The skip line a justified-skip hold offers, backticked whole: its skill is asked for too, as for the closeout's proof item.
const OFFERED_SKIP = /`goated-skip: ([a-z0-9]+(?:-[a-z0-9]+)*): /g
/** The grammar's own words, which adapters before Ticket 034 backticked in hold texts; they are no skills. */
const MARKER_WORDS = new Set(['goated-hold', 'goated-route', 'goated-skip'])
/** The adapter's gate for a route's required skills. */
const PIPELINE_GATE = 'pipeline'
/** Gates whose named skills are alternatives, one of which answers the hold: the spawn hold's `handoff` or `subagent-driven-development`. */
const ALTERNATIVE_GATES = new Set(['spawn'])
/**
 * How many times in a row Claude Code lets a `Stop` hook block before it ends
 * the turn anyway (2.1.325, seen in Ticket 034's runs). A turn that ends after
 * that many blocks did not get past the hold.
 */
const STOP_BLOCK_LIMIT = 9

/**
 * What an adapter hold asks for: the router, a route line, or every skill its
 * text backticks, alone or as the skill of a skip line it offers, in the order
 * they appear. The adapter backticks only skill names and whole marker lines,
 * so the names are taken as they stand, whether or not the session's skill
 * listing has loaded.
 */
function adapterHoldNamed(gate: string, body: string): string[] {
  if (gate === 'router-first') return [ROUTER]
  if (gate === 'route-line') return [ROUTE_LINE]
  const named = [...body.matchAll(BACKTICKED_SKILL), ...body.matchAll(OFFERED_SKIP)].sort((a, b) => (a.index ?? 0) - (b.index ?? 0))
  return [...new Set(named.flatMap(m => (m[1] && !MARKER_WORDS.has(m[1]) ? [m[1]] : [])))]
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
 * The hook messages in one piece of hook output, each with the skills it
 * names. Output that carries an adapter hold is that one hold, and its
 * `hook` is its gate; `isStop`: it held a `Stop`, not a call. Otherwise a legacy marked paragraph starts a message,
 * and unmarked paragraphs after it belong to it. `holdsOnly`: the text is an
 * errored tool result, which can quote a marker, so only holds count.
 */
export function hookNudges(text: string, skills: readonly string[], holdsOnly = false): { hook: string; named: string[]; holdKind?: HoldKind; isStop?: true }[] {
  const hold = adapterHold(text, holdsOnly)
  if (hold) return [{ hook: hold.gate, named: adapterHoldNamed(hold.gate, hold.body), holdKind: hold.kind, ...(hold.isStop ? { isStop: true as const } : {}) }]

  const messages: { hook: string; body: string }[] = []
  for (const paragraph of text.split('\n\n')) {
    const hook = LEGACY_MARKERS.find(([marker]) => paragraph.includes(marker))?.[1]
    if (hook) messages.push({ hook, body: paragraph })
    else {
      const last = messages.at(-1)
      if (last) last.body += '\n\n' + paragraph
    }
  }
  return messages
    .filter(m => !holdsOnly || LEGACY_HOLDS.has(m.hook))
    .map(m => ({ hook: m.hook, named: m.hook === 'route-hold' ? [ANY_SPECIALIST] : m.hook === 'subagent-start' ? [] : skillsBackticked(m.body, skills) }))
}

/**
 * The events of one piece of hook output: a nudge per hook message, or a
 * subagent's start for its start message. `agent`: the subagent the hook
 * spoke to; `holdsOnly`: the text is an errored tool result.
 */
export function hookEvents(text: string, skills: readonly string[], t: number, opts: { agent?: string; holdsOnly?: boolean } = {}): UsageEvent[] {
  const ofAgent = opts.agent ? { agent: opts.agent } : {}
  return hookNudges(text, skills, opts.holdsOnly).map((n): UsageEvent =>
    n.hook === 'subagent-start' ? { kind: 'subagent-start', t, ...ofAgent } : { kind: 'nudge', t, ...n, ...(opts.agent ? { isSubagent: true as const } : {}), ...ofAgent },
  )
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

// App bookkeeping tools that say nothing about whether the agent started work.
const BOOKKEEPING_TOOL = /^(ToolSearch$|mcp__ccd_)/

/**
 * The events of one message the person sent: a prompt, plus a skill load when
 * it is a slash command naming a skill. Any other slash command, such as
 * /compact or this mod's own /skill-usage, runs in Claude Code without a
 * model turn, so it is no prompt, and neither is its output.
 */
export function promptEvents(text: string, skills: readonly string[], t: number): UsageEvent[] {
  if (text.trimStart().startsWith('<local-command-')) return []
  const command = /<command-name>\/?([\w:.-]+)<\/command-name>/.exec(text)?.[1]
  if (!command) return [{ kind: 'prompt', t, named: skillsNamed(text, skills) }]
  if (!skills.includes(short(command))) return []
  return [
    { kind: 'prompt', t, named: [] },
    { kind: 'load', t, skill: short(command), via: 'slash', isSubagent: false },
  ]
}

/** The skill a Skill call names, as the adapter reads it: `/tdd write the test` is `tdd`, and `plugin:tdd` is `tdd`. */
const skillArgument = (value: unknown) => short(String(value ?? '').trim().replace(/^\/+/, '').split(/\s+/)[0] ?? '')

// The tools that start a subagent; `Task` is the Agent tool's older name.
const SPAWN_TOOLS = new Set(['Agent', 'Task'])
// What the adapter holds like a write (adapters/claude-code/README.md): edits, and spawns, which hand work on.
const WRITE_TOOLS = new Set(['Edit', 'Write', 'MultiEdit', 'NotebookEdit', ...SPAWN_TOOLS, 'mcp__ccd_session__start_session', 'mcp__ccd_session__hand_off_to_session'])

/**
 * The events of one assistant message's tool calls: skill loads, subagent
 * spawns, writes, reads into a skill's folder, reads of a skill's supporting
 * files, and the turn's first real tool (`hasToolBefore`: one was already
 * seen). A subagent's calls count only as skill loads, spawns,
 * supporting-file reads and reads of a SKILL.md (`body`); `agent` names that
 * subagent.
 */
export function toolUseEvents(
  uses: readonly { id?: string; name: string; input: Record<string, unknown> }[],
  isSubagent: boolean,
  hasToolBefore: boolean,
  t: number,
  agent?: string,
): UsageEvent[] {
  const events: UsageEvent[] = []
  const ofAgent = isSubagent && agent ? { agent } : {}
  let seenTool = hasToolBefore
  for (const { id, name, input } of uses) {
    const ofCall = id ? { id } : {}
    if (name === 'Skill') {
      events.push({ kind: 'load', t, ...ofCall, skill: skillArgument(input.skill), via: 'tool', isSubagent })
      continue
    }
    if (SPAWN_TOOLS.has(name)) {
      const spawn = { agentType: String(input.subagent_type || 'general-purpose'), description: String(input.description ?? '') }
      events.push({ kind: 'spawn', t, ...ofCall, ...spawn, ...(isSubagent ? { isSubagent: true as const } : {}), ...ofAgent })
    }
    const target = String((name === 'Read' ? input.file_path : input.command) ?? '')
    const refs: UsageEvent[] = skillFiles(target).map(f => ({ kind: 'ref', t, ...f, ...(isSubagent ? { isSubagent: true as const } : {}) }))
    if (isSubagent) {
      for (const skill of skillBodies(target)) events.push({ kind: 'body', t, skill, isSubagent: true, ...ofAgent })
      events.push(...refs)
      continue
    }
    const reached = skillsInPath(target)
    if (reached.length > 0) events.push({ kind: 'read', t, skills: reached })
    events.push(...refs)
    if (WRITE_TOOLS.has(name)) events.push({ kind: 'write', t, ...ofCall })
    if (!seenTool && !BOOKKEEPING_TOOL.test(name)) {
      events.push({ kind: 'tool', t })
      seenTool = true
    }
  }
  return events
}

// The GOATED marker grammar: stack/fixtures/markers/README.md in the GOATED repo, whose lines.yaml the tests read.
const SKILL = '[a-z0-9]+(?:-[a-z0-9]+)*'
const ROUTE_RE = new RegExp(`^goated-route:[ \\t]+(?:(direct|continue)|(lightweight|standard|full)[ \\t]+\\|[ \\t]+requires:[ \\t]+(${SKILL}(?:[ \\t]*,[ \\t]*${SKILL})*))$`)
const SKIP_RE = new RegExp(`^goated-skip:[ \\t]+(${SKILL}):[ \\t]+(\\S.*)$`)
// A candidate marker line, compared case-insensitively: one that fails the grammar is malformed.
const MARKER_PREFIX = /^goated-(route|skip):/i
const FENCE = /^(```|~~~)/
/** The grammar's floor for a reason: at least three words. */
const MIN_REASON_WORDS = 3

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
  if (!m?.[1] || reason.split(/\s+/).length < MIN_REASON_WORDS) return null
  return { skill: m[1], reason }
}

/**
 * The marker lines of one reply, as the grammar reads them: the winning route
 * (the last valid route line), every skip line, and each candidate line that
 * starts like a marker but fails the grammar. Only whole lines outside fenced
 * code count, each unwrapped from at most one pair of backticks.
 */
export function markerLines(text: string): { route: Route | null; skips: Skip[]; malformed: string[] } {
  let route: Route | null = null
  const skips: Skip[] = []
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
    }
  }
  return { route, skips, malformed }
}

/** The marker events of one reply: its winning route, then each skip line. `agent`: the subagent that wrote it. */
export function markerEvents(text: string, t: number, agent?: string): UsageEvent[] {
  const { route, skips } = markerLines(text)
  const loop = agent ? { isSubagent: true as const, agent } : {}
  return [...(route ? [{ kind: 'route' as const, t, ...route, ...loop }] : []), ...skips.map(k => ({ kind: 'skip' as const, t, ...k, ...loop }))]
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
  let hasTool = false
  let lastBoundary: 'response' | 'results' | undefined
  for (const message of messages) {
    if (message.role === 'assistant') {
      const uses = toolUses(message.content)
      const add = toolUseEvents(uses, false, hasTool, t)
      hasTool ||= add.some(e => e.kind === 'tool')
      if (lastBoundary !== 'response') events.push({ kind: 'response', t })
      lastBoundary = 'response'
      events.push(...markerEvents(textOf(message.content.filter(b => b.type === 'text')), t), ...add)
      continue
    }
    const opening: UsageEvent[] = []
    const after: UsageEvent[] = []
    for (const b of message.content) {
      if (b.type === 'tool_result') {
        if (b.is_error) after.push(...refusalEvents(b, skills, t))
        continue
      }
      if (b.type !== 'text') continue
      const text = String(b.text ?? '').trim()
      if (HOOK_TEXT.test(text)) after.push(...hookEvents(text, skills, t))
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
function refusalEvents(block: { [field: string]: unknown }, skills: readonly string[], t: number, agent?: string): UsageEvent[] {
  const id = block.tool_use_id
  return [...hookEvents(textOf(block.content), skills, t, { agent, holdsOnly: true }), ...(typeof id === 'string' ? [{ kind: 'refused' as const, t, id }] : [])]
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
 * compactions; and the main agent's round-trip boundaries. `seen`: whether
 * the session's events already hold a real tool, the kind of the last one,
 * and the last round-trip boundary.
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
  seen: { hasTool: boolean; lastKind?: UsageEvent['kind']; lastBoundary?: 'response' | 'results' },
): UsageEvent[] {
  const isMain = !row.agentId
  const blocks = row.message.content
  // A local command's output comes in as a system row by the command door.
  if (row.door === 'prompt' || row.door === 'command') return isMain && !row.message.isMeta && row.message.type !== 'system' ? promptEvents(textOf(blocks), skills, t) : []
  if (row.door === 'response') {
    const uses = toolUses(blocks)
    const begins: UsageEvent[] = isMain && seen.lastBoundary !== 'response' ? [{ kind: 'response', t }] : []
    return [...begins, ...markerEvents(textOf(blocks.filter(b => b.type === 'text')), t, row.agentId), ...toolUseEvents(uses, !isMain, seen.hasTool, t, row.agentId)]
  }
  if (isHookRow(row)) {
    const text = textOf(blocks)
    const heard = hookEvents(text, skills, t, { agent: row.agentId })
    // A blocked Stop hands the agent its reason as tool results do, so it ends the reply's round trip.
    const ends = isMain && heard.some(isStopHold) && seen.lastBoundary !== 'results' ? [{ kind: 'results' as const, t }] : []
    return [...heard, ...(isMain ? overrideEvents(text, t) : []), ...ends]
  }
  if (row.door === 'tool-result') {
    const refusals = blocks.flatMap(b => (b.type === 'tool_result' && b.is_error ? refusalEvents(b, skills, t, row.agentId) : []))
    const isResult = isMain && blocks.some(b => b.type === 'tool_result')
    return [...refusals, ...(isResult && seen.lastBoundary !== 'results' ? [{ kind: 'results' as const, t }] : [])]
  }
  // A compaction appends a boundary and a summary: count it once.
  if (row.door === 'compaction' && isMain && seen.lastKind !== 'compact') return [{ kind: 'compact', t }]
  return []
}

/** An event's time, as a timeline row carries it. */
const stamp = (e: UsageEvent) => (e.isEarlier ? { t: e.t, isEarlier: true as const } : { t: e.t })

function bump<K extends string>(table: Record<string, Counts<K>>, row: string, key: K) {
  const counts = (table[row] ??= {})
  counts[key] = (counts[key] ?? 0) + 1
}

/**
 * Folds a session's events into what loaded and why, what became of each
 * nudge, and a readable timeline. A nudge still open at the end is `pending`
 * while the session runs; once it has ended (`isFinal`) it was `ignored`.
 */
export function summarize(events: readonly UsageEvent[], isFinal = false): SessionSummary & { timeline: TimelineEntry[] } {
  const loads: SessionSummary['loads'] = {}
  const nudges: SessionSummary['nudges'] = {}
  const lastUsed: Record<string, number> = {}
  const refs: Refs = {}
  let refsUnloaded = 0
  const measures: Required<Measures> = { routes: {}, writingTurns: { ...NO_WRITING_TURNS }, holds: {}, overrides: {}, subagents: { ...NO_SUBAGENTS } }
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
  // Skill calls whose result was an error: they loaded nothing. A refusal arrives after its call, so it is looked up ahead.
  const failedLoads = new Set(events.flatMap(e => (e.kind === 'refused' ? [e.id] : [])))
  // Spawn log rows by tool_use id, so a refusal of the call marks its row held and takes it out of the count.
  const spawnRows = new Map<string, { isHeld?: true }>()
  const timeline: TimelineEntry[] = []
  let loaded = new Set<string>()
  let turnNamed = new Set<string>()
  let turnNudged = new Set<string>()
  let turnRouter = false
  // One open ask per nudge: the skills any one of which answers it (`anyOf`; more than one only for a gate whose skills
  // are alternatives), and its mark on the nudge's own log row, so settling it updates that row.
  // `agent`: the subagent it spoke to, absent for the main agent; that loop's turn end settles it.
  // `isStrict`: an adapter hold that only loading the skill clears; a skip line never declines it.
  // `row`: the nudge's log row, which a repeat of the same hold in the turn joins. `isStop`: a hold on a `Stop`.
  type NudgeRow = TimelineEntry & { kind: 'nudge' }
  type Open = { hook: string; anyOf: string[]; agent?: string; isStrict?: true; isStop?: true; mark: NudgedSkill; row: NudgeRow }
  let open: Open[] = []
  /** Whether an open ask is answered by `skill`; the route hold of earlier hooks is answered by any specialist. */
  const answers = (n: Open, skill: string) => n.anyOf.includes(skill) || (n.anyOf[0] === ANY_SPECIALIST && skill !== ROUTER)
  // Skip lines written in each loop's running turn, by agent ('' for the main agent) then skill, with their reasons.
  const skipped = new Map<string, Map<string, string>>()
  const skipsOf = (agent?: string) => skipped.get(agent ?? '') ?? new Map<string, string>()
  const skipReason = (anyOf: readonly string[], agent?: string) => anyOf.map(s => skipsOf(agent).get(s)).find(r => r !== undefined)
  // The main agent's round trip a held call belongs to: what its reply did before the call. Claude Code records a call
  // only after its hold returns, so a route line or load beside the held call reaches the adapter one call late.
  type Reply = { route?: RouteForm; loads: Set<string> }
  let reply: Reply = { loads: new Set() }
  let answeredReply: Reply = reply
  let isInResults = false
  // Whether the main agent replied since the last blocked `Stop`: a turn that then ends got past that hold.
  let hasRepliedSinceStop = false
  // Whether the session has a task a `continue` route line can continue, as the adapter's route-line hold checks.
  let hasTask = false
  let routerRule = false
  let toolSeen = false
  let router: RouterStatus | null = null

  // `by`: the event that settled it, whose time the row keeps so the picture can show the moment; a rebuilt event has no real time.
  // `chosen`: for an ask with alternatives, the skill that answered it, which its row then names.
  const settle = (matches: (n: Open) => boolean, outcome: Outcome, by?: UsageEvent, chosen?: string) => {
    open = open.filter(n => {
      if (!matches(n)) return true
      bump(nudges, n.hook, outcome)
      n.mark.status = outcome
      if (chosen && n.anyOf.length > 1) n.mark.skill = chosen
      if (by && !by.isEarlier) n.mark.at = by.t
      return false
    })
  }
  /**
   * A loop's turn is over: what it left open can no longer be followed, so each is declined (a skip line said why) or
   * ignored. A hold on a `Stop` is the exception: the adapter judges every `Stop`, so a turn that ended after the agent
   * answered the last block got past it, by a check run, a fix or a load the hold cannot name, unless Claude Code's
   * limit on blocks in a row ended it.
   */
  const closeTurn = (isInLoop: (n: Open) => boolean, by: UsageEvent) => {
    const ending = open.filter(n => isInLoop(n) && n.hook !== 'router-rule')
    for (const n of ending) {
      const reason = n.isStrict ? undefined : skipReason(n.anyOf, n.agent)
      if (reason !== undefined) n.mark.reason = reason
      const isPassed = n.isStop && hasRepliedSinceStop && (n.row.repeats ?? 1) < STOP_BLOCK_LIMIT
      settle(m => m === n, reason !== undefined ? 'declined' : isPassed ? 'followed' : 'ignored', by)
    }
  }
  /**
   * An adapter hold asking again, in the same turn, only for what an earlier hold of its gate still waits on: the agent
   * retried, or a blocked `Stop` blocked again. It joins that hold's row as a repeat and counts once; what the earlier
   * hold asked and this one no longer does was met. A hold that asks for anything new, or for nothing, is a row of its own.
   */
  const joinRepeat = (e: UsageEvent & { kind: 'nudge' }, asks: readonly string[][]): boolean => {
    const row = open.findLast(n => n.hook === e.hook && n.agent === e.agent)?.row
    const waiting = open.filter(n => n.row === row)
    const sameAsk = (n: Open, ask: readonly string[]) => n.anyOf.join(' ') === ask.join(' ')
    if (!row || asks.length === 0 || !asks.every(ask => waiting.some(n => sameAsk(n, ask)))) return false
    row.repeats = (row.repeats ?? 1) + 1
    settle(n => waiting.includes(n) && !asks.some(ask => sameAsk(n, ask)), 'followed', e)
    for (const ask of asks) {
      const inReply = answeredInReply(ask, e)
      if (inReply !== undefined) settle(n => waiting.includes(n) && sameAsk(n, ask), 'followed', e, inReply)
    }
    return true
  }
  /** What the held call's own reply already did for `ask`, which the adapter could not see yet: the answering skill, or none. */
  const answeredInReply = (ask: readonly string[], e: UsageEvent & { kind: 'nudge' }) => {
    if (!e.holdKind || e.agent) return undefined
    const own = isInResults ? answeredReply : reply
    if (ask[0] === ROUTE_LINE) return own.route && (own.route !== 'continue' || hasTask) ? ROUTE_LINE : undefined
    return ask.find(s => own.loads.has(s))
  }

  for (const e of events) {
    switch (e.kind) {
      case 'prompt':
        // The router rule arrives at session start, before the first prompt,
        // and holds for the whole session: it stays open until the router loads.
        // Anything else still open belongs to a turn that is over, a turn end the mod did not see included.
        closeTurn(() => true, e)
        tallyWritingTurn()
        skipped.clear()
        turnNamed = new Set(e.named)
        turnNudged = new Set(open.flatMap(n => n.anyOf))
        turnRouter = false
        reply = answeredReply = { loads: new Set() }
        isInResults = false
        timeline.push({ ...stamp(e), kind: 'prompt' })
        break
      case 'response':
        reply = { loads: new Set() }
        isInResults = false
        hasRepliedSinceStop = true
        break
      case 'results':
        if (!isInResults) answeredReply = reply
        isInResults = true
        break
      case 'nudge': {
        if (e.hook === 'router-rule') routerRule = true
        if (e.holdKind) measures.holds[e.holdKind] = (measures.holds[e.holdKind] ?? 0) + 1
        if (e.isStop) hasRepliedSinceStop = false
        // A gate whose skills are alternatives asks once; any other nudge asks for each skill it names.
        const asks = ALTERNATIVE_GATES.has(e.hook) && e.named.length > 1 ? [e.named] : e.named.map(s => [s])
        if (e.holdKind && joinRepeat(e, asks)) break
        const row: NudgeRow = {
          ...stamp(e),
          kind: 'nudge' as const,
          hook: e.hook,
          skills: [] as NudgedSkill[],
          ...(e.holdKind ? { holdKind: e.holdKind } : {}),
          ...(e.isSubagent ? { isSubagent: true as const } : {}),
        }
        timeline.push(row)
        const at = e.isEarlier ? {} : { at: e.t }
        for (const ask of asks) {
          const label = ask.join(' or ')
          const reason = e.holdKind === 'strict' ? undefined : skipReason(ask, e.agent)
          const inReply = answeredInReply(ask, e)
          if (inReply !== undefined) {
            bump(nudges, e.hook, 'followed')
            row.skills.push({ skill: inReply, status: 'followed', ...at })
          } else if (!e.holdKind && e.hook !== 'router-rule' && ask.some(s => loaded.has(s))) {
            // Earlier hooks asked once a session; the adapter's holds ask for a load in this turn, so one before does not answer them.
            bump(nudges, e.hook, 'already loaded')
            row.skills.push({ skill: label, status: 'already loaded', ...at })
          } else if (reason !== undefined) {
            // Declined before it was asked, earlier in the same turn.
            bump(nudges, e.hook, 'declined')
            row.skills.push({ skill: label, status: 'declined', reason, ...at })
          } else {
            const mark: NudgedSkill = { skill: label, status: 'pending' }
            row.skills.push(mark)
            for (const s of ask) turnNudged.add(s)
            open.push({
              hook: e.hook,
              anyOf: ask,
              ...(e.agent ? { agent: e.agent } : {}),
              ...(e.holdKind === 'strict' ? { isStrict: true as const } : {}),
              ...(e.isStop ? { isStop: true as const } : {}),
              mark,
              row,
            })
          }
        }
        break
      }
      case 'skip': {
        const own = skipsOf(e.agent)
        own.set(e.skill, e.reason)
        skipped.set(e.agent ?? '', own)
        for (const n of open.filter(n => n.anyOf.includes(e.skill) && n.agent === e.agent && !n.isStrict)) {
          n.mark.reason = e.reason
          settle(m => m === n, 'declined', e)
        }
        break
      }
      case 'turn-end':
        closeTurn(n => n.agent === e.agent, e)
        skipped.delete(e.agent ?? '')
        break
      case 'load': {
        if (e.id && failedLoads.has(e.id)) break
        // A hook asking for the skill outranks who loaded it, for a subagent as for the agent; the log row keeps that a subagent did.
        const origin: Origin =
          e.via === 'slash' ? 'user-slash'
          : e.isSubagent ? (turnNudged.has(e.skill) ? 'hook-nudged' : 'subagent')
          : turnNamed.has(e.skill) ? 'user-named'
          : turnNudged.has(e.skill) ? 'hook-nudged'
          : turnRouter && e.skill !== ROUTER ? 'router-routed'
          : 'self-initiated'
        bump(loads, e.skill, origin)
        lastUsed[e.skill] = e.t
        timeline.push({ ...stamp(e), kind: 'load', skill: e.skill, origin, ...(e.isSubagent ? { isSubagent: true as const } : {}) })
        if (e.skill === ROUTER) {
          turnRouter = true
          router ??= toolSeen ? 'late' : 'first'
        }
        if (!e.isSubagent && e.via === 'tool') reply.loads.add(e.skill)
        settle(n => answers(n, e.skill), 'followed', e, e.skill)
        loaded.add(e.skill)
        break
      }
      case 'read':
        settle(n => n.anyOf.some(s => e.skills.includes(s)), 'read files', e, e.skills.find(s => open.some(n => n.anyOf.includes(s))))
        break
      case 'body':
        // A subagent reading a skill's body settles only what was asked of that subagent.
        measures.subagents.bodyReads += 1
        settle(n => n.anyOf.includes(e.skill) && n.agent === e.agent, 'read files', e, e.skill)
        timeline.push({ ...stamp(e), kind: 'body', skill: e.skill, isSubagent: true })
        break
      case 'route': {
        measures.routes[e.form] = (measures.routes[e.form] ?? 0) + 1
        if (!e.agent) {
          isTurnRouted = true
          if (turnWrites === 'none') turnWrites = 'late'
          reply.route = e.form
        }
        // A `continue` with no task to continue does not answer a route-line hold: the adapter holds it too.
        if (e.form !== 'continue' || hasTask || e.agent) settle(n => n.anyOf[0] === ROUTE_LINE && n.agent === e.agent, 'followed', e)
        if (!e.agent && e.form !== 'continue') hasTask = true
        // The pipeline hold says to drop a skill that does not apply by writing a corrected route line, the last one
        // winning: a new route that no longer requires a held skill follows that hold. `continue` keeps the route.
        if (e.form !== 'continue') {
          const requires: readonly string[] = e.form === 'route' ? e.requires : []
          settle(n => n.hook === PIPELINE_GATE && n.agent === e.agent && !n.anyOf.some(s => requires.includes(s)), 'followed', e)
        }
        const route: Route = e.form === 'route' ? { form: e.form, intensity: e.intensity, requires: e.requires } : { form: e.form }
        timeline.push({ ...stamp(e), kind: 'route', ...route, ...(e.isSubagent ? { isSubagent: true as const } : {}) })
        break
      }
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
        timeline.push({ ...stamp(e), kind: 'ref', skill: e.skill, file: e.file, isLoaded, ...(e.isSubagent ? { isSubagent: true as const } : {}) })
        break
      }
      case 'write':
        if (e.id) pendingWrites.set(e.id, isTurnRouted)
        // A write with no call id (events kept before ids were recorded) cannot be refused, so it counts at once.
        else turnWrites ??= isTurnRouted ? 'routed' : 'none'
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
      case 'tool':
        toolSeen = true
        break
      case 'compact':
        // The hooks forget loaded skills here, so a later nudge is not "already loaded".
        loaded = new Set()
        timeline.push({ ...stamp(e), kind: 'compact' })
        break
    }
  }
  settle(() => true, isFinal ? 'ignored' : 'pending')
  tallyWritingTurn()

  return { loads, nudges, lastUsed, refs, refsUnloaded, ...measures, timeline, router: routerRule ? router ?? 'never' : 'off' }
}

function addFlat(into: Record<string, number | undefined>, from: Record<string, number | undefined> | undefined) {
  for (const [key, n] of Object.entries(from ?? {})) into[key] = (into[key] ?? 0) + (n ?? 0)
}

/** Adds `from`'s measures into `into`, either of which may predate them. */
function addMeasures(into: Measures, from: Measures) {
  addFlat((into.routes ??= {}), from.routes)
  addFlat((into.writingTurns ??= { ...NO_WRITING_TURNS }), from.writingTurns)
  addFlat((into.holds ??= {}), from.holds)
  addFlat((into.overrides ??= {}), from.overrides)
  addFlat((into.subagents ??= { ...NO_SUBAGENTS }), from.subagents)
}

function addCounts<K extends string>(into: Record<string, Counts<K>>, from: Record<string, Counts<K>>) {
  for (const [row, counts] of Object.entries(from)) {
    for (const [key, n] of Object.entries(counts) as [K, number][]) {
      const target = (into[row] ??= {})
      target[key] = (target[key] ?? 0) + n
    }
  }
}

function addRefs(into: Refs, from: Refs | undefined) {
  for (const [skill, files] of Object.entries(from ?? {})) {
    const target = (into[skill] ??= {})
    for (const [file, n] of Object.entries(files)) target[file] = (target[file] ?? 0) + n
  }
}

function addLastUsed(into: Record<string, number>, from: Record<string, number>) {
  for (const [skill, t] of Object.entries(from)) into[skill] = Math.max(into[skill] ?? 0, t)
}

// The module runs without DOM or Node globals, so no structuredClone.
const copy = <T>(value: T): T => JSON.parse(JSON.stringify(value))

/** Adds one session's summary to the running all-time totals. */
export function addSession(total: AllTime | null, s: SessionSummary): AllTime {
  const out: AllTime = total ? copy(total) : { sessions: 0, loads: {}, nudges: {}, router: {}, lastUsed: {} }
  out.sessions += 1
  addCounts(out.loads, s.loads)
  addCounts(out.nudges, s.nudges)
  out.router[s.router] = (out.router[s.router] ?? 0) + 1
  addLastUsed(out.lastUsed, s.lastUsed)
  addRefs((out.refs ??= {}), s.refs)
  out.refsUnloaded = (out.refsUnloaded ?? 0) + (s.refsUnloaded ?? 0)
  addMeasures(out, s)
  return out
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
  addRefs((out.refs ??= {}), from.refs)
  out.refsUnloaded = (out.refsUnloaded ?? 0) + (from.refsUnloaded ?? 0)
  addMeasures(out, from)
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
 * resume (`earlier`) and what was observed since. The earlier router status
 * stands once it was decided.
 */
export function mergeSummaries(earlier: SessionSummary | null, later: SessionSummary): SessionSummary {
  if (!earlier) return later
  const out = copy(earlier)
  addCounts(out.loads, later.loads)
  addCounts(out.nudges, later.nudges)
  addLastUsed(out.lastUsed, later.lastUsed)
  addRefs((out.refs ??= {}), later.refs)
  out.refsUnloaded = (out.refsUnloaded ?? 0) + (later.refsUnloaded ?? 0)
  addMeasures(out, later)
  if (out.router === 'off' || out.router === 'never') out.router = later.router === 'off' ? out.router : later.router
  return out
}

/**
 * A stored summary whose session is over, or whose events are gone (a resume
 * starts them afresh): a nudge still waiting in it can no longer settle, so it
 * counts as ignored, as it would have at a clean end.
 */
export function closeOpen(s: SessionSummary): SessionSummary {
  const out = copy(s)
  for (const c of Object.values(out.nudges)) {
    if (!c.pending) continue
    c.ignored = (c.ignored ?? 0) + c.pending
    delete c.pending
  }
  return out
}

export const total = (counts: Counts<string> | undefined) => Object.values(counts ?? {}).reduce<number>((sum, n) => sum + (n ?? 0), 0)
