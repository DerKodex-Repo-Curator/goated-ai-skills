import { expect, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'

import type { TimelineEntry, UsageEvent } from '../types'
import type { HistoryMessage } from '../hooks/classify'
import { addSession, allTimeOf, closeOpen, historyEvents, hookNudges, mergeSummaries, skillFiles, skillsInPath, skillsNamed, markerEvents, summarize, toolUseEvents } from '../hooks/classify'
import { DECLINED_COLOR, followCounts, PANE_COLUMNS, READ_COLOR, reportText, statusText } from '../hooks/view'
import { badgeWords, PREVIEW_MS, playQueue, previewTimeline } from '../hooks/picture'
import { ADAPTER_TEXTS } from './adapter-texts'

// `run` is a real built-in skill name that also appears as a plain word in hook messages.
const SKILLS = ['using-goated-ai-skills', 'software-design-principles', 'code-security-review', 'tdd', 'commit-message', 'run']

test('an open nudge is pending while the session runs and ignored once it ended', async () => {
  const events: UsageEvent[] = [
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'nudge', t: 2, hook: 'design', named: ['software-design-principles'], holdKind: 'justified-skip' },
  ]
  expect(summarize(events).nudges).toEqual({ design: { pending: 1 } })
  expect(summarize(events, true).nudges).toEqual({ design: { unanswered: 1 } })
})

test('a stored session that never ended cleanly has no nudge left waiting', async () => {
  // A crash or a resume leaves "pending" in the store; nothing can settle it any more, so it reads as ignored.
  const stored = summarize([
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'nudge', t: 2, hook: 'design', named: ['software-design-principles'], holdKind: 'justified-skip' },
  ])
  expect(stored.nudges).toEqual({ design: { pending: 1 } })
  expect(closeOpen(stored).nudges).toEqual({ design: { unanswered: 1 } })
  expect(stored.nudges).toEqual({ design: { pending: 1 } })
})

test('all time keeps every session: past the cap, the oldest fold into one total of older sessions instead of being dropped', async () => {
  const session = (skill: string, t: number) => ({ t, summary: summarize([{ kind: 'prompt', t, named: [] }, { kind: 'load', t, skill, via: 'tool', isSubagent: false }]) })
  const stored: [string, ReturnType<typeof session>][] = [['s:b', session('tdd', 2)], ['s:a', session('tdd', 1)], ['s:c', session('diagnose', 3)], ['s:now', session('handoff', 4)]]
  // The running session is left out (the pane adds it live); of the other three, the oldest is past a cap of two.
  const { total, older, folded } = allTimeOf(stored, null, 2, 's:now')
  expect(folded).toEqual(['s:a'])
  expect(older?.sessions).toBe(1)
  expect(older?.loads).toEqual({ tdd: { 'self-initiated': 1 } })
  expect(total?.sessions).toBe(3)
  expect(total?.loads).toEqual({ tdd: { 'self-initiated': 2 }, diagnose: { 'self-initiated': 1 } })
  // A later fold adds to the older total kept before, so its sessions still count.
  const again = allTimeOf([['s:c', session('diagnose', 3)], ['s:d', session('tdd', 5)], ['s:e', session('tdd', 6)]], older, 2, 's:none')
  expect(again.folded).toEqual(['s:c'])
  expect(again.older?.sessions).toBe(2)
  expect(again.total?.sessions).toBe(4)
  expect(again.total?.loads).toEqual({ tdd: { 'self-initiated': 3 }, diagnose: { 'self-initiated': 1 } })
  // Nothing past the cap folds nothing, and a waiting nudge in a stored session counts as ignored, as before.
  const waiting = { t: 1, summary: summarize([{ kind: 'prompt', t: 1, named: [] }, { kind: 'nudge', t: 2, hook: 'design', named: ['software-design-principles'], holdKind: 'justified-skip' }]) }
  const quiet = allTimeOf([['s:w', waiting]], null, 2, 's:none')
  expect(quiet.folded).toEqual([])
  expect(quiet.older).toBeNull()
  expect(quiet.total?.nudges).toEqual({ design: { unanswered: 1 } })
  expect(allTimeOf([], null, 2, 's:none').total).toBeNull()
  // The running session is never folded, even when it is old (a resume): it is stored again at its next turn.
  expect(allTimeOf(stored, null, 1, 's:a').folded).toEqual(['s:c', 's:b'])
})

test('a resumed session adds to what was stored before', async () => {
  const before = summarize([
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'nudge', t: 2, hook: 'router-first', named: ['using-goated-ai-skills'], holdKind: 'strict' },
    { kind: 'load', t: 3, skill: 'using-goated-ai-skills', via: 'tool', isSubagent: false },
  ])
  const after = summarize([
    { kind: 'prompt', t: 4, named: [] },
    { kind: 'load', t: 5, skill: 'tdd', via: 'tool', isSubagent: false },
  ])
  const merged = mergeSummaries(before, after)
  expect(merged.router).toBe('off')
  // A summary stored by an earlier version keeps the router status it carried.
  expect(mergeSummaries({ ...before, router: 'first' }, after).router).toBe('first')
  expect(merged.loads).toEqual({ 'using-goated-ai-skills': { 'hook-nudged': 1 }, tdd: { 'self-initiated': 1 } })
  expect(merged.lastUsed).toEqual({ 'using-goated-ai-skills': 3, tdd: 5 })
})

test('an ordinary tool error is not a hold', async () => {
  expect(hookNudges('COMMIT failed: nothing to commit', true)).toEqual([])
})

test('names and skill paths are found, partial words are not', async () => {
  expect(skillsNamed('please use tdd and /commit-message', SKILLS)).toEqual(['tdd', 'commit-message'])
  expect(skillsNamed('tddx and pre-tdd', SKILLS)).toEqual([])
  expect(skillsInPath('C:\\Users\\me\\.claude\\skills\\software-design-principles\\references\\red-flags.md')).toEqual(['software-design-principles'])
  expect(skillsInPath('cd ~/.claude/skills/tdd && cat SKILL.md')).toEqual(['tdd'])
})

test('a read into a skill settles its nudge by the same skill the reference log names', async () => {
  // A relative path, as a shell command in a source repo writes it.
  expect(skillsInPath('cat skills/software-design-principles/references/red-flags.md')).toEqual(['software-design-principles'])
  // A category folder above the skill is not the skill, whether the read reaches a reference, the SKILL.md or a folder.
  expect(skillsInPath('cat skills/agent-workflows/using-goated-ai-skills/references/routing.md')).toEqual(['using-goated-ai-skills'])
  expect(skillsInPath('cat skills/agent-workflows/using-goated-ai-skills/SKILL.md')).toEqual(['using-goated-ai-skills'])
  expect(skillsInPath('ls ~/.claude/skills/tdd/references/')).toEqual(['tdd'])
  // A file beside the skill folders, or a folder named like one, is no skill.
  expect(skillsInPath('cat skills/README.md && ls goated-ai-skills/x')).toEqual([])
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'nudge', t: 2, hook: 'design', named: ['software-design-principles'], holdKind: 'justified-skip' },
    ...toolUseEvents([{ name: 'Bash', input: { command: 'cat skills/software-design-principles/references/red-flags.md' } }], false, 3),
  ])
  expect(s.nudges).toEqual({ design: { 'read files': 1 } })
})

test('a routed session: origins and outcomes', async () => {
  let t = 0
  // Omit each member of the union on its own, so each event keeps its fields.
  const at = (e: UsageEvent extends infer E ? (E extends unknown ? Omit<E, 't'> : never) : never) => ({ ...e, t: ++t }) as UsageEvent
  const events: UsageEvent[] = [
    at({ kind: 'prompt', named: [] }),
    at({ kind: 'nudge', hook: 'router-first', named: ['using-goated-ai-skills'], holdKind: 'strict' }),
    at({ kind: 'load', skill: 'using-goated-ai-skills', via: 'tool', isSubagent: false }),
    at({ kind: 'load', skill: 'tdd', via: 'tool', isSubagent: false }),
    at({ kind: 'nudge', hook: 'design', named: ['software-design-principles'], holdKind: 'justified-skip' }),
    at({ kind: 'read', skills: ['software-design-principles'] }),
    at({ kind: 'nudge', hook: 'security', named: ['code-security-review'], holdKind: 'justified-skip' }),
    at({ kind: 'prompt', named: ['commit-message'] }),
    at({ kind: 'nudge', hook: 'commit', named: ['commit-message'], holdKind: 'strict' }),
    at({ kind: 'load', skill: 'commit-message', via: 'tool', isSubagent: false }),
    at({ kind: 'load', skill: 'grill-me', via: 'slash', isSubagent: false }),
  ]
  const s = summarize(events)
  expect(s.loads).toEqual({
    'using-goated-ai-skills': { 'hook-nudged': 1 },
    tdd: { 'router-routed': 1 },
    'commit-message': { 'user-named': 1 },
    'grill-me': { 'user-slash': 1 },
  })
  expect(s.nudges).toEqual({
    'router-first': { followed: 1 },
    design: { 'read files': 1 },
    // Still open when the next message arrived, so its turn was over.
    security: { 'new prompt': 1 },
    commit: { followed: 1 },
  })
})

test('a summary has router status off; all-time adds sessions', async () => {
  const s = summarize([{ kind: 'load', t: 1, skill: 'tdd', via: 'tool', isSubagent: true }])
  expect(s.router).toBe('off')
  expect(s.loads).toEqual({ tdd: { subagent: 1 } })
  const all = addSession(addSession(null, s), s)
  expect(all.sessions).toBe(2)
  expect(all.loads).toEqual({ tdd: { subagent: 2 } })
  expect(all.router).toEqual({ off: 2 })
})

test('a stored event of a kind this version no longer records is skipped', async () => {
  // Earlier versions stored a `tool` event at a session's first real tool call.
  const stored = [{ kind: 'prompt', t: 1, named: [] }, { kind: 'tool', t: 2 }, { kind: 'load', t: 3, skill: 'tdd', via: 'tool', isSubagent: false }] as unknown as UsageEvent[]
  const s = summarize(stored)
  expect(s.loads).toEqual({ tdd: { 'self-initiated': 1 } })
  expect(s.timeline.map(e => e.kind)).toEqual(['prompt', 'load'])
})

/**
 * The animated picture: the sandboxed frame laid over the still copy. The
 * still copy, a plain image, comes first in the tree, so a plain `find` would
 * return it.
 */
async function frameOf(ui: { findAll: (q: { type: string }) => Promise<{ props: Record<string, unknown> }[]> }) {
  const frame = (await ui.findAll({ type: 'Svg' })).find(e => e.props.isInteractive === true)
  return frame?.props as { source: string; isInteractive?: boolean; width?: number; height?: number } | undefined
}

const PANE = {
  plugin: 'skill-usage',
  component: 'Pane',
  requestId: 'skill-usage',
  props: {
    title: 'Skill usage',
    isFocused: false,
    bodyColumns: 60,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 30 },
    view: {},
  },
} as const

