// When each reference is read relative to the turn's code changes (Ticket 050):
// before the first, between two, after the last, or in a turn with none; and
// that a `goated-design-reads:` line, which left the grammar, records nothing.

import { expect, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'

import type { UsageEvent } from '../types'
import { addSession, allTimeOf, historyEvents, markerEvents, markerLines, mergeSummaries, promptEvents, rowEvents, summarize, toolUseEvents } from '../hooks/classify'
import type { Row } from '../hooks/classify'
import { reportText } from '../hooks/view'

const SDP = 'software-design-principles'
const ref = (t: number, file: string, rest: Partial<UsageEvent & { kind: 'ref' }> = {}): UsageEvent => ({ kind: 'ref', t, skill: SDP, file: `references/${file}`, ...rest })
/** A typed prompt as this version records it: its turn's code changes are recorded, so its reads can be timed. */
const prompt = (t: number): UsageEvent => ({ kind: 'prompt', t, named: [], isTimed: true })

test('a read before, between and after code changes is recorded with that moment, and a turn with no code change as such', async () => {
  const s = summarize([
    prompt(1),
    ref(2, 'process.md'),
    { kind: 'change', t: 3, id: 'c1' },
    ref(4, 'errors.md'),
    { kind: 'change', t: 5, id: 'c2' },
    ref(6, 'red-flags.md'),
    prompt(7),
    ref(8, 'coding.md'),
  ])
  expect(s.refMoments).toEqual({
    [SDP]: {
      'references/process.md': { before: 1 },
      'references/errors.md': { between: 1 },
      'references/red-flags.md': { after: 1 },
      'references/coding.md': { 'no-change': 1 },
    },
  })
})

test("a code change is an edit tool's call on a code file, by the main agent or a subagent; docs and shell commands are not", async () => {
  const edit = (name: string, input: Record<string, unknown>) => [{ id: 'e1', name, input }]
  const changes = (events: UsageEvent[]) => events.filter(e => e.kind === 'change')
  expect(changes(toolUseEvents(edit('Edit', { file_path: 'src/export.py', new_string: 'x' }), false, 1))).toEqual([{ kind: 'change', t: 1, id: 'e1' }])
  expect(changes(toolUseEvents(edit('Write', { file_path: 'C:\\repo\\hooks\\view.TSX', content: 'x' }), false, 1))).toEqual([{ kind: 'change', t: 1, id: 'e1' }])
  expect(changes(toolUseEvents(edit('MultiEdit', { file_path: 'lib/a.go', edits: [] }), false, 1))).toEqual([{ kind: 'change', t: 1, id: 'e1' }])
  expect(changes(toolUseEvents(edit('NotebookEdit', { notebook_path: 'n/x.ipynb', new_source: 'x' }), false, 1))).toEqual([{ kind: 'change', t: 1, id: 'e1' }])
  expect(changes(toolUseEvents(edit('Edit', { file_path: 'src/x.ts' }), true, 1, 'a1'))).toEqual([{ kind: 'change', t: 1, id: 'e1', isSubagent: true }])
  // Not code: docs, settings, a file with no extension, a folder named like code; nor a Read of a code file.
  for (const path of ['README.md', 'config.yaml', 'Makefile', 'src.py/notes']) {
    expect(changes(toolUseEvents(edit('Edit', { file_path: path }), false, 1))).toEqual([])
  }
  expect(changes(toolUseEvents(edit('Read', { file_path: 'src/x.ts' }), false, 1))).toEqual([])
  expect(changes(toolUseEvents(edit('Bash', { command: 'echo x > src/x.ts' }), false, 1))).toEqual([])
})

test('a refused edit changed nothing, so a read after it is still before the first change', async () => {
  const s = summarize([
    prompt(1),
    { kind: 'change', t: 2, id: 'held' },
    { kind: 'refused', t: 3, id: 'held' },
    ref(4, 'process.md'),
    { kind: 'change', t: 5, id: 'ran' },
    ref(6, 'red-flags.md', { isSubagent: true }),
  ])
  expect(s.refMoments?.[SDP]).toEqual({ 'references/process.md': { before: 1 }, 'references/red-flags.md': { after: 1 } })
})

test("reads in a turn whose prompt an earlier version stored, or before any prompt, are not timed: that version recorded no code changes", async () => {
  expect(promptEvents('Add CSV export.', [], 1)).toEqual([prompt(1)])
  const s = summarize([
    // The log's start was trimmed mid-turn: no prompt says whether this turn's changes were recorded.
    ref(1, 'decoupling.md'),
    // Stored before the upgrade: the turn edited code, but no change was recorded.
    { kind: 'prompt', t: 2, named: [] },
    ref(3, 'process.md'),
    ref(4, 'red-flags.md'),
    prompt(5),
    ref(6, 'errors.md'),
  ])
  expect(s.refs?.[SDP]).toEqual({ 'references/decoupling.md': 1, 'references/process.md': 1, 'references/red-flags.md': 1, 'references/errors.md': 1 })
  expect(s.refMoments).toEqual({ [SDP]: { 'references/errors.md': { 'no-change': 1 } } })
})

test("a subagent's edit refused on the live path changed nothing", async () => {
  const rows: Row[] = [
    { door: 'prompt', message: { content: [{ type: 'text', text: 'Add CSV export.' }] } },
    { door: 'response', agentId: 'a1', message: { content: [{ type: 'tool_use', id: 'e1', name: 'Edit', input: { file_path: 'src/export.py' } }] } },
    { door: 'tool-result', agentId: 'a1', message: { content: [{ type: 'tool_result', tool_use_id: 'e1', is_error: true, content: 'held' }] } },
    { door: 'response', message: { content: [{ type: 'tool_use', id: 'r1', name: 'Read', input: { file_path: `/h/.claude/skills/${SDP}/references/process.md` } }] } },
  ]
  const events: UsageEvent[] = []
  for (const row of rows) {
    const boundary = [...events].reverse().find(e => e.kind === 'response' || e.kind === 'results')?.kind as 'response' | 'results' | undefined
    events.push(...rowEvents(row, [SDP], 1, { lastKind: events.at(-1)?.kind, lastBoundary: boundary }))
  }
  expect(events.filter(e => e.kind === 'change' || e.kind === 'refused')).toEqual([
    { kind: 'change', t: 1, id: 'e1', isSubagent: true },
    { kind: 'refused', t: 1, id: 'e1' },
  ])
  expect(summarize(events).refMoments?.[SDP]).toEqual({ 'references/process.md': { 'no-change': 1 } })
})

test('history rebuilds code changes, so a mod that joined late still times the reads', async () => {
  const s = summarize(
    historyEvents(
      [
        { role: 'user', content: [{ type: 'text', text: 'Add CSV export.' }] },
        { role: 'assistant', content: [{ type: 'tool_use', id: 'r1', name: 'Read', input: { file_path: `/h/.claude/skills/${SDP}/references/process.md` } }] },
        { role: 'user', content: [{ type: 'tool_result', tool_use_id: 'r1', content: 'ok' }] },
        { role: 'assistant', content: [{ type: 'tool_use', id: 'w1', name: 'Write', input: { file_path: 'src/export.py', content: 'x' } }] },
        { role: 'user', content: [{ type: 'tool_result', tool_use_id: 'w1', content: 'ok' }] },
      ],
      [SDP],
      9,
    ),
  )
  expect(s.refMoments?.[SDP]).toEqual({ 'references/process.md': { before: 1 } })
})

test('moments add up across a resume and across sessions, and an older summary with no moments still merges', async () => {
  const s = summarize([prompt(1), ref(2, 'process.md'), { kind: 'change', t: 3, id: 'c1' }, ref(4, 'red-flags.md')])
  const both = { 'references/process.md': { before: 2 }, 'references/red-flags.md': { after: 2 } }
  expect(mergeSummaries(s, s).refMoments?.[SDP]).toEqual(both)
  expect(addSession(addSession(null, s), s).refMoments?.[SDP]).toEqual(both)
  // A summary stored before moments were recorded: its reads still count in refs, with no moment.
  const { refMoments: _, ...old } = s
  const merged = mergeSummaries(old, s)
  expect(merged.refs?.[SDP]).toEqual({ 'references/process.md': 2, 'references/red-flags.md': 2 })
  expect(merged.refMoments?.[SDP]).toEqual({ 'references/process.md': { before: 1 }, 'references/red-flags.md': { after: 1 } })
  expect(addSession(addSession(null, old), s).refMoments?.[SDP]).toEqual({ 'references/process.md': { before: 1 }, 'references/red-flags.md': { after: 1 } })
  // All-time totals stored before moments were recorded fold in too, past the cap.
  const { refMoments: __, ...oldTotal } = addSession(null, s)
  const folded = allTimeOf([['s:a', { t: 1, summary: s }], ['s:b', { t: 2, summary: old }]], oldTotal, 1, 's:none')
  expect(folded.total?.refs?.[SDP]).toEqual({ 'references/process.md': 3, 'references/red-flags.md': 3 })
  expect(folded.total?.refMoments?.[SDP]).toEqual({ 'references/process.md': { before: 1 }, 'references/red-flags.md': { after: 1 } })
})

// ---------- a design-reads line, which left the grammar (Ticket 089) ----------

test('a design-reads line is prose: no marker, not malformed, and nothing recorded', async () => {
  const reply = 'goated-design-reads: process.md, errors.md\n`goated-design-reads: none: renames one local variable`\ngoated-design-reads: references/process.md'
  expect(markerLines(reply)).toEqual({ route: null, skips: [], malformed: [] })
  expect(markerEvents(reply, 2)).toEqual([])
  const s = summarize([prompt(1), ...markerEvents(reply, 2), ...markerEvents('goated-design-reads: errors.md', 3, 'a1')])
  expect('designReads' in s).toBe(false)
  // The near miss: a skip line beside it is still read.
  expect(markerEvents(`${reply}\ngoated-skip: tdd: no test surface exists here`, 4)).toEqual([
    { kind: 'skip', t: 4, skill: 'tdd', reason: 'no test surface exists here' },
  ])
})

// ---------- the pane ------------------------------------------------------------------

const PANE = {
  plugin: 'skill-usage',
  component: 'Pane',
  requestId: 'skill-usage',
  props: { title: 'Skill usage', isFocused: false, bodyColumns: 60, placement: 'dock', scroll: { offset: 0, bodyRows: 40 }, view: {} },
} as const

/** Mounts the pane over `stored` state and hands back every text it shows, one per line. */
async function paneText(...[$, on, stored]: [...Parameters<TestBody>, Record<string, unknown>]): Promise<string> {
  on('clock.now', () => ({ value: 100_000 }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', () => ({ value: { isSet: true, version: 2 } }))
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  const text = (await ui.findAll({ type: 'Text' })).map(t => t.text).join('\n')
  await ui.unmount()
  return text
}

const SESSION_EVENTS: UsageEvent[] = [
  prompt(1),
  { kind: 'load', t: 2, skill: SDP, via: 'tool', isSubagent: false },
  ref(4, 'process.md'),
  { kind: 'change', t: 5, id: 'c1' },
  ref(6, 'process.md'),
  { kind: 'change', t: 7, id: 'c2' },
  ref(8, 'red-flags.md'),
]

test('the Session tab shows each reference by moment, and no design-reads count', async ($, on) => {
  const text = await paneText($, on, { tab: 'session', events: { shape: 'events-4', value: SESSION_EVENTS } })
  expect(text).toContain('1 before code · 1 between changes')
  expect(text).toContain('1 after code')
  expect(text).not.toContain('Design reads')
})

test('the All time tab shows moments across sessions, and reads stored before moments were recorded as not timed', async ($, on) => {
  const text = await paneText($, on, {
    tab: 'all',
    events: { shape: 'events-4', value: SESSION_EVENTS },
    // Stored by an earlier version: four reads of red-flags.md with no moment, and design-reads counts,
    // which no longer show (Ticket 089).
    allTime: { shape: 'all-time-2', value: { sessions: 1, loads: {}, nudges: {}, router: {}, lastUsed: {}, refs: { [SDP]: { 'references/red-flags.md': 4 } }, designReads: { files: { 'errors.md': 3 }, none: 1 } } },
  })
  expect(text).toContain('1 after code · 4 not timed')
  expect(text).toContain('1 before code · 1 between changes')
  expect(text).not.toContain('Design reads')
})

test('the report lists each reference with its moments, and no design-reads counts', async () => {
  const s = summarize(SESSION_EVENTS)
  const { refMoments: _, ...old } = s
  const report = reportText(addSession(addSession(null, old), s), null)
  expect(report).toContain(`- ${SDP} › references/process.md: 4 (1 before code · 1 between changes · 2 not timed)`)
  expect(report).toContain(`- ${SDP} › references/red-flags.md: 2 (1 after code · 1 not timed)`)
  expect(report).not.toContain('Design reads')
})
