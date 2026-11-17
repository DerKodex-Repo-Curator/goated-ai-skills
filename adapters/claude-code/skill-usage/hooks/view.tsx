// The pane's rows and tabs and the report's words: one function per tab, from
// plain data to an element tree, and the markdown report. No engine calls here;
// register.tsx reads the state and passes it in. The picture above each tab is
// picture.tsx's; the words and tones every part shares are meaning.ts's.
//
// Laid out the way the Work Map mod (lot-map) is: one picture, one line that
// says where things stand, then a feed with one row per event, newest first.
// Colour carries meaning and nothing else: green for what succeeded, pale green
// for a nudge declined with a reason, amber for a nudge still waiting, red for a
// nudge not followed. Text colours are theme keys, so the rows read on a light
// theme too.

import type { AllTime, Available, Counts, EarlierHolds, Measures, Origin, Outcome, RefMoment, RefMoments, Refs, RouteForm, SessionSummary, SideSessionKind, SkipReasons, TimelineEntry, WritingTurns } from '../types'
import { forProject, NO_SUBAGENTS, NO_WRITING_TURNS, ORIGINS, OUTCOMES, total } from './classify'
import { BECAUSE, COLOR, followCounts, hookName, OUTCOME_TONE, plural, rateTone, REF_MOMENT, RESULT, ROUTE_FORM, skillName, STATION, UNANSWERED, UNANSWERED_SHORT, unansweredCount, UNTIMED } from './meaning'
import type { Tone, View } from './meaning'
import { badgeWords, picture, PREVIEW_MS, previewTimeline } from './picture'
import type { Badges } from './picture'

export { DECLINED_COLOR, followCounts, READ_COLOR } from './meaning'
export type { View } from './meaning'

/**
 * The widest a tab is laid out, in cells of the surface's code font: about the
 * picture's width, so in a wide pane a row's time, rate or count stays beside
 * its words instead of drifting to the far edge. A narrower pane takes its own width.
 */
export const PANE_COLUMNS = 64

// ---------- rows ------------------------------------------------------------------

// Text takes no mono, size or weight props on this build (the test kit refuses them on every surface), so rows line
// up by real columns, not by padding words in a monospaced face.

/** A run of words in one tone, so one line can carry several meanings. */
type Run = { text: string; tone?: Tone }

/** Words in runs, each run in its own tone; `wrap` lets a long line continue below instead of being cut. */
function words(v: View, runs: Run[], tone: Tone, isWrapped: boolean) {
  const { Text } = v.ui
  const paint = (t: Tone) => ({ color: COLOR[t], dimColor: t === 'dim' })
  if (runs.length === 1) return <Text {...paint(runs[0]?.tone ?? tone)} wrap={isWrapped ? 'wrap' : 'truncate-end'}>{runs[0]?.text}</Text>
  return (
    <Text {...paint(tone)} wrap={isWrapped ? 'wrap' : 'truncate-end'}>
      {runs.map(r => (r.tone && r.tone !== tone ? <Text {...paint(r.tone)}>{r.text}</Text> : r.text))}
    </Text>
  )
}

/**
 * One cell of a row: words in runs, or a drawn element such as a meter; a
 * fixed width in cells, or the room left over (`grow`), which wraps rather than cuts.
 */
type Cell = { runs?: Run[]; node?: ReturnType<typeof words>; width?: number; grow?: true; isRight?: true; tone?: Tone; canShrink?: true }
const cell = (text: string, rest: Omit<Cell, 'runs'> = {}): Cell => ({ runs: [{ text }], ...rest })

/** One line of the pane in columns, as the Work Map's feed: a mark, a kind, the words, and a time at the right. */
function row(v: View, cells: Cell[], tone: Tone) {
  const { Box } = v.ui
  return (
    <Box flexDirection="row" gap={1} alignItems="flex-start">
      {cells.map(c =>
        c.grow ? (
          <Box flexGrow={1} flexShrink={1} minWidth={0}>{c.node ?? words(v, c.runs ?? [], c.tone ?? tone, true)}</Box>
        ) : c.canShrink ? (
          // A name column: its full width when there is room, cut short rather than pushing the row past a narrow pane.
          <Box flexShrink={1} width={c.width} minWidth={6}>{c.node ?? words(v, c.runs ?? [], c.tone ?? tone, false)}</Box>
        ) : (
          <Box flexShrink={0} minWidth={c.width ?? 1} justifyContent={c.isRight ? 'flex-end' : 'flex-start'}>{c.node ?? words(v, c.runs ?? [], c.tone ?? tone, false)}</Box>
        ),
      )}
    </Box>
  )
}

function line(v: View, text: string, tone: Tone = 'plain') {
  return words(v, [{ text }], tone, true)
}

/** A table's heading: its name in bold, and a dim note beside it that wraps under itself in a narrow pane rather than being cut. */
function title(v: View, text: string, note?: string) {
  const { Box, Text } = v.ui
  return (
    <Box marginTop={1} flexDirection="row" gap={1} alignItems="flex-start">
      <Box flexShrink={0}>
        <Text bold>{text}</Text>
      </Box>
      {note && (
        <Box flexShrink={1} minWidth={0}>
          <Text dimColor wrap="wrap">{note}</Text>
        </Box>
      )}
    </Box>
  )
}

/**
 * The smallest fill a non-zero part gets, as a share of its bar, so a small part
 * still shows where the surface draws exact widths. A terminal rounds a bar to
 * whole cells, so on an 8-cell bar a part under about a sixteenth may round away.
 */
const MIN_SHARE = 0.03