test('history rebuilds a session the mod joined late, as the live view would see it', async () => {
  const use = (id: string, name: string, input: Record<string, unknown>) => ({ type: 'tool_use', id, name, input })
  const held = (id: string, text: string) => ({ role: 'user' as const, content: [{ type: 'tool_result', tool_use_id: id, is_error: true, content: `PreToolUse:Edit hook error: ${text}` }] })
  const history: HistoryMessage[] = [
    { role: 'user', content: [{ type: 'text', text: 'Fix the bug in calc.py' }] },
    { role: 'assistant', content: [{ type: 'text', text: 'Editing.' }, use('e1', 'Edit', { file_path: 'calc.py' })] },
    held('e1', ADAPTER_TEXTS.routerFirst),
    { role: 'assistant', content: [use('s1', 'Skill', { skill: 'using-goated-ai-skills' })] },
    { role: 'user', content: [{ type: 'tool_result', tool_use_id: 's1', content: 'Launching skill' }, { type: 'text', text: 'Base directory for this skill: ...' }] },
    { role: 'assistant', content: [use('e2', 'Edit', { file_path: 'calc.py' })] },
    held('e2', ADAPTER_TEXTS.design),
    { role: 'assistant', content: [use('s2', 'Skill', { skill: 'software-design-principles' })] },
    { role: 'user', content: [{ type: 'text', text: '<command-name>/tdd</command-name>' }] },
    { role: 'user', content: [{ type: 'text', text: '<task-notification>a background task ended</task-notification>' }] },
  ]
  const events = historyEvents(history, SKILLS, 99)
  expect(events.every(e => e.isEarlier && e.t === 99)).toBe(true)
  expect(events.filter(e => e.kind === 'prompt').length).toBe(2)
  const s = summarize(events)
  expect(s.loads).toEqual({ 'using-goated-ai-skills': { 'hook-nudged': 1 }, 'software-design-principles': { 'hook-nudged': 1 }, tdd: { 'user-slash': 1 } })
  expect(s.nudges).toEqual({ 'router-first': { followed: 1 }, design: { followed: 1 } })
  expect(s.timeline.every(entry => entry.isEarlier)).toBe(true)
})

test('a nudge row keeps when each skill settled, so the picture plays that moment; rebuilt rows keep none', async () => {
  const live = summarize([
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'nudge', t: 2, hook: 'closeout', named: ['code-security-review', 'setup-scribe'] },
    { kind: 'load', t: 5, skill: 'code-security-review', via: 'tool', isSubagent: false },
    { kind: 'prompt', t: 9, named: [] },
  ])
  const row = live.timeline.find(e => e.kind === 'nudge')
  expect(row?.kind === 'nudge' && row.skills).toEqual([
    { skill: 'code-security-review', status: 'followed', at: 5 },
    { skill: 'setup-scribe', status: 'new prompt', at: 9 },
  ])
  const rebuilt = summarize([
    { kind: 'nudge', t: 7, hook: 'design', named: ['software-design-principles'], holdKind: 'justified-skip', isEarlier: true },
    { kind: 'load', t: 7, skill: 'software-design-principles', via: 'tool', isSubagent: false, isEarlier: true },
  ])
  const earlier = rebuilt.timeline.find(e => e.kind === 'nudge')
  expect(earlier?.kind === 'nudge' && earlier.skills).toEqual([{ skill: 'software-design-principles', status: 'followed' }])
})

test("the report uses the pane's words, not internal labels", async () => {
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'nudge', t: 2, hook: 'router-first', named: ['using-goated-ai-skills'], holdKind: 'strict' },
    { kind: 'load', t: 3, skill: 'using-goated-ai-skills', via: 'tool', isSubagent: false },
    { kind: 'nudge', t: 4, hook: 'closeout', named: ['tdd'], holdKind: 'justified-skip' },
    { kind: 'prompt', t: 5, named: [] },
  ])
  const all = addSession(null, s)
  const text = reportText(all, { names: SKILLS, own: ['tdd'], total: 6, included: 6 })
  expect(text).toContain('- router-first hold: 1 of 1 handled (100%) · loaded 1')
  expect(text).toContain('- closeout hold: 0 of 1 handled (0%) · ended by a new prompt 1')
  expect(text).toContain('- using-goated-ai-skills: 1 (after a hook 1)')
  expect(text).toContain('- Subagents: 0 started · 0 skill bodies read')
  expect(text).not.toMatch(/hook-nudged|router-first:|closeout:|GOATED router rule|start message/)
  // Summaries stored by earlier versions still bring their router rule and start messages into the report.
  const stored = reportText({ ...all, router: { first: 1, late: 1 }, subagents: { spawns: 0, starts: 2, bodyReads: 0 } }, null)
  expect(stored).toContain('GOATED router rule: router loaded first in 1 of 2 sessions.')
  expect(stored).toContain('- Subagents: 0 started · 2 start messages · 0 skill bodies read')
})

test("a session's events stored before the retired hooks' reading was removed are dropped, not misread", async ($, on) => {
  // The previous version's events of a running session: the router rule, a route hold for any specialist, a start message.
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: {
      shape: 'events-1',
      value: [
        { kind: 'nudge', t: 1, hook: 'router-rule', named: ['using-goated-ai-skills'] },
        { kind: 'prompt', t: 2, named: [] },
        { kind: 'nudge', t: 3, hook: 'route-hold', named: ['(any specialist)'] },
        { kind: 'subagent-start', t: 4 },
      ],
    },
  }
  on('clock.now', () => ({ value: 500 }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  // The pane drew, with no load and no hold to report.
  expect((await ui.find({ type: 'Text', text: /skill load/ }))?.text).toBe('0 skill loads · no hook nudges yet')
  expect(await ui.find({ type: 'Text', text: /any specialist|→|hooks:/ })).toBeUndefined()
  await ui.unmount()
})

test('the pane shows the session and switches tabs, on every surface', async ($, on) => {
  const stored: Record<string, unknown> = {
    // The events atom keeps a shape tag; an untagged value would read as empty.
    events: {
      shape: 'events-4',
      value: [
        { kind: 'prompt', t: 1, named: [] },
        { kind: 'nudge', t: 2, hook: 'router-first', named: ['using-goated-ai-skills'], holdKind: 'strict' },
        { kind: 'load', t: 3, skill: 'using-goated-ai-skills', via: 'tool', isSubagent: false },
      ],
    },
    available: { shape: 'available-2', value: { names: ['using-goated-ai-skills', 'tdd', 'diagnose', 'docx'], own: ['using-goated-ai-skills', 'tdd', 'diagnose'], total: 50, included: 40 } },
  }
  // Half a second after the load: its pulse is still in flight.
  on('clock.now', () => ({ value: 500 }))
  let version = 1
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version } : { value: undefined, version: 0 } }
  })
  on('state.set', (_, e) => {
    const { key, value } = e as { key: string; value: unknown }
    stored[key] = value
    version += 1
    return { value: { isSet: true, version } }
  })

  for (const surface of ['terminal', 'desktop', 'vscode', 'mobile'] as const) {
    stored.tab = 'session'
    const ui = await $.ui.mount({ ...PANE, surface })
    // The line under the picture says where things stand, in words, on every surface.
    expect((await ui.find({ type: 'Text', text: /skill load/ }))?.text).toBe('1 skill load · hooks: 1 followed')
    // No router rule line: this session had none.
    expect(await ui.find({ type: 'Text', text: /router rule/ })).toBeUndefined()
    // One row per event, newest first, in columns; a nudge is one sentence with its result.
    expect((await ui.find({ type: 'Text', text: /→/ }))?.text).toBe('router-first hold → using-goated-ai-skills loaded')
    // The load half a second ago is still flying from its station to the core, where the picture draws.
    if (surface !== 'terminal') expect((await frameOf(ui))?.source).toContain('<animateMotion')
    expect((await ui.find({ type: 'Text', text: /after a hook/ }))?.text).toBe('using-goated-ai-skills · after a hook')
    expect(await ui.find({ type: 'Text', text: /^new message$/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /^Hook$/ })).toBeDefined()

    await ui.press({ key: 'tab-all' })
    expect(stored.tab).toBe('all')
    await ui.unmount()

    const all = await $.ui.mount({ ...PANE, surface })
    expect(await all.find({ type: 'Text', text: /^router-first hold$/ })).toBeDefined()
    expect(await all.find({ type: 'Text', text: /router rule/ })).toBeUndefined()
    expect(await all.find({ type: 'Text', text: /^1 of 1$/ })).toBeDefined()
    // The outcome bar: one followed of one settled fills the whole bar green, on every surface.
    const fills = (await all.findAll({ type: 'Box' })).filter(b => b.props.backgroundColor === 'success')
    expect(fills.map(b => b.props.width)).toContain('100%')
    // The All time picture is still: it plays no moments.
    if (surface !== 'terminal') expect((await frameOf(all))?.source).not.toContain('<animateMotion')
    await all.press({ key: 'tab-unused' })
    expect(stored.tab).toBe('unused')
    await all.unmount()

    const unused = await $.ui.mount({ ...PANE, surface })
    expect(await unused.find({ type: 'Text', text: /Only 40 of 50 skills fit/ })).toBeDefined()
    // Two lists, one name per row, A to Z: a loaded skill with its count in its own column, then those never loaded.
    expect(await unused.find({ type: 'Text', text: /^using-goated-ai-skills$/ })).toBeDefined()
    expect(await unused.find({ type: 'Text', text: /^×1$/ })).toBeDefined()
    const names = (await unused.findAll({ type: 'Text', text: /^(diagnose|tdd)$/ })).map(t => t.text)
    expect(names).toEqual(['diagnose', 'tdd'])
    // Built-in and plugin skills are summarised, not listed one by one.
    expect(await unused.find({ type: 'Text', text: /docx/ })).toBeUndefined()
    await unused.unmount()
  }
})

test('a nudge flies from Hooks to the agent it spoke to, straight to Agent or to Subagents', async ($, on) => {
  const nudge = (isSubagent: boolean) => ({ kind: 'nudge', t: 400, hook: 'commit', named: ['commit-message'], holdKind: 'strict', ...(isSubagent ? { isSubagent: true } : {}) })
  const stored: Record<string, unknown> = { tab: 'session' }
  on('clock.now', () => ({ value: 500 }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', () => ({ value: { isSet: true, version: 2 } }))
  const motion = async (isSubagent: boolean) => {
    stored.events = { shape: 'events-4', value: [{ kind: 'prompt', t: 1, named: [] }, nudge(isSubagent)] }
    const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
    const svg = String((await frameOf(ui))?.source)
    await ui.unmount()
    return /<animateMotion path="([^"]+)"/.exec(svg)?.[1] ?? ''
  }
  // Hooks sits at the lower right and Claude at the lower left: a straight run below the core, ending at Claude's rim.
  expect(await motion(false)).toBe('M318.9 246 L101.1 246')
  // Subagents, the small node below Agent, gets its nudges straight from Hooks, not through Agent: hooks speak to a subagent directly.
  expect(await motion(true)).toBe('M319.6 251.5 L139.5 300.3')
})

