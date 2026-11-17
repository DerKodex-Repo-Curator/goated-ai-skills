// What the mod records from the GOATED Claude Code adapter and the marker
// grammar: route lines, the adapter's routing holds and their outcomes, typed
// overrides, justified skips against an adapter hold, required-reference
// reads, subagent spawns, and subagent reads of skill bodies.

import { expect, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'

import type { UsageEvent } from '../types'
import { addSession, hookEvents, isObservedRow, markerEvents, markerLines, mergeSummaries, overrideEvents, ROUTE_LINE, ROUTER, rowEvents, summarize, toolUseEvents } from '../hooks/classify'
import type { Row } from '../hooks/classify'
import { reportText } from '../hooks/view'
import { ADAPTER_TEXTS } from './adapter-texts'
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

// ---------- a route line on every turn that writes ----------------------------------

const EDIT = { name: 'Edit', input: { file_path: 'src/a.ts', old_string: 'a', new_string: 'b' } }

test('writes are the calls the adapter holds like writes: edits and spawns, by the main agent only', async () => {
  for (const name of ['Edit', 'Write', 'MultiEdit', 'NotebookEdit', 'Agent', 'mcp__ccd_session__start_session', 'mcp__ccd_session__hand_off_to_session']) {
    expect(toolUseEvents([{ name, input: {} }], false, 1).filter(e => e.kind === 'write')).toEqual([{ kind: 'write', t: 1 }])
  }
  expect(toolUseEvents([{ name: 'Read', input: { file_path: 'a' } }, { name: 'Bash', input: { command: 'ls' } }], false, 1).filter(e => e.kind === 'write')).toEqual([])
  expect(toolUseEvents([EDIT], true, 1, 'a1').filter(e => e.kind === 'write')).toEqual([])
})

test('each turn that writes counts once: routed before its first write, only after it, or not at all', async () => {
  const s = summarize([
    // Routed before the first write; a second write in the turn does not count again.
    { kind: 'prompt', t: 1, named: [] },
    ...markerEvents('goated-route: standard | requires: tdd', 2),
    ...toolUseEvents([EDIT], false, 3),
    ...toolUseEvents([EDIT], false, 4),
    // `continue` is a route line too.
    { kind: 'prompt', t: 5, named: [] },
    ...markerEvents('goated-route: continue', 6),
    ...toolUseEvents([EDIT], false, 7),
    // A route line only after the write.
    { kind: 'prompt', t: 8, named: [] },
    ...toolUseEvents([EDIT], false, 9),
    ...markerEvents('goated-route: direct', 10),
    // A main turn end inside a typed prompt's turn (a background result woke the agent) does not split it.
    { kind: 'turn-end', t: 11 },
    ...toolUseEvents([EDIT], false, 12),
    // No route line at all.
    { kind: 'prompt', t: 13, named: [] },
    ...toolUseEvents([EDIT], false, 14),
    // A turn that only reads is not counted.
    { kind: 'prompt', t: 15, named: [] },
    ...toolUseEvents([{ name: 'Read', input: { file_path: 'a' } }], false, 16),
  ])
  expect(s.writingTurns).toEqual({ routed: 2, late: 1, none: 1 })
  expect(addSession(addSession(null, s), s).writingTurns).toEqual({ routed: 4, late: 2, none: 2 })
})

test('the report says how many writing turns had a route line', async () => {
  const s = summarize([{ kind: 'prompt', t: 1, named: [] }, ...toolUseEvents([EDIT], false, 2)])
  expect(reportText(addSession(null, s), null)).toContain('- Writing turns: 0 routed before the first write · 0 routed only after it · 1 with no route line')
})

// ---------- the adapter's routing holds --------------------------------------------

// As a held call's errored tool result reads in a real transcript: Claude Code's prefix, then the adapter's own reason.
const held = (tool: string, reason: string) => `PreToolUse:${tool} hook error: ${reason}`
const ROUTER_FIRST = held('Write', ADAPTER_TEXTS.routerFirst)
const ROUTE_MISSING = held('Edit', ADAPTER_TEXTS.routeLine)
const PIPELINE = held('Edit', ADAPTER_TEXTS.pipeline)

test("each adapter hold names its gate, its kind and what it asks for: the router, a route line, or the route's missing skills", async () => {
  expect(hookEvents(ROUTER_FIRST, 1, { holdsOnly: true })).toEqual([{ kind: 'nudge', t: 1, hook: 'router-first', named: [ROUTER], holdKind: 'strict' }])
  expect(hookEvents(ROUTE_MISSING, 1, { holdsOnly: true })).toEqual([{ kind: 'nudge', t: 1, hook: 'route-line', named: [ROUTE_LINE], holdKind: 'strict' }])
  expect(hookEvents(PIPELINE, 1, { holdsOnly: true })).toEqual([{ kind: 'nudge', t: 1, hook: 'pipeline', named: ['tdd', 'doc-sync'], holdKind: 'strict' }])
  // An ordinary failure that quotes a hold mid-line is not one.
  expect(hookEvents('Error: grep found "goated-hold: pipeline | strict" in a file', 1, { holdsOnly: true })).toEqual([])
})

test("a hold line is a hold only as the result's first line, so failing output that prints one is not", async () => {
  const output = `FAIL test_holds (tests.test_claude_code_adapter)\n${ADAPTER_TEXTS.pipeline}\nAssertionError: 'deny' != 'pass'`
  expect(hookEvents(output, 1, { holdsOnly: true })).toEqual([])
})

test('a corrected route line that drops a held skill follows the pipeline hold for it; continue keeps the route', async () => {
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    ...markerEvents('goated-route: standard | requires: tdd, doc-sync', 2),
    ...hookEvents(PIPELINE, 3, { holdsOnly: true }),
    { kind: 'load', t: 4, skill: 'tdd', via: 'tool', isSubagent: false },
    ...markerEvents('goated-route: continue', 5),
    ...markerEvents('goated-route: standard | requires: tdd', 6),
  ])
  const row = s.timeline.find(e => e.kind === 'nudge')
  expect(row?.kind === 'nudge' && row.skills).toEqual([
    { skill: 'tdd', status: 'followed', at: 4 },
    { skill: 'doc-sync', status: 'followed', at: 6 },
  ])
  const direct = summarize([{ kind: 'prompt', t: 1, named: [] }, ...hookEvents(PIPELINE, 2, { holdsOnly: true }), ...markerEvents('goated-route: direct', 3)])
  expect(direct.nudges).toEqual({ pipeline: { followed: 2 } })
})

