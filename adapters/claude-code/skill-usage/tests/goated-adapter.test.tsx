// What the mod records from the GOATED Claude Code adapter and the marker
// grammar: route lines, the adapter's routing holds and their outcomes, typed
// overrides, justified skips against an adapter hold, required-reference
// reads, subagent spawns and start messages, and subagent reads of skill bodies.

import { expect, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'

import type { UsageEvent } from '../types'
import { addSession, hookEvents, markerEvents, markerLines, mergeSummaries, overrideEvents, ROUTE_LINE, ROUTER, summarize, toolUseEvents } from '../hooks/classify'
import { reportText } from '../hooks/view'
import { MARKER_FIXTURES } from './marker-fixtures'

const SKILLS = ['using-goated-ai-skills', 'tdd', 'doc-sync', 'writing-plans', 'commit-message', 'handoff']

// ---------- the marker grammar, from stack/fixtures/markers/lines.yaml ---------------

/** A parsed route in the fixtures' `expect` shape. */
const asExpected = (route: ReturnType<typeof markerLines>['route']) =>
  route === null ? null : route.form === 'route' ? { form: route.form, intensity: route.intensity, requires: route.requires } : { form: route.form }

test('every valid route line in the grammar fixtures reads as the fixture expects', async () => {
  for (const { line, expect: want } of MARKER_FIXTURES.route_lines.valid) {
    expect(asExpected(markerLines(line).route)).toEqual(want)
  }
})

test('every invalid route line in the grammar fixtures is no route and is reported as malformed', async () => {
  for (const { line } of MARKER_FIXTURES.route_lines.invalid) {
    const read = markerLines(line)
    expect(read.route).toBeNull()
    expect(read.malformed).toEqual([line])
  }
})

test('every valid skip line in the grammar fixtures reads as the fixture expects; every invalid one is no skip', async () => {
  for (const { line, expect: want } of MARKER_FIXTURES.skip_lines.valid) expect(markerLines(line).skips).toEqual([want])
  for (const { line } of MARKER_FIXTURES.skip_lines.invalid) {
    const read = markerLines(line)
    expect(read.skips).toEqual([])
    expect(read.malformed).toEqual([line])
  }
})

test('every whole reply in the grammar fixtures gives its route, skips and malformed lines', async () => {
  for (const reply of MARKER_FIXTURES.replies) {
    const read = markerLines(reply.text)
    expect({ id: reply.identifier, route: asExpected(read.route), skips: read.skips, malformed: read.malformed }).toEqual({
      id: reply.identifier,
      route: reply.expect.route,
      skips: reply.expect.skips,
      malformed: reply.expect.malformed,
    })
  }
})

// ---------- route lines -------------------------------------------------------------

test('a reply records its winning route line, and a subagent reply records whose it is', async () => {
  const reply = 'goated-route: direct\nScope grew.\ngoated-route: standard | requires: writing-plans, tdd\ngoated-skip: doc-sync: change touches only test fixtures'
  expect(markerEvents(reply, 5)).toEqual([
    { kind: 'route', t: 5, form: 'route', intensity: 'standard', requires: ['writing-plans', 'tdd'] },
    { kind: 'skip', t: 5, skill: 'doc-sync', reason: 'change touches only test fixtures' },
  ])
  expect(markerEvents('goated-route: continue', 6, 'a1')).toEqual([{ kind: 'route', t: 6, form: 'continue', isSubagent: true, agent: 'a1' }])
  expect(markerEvents('No markers here.', 7)).toEqual([])
})

test('route lines are counted by form, listed in the log, and add up across sessions', async () => {
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'route', t: 2, form: 'route', intensity: 'standard', requires: ['tdd'] },
    { kind: 'prompt', t: 3, named: [] },
    { kind: 'route', t: 4, form: 'continue' },
    { kind: 'prompt', t: 5, named: [] },
    { kind: 'route', t: 6, form: 'direct' },
  ])
  expect(s.routes).toEqual({ route: 1, continue: 1, direct: 1 })
  expect(s.timeline.filter(e => e.kind === 'route')).toEqual([
    { kind: 'route', t: 2, form: 'route', intensity: 'standard', requires: ['tdd'] },
    { kind: 'route', t: 4, form: 'continue' },
    { kind: 'route', t: 6, form: 'direct' },
  ])
  expect(addSession(addSession(null, s), s).routes).toEqual({ route: 2, continue: 2, direct: 2 })
  expect(mergeSummaries(s, s).routes).toEqual({ route: 2, continue: 2, direct: 2 })
})

// ---------- the adapter's routing holds --------------------------------------------