test('moments queue one after another with a gap, from event times alone, and an old backlog is skipped', async () => {
  const timeline: TimelineEntry[] = [
    { t: 1000, kind: 'load', skill: 'tdd', origin: 'self-initiated' },
    { t: 1100, kind: 'nudge', hook: 'commit', holdKind: 'strict', skills: [{ skill: 'commit-message', status: 'followed', at: 1100 }] },
    { t: 1200, kind: 'load', skill: 'caveman', origin: 'user-slash' },
  ]
  const plays = playQueue(timeline)
  // The first waits out its 1000 ms lead-in; each after waits for the one before plus a 450 ms gap. A load is a round trip,
  // two 1 s legs and 800 ms to land (2800 ms); a nudge's sending and its result flying back are one leg each (1800 ms).
  expect(plays.map(p => [p.kind, p.start])).toEqual([
    ['load', 2000],
    ['sent', 5250],
    ['settle', 7500],
    ['load', 9750],
  ])
  // The queue never reads the clock: an idle redraw an hour later sees the same slots, so the picture's text holds.
  expect(playQueue(timeline)).toEqual(plays)
  // A burst long enough that a moment would wait over 12 s drops the late ones instead of playing them long after.
  const burst: TimelineEntry[] = Array.from({ length: 12 }, (_, i) => ({ t: 1000 + i, kind: 'load' as const, skill: `s${i}`, origin: 'self-initiated' as const }))
  expect(playQueue(burst).length).toBeLessThan(12)
})

