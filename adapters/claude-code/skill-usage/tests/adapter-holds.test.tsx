// Every hold the GOATED Claude Code adapter emits, as the mod records it: its
// gate and kind, what it asks for, and what became of it (followed, declined
// with a reason, or ignored). The hold texts are the adapter's own, generated
// into adapter-texts.ts. Pre-tool holds arrive as errored tool results and the
// closeout hold as a blocked `Stop`; the shapes of both come from real runs
// (Claude Code 2.1.325).

import { expect, test } from 'claude-code/testing'

import type { UsageEvent } from '../types'
import { hookEvents, isObservedRow, markerEvents, rowEvents, summarize } from '../hooks/classify'
import type { HistoryMessage, Row } from '../hooks/classify'
import { historyEvents } from '../hooks/classify'
import { ADAPTER_TEXTS } from './adapter-texts'

const SKILLS = ['using-goated-ai-skills', 'tdd', 'doc-sync', 'commit-message', 'pr-description', 'handoff', 'subagent-driven-development', 'software-design-principles', 'code-security-review']

const denied = (tool: string, text: string) => `PreToolUse:${tool} hook error: ${text}`
// A blocked Stop reaches a mod, live and in history, wrapped in Claude Code's own sentence.
const STOP_COMMAND = 'python /tools/goated-adapter/goated_hook.py'
const blockedStop = (reason: string) => `<system-reminder>\nStop hook blocking error from command: "${STOP_COMMAND}": ${reason}\n</system-reminder>`

const prompt = (t = 1): UsageEvent => ({ kind: 'prompt', t, named: [] })
const load = (skill: string, t: number): UsageEvent => ({ kind: 'load', t, skill, via: 'tool', isSubagent: false })
const preHold = (tool: string, text: string, t: number) => hookEvents(denied(tool, text), SKILLS, t, { holdsOnly: true })
const stopHold = (t: number) => hookEvents(blockedStop(ADAPTER_TEXTS.closeout), SKILLS, t, { holdsOnly: false })
const turnEnd = (t: number): UsageEvent => ({ kind: 'turn-end', t })

const row = (door: string, content: Row['message']['content'], more: Partial<Row['message']> = {}): Row => ({ door, message: { content, ...more } })

// ---------- what each hold is and asks for ------------------------------------------

test('each action hold reads as its gate and kind and names the skills it asks for', async () => {
  const cases: [string, string, string, string, string[]][] = [
    ['commit', 'Bash', ADAPTER_TEXTS.commit, 'strict', ['commit-message']],
    ['pull-request', 'Bash', ADAPTER_TEXTS.pullRequest, 'strict', ['pr-description']],
    ['spawn', 'Agent', ADAPTER_TEXTS.spawn, 'strict', ['handoff', 'subagent-driven-development']],
    ['design', 'Write', ADAPTER_TEXTS.design, 'justified-skip', ['software-design-principles']],
    ['security', 'Write', ADAPTER_TEXTS.security, 'justified-skip', ['code-security-review']],
    // A shell write is held like a write tool's.
    ['security', 'Bash', ADAPTER_TEXTS.shellWrite, 'justified-skip', ['code-security-review']],
  ]
  for (const [gate, tool, text, kind, named] of cases) {
    expect(preHold(tool, text, 1)).toEqual([expect.objectContaining({ kind: 'nudge', hook: gate, holdKind: kind, named })])
  }
})

test('the spawn hold that asks for a template read names no skill, so it is recorded by its gate and kind alone', async () => {
  // It asks for a Read of a file, which no skill load or skip line answers; the pane counts it as a hold without a per-skill result.
  expect(preHold('Agent', ADAPTER_TEXTS.spawnRead, 1)).toEqual([{ kind: 'nudge', t: 1, hook: 'spawn', named: [], holdKind: 'strict' }])
  const s = summarize([prompt(), ...preHold('Agent', ADAPTER_TEXTS.spawnRead, 2), turnEnd(3)])
  expect(s.holds).toEqual({ strict: 1 })
  expect(s.nudges).toEqual({})
  const row = s.timeline.find(e => e.kind === 'nudge')
  expect(row?.kind === 'nudge' && row.skills).toEqual([])
})

// ---------- the closeout hold, a blocked Stop ---------------------------------------

