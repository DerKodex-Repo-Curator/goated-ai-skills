// What lies behind each hold count (Ticket 075): the closeout item each
// closeout hold asks for, the reason of each skip line that declined a hold,
// and why a hold with no answer went unanswered. The hold texts are the
// adapter's own, generated into adapter-texts.ts.

import { expect, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'

import type { UsageEvent } from '../types'
import { addSession, allTimeOf, hookEvents, markerEvents, mergeSummaries, summarize } from '../hooks/classify'
import { reportText, statusText } from '../hooks/view'
import { ADAPTER_TEXTS } from './adapter-texts'

const denied = (tool: string, text: string) => `PreToolUse:${tool} hook error: ${text}`
const blockedStop = (reason: string) => `<system-reminder>\nStop hook blocking error from command: "python goated_hook.py": ${reason}\n</system-reminder>`

const prompt = (t = 1): UsageEvent => ({ kind: 'prompt', t, named: [] })
const response = (t: number): UsageEvent => ({ kind: 'response', t })
const results = (t: number): UsageEvent => ({ kind: 'results', t })
const turnEnd = (t: number, reason?: 'answer' | 'aborted'): UsageEvent => ({ kind: 'turn-end', t, ...(reason ? { reason } : {}) })
const preHold = (tool: string, text: string, t: number) => hookEvents(denied(tool, text), t, { holdsOnly: true })
const stopHold = (t: number, text: string = ADAPTER_TEXTS.closeout) => hookEvents(blockedStop(text), t)

const PANE = {
  plugin: 'skill-usage',
  component: 'Pane',
  requestId: 'skill-usage',
  props: { title: 'Skill usage', isFocused: false, bodyColumns: 60, placement: 'dock', scroll: { offset: 0, bodyRows: 60 }, view: {} },
} as const

// ---------- closeout items --------------------------------------------------------

test('a closeout hold listing Proof and Docs adds one to each item, and each shows its own outcome', async () => {
  // The hold lists Proof and Docs; a skip line declines Docs, and the turn then ends past the hold, which meets Proof.
  const skipDocs = markerEvents('goated-skip: doc-sync: only a test file changed here', 3)
  const s = summarize([prompt(), response(1), ...stopHold(2), results(2), response(3), ...skipDocs, turnEnd(4)])
  expect(s.closeoutItems).toEqual({ Proof: { followed: 1 }, Docs: { declined: 1 } })
  // Near miss: a closeout hold listing only Setup adds nothing to Proof or Docs.
  const setup = summarize([prompt(), response(1), ...stopHold(2, ADAPTER_TEXTS.closeoutSetup), results(2), response(3), turnEnd(4)])
  expect(setup.closeoutItems).toEqual({ Setup: { followed: 1 } })
})

test('a closeout hold on a commit and one at Stop are split into items the same way', async () => {
  const atCommit = summarize([prompt(), response(1), ...preHold('Bash', ADAPTER_TEXTS.closeoutCommit, 2), results(2), response(3), turnEnd(4)])
  const atStop = summarize([prompt(), response(1), ...stopHold(2), results(2), response(3), turnEnd(4)])
  expect(atCommit.closeoutItems).toEqual({ Proof: { followed: 1 }, Docs: { followed: 1 } })
  expect(atStop.closeoutItems).toEqual(atCommit.closeoutItems)
  // Near miss: another gate's hold, which lists no items, adds none.
  const design = summarize([prompt(), response(1), ...preHold('Write', ADAPTER_TEXTS.design, 2), results(2), response(3), turnEnd(4)])
  expect(design.closeoutItems).toEqual({})
})

test('every closeout item the adapter writes is read by its label', async () => {
  const items = (text: string) => Object.keys(summarize([prompt(), response(1), ...stopHold(2, text), results(2), response(3), turnEnd(4)]).closeoutItems ?? {})
  expect(items(ADAPTER_TEXTS.closeoutUnfinished)).toEqual(['Unfinished', 'Docs', 'Design'])
  expect(items(ADAPTER_TEXTS.closeoutChangeRead)).toEqual(['Docs', 'Design', 'Security'])
})

test('the pane and the report show each closeout item with its outcomes', async ($, on) => {
  const skipDocs = markerEvents('goated-skip: doc-sync: only a test file changed here', 3)
  const events = [prompt(), response(1), ...stopHold(2), results(2), response(3), ...skipDocs, turnEnd(4)]
  const all = addSession(null, summarize(events))
  const report = reportText(all, null)
  expect(report).toContain('## Closeout items\n\n- Docs: 1 of 1 handled (100%) · declined 1\n- Proof: 1 of 1 handled (100%) · loaded 1')
  // Near miss: with no closeout hold, or none recorded by an earlier version, the report says so.
  expect(reportText(addSession(null, summarize([prompt()])), null)).toContain('## Closeout items\n\n(none recorded)')
  const stored: Record<string, unknown> = { tab: 'session', events: { shape: 'events-4', value: events } }
  on('clock.now', () => ({ value: 50_000 }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /^Closeout items this session$/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^Proof$/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^Docs$/ })).toBeDefined()
  await ui.unmount()
})

