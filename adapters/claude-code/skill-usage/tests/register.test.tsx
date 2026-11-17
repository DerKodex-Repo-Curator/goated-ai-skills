// The mod's store as a session runs: what it reads from and writes to `$.store`
// at session start and at each turn end. The tests stand for Claude Code
// beneath the mod, answering each engine call from memory and logging what the
// store was asked, in order.

import { expect, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'

import { summarize } from '../hooks/classify'

type On = Parameters<TestBody>[1]
type Stored = { t: number; summary: ReturnType<typeof summarize> }

const session = (t: number, skill: string): Stored => {
  const { timeline: _, ...summary } = summarize([{ kind: 'prompt', t, named: [] }, { kind: 'load', t, skill, via: 'tool', isSubagent: false }])
  return { t, summary }
}

/** Answers the calls the mod makes outside its own state; `store` is the plugin store, `log` its writes in order. */
function world(on: On, store: Map<string, unknown>, log: string[]) {
  // The events' own results, as the engine would give them beneath the mod.
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('turn.complete', () => ({ text: '' }))
  on('clock.now', () => ({ value: 1_000_000 }))
  on('session.id', () => ({ value: 'running' }))
  on('session.usage', () => ({ value: { context: { breakdown: { skills: { skillFrontmatter: [], totalSkills: 0, includedSkills: 0 } } } } }))
  on('session.messages', () => ({ value: [] }))
  on('session.repo', () => ({ value: null }))
  on('session.root', () => ({ value: '/project' }))
  on('command.register', () => ({ value: { isRegistered: true } }))
  on('ui.open', () => ({ value: { isPlaced: false } }))
  on('ui.status', () => ({ value: undefined }))
  on('store.keys', () => ({ value: [...store.keys()] }))
  on('store.get', (_, e) => ({ value: store.get((e as { key: string }).key) }))
  on('store.set', (_, e) => {
    const { key, value } = e as { key: string; value: unknown }
    log.push(`set ${key}`)
    store.set(key, value)
    return { value: undefined }
  })
  on('store.delete', (_, e) => {
    const { key } = e as { key: string }
    log.push(`delete ${key}`)
    store.delete(key)
    return { value: undefined }
  })
}

const report = async ($: Parameters<TestBody>[0]) => String((await $.command.run({ command: 'skill-usage', args: 'report' }))?.text ?? '')
const turnDone = { answer: '', durationMs: 1, isAborted: false, turnId: 'turn-1', reason: 'answer' } as const

test('each finished turn rereads the other sessions, so All time counts one that stored a turn since this one started', async ($, on) => {
  const store = new Map<string, unknown>()
  world(on, store, [])
  await $.session.start({ cwd: '/project', surface: null, isInteractive: false })
  expect(await report($)).toContain('# Skill usage: 1 session')
  // Another session, running beside this one, stores its first turn.
  store.set('s:beside', session(10, 'tdd'))
  await $.turn.complete(turnDone)
  const text = await report($)
  expect(text).toContain('# Skill usage: 2 sessions')
  expect(text).toContain('- tdd: 1')
})

test('past the cap the oldest session folds into the older total, which is stored before the session is removed', async ($, on) => {
  const store = new Map<string, unknown>()
  // 301 other sessions: one more than the store keeps one by one.
  for (let i = 0; i < 301; i++) store.set(`s:old-${i}`, session(100 + i, i === 0 ? 'diagnose' : 'tdd'))
  const log: string[] = []
  world(on, store, log)
  await $.session.start({ cwd: '/project', surface: null, isInteractive: false })
  // Stored first, then removed: a failure between the two can count the session twice, never lose it.
  expect(log.filter(l => l.includes('older') || l.includes('old-0'))).toEqual(['set older', 'delete s:old-0'])
  const text = await report($)
  expect(text).toContain('# Skill usage: 302 sessions')
  expect(text).toContain('- diagnose: 1')
})