test('the router-first hold is followed by loading the router, the route-line hold by a route line, the pipeline hold by each skill', async () => {
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    ...hookEvents(ROUTER_FIRST, 2, { holdsOnly: true }),
    { kind: 'load', t: 3, skill: ROUTER, via: 'tool', isSubagent: false },
    ...hookEvents(ROUTE_MISSING, 4, { holdsOnly: true }),
    { kind: 'route', t: 5, form: 'route', intensity: 'standard', requires: ['tdd', 'doc-sync'] },
    ...hookEvents(PIPELINE, 6, { holdsOnly: true }),
    { kind: 'load', t: 7, skill: 'tdd', via: 'tool', isSubagent: false },
    { kind: 'turn-end', t: 8 },
  ])
  expect(s.nudges).toEqual({ 'router-first': { followed: 1 }, 'route-line': { followed: 1 }, pipeline: { followed: 1, ignored: 1 } })
  expect(s.holds).toEqual({ strict: 3 })
  // The log row keeps the hold's kind and each skill's own result.
  const pipeline = s.timeline.find(e => e.kind === 'nudge' && e.hook === 'pipeline')
  expect(pipeline).toEqual({ kind: 'nudge', t: 6, hook: 'pipeline', holdKind: 'strict', skills: [{ skill: 'tdd', status: 'followed', at: 7 }, { skill: 'doc-sync', status: 'ignored', at: 8 }] })
})