// ---------- skip reasons ----------------------------------------------------------

const DESIGN_SKIP = 'goated-skip: software-design-principles: renames one local variable only'

test("a skip line's reason is stored under its skill and gate, and All time lists it there", async ($, on) => {
  const events = [prompt(), response(1), ...preHold('Write', ADAPTER_TEXTS.design, 2), results(2), response(3), ...markerEvents(DESIGN_SKIP, 3), turnEnd(4)]
  const s = summarize(events)
  expect(s.skipReasons).toEqual({ 'software-design-principles': { design: { 'renames one local variable only': 1 } } })
  // All time adds the same reason from two sessions into one count.
  const all = addSession(addSession(null, s), s)
  expect(all.skipReasons).toEqual({ 'software-design-principles': { design: { 'renames one local variable only': 2 } } })
  expect(reportText(all, null)).toContain('- software-design-principles › design hold: "renames one local variable only" ×2')
  // The All time tab lists it under its skill and gate.
  const stored: Record<string, unknown> = { tab: 'all', events: { shape: 'events-4', value: events } }
  on('clock.now', () => ({ value: 500 }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /^software-design-principles › design hold$/ })).toBeDefined()
  expect((await ui.find({ type: 'Text', text: /renames one local/ }))?.text).toBe('"renames one local variable only" ×1')
  await ui.unmount()
})

test('a skip line that declined no hold stores no reason, and one the closeout asked past is taken back', async () => {
  // Near miss: the same skip line with no hold it answers.
  const free = summarize([prompt(), response(1), ...markerEvents(DESIGN_SKIP, 2), turnEnd(3)])
  expect(free.skipReasons).toEqual({})
  // A blocked Stop that asks for doc-sync again after its skip line: that line did not clear it, so its reason goes.
  const skip = markerEvents('goated-skip: doc-sync: nothing here is documented', 3)
  const askedPast = summarize([prompt(), response(1), ...stopHold(2), results(2), response(3), ...skip, ...stopHold(4), results(4), turnEnd(5, 'aborted')])
  expect(askedPast.skipReasons).toEqual({})
})

test('a 500-character reason is stored cut to a fixed length', async () => {
  const long = `${'because '.repeat(63)}end`
  expect(long.length).toBeGreaterThanOrEqual(500)
  const s = summarize([prompt(), response(1), ...preHold('Write', ADAPTER_TEXTS.design, 2), results(2), ...markerEvents(`goated-skip: software-design-principles: ${long}`, 3), turnEnd(4)])
  const [reason = ''] = Object.keys(s.skipReasons?.['software-design-principles']?.design ?? {})
  expect(reason).toBe(`${long.slice(0, 159)}…`)
  // Near miss: a reason at the limit is stored whole.
  const fits = `one two ${'x'.repeat(152)}`
  expect(fits.length).toBe(160)
  const kept = summarize([prompt(), response(1), ...preHold('Write', ADAPTER_TEXTS.design, 2), results(2), ...markerEvents(`goated-skip: software-design-principles: ${fits}`, 3), turnEnd(4)])
  expect(Object.keys(kept.skipReasons?.['software-design-principles']?.design ?? {})).toEqual([fits])
})