// As a held call's errored tool result reads in a real transcript.
const held = (tool: string, gate: string, body: string) => `PreToolUse:${tool} hook error: goated-hold: ${gate} | strict\n${body}`
const ROUTER_FIRST = held(
  'Write',
  'router-first',
  'Load the `using-goated-ai-skills` skill with the Skill tool before the first write, spawn, or command of a task, and follow the route it selects. Reads stay free. If that skill is not installed, tell the user: they can type `skip routing` in their prompt to proceed without it.',
)
const ROUTE_MISSING = held('Edit', 'route-line', 'Before the first write after a user prompt, end routing with a route line on its own line: `goated-route: direct`, `goated-route: continue`, or `goated-route: <intensity> | requires: <skills>`.')
const PIPELINE = held(
  'Edit',
  'pipeline',
  'The current route requires `tdd`, `doc-sync` before the first write or spawn. Load each with the Skill tool and follow it; only loads after the route line that started this task count, so load again if you loaded it earlier. If one does not apply, write a corrected route line without it; the last route line wins.',
)

test("each adapter hold names its gate, its kind and what it asks for: the router, a route line, or the route's missing skills", async () => {
  expect(hookEvents(ROUTER_FIRST, SKILLS, 1, { holdsOnly: true })).toEqual([{ kind: 'nudge', t: 1, hook: 'router-first', named: [ROUTER], holdKind: 'strict' }])
  expect(hookEvents(ROUTE_MISSING, SKILLS, 1, { holdsOnly: true })).toEqual([{ kind: 'nudge', t: 1, hook: 'route-line', named: [ROUTE_LINE], holdKind: 'strict' }])
  expect(hookEvents(PIPELINE, SKILLS, 1, { holdsOnly: true })).toEqual([{ kind: 'nudge', t: 1, hook: 'pipeline', named: ['tdd', 'doc-sync'], holdKind: 'strict' }])
  // An ordinary failure that quotes a hold mid-line is not one.
  expect(hookEvents('Error: grep found "goated-hold: pipeline | strict" in a file', SKILLS, 1, { holdsOnly: true })).toEqual([])
})

test('the router-first hold is followed by loading the router, the route-line hold by a route line, the pipeline hold by each skill', async () => {
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    ...hookEvents(ROUTER_FIRST, SKILLS, 2, { holdsOnly: true }),
    { kind: 'load', t: 3, skill: ROUTER, via: 'tool', isSubagent: false },
    ...hookEvents(ROUTE_MISSING, SKILLS, 4, { holdsOnly: true }),
    { kind: 'route', t: 5, form: 'route', intensity: 'standard', requires: ['tdd', 'doc-sync'] },
    ...hookEvents(PIPELINE, SKILLS, 6, { holdsOnly: true }),
    { kind: 'load', t: 7, skill: 'tdd', via: 'tool', isSubagent: false },
    { kind: 'turn-end', t: 8 },
  ])
  expect(s.nudges).toEqual({ 'router-first': { followed: 1 }, 'route-line': { followed: 1 }, pipeline: { followed: 1, ignored: 1 } })
  expect(s.holds).toEqual({ strict: 3 })
  // The log row keeps the hold's kind and each skill's own result.
  const pipeline = s.timeline.find(e => e.kind === 'nudge' && e.hook === 'pipeline')
  expect(pipeline).toEqual({ kind: 'nudge', t: 6, hook: 'pipeline', holdKind: 'strict', skills: [{ skill: 'tdd', status: 'followed', at: 7 }, { skill: 'doc-sync', status: 'ignored', at: 8 }] })
})

test('a justified skip line declines the adapter hold it names, keeping the reason', async () => {
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    ...hookEvents(PIPELINE, SKILLS, 2, { holdsOnly: true }),
    { kind: 'load', t: 3, skill: 'tdd', via: 'tool', isSubagent: false },
    ...markerEvents('goated-skip: doc-sync: change touches only test fixtures', 4),
  ])
  expect(s.nudges).toEqual({ pipeline: { followed: 1, declined: 1 } })
  const row = s.timeline.find(e => e.kind === 'nudge')
  expect(row?.kind === 'nudge' && row.skills[1]).toEqual({ skill: 'doc-sync', status: 'declined', at: 4, reason: 'change touches only test fixtures' })
})

test('the hooks of earlier installs are still read beside the adapter', async () => {
  // Their hold texts stay readable until the adapter replaces them.
  const legacy = 'COMMIT CHECK (held once this turn): before committing, invoke the `commit-message` skill and draft the message with it.'
  expect(hookEvents(legacy, SKILLS, 1, { holdsOnly: true })).toEqual([{ kind: 'nudge', t: 1, hook: 'commit-hold', named: ['commit-message'] }])
})

// ---------- overrides ---------------------------------------------------------------

const NOTICE = 'GOATED Claude Code adapter: recorded your override for this prompt: "Skip routing", "skip the tdd skill".'

