// When each reference is read relative to the turn's code changes (Ticket 050):
// before the first, between two, after the last, or in a turn with none; and
// the `goated-design-reads:` lines agents write.

import { expect, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'

import type { UsageEvent } from '../types'
import { addSession, allTimeOf, historyEvents, markerEvents, markerLines, mergeSummaries, summarize, toolUseEvents } from '../hooks/classify'
import { reportText } from '../hooks/view'
import { DESIGN_READS_FIXTURES } from './design-reads-fixtures'

const SDP = 'software-design-principles'
const ref = (t: number, file: string, rest: Partial<UsageEvent & { kind: 'ref' }> = {}): UsageEvent => ({ kind: 'ref', t, skill: SDP, file: `references/${file}`, ...rest })

test('a read before, between and after code changes is recorded with that moment, and a turn with no code change as such', async () => {
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    ref(2, 'process.md'),
    { kind: 'change', t: 3, id: 'c1' },
    ref(4, 'errors.md'),
    { kind: 'change', t: 5, id: 'c2' },
    ref(6, 'red-flags.md'),
    { kind: 'prompt', t: 7, named: [] },
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
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'change', t: 2, id: 'held' },
    { kind: 'refused', t: 3, id: 'held' },
    ref(4, 'process.md'),
    { kind: 'change', t: 5, id: 'ran' },
    ref(6, 'red-flags.md', { isSubagent: true }),
  ])
  expect(s.refMoments?.[SDP]).toEqual({ 'references/process.md': { before: 1 }, 'references/red-flags.md': { after: 1 } })
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
  const s = summarize([{ kind: 'prompt', t: 1, named: [] }, ref(2, 'process.md'), { kind: 'change', t: 3, id: 'c1' }, ref(4, 'red-flags.md')])
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

// ---------- design-reads lines, from stack/fixtures/markers/design-reads.yaml ----------

test('every design-reads line in the grammar fixtures reads as the fixture expects; every invalid one is reported as malformed', async () => {
  for (const { line, expect: want } of DESIGN_READS_FIXTURES.design_reads_lines.valid) expect(markerLines(line).designReads).toEqual([want])
  for (const { line } of DESIGN_READS_FIXTURES.design_reads_lines.invalid) {
    const read = markerLines(line)
    expect(read.designReads).toEqual([])
    expect(read.malformed).toEqual([line])
  }
  for (const { text, expect: want } of DESIGN_READS_FIXTURES.design_reads_replies) {
    const read = markerLines(text)
    expect(read.designReads).toEqual(want.lines)
    expect(read.malformed).toEqual(want.malformed)
  }
})

test('design-reads lines are recorded per session: the files each declares, and the none declarations', async () => {
  const reply = 'goated-design-reads: process.md, errors.md\nThen a lock.\ngoated-design-reads: errors.md, concurrency.md'
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    ...markerEvents(reply, 2),
    ...markerEvents('`goated-design-reads: none: renames one local variable`', 3),
    ...markerEvents('goated-design-reads: none: edits only test data', 4, 'a1'),
    // Malformed: not recorded.
    ...markerEvents('goated-design-reads: none: too short', 5),
  ])
  expect(s.designReads).toEqual({ files: { 'process.md': 1, 'errors.md': 2, 'concurrency.md': 1 }, none: 2 })
  expect(s.timeline.filter(e => e.kind === 'design-reads')).toEqual([
    { kind: 'design-reads', t: 2, form: 'files', files: ['process.md', 'errors.md'] },
    { kind: 'design-reads', t: 2, form: 'files', files: ['errors.md', 'concurrency.md'] },
    { kind: 'design-reads', t: 3, form: 'none', reason: 'renames one local variable' },
    { kind: 'design-reads', t: 4, form: 'none', reason: 'edits only test data', isSubagent: true },
  ])
  // They add up across a resume and across sessions; a summary stored before they were recorded still merges.
  expect(mergeSummaries(s, s).designReads).toEqual({ files: { 'process.md': 2, 'errors.md': 4, 'concurrency.md': 2 }, none: 4 })
  const { designReads: _, ...old } = s
  expect(addSession(addSession(null, old), s).designReads).toEqual(s.designReads)
  expect(mergeSummaries(old, s).designReads).toEqual(s.designReads)
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
  { kind: 'prompt', t: 1, named: [] },
  { kind: 'load', t: 2, skill: SDP, via: 'tool', isSubagent: false },
  { kind: 'design-reads', t: 3, form: 'files', files: ['process.md', 'errors.md'] },
  ref(4, 'process.md'),
  { kind: 'change', t: 5, id: 'c1' },
  ref(6, 'process.md'),
  { kind: 'change', t: 7, id: 'c2' },
  ref(8, 'red-flags.md'),
  { kind: 'design-reads', t: 9, form: 'none', reason: 'renames one local variable' },
]

test('the Session tab shows each reference by moment, and logs and counts design-reads lines', async ($, on) => {
  const text = await paneText($, on, { tab: 'session', events: { shape: 'events-2', value: SESSION_EVENTS } })
  expect(text).toContain('1 before code · 1 between changes')
  expect(text).toContain('1 after code')
  expect(text).toContain('process.md, errors.md')
  expect(text).toContain('none: renames one local variable')
  expect(text).toContain('Design reads: errors.md 1, process.md 1, 1 none')
})

test('the All time tab shows moments across sessions, and reads stored before moments were recorded as not timed', async ($, on) => {
  const text = await paneText($, on, {
    tab: 'all',
    events: { shape: 'events-2', value: SESSION_EVENTS },
    // Stored by an earlier version: four reads of red-flags.md with no moment, and no design-reads counts.
    allTime: { shape: 'all-time-1', value: { sessions: 1, loads: {}, nudges: {}, router: {}, lastUsed: {}, refs: { [SDP]: { 'references/red-flags.md': 4 } } } },
  })
  expect(text).toContain('1 after code · 4 not timed')
  expect(text).toContain('1 before code · 1 between changes')
  expect(text).toContain('Design reads: errors.md 1, process.md 1, 1 none')
})

test('the report lists each reference with its moments and the design-reads counts', async () => {
  const s = summarize(SESSION_EVENTS)
  const { refMoments: _, ...old } = s
  const report = reportText(addSession(addSession(null, old), s), null)
  expect(report).toContain(`- ${SDP} › references/process.md: 4 (1 before code · 1 between changes · 2 not timed)`)
  expect(report).toContain(`- ${SDP} › references/red-flags.md: 2 (1 after code · 1 not timed)`)
  expect(report).toContain('- Design reads: errors.md 2, process.md 2, 2 none')
})