test('a path in a skip reason is masked before it is stored, whatever form it takes', async () => {
  const kept = (reason: string) => {
    const s = summarize([prompt(), response(1), ...preHold('Write', ADAPTER_TEXTS.design, 2), results(2), ...markerEvents(`goated-skip: software-design-principles: ${reason}`, 3), turnEnd(4)])
    return Object.keys(s.skipReasons?.['software-design-principles']?.design ?? {})
  }
  expect(kept('only edited C:/Users/someone/client/app/x.ts here')).toEqual(['only edited <path> here'])
  expect(kept('only edited C:\\Users\\someone\\x.ts here')).toEqual(['only edited <path> here'])
  expect(kept('only edited /home/someone/client/x.ts here')).toEqual(['only edited <path> here'])
  expect(kept('only edited ~/client/x.ts here')).toEqual(['only edited <path> here'])
  expect(kept('only edited \\\\server\\share\\x.ts here')).toEqual(['only edited <path> here'])
  expect(kept('only edited src\\client\\x.ts here')).toEqual(['only edited <path> here'])
  // The skip event keeps only the masked reason too, so the activity log never shows the path.
  expect(markerEvents('goated-skip: tdd: only edited /home/someone/x.ts here', 1)).toEqual([{ kind: 'skip', t: 1, skill: 'tdd', reason: 'only edited <path> here' }])
  // Near misses: an ordinary reason, a word pair with a slash, and a tilde for about, stay as written.
  expect(kept('renames one local variable only')).toEqual(['renames one local variable only'])
  expect(kept('a read and/or write of ~5 lines in tests')).toEqual(['a read and/or write of ~5 lines in tests'])
})

// ---------- unanswered holds ------------------------------------------------------

const override = (t: number, ...phrases: string[]): UsageEvent => ({ kind: 'override', t, phrases })
// A design hold the agent left: no load, read or skip line answers it.
const leftOpen = [prompt(), response(1), ...preHold('Write', ADAPTER_TEXTS.design, 2), results(2), response(3)]

test('a hold the agent never answered, before its turn ended or the session did, counts as unanswered', async () => {
  expect(summarize([...leftOpen, turnEnd(4, 'answer')]).nudges).toEqual({ design: { unanswered: 1 } })
  expect(summarize(leftOpen, true).nudges).toEqual({ design: { unanswered: 1 } })
  // Near miss: while the session runs it is still waiting.
  expect(summarize(leftOpen).nudges).toEqual({ design: { pending: 1 } })
})

test('a hold whose turn a new prompt ended counts as ended by a new prompt', async () => {
  expect(summarize([...leftOpen, prompt(4), response(5)]).nudges).toEqual({ design: { 'new prompt': 1 } })
  // A turn you stopped ended the same way: you cut it off.
  expect(summarize([...leftOpen, turnEnd(4, 'aborted'), prompt(5)]).nudges).toEqual({ design: { 'new prompt': 1 } })
  // Near miss: a turn that ended on its own before the prompt left it unanswered.
  expect(summarize([...leftOpen, turnEnd(4, 'answer'), prompt(5)]).nudges).toEqual({ design: { unanswered: 1 } })
})

test("a hold the next prompt's override stands down counts as overridden by you", async () => {
  expect(summarize([...leftOpen, turnEnd(4), prompt(5), override(5, 'skip software-design-principles'), response(6)]).nudges).toEqual({ design: { overridden: 1 } })
  expect(summarize([...leftOpen, prompt(4), override(4, 'skip the software-design-principles skill')]).nudges).toEqual({ design: { overridden: 1 } })
  // Routing overrides stand down the route-line hold; a typed commit message, the commit hold.
  const routeLine = [prompt(), response(1), ...preHold('Write', ADAPTER_TEXTS.routeLine, 2), results(2), turnEnd(3), prompt(4)]
  expect(summarize([...routeLine, override(4, 'skip routing')]).nudges).toEqual({ 'route-line': { overridden: 1 } })
  const commit = [prompt(), response(1), ...preHold('Bash', ADAPTER_TEXTS.commit, 2), results(2), turnEnd(3), prompt(4)]
  expect(summarize([...commit, override(4, 'commit message: fix the parser')]).nudges).toEqual({ commit: { overridden: 1 } })
  // Near misses: an override of another skill, and one typed after the agent has begun the new turn.
  expect(summarize([...leftOpen, turnEnd(4), prompt(5), override(5, 'skip tdd')]).nudges).toEqual({ design: { unanswered: 1 } })
  expect(summarize([...leftOpen, prompt(4), response(5), override(6, 'skip software-design-principles')]).nudges).toEqual({ design: { 'new prompt': 1 } })
})