test("the adapter's override notice records each phrase you typed, and nothing else does", async () => {
  expect(overrideEvents(NOTICE, 3)).toEqual([{ kind: 'override', t: 3, phrases: ['skip routing', 'skip the tdd skill'] }])
  // A warning that also notes a failed save still carries the override.
  expect(overrideEvents('GOATED Claude Code adapter: recorded your override for this prompt: "skip doc-sync"; could not save its session state (EACCES).', 3)).toEqual([
    { kind: 'override', t: 3, phrases: ['skip doc-sync'] },
  ])
  expect(overrideEvents('GOATED Claude Code adapter: the transcript cannot be read, so this action was allowed without checks.', 3)).toEqual([])
  expect(overrideEvents('You wrote: recorded your override for this prompt: "skip routing".', 3)).toEqual([])
})

test('overrides are counted by phrase, logged, and add up across sessions', async () => {
  const s = summarize([{ kind: 'prompt', t: 1, named: [] }, ...overrideEvents(NOTICE, 2)])
  expect(s.overrides).toEqual({ 'skip routing': 1, 'skip the tdd skill': 1 })
  expect(s.timeline.at(-1)).toEqual({ kind: 'override', t: 2, phrases: ['skip routing', 'skip the tdd skill'] })
  expect(addSession(addSession(null, s), s).overrides).toEqual({ 'skip routing': 2, 'skip the tdd skill': 2 })
})

// ---------- required-reference reads -----------------------------------------------

test('a read of a reference file the route requires is recorded against its skill, loaded or not', async () => {
  const uses = [{ name: 'Read', input: { file_path: '/home/me/.claude/skills/tdd/references/mocking.md' } }]
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'route', t: 2, form: 'route', intensity: 'standard', requires: ['tdd'] },
    ...toolUseEvents(uses, false, false, 3),
    { kind: 'load', t: 4, skill: 'tdd', via: 'tool', isSubagent: false },
    ...toolUseEvents(uses, false, true, 5),
  ])
  expect(s.refs).toEqual({ tdd: { 'references/mocking.md': 2 } })
  expect(s.refsUnloaded).toBe(1)
})

// ---------- subagents ---------------------------------------------------------------

const SPAWN = { name: 'Agent', input: { description: 'Scan the repo', subagent_type: 'Explore', prompt: 'Find every caller of x.' } }

test('a subagent spawn is recorded with its type and task, by the main agent or a subagent', async () => {
  expect(toolUseEvents([SPAWN], false, true, 4)).toEqual([{ kind: 'spawn', t: 4, agentType: 'Explore', description: 'Scan the repo' }])
  expect(toolUseEvents([{ name: 'Agent', input: { description: 'Help', prompt: 'x' } }], true, true, 4, 'a1')).toEqual([
    { kind: 'spawn', t: 4, agentType: 'general-purpose', description: 'Help', isSubagent: true, agent: 'a1' },
  ])
})

test('a subagent that loads no skill still counts and shows in the log', async () => {
  const s = summarize([{ kind: 'prompt', t: 1, named: [] }, ...toolUseEvents([SPAWN], false, false, 2), { kind: 'turn-end', t: 3, agent: 'a1' }])
  expect(s.loads).toEqual({})
  expect(s.subagents).toEqual({ spawns: 1, starts: 0, bodyReads: 0 })
  expect(s.timeline.at(-1)).toEqual({ kind: 'spawn', t: 2, agentType: 'Explore', description: 'Scan the repo' })
})

// As the SubagentStart hook of an earlier install hands a subagent its contract.
const START = "DELEGATED AGENT: another agent started you for the task in your first message, and it owns the user's intent and the final answer. For delivery work, invoke the using-goated-ai-skills router first."

test("the subagent start message is recorded as the subagent's start, not as a nudge", async () => {
  expect(hookEvents(START, SKILLS, 3, { agent: 'a1' })).toEqual([{ kind: 'subagent-start', t: 3, agent: 'a1' }])
  const s = summarize([{ kind: 'prompt', t: 1, named: [] }, ...toolUseEvents([SPAWN], false, false, 2), ...hookEvents(START, SKILLS, 3, { agent: 'a1' })])
  expect(s.nudges).toEqual({})
  expect(s.subagents).toEqual({ spawns: 1, starts: 1, bodyReads: 0 })
  expect(s.timeline.at(-1)).toEqual({ kind: 'subagent-start', t: 3 })
})