test('a waiting nudge holds its dotted trail in amber, fading in when its dot sets off', async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: { shape: 'events-4', value: [{ kind: 'prompt', t: 1, named: [] }, { kind: 'nudge', t: 450, hook: 'pull-request', named: ['pr-description'], holdKind: 'strict' }] },
  }
  let now = 500
  on('clock.now', () => ({ value: now }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', () => ({ value: { isSet: true, version: 2 } }))
  const draw = async () => {
    const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
    const svg = String((await frameOf(ui))?.source)
    await ui.unmount()
    return svg
  }
  // 50 ms after the nudge, inside its 1000 ms lead-in: the trail is set to fade in behind the dot when it sets off.
  const flying = await draw()
  expect(flying).toContain('stroke-dasharray="1.5 4.5" stroke="#ffa62b" opacity="0"><animate attributeName="opacity" values="0;.6" begin="0.950s"')
  // Mid-flight, nothing new: the very same text, so the frame keeps its clock.
  now = 1500
  expect(await draw()).toBe(flying)
  // A minute later the dot has long landed: the picture is drawn once more at that time, every moment in its past, so a frame
  // mounted again (another tab, a reopened pane) shows the trail standing, as drawn, instead of replaying the flight. Then it holds.
  now = 60_500
  const settled = await draw()
  expect(settled).not.toBe(flying)
  expect(settled).toContain('stroke-dasharray="1.5 4.5" stroke="#ffa62b" opacity="0.6"/>')
  expect(settled).not.toMatch(/begin="\d/)
  now = 61_000
  expect(await draw()).toBe(settled)
})

test('the still copy under the frame shows a trail only when the frame does, so a rebuilt frame never flashes one', async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: { shape: 'events-4', value: [{ kind: 'prompt', t: 1, named: [] }, { kind: 'nudge', t: 450, hook: 'pull-request', named: ['pr-description'], holdKind: 'strict' }] },
  }
  let now = 500
  on('clock.now', () => ({ value: now }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', () => ({ value: { isSet: true, version: 2 } }))
  const stillAt = async (t: number) => {
    now = t
    const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
    const [still] = await ui.findAll({ type: 'Svg' })
    await ui.unmount()
    return String(still?.props.source)
  }
  const DOTS = 'stroke-dasharray="1.5 4.5"'
  // Inside the lead-in the frame's trail is still hidden, waiting for its dot: the copy under it must not show it either.
  expect(await stillAt(500)).not.toContain(DOTS)
  // Once the dot has set off (450 + 1000 ms), the trail stands in both.
  expect(await stillAt(3000)).toContain(DOTS)
})

test("a trail whose dot set off long ago stands in the frame as drawn, not by replaying an old animation", async ($, on) => {
  // A hold waits until its turn ends; each new moment rebuilds the frame, which must show its trail from the first paint.
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: { shape: 'events-4', value: [{ kind: 'prompt', t: 1, named: [] }, { kind: 'nudge', t: 450, hook: 'router-first', named: ['using-goated-ai-skills'], holdKind: 'strict' }] },
  }
  on('clock.now', () => ({ value: 600_000 }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', () => ({ value: { isSet: true, version: 2 } }))
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  const [still, frame] = (await ui.findAll({ type: 'Svg' })).map(s => String(s.props.source))
  await ui.unmount()
  const trailOf = (src: string | undefined) => src?.match(/<path [^>]*stroke-dasharray="1.5 4.5"[^>]*\/?>/)?.[0]
  expect(trailOf(frame)).toContain('opacity="0.6"')
  expect(frame).not.toContain('values="0;.6"')
  // The still copy under it draws the very same line.
  expect(trailOf(still)?.replace('/>', '>')).toBe(trailOf(frame)?.replace('/>', '>'))
})

test('the preview script plays every kind of moment in turn, none skipped for waiting too long', async () => {
  const script = previewTimeline(1000)
  const plays = playQueue(script)
  // A load from every station, a nudge to Claude and one to Subagents, each settling: one followed (green), one not (red);
  // then a nudge to Claude still waiting while Claude reads a reference, so both dotted ways show at once, and a subagent's read.
  expect(plays.filter(p => p.kind === 'load').map(p => (p.kind === 'load' ? p.origin : '')).sort()).toEqual(
    ['hook-nudged', 'router-routed', 'self-initiated', 'subagent', 'user-named', 'user-slash'],
  )
  const sentTo = plays.flatMap(p => (p.kind === 'sent' ? [script[p.row]] : [])).map(e => (e?.kind === 'nudge' && e.isSubagent ? 'subagents' : 'claude'))
  expect(sentTo).toEqual(['claude', 'subagents', 'claude'])
  expect(plays.filter(p => p.kind === 'settle').map(p => (p.kind === 'settle' && p.acted === p.settled ? 'green' : 'red'))).toEqual(['green', 'red', 'green'])
  expect(plays.map(p => p.kind).slice(-4)).toEqual(['sent', 'ref', 'settle', 'ref'])
  // Every moment in the script gets its slot: the queue skipped none, and all of it finishes inside the preview.
  expect(plays.length).toBe(14)
  expect(Math.max(...plays.map(p => p.start))).toBeLessThan(1000 + PREVIEW_MS)
})

test('during a preview the picture plays the script, while the counts and the activity rows stay real', async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: { shape: 'events-4', value: [{ kind: 'prompt', t: 1, named: [] }] },
    preview: 100_000,
  }
  let now = 100_500
  on('clock.now', () => ({ value: now }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', () => ({ value: { isSet: true, version: 2 } }))
  const look = async () => {
    const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
    const frame = String((await frameOf(ui))?.source)
    const hookRows = await ui.findAll({ type: 'Text', text: /^Hook$/ })
    const counts = (await ui.find({ type: 'Text', text: /skill load/ }))?.text
    await ui.unmount()
    return { frame, hookRows: hookRows.length, counts }
  }
  const during = await look()
  // The script's flights: a reference page, and a red settle at Hooks.
  expect(during.frame).toContain('ref-page')
  expect(during.frame).toContain('#e8654f')
  // Nothing scripted reaches the numbers or the feed.
  expect(during.hookRows).toBe(0)
  expect(during.counts).toMatch(/^0 skill loads/)
  // Once the preview is over the picture is the session's own again.
  now = 100_000 + PREVIEW_MS + 1
  const after = await look()
  expect(after.frame).not.toContain('<animateMotion')
})

test('the Session tab breaks down this session alone: each hook with its follow rate, each skill with its loads', async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: {
      shape: 'events-4',
      value: [
        { kind: 'prompt', t: 1, named: [] },
        { kind: 'nudge', t: 2, hook: 'commit', named: ['commit-message'], holdKind: 'strict' },
        { kind: 'load', t: 3, skill: 'commit-message', via: 'tool', isSubagent: false },
        { kind: 'load', t: 4, skill: 'tdd', via: 'tool', isSubagent: false },
        { kind: 'load', t: 5, skill: 'tdd', via: 'tool', isSubagent: false },
      ],
    },
    // Another session's totals must not show here.
    allTime: { shape: 'all-time-2', value: { sessions: 1, loads: { diagnose: { 'self-initiated': 9 } }, nudges: { 'pull-request': { unanswered: 4 } }, router: {}, lastUsed: {} } },
  }
  on('clock.now', () => ({ value: 100_000 }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', () => ({ value: { isSet: true, version: 2 } }))
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  const text = async (re: RegExp) => (await ui.find({ type: 'Text', text: re }))?.text
  expect(await text(/^Hooks this session$/)).toBeDefined()
  expect(await text(/^commit hold$/)).toBeDefined()
  expect(await text(/^1 of 1$/)).toBeDefined()
  expect(await text(/^Skills this session$/)).toBeDefined()
  // Most loaded first, with its count.
  const skills = (await ui.findAll({ type: 'Text', text: /^(tdd|commit-message)$/ })).map(t => t.text)
  expect(skills.slice(0, 2)).toEqual(['tdd', 'commit-message'])
  expect(await text(/^pull-request hold$/)).toBeUndefined()
  expect(await text(/^diagnose$/)).toBeUndefined()
  await ui.unmount()
})

test("the agent a nudge spoke to holds amber on its border until it sends the result back to Hooks", async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: { shape: 'events-4', value: [{ kind: 'prompt', t: 1, named: [] }, { kind: 'nudge', t: 1000, hook: 'commit', named: ['commit-message'], holdKind: 'strict' }] },
  }
  let now = 1050
  on('clock.now', () => ({ value: now }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', () => ({ value: { isSet: true, version: 2 } }))
  const draw = async () => {
    const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
    const [still = '', frame = ''] = (await ui.findAll({ type: 'Svg' })).map(x => String(x.props.source))
    await ui.unmount()
    return { still, frame }
  }
  // The agent's border, drawn over its node: Claude sits at (80.1, 246) in the picture.
  const border = (src: string, color: string) => src.match(new RegExp(`<circle cx="80.1" cy="246" r="21" fill="none" stroke="${color}" stroke-width="1.8"[^>]*>`))?.[0]
  // Just sent: the border turns amber when the dot lands at Agent (2000 + 1000 ms from the nudge, 1.95 s from now), and holds.
  const sent = await draw()
  expect(border(sent.frame, '#ffa62b')).toBeDefined()
  expect(sent.frame).toContain('<g opacity="0"><set attributeName="opacity" to="1" begin="1.950s"')
  // Long after, still waiting: amber, as drawn, in the frame and the still copy alike.
  now = 30_000
  const holding = await draw()
  expect(holding.frame).toContain('<g opacity="1"><circle cx="80.1" cy="246" r="24"')
  expect(border(holding.still, '#ffa62b')).toContain('opacity="1"')
  // While it holds, the amber breathes, quicker than the badge: the border thickens and brightens, and a glow swells around it.
  // The copy underneath holds still.
  expect(holding.frame).toMatch(/stroke-width="1.8"><animate attributeName="opacity" values=".55;1;.55" begin="-[\d.]+s" dur="1.100s" repeatCount="indefinite"\/><animate attributeName="stroke-width" values="2;4.6;2"/)
  expect(holding.frame).toMatch(/r="24" fill="none" stroke="#ffa62b" stroke-width="7" opacity="0"><animate attributeName="opacity" values="0;.35;0"/)
  expect(holding.still).not.toContain('values=".55;1;.55"')
  // Followed: Agent sends the result back, so its amber ends and it shows no result colour of its own; Hooks receives the green.
  stored.events = { shape: 'events-4', value: [...(stored.events as { value: unknown[] }).value, { kind: 'load', t: 30_000, skill: 'commit-message', via: 'tool', isSubagent: false }] }
  now = 30_050
  const settling = await draw()
  expect(border(settling.frame, '#5fcf8f')).toBeUndefined()
  expect(settling.frame).not.toMatch(/<circle class="arrival" cx="80.1" cy="246"[^>]*stroke="#5fcf8f"/)
  expect(settling.frame).toMatch(/<circle class="arrival" cx="339.9" cy="246" r="25" fill="none" stroke="#5fcf8f"/)
  // Once faded, no border is left on Agent.
  now = 60_000
  const after = await draw()
  expect(border(after.frame, '#5fcf8f')).toBeUndefined()
  expect(border(after.frame, '#ffa62b')).toBeUndefined()
})

test('the picture sits in a sized frame whose text holds still across redraws until what it shows changes', async ($, on) => {
  let now = 2000
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: { shape: 'events-4', value: [{ kind: 'prompt', t: 1, named: [] }, { kind: 'load', t: 1500, skill: 'tdd', via: 'tool', isSubagent: false }] },
  }
  on('clock.now', () => ({ value: now }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', () => ({ value: { isSet: true, version: 2 } }))
  const draw = async () => {
    const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
    const props = (await frameOf(ui)) as { source: string; isInteractive?: boolean; width?: number; height?: number }
    await ui.unmount()
    return props
  }
  // Under the frame, a still copy as a plain image covers the instant a new frame shows blank while it loads.
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  const [still, frame] = await ui.findAll({ type: 'Svg' })
  await ui.unmount()
  expect(still?.props.isInteractive).toBeUndefined()
  expect(String(still?.props.source)).not.toContain('<animate')
  expect(frame?.props.isInteractive).toBe(true)
  const first = await draw()
  // The frame runs SMIL and is kept by the desktop while its text is unchanged; an image would be replaced every time.
  expect(first.isInteractive).toBe(true)
  // Both layers get a width and height in the picture's proportions, small enough that a docked pane need not narrow it (the frame, unlike
  // the image, does not follow the markup's proportions when given no height, and a narrowed one keeps its height, leaving blank bands).
  expect([first.width, first.height]).toEqual([460, 407])
  // Mid-flight, with nothing new: the very same text, so the frame and its clock carry on.
  now = 2600
  expect((await draw()).source).toBe(first.source)
  // Once the flight is over the picture is drawn once more at that time, with nothing left to play, and then holds.
  now = 9000
  const quiet = (await draw()).source
  expect(quiet).not.toBe(first.source)
  expect(quiet).not.toMatch(/begin="\d/)
  now = 9500
  expect((await draw()).source).toBe(quiet)
  // A new moment changes what the picture shows, so it is drawn afresh.
  stored.events = { shape: 'events-4', value: [...(stored.events as { value: unknown[] }).value, { kind: 'load', t: 8900, skill: 'caveman', via: 'slash', isSubagent: false }] }
  expect((await draw()).source).not.toBe(quiet)
})

test('the Unused tab lists loaded skills most loaded first with their share of all loads, and the rest A to Z', async ($, on) => {
  const load = (t: number, skill: string) => ({ kind: 'load', t, skill, via: 'tool', isSubagent: false })
  const stored: Record<string, unknown> = {
    tab: 'unused',
    events: { shape: 'events-4', value: [{ kind: 'prompt', t: 1, named: [] }, load(2, 'tdd'), load(3, 'diagnose'), load(4, 'diagnose'), load(5, 'diagnose')] },
    available: { shape: 'available-2', value: { names: ['tdd', 'diagnose', 'caveman', 'agent-x'], own: ['tdd', 'diagnose', 'caveman', 'agent-x'], total: 4, included: 4 } },
  }
  on('clock.now', () => ({ value: 10 }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', () => ({ value: { isSet: true, version: 2 } }))
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  const texts = async (re: RegExp) => (await ui.findAll({ type: 'Text', text: re })).map(t => t.text)
  // diagnose loaded 3 of the 4 times, tdd once: most loaded first, each with its share as a percentage.
  expect(await texts(/^(diagnose|tdd)$/)).toEqual(['diagnose', 'tdd'])
  expect(await texts(/^\d+%$/)).toEqual(['75%', '25%'])
  // Bars are exact percentages, scaled to the most loaded skill: diagnose fills its bar and tdd, a third of its loads, a third of it.
  // The header's 2 of 4 skills loaded fills half its bar. No grey track sits behind any of them.
  const boxes = await ui.findAll({ type: 'Box' })
  const fills = boxes.filter(b => b.props.backgroundColor === 'success').map(b => b.props.width)
  expect(fills).toEqual(['50%', '100%', '33%'])
  expect(boxes.filter(b => b.props.backgroundColor !== undefined && b.props.backgroundColor !== 'success')).toEqual([])
  // Never loaded stays A to Z.
  expect(await texts(/^(agent-x|caveman)$/)).toEqual(['agent-x', 'caveman'])
  await ui.unmount()
})

test("a skill's supporting files are found by skill and path; its SKILL.md, folders and globs are not", async () => {
  expect(skillFiles('C:\\Users\\me\\.claude\\skills\\diagnose\\references\\root-cause-tracing.md')).toEqual([{ skill: 'diagnose', file: 'references/root-cause-tracing.md' }])
  // A category folder above the skill, as in a source repo, is not taken for the skill.
  expect(skillFiles('cat skills/agent-workflows/using-goated-ai-skills/references/routing.md')).toEqual([{ skill: 'using-goated-ai-skills', file: 'references/routing.md' }])
  // A file at the skill's top level, as some plugin skills keep their reference.
  expect(skillFiles('/x/plugins/cache/p/skills/plugin-authoring/reference.md')).toEqual([{ skill: 'plugin-authoring', file: 'reference.md' }])
  expect(skillFiles('cd ~/.claude/skills/tdd && cat SKILL.md')).toEqual([])
  expect(skillFiles('cat ~/.claude/skills/tdd/SKILL.md')).toEqual([])
  expect(skillFiles('ls ~/.claude/skills/tdd/references/')).toEqual([])
  expect(skillFiles('grep -l x ~/.claude/skills/tdd/references/*.md')).toEqual([])
})

test('reading a reference is recorded for the main agent and for subagents alike', async () => {
  const read = (path: string) => [{ name: 'Read', input: { file_path: path } }]
  const path = '/h/.claude/skills/diagnose/references/root-cause-tracing.md'
  expect(toolUseEvents(read(path), false, 5)).toEqual([
    { kind: 'read', t: 5, skills: ['diagnose'] },
    { kind: 'ref', t: 5, skill: 'diagnose', file: 'references/root-cause-tracing.md', isReadTool: true },
  ])
  // A shell command printing the file is a read too, but not by the Read tool.
  expect(toolUseEvents([{ name: 'Bash', input: { command: `cat ${path}` } }], false, 5)).toEqual([
    { kind: 'read', t: 5, skills: ['diagnose'] },
    { kind: 'ref', t: 5, skill: 'diagnose', file: 'references/root-cause-tracing.md' },
  ])
  // A subagent's read settles no nudge of the main agent's, but its reference still counts.
  expect(toolUseEvents(read(path), true, 6)).toEqual([{ kind: 'ref', t: 6, skill: 'diagnose', file: 'references/root-cause-tracing.md', isReadTool: true, isSubagent: true }])
})

test('each reference read is counted per skill and file, and the log says whether its skill had loaded', async () => {
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'ref', t: 2, skill: 'tdd', file: 'references/mocking.md' },
    { kind: 'load', t: 3, skill: 'diagnose', via: 'tool', isSubagent: false },
    { kind: 'ref', t: 4, skill: 'diagnose', file: 'references/root-cause-tracing.md' },
    { kind: 'ref', t: 5, skill: 'diagnose', file: 'references/root-cause-tracing.md', isSubagent: true },
  ])
  expect(s.refs).toEqual({ tdd: { 'references/mocking.md': 1 }, diagnose: { 'references/root-cause-tracing.md': 2 } })
  expect(s.timeline.filter(e => e.kind === 'ref')).toEqual([
    { kind: 'ref', t: 2, skill: 'tdd', file: 'references/mocking.md', isLoaded: false },
    { kind: 'ref', t: 4, skill: 'diagnose', file: 'references/root-cause-tracing.md', isLoaded: true },
    { kind: 'ref', t: 5, skill: 'diagnose', file: 'references/root-cause-tracing.md', isLoaded: true, isSubagent: true },
  ])
  const all = addSession(addSession(null, s), s)
  expect(all.refs).toEqual({ tdd: { 'references/mocking.md': 2 }, diagnose: { 'references/root-cause-tracing.md': 4 } })
  expect(mergeSummaries(s, s).refs?.diagnose).toEqual({ 'references/root-cause-tracing.md': 4 })
  // A summary stored before references were counted still adds up.
  const { refs: _, ...old } = s
  expect(addSession(addSession(null, old), s).refs?.tdd).toEqual({ 'references/mocking.md': 1 })
  expect(reportText(all, null)).toContain('- diagnose › references/root-cause-tracing.md: 4')
})

test('the Session tab logs each reference read and lists the references this session', async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: {
      shape: 'events-4',
      value: [
        { kind: 'prompt', t: 1, named: [] },
        { kind: 'load', t: 2, skill: 'diagnose', via: 'tool', isSubagent: false },
        { kind: 'ref', t: 3, skill: 'diagnose', file: 'references/root-cause-tracing.md' },
        { kind: 'ref', t: 4, skill: 'tdd', file: 'references/mocking.md', isSubagent: true },
      ],
    },
  }
  on('clock.now', () => ({ value: 100_000 }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', () => ({ value: { isSet: true, version: 2 } }))
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  const all = (await ui.findAll({ type: 'Text' })).map(t => t.text).join('\n')
  expect(all).toContain('diagnose › references/root-cause-tracing.md · after loading it')
  expect(all).toContain('tdd › references/mocking.md · by a subagent, skill not loaded')
  expect(all).toContain('References this session')
  // A reference row wears the picture's pink for reads; a read without loading notes it in amber.
  const ref = (await ui.findAll({ type: 'Text' })).filter(t => /references\/root-cause-tracing\.md/.test(t.text) && t.props.color !== undefined)
  expect(ref.map(t => t.props.color)).toContain('#e0679b')
  expect((await ui.findAll({ type: 'Text', text: /^Ref$/ })).map(t => t.props.color)).toEqual(['#e0679b', '#e0679b'])
  expect((await ui.find({ type: 'Text', text: /^ · by a subagent, skill not loaded$/ }))?.props.color).toBe('warning')
  await ui.unmount()
})

// ---------- references on the map ---------------------------------------------------

/** Answers the clock and state over `stored` at `now()`; the returned draw mounts the Session or All time pane and hands back the still copy, the frame and the picture's alt text. */
function pictureRig(...[$, on, stored, now]: [...Parameters<TestBody>, Record<string, unknown>, () => number]) {
  on('clock.now', () => ({ value: now() }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', () => ({ value: { isSet: true, version: 2 } }))
  return async () => {
    const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
    const svgs = await ui.findAll({ type: 'Svg' })
    const [still = '', frame = ''] = svgs.map(x => String(x.props.source))
    await ui.unmount()
    return { still, frame, alt: String(svgs[0]?.props.alt) }
  }
}

const refsNode = (src: string) => /<g class="refs-node">.*?<\/g>/.exec(src)?.[0]
/** The page glyph's flight: where its path ends, and the glyph's own markup. */
function pageFlight(src: string): { to: [number, number]; glyph: string } | undefined {
  const m = /<g class="ref-page"[^>]*>(.*?)<\/g>/.exec(src)
  if (!m) return undefined
  const d = /<animateMotion path="([^"]+)"/.exec(m[1] ?? '')?.[1] ?? ''
  const nums = d.match(/-?\d+(\.\d+)?/g)?.map(Number) ?? []
  return { to: [nums[nums.length - 2] ?? NaN, nums[nums.length - 1] ?? NaN], glyph: m[1] ?? '' }
}
const CLAUDE_AT: [number, number] = [80.1, 246]
const SUBAGENTS_AT: [number, number] = [126, 304]
/** Subagents' small node's radius. */
const SUBAGENTS_R = 14
const dist = (a: [number, number], b: [number, number]) => Math.hypot(a[0] - b[0], a[1] - b[1])

test('reads of a skill without loading it are counted, and add up across sessions, old summaries included', async () => {
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'ref', t: 2, skill: 'tdd', file: 'references/mocking.md' },
    { kind: 'load', t: 3, skill: 'diagnose', via: 'tool', isSubagent: false },
    { kind: 'ref', t: 4, skill: 'diagnose', file: 'references/root-cause-tracing.md' },
    { kind: 'ref', t: 5, skill: 'caveman', file: 'references/x.md', isSubagent: true },
  ])
  expect(s.refsUnloaded).toBe(2)
  expect(addSession(addSession(null, s), s).refsUnloaded).toBe(4)
  expect(mergeSummaries(s, s).refsUnloaded).toBe(4)
  // Summaries and totals stored before this was counted still add up.
  const { refsUnloaded: _, ...old } = s
  expect(addSession(addSession(null, old), s).refsUnloaded).toBe(2)
  expect(mergeSummaries(old, s).refsUnloaded).toBe(2)
  const { refsUnloaded: __, ...oldTotal } = addSession(null, s)
  expect(addSession(oldTotal, s).refsUnloaded).toBe(2)
})

