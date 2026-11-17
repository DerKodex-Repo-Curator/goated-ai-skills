// What the router chose, which side sessions were started, and which project
// and mod version each summary comes from (Ticket 076).

import { expect, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'

import type { SessionSummary, UsageEvent } from '../types'
import { addSession, allTimeOf, DATA_VERSION, markerEvents, mergeSummaries, rowEvents, summarize, toolUseEvents } from '../hooks/classify'
import { errorText } from '../hooks/holds'
import { projectKey } from '../hooks/project'
import { reportText } from '../hooks/view'

const prompt = (t = 1): UsageEvent => ({ kind: 'prompt', t, named: [] })
const START = 'mcp__ccd_session__start_session'
const HAND_OFF = 'mcp__ccd_session__hand_off_to_session'

const PANE = {
  plugin: 'skill-usage',
  component: 'Pane',
  requestId: 'skill-usage',
  props: { title: 'Skill usage', isFocused: false, bodyColumns: 60, placement: 'dock', scroll: { offset: 0, bodyRows: 80 }, view: {} },
} as const

/** The pane's text with the mod's state as `stored` gives it. */
async function paneText(...[$, on, stored]: [...Parameters<TestBody>, Record<string, unknown>]): Promise<string> {
  on('clock.now', () => ({ value: 100_000 }))
  on('state.get', (_, request) => {
    const key = (request as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', () => ({ value: { isSet: true, version: 2 } }))
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  const text = (await ui.findAll({ type: 'Text' })).map(node => node.text).join('\n')
  await ui.unmount()
  return text
}

/** A stored summary of one session that loaded `skill`, in `project` when given. */
const sessionIn = (skill: string, project?: string): SessionSummary => {
  const { timeline: _, ...summary } = summarize([prompt(), { kind: 'load', t: 2, skill, via: 'tool', isSubagent: false }])
  return { ...summary, ...(project ? { project } : {}) }
}

// ---------- routes ----------------------------------------------------------------

test('a route line requiring tdd and doc-sync adds one to each, with the route intensity', async () => {
  const summary = summarize([prompt(), ...markerEvents('goated-route: standard | requires: tdd, doc-sync', 2)])
  expect(summary.routeSkills).toEqual({ tdd: { standard: 1 }, 'doc-sync': { standard: 1 } })
  // A second route line in another reply adds again, under its own intensity.
  const twice = summarize([prompt(), ...markerEvents('goated-route: standard | requires: tdd, doc-sync', 2), ...markerEvents('goated-route: full | requires: tdd', 3)])
  expect(twice.routeSkills).toEqual({ tdd: { standard: 1, full: 1 }, 'doc-sync': { standard: 1 } })
  // Near misses: a direct route requires nothing, and a line repeating a skill fails the grammar and adds none.
  expect(summarize([prompt(), ...markerEvents('goated-route: direct', 2)]).routeSkills).toEqual({})
  expect(summarize([prompt(), ...markerEvents('goated-route: standard | requires: tdd, tdd', 2)]).routeSkills).toEqual({})
})

test('routed skills add up across sessions, and the report and pane show them', async ($, on) => {
  const one = summarize([prompt(), ...markerEvents('goated-route: standard | requires: tdd, doc-sync', 2)])
  const all = addSession(addSession(null, one), one)
  expect(all.routeSkills).toEqual({ tdd: { standard: 2 }, 'doc-sync': { standard: 2 } })
  expect(reportText(all, null)).toContain('- Routed skills: doc-sync 2 (standard 2) · tdd 2 (standard 2)')
  // Near miss: with no route line, the report says none.
  expect(reportText(addSession(null, summarize([prompt()])), null)).toContain('- Routed skills: none')
  const text = await paneText($, on, { tab: 'session', events: { shape: `events-${DATA_VERSION}`, value: [prompt(), ...markerEvents('goated-route: full | requires: tdd', 2)] } })
  expect(text).toContain('Routed skills: tdd 1')
})

// ---------- side sessions ---------------------------------------------------------

const call = (id: string, name: string, input: Record<string, unknown>) => toolUseEvents([{ id, name, input }], false, 2)
const errored = (id: string): UsageEvent => ({ kind: 'refused', t: 3, id })

test('a proposal card and a started side session are counted apart, by tool', async () => {
  const summary = summarize([
    prompt(),
    ...call('a', START, { title: 'Fix the parser', initiation: 'offer' }),
    ...call('b', START, { title: 'Docs pass', initiation: 'own_initiative', prompt: 'brief' }),
    ...call('c', START, { title: 'Run it', initiation: 'user_asked', prompt: 'brief' }),
    ...call('d', START, { proposal_id: 'p1', initiation: 'own_initiative' }),
    ...call('e', HAND_OFF, { title: 'Carry on', remaining_plan: 'steps' }),
  ])
  expect(summary.sideSessions).toEqual({ [START]: { card: 2, start: 2 }, [HAND_OFF]: { start: 1 } })
  // Near miss: a subagent spawn is no side session.
  expect(summarize([prompt(), ...call('f', 'Agent', { description: 'scan', prompt: 'p' })]).sideSessions).toEqual({})
})

test('a held or failed session-start call is not counted', async () => {
  const held = summarize([prompt(), ...call('a', START, { initiation: 'user_asked' }), errored('a')])
  expect(held.sideSessions).toEqual({})
  const failedCard = summarize([prompt(), ...call('b', START, { initiation: 'offer' }), errored('b')])
  expect(failedCard.sideSessions).toEqual({})
  // Near miss: another call's error takes nothing back.
  const ran = summarize([prompt(), ...call('c', START, { initiation: 'offer' }), errored('other')])
  expect(ran.sideSessions).toEqual({ [START]: { card: 1 } })
})

test('a subagent calling the session tools adds no side session; the report and pane show the main agent counts', async ($, on) => {
  const row = { door: 'response', agentId: 'sub-1', message: { content: [{ type: 'tool_use', id: 'x', name: START, input: { initiation: 'user_asked' } }] } }
  expect(summarize([prompt(), ...rowEvents(row, [], 2, {})]).sideSessions).toEqual({})
  const events = [prompt(), ...call('a', START, { initiation: 'offer' }), ...call('b', HAND_OFF, {})]
  expect(reportText(addSession(null, summarize(events)), null)).toContain('- Side sessions: hand_off_to_session 1 started · start_session 1 card')
  expect(reportText(addSession(null, summarize([prompt()])), null)).toContain('- Side sessions: none')
  const text = await paneText($, on, { tab: 'session', events: { shape: `events-${DATA_VERSION}`, value: events } })
  expect(text).toContain('Side sessions: 1 card, 1 started')
})

// ---------- projects --------------------------------------------------------------

/** A fixed salt, so keys in tests that build summaries by hand are stable. */
const TEST_SALT = 'test-salt'
const keyOf = (folder: string) => projectKey(folder, TEST_SALT)

test('a project key is the same for one folder however it is spelled, and differs between folders', async () => {
  const alphaKey = await keyOf('C:\\Users\\someone\\code\\alpha-app')
  expect(alphaKey).toMatch(/^[0-9a-f]{10}$/)
  expect(alphaKey).not.toBe(await keyOf('C:\\Users\\someone\\code\\beta-site'))
  expect(await keyOf('c:/Users/someone/code/alpha-app/')).toBe(alphaKey)
  // Near miss: on a path with no drive, case is part of the name.
  expect(await keyOf('/home/someone/Alpha')).not.toBe(await keyOf('/home/someone/alpha'))
})

test('a project key depends on the salt, so a guessed path cannot be checked without it', async () => {
  const salted = await projectKey('/work/alpha', 'one-salt')
  expect(await projectKey('/work/alpha', 'one-salt')).toBe(salted)
  // Near miss: the same folder under another install's salt gets another key.
  expect(await projectKey('/work/alpha', 'another-salt')).not.toBe(salted)
})

test('sessions from two project folders can be filtered apart in All time', async () => {
  const alpha = await keyOf('/work/alpha')
  const beta = await keyOf('/work/beta')
  const { total } = allTimeOf(
    [
      ['s:1', { t: 1, summary: sessionIn('tdd', alpha) }],
      ['s:2', { t: 2, summary: sessionIn('tdd', alpha) }],
      ['s:3', { t: 3, summary: sessionIn('diagnose', beta) }],
      ['s:4', { t: 4, summary: sessionIn('caveman') }],
    ],
    null,
    300,
    's:now',
  )
  expect(total?.sessions).toBe(4)
  expect(total?.byProject?.[alpha]?.sessions).toBe(2)
  expect(Object.keys(total?.byProject?.[alpha]?.loads ?? {})).toEqual(['tdd'])
  expect(Object.keys(total?.byProject?.[beta]?.loads ?? {})).toEqual(['diagnose'])
  // Near miss: a summary with no project key, stored by an earlier version, counts in all projects but in no one project.
  expect(Object.keys(total?.byProject ?? {}).sort()).toEqual([alpha, beta].sort())
  const stored = JSON.stringify(total)
  expect(stored.includes('/work') || stored.includes('alpha') || stored.includes('beta')).toBe(false)
})

/** Where the store keeps the install's salt for project keys. */
const SALT_KEY = 'project-salt'
const WORKTREE = '/work/alpha/.claude/worktrees/fix-parser'

/**
 * Runs a session through its start and one finished turn, answering the engine as `world` says: a repository root, or
 * none outside a repository; a session root; either left unanswered makes that lookup fail. Returns the plugin store,
 * the mod's state and the stored summary afterwards.
 */
async function oneTurn(
  $: Parameters<TestBody>[0],
  on: Parameters<TestBody>[1],
  world: { repoRoot?: string | null; sessionRoot?: string; store?: Map<string, unknown>; state?: Record<string, unknown> },
) {
  const store = world.store ?? new Map<string, unknown>()
  const state = world.state ?? {}
  on('session.start', (_, request) => ({ cwd: request.cwd }))
  on('turn.complete', () => ({ text: '' }))
  on('clock.now', () => ({ value: 1_000_000 }))
  on('session.id', () => ({ value: 'running' }))
  on('session.usage', () => ({ value: { context: { breakdown: { skills: { skillFrontmatter: [], totalSkills: 0, includedSkills: 0, tokens: 0 } } } } as never }))
  on('session.messages', () => ({ value: [{ role: 'user', content: [{ type: 'text', text: 'Fix the parser' }] }] as never }))
  const { repoRoot, sessionRoot } = world
  if (sessionRoot !== undefined) on('session.root', () => ({ value: sessionRoot }))
  if (repoRoot !== undefined) on('session.repo', () => ({ value: (repoRoot === null ? null : { root: repoRoot, remote: null }) as never }))
  on('command.register', () => ({ value: { command: 'skill-usage' } }))
  on('ui.open', () => ({ value: { isPlaced: false, reason: 'no pane in this test' } }))
  on('ui.status', () => ({ value: undefined }))
  on('state.get', (_, request) => {
    const key = (request as { key: string }).key
    return { value: key in state ? { value: state[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', (_, request) => {
    const { key, value } = request as { key: string; value: unknown }
    state[key] = value
    return { value: { isSet: true, version: 2 } }
  })
  on('store.keys', () => ({ value: [...store.keys()] }))
  on('store.get', (_, request) => ({ value: store.get((request as { key: string }).key) }))
  on('store.set', (_, request) => {
    const { key, value } = request as { key: string; value: unknown }
    store.set(key, value)
    return { value: undefined }
  })
  on('store.delete', () => ({ value: undefined }))
  await $.session.start({ cwd: WORKTREE, surface: null, isInteractive: false })
  await $.turn.complete({ answer: '', durationMs: 1, isAborted: false, turnId: 'turn-1', reason: 'answer' })
  return { store, state, saved: (store.get('s:running') as { summary: SessionSummary } | undefined)?.summary }
}

test('the stored summary carries the salted key of the repository root, so a worktree counts with its repository', async ($, on) => {
  const { store, saved } = await oneTurn($, on, { repoRoot: '/work/alpha', sessionRoot: WORKTREE })
  const salt = String(store.get(SALT_KEY))
  expect(saved?.project).toBe(await projectKey('/work/alpha', salt))
  expect(saved?.version).toBe(DATA_VERSION)
  // Near miss: the worktree's own folder would give another key.
  expect(saved?.project).not.toBe(await projectKey(WORKTREE, salt))
  // Nothing the mod stored, the salt and every summary included, names the folder or any part of its path.
  const everything = JSON.stringify([...store.entries()])
  for (const part of ['/work', 'work/', 'alpha', 'worktrees', 'fix-parser']) expect(everything.includes(part)).toBe(false)
})

test('an install keeps its salt, so a project keeps its key across sessions', async ($, on) => {
  const store = new Map<string, unknown>([[SALT_KEY, 'kept-salt']])
  const { saved } = await oneTurn($, on, { repoRoot: '/work/alpha', sessionRoot: WORKTREE, store })
  expect(store.get(SALT_KEY)).toBe('kept-salt')
  expect(saved?.project).toBe(await projectKey('/work/alpha', 'kept-salt'))
})

test('when the repository lookup fails, the key comes from the session root', async ($, on) => {
  const { store, saved } = await oneTurn($, on, { sessionRoot: '/work/alpha' })
  expect(saved?.project).toBe(await projectKey('/work/alpha', String(store.get(SALT_KEY))))
})

test('when both lookups fail, the summary is still stored, with no project key', async ($, on) => {
  const { saved } = await oneTurn($, on, {})
  // Near miss of the test above: the session is counted, under no project.
  expect(saved?.loads).toBeDefined()
  expect(saved?.version).toBe(DATA_VERSION)
  expect(saved?.project).toBeUndefined()
})

test('a resumed session running across the update keeps what it stored since its resume', async ($, on) => {
  // The summary stored at resume (the baseline the earlier version kept), and the one stored after more turns.
  const atResume = { ...sessionIn('tdd'), loads: { tdd: { 'self-initiated': 1 } } }
  const sinceResume = { ...sessionIn('tdd'), loads: { tdd: { 'self-initiated': 4 } } }
  const store = new Map<string, unknown>([['s:running', { t: 5, summary: sinceResume }]])
  const state: Record<string, unknown> = {
    owner: 'running',
    backfilled: { shape: 'events-3', value: 'running' },
    events: { shape: 'events-3', value: [prompt()] },
    baseline: { shape: 'summary-1', value: atResume },
  }
  const { saved } = await oneTurn($, on, { repoRoot: null, sessionRoot: '/work/alpha', store, state })
  // The dropped events' stretch is not lost: the summary stored since the resume is the new baseline.
  expect(saved?.loads.tdd?.['self-initiated']).toBe(4)
})

test('a resumed session already on this version keeps its baseline', async ($, on) => {
  // Near miss: with the events on the current tag, nothing is dropped, so the baseline stays as it was.
  const atResume = { ...sessionIn('tdd'), loads: { tdd: { 'self-initiated': 1 } } }
  const store = new Map<string, unknown>([['s:running', { t: 5, summary: { ...atResume, loads: { tdd: { 'self-initiated': 9 } } } }]])
  const tag = `events-${DATA_VERSION}`
  const state: Record<string, unknown> = { owner: 'running', backfilled: { shape: tag, value: 'running' }, events: { shape: tag, value: [] }, baseline: { shape: 'summary-1', value: atResume } }
  const { saved } = await oneTurn($, on, { repoRoot: null, sessionRoot: '/work/alpha', store, state })
  expect(saved?.loads.tdd?.['self-initiated']).toBe(1)
})

/** All time with one stored session in each of two projects, and this session, which loads caveman, in alpha. */
async function twoProjects(shown?: 'alpha' | 'beta') {
  const alpha = await keyOf('/work/alpha')
  const beta = await keyOf('/work/beta')
  const total = addSession(addSession(null, sessionIn('tdd', alpha)), sessionIn('diagnose', beta))
  const live = [prompt(), { kind: 'load' as const, t: 2, skill: 'caveman', via: 'tool' as const, isSubagent: false }]
  const filter = shown ? { allProject: shown === 'alpha' ? alpha : beta } : {}
  return { alpha, state: { tab: 'all', events: { shape: `events-${DATA_VERSION}`, value: live }, allTime: { shape: 'all-time-2', value: total }, project: alpha, ...filter } }
}

test('the All time tab lists each project, marking this one, and counts every project unfiltered', async ($, on) => {
  const { alpha, state } = await twoProjects()
  const text = await paneText($, on, state)
  expect(text).toContain('3 sessions ·')
  expect(text).toContain(`${alpha} · this project · 2 sessions`)
  expect(text).toContain('caveman')
  expect(text).toContain('diagnose')
})

test('the All time tab filtered to another project leaves this session out', async ($, on) => {
  const text = await paneText($, on, (await twoProjects('beta')).state)
  expect(text).toContain('1 session ·')
  expect(text).toContain('diagnose')
  expect(text).not.toContain('caveman')
})

test('the All time tab filtered to this project counts this session in it', async ($, on) => {
  // Near miss of the filter above: the same state shown for alpha.
  const text = await paneText($, on, (await twoProjects('alpha')).state)
  expect(text).toContain('2 sessions ·')
  expect(text).toContain('caveman')
  expect(text).not.toContain('diagnose')
})

test('the report lists each project by its key and session count', async () => {
  const alpha = await keyOf('/work/alpha')
  const total = addSession(addSession(addSession(null, sessionIn('tdd', alpha)), sessionIn('tdd', alpha)), sessionIn('tdd'))
  const report = reportText(total, null)
  expect(report).toContain(`## Projects\n\n- ${alpha}: 2 sessions\n- not recorded: 1 session`)
})

// ---------- versions --------------------------------------------------------------

/** A summary as versions before 076 stored it: no version, holds under a retired gate name. */
const earlierSummary = (): SessionSummary => {
  const { version: _, ...summary } = sessionIn('tdd')
  return { ...summary, nudges: { 'design-hold': { followed: 2, ignored: 1 }, design: { followed: 1 } }, holds: { 'justified-skip': 4 } }
}

test('a summary stored by an earlier version shows under the earlier-versions heading and changes no current count', async () => {
  const current = { ...sessionIn('tdd'), nudges: { design: { followed: 1 } }, holds: { 'justified-skip': 1 } }
  const withEarlier = addSession(addSession(null, current), earlierSummary())
  const alone = addSession(null, current)
  expect(withEarlier.nudges).toEqual(alone.nudges)
  expect(withEarlier.holds).toEqual(alone.holds)
  expect(withEarlier.earlier?.sessions).toBe(1)
  expect(withEarlier.earlier?.nudges).toEqual({ 'design-hold': { followed: 2, ignored: 1 }, design: { followed: 1 } })
  expect(withEarlier.earlier?.holds).toEqual({ 'justified-skip': 4 })
  const report = reportText(withEarlier, null)
  expect(report).toContain('## Hooks from earlier versions of the mod\n\n1 session stored before summaries carried a version.\n\n- design check: 2 of 3 handled')
  // Near miss: a summary this version stored counts as current.
  expect(addSession(null, current).earlier).toBeUndefined()
  expect(current.version).toBe(DATA_VERSION)
})

test('the All time tab shows earlier versions holds under their own heading', async ($, on) => {
  const total = addSession(null, earlierSummary())
  const text = await paneText($, on, { tab: 'all', events: { shape: `events-${DATA_VERSION}`, value: [prompt()] }, allTime: { shape: 'all-time-2', value: total } })
  expect(text).toContain('Hooks from earlier versions')
  expect(text).toContain('design check')
  // The current standing line counts none of them.
  expect(text).toContain('2 sessions · 1 skill load · no hook nudges yet')
})

test('a session resumed across the update keeps the earlier stretch marked as earlier', async () => {
  const later = { ...sessionIn('tdd'), nudges: { design: { followed: 1 } } }
  const merged = mergeSummaries(earlierSummary(), later)
  expect(merged.version).toBeUndefined()
  expect(addSession(null, merged).nudges).toEqual({})
  // Near miss: two stretches both stamped stay current.
  expect(mergeSummaries(sessionIn('tdd'), later).version).toBe(DATA_VERSION)
})

test('an earlier summary keeps all its gate-keyed data apart: closeout items and skip reasons too', async () => {
  const earlier = {
    ...earlierSummary(),
    closeoutItems: { Proof: { followed: 1 } },
    skipReasons: { 'software-design-principles': { 'design-hold': { 'renames one local variable': 1 } } },
  }
  const current = { ...sessionIn('tdd'), closeoutItems: { Docs: { declined: 1 } }, skipReasons: { 'doc-sync': { closeout: { 'only a test changed here': 1 } } } }
  const all = addSession(addSession(null, current), earlier)
  expect(all.closeoutItems).toEqual({ Docs: { declined: 1 } })
  expect(all.skipReasons).toEqual({ 'doc-sync': { closeout: { 'only a test changed here': 1 } } })
  expect(all.earlier?.closeoutItems).toEqual({ Proof: { followed: 1 } })
  expect(all.earlier?.skipReasons).toEqual(earlier.skipReasons)
  const report = reportText(all, null)
  // Under the earlier-versions heading, not among the current skip reasons.
  const earlierPart = report.slice(report.indexOf('## Hooks from earlier versions'), report.indexOf('## Projects'))
  expect(earlierPart).toContain('- Proof: 1 of 1 handled')
  expect(earlierPart).toContain('software-design-principles › design check: "renames one local variable" ×1')
  const currentReasons = report.slice(report.indexOf('## Skip reasons'))
  expect(currentReasons).not.toContain('renames one local variable')
  expect(currentReasons).toContain('only a test changed here')
})

test('a session resumed from an earlier summary counts under this version project, its holds still apart', async () => {
  const alpha = await keyOf('/work/alpha')
  const merged = mergeSummaries(earlierSummary(), { ...sessionIn('tdd'), project: alpha })
  expect(merged.project).toBe(alpha)
  const all = addSession(null, merged)
  expect(all.byProject?.[alpha]?.sessions).toBe(1)
  expect(all.byProject?.[alpha]?.earlier?.nudges['design-hold']).toEqual({ followed: 2, ignored: 1 })
  // Near miss: an earlier summary never resumed has no project and counts under none.
  expect(addSession(null, earlierSummary()).byProject).toBeUndefined()
})

test('an observer error is kept with its paths masked, as a skip reason is', async () => {
  // The kit wraps any failure an engine call raises, so a test cannot get a path into the mod's error; this checks the
  // text the mod keeps for one, which register.tsx's noteError stores and the pane shows.
  const error = new Error('EACCES: permission denied, open C:\\Users\\someone\\store.json and /home/someone/x')
  expect(errorText(error)).toBe('Error: EACCES: permission denied, open <path> and <path>')
  // Near miss: an error naming no path keeps its words, and a long one is not cut, unlike a skip reason.
  const long = `no implementation for store.set ${'x'.repeat(300)}`
  expect(errorText(new Error(long))).toBe(`Error: ${long}`)
})

async function startWith($: Parameters<TestBody>[0], on: Parameters<TestBody>[1], state: Record<string, unknown>): Promise<UsageEvent[]> {
  const history = [
    { role: 'user' as const, content: [{ type: 'text' as const, text: 'Fix the parser' }] },
    { role: 'assistant' as const, content: [{ type: 'tool_use' as const, id: 'a', name: START, input: { initiation: 'offer' } }] },
    { role: 'user' as const, content: [{ type: 'tool_result' as const, tool_use_id: 'a', content: 'card shown' }] },
  ]
  on('session.start', (_, request) => ({ cwd: request.cwd }))
  on('clock.now', () => ({ value: 1_000_000 }))
  on('session.id', () => ({ value: 'running' }))
  on('session.usage', () => ({ value: { context: { breakdown: { skills: { skillFrontmatter: [], totalSkills: 0, includedSkills: 0, tokens: 0 } } } } as never }))
  on('session.messages', () => ({ value: history as never }))
  on('session.root', () => ({ value: '/work/alpha' }))
  on('session.repo', () => ({ value: null }))
  on('command.register', () => ({ value: { command: 'skill-usage' } }))
  on('ui.open', () => ({ value: { isPlaced: false, reason: 'no pane in this test' } }))
  on('ui.status', () => ({ value: undefined }))
  on('store.keys', () => ({ value: [] }))
  on('store.get', () => ({ value: undefined }))
  on('store.set', () => ({ value: undefined }))
  on('store.delete', () => ({ value: undefined }))
  on('state.get', (_, request) => {
    const key = (request as { key: string }).key
    return { value: key in state ? { value: state[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', (_, request) => {
    const { key, value } = request as { key: string; value: unknown }
    state[key] = value
    return { value: { isSet: true, version: 2 } }
  })
  await $.session.start({ cwd: '/work/alpha', surface: null, isInteractive: false })
  return (state.events as { value: UsageEvent[] }).value
}

// The previous version's events: a card shown, recorded as a write and nothing more.
const OLD_EVENTS: UsageEvent[] = [prompt(), { kind: 'write', t: 2, id: 'a' }]

test('a session running across the update is rebuilt from its history, so its side session is not missed', async ($, on) => {
  const events = await startWith($, on, { owner: 'running', backfilled: { shape: 'events-3', value: 'running' }, events: { shape: 'events-3', value: OLD_EVENTS } })
  expect(summarize(events).sideSessions).toEqual({ [START]: { card: 1 } })
})

test('a session already on this version keeps its events', async ($, on) => {
  // Near miss: the same events under the current tag stay as they are.
  const tag = `events-${DATA_VERSION}`
  const events = await startWith($, on, { owner: 'running', backfilled: { shape: tag, value: 'running' }, events: { shape: tag, value: OLD_EVENTS } })
  expect(events).toEqual(OLD_EVENTS)
})