test("a subagent reading a skill's SKILL.md is a body read, which settles that subagent's nudge for it", async () => {
  const read = toolUseEvents([{ name: 'Read', input: { file_path: 'C:\\home\\.claude\\skills\\tdd\\SKILL.md' } }], true, true, 4, 'a1')
  expect(read).toEqual([{ kind: 'body', t: 4, skill: 'tdd', isSubagent: true, agent: 'a1' }])
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'nudge', t: 2, hook: 'design-hold', named: ['tdd'], isSubagent: true, agent: 'a1' },
    { kind: 'nudge', t: 3, hook: 'design-hold', named: ['tdd'], isSubagent: true, agent: 'a2' },
    ...read,
    { kind: 'turn-end', t: 5, agent: 'a2' },
  ])
  expect(s.nudges).toEqual({ 'design-hold': { 'read files': 1, ignored: 1 } })
  expect(s.subagents).toEqual({ spawns: 0, starts: 0, bodyReads: 1 })
  expect(s.timeline.at(-1)).toEqual({ kind: 'body', t: 4, skill: 'tdd', isSubagent: true })
})

// ---------- in the pane and the report ----------------------------------------------

const PANE = {
  plugin: 'skill-usage',
  component: 'Pane',
  requestId: 'skill-usage',
  props: { title: 'Skill usage', isFocused: false, bodyColumns: 60, placement: 'dock', scroll: { offset: 0, bodyRows: 30 }, view: {} },
} as const

function paneRig(...[$, on, events]: [...Parameters<TestBody>, UsageEvent[]]) {
  const stored: Record<string, unknown> = { tab: 'session', events: { shape: 'events-1', value: events } }
  on('clock.now', () => ({ value: 100_000 }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', () => ({ value: { isSet: true, version: 2 } }))
  return (surface: 'terminal' | 'desktop') => $.ui.mount({ ...PANE, surface })
}

test('the Session tab logs route lines, adapter holds, overrides, spawns and start messages, on every surface', async ($, on) => {
  const mount = paneRig($, on, [
    { kind: 'prompt', t: 1, named: [] },
    ...overrideEvents('GOATED Claude Code adapter: recorded your override for this prompt: "skip doc-sync".', 2),
    ...markerEvents('goated-route: standard | requires: tdd', 3),
    ...hookEvents(PIPELINE.replace('`tdd`, `doc-sync`', '`tdd`'), SKILLS, 4, { holdsOnly: true }),
    { kind: 'load', t: 5, skill: 'tdd', via: 'tool', isSubagent: false },
    ...toolUseEvents([SPAWN], false, true, 6),
    ...hookEvents(START, SKILLS, 7, { agent: 'a1' }),
  ])
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await mount(surface)
    expect((await ui.find({ type: 'Text', text: /^standard · requires tdd$/ }))?.text).toBeDefined()
    expect((await ui.find({ type: 'Text', text: /^pipeline hold → $/ }))?.text).toBeDefined()
    expect((await ui.find({ type: 'Text', text: /^you typed "skip doc-sync"$/ }))?.text).toBeDefined()
    expect((await ui.find({ type: 'Text', text: /^Explore started: Scan the repo$/ }))?.text).toBeDefined()
    expect((await ui.find({ type: 'Text', text: /^a subagent received its start message$/ }))?.text).toBeDefined()
    expect((await ui.find({ type: 'Text', text: /^Routes: 1 routed · Adapter holds: 1 strict · Overrides: 1 · Subagents: 1 started, 1 start message$/ }))?.text).toBeDefined()
    await ui.unmount()
  }
})

test('a subagent that loads no skill lights the Subagents node, with its spawn count on a badge', async ($, on) => {
  const mount = paneRig($, on, [{ kind: 'prompt', t: 1, named: [] }, ...toolUseEvents([SPAWN], false, false, 2)])
  const ui = await mount('desktop')
  const [still = ''] = (await ui.findAll({ type: 'Svg' })).map(x => String(x.props.source))
  await ui.unmount()
  // Lit in the accent colour, as a node with traffic is.
  expect(still).toMatch(/<circle cx="126" cy="304" r="14" fill="#12151c" stroke="#e1ac6e"/)
  expect(still).toMatch(/<g class="spawn-badge">.*>1<\/text><\/g>/)
})

test('the report lists route lines, adapter holds by kind, overrides and subagents', async () => {
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    ...markerEvents('goated-route: direct', 2),
    ...hookEvents(ROUTER_FIRST, SKILLS, 3, { holdsOnly: true }),
    ...overrideEvents(NOTICE, 4),
    ...toolUseEvents([SPAWN], false, true, 5),
  ])
  const report = reportText(addSession(null, s), null)
  expect(report).toContain('## Routes and adapter holds')
  expect(report).toContain('- Route lines: 1 direct')
  expect(report).toContain('- Adapter holds: 1 strict')
  expect(report).toContain('- Overrides: "skip routing" 1 · "skip the tdd skill" 1')
  expect(report).toContain('- Subagents: 1 started · 0 start messages · 0 skill bodies read')
})