test('each reference read is its own moment in the queue, bursts not merged', async () => {
  const timeline: TimelineEntry[] = [
    { t: 1000, kind: 'ref', skill: 'tdd', file: 'references/a.md', isLoaded: true },
    { t: 1001, kind: 'ref', skill: 'tdd', file: 'references/b.md', isLoaded: false, isSubagent: true },
  ]
  expect(playQueue(timeline)).toEqual([
    { start: 2000, kind: 'ref', file: 'references/a.md', isLoaded: true },
    // After the first page's flight and its ripple (2800 ms), then the gap.
    { start: 5250, kind: 'ref', file: 'references/b.md', isLoaded: false, isSubagent: true },
  ])
})

test('the References node shows its read count, lit, with a spoke to the core, and the still copy draws it the same', async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: {
      shape: 'events-4',
      value: [
        { kind: 'prompt', t: 1, named: [] },
        { kind: 'load', t: 2, skill: 'diagnose', via: 'tool', isSubagent: false },
        { kind: 'ref', t: 3, skill: 'diagnose', file: 'references/a.md' },
        { kind: 'ref', t: 4, skill: 'diagnose', file: 'references/b.md' },
        { kind: 'ref', t: 5, skill: 'diagnose', file: 'references/a.md' },
      ],
    },
  }
  let now = 2500
  const draw = pictureRig($, on, stored, () => now)
  const { still, frame } = await draw()
  const node = refsNode(frame)
  expect(node).toBeDefined()
  expect(node).toContain('>References</text>')
  expect(node).toMatch(/>3<\/text>/)
  // Lit: the node's border in the accent colour, and its spoke worn in it too.
  expect(node).toMatch(/r="21" fill="#12151c" stroke="#e1ac6e"/)
  expect(frame).toMatch(/<line class="refs-spoke"[^>]*stroke="#e1ac6e"/)
  // Every read came after loading: no amber badge.
  expect(node).not.toContain('#ffa62b')
  // The copy under the frame draws the very same node, mid-flight or long after.
  expect(refsNode(still)).toBe(node)
  now = 60_000
  const later = await draw()
  expect(refsNode(later.still)).toBe(refsNode(later.frame))
})

test('a quiet References node is unlit and drawn with no count', async ($, on) => {
  const stored: Record<string, unknown> = { tab: 'session', events: { shape: 'events-4', value: [{ kind: 'prompt', t: 1, named: [] }] } }
  const draw = pictureRig($, on, stored, () => 10_000)
  const node = refsNode((await draw()).frame) ?? ''
  expect(node).toMatch(/r="21" fill="#12151c" stroke="#272c36"/)
  expect(node).not.toMatch(/>\d+<\/text>/)
})

test('a reference read flies a pink page from References to Agent, its file name showing as it leaves', async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: {
      shape: 'events-4',
      value: [
        { kind: 'prompt', t: 1, named: [] },
        { kind: 'load', t: 2, skill: 'software-design-principles', via: 'tool', isSubagent: false },
        { kind: 'ref', t: 400, skill: 'software-design-principles', file: 'references/red-flags.md' },
      ],
    },
  }
  const draw = pictureRig($, on, stored, () => 500)
  const { still, frame } = await draw()
  const page = pageFlight(frame)
  expect(page).toBeDefined()
  // It lands on Claude's rim.
  expect(Math.abs(dist(page?.to ?? [0, 0], CLAUDE_AT) - 21)).toBeLessThan(0.2)
  expect(page?.glyph).toContain('#f07aa8')
  // Read after loading: the page is not outlined in amber.
  expect(page?.glyph).not.toContain('#ffa62b')
  // The pink ring just outside the reader's border, from when the page lands.
  expect(frame).toMatch(/<circle class="arrival" cx="80.1" cy="246" r="25" fill="none" stroke="#f07aa8"/)
  // The file's base name beside the node, shown as the page leaves.
  expect(frame).toMatch(/<text class="ref-label"[^>]*>red-flags.md<animate/)
  // The pink is repainted on a light theme like every other colour.
  expect(frame).toContain('[fill="#f07aa8"]{fill:#c2457a}')
  // The still copy plays nothing.
  expect(still).not.toContain('ref-page')
  expect(still).not.toContain('ref-label')
})

test('a subagent read flies to Subagents; a read without loading arrives outlined in amber and counts on a pink badge edged in amber', async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: {
      shape: 'events-4',
      value: [
        { kind: 'prompt', t: 1, named: [] },
        { kind: 'ref', t: 400, skill: 'tdd', file: 'references/a-very-long-reference-file-name.md', isSubagent: true },
      ],
    },
  }
  const draw = pictureRig($, on, stored, () => 500)
  const { still, frame } = await draw()
  const page = pageFlight(frame)
  expect(Math.abs(dist(page?.to ?? [0, 0], SUBAGENTS_AT) - SUBAGENTS_R)).toBeLessThan(0.2)
  expect(page?.glyph).toContain('stroke="#ffa62b"')
  // A long name is cut short, to 22 characters with its ellipsis.
  expect(frame).toMatch(/>a-very-long-reference…<animate/)
  // The badge counts reads without loading, in the frame and the still copy alike: filled in the reads' pink and
  // edged in amber, since a filled amber means a hold still waiting.
  const node = refsNode(frame) ?? ''
  expect(node).toMatch(/fill="#f07aa8" stroke="#ffa62b"[^>]*\/><text[^>]*>1<\/text>/)
  expect(node).not.toMatch(/fill="#ffa62b"/)
  expect(refsNode(still)).toBe(node)
})

test('the All time picture shows node counts and the core ring but no badge, with nothing moving', async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'all',
    events: {
      shape: 'events-4',
      value: [
        { kind: 'prompt', t: 1, named: [] },
        { kind: 'ref', t: 400, skill: 'tdd', file: 'references/a.md' },
        // Still waiting in the live session, which All time adds as it runs.
        { kind: 'nudge', t: 450, hook: 'design', named: ['software-design-principles'], holdKind: 'justified-skip' },
      ],
    },
    allTime: {
      shape: 'all-time-2',
      value: {
        sessions: 1,
        loads: { tdd: { 'self-initiated': 2 } },
        nudges: { commit: { followed: 1, unanswered: 2 } },
        router: {},
        lastUsed: {},
        refs: { tdd: { 'references/a.md': 4 } },
        refsUnloaded: 2,
        subagents: { spawns: 3, starts: 0, bodyReads: 0 },
      },
    },
  }
  const draw = pictureRig($, on, stored, () => 500)
  const { still, frame } = await draw()
  for (const src of [still, frame]) {
    const node = refsNode(src) ?? ''
    // Four stored plus this session's one, as the node's count.
    expect(node).toMatch(/>5<\/text>/)
    expect(src).toMatch(/>2<\/text>/)
    // The core ring: one handled of three settled.
    expect(src).toContain('33% handled')
    // No badge: not followed, waiting, read before loading, or started.
    expect(src).not.toMatch(/fill="#e8654f"\/><text/)
    expect(src).not.toContain('×')
    expect(node).not.toMatch(/<circle[^>]*\/><text[^>]*>3<\/text>/)
    expect(src).not.toContain('spawn-badge')
    expect(src).not.toContain('ref-page')
    expect(src).not.toContain('<animateMotion')
  }
})

test("the Session picture's alt text names each badge it shows, and leaves out a count of none", async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: {
      shape: 'events-4',
      value: [
        { kind: 'prompt', t: 1, named: [] },
        { kind: 'ref', t: 2, skill: 'tdd', file: 'references/a.md' },
        { kind: 'ref', t: 3, skill: 'tdd', file: 'references/b.md' },
        { kind: 'nudge', t: 4, hook: 'design', named: ['software-design-principles'], holdKind: 'justified-skip' },
      ],
    },
  }
  const { alt } = await pictureRig($, on, stored, () => 10_000)()
  expect(alt).toContain('Badges: 1 hold waiting, 2 reference reads before loading.')
  expect(alt).not.toMatch(/not followed|started/)
})

test('badge words name every badge count above zero, singular or plural', async () => {
  expect(badgeWords({ notFollowed: 9, waiting: 1, readsUnloaded: 4, started: 6 })).toBe('9 holds not followed, 1 hold waiting, 4 reference reads before loading, 6 subagents started')
  expect(badgeWords({ notFollowed: 1, waiting: 0, readsUnloaded: 0, started: 1 })).toBe('1 hold not followed, 1 subagent started')
  expect(badgeWords({ notFollowed: 0, waiting: 0, readsUnloaded: 0, started: 0 })).toBe('')
})