test('a skip line never declines a strict adapter hold: only loading the skill clears it', async () => {
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    ...hookEvents(PIPELINE, 2, { holdsOnly: true }),
    { kind: 'load', t: 3, skill: 'tdd', via: 'tool', isSubagent: false },
    ...markerEvents('goated-skip: doc-sync: change touches only test fixtures', 4),
    { kind: 'turn-end', t: 5 },
  ])
  expect(s.nudges).toEqual({ pipeline: { followed: 1, ignored: 1 } })
  const row = s.timeline.find(e => e.kind === 'nudge')
  expect(row?.kind === 'nudge' && row.skills[1]).toEqual({ skill: 'doc-sync', status: 'ignored', at: 5 })
})

test('a justified skip line declines a justified-skip hold it names, before or after the hold, keeping the reason', async () => {
  const design = 'PreToolUse:Edit hook error: goated-hold: design | justified-skip\nLoad `doc-sync` or write a skip line.'
  const after = summarize([
    { kind: 'prompt', t: 1, named: [] },
    ...hookEvents(design, 2, { holdsOnly: true }),
    ...markerEvents('goated-skip: doc-sync: change touches only test fixtures', 3),
  ])
  expect(after.nudges).toEqual({ design: { declined: 1 } })
  expect(after.holds).toEqual({ 'justified-skip': 1 })
  const row = after.timeline.find(e => e.kind === 'nudge')
  expect(row?.kind === 'nudge' && row.skills[0]).toEqual({ skill: 'doc-sync', status: 'declined', at: 3, reason: 'change touches only test fixtures' })
  const before = summarize([
    { kind: 'prompt', t: 1, named: [] },
    ...markerEvents('goated-skip: doc-sync: change touches only test fixtures', 2),
    ...hookEvents(design, 3, { holdsOnly: true }),
  ])
  expect(before.nudges).toEqual({ design: { declined: 1 } })
})

// ---------- overrides ---------------------------------------------------------------

// The adapter's notice for one phrase, and as it reads for two.
const NOTICE = ADAPTER_TEXTS.overrideContext.replace('"Skip routing"', '"Skip routing", "skip the tdd skill"')

test('the adapter\'s own notice for one override reads as that phrase', async () => {
  expect(overrideEvents(ADAPTER_TEXTS.overrideContext, 3)).toEqual([{ kind: 'override', t: 3, phrases: ['skip routing'] }])
})

test("the adapter's override notice records each phrase you typed, and nothing else does", async () => {
  expect(overrideEvents(NOTICE, 3)).toEqual([{ kind: 'override', t: 3, phrases: ['skip routing', 'skip the tdd skill'] }])
  // A warning that also notes a failed save still carries the override.
  expect(overrideEvents('GOATED Claude Code adapter: recorded your override for this prompt: "skip doc-sync"; could not save its session state (EACCES).', 3)).toEqual([
    { kind: 'override', t: 3, phrases: ['skip doc-sync'] },
  ])
  expect(overrideEvents('GOATED Claude Code adapter: the transcript cannot be read, so this action was allowed without checks.', 3)).toEqual([])
  expect(overrideEvents('You wrote: recorded your override for this prompt: "skip routing".', 3)).toEqual([])
})

test('the override sentence is found inside hook context beside other notices, which is where mods can read it', async () => {
  // The notice row itself reaches a mod with no text; the adapter's hook context carries the same sentence.
  const context = `The GOATED shared policy is not loaded. ${NOTICE}`
  expect(overrideEvents(context, 3)).toEqual([{ kind: 'override', t: 3, phrases: ['skip routing', 'skip the tdd skill'] }])
})

test('overrides are counted by phrase, logged, and add up across sessions', async () => {
  const s = summarize([{ kind: 'prompt', t: 1, named: [] }, ...overrideEvents(NOTICE, 2)])
  expect(s.overrides).toEqual({ 'skip routing': 1, 'skip the tdd skill': 1 })
  expect(s.timeline.at(-1)).toEqual({ kind: 'override', t: 2, phrases: ['skip routing', 'skip the tdd skill'] })
  expect(addSession(addSession(null, s), s).overrides).toEqual({ 'skip routing': 2, 'skip the tdd skill': 2 })
})