test('the closeout hold reads from the blocked Stop that carries it, live and in history', async () => {
  // The proof item asks for a check to run, which is no skill, so the hold names the skills its other items ask for.
  const want = [{ kind: 'nudge', t: 1, hook: 'closeout', named: ['doc-sync'], holdKind: 'justified-skip' }]
  expect(rowEvents(row('hook-context', [{ type: 'text', text: blockedStop(ADAPTER_TEXTS.closeout) }], { name: 'hook_blocking_error' }), SKILLS, 1, { hasTool: true })).toEqual(want)
  const history: HistoryMessage[] = [
    { role: 'user', content: [{ type: 'text', text: 'Fix the exporter.' }] },
    { role: 'user', content: [{ type: 'text', text: blockedStop(ADAPTER_TEXTS.closeout) }] },
  ]
  expect(historyEvents(history, SKILLS, 1).filter(e => e.kind === 'nudge')).toEqual(want.map(e => ({ ...e, isEarlier: true })))
  // The same reason as the plain feedback line Claude Code also writes reads the same way.
  expect(hookEvents(`Stop hook feedback:\n${ADAPTER_TEXTS.closeout}`, SKILLS, 1)).toEqual(want)
})

test('the closeout hold is read once: the plain feedback note row is not observed, so it is not counted again', async () => {
  const note = row('note', [{ type: 'text', text: `Stop hook feedback:\n${ADAPTER_TEXTS.closeout}` }], { type: 'user', isMeta: true })
  expect(isObservedRow(note)).toBe(false)
})

test('a goated-hold line that is not a hold, an errored result aside, is not one: a stop wrapper only carries a hold as its reason', async () => {
  // Some other hook's context that quotes a hold, and a Stop block with another reason.
  expect(hookEvents(`SessionStart hook additional context: see the log:\n${ADAPTER_TEXTS.closeout}`, SKILLS, 1)).toEqual([])
  expect(hookEvents(blockedStop('Tests are failing; fix them first.'), SKILLS, 1)).toEqual([])
})

// ---------- strict holds: only loading clears them ----------------------------------

for (const [gate, tool, text, skill] of [
  ['commit', 'Bash', ADAPTER_TEXTS.commit, 'commit-message'],
  ['pull-request', 'Bash', ADAPTER_TEXTS.pullRequest, 'pr-description'],
] as const) {
  test(`the ${gate} hold is followed by loading ${skill}`, async () => {
    const s = summarize([prompt(), ...preHold(tool, text, 2), load(skill, 3), turnEnd(4)])
    expect(s.nudges).toEqual({ [gate]: { followed: 1 } })
    expect(s.holds).toEqual({ strict: 1 })
  })

  test(`the ${gate} hold is ignored when the turn ends without ${skill}, and a skip line never declines it`, async () => {
    const s = summarize([prompt(), ...preHold(tool, text, 2), ...markerEvents(`goated-skip: ${skill}: the message was typed by the user`, 3), turnEnd(4)])
    expect(s.nudges).toEqual({ [gate]: { ignored: 1 } })
    // Even a skip line written before the hold does not decline a strict one.
    const early = summarize([prompt(), ...markerEvents(`goated-skip: ${skill}: the message was typed by the user`, 2), ...preHold(tool, text, 3), turnEnd(4)])
    expect(early.nudges).toEqual({ [gate]: { ignored: 1 } })
  })
}

test('the spawn hold names two ways to brief; loading either follows it, and the other is not counted against it', async () => {
  const sdd = summarize([prompt(), ...preHold('Agent', ADAPTER_TEXTS.spawn, 2), load('subagent-driven-development', 3), turnEnd(4)])
  expect(sdd.nudges).toEqual({ spawn: { followed: 1 } })
  const row = sdd.timeline.find(e => e.kind === 'nudge')
  expect(row?.kind === 'nudge' && row.skills).toEqual([{ skill: 'subagent-driven-development', status: 'followed', at: 3 }])
  const handoff = summarize([prompt(), ...preHold('Agent', ADAPTER_TEXTS.spawn, 2), load('handoff', 3), turnEnd(4)])
  expect(handoff.nudges).toEqual({ spawn: { followed: 1 } })
  const neither = summarize([prompt(), ...preHold('Agent', ADAPTER_TEXTS.spawn, 2), turnEnd(3)])
  expect(neither.nudges).toEqual({ spawn: { ignored: 2 } })
})