test("the References table's subtitle counts reads made before their skill loaded, on both tabs, and says nothing of none", async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: {
      shape: 'events-4',
      value: [
        { kind: 'prompt', t: 1, named: [] },
        { kind: 'ref', t: 2, skill: 'tdd', file: 'references/a.md' },
        { kind: 'ref', t: 3, skill: 'tdd', file: 'references/b.md' },
      ],
    },
    allTime: {
      shape: 'all-time-2',
      value: { sessions: 1, loads: {}, nudges: {}, router: {}, lastUsed: {}, refs: { tdd: { 'references/a.md': 4 } }, refsUnloaded: 3 },
    },
  }
  pictureRig($, on, stored, () => 10_000)
  const subtitle = async () => {
    const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
    const found = (await ui.findAll({ type: 'Text', text: /most read first/ })).map(t => t.text)
    await ui.unmount()
    return found
  }
  expect(await subtitle()).toEqual(["each skill's supporting files read, most read first · 2 read before their skill loaded"])
  stored.tab = 'all'
  // Three stored plus this session's two.
  expect(await subtitle()).toEqual(["each skill's supporting files read, most read first · 5 read before their skill loaded"])
  // Read after loading: the subtitle as it was.
  stored.tab = 'session'
  stored.events = { shape: 'events-4', value: [{ kind: 'prompt', t: 1, named: [] }, { kind: 'load', t: 2, skill: 'tdd', via: 'tool', isSubagent: false }, { kind: 'ref', t: 3, skill: 'tdd', file: 'references/a.md' }] }
  expect(await subtitle()).toEqual(["each skill's supporting files read, most read first"])
})

test('a table heading\'s note wraps onto more lines in a narrow pane instead of being cut short', async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'all',
    events: { shape: 'events-4', value: [{ kind: 'prompt', t: 1, named: [] }, { kind: 'ref', t: 2, skill: 'tdd', file: 'references/a.md' }] },
  }
  pictureRig($, on, stored, () => 10_000)
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  const notes = await ui.findAll({ type: 'Text', text: /^(how often each hold|what most often|each skill's supporting files)/ })
  expect(notes.length).toBe(3)
  for (const note of notes) expect(note.props.wrap).toBe('wrap')
  await ui.unmount()
})

test('the preview plays a reference read and one without loading', async () => {
  const plays = playQueue(previewTimeline(1000))
  expect(plays.flatMap(p => (p.kind === 'ref' ? [p.isLoaded] : []))).toEqual([true, false])
  expect(plays.length).toBe(14)
  expect(Math.max(...plays.map(p => p.start))).toBeLessThan(1000 + PREVIEW_MS)
})

test('a page leaves a dotted pink way that fades once it lands, drawn the same in the still copy, beside a waiting nudge trail', async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: {
      shape: 'events-4',
      value: [
        { kind: 'prompt', t: 1, named: [] },
        { kind: 'nudge', t: 100, hook: 'pull-request', named: ['pr-description'], holdKind: 'strict' },
        { kind: 'ref', t: 200, skill: 'tdd', file: 'references/a.md' },
      ],
    },
  }
  let now = 300
  const draw = pictureRig($, on, stored, () => now)
  const refTrail = (src: string) => /<path class="ref-trail"[^>]*\/?>/.exec(src)?.[0]
  // The read waits its turn behind the nudge (which plays at 1100 for 2800 ms, then the gap): it leaves at 4350.
  const early = await draw()
  expect(refTrail(early.frame)).toContain('stroke="#f07aa8" opacity="0"')
  expect(early.frame).toMatch(/class="ref-trail"[^>]*><animate attributeName="opacity" values="0;.6;.6;0" [^>]*begin="4.050s"/)
  expect(refTrail(early.still)).toBeUndefined()
  // While it lands the frame plays on unchanged, and the copy under it draws the way as it stands, beside the nudge's amber way to Claude.
  now = 6500
  const landing = await draw()
  expect(landing.frame).toBe(early.frame)
  expect(refTrail(landing.still)).toContain('opacity="0.6"')
  expect(landing.still).toContain('stroke="#ffa62b" opacity="0.6"')
  // Long after, it is gone from both; the waiting nudge's way remains.
  now = 60_000
  const after = await draw()
  expect(refTrail(after.frame)).toBeUndefined()
  expect(refTrail(after.still)).toBeUndefined()
  expect(after.frame).toContain('stroke="#ffa62b" opacity="0.6"')
})

test('the tab keeps its columns together beside the picture in a wide pane, and fills a narrow one', async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: { shape: 'events-4', value: [{ kind: 'prompt', t: 1, named: [] }, { kind: 'load', t: 2, skill: 'tdd', via: 'tool', isSubagent: false }] },
  }
  on('clock.now', () => ({ value: 100_000 }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', () => ({ value: { isSet: true, version: 2 } }))
  const widthOf = async (bodyColumns: number) => {
    const ui = await $.ui.mount({ ...PANE, surface: 'desktop', props: { ...PANE.props, bodyColumns } })
    const widths = (await ui.findAll({ type: 'Box' })).map(b => b.props.width).filter(w => typeof w === 'number')
    await ui.unmount()
    return Math.max(...(widths as number[]))
  }
  // A wide pane: the rows stop at about the picture's width, so a time or a rate sits beside its words, not at the far edge.
  expect(await widthOf(200)).toBe(PANE_COLUMNS)
  // A narrow one: the rows take the room there is, inside the pane's padding.
  expect(await widthOf(40)).toBe(38)
})

test('Agent has Subagents as a small node beside it, joined by a line nothing flies along, with its own spoke to the core', async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: { shape: 'events-4', value: [{ kind: 'prompt', t: 1, named: [] }, { kind: 'load', t: 2, skill: 'tdd', via: 'tool', isSubagent: true }] },
  }
  const draw = pictureRig($, on, stored, () => 500)
  const { still, frame } = await draw()
  expect(frame).toContain('>Agent</text>')
  expect(frame).not.toContain('>Claude</text>')
  // The small node, lit by its load, with its count.
  expect(frame).toMatch(/<circle cx="126" cy="304" r="14" fill="#12151c" stroke="#e1ac6e"/)
  expect(frame).toContain('>Subagents</text>')
  // Started by Agent: a thin line between the two rims.
  expect(frame).toMatch(/<line class="started-by" [^>]*\/>/)
  // Its load flies from its own rim straight to the core.
  const load = /<animateMotion path="M([\d.]+) ([\d.]+) L/.exec(frame)
  expect(Math.abs(dist([Number(load?.[1]), Number(load?.[2])], SUBAGENTS_AT) - SUBAGENTS_R)).toBeLessThan(0.2)
  // The References station sits at the bottom of the ring.
  expect(refsNode(still)).toMatch(/<circle cx="210" cy="312" r="21"/)
})

test('the tables chart each count by what it is: a hook by its split of outcomes, a skill or a file by its size beside the largest', async ($, on) => {
  const design = (t: number) => ({ kind: 'nudge', t, hook: 'design', named: ['software-design-principles'], holdKind: 'justified-skip' })
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: {
      shape: 'events-4',
      value: [
        // Four design holds, one turn each: two followed, one declined with a reason, one left unanswered.
        { kind: 'prompt', t: 1, named: [] },
        design(2),
        { kind: 'load', t: 3, skill: 'software-design-principles', via: 'tool', isSubagent: false },
        { kind: 'prompt', t: 4, named: [] },
        design(5),
        { kind: 'load', t: 6, skill: 'software-design-principles', via: 'tool', isSubagent: false },
        { kind: 'prompt', t: 7, named: [] },
        design(8),
        { kind: 'skip', t: 9, skill: 'software-design-principles', reason: 'the edit renames one variable' },
        { kind: 'prompt', t: 10, named: [] },
        design(11),
        { kind: 'prompt', t: 12, named: [] },
        { kind: 'load', t: 13, skill: 'tdd', via: 'tool', isSubagent: false },
        { kind: 'ref', t: 14, skill: 'tdd', file: 'references/mocking.md' },
        { kind: 'ref', t: 15, skill: 'tdd', file: 'references/mocking.md' },
        { kind: 'ref', t: 16, skill: 'tdd', file: 'references/test-design.md' },
      ],
    },
  }
  on('clock.now', () => ({ value: 100_000 }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', () => ({ value: { isSet: true, version: 2 } }))
  for (const surface of ['desktop', 'terminal'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    // No count is drawn as a ring, which would read as progress towards a limit.
    expect((await ui.findAll({ type: 'Svg' })).filter(x => x.props.isInteractive !== true && x.props.width === 16)).toEqual([])
    const fills = (await ui.findAll({ type: 'Box' })).flatMap(b => (b.props.backgroundColor ? [[b.props.backgroundColor, b.props.width]] : []))
    await ui.unmount()
    expect(fills).toEqual([
      // The design hold's four settled holds, split left to right: two followed, one declined, one not.
      ['success', '50%'], [DECLINED_COLOR, '25%'], ['error', '25%'],
      // Skills scale to the most loaded: software-design-principles fills its bar, tdd half of it.
      ['success', '100%'], ['success', '50%'],
      // Files scale to the most read, in the reads' pink.
      [READ_COLOR, '100%'], [READ_COLOR, '50%'],
    ])
  }
})

test('rates count declines with what was acted on, so they say "handled", not "followed"', async ($, on) => {
  const events: UsageEvent[] = [
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'nudge', t: 2, hook: 'design', named: ['software-design-principles'], holdKind: 'justified-skip' },
    { kind: 'skip', t: 3, skill: 'software-design-principles', reason: 'the edit renames one variable' },
  ]
  const stored: Record<string, unknown> = { tab: 'all', events: { shape: 'events-4', value: events } }
  on('clock.now', () => ({ value: 100_000 }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', () => ({ value: { isSet: true, version: 2 } }))
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect((await frameOf(ui))?.source).toContain('100% handled')
  expect(await ui.find({ type: 'Text', text: /how often each hold was handled/ })).toBeDefined()
  await ui.unmount()
  expect(reportText(addSession(null, summarize(events, true)), null)).toContain('- design hold: 1 of 1 handled (100%) · declined 1')
})

test("each adapter gate reads by its own name, not as an earlier hook's tip that shared its key", async () => {
  const gates = ['commit', 'pull-request', 'spawn', 'design', 'security', 'closeout']
  const s = summarize([{ kind: 'prompt', t: 1, named: [] }, ...gates.map((hook, i): UsageEvent => ({ kind: 'nudge', t: 2 + i, hook, named: ['tdd'], holdKind: 'strict' }))], true)
  const report = reportText(addSession(null, s), null)
  for (const name of ['commit hold', 'pull-request hold', 'spawn hold', 'design hold', 'security hold', 'closeout hold']) expect(report).toContain(`- ${name}: `)
  expect(report).not.toContain('tip')
})

test("the conflict-resolution hold counts apart from the earlier hooks' merge-conflict tips", async () => {
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'nudge', t: 2, hook: 'merge-conflict', named: ['resolving-merge-conflicts'] },
    { kind: 'nudge', t: 3, hook: 'conflict-resolution', named: ['resolving-merge-conflicts'], holdKind: 'justified-skip' },
  ], true)
  expect(Object.keys(s.nudges).sort()).toEqual(['conflict-resolution', 'merge-conflict'])
  const report = reportText(addSession(null, s), null)
  expect(report).toContain('- conflict-resolution hold: ')
  expect(report).toContain('- merge conflict: ')
})