// ---------- required-reference reads -----------------------------------------------

test('a read of a reference file the route requires is recorded against its skill, loaded or not', async () => {
  // A reference the design skill requires before its red-flag scan.
  const uses = [{ name: 'Read', input: { file_path: '/home/me/.claude/skills/software-design-principles/references/red-flags.md' } }]
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'route', t: 2, form: 'route', intensity: 'standard', requires: ['software-design-principles'] },
    ...toolUseEvents(uses, false, 3),
    { kind: 'load', t: 4, skill: 'software-design-principles', via: 'tool', isSubagent: false },
    ...toolUseEvents(uses, false, 5),
  ])
  expect(s.refs).toEqual({ 'software-design-principles': { 'references/red-flags.md': 2 } })
  expect(s.refsUnloaded).toBe(1)
})

// ---------- subagents ---------------------------------------------------------------

const SPAWN = { name: 'Agent', input: { description: 'Scan the repo', subagent_type: 'Explore', prompt: 'Find every caller of x.' } }

test('a subagent spawn is recorded with its type and task, by the main agent or a subagent', async () => {
  // A spawn hands work on, so it is also a write, as the adapter holds it.
  expect(toolUseEvents([SPAWN], false, 4)).toEqual([{ kind: 'spawn', t: 4, agentType: 'Explore', description: 'Scan the repo' }, { kind: 'write', t: 4 }])
  expect(toolUseEvents([{ name: 'Agent', input: { description: 'Help', prompt: 'x' } }], true, 4, 'a1')).toEqual([
    { kind: 'spawn', t: 4, agentType: 'general-purpose', description: 'Help', isSubagent: true, agent: 'a1' },
  ])
})

test('a subagent that loads no skill still counts and shows in the log', async () => {
  const s = summarize([{ kind: 'prompt', t: 1, named: [] }, ...toolUseEvents([SPAWN], false, 2), { kind: 'turn-end', t: 3, agent: 'a1' }])
  expect(s.loads).toEqual({})
  expect(s.subagents).toEqual({ spawns: 1, starts: 0, bodyReads: 0 })
  expect(s.timeline.at(-1)).toEqual({ kind: 'spawn', t: 2, agentType: 'Explore', description: 'Scan the repo' })
})

test("a subagent reading a skill's SKILL.md is a body read, which settles that subagent's nudge for it", async () => {
  const read = toolUseEvents([{ name: 'Read', input: { file_path: 'C:\\home\\.claude\\skills\\tdd\\SKILL.md' } }], true, 4, 'a1')
  expect(read).toEqual([{ kind: 'body', t: 4, skill: 'tdd', isSubagent: true, agent: 'a1' }])
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'nudge', t: 2, hook: 'design', named: ['tdd'], holdKind: 'justified-skip', isSubagent: true, agent: 'a1' },
    { kind: 'nudge', t: 3, hook: 'design', named: ['tdd'], holdKind: 'justified-skip', isSubagent: true, agent: 'a2' },
    ...read,
    { kind: 'turn-end', t: 5, agent: 'a2' },
  ])
  expect(s.nudges).toEqual({ design: { 'read files': 1, ignored: 1 } })
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
  const stored: Record<string, unknown> = { tab: 'session', events: { shape: 'events-2', value: events } }
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
    ...hookEvents(PIPELINE.replace('`tdd`, `doc-sync`', '`tdd`'), 4, { holdsOnly: true }),
    { kind: 'load', t: 5, skill: 'tdd', via: 'tool', isSubagent: false },
    ...toolUseEvents([SPAWN], false, 6),
    // A start message, as events stored by earlier versions carry it.
    { kind: 'subagent-start', t: 7, agent: 'a1' },
  ])
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await mount(surface)
    expect((await ui.find({ type: 'Text', text: /^standard · requires tdd$/ }))?.text).toBeDefined()
    expect((await ui.find({ type: 'Text', text: /^pipeline hold → $/ }))?.text).toBeDefined()
    expect((await ui.find({ type: 'Text', text: /^you typed "skip doc-sync"$/ }))?.text).toBeDefined()
    expect((await ui.find({ type: 'Text', text: /^Explore started: Scan the repo$/ }))?.text).toBeDefined()
    expect((await ui.find({ type: 'Text', text: /^a subagent received its start message$/ }))?.text).toBeDefined()
    expect(
      (await ui.find({ type: 'Text', text: /^Routes: 1 routed · Writing turns: 1 routed · Adapter holds: 1 strict · Overrides: 1 · Subagents: 1 started, 1 start message$/ }))?.text,
    ).toBeDefined()
    await ui.unmount()
  }
})