/**
 * A bar `width` cells long: one solid fill per coloured part, in order from
 * the left, each as wide as its share of `whole` (the parts' sum unless given,
 * so a list can scale every bar to its largest). Dim parts leave empty space,
 * not a grey track. Widths are percentages, so a graphical surface draws them
 * exactly (3% and 14% differ) where the terminal rounds to whole cells.
 */
function meter(v: View, parts: { n: number; tone: Tone }[], width: number, whole?: number) {
  const { Box } = v.ui
  const of = whole ?? parts.reduce((s, p) => s + p.n, 0)
  const pct = parts.map(p => (of > 0 && p.n > 0 ? Math.round(Math.max(MIN_SHARE, p.n / of) * 100) : 0))
  // The minimum a small part keeps comes out of the largest, so the fills never add up past the bar.
  const over = pct.reduce((s, n) => s + n, 0) - 100
  const largest = pct.indexOf(Math.max(...pct))
  if (over > 0) pct[largest] = (pct[largest] ?? 0) - over
  return (
    <Box flexDirection="row" width={width} height={1}>
      {parts.map((p, i) =>
        (pct[i] ?? 0) > 0 && p.tone !== 'dim' && p.tone !== 'plain' ? <Box width={`${pct[i]}%`} height={1} backgroundColor={COLOR[p.tone]} /> : null,
      )}
    </Box>
  )
}

