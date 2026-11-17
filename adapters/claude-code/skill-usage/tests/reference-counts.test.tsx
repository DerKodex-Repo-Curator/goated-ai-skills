// Counts per declared reference (Ticket 078): for a reference the registry enforces, how often a hold asked for it
// (fired), then it was read, or its skill was skipped; for an advisory one, its reads beside its skill's loads.

import { expect, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'

import type { DeclaredReferences, UsageEvent } from '../types'
import { addSession, DATA_VERSION, hookEvents, markerEvents, mergeSummaries, summarize, toolUseEvents } from '../hooks/classify'
import { declaredReferences } from '../hooks/registry'
import { reportText } from '../hooks/view'
import { ADAPTER_TEXTS } from './adapter-texts'
import { REGISTRY_FIXTURE } from './registry-fixture'

const prompt = (t = 1): UsageEvent => ({ kind: 'prompt', t, named: [], isTimed: true })
const turnEnd = (t: number): UsageEvent => ({ kind: 'turn-end', t })
const held = (t: number, text: string = ADAPTER_TEXTS.referenceReads) => hookEvents(`PreToolUse:Edit hook error: ${text}`, t, { holdsOnly: true })
const readTool = (path: string, t: number) => toolUseEvents([{ name: 'Read', input: { file_path: path } }], false, t)
const shellRead = (path: string, t: number) => toolUseEvents([{ name: 'Bash', input: { command: `cat ${path}` } }], false, t)

const SEAMS = '/skills/tdd/references/mocking-and-seams.md'
const WAITING = '/skills/diagnose/references/condition-based-waiting.md'

test('a reference-reads hold then read adds one fired and one read for that reference', async () => {
  const s = summarize([prompt(), ...held(2), ...readTool(SEAMS, 3), turnEnd(4)])
  expect(s.refAsks?.tdd).toEqual({ 'references/mocking-and-seams.md': { fired: 1, read: 1 } })
  // The other reference the hold named fired too, and was neither read nor skipped.
  expect(s.refAsks?.diagnose).toEqual({ 'references/condition-based-waiting.md': { fired: 1 } })
})

test('near miss: a shell read, or a Read of another file, is not the read the hold asked for', async () => {
  for (const other of [shellRead(SEAMS, 3), readTool('/skills/tdd/references/test-design.md', 3), readTool('/skills/diagnose/references/mocking-and-seams.md', 3)]) {
    const s = summarize([prompt(), ...held(2), ...other, turnEnd(4)])
    expect(s.refAsks?.tdd).toEqual({ 'references/mocking-and-seams.md': { fired: 1 } })
  }
})

test('near miss: the hold repeated on a retry in the same turn fires once', async () => {
  const s = summarize([prompt(), ...held(2), ...held(3), ...readTool(SEAMS, 4), ...readTool(WAITING, 5), turnEnd(6)])
  expect(s.refAsks).toEqual({
    tdd: { 'references/mocking-and-seams.md': { fired: 1, read: 1 } },
    diagnose: { 'references/condition-based-waiting.md': { fired: 1, read: 1 } },
  })
})

const skip = (skill: string, t: number) => markerEvents(`goated-skip: ${skill}: the double is a shared fixture already`, t)

test('a reference-reads hold declined with a skip line adds one fired and one skipped', async () => {
  const s = summarize([prompt(), ...held(2), ...skip('tdd', 3), turnEnd(4)])
  expect(s.refAsks?.tdd).toEqual({ 'references/mocking-and-seams.md': { fired: 1, skipped: 1 } })
  // A skip line written before the hold, in the same turn, declines it too.
  expect(summarize([prompt(), ...skip('tdd', 2), ...held(3), turnEnd(4)]).refAsks?.tdd).toEqual({ 'references/mocking-and-seams.md': { fired: 1, skipped: 1 } })
})

test("near miss: a skip line naming another skill, or from an earlier turn, does not skip the reference", async () => {
  expect(summarize([prompt(), ...held(2), ...skip('diagnose', 3), turnEnd(4)]).refAsks?.tdd).toEqual({ 'references/mocking-and-seams.md': { fired: 1 } })
  expect(summarize([prompt(), ...skip('tdd', 2), turnEnd(3), prompt(4), ...held(5), turnEnd(6)]).refAsks?.tdd).toEqual({ 'references/mocking-and-seams.md': { fired: 1 } })
})

test('near miss: a reference read before the skip line counts as read, not skipped', async () => {
  const both = ADAPTER_TEXTS.referenceReads.replace('`tdd/references/mocking-and-seams.md`', '`tdd/references/mocking-and-seams.md`, `tdd/references/test-design.md`')
  const s = summarize([prompt(), ...held(2, both), ...readTool(SEAMS, 3), ...skip('tdd', 4), turnEnd(5)])
  expect(s.refAsks?.tdd).toEqual({ 'references/mocking-and-seams.md': { fired: 1, read: 1 }, 'references/test-design.md': { fired: 1, skipped: 1 } })
})

test('each turn that holds again fires again, and All time adds the sessions up', async () => {
  const one = summarize([prompt(1), ...held(2), ...readTool(SEAMS, 3), turnEnd(4), prompt(5), ...held(6), ...skip('tdd', 7), turnEnd(8)], true)
  expect(one.refAsks?.tdd).toEqual({ 'references/mocking-and-seams.md': { fired: 2, read: 1, skipped: 1 } })
  const { timeline: _, ...stored } = one
  const all = addSession(addSession(null, stored), stored)
  expect(all.refAsks?.tdd).toEqual({ 'references/mocking-and-seams.md': { fired: 4, read: 2, skipped: 2 } })
  expect(mergeSummaries(stored, stored).refAsks?.tdd).toEqual({ 'references/mocking-and-seams.md': { fired: 4, read: 2, skipped: 2 } })
})

// ---------- the registry's declared references, read from the installed registry --------------------------------

test("the mod's registry reader finds each skill's references and their status as a full YAML parser does", async () => {
  expect(declaredReferences(REGISTRY_FIXTURE.text)).toEqual(REGISTRY_FIXTURE.declared)
})

test('near miss: a registry with Windows line ends, comments, or no references section reads the same, and text that is no registry reads as none', async () => {
  const text = REGISTRY_FIXTURE.text
  expect(declaredReferences(text.replace(/\n/g, '\r\n'))).toEqual(REGISTRY_FIXTURE.declared)
  expect(declaredReferences(`# installed copy\n${text}`)).toEqual(REGISTRY_FIXTURE.declared)
  expect(declaredReferences('skills:\n  - name: tdd\n    references: []\n')).toEqual({})
  expect(declaredReferences('')).toBeNull()
  expect(declaredReferences('not: a registry\n')).toBeNull()
})

// ---------- what All time and the report show --------------------------------------------------------------------

const DECLARED: DeclaredReferences = {
  tdd: { 'test-design.md': 'enforced', 'mocking-and-seams.md': 'enforced' },
  'code-refinement': { 'refinement-patterns.md': 'advisory' },
  diagnose: { 'condition-based-waiting.md': 'enforced' },
}
const load = (skill: string, t: number): UsageEvent => ({ kind: 'load', t, skill, via: 'tool', isSubagent: false })
const allOf = (events: UsageEvent[]) => {
  const { timeline: _, ...s } = summarize(events, true)
  return addSession(null, s)
}
const section = (text: string) => text.split('## Declared references')[1]?.split('\n## ')[0] ?? ''

test("an advisory reference shows its reads beside its skill's loads", async () => {
  const all = allOf([prompt(1), load('code-refinement', 2), ...readTool('/skills/code-refinement/references/refinement-patterns.md', 3), turnEnd(4), prompt(5), load('code-refinement', 6), turnEnd(7)])
  expect(section(reportText(all, null, DECLARED))).toContain('- code-refinement › refinement-patterns.md: advisory · read 1 in 2 loads')
})

test("near miss: an advisory reference never read shows none read, and another skill's file of that name is not its read", async () => {
  const all = allOf([prompt(1), load('code-refinement', 2), ...readTool('/skills/tdd/references/refinement-patterns.md', 3), turnEnd(4)])
  const text = section(reportText(all, null, DECLARED))
  expect(text).toContain('- code-refinement › refinement-patterns.md: advisory · read 0 in 1 load')
  // A skill the registry declares references for that never loaded nor was asked about shows no row.
  expect(text).not.toContain('diagnose')
})

test('an enforced reference shows how often its hold fired, then it was read or skipped', async () => {
  const all = allOf([prompt(1), ...held(2), ...readTool(SEAMS, 3), ...skip('diagnose', 4), turnEnd(5)])
  const text = section(reportText(all, null, DECLARED))
  expect(text).toContain('- tdd › mocking-and-seams.md: enforced · fired 1 · read 1 · skipped 0')
  expect(text).toContain('- tdd › test-design.md: enforced · fired 0 · read 0 · skipped 0')
  expect(text).toContain('- diagnose › condition-based-waiting.md: enforced · fired 1 · read 0 · skipped 1')
})

test('a reference the registry no longer declares keeps its counts and shows as retired', async () => {
  const all = allOf([prompt(1), ...held(2), ...readTool(SEAMS, 3), turnEnd(4)])
  const text = section(reportText(all, null, { tdd: { 'test-design.md': 'enforced' } }))
  expect(text).toContain('- tdd › mocking-and-seams.md: retired · fired 1 · read 1 · skipped 0')
  expect(all.refAsks?.tdd?.['references/mocking-and-seams.md']).toEqual({ fired: 1, read: 1 })
  // Near miss: a reference of a skill the registry does not know, such as one of your own skills, is not retired.
  const own = allOf([prompt(1), load('my-skill', 2), ...readTool('/skills/my-skill/references/notes.md', 3), turnEnd(4)])
  expect(section(reportText(own, null, DECLARED))).not.toContain('my-skill')
})

test('with no readable registry, the report shows reads as before and no declared references', async () => {
  const all = allOf([prompt(1), ...held(2), ...readTool(SEAMS, 3), turnEnd(4)])
  const text = reportText(all, null, null)
  expect(text).not.toContain('## Declared references')
  expect(text).toContain('- tdd › references/mocking-and-seams.md: 1')
  expect(text).toBe(reportText(all, null))
})

// ---------- the mod reads the installed registry at session start ------------------------------------------------

type On = Parameters<TestBody>[1]

/** Claude Code beneath the mod for one session; `registry`: what reading the registry gives, or an error to reject with. */
function world(on: On, registry: string | Error, asked: string[] = []) {
  const state: Record<string, unknown> = {}
  const store = new Map<string, unknown>()
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('turn.complete', () => ({ text: '' }))
  on('clock.now', () => ({ value: 1_000_000 }))
  on('session.id', () => ({ value: 'running' }))
  on('session.usage', () => ({ value: { context: { breakdown: { skills: { skillFrontmatter: [], totalSkills: 0, includedSkills: 0, tokens: 0 } } } } as never }))
  on('session.messages', () => ({ value: [] }))
  on('session.repo', () => ({ value: null }))
  on('session.root', () => ({ value: '/project' }))
  on('command.register', () => ({ value: { command: 'skill-usage' } }))
  on('ui.open', () => ({ value: { isPlaced: false, reason: 'no pane in this test' } }))
  on('ui.status', () => ({ value: undefined }))
  on('fs.read', (_, e) => {
    asked.push((e as { path: string }).path)
    if (registry instanceof Error) throw registry
    return { value: registry }
  })
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in state ? { value: state[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', (_, e) => {
    const { key, value } = e as { key: string; value: unknown }
    state[key] = value
    return { value: { isSet: true, version: 2 } }
  })
  on('store.keys', () => ({ value: [...store.keys()] }))
  on('store.get', (_, e) => ({ value: store.get((e as { key: string }).key) }))
  on('store.set', (_, e) => {
    const { key, value } = e as { key: string; value: unknown }
    store.set(key, value)
    return { value: undefined }
  })
  on('store.delete', () => ({ value: undefined }))
  return state
}

const PANE = {
  plugin: 'skill-usage',
  component: 'Pane',
  requestId: 'skill-usage',
  props: { title: 'Skill usage', isFocused: false, bodyColumns: 60, placement: 'dock', scroll: { offset: 0, bodyRows: 200 }, view: {} },
} as const

/** Starts a session, records a reference-reads hold then read, and gives the report and the All time tab's text. */
async function seen($: Parameters<TestBody>[0], state: Record<string, unknown>) {
  await $.session.start({ cwd: '/project', surface: null, isInteractive: false })
  state.events = { shape: `events-${DATA_VERSION}`, value: [prompt(1), ...held(2), ...readTool(SEAMS, 3)] }
  const report = String((await $.command.run({ command: 'skill-usage', args: 'report' } as never))?.text ?? '')
  state.tab = 'all'
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  const pane = (await ui.findAll({ type: 'Text' })).map(node => node.text).join('\n')
  await ui.unmount()
  return { report, pane, error: state.lastError ?? null }
}

test("the mod reads the installed registry two folders above its adapter, and All time and the report show each declared reference", async ($, on) => {
  const asked: string[] = []
  const state = world(on, REGISTRY_FIXTURE.text, asked)
  const { report, pane, error } = await seen($, state)
  // Three folders above the mod's own (`adapters/claude-code/skill-usage`): the distribution's root.
  expect(asked.length).toBe(1)
  const path = (asked[0] ?? '').replace(/\\/g, '/')
  expect(path.endsWith('/stack/goated-stack.yaml')).toBe(true)
  expect(path).not.toContain('/adapters/')
  expect(error).toBeNull()
  expect(report).toContain('- tdd › mocking-and-seams.md: enforced · fired 1 · read 1 · skipped 0')
  expect(pane).toContain('Declared references')
  expect(pane).toContain('mocking-and-seams.md')
  expect(pane).toContain('fired 1 · read 1 · skipped 0')
})

/** What the mod shows with `registry` as what reading the registry gives: reads as it does today, and no error. */
async function expectReadsAsToday($: Parameters<TestBody>[0], on: On, registry: string | Error) {
  const { report, pane, error } = await seen($, world(on, registry))
  expect(error).toBeNull()
  expect(report).not.toContain('Declared references')
  expect(report).toContain('- tdd › references/mocking-and-seams.md: 1')
  expect(pane).not.toContain('Declared references')
  expect(pane).toContain('mocking-and-seams.md')
}

test('with no registry where the mod looks, it shows reads as it does today and does not fail', async ($, on) => {
  await expectReadsAsToday($, on, new Error('ENOENT: no such file'))
})

test('near miss: a file there that is no registry is read as none, the same way', async ($, on) => {
  await expectReadsAsToday($, on, 'not: a registry\n')
})

test("a design-reads hold counts for the design skill's reference as a reference-reads hold does", async () => {
  const errors = '/skills/software-design-principles/references/errors.md'
  const read = summarize([prompt(), ...held(2, ADAPTER_TEXTS.designReads), ...readTool(errors, 3), turnEnd(4)])
  expect(read.refAsks?.['software-design-principles']).toEqual({ 'references/errors.md': { fired: 1, read: 1 } })
  const skipped = summarize([prompt(), ...held(2, ADAPTER_TEXTS.designReads), ...skip('software-design-principles', 3), turnEnd(4)])
  expect(skipped.refAsks?.['software-design-principles']).toEqual({ 'references/errors.md': { fired: 1, skipped: 1 } })
})