test('a subagent that loads no skill lights the Subagents node, with its spawn count on a badge', async ($, on) => {
  const mount = paneRig($, on, [{ kind: 'prompt', t: 1, named: [] }, ...toolUseEvents([SPAWN], false, 2)])
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
    ...hookEvents(ROUTER_FIRST, 3, { holdsOnly: true }),
    ...overrideEvents(NOTICE, 4),
    ...toolUseEvents([SPAWN], false, 5),
  ])
  const report = reportText(addSession(null, s), null)
  expect(report).toContain('## Routes and adapter holds')
  expect(report).toContain('- Route lines: 1 direct')
  expect(report).toContain('- Adapter holds: 1 strict')
  expect(report).toContain('- Overrides: "skip routing" 1 · "skip the tdd skill" 1')
  expect(report).toContain('- Subagents: 1 started · 0 skill bodies read')
})

// Ticket 077: the adapter records `commit message: <text>` as "commit message", its text left out.
test('the commit-message override is shown as the documented phrase, and no other phrase is relabelled', async () => {
  const notice = 'GOATED Claude Code adapter: recorded your override for this prompt: "commit message", "skip commit-message".'
  const s = summarize([{ kind: 'prompt', t: 1, named: [] }, ...overrideEvents(notice, 2)])
  expect(s.overrides).toEqual({ 'commit message': 1, 'skip commit-message': 1 })
  const report = reportText(addSession(null, s), null)
  expect(report).toContain('- Overrides: "commit message: <text>" 1 · "skip commit-message" 1')
})

test('the Session tab shows the commit-message override as the documented phrase', async ($, on) => {
  const mount = paneRig($, on, [
    { kind: 'prompt', t: 1, named: [] },
    ...overrideEvents('GOATED Claude Code adapter: recorded your override for this prompt: "commit message".', 2),
  ])
  const ui = await mount('terminal')
  expect((await ui.find({ type: 'Text', text: /^you typed "commit message: <text>"$/ }))?.text).toBeDefined()
  await ui.unmount()
})

// ---------- rows as session.append carries them ------------------------------------

// The kit raises only a plugin's own rows (door `note`), so these drive the row reader that observeRow hands each row to.
const row = (door: string, content: Row['message']['content'], more: Partial<Row['message']> & { agentId?: string } = {}): Row => {
  const { agentId, ...message } = more
  return { door, ...(agentId ? { agentId } : {}), message: { content, ...message } }
}
const SEEN = {}

test("the adapter's notice row, as Claude Code 2.1.325 hands it to a mod, carries no text and yields nothing", async () => {
  const notice = row('hook-context', [], { name: 'hook_system_message' })
  expect(isObservedRow(notice)).toBe(true)
  expect(rowEvents(notice, SKILLS, 1, SEEN)).toEqual([])
})

test('the override sentence in a main hook-context row is an override; in a subagent row it is not', async () => {
  const context = [{ type: 'text', text: ADAPTER_TEXTS.overrideContext }]
  expect(rowEvents(row('hook-context', context, { name: 'hook_additional_context' }), SKILLS, 1, SEEN)).toEqual([{ kind: 'override', t: 1, phrases: ['skip routing'] }])
  expect(rowEvents(row('hook-context', context, { name: 'hook_additional_context', agentId: 'a1' }), SKILLS, 1, SEEN)).toEqual([])
})