test('a route-line hold repeated after the route line was written in the same message counts as followed', async () => {
  // Claude Code records a call only after its hold returns, so the line written beside the call is seen first.
  const s = summarize([
    prompt(),
    ...hookEvents(denied('Edit', ADAPTER_TEXTS.routeLine), SKILLS, 2, { holdsOnly: true }),
    ...markerEvents('goated-route: direct', 3),
    ...hookEvents(denied('Edit', ADAPTER_TEXTS.routeLine), SKILLS, 4, { holdsOnly: true }),
    turnEnd(5),
  ])
  expect(s.nudges).toEqual({ 'route-line': { followed: 2 } })
  // A route line from an earlier prompt does not.
  const later = summarize([prompt(), ...markerEvents('goated-route: direct', 2), prompt(3), ...hookEvents(denied('Edit', ADAPTER_TEXTS.routeLine), SKILLS, 4, { holdsOnly: true }), turnEnd(5)])
  expect(later.nudges).toEqual({ 'route-line': { ignored: 1 } })
})

// ---------- justified-skip holds: followed, declined with a reason, or ignored -------

for (const [gate, tool, text, skill] of [
  ['design', 'Write', ADAPTER_TEXTS.design, 'software-design-principles'],
  ['security', 'Write', ADAPTER_TEXTS.security, 'code-security-review'],
  ['security', 'Bash', ADAPTER_TEXTS.shellWrite, 'code-security-review'],
] as const) {
  const reason = 'the edit changes one constant and nothing else'
  test(`the ${gate} hold on ${tool} is followed by loading ${skill}, declined by a skip line with its reason, and otherwise ignored`, async () => {
    const followed = summarize([prompt(), ...preHold(tool, text, 2), load(skill, 3), turnEnd(4)])
    expect(followed.nudges).toEqual({ [gate]: { followed: 1 } })

    const declined = summarize([prompt(), ...preHold(tool, text, 2), ...markerEvents(`goated-skip: ${skill}: ${reason}`, 3), turnEnd(4)])
    expect(declined.nudges).toEqual({ [gate]: { declined: 1 } })
    const row = declined.timeline.find(e => e.kind === 'nudge')
    expect(row?.kind === 'nudge' && row.holdKind).toBe('justified-skip')
    expect(row?.kind === 'nudge' && row.skills).toEqual([{ skill, status: 'declined', at: 3, reason }])

    const ignored = summarize([prompt(), ...preHold(tool, text, 2), turnEnd(3)])
    expect(ignored.nudges).toEqual({ [gate]: { ignored: 1 } })
    expect(ignored.holds).toEqual({ 'justified-skip': 1 })
  })
}

test('the closeout hold is followed by loading the skill it names, declined by a skip line with its reason, and otherwise ignored', async () => {
  const followed = summarize([prompt(), ...stopHold(2), load('doc-sync', 3), turnEnd(4)])
  expect(followed.nudges).toEqual({ closeout: { followed: 1 } })
  const reason = 'the change touches behavior no doc describes'
  const declined = summarize([prompt(), ...stopHold(2), ...markerEvents(`goated-skip: doc-sync: ${reason}`, 3), turnEnd(4)])
  expect(declined.nudges).toEqual({ closeout: { declined: 1 } })
  const row = declined.timeline.find(e => e.kind === 'nudge' && e.hook === 'closeout')
  expect(row?.kind === 'nudge' && row.skills).toEqual([{ skill: 'doc-sync', status: 'declined', at: 3, reason }])
  const ignored = summarize([prompt(), ...stopHold(2), turnEnd(3)])
  expect(ignored.nudges).toEqual({ closeout: { ignored: 1 } })
  expect(ignored.holds).toEqual({ 'justified-skip': 1 })
})

test("a blocked Stop does not end the turn: the closeout hold waits for the agent's next move, then the turn's end settles it", async () => {
  // The agent answers the first block and is held again; each hold is its own row.
  const s = summarize([prompt(), ...stopHold(2), load('doc-sync', 3), ...stopHold(4), turnEnd(5)])
  expect(s.nudges.closeout).toEqual({ followed: 1, 'already loaded': 1 })
  expect(s.holds).toEqual({ 'justified-skip': 2 })
})