function clock(t: number): string {
  const d = new Date(t)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const percent = (part: number, whole: number) => (whole === 0 ? '–' : `${Math.round((part / whole) * 100)}%`)

function sumOutcomes(nudges: Record<string, Counts<Outcome>>): Counts<Outcome> {
  const out: Counts<Outcome> = {}
  for (const c of Object.values(nudges)) for (const k of OUTCOMES) out[k] = (out[k] ?? 0) + (c[k] ?? 0)
  return out
}

function byOrigin(loads: Record<string, Counts<Origin>>): Record<Origin, number> {
  const out = Object.fromEntries(ORIGINS.map(o => [o, 0])) as Record<Origin, number>
  for (const c of Object.values(loads)) for (const o of ORIGINS) out[o] += c[o] ?? 0
  return out
}

/** The one line under the picture: where things stand, in words, each count in its meaning's colour. */
function standing(loadCount: number, outcomes: Counts<Outcome>): Run[] {
  const f = followCounts(outcomes)
  const runs: Run[] = [{ text: plural(loadCount, 'skill load') }]
  if (f.settled + f.pending === 0) return [...runs, { text: ' · no hook nudges yet', tone: 'dim' }]
  runs.push({ text: ' · hooks: ' }, { text: `${f.acted - f.declined} followed`, tone: 'good' })
  if (f.declined) runs.push({ text: ' · ' }, { text: `${f.declined} declined`, tone: 'declined' })
  for (const words of unansweredWords(outcomes)) runs.push({ text: ' · ' }, { text: words, tone: 'bad' })
  if (f.pending) runs.push({ text: ' · ' }, { text: `${f.pending} waiting`, tone: 'waiting' })
  return runs
}

/** Each kind of hold nothing answered, as `<n> <kind>`, in the pane's order, those with none left out. */
const unansweredWords = (c: Counts<Outcome>) => UNANSWERED.flatMap(k => (c[k] ? [`${c[k]} ${UNANSWERED_SHORT[k] ?? k}`] : []))

/**
 * The status line: the session's skills, its hooks in the pane's words with
 * counts of none left out, and, for a session stored while a router rule was
 * active, that rule in a word.
 */
export function statusText(s: SessionSummary): string {
  const outcomes = sumOutcomes(s.nudges)
  const f = followCounts(outcomes)
  const hooks = [`${f.acted - f.declined} followed`, ...(f.declined ? [`${f.declined} declined`] : []), ...unansweredWords(outcomes), ...(f.pending ? [`${f.pending} waiting`] : [])]
  const router = { first: 'router ✓', late: 'router late', never: 'router ✗', off: '' }[s.router]
  return [`skills ${Object.keys(s.loads).length}`, f.settled + f.pending > 0 ? `hooks: ${hooks.join(' · ')}` : '', router].filter(Boolean).join(' · ')
}

/** The router rule's line, for a session resumed from a summary stored while that rule was active. */
const ROUTER_LINE: Record<Exclude<SessionSummary['router'], 'off'>, [string, Tone]> = {
  first: ['GOATED router rule: router loaded first', 'good'],
  late: ['GOATED router rule: router loaded, but after other tools', 'waiting'],
  never: ['GOATED router rule: router not loaded yet', 'bad'],
}

/**
 * An override phrase as shown, quoted. The adapter records its commit-message
 * override as "commit message", leaving out the message, so that one reads as
 * the documented phrase `commit message: <text>`; others read as stored.
 */
function overrideLabel(phrase: string): string {
  return `"${phrase === 'commit message' ? 'commit message: <text>' : phrase}"`
}

/**
 * A feed row: its mark, kind and words. A nudge reads as one sentence whatever
 * became of it, each skill it named in the colour of its own result, so a row
 * where one skill loaded and another did not shows both.
 */
function feedRow(entry: TimelineEntry): { mark: string; kind: string; runs: Run[]; tone: Tone; reasons?: string[] } {
  switch (entry.kind) {
    case 'prompt':
      return { mark: '›', kind: 'You', runs: [{ text: 'new message' }], tone: 'dim' }
    case 'compact':
      return { mark: '↻', kind: 'Context', runs: [{ text: 'compacted · checks re-armed' }], tone: 'dim' }
    case 'route': {
      const what = entry.form === 'route' ? `${entry.intensity} · requires ${entry.requires.join(', ')}` : entry.form
      return { mark: '⇢', kind: 'Route', runs: [{ text: what }, ...(entry.isSubagent ? [{ text: ' · by a subagent', tone: 'dim' as const }] : [])], tone: 'plain' }
    }
    case 'override':
      return { mark: '›', kind: 'You', runs: [{ text: `you typed ${entry.phrases.map(overrideLabel).join(', ')}` }], tone: 'waiting' }
    case 'spawn': {
      const task = entry.description ? `: ${entry.description}` : ''
      if (entry.isHeld) return { mark: '⑂', kind: 'Spawn', runs: [{ text: `${entry.agentType} held, not started${task}` }], tone: 'dim' }
      return { mark: '⑂', kind: 'Spawn', runs: [{ text: `${entry.agentType} started${task}` }, ...(entry.isSubagent ? [{ text: ' · by a subagent', tone: 'dim' as const }] : [])], tone: 'plain' }
    }
    case 'subagent-start':
      return { mark: '⑂', kind: 'Spawn', runs: [{ text: 'a subagent received its start message' }], tone: 'dim' }
    case 'body':
      return { mark: '↳', kind: 'Read', runs: [{ text: `${entry.skill} › SKILL.md`, tone: 'read' }, { text: ' · by a subagent', tone: 'dim' }], tone: 'read' }
    case 'ref': {
      const who = entry.isSubagent ? 'by a subagent, ' : ''
      const note = entry.isLoaded ? `${who}after loading it` : `${who}skill not loaded`
      // Amber when its skill had not loaded, as the page's edge is on the picture.
      return { mark: '↳', kind: 'Ref', runs: [{ text: `${entry.skill} › ${entry.file}`, tone: 'read' }, { text: ` · ${note}`, tone: entry.isLoaded ? 'dim' : 'waiting' }], tone: 'read' }
    }
    case 'design-reads': {
      const declared = [...(entry.files.length > 0 ? [entry.files.join(', ')] : []), ...entry.noneReasons.map(r => `none: ${r}`)].join(' · ')
      return { mark: '✎', kind: 'Design', runs: [{ text: `reads ${declared}` }, ...(entry.isSubagent ? [{ text: ' · by a subagent', tone: 'dim' as const }] : [])], tone: 'plain' }
    }
    case 'load':
      // A subagent's load for another reason, such as a hook asking, still says where it happened.
      const where = entry.isSubagent && entry.origin !== 'subagent' ? ', in a subagent' : ''
      return { mark: '+', kind: 'Skill', runs: [{ text: entry.skill, tone: 'good' }, { text: ` · ${BECAUSE[entry.origin]}${where}`, tone: 'dim' }], tone: 'good' }
    case 'nudge': {
      const statuses = entry.skills.map(s => s.status)
      const tone: Tone =
        statuses.some(s => UNANSWERED.includes(s)) ? 'bad'
        : statuses.includes('pending') ? 'waiting'
        : statuses.length > 0 && statuses.every(s => s === 'declined') ? 'declined'
        : 'good'
      const reasons = entry.skills.flatMap(s => (s.status === 'declined' && s.reason ? [s.reason] : []))
      const runs: Run[] = [{ text: `${hookName(entry.hook)}${entry.repeats ? ` ×${entry.repeats}` : ''} → `, tone: 'plain' }]
      if (entry.skills.length === 0) runs.push({ text: entry.holdKind ? (FIX_ASKED[entry.hook] ?? 'asked for a fix, not a skill') : 'no skill named', tone: 'dim' })
      entry.skills.forEach((s, i) => {
        if (i > 0) runs.push({ text: ', ', tone: 'plain' })
        runs.push({ text: `${skillName(s.skill)} ${RESULT[s.status]}`, tone: OUTCOME_TONE[s.status] })
      })
      const mark = tone === 'bad' ? '✕' : tone === 'waiting' ? '●' : tone === 'declined' ? '↷' : '✓'
      return { mark, kind: 'Hook', runs, tone, ...(reasons.length > 0 ? { reasons } : {}) }
    }
  }
}

/**
 * What an adapter hold that names no skill asks for instead: a fix to the call it held, or, once the skill loaded, a
 * read of the change (its diff, or a changed file) before the commit or pull request describes or reviews it.
 */
const FIX_ASKED: Record<string, string> = {
  commit: 'asked to read the change or fix the commit message',
  'pull-request': 'asked to read the change',
  'pr-review': 'asked to read the change',
  spawn: 'asked for the brief template or its headings',
}

/** Each count of a table that is not zero, as `<n> <label>`, joined by commas; empty when none is. */
const countWords = (c: Counts<string> | undefined, label: (k: string) => string = k => k) =>
  Object.entries(c ?? {}).flatMap(([k, n]) => (n ? [`${n} ${label(k)}`] : [])).join(', ')
const routeWords = (m: Measures) => countWords(m.routes, k => ROUTE_FORM[k as RouteForm] ?? k)
const holdWords = (m: Measures) => countWords(m.holds)
/** Writing turns by whether a route line came before the first write, only after it, or never. */
const WRITING: Record<keyof WritingTurns, string> = { routed: 'routed', late: 'routed late', none: 'unrouted' }
const writingWords = (m: Measures) => countWords(m.writingTurns, k => WRITING[k as keyof WritingTurns] ?? k)
/** Design-reads lines: each file with how many replies declared it, most declared first, then the `none` declarations. */
function designReadWords(m: Measures): string {
  const files = Object.entries(m.designReads?.files ?? {}).sort(([a, x], [b, y]) => y - x || a.localeCompare(b))
  const none = m.designReads?.none ?? 0
  return [...files.map(([file, n]) => `${file} ${n}`), ...(none ? [`${none} none`] : [])].join(', ')
}

/** Rows of counts, most counted first, equal ones A to Z, so the order holds between redraws. */
const byMostThenName = ([leftName, leftCounts]: [string, Counts<string>], [rightName, rightCounts]: [string, Counts<string>]) =>
  total(rightCounts) - total(leftCounts) || leftName.localeCompare(rightName)

/** Each skill a routed line required, most required first, as `<skill> <n>`; with `detail`, each followed by its intensities. */
function routedSkillWords(measures: Measures, detail = false): string {
  return Object.entries(measures.routeSkills ?? {})
    .sort(byMostThenName)
    .map(([skill, byIntensity]) => {
      const intensities = Object.entries(byIntensity).flatMap(([intensity, count]) => (count ? [`${intensity} ${count}`] : []))
      return `${skill} ${total(byIntensity)}${detail ? ` (${intensities.join(', ')})` : ''}`
    })
    .join(detail ? ' · ' : ', ')
}

/** What a session tool's call did, in words for a count of them. */
const sideSessionCount = (count: number, kind: SideSessionKind) => (kind === 'card' ? plural(count, 'card') : `${count} started`)
const SESSION_TOOL_PREFIX = 'mcp__ccd_session__'
/** Side sessions across tools, cards then starts, as `1 card, 2 started`. */
function sideSessionWords(measures: Measures): string {
  const sum = (kind: SideSessionKind) => Object.values(measures.sideSessions ?? {}).reduce((sumSoFar, byKind) => sumSoFar + (byKind[kind] ?? 0), 0)
  return (['card', 'start'] as const).flatMap(kind => (sum(kind) ? [sideSessionCount(sum(kind), kind)] : [])).join(', ')
}
/** Side sessions by tool, most used first, each tool by its short name, as `start_session 1 card, 1 started`. */
function sideSessionToolWords(measures: Measures): string {
  return Object.entries(measures.sideSessions ?? {})
    .sort(byMostThenName)
    .map(([tool, byKind]) => {
      const kinds = (['card', 'start'] as const).flatMap(kind => (byKind[kind] ? [sideSessionCount(byKind[kind] ?? 0, kind)] : []))
      return `${tool.replace(SESSION_TOOL_PREFIX, '')} ${kinds.join(', ')}`
    })
    .join(' · ')
}

/**
 * Route lines, routed skills, side sessions, adapter holds, overrides, subagents and design-reads lines in one line of
 * words, each part only when it has a count; undefined when none has.
 */
function measuresText(m: Measures): string | undefined {
  const sub = m.subagents ?? NO_SUBAGENTS
  const subParts = [
    ...(sub.spawns ? [`${sub.spawns} started`] : []),
    ...(sub.starts ? [plural(sub.starts, 'start message')] : []),
    ...(sub.bodyReads ? [`${sub.bodyReads} skill ${sub.bodyReads === 1 ? 'body' : 'bodies'} read`] : []),
  ]
  const overrides = total(m.overrides)
  const parts = [
    ['Routes', routeWords(m)],
    ['Routed skills', routedSkillWords(m)],
    ['Side sessions', sideSessionWords(m)],
    ['Writing turns', writingWords(m)],
    ['Adapter holds', holdWords(m)],
    ['Overrides', overrides ? String(overrides) : ''],
    ['Subagents', subParts.join(', ')],
    ['Design reads', designReadWords(m)],
  ].flatMap(([name, text]) => (text ? [`${name}: ${text}`] : []))
  return parts.length > 0 ? parts.join(' · ') : undefined
}

// ---------- tabs ------------------------------------------------------------------

/** The live tab: the picture with what just happened playing on it, where things stand, and the newest rows. */
/** `preview`: when `/skill-usage preview` started, while it runs; the picture plays its script instead of the session. */
export function sessionTab(v: View, s: SessionSummary, timeline: TimelineEntry[], rows: number, now: number, preview?: number | null) {
  const { Box } = v.ui
  const outcomes = sumOutcomes(s.nudges)
  const loads = byOrigin(s.loads)
  const loadCount = Object.values(loads).reduce((a, b) => a + b, 0)
  const feed = timeline.slice(-rows).reverse()
  const spawns = s.subagents?.spawns ?? 0
  const badges: Badges = { notFollowed: unansweredCount(outcomes), waiting: outcomes.pending ?? 0, readsUnloaded: s.refsUnloaded ?? 0, started: spawns }
  return (
    <Box flexDirection="column">
      {picture(
        v,
        { loads, outcomes, title: 'SKILLS', subtitle: `${Object.keys(s.loads).length} loaded`, refs: readCount(s.refs), spawns, badges },
        `Skill loads this session by who caused them: ${ORIGINS.map(o => `${STATION[o]} ${loads[o]}`).join(', ')}. Reference files read: ${readCount(s.refs)}.` +
          (badgeWords(badges) ? ` Badges: ${badgeWords(badges)}.` : ''),
        { now, timeline: preview != null && now < preview + PREVIEW_MS ? previewTimeline(preview) : timeline },
      )}
      {words(v, standing(loadCount, outcomes), 'plain', true)}
      {s.router !== 'off' && line(v, ...ROUTER_LINE[s.router])}
      {measuresText(s) && line(v, measuresText(s) ?? '', 'plain')}
      {title(v, 'Activity', 'newest first')}
      {feed.length === 0
        ? line(v, 'Nothing yet. Skills and hook nudges show here as they happen.', 'dim')
        : feed.map((entry, i) => {
            const r = feedRow(entry)
            // A row rebuilt from history has no time of its own, only the mod's load time.
            const when = entry.isEarlier ? 'earlier' : clock(entry.t)
            const shown = row(v, [cell(r.mark, { width: 1 }), cell(r.kind, { width: 7 }), { runs: r.runs, grow: true }, cell(when, { width: 7, isRight: true, tone: 'dim' })], r.tone)
            if (!r.reasons) return shown
            // A decline's reason shows while the pointer is on its row (the keyed Box is the hover scope); the
            // terminal has no pointer, so there it is always shown, on its own line under the row.
            const reason = words(v, [{ text: `reason: ${r.reasons.join('; ')}` }], 'declined', true)
            return (
              <Box key={`feed-${entry.t}-${i}`} flexDirection="column">
                {shown}
                {v.surface === 'terminal' ? (
                  <Box paddingLeft={10}>{reason}</Box>
                ) : (
                  <Box display="none" hover={{ display: 'flex' }} paddingLeft={10}>
                    {reason}
                  </Box>
                )}
              </Box>
            )
          })}
      {usageTables(v, s, rows, ' this session')}
    </Box>
  )
}

/**
 * Each hook with what became of its nudges, as a bar split by outcome, each
 * skill with its loads and what most often caused them, and each supporting
 * file with its reads: for all time, or for one session (`suffix` names which
 * in the titles). A count is a bar to scale beside the table's largest, never a
 * ring, which would read as progress towards a limit the count does not have.
 */
function usageTables(
  v: View,
  counts: { nudges: Record<string, Counts<Outcome>>; closeoutItems?: Record<string, Counts<Outcome>>; loads: Record<string, Counts<Origin>>; refs?: Refs; refsUnloaded?: number; refMoments?: RefMoments },
  rows: number,
  suffix: string,
) {
  const { Box } = v.ui
  const hooks = Object.entries(counts.nudges).sort(([, x], [, y]) => total(y) - total(x))
  const items = Object.entries(counts.closeoutItems ?? {}).sort(byMostThenName)
  const skills = Object.entries(counts.loads).sort(([, x], [, y]) => total(y) - total(x))
  const most = Math.max(1, ...skills.map(([, c]) => total(c)))
  const refs = refRows(counts)
  const mostRead = Math.max(1, ...refs.map(r => r.n))
  const nameWidth = Math.min(26, Math.max(12, ...hooks.map(([h]) => hookName(h).length), ...skills.slice(0, rows).map(([s]) => s.length)) + 1)
  // The column a count's bar sits in, as wide as its heading.
  const BAR = 8
  /** One hold or closeout item with what became of it: a bar split by outcome, the counts in words, and the rate. */
  const outcomeRow = (name: string, c: Counts<Outcome>) => {
    const f = followCounts(c)
    const runs: Run[] = [{ text: `${f.acted} of ${f.settled}`, tone: 'dim' }]
    if (f.declined) runs.push({ text: ` · ${f.declined} declined`, tone: 'declined' })
    for (const words of unansweredWords(c)) runs.push({ text: ` · ${words}`, tone: 'bad' })
    if (f.pending) runs.push({ text: ` · ${f.pending} waiting`, tone: 'waiting' })
    return row(
      v,
      [
        cell(name, { width: nameWidth, tone: 'plain', canShrink: true }),
        { node: meter(v, [{ n: f.acted - f.declined, tone: 'good' }, { n: f.declined, tone: 'declined' }, { n: f.settled - f.acted, tone: 'bad' }], BAR), width: BAR },
        { runs, grow: true },
        cell(percent(f.acted, f.settled), { width: 4, isRight: true }),
      ],
      rateTone(f.acted, f.settled),
    )
  }
  return (
    <Box flexDirection="column">
      {title(v, `Hooks${suffix}`, 'how often each hold was handled: followed, or declined with a reason')}
      {hooks.length === 0
        ? line(v, 'No GOATED hook has nudged yet.', 'dim')
        : [
            row(v, [cell('hook', { width: nameWidth, canShrink: true }), cell('outcome', { width: BAR }), cell('', { grow: true }), cell('rate', { width: 4, isRight: true })], 'dim'),
            ...hooks.map(([hook, c]) => outcomeRow(hookName(hook), c)),
          ]}
      {items.length > 0 && [
        title(v, `Closeout items${suffix}`, 'what became of each item a closeout hold listed'),
        row(v, [cell('item', { width: nameWidth, canShrink: true }), cell('outcome', { width: BAR }), cell('', { grow: true }), cell('rate', { width: 4, isRight: true })], 'dim'),
        ...items.map(([label, c]) => outcomeRow(label, c)),
      ]}
      {title(v, `Skills${suffix}`, 'what most often makes each one load')}
      {skills.length === 0
        ? line(v, 'No skill has loaded yet.', 'dim')
        : [
            row(v, [cell('skill', { width: nameWidth, canShrink: true }), cell('loads', { width: BAR }), cell('mostly', { grow: true }), cell('', { width: 4 })], 'dim'),
            ...skills.slice(0, rows).map(([skill, c]) => {
              const top = ORIGINS.reduce((best, o) => ((c[o] ?? 0) > (c[best] ?? 0) ? o : best), ORIGINS[0] as Origin)
              const n = total(c)
              return row(
                v,
                [
                  cell(skill, { width: nameWidth, canShrink: true }),
                  { node: meter(v, [{ n, tone: 'good' }], BAR, most), width: BAR },
                  cell(BECAUSE[top], { grow: true, tone: 'dim' }),
                  cell(String(n), { width: 4, isRight: true }),
                ],
                'plain',
              )
            }),
          ]}
      {title(
        v,
        `References${suffix}`,
        // Reads made before their skill loaded, in words on both tabs: the All time picture draws no badge for them.
        `each skill's supporting files read, most read first${counts.refsUnloaded ? ` · ${counts.refsUnloaded} read before their skill loaded` : ''}`,
      )}
      {refs.length === 0
        ? line(v, 'No skill reference file has been read yet.', 'dim')
        : [
            row(v, [cell('skill › file', { grow: true }), cell('reads', { width: BAR }), cell('', { width: 4 })], 'dim'),
            ...refs.slice(0, rows).map(r => (
              <Box key={`ref-${r.skill}/${r.file}`} flexDirection="column">
                {row(
                  v,
                  [
                    { runs: [{ text: r.skill }, { text: ` › ${r.file}`, tone: 'dim' }], grow: true },
                    { node: meter(v, [{ n: r.n, tone: 'read' }], BAR, mostRead), width: BAR },
                    cell(String(r.n), { width: 4, isRight: true }),
                  ],
                  'plain',
                )}
                <Box paddingLeft={2}>{words(v, [{ text: momentWords(r) }], 'dim', true)}</Box>
              </Box>
            )),
          ]}
    </Box>
  )
}

/** How many supporting files were read in all, rereads included. */
const readCount = (refs: Refs | undefined) => Object.values(refs ?? {}).reduce((sum, files) => sum + total(files), 0)

/** One skill file read: how often in all, and how many of those reads at each moment in their turn. */
type RefRow = { skill: string; file: string; n: number; moments: Counts<RefMoment> }

/** Each skill file read, how often and when, most read first; equal counts A to Z, so the order holds between redraws. */
function refRows(counts: { refs?: Refs; refMoments?: RefMoments }): RefRow[] {
  return Object.entries(counts.refs ?? {})
    .flatMap(([skill, files]) => Object.entries(files).map(([file, n]) => ({ skill, file, n, moments: counts.refMoments?.[skill]?.[file] ?? {} })))
    .sort((a, b) => b.n - a.n || `${a.skill}/${a.file}`.localeCompare(`${b.skill}/${b.file}`))
}

/** A file's reads by moment, in the turn's order, then those with no moment: reads stored before moments were recorded. */
function momentWords(r: RefRow): string {
  const timed = (Object.keys(REF_MOMENT) as RefMoment[]).flatMap(m => (r.moments[m] ? [`${r.moments[m]} ${REF_MOMENT[m]}`] : []))
  const untimed = r.n - total(r.moments)
  return [...timed, ...(untimed > 0 ? [`${untimed} ${UNTIMED}`] : [])].join(' · ')
}

/** Each skill a skip line declined a hold for, A to Z, then each gate, then each reason, most given first, then A to Z. */
function skipReasonRows(reasons: SkipReasons | undefined): { skill: string; gate: string; reasons: [string, number][] }[] {
  return Object.entries(reasons ?? {})
    .sort(([a], [b]) => a.localeCompare(b))
    .flatMap(([skill, gates]) =>
      Object.entries(gates)
        .sort(([a], [b]) => hookName(a).localeCompare(hookName(b)))
        .map(([gate, counts]) => ({ skill, gate, reasons: Object.entries(counts).sort(([a, x], [b, y]) => y - x || a.localeCompare(b)) })),
    )
}

const EARLIER_TITLE = 'Hooks from earlier versions of the mod'
const EARLIER_NOTE = (earlier: EarlierHolds) => `${plural(earlier.sessions, 'session')} stored before summaries carried a version`
/**
 * What earlier versions' summaries held, one line each, in the words of the current tables: each gate's holds, then
 * each closeout item, then each skill and gate a skip line declined with its reasons, most given first.
 */
function earlierLines(earlier: EarlierHolds): string[] {
  const reasonWords = (reasons: [string, number][]) => reasons.map(([reason, count]) => `"${reason}" ×${count}`).join(' · ')
  return [
    ...Object.entries(earlier.nudges).sort(byMostThenName).map(([hook, outcomes]) => `${hookName(hook)}: ${outcomeWords(outcomes)}`),
    ...Object.entries(earlier.closeoutItems ?? {}).sort(byMostThenName).map(([label, outcomes]) => `${label}: ${outcomeWords(outcomes)}`),
    ...skipReasonRows(earlier.skipReasons).map(row => `${row.skill} › ${hookName(row.gate)}: ${reasonWords(row.reasons)}`),
  ]
}

/** How the sessions stored with no project key, by versions before keys were recorded, are named. */
const NOT_RECORDED = 'not recorded'

/** Each project with its sessions, most first, equal ones A to Z, then the sessions stored with no project key (`key` absent). */
function projectRows(all: AllTime): { key?: string; sessions: number }[] {
  const keyed = Object.entries(all.byProject ?? {})
    .map(([key, project]) => ({ key, sessions: project.sessions }))
    .sort((left, right) => right.sessions - left.sessions || left.key.localeCompare(right.key))
  const unkeyed = all.sessions - keyed.reduce((sumSoFar, project) => sumSoFar + project.sessions, 0)
  return [...keyed, ...(unkeyed > 0 ? [{ sessions: unkeyed }] : [])]
}

/**
 * The All time tab's project filter: the project key shown, null for every project; this session's key, if read; and
 * what choosing another does.
 */
export type ProjectFilter = { shown: string | null; own?: string; choose: (key: string | null) => unknown }

/** The projects All time can be filtered to, each with a button that shows it alone, and one that shows them all. */
function projectChooser(view: View, all: AllTime, filter: ProjectFilter) {
  const { Box, Button } = view.ui
  const choice = (id: string, key: string | null, text: string) => (
    <Box key={`project-${id}`} flexDirection="row" gap={1}>
      <Button label={filter.shown === key ? 'Shown' : 'Show'} variant={filter.shown === key ? 'primary' : 'secondary'} onPress={() => filter.choose(key)} />
      {line(view, text, filter.shown === key ? 'plain' : 'dim')}
    </Box>
  )
  return [
    title(view, 'Projects', 'show one project alone; each key stands for a folder, which is not stored'),
    choice('all', null, `every project · ${plural(all.sessions, 'session')}`),
    ...projectRows(all).map(project =>
      project.key === undefined
        ? line(view, `${NOT_RECORDED} · ${plural(project.sessions, 'session')}, stored before projects were`, 'dim')
        : choice(project.key, project.key, `${project.key}${project.key === filter.own ? ' · this project' : ''} · ${plural(project.sessions, 'session')}`),
    ),
  ]
}

/**
 * Totals across sessions: the still picture, each hook's follow rate as a bar, and what makes each skill load; with
 * `filter`, for the project it shows, and a chooser of projects once any session carries a project key.
 */
export function allTimeTab(v: View, everything: AllTime, rows: number, filter?: ProjectFilter) {
  const { Box } = v.ui
  const all = forProject(everything, filter?.shown ?? null)
  const outcomes = sumOutcomes(all.nudges)
  const loads = byOrigin(all.loads)
  const loadCount = Object.values(loads).reduce((a, b) => a + b, 0)
  const ruled = (all.router.first ?? 0) + (all.router.late ?? 0) + (all.router.never ?? 0)
  const first = all.router.first ?? 0
  return (
    <Box flexDirection="column">
      {picture(
        v,
        // The long view: totals only, no per-case badges.
        { loads, outcomes, title: 'ALL TIME', subtitle: plural(all.sessions, 'session'), refs: readCount(all.refs), spawns: all.subagents?.spawns ?? 0 },
        `Skill loads across ${plural(all.sessions, 'session')} by who caused them: ${ORIGINS.map(o => `${STATION[o]} ${loads[o]}`).join(', ')}. Reference files read: ${readCount(all.refs)}.`,
      )}
      {words(v, [{ text: `${plural(all.sessions, 'session')} · ` }, ...standing(loadCount, outcomes)], 'plain', true)}
      {ruled > 0 && line(v, `GOATED router rule: router loaded first in ${first} of ${plural(ruled, 'session')}`, rateTone(first, ruled))}
      {measuresText(all) && line(v, measuresText(all) ?? '', 'plain')}
      {filter && everything.byProject && projectChooser(v, everything, filter)}
      {usageTables(v, all, rows, '')}
      {all.earlier && [
        title(v, EARLIER_TITLE, `${EARLIER_NOTE(all.earlier)}; their holds, closeout items and skip reasons add to no count here`),
        ...earlierLines(all.earlier).map(text => line(v, text, 'dim')),
      ]}
      {title(v, 'Skip reasons', 'why a skip line declined a hold, by skill and hold')}
      {skipReasonRows(all.skipReasons).length === 0
        ? line(v, 'No skip line has declined a hold yet.', 'dim')
        : skipReasonRows(all.skipReasons).map(r => (
            <Box key={`skip-${r.skill}/${r.gate}`} flexDirection="column">
              {line(v, `${r.skill} › ${hookName(r.gate)}`, 'plain')}
              {r.reasons.slice(0, rows).map(([reason, n]) => (
                <Box key={reason} paddingLeft={2}>
                  {words(v, [{ text: `"${reason}" ×${n}` }], 'declined', true)}
                </Box>
              ))}
            </Box>
          ))}
    </Box>
  )
}

/**
 * Your own skills: how many have ever loaded, as a bar, then two lists: those
 * that loaded, most loaded first, each with a bar to scale beside the most
 * loaded and its share of all their loads as a percentage; and those that
 * never have, A to Z.
 */
export function unusedTab(v: View, all: AllTime, avail: Available | null) {
  const { Box } = v.ui
  if (!avail) return line(v, 'The skill list is read at your next message.', 'dim')
  const byName = (a: string, b: string) => a.localeCompare(b)
  const unused = avail.own.filter(s => !all.loads[s]).sort(byName)
  const loadsOf = (s: string) => total(all.loads[s])
  // Most loaded first; equal counts A to Z, so the order never shuffles between redraws.
  const loaded = avail.own.filter(s => all.loads[s]).sort((a, b) => loadsOf(b) - loadsOf(a) || byName(a, b))
  const allLoads = loaded.reduce((sum, s) => sum + loadsOf(s), 0)
  // Bars scale to the most loaded skill, so it fills its column and every other bar keeps its true proportion to it.
  const mostLoads = Math.max(1, ...loaded.map(loadsOf))
  const SHARE_BAR = 16
  return (
    <Box flexDirection="column">
      {avail.included < avail.total && line(v, `✕ Only ${avail.included} of ${avail.total} skills fit the skill listing: the rest are invisible to Claude.`, 'bad')}
      {title(v, 'Your skills', `across ${plural(all.sessions, 'session')}`)}
      {row(
        v,
        [
          { node: meter(v, [{ n: loaded.length, tone: 'good' }], 24, avail.own.length), width: 24 },
          {
            runs: [
              { text: `${loaded.length} of ${avail.own.length} have loaded`, tone: rateTone(loaded.length, avail.own.length) },
              { text: ` · ${percent(loaded.length, avail.own.length)}`, tone: 'dim' },
            ],
            grow: true,
          },
        ],
        'plain',
      )}
      {line(v, `${plural(avail.names.length - avail.own.length, 'built-in and plugin skill')} are not counted here.`, 'dim')}
      {title(v, `Loaded · ${loaded.length}`, `most loaded first; each one's share of all ${allLoads} loads, bars to scale`)}
      {loaded.length === 0
        ? line(v, 'None of your skills has loaded yet.', 'dim')
        : loaded.map(s =>
            row(
              v,
              [
                cell('✓', { width: 1 }),
                cell(s, { grow: true }),
                { node: meter(v, [{ n: loadsOf(s), tone: 'good' }], SHARE_BAR, mostLoads), width: SHARE_BAR },
                cell(percent(loadsOf(s), allLoads), { width: 4, isRight: true, tone: 'plain' }),
                cell(`×${loadsOf(s)}`, { width: 4, isRight: true, tone: 'dim' }),
              ],
              'good',
            ),
          )}
      {title(v, `Never loaded · ${unused.length}`, unused.length > 0 ? 'A to Z; candidates for a hook nudge or a better description' : undefined)}
      {unused.length === 0
        ? line(v, 'Every one of your skills has loaded at least once.', 'good')
        : unused.map(s => row(v, [cell('·', { width: 1 }), cell(s, { grow: true })], 'dim'))}
    </Box>
  )
}

// ---------- report ----------------------------------------------------------------

/** What became of a hold or closeout item, in the report's words: how many were handled, then each outcome. */
function outcomeWords(c: Counts<Outcome>): string {
  const f = followCounts(c)
  const parts = OUTCOMES.filter(k => c[k]).map(k => `${RESULT[k]} ${c[k]}`)
  return `${f.acted} of ${f.settled} handled (${percent(f.acted, f.settled)})${parts.length ? ` · ${parts.join(' · ')}` : ''}`
}

/** `/skill-usage report`: the All time and Unused tabs as markdown, in the pane's own words. */
export function reportText(all: AllTime, avail: Available | null): string {
  const out = [`# Skill usage: ${plural(all.sessions, 'session')}`, '', '## Hooks', '']
  for (const [hook, c] of Object.entries(all.nudges).sort(([, x], [, y]) => total(y) - total(x))) out.push(`- ${hookName(hook)}: ${outcomeWords(c)}`)
  out.push('', '## Closeout items', '')
  const items = Object.entries(all.closeoutItems ?? {}).sort(byMostThenName)
  if (items.length === 0) out.push('(none recorded)')
  for (const [label, c] of items) out.push(`- ${label}: ${outcomeWords(c)}`)
  if (all.earlier) {
    out.push('', `## ${EARLIER_TITLE}`, '', `${EARLIER_NOTE(all.earlier)}.`, '')
    for (const text of earlierLines(all.earlier)) out.push(`- ${text}`)
  }
  const projects = projectRows(all)
  if (projects.length > 0) {
    out.push('', '## Projects', '')
    for (const project of projects) out.push(`- ${project.key ?? NOT_RECORDED}: ${plural(project.sessions, 'session')}`)
  }
  const ruled = (all.router.first ?? 0) + (all.router.late ?? 0) + (all.router.never ?? 0)
  if (ruled > 0) out.push('', `GOATED router rule: router loaded first in ${all.router.first ?? 0} of ${plural(ruled, 'session')}.`)
  out.push('', '## Skills', '')
  for (const [skill, c] of Object.entries(all.loads).sort(([, x], [, y]) => total(y) - total(x))) {
    out.push(`- ${skill}: ${total(c)} (${ORIGINS.filter(o => c[o]).map(o => `${BECAUSE[o]} ${c[o]}`).join(' · ')})`)
  }
  const overrides = Object.entries(all.overrides ?? {}).sort(([, x], [, y]) => y - x).map(([phrase, n]) => `${overrideLabel(phrase)} ${n}`)
  const sub = all.subagents ?? NO_SUBAGENTS
  const writes = all.writingTurns ?? NO_WRITING_TURNS
  out.push('', '## Routes and adapter holds', '')
  out.push(`- Route lines: ${routeWords(all) || 'none'}`)
  out.push(`- Routed skills: ${routedSkillWords(all, true) || 'none'}`)
  out.push(`- Side sessions: ${sideSessionToolWords(all) || 'none'}`)
  out.push(`- Writing turns: ${writes.routed} routed before the first write · ${writes.late} routed only after it · ${writes.none} with no route line`)
  out.push(`- Adapter holds: ${holdWords(all) || 'none'}`)
  out.push(`- Overrides: ${overrides.join(' · ') || 'none'}`)
  out.push(`- Design reads: ${designReadWords(all) || 'none written'}`)
  out.push(`- Subagents: ${sub.spawns} started${sub.starts ? ` · ${plural(sub.starts, 'start message')}` : ''} · ${sub.bodyReads} skill bodies read`)
  const skips = skipReasonRows(all.skipReasons)
  out.push('', '## Skip reasons', '')
  if (skips.length === 0) out.push('(none given yet)')
  for (const r of skips) out.push(`- ${r.skill} › ${hookName(r.gate)}: ${r.reasons.map(([reason, n]) => `"${reason}" ×${n}`).join(' · ')}`)
  const refs = refRows(all)
  out.push('', '## References', '')
  if (refs.length === 0) out.push('(none read yet)')
  for (const r of refs) out.push(`- ${r.skill} › ${r.file}: ${r.n} (${momentWords(r)})`)
  const unused = (avail?.own ?? []).filter(s => !all.loads[s])
  out.push('', `## Your skills never loaded (${unused.length})`, '', unused.join(', ') || '(none)')
  if (avail && avail.included < avail.total) out.push('', `Only ${avail.included} of ${avail.total} skills fit the skill listing.`)
  return out.join('\n')
}