test("a held call's errored tool result is a hold; a plain one is not", async () => {
  const result = (text: string, isError: boolean) => row('tool-result', [{ type: 'tool_result', tool_use_id: 'u1', content: text, is_error: isError }])
  expect(rowEvents(result(PIPELINE, true), SKILLS, 1, SEEN)).toEqual([
    { kind: 'nudge', t: 1, hook: 'pipeline', named: ['tdd', 'doc-sync'], holdKind: 'strict' },
    { kind: 'refused', t: 1, id: 'u1' },
    { kind: 'results', t: 1 },
  ])
  expect(rowEvents(result(PIPELINE, false), SKILLS, 1, SEEN)).toEqual([{ kind: 'results', t: 1 }])
})

test('a reply row gives its route line, then its writes; a typed prompt row is a prompt; other rows are not read', async () => {
  const reply = row('response', [
    { type: 'text', text: 'goated-route: direct' },
    { type: 'tool_use', id: 'u1', name: 'Edit', input: { file_path: 'a.md' } },
  ])
  expect(rowEvents(reply, SKILLS, 1, SEEN)).toEqual([{ kind: 'response', t: 1 }, { kind: 'route', t: 1, form: 'direct' }, { kind: 'write', t: 1, id: 'u1' }])
  expect(rowEvents(row('prompt', [{ type: 'text', text: 'Use tdd here.' }]), SKILLS, 1, SEEN)).toEqual([{ kind: 'prompt', t: 1, named: ['tdd'], isTimed: true }])
  expect(isObservedRow(row('attachment', [{ type: 'text', text: 'x' }], { name: 'environment' }))).toBe(false)
})

// ---------- held calls, and local commands, from the live check ---------------------

test('a spawn or write the adapter held is refused by its errored result: the spawn count and writing turns leave it out', async () => {
  const agent = (id: string) => ({ id, name: 'Agent', input: { description: 'Scan the repo', subagent_type: 'Explore', prompt: 'x' } })
  const refusal = (id: string, reason: string) => row('tool-result', [{ type: 'tool_result', tool_use_id: id, content: held('Agent', reason), is_error: true }])
  const reply = (...uses: { id: string; name: string; input: Record<string, unknown> }[]) => row('response', uses.map(u => ({ type: 'tool_use', ...u })))
  expect(rowEvents(reply(agent('u1')), SKILLS, 1, SEEN)).toEqual([
    { kind: 'response', t: 1 },
    { kind: 'spawn', t: 1, id: 'u1', agentType: 'Explore', description: 'Scan the repo' },
    { kind: 'write', t: 1, id: 'u1' },
  ])
  expect(rowEvents(refusal('u1', ADAPTER_TEXTS.routerFirst), SKILLS, 2, SEEN).find(e => e.kind === 'refused')).toEqual({ kind: 'refused', t: 2, id: 'u1' })

  // Held at router-first, then at the route line, then run once a route line was written.
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    ...rowEvents(reply(agent('u1')), SKILLS, 2, SEEN),
    ...rowEvents(refusal('u1', ADAPTER_TEXTS.routerFirst), SKILLS, 3, SEEN),
    ...rowEvents(reply(agent('u2')), SKILLS, 4, SEEN),
    ...rowEvents(refusal('u2', ADAPTER_TEXTS.routeLine), SKILLS, 5, SEEN),
    ...markerEvents('goated-route: direct', 6),
    ...rowEvents(reply(agent('u3')), SKILLS, 7, SEEN),
  ])
  expect(s.subagents).toEqual({ spawns: 1, starts: 0, bodyReads: 0 })
  expect(s.writingTurns).toEqual({ routed: 1, late: 0, none: 0 })
  // Each attempt keeps its log row; the held ones say so.
  expect(s.timeline.filter(e => e.kind === 'spawn').map(e => e.kind === 'spawn' && (e.isHeld ?? false))).toEqual([true, true, false])
})

test('a turn whose only write was held is not a writing turn', async () => {
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    ...rowEvents(row('response', [{ type: 'tool_use', id: 'e1', name: 'Edit', input: { file_path: 'a.md' } }]), SKILLS, 2, SEEN),
    ...rowEvents(row('tool-result', [{ type: 'tool_result', tool_use_id: 'e1', content: held('Edit', ADAPTER_TEXTS.routeLine), is_error: true }]), SKILLS, 3, SEEN),
  ])
  expect(s.writingTurns).toEqual({ routed: 0, late: 0, none: 0 })
})