test('a load the agent made of its own accord says so, apart from one a subagent made', async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: {
      shape: 'events-4',
      value: [
        { kind: 'prompt', t: 1, named: [] },
        { kind: 'load', t: 2, skill: 'tdd', via: 'tool', isSubagent: false },
        { kind: 'load', t: 3, skill: 'diagnose', via: 'tool', isSubagent: true },
      ],
    },
  }
  on('clock.now', () => ({ value: 100_000 }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', () => ({ value: { isSet: true, version: 2 } }))
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  const all = (await ui.findAll({ type: 'Text' })).map(t => t.text).join('\n')
  await ui.unmount()
  expect(all).toContain('tdd · the agent chose it')
  expect(all).toContain('diagnose · a subagent chose it')
  expect(all).not.toContain('Claude chose it')
})

test('a subagent loading a skill a hook asked for loaded it after a hook, not of its own accord', async ($, on) => {
  const events: UsageEvent[] = [
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'nudge', t: 2, hook: 'design', named: ['software-design-principles'], holdKind: 'justified-skip', isSubagent: true },
    { kind: 'load', t: 3, skill: 'software-design-principles', via: 'tool', isSubagent: true },
    { kind: 'load', t: 4, skill: 'tdd', via: 'tool', isSubagent: true },
  ]
  const s = summarize(events)
  expect(s.loads).toEqual({ 'software-design-principles': { 'hook-nudged': 1 }, tdd: { subagent: 1 } })
  expect(s.nudges).toEqual({ design: { followed: 1 } })
  // The log row keeps that a subagent made it.
  expect(s.timeline.filter(e => e.kind === 'load')).toEqual([
    { t: 3, kind: 'load', skill: 'software-design-principles', origin: 'hook-nudged', isSubagent: true },
    { t: 4, kind: 'load', skill: 'tdd', origin: 'subagent', isSubagent: true },
  ])
  const stored: Record<string, unknown> = { tab: 'session', events: { shape: 'events-4', value: events } }
  on('clock.now', () => ({ value: 100_000 }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  on('state.set', () => ({ value: { isSet: true, version: 2 } }))
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  const all = (await ui.findAll({ type: 'Text' })).map(t => t.text).join('\n')
  await ui.unmount()
  expect(all).toContain('software-design-principles · after a hook, in a subagent')
  expect(all).toContain('tdd · a subagent chose it')
})

/** Every dot's flight in a frame: its path's ends and when it sets off, in seconds from the drawing's start. */
function flights(src: string): { from: [number, number]; to: [number, number]; begin: number; color: string }[] {
  return [...src.matchAll(/<circle r="3.8" fill="(#[0-9a-f]+)" opacity="0"><animateMotion path="([^"]+)" begin="(-?[\d.]+)s"/g)].map(m => {
    const nums = (m[2] ?? '').match(/-?\d+(\.\d+)?/g)?.map(Number) ?? []
    return { color: m[1] ?? '', from: [nums[0] ?? NaN, nums[1] ?? NaN], to: [nums[nums.length - 2] ?? NaN, nums[nums.length - 1] ?? NaN], begin: Number(m[3]) }
  })
}
const CORE_AT: [number, number] = [210, 180]
const HOOKS_AT: [number, number] = [339.9, 246]
const REFS_AT: [number, number] = [210, 312]
const near = (a: [number, number], b: [number, number], r: number) => Math.abs(dist(a, b) - r) < 0.2

test("a skill load is a round trip: its cause's dot reaches SKILLS, and the skill's text flies on to the agent that loaded it, ringing it blue", async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: { shape: 'events-4', value: [{ kind: 'prompt', t: 1, named: [] }, { kind: 'load', t: 400, skill: 'tdd', via: 'tool', isSubagent: false }] },
  }
  let now = 500
  const draw = pictureRig($, on, stored, () => now)
  const { frame } = await draw()
  const [out, back] = flights(frame).filter(f => f.color === '#6cb6ff')
  // Agent chose it: out from Agent's rim to SKILLS, a one-second leg, then back from SKILLS to Agent's rim.
  expect(near(out?.from ?? [0, 0], CLAUDE_AT, 21) && near(out?.to ?? [0, 0], CORE_AT, 48)).toBe(true)
  expect(near(back?.from ?? [0, 0], CORE_AT, 48) && near(back?.to ?? [0, 0], CLAUDE_AT, 21)).toBe(true)
  expect([out?.begin, back?.begin]).toEqual([0.9, 1.9])
  // Agent's outer ring turns blue as the text arrives (1400 + 2000 ms from the load), holds, then fades.
  expect(frame).toMatch(/<circle class="arrival" cx="80.1" cy="246" r="25" fill="none" stroke="#6cb6ff" stroke-width="2" opacity="0"><animate attributeName="opacity" values="1;1;0" [^>]*begin="2.900s"/)
  // The still copy under it draws the ring as it stands: fully lit once arrived, then gone after its fade.
  now = 3500
  expect((await draw()).still).toMatch(/<circle class="arrival" cx="80.1" cy="246" r="25" fill="none" stroke="#6cb6ff" stroke-width="2" opacity="1"\/>/)
  now = 30_000
  expect((await draw()).still).not.toContain('class="arrival"')
})

test('a load a hook asked a subagent for flies from Hooks to SKILLS and on to Subagents', async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: {
      shape: 'events-4',
      value: [
        { kind: 'prompt', t: 1, named: [] },
        { kind: 'nudge', t: 300, hook: 'design', named: ['software-design-principles'], holdKind: 'justified-skip', isSubagent: true },
        { kind: 'load', t: 400, skill: 'software-design-principles', via: 'tool', isSubagent: true },
      ],
    },
  }
  const draw = pictureRig($, on, stored, () => 500)
  const [out, back] = flights((await draw()).frame).filter(f => f.color === '#6cb6ff')
  expect(near(out?.from ?? [0, 0], HOOKS_AT, 21)).toBe(true)
  expect(near(back?.to ?? [0, 0], SUBAGENTS_AT, SUBAGENTS_R)).toBe(true)
})

test("a nudge's result flies back from the agent to Hooks in its colour, and Hooks' outer ring takes it", async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: {
      shape: 'events-4',
      value: [
        { kind: 'prompt', t: 1, named: [] },
        { kind: 'nudge', t: 300, hook: 'commit', named: ['commit-message'], holdKind: 'strict' },
        { kind: 'prompt', t: 400, named: [] },
      ],
    },
  }
  const draw = pictureRig($, on, stored, () => 500)
  const { frame } = await draw()
  // Not followed by the next message: a red dot from Agent's rim back to Hooks' rim, one leg after its sending's slot.
  const reply = flights(frame).find(f => f.color === '#e8654f')
  expect(near(reply?.from ?? [0, 0], CLAUDE_AT, 21) && near(reply?.to ?? [0, 0], HOOKS_AT, 21)).toBe(true)
  expect(frame).toMatch(/<circle class="arrival" cx="339.9" cy="246" r="25" fill="none" stroke="#e8654f"/)
  // The trail turns red behind the dot as it flies.
  expect(frame).toMatch(/stroke="#e8654f" opacity="0"><animate attributeName="opacity" values="0;.7;.7;0"/)
})

test('a reference read is a round trip: a request from the reader to References, then the page back, ringing the reader pink', async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: { shape: 'events-4', value: [{ kind: 'prompt', t: 1, named: [] }, { kind: 'ref', t: 400, skill: 'tdd', file: 'references/a.md', isSubagent: true }] },
  }
  const draw = pictureRig($, on, stored, () => 500)
  const { frame } = await draw()
  const request = flights(frame).find(f => f.color === '#f07aa8')
  expect(near(request?.from ?? [0, 0], SUBAGENTS_AT, SUBAGENTS_R) && near(request?.to ?? [0, 0], REFS_AT, 21)).toBe(true)
  expect(request?.begin).toBe(0.9)
  // The page sets off back when the request lands, its name showing beside References as it leaves.
  expect(frame).toMatch(/<g class="ref-page" opacity="0"><animateMotion path="[^"]+" begin="1.900s"/)
  expect(frame).toMatch(/<text class="ref-label"[^>]*>a.md<animate [^>]*begin="1.900s"/)
  expect(frame).toMatch(/<circle class="arrival" cx="126" cy="304" r="18" fill="none" stroke="#f07aa8"/)
})

test('the status line says in words how the hooks went, leaving out counts of none', async () => {
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'nudge', t: 2, hook: 'router-first', named: ['using-goated-ai-skills'], holdKind: 'strict' },
    { kind: 'load', t: 3, skill: 'using-goated-ai-skills', via: 'tool', isSubagent: false },
    { kind: 'nudge', t: 4, hook: 'design', named: ['software-design-principles'], holdKind: 'justified-skip' },
  ])
  expect(statusText(s)).toBe('skills 1 · hooks: 1 followed · 1 waiting')
  // A summary stored by an earlier version, while a router rule was active, still says how the router went.
  expect(statusText({ ...s, router: 'first' })).toBe('skills 1 · hooks: 1 followed · 1 waiting · router ✓')
  expect(statusText(summarize([{ kind: 'prompt', t: 1, named: [] }, { kind: 'nudge', t: 2, hook: 'pull-request', named: ['pr-description'], holdKind: 'strict' }], true))).toBe(
    'skills 0 · hooks: 0 followed · 1 unanswered',
  )
  // A summary stored before the kinds were told apart says its holds were not answered.
  expect(statusText({ ...s, nudges: { design: { ignored: 2 } } })).toBe('skills 1 · hooks: 0 followed · 2 not answered')
  expect(statusText(summarize([{ kind: 'prompt', t: 1, named: [] }]))).toBe('skills 0')
})

// ---------- declines and turn ends ---------------------------------------------

test('a goated-skip line declines the nudge it names, keeping the reason', async () => {
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'nudge', t: 2, hook: 'closeout', named: ['software-design-principles'] },
    { kind: 'skip', t: 3, skill: 'software-design-principles', reason: 'no code changed this turn' },
    { kind: 'turn-end', t: 4 },
  ])
  expect(s.nudges).toEqual({ closeout: { declined: 1 } })
  const row = s.timeline.find(e => e.kind === 'nudge')
  expect(row?.kind === 'nudge' && row.skills).toEqual([{ skill: 'software-design-principles', status: 'declined', at: 3, reason: 'no code changed this turn' }])
})

test('a nudge still open when its turn ends is ignored then, not left waiting', async () => {
  const s = summarize([
    { kind: 'prompt', t: 2, named: [] },
    { kind: 'nudge', t: 3, hook: 'design', named: ['software-design-principles'], holdKind: 'justified-skip' },
    { kind: 'turn-end', t: 4 },
  ])
  expect(s.nudges).toEqual({ design: { unanswered: 1 } })
  const row = s.timeline.find(e => e.kind === 'nudge' && e.hook === 'design')
  expect(row?.kind === 'nudge' && row.skills).toEqual([{ skill: 'software-design-principles', status: 'unanswered', at: 4 }])
})