test('every override form the adapter accepts stands its hold down', async () => {
  const routeLine = [prompt(), response(1), ...preHold('Write', ADAPTER_TEXTS.routeLine, 2), results(2), turnEnd(3), prompt(4)]
  for (const phrase of ['skip routing', 'skip the routing', 'skip router', 'skip the router', 'skip   the\trouter']) {
    expect(summarize([...routeLine, override(4, phrase)]).nudges).toEqual({ 'route-line': { overridden: 1 } })
  }
  for (const phrase of ['skip software-design-principles', 'skip  the  software-design-principles  skill', 'skip `software-design-principles`', 'skip `software-design-principles']) {
    expect(summarize([...leftOpen, turnEnd(4), prompt(5), override(5, phrase)]).nudges).toEqual({ design: { overridden: 1 } })
  }
  // Near misses: a routing override does not stand down a design hold, nor a skip of a longer skill name.
  expect(summarize([...leftOpen, turnEnd(4), prompt(5), override(5, 'skip routing')]).nudges).toEqual({ design: { unanswered: 1 } })
  expect(summarize([...leftOpen, turnEnd(4), prompt(5), override(5, 'skip software-design-principles-extra')]).nudges).toEqual({ design: { unanswered: 1 } })
})

test('an override counts only against the turn its prompt follows, not an older one', async () => {
  // A prompt interrupted before any reply, then another: its override belongs to the interrupted turn, which held nothing.
  const s = summarize([...leftOpen, turnEnd(4), prompt(5), turnEnd(6, 'aborted'), prompt(7), override(7, 'skip software-design-principles')])
  expect(s.nudges).toEqual({ design: { unanswered: 1 } })
  // Near miss: the override in the prompt right after the hold's turn stands it down.
  expect(summarize([...leftOpen, turnEnd(4), prompt(5), override(5, 'skip software-design-principles')]).nudges).toEqual({ design: { overridden: 1 } })
})

test('a closeout item left unanswered shows its kind as its outcome', async () => {
  const s = summarize([prompt(), response(1), ...stopHold(2), results(2), prompt(3), override(3, 'skip doc-sync')])
  expect(s.closeoutItems).toEqual({ Proof: { 'new prompt': 1 }, Docs: { overridden: 1 } })
})

test('the pane shows the three kinds apart where it showed holds not followed', async ($, on) => {
  // One of each: a design hold you overrode, a security hold your next prompt cut off, a commit hold left unanswered.
  const events = [
    prompt(1), response(1), ...preHold('Write', ADAPTER_TEXTS.design, 2), results(2), turnEnd(3),
    prompt(4), override(4, 'skip software-design-principles'), response(5), ...preHold('Write', ADAPTER_TEXTS.security, 6), results(6),
    prompt(7), response(8), ...preHold('Bash', ADAPTER_TEXTS.commit, 9), results(9), turnEnd(10),
  ]
  const s = summarize(events)
  expect(s.nudges).toEqual({ design: { overridden: 1 }, security: { 'new prompt': 1 }, commit: { unanswered: 1 } })
  expect(statusText(s)).toBe('skills 0 · hooks: 0 followed · 1 overridden · 1 new prompt · 1 unanswered')
  const stored: Record<string, unknown> = { tab: 'session', events: { shape: 'events-4', value: events } }
  on('clock.now', () => ({ value: 50_000 }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /skill load/ }))?.text).toBe('0 skill loads · hooks: 0 followed · 1 overridden · 1 new prompt · 1 unanswered')
  expect((await ui.find({ type: 'Text', text: /^design hold →/ }))?.text).toBe('design hold → software-design-principles overridden by you')
  expect((await ui.find({ type: 'Text', text: /^security hold →/ }))?.text).toBe('security hold → code-security-review ended by a new prompt')
  expect((await ui.find({ type: 'Text', text: /^commit hold →/ }))?.text).toBe('commit hold → commit-message unanswered')
  // Near miss: no holds not followed, no such words.
  expect(statusText(summarize([prompt()]))).toBe('skills 0')
  await ui.unmount()
})

// ---------- across the update -----------------------------------------------------