test('a local command such as /skill-usage is no prompt, nor is its output; a typed prompt after it is one', async () => {
  // The rows Claude Code 2.1.325 hands a mod for a local command, then a typed prompt.
  const rows = [
    row('command', [{ type: 'text', text: '<local-command-caveat>The command below was run directly in Claude Code.</local-command-caveat>' }], { type: 'user', isMeta: true }),
    row('command', [{ type: 'text', text: '<command-name>/skill-usage</command-name>\n            <command-message>skill-usage</command-message>\n            <command-args></command-args>' }], { type: 'user' }),
    row('command', [{ type: 'text', text: '<local-command-stdout>skill-usage: Skill usage pane opened.</local-command-stdout>' }], { type: 'system' }),
    row('prompt', [{ type: 'text', text: 'Run git log --oneline -3.' }], { type: 'user' }),
  ]
  expect(rows.flatMap(r => rowEvents(r, SKILLS, 1, SEEN))).toEqual([{ kind: 'prompt', t: 1, named: [], isTimed: true }])
  // A skill invoked by its slash command is still a prompt that loads it.
  const tdd = row('command', [{ type: 'text', text: '<command-name>/tdd</command-name>' }], { type: 'user' })
  expect(rowEvents(tdd, SKILLS, 1, SEEN)).toEqual([
    { kind: 'prompt', t: 1, named: [], isTimed: true },
    { kind: 'load', t: 1, skill: 'tdd', via: 'slash', isSubagent: false },
  ])
})

// ---------- compaction and summaries from earlier versions ----------------------------

test('a compaction is one context row: a reference read after it counts as read before loading', async ($, on) => {
  const compaction = row('compaction', [{ type: 'text', text: 'This session is being continued from a previous conversation.' }])
  expect(rowEvents(compaction, SKILLS, 5, SEEN)).toEqual([{ kind: 'compact', t: 5 }])
  // Its boundary and summary arrive as two rows: the second adds nothing, nor does a subagent's.
  expect(rowEvents(compaction, SKILLS, 6, { lastKind: 'compact' })).toEqual([])
  expect(rowEvents(row('compaction', [], { agentId: 'a1' }), SKILLS, 6, SEEN)).toEqual([])
  const events: UsageEvent[] = [
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'load', t: 2, skill: 'tdd', via: 'tool', isSubagent: false },
    { kind: 'ref', t: 3, skill: 'tdd', file: 'references/a.md' },
    { kind: 'compact', t: 4 },
    { kind: 'ref', t: 5, skill: 'tdd', file: 'references/a.md' },
  ]
  const s = summarize(events)
  expect(s.refsUnloaded).toBe(1)
  expect(s.timeline.map(e => e.kind)).toEqual(['prompt', 'load', 'ref', 'compact', 'ref'])
  const ui = await paneRig($, on, events)('terminal')
  expect(await ui.find({ type: 'Text', text: /^compacted · checks re-armed$/ })).toBeDefined()
  await ui.unmount()
})

test('a summary stored by an earlier version still shows its hook keys and already-loaded counts, in the report and All time', async ($, on) => {
  const earlier = { ...summarize([{ kind: 'prompt', t: 1, named: [] }]), nudges: { 'commit-hold': { followed: 1, 'already loaded': 2 } } }
  const all = addSession(null, earlier)
  const text = reportText(all, null)
  expect(text).toContain('- commit check: 3 of 3 handled (100%)')
  expect(text).toContain('already loaded 2')
  const stored: Record<string, unknown> = { tab: 'all', events: { shape: 'events-2', value: [] }, allTime: { shape: 'all-time-1', value: all } }
  on('clock.now', () => ({ value: 100_000 }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', () => ({ value: { isSet: true, version: 2 } }))
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /^commit check$/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^3 of 3$/ })).toBeDefined()
  await ui.unmount()
})
