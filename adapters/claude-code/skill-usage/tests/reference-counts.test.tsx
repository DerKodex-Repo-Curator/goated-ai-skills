// Counts per declared reference (Ticket 078): for a reference the registry enforces, how often a hold asked for it
// (fired), then it was read, or its skill was skipped; for an advisory one, its reads beside its skill's loads.

import { expect, mock, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'

import type { DeclaredReferences, UsageEvent } from '../types'
import { addSession, DATA_VERSION, hookEvents, markerEvents, mergeSummaries, summarize, toolUseEvents } from '../hooks/classify'
import { declaredReferences, registryPlaces } from '../hooks/registry'
import { reportText } from '../hooks/view'
import { ADAPTER_TEXTS } from './adapter-texts'
import { REGISTRY_FIXTURE } from './registry-fixture'
import { USAGE_LOG_SESSION } from './usage-log-session'

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

test('near miss: a Read with a limit or an offset is not the whole read the hold asked for (Ticket 092)', async () => {
  for (const range of [{ limit: 20 }, { offset: 10 }, { limit: 20, offset: 10 }]) {
    const partial = toolUseEvents([{ name: 'Read', input: { file_path: SEAMS, ...range } }], false, 3)
    const s = summarize([prompt(), ...held(2), ...partial, turnEnd(4)])
    expect(s.refAsks?.tdd).toEqual({ 'references/mocking-and-seams.md': { fired: 1 } })
    // The whole read after it is the read.
    const whole = summarize([prompt(), ...held(2), ...partial, ...readTool(SEAMS, 4), turnEnd(5)])
    expect(whole.refAsks?.tdd).toEqual({ 'references/mocking-and-seams.md': { fired: 1, read: 1 } })
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

/** A path as the tests compare it: forward slashes. */
const slashed = (path: string) => path.replace(/\\/g, '/')
/** Files readable only at the path ending `place`: the registry's text there, nothing anywhere else. */
const onlyAt = (place: string, text: string = REGISTRY_FIXTURE.text) => (path: string) => (slashed(path).endsWith(place) ? text : undefined)
const everywhere = (text: string) => () => text
const nowhere = () => undefined

/**
 * Claude Code beneath the mod for one session. `readable`: the text of the file at a path, undefined for one missing,
 * which the read rejects as missing; `asked`: every path the mod asked to read, in order, with forward slashes.
 */
function world(on: On, readable: (path: string) => string | undefined, asked: string[] = []) {
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
    const { path } = e as { path: string }
    // `asked` lists the places tried for the registry; the usage log is read at each start too (hooks/usage-log.ts).
    if (!slashed(path).endsWith('/usage-log.jsonl')) asked.push(slashed(path))
    const text = readable(path)
    if (text === undefined) throw new Error(`ENOENT: no such file, open '${path}'`)
    return { value: text }
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

const INTEGRATED = '/home/dev/.claude/goated/stack/goated-stack.yaml'

test("the mod reads the integrated install's registry under your home folder, and All time and the report show each declared reference", async ($, on) => {
  mock.env(on, { HOME: '/home/dev' })
  const asked: string[] = []
  const state = world(on, onlyAt(INTEGRATED), asked)
  const { report, pane, error } = await seen($, state)
  expect(asked.length).toBe(1)
  expect(asked[0]?.endsWith(INTEGRATED)).toBe(true)
  expect(error).toBeNull()
  expect(report).toContain('- tdd › mocking-and-seams.md: enforced · fired 1 · read 1 · skipped 0')
  expect(pane).toContain('Declared references')
  expect(pane).toContain('mocking-and-seams.md')
  expect(pane).toContain('fired 1 · read 1 · skipped 0')
})

test('near miss: with no HOME, as on Windows, the home folder is USERPROFILE', async ($, on) => {
  mock.env(on, { USERPROFILE: 'C:\\Users\\dev' })
  const { report } = await seen($, world(on, onlyAt('/Users/dev/.claude/goated/stack/goated-stack.yaml')))
  expect(report).toContain('## Declared references')
})

test("the mod reads a source checkout's registry, three folders above its own, when the integrated install has none", async ($, on) => {
  mock.env(on, { HOME: '/home/dev' })
  const asked: string[] = []
  // Any registry path but the integrated install's: the one beside the mod, as `--plugin-dir` runs it from a checkout.
  const { report } = await seen($, world(on, path => (slashed(path).endsWith(INTEGRATED) ? undefined : REGISTRY_FIXTURE.text), asked))
  expect(asked.length).toBe(2)
  expect(asked[1]?.endsWith('/stack/goated-stack.yaml')).toBe(true)
  expect(asked[1]).not.toContain('/adapters/')
  expect(report).toContain('- tdd › mocking-and-seams.md: enforced · fired 1 · read 1 · skipped 0')
})

test("a registry path set in the mod's options is read first", { options: { registryPath: '/opt/goated/stack/goated-stack.yaml' } }, async ($, on) => {
  mock.env(on, { HOME: '/home/dev' })
  const asked: string[] = []
  const { report } = await seen($, world(on, onlyAt('/opt/goated/stack/goated-stack.yaml'), asked))
  expect(asked.length).toBe(1)
  expect(asked[0]?.endsWith('/opt/goated/stack/goated-stack.yaml')).toBe(true)
  expect(report).toContain('## Declared references')
})

test('near miss: a set path with no registry there falls back to the integrated install', { options: { registryPath: '/opt/missing.yaml' } }, async ($, on) => {
  mock.env(on, { HOME: '/home/dev' })
  const asked: string[] = []
  const { report } = await seen($, world(on, onlyAt(INTEGRATED), asked))
  expect(asked.length).toBe(2)
  expect(report).toContain('## Declared references')
})

// ---------- the mod reads the GOATED core's usage log at session start (Ticket 082) --------------------------------

const LOG = '/home/dev/.local/state/goated/usage-log.jsonl'
/** The recorded session's log as another adapter wrote it. */
const PI_LOG = USAGE_LOG_SESSION.logText.replaceAll('"adapter": "claude-code"', '"adapter": "pi-agent"')
/** The registry at the integrated install, and `log` at the core's default log place. */
const withLog = (log: string) => (path: string) => (slashed(path).endsWith(LOG) ? log : onlyAt(INTEGRATED)(path))

test("a session another adapter logged counts in All time and the report, under the log's project key", async ($, on) => {
  mock.env(on, { HOME: '/home/dev' })
  const { report, error } = await seen($, world(on, withLog(PI_LOG)))
  expect(error).toBeNull()
  // The running session and the logged one.
  expect(report).toContain('# Skill usage: 2 sessions')
  expect(report).toContain('- 0123456789: 1 session')
  expect(report).toContain('- doc-sync: 1')
})

test("near miss: the mod's own adapter's sessions in the log are its own reading's, so they add nothing", async ($, on) => {
  mock.env(on, { HOME: '/home/dev' })
  const { report, error } = await seen($, world(on, withLog(USAGE_LOG_SESSION.logText)))
  expect(error).toBeNull()
  expect(report).toContain('# Skill usage: 1 session')
  expect(report).not.toContain('doc-sync')
})

test('a log of a version the mod does not know is refused with its reason, and the rest of the start still runs', async ($, on) => {
  mock.env(on, { HOME: '/home/dev' })
  const later = `${PI_LOG}${JSON.stringify({ log: 2, t: 1, adapter: 'pi-agent', session: 's', project: null, type: 'prompt' })}\n`
  const { report, error } = await seen($, world(on, withLog(later)))
  expect(String(error)).toContain('the GOATED usage log was not read: line 26 of the usage log is of log version 2')
  expect(report).toContain('# Skill usage: 1 session')
  expect(report).toContain('## Declared references')
})

test('from a plugin cache, as the documented install places the mod, the places tried still reach the integrated install', async () => {
  const cache = 'C:/Users/dev/.claude/plugins/cache/goated-skill-usage/skill-usage/0.2.0'
  expect(registryPlaces({ configured: '', home: 'C:/Users/dev', pluginRoot: cache })).toEqual([
    'C:/Users/dev/.claude/goated/stack/goated-stack.yaml',
    `${cache}/../../../stack/goated-stack.yaml`,
  ])
  // Near miss: with no home folder known, only a set path and the checkout's place are tried, the set path first.
  expect(registryPlaces({ configured: '/opt/r.yaml', pluginRoot: cache })).toEqual(['/opt/r.yaml', `${cache}/../../../stack/goated-stack.yaml`])
})

/** What the mod shows when reading the registry gives `readable`: reads as it does today, and no error. */
async function expectReadsAsToday($: Parameters<TestBody>[0], on: On, readable: (path: string) => string | undefined) {
  mock.env(on, { HOME: '/home/dev' })
  const { report, pane, error } = await seen($, world(on, readable))
  expect(error).toBeNull()
  expect(report).not.toContain('Declared references')
  expect(report).toContain('- tdd › references/mocking-and-seams.md: 1')
  expect(pane).not.toContain('Declared references')
  expect(pane).toContain('mocking-and-seams.md')
}

test('with no registry where the mod looks, it shows reads as it does today and does not fail', async ($, on) => {
  await expectReadsAsToday($, on, nowhere)
})

test('near miss: a file there that is no registry is read as none, the same way', async ($, on) => {
  await expectReadsAsToday($, on, everywhere('not: a registry\n'))
})

test("a design-reads hold counts for the design skill's reference as a reference-reads hold does", async () => {
  const errors = '/skills/software-design-principles/references/errors.md'
  const read = summarize([prompt(), ...held(2, ADAPTER_TEXTS.designReads), ...readTool(errors, 3), turnEnd(4)])
  expect(read.refAsks?.['software-design-principles']).toEqual({ 'references/errors.md': { fired: 1, read: 1 } })
  const skipped = summarize([prompt(), ...held(2, ADAPTER_TEXTS.designReads), ...skip('software-design-principles', 3), turnEnd(4)])
  expect(skipped.refAsks?.['software-design-principles']).toEqual({ 'references/errors.md': { fired: 1, skipped: 1 } })
})

// ---------- references a hold names after its skill's ask settled, or beside a load it asks for -------------------

const SDP_REFS = '/skills/software-design-principles/references/'
const sdpCounts = (events: UsageEvent[]) => summarize(events).refAsks?.['software-design-principles']
const concurrencyHold = ADAPTER_TEXTS.designReads.replace('software-design-principles/references/errors.md', 'software-design-principles/references/concurrency.md')

test('a reference a later hold names, after the earlier hold of the turn was met, counts as fired and then read', async () => {
  const counts = sdpCounts([prompt(), ...held(2, ADAPTER_TEXTS.designReads), ...readTool(`${SDP_REFS}errors.md`, 3), ...held(4, concurrencyHold), ...readTool(`${SDP_REFS}concurrency.md`, 5), turnEnd(6)])
  expect(counts).toEqual({ 'references/errors.md': { fired: 1, read: 1 }, 'references/concurrency.md': { fired: 1, read: 1 } })
  // The same for the reference-reads hold: a later hold naming test-design.md after mocking-and-seams.md was read.
  const later = ADAPTER_TEXTS.referenceReads.replace('`tdd/references/mocking-and-seams.md`', '`tdd/references/test-design.md`')
  const tdd = summarize([prompt(), ...held(2), ...readTool(SEAMS, 3), ...held(4, later), ...readTool('/skills/tdd/references/test-design.md', 5), turnEnd(6)]).refAsks?.tdd
  expect(tdd).toEqual({ 'references/mocking-and-seams.md': { fired: 1, read: 1 }, 'references/test-design.md': { fired: 1, read: 1 } })
})

test('near miss: a later hold naming a reference still unread from the earlier one does not fire it again', async () => {
  const counts = sdpCounts([prompt(), ...held(2, ADAPTER_TEXTS.designReads), ...held(3, ADAPTER_TEXTS.designReads), ...readTool(`${SDP_REFS}errors.md`, 4), turnEnd(5)])
  expect(counts).toEqual({ 'references/errors.md': { fired: 1, read: 1 } })
})

test('a design hold made before the skill loads counts the references it names, then their reads', async () => {
  const reads = ['process.md', 'complexity-and-modules.md', 'readability.md'].flatMap((file, i) => readTool(`${SDP_REFS}${file}`, 4 + i))
  const counts = sdpCounts([prompt(), ...held(2, ADAPTER_TEXTS.design), load('software-design-principles', 3), ...reads, turnEnd(8)])
  expect(counts).toEqual({
    'references/process.md': { fired: 1, read: 1 },
    'references/complexity-and-modules.md': { fired: 1, read: 1 },
    'references/readability.md': { fired: 1, read: 1 },
  })
  // Near miss: the load alone reads none of them, so each is fired only.
  expect(sdpCounts([prompt(), ...held(2, ADAPTER_TEXTS.design), load('software-design-principles', 3), turnEnd(4)])?.['references/process.md']).toEqual({ fired: 1 })
})