test("a subagent's turn end settles only that subagent's nudges, and its skip lines decline only its own", async () => {
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'nudge', t: 2, hook: 'design', named: ['software-design-principles'], isSubagent: true, agent: 'a1' },
    { kind: 'nudge', t: 3, hook: 'security', named: ['code-security-review'], holdKind: 'justified-skip', isSubagent: true, agent: 'a2' },
    { kind: 'nudge', t: 4, hook: 'commit', named: ['commit-message'], holdKind: 'strict' },
    { kind: 'skip', t: 5, skill: 'code-security-review', reason: 'only a scratch probe script', isSubagent: true, agent: 'a2' },
    { kind: 'skip', t: 6, skill: 'commit-message', reason: 'a subagent cannot speak for the agent', isSubagent: true, agent: 'a1' },
    { kind: 'turn-end', t: 7, agent: 'a1' },
  ])
  expect(s.nudges).toEqual({ design: { unanswered: 1 }, security: { declined: 1 }, commit: { pending: 1 } })
})

test('a skip line written earlier in the same turn declines a later nudge; one from an earlier turn does not', async () => {
  const sameTurn = summarize([
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'skip', t: 2, skill: 'software-design-principles', reason: 'docs only, no code here' },
    { kind: 'nudge', t: 3, hook: 'closeout', named: ['software-design-principles'] },
    { kind: 'turn-end', t: 4 },
  ])
  expect(sameTurn.nudges).toEqual({ closeout: { declined: 1 } })
  const laterTurn = summarize([
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'skip', t: 2, skill: 'software-design-principles', reason: 'docs only, no code here' },
    { kind: 'turn-end', t: 3 },
    { kind: 'prompt', t: 4, named: [] },
    { kind: 'nudge', t: 5, hook: 'closeout', named: ['software-design-principles'] },
    { kind: 'turn-end', t: 6 },
  ])
  expect(laterTurn.nudges).toEqual({ closeout: { unanswered: 1 } })
})

test('skip lines count only as whole lines outside code, in the grammar, with a reason of three words or more', async () => {
  const reply = [
    'Prose that mentions goated-skip: tdd: inline does not count.',
    '`goated-skip: tdd: no behaviour changes here`',
    '```',
    'goated-skip: commit-message: shown inside a fence',
    '```',
    'goated-skip: Bad-Name: uppercase is not a skill',
    'goated-skip: doc-sync: too short',
    '  goated-skip: code-security-review: no trust boundary touched  ',
  ].join('\n')
  expect(markerEvents(reply, 9)).toEqual([
    { kind: 'skip', t: 9, skill: 'tdd', reason: 'no behaviour changes here' },
    { kind: 'skip', t: 9, skill: 'code-security-review', reason: 'no trust boundary touched' },
  ])
  expect(markerEvents('goated-skip: tdd: no behaviour changes here', 9, 'a1')).toEqual([
    { kind: 'skip', t: 9, skill: 'tdd', reason: 'no behaviour changes here', isSubagent: true, agent: 'a1' },
  ])
})

test("route and skip lines count from a Skill call's args and any call's description, before the call", async () => {
  const route = 'goated-route: standard | requires: tdd'
  expect(toolUseEvents([{ id: 'u1', name: 'Skill', input: { skill: 'tdd', args: route } }], false, 4)).toEqual([
    { kind: 'route', t: 4, form: 'route', intensity: 'standard', requires: ['tdd'] },
    { kind: 'load', t: 4, id: 'u1', skill: 'tdd', via: 'tool', isSubagent: false },
  ])
  const skip = 'Check status\ngoated-skip: software-design-principles: this is a mechanical rename only'
  expect(toolUseEvents([{ name: 'Bash', input: { command: 'git status', description: skip } }], false, 5)).toEqual([
    { kind: 'skip', t: 5, skill: 'software-design-principles', reason: 'this is a mechanical rename only' },
  ])
  for (const name of ['PowerShell', 'Agent', 'Task']) {
    expect(toolUseEvents([{ name, input: { description: 'goated-route: direct' } }], false, 5).filter(e => e.kind === 'route')).toEqual([{ kind: 'route', t: 5, form: 'direct' }])
  }
  // A subagent's call lines are its own, as its reply lines are.
  expect(toolUseEvents([{ name: 'Bash', input: { command: 'ls', description: 'goated-route: direct' } }], true, 6, 'a1')).toEqual([
    { kind: 'route', t: 6, form: 'direct', isSubagent: true, agent: 'a1' },
  ])
})

test('no other field of a call carries a route, skip or design-reads line', async () => {
  const line = 'goated-route: direct'
  const uses = [
    { name: 'Edit', input: { file_path: 'notes.md', old_string: 'x', new_string: line } },
    { name: 'Write', input: { file_path: 'notes.md', content: line } },
    { name: 'Bash', input: { command: `cat > notes.md <<'EOF'\n${line}\nEOF`, args: line } },
    { name: 'Bash', input: { command: 'ls', description: '```\n' + line + '\n```' } },
    { name: 'Write', input: { file_path: 'notes.md', content: 'goated-design-reads: process.md' } },
    // A tool whose description is its payload, such as an issue or merge-request body, carries no line.
    { name: 'mcp__gitlab__create_merge_request', input: { title: 'x', description: line } },
    { name: 'mcp__linear__create_issue', input: { title: 'x', description: line } },
    { name: 'TaskCreate', input: { subject: 'x', description: line } },
    { name: 'Skill', input: { skill: 'tdd', description: line } },
  ]
  expect(toolUseEvents(uses, false, 7).filter(e => e.kind === 'route' || e.kind === 'skip' || e.kind === 'design-reads')).toEqual([])
})

test('a design-reads line counts from the same call fields as a route line', async () => {
  const uses = [{ name: 'Bash', input: { command: 'ls', description: 'goated-design-reads: process.md' } }]
  expect(toolUseEvents(uses, false, 8).filter(e => e.kind === 'design-reads')).toMatchObject([
    { kind: 'design-reads', t: 8, files: ['process.md'], noneReasons: [] },
  ])
})

test('history reads a route line from a call when the reply text was saved as a summary', async () => {
  const history: HistoryMessage[] = [
    { role: 'user', content: [{ type: 'text', text: 'rename the loader' }] },
    { role: 'assistant', content: [
      { type: 'thinking', thinking: 'I will route this as direct work.' },
      { type: 'tool_use', id: 'u1', name: 'Skill', input: { skill: 'using-goated-ai-skills', args: 'goated-route: direct' } },
    ] },
  ]
  expect(historyEvents(history, SKILLS, 50)).toContainEqual({ kind: 'route', t: 50, form: 'direct', isEarlier: true })
})

test('history rebuilds skip lines from replies, so a late-loading mod sees declines', async () => {
  const history: HistoryMessage[] = [
    { role: 'user', content: [{ type: 'text', text: 'tidy the docs' }] },
    { role: 'assistant', content: [{ type: 'text', text: 'Done.\ngoated-skip: software-design-principles: docs only, no code' }] },
  ]
  expect(historyEvents(history, SKILLS, 50)).toContainEqual({ kind: 'skip', t: 50, skill: 'software-design-principles', reason: 'docs only, no code', isEarlier: true })
})

test('a decline counts as handled in the rates, and the status line names declines apart', async () => {
  expect(followCounts({ followed: 1, declined: 1, unanswered: 1 })).toEqual({ acted: 2, settled: 3, pending: 0, declined: 1 })
  const s = summarize([
    { kind: 'prompt', t: 1, named: [] },
    { kind: 'nudge', t: 2, hook: 'security', named: ['code-security-review'], holdKind: 'justified-skip' },
    { kind: 'skip', t: 3, skill: 'code-security-review', reason: 'only a scratch probe script' },
    { kind: 'turn-end', t: 4 },
  ])
  expect(statusText(s)).toBe('skills 0 · hooks: 0 followed · 1 declined')
  const report = reportText(addSession(null, s), { names: SKILLS, own: [], total: 6, included: 6 })
  expect(report).toContain('- security hold: 1 of 1 handled (100%) · declined 1')
})

test('a declined row reads in pale green and reveals its reason on hover', async ($, on) => {
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: {
      shape: 'events-4',
      value: [
        { kind: 'prompt', t: 1, named: [] },
        { kind: 'nudge', t: 2, hook: 'closeout', named: ['software-design-principles'] },
        { kind: 'skip', t: 3, skill: 'software-design-principles', reason: 'this turn changed no files' },
        { kind: 'turn-end', t: 4 },
      ],
    },
  }
  on('clock.now', () => ({ value: 60_000 }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    expect((await ui.find({ type: 'Text', text: /→/ }))?.text).toBe('closeout hold → software-design-principles declined')
    // The row's tone is the decline's, so its sentence takes the pale green; the hook's name inside stays plain.
    expect((await ui.find({ type: 'Text', text: /→/ }))?.props.color).toBe(DECLINED_COLOR)
    expect((await ui.find({ type: 'Text', text: /hooks:/ }))?.text).toBe('0 skill loads · hooks: 0 followed · 1 declined')
    expect(await ui.find({ type: 'Text', text: /^↷$/ })).toBeDefined()
    // A pointer surface keeps the reason hidden until the row is hovered (the kit does not report the hover prop
    // itself); the terminal has no pointer, so it shows the reason on its own line under the row.
    const hidden = (await ui.findAll({ type: 'Box' })).filter(b => b.props.display === 'none')
    expect(hidden.length).toBe(surface === 'terminal' ? 0 : 1)
    expect((await ui.find({ type: 'Text', text: /this turn changed no files/ }))?.text).toBe('reason: this turn changed no files')
    await ui.unmount()
  }
})

test('a hold that held again reads once with how many times, and one that asks for a fix says so instead of naming no skill', async ($, on) => {
  const hold = (t: number, hook: string, named: string[]) => ({ kind: 'nudge', t, hook, named, holdKind: 'strict' })
  const stored: Record<string, unknown> = {
    tab: 'session',
    events: {
      shape: 'events-4',
      value: [
        { kind: 'prompt', t: 1, named: [] },
        hold(2, 'route-line', ['(route line)']),
        hold(3, 'route-line', ['(route line)']),
        hold(4, 'route-line', ['(route line)']),
        { kind: 'route', t: 5, form: 'direct' },
        hold(6, 'commit', []),
        hold(7, 'spawn', []),
        hold(8, 'pull-request', []),
        // The pr-review hold that asks, once its skill loaded, for a read of the change.
        { kind: 'nudge', t: 9, hook: 'pr-review', named: [], holdKind: 'justified-skip' },
      ],
    },
  }
  on('clock.now', () => ({ value: 60_000 }))
  on('state.get', (_, e) => {
    const key = (e as { key: string }).key
    return { value: key in stored ? { value: stored[key], version: 1 } : { value: undefined, version: 0 } }
  })
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  // Each row's whole sentence; its hook's name is a run of its own inside it.
  const rows = (await ui.findAll({ type: 'Text', text: /→ ./ })).map(t => t.text)
  await ui.unmount()
  expect(rows).toEqual([
    'pr-review hold → asked to read the change',
    'pull-request hold → asked to read the change',
    'spawn hold → asked for the brief template or its headings',
    'commit hold → asked to read the change or fix the commit message',
    'route-line hold ×3 → a route line loaded',
  ])
})