test('a summary stored before this change still displays: its holds not answered, with no items or reasons', async ($, on) => {
  // A summary as the previous version stored it: one closeout hold not followed, no closeout items, no skip reasons.
  const { closeoutItems: _items, skipReasons: _reasons, ...shape } = summarize([prompt()])
  const earlier = { ...shape, nudges: { closeout: { followed: 1, ignored: 3 } }, holds: { 'justified-skip': 4 } }
  const { total } = allTimeOf([['s:earlier', { t: 1, summary: earlier }]], null, 300, 's:now')
  if (!total) throw new Error('no total')
  const report = reportText(total, null)
  // The report says it in the pane's words.
  expect(report).toContain('- closeout hold: 1 of 4 handled (25%) · loaded 1 · not answered 3')
  expect(report).toContain('## Closeout items\n\n(none recorded)')
  expect(report).toContain('## Skip reasons\n\n(none given yet)')
  // A session resumed across the update adds its new counts to the earlier ones, which keep their meaning.
  const later = summarize([prompt(), response(1), ...preHold('Write', ADAPTER_TEXTS.design, 2), results(2), turnEnd(3)])
  expect(mergeSummaries(earlier, later).nudges).toEqual({ closeout: { followed: 1, ignored: 3 }, design: { unanswered: 1 } })
  const stored: Record<string, unknown> = { tab: 'all', events: { shape: 'events-4', value: [] }, allTime: { shape: 'all-time-2', value: total } }
  on('clock.now', () => ({ value: 100_000 }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', () => ({ value: { isSet: true, version: 2 } }))
  // The pane adds the running session, empty here, to the stored one.
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text', text: /skill load/ }))?.text).toBe('2 sessions · 0 skill loads · hooks: 1 followed · 3 not answered')
  expect(await ui.find({ type: 'Text', text: /^1 of 4$/ })).toBeDefined()
  await ui.unmount()
})

/**
 * Starts a session that runs across the update, with its events and backfill mark stored as `stored` says, and returns
 * the events the mod keeps afterwards.
 */
async function startAcrossUpdate($: Parameters<TestBody>[0], on: Parameters<TestBody>[1], stored: Record<string, unknown>): Promise<UsageEvent[]> {
  const history = [
    { role: 'user' as const, content: [{ type: 'text' as const, text: 'Fix the parser' }] },
    { role: 'assistant' as const, content: [{ type: 'text' as const, text: 'Done.' }] },
    { role: 'user' as const, content: [{ type: 'text' as const, text: blockedStop(ADAPTER_TEXTS.closeout) }] },
  ]
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('clock.now', () => ({ value: 1_000_000 }))
  on('session.id', () => ({ value: 'running' }))
  // The mod reads only the skill listing of the usage breakdown; the rest of it is left out.
  const usage = { context: { breakdown: { skills: { skillFrontmatter: [], totalSkills: 0, includedSkills: 0, tokens: 0 } } } }
  on('session.usage', () => ({ value: usage as never }))
  on('session.messages', () => ({ value: history }))
  on('command.register', () => ({ value: { command: 'skill-usage' } }))
  on('ui.open', () => ({ value: { isPlaced: false, reason: 'no pane in this test' } }))
  on('ui.status', () => ({ value: undefined }))
  on('store.keys', () => ({ value: [] }))
  on('store.get', () => ({ value: undefined }))
  on('store.set', () => ({ value: undefined }))
  on('store.delete', () => ({ value: undefined }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', (_, e) => {
    const { key, value } = e as { key: string; value: unknown }
    stored[key] = value
    return { value: { isSet: true, version: 2 } }
  })
  await $.session.start({ cwd: '/project', surface: null, isInteractive: false })
  return (stored.events as { value: UsageEvent[] }).value
}

// The previous version's events: the closeout hold, recorded with no items.
const OLD_EVENTS: UsageEvent[] = [prompt(), { kind: 'nudge', t: 2, hook: 'closeout', named: ['verification-before-completion', 'doc-sync'], holdKind: 'justified-skip', isStop: true }]

test('a session running across the update reads its history again instead of misreading the events stored before it', async ($, on) => {
  const events = await startAcrossUpdate($, on, { owner: 'running', backfilled: 'running', events: { shape: 'events-2', value: OLD_EVENTS } })
  // Its events were dropped and rebuilt from history, so the closeout hold now lists its items.
  expect(summarize(events).closeoutItems).toEqual({ Proof: { pending: 1 }, Docs: { pending: 1 } })
})

test('a session already on this version keeps its events: its history is not read again', async ($, on) => {
  // Near miss: the same events stored under the current tag stay as they are, items or not.
  const events = await startAcrossUpdate($, on, { owner: 'running', backfilled: { shape: 'events-4', value: 'running' }, events: { shape: 'events-4', value: OLD_EVENTS } })
  expect(events).toEqual(OLD_EVENTS)
  expect(summarize(events).closeoutItems).toEqual({})
})
