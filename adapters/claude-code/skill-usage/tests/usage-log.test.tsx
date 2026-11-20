// The GOATED core's usage log, read by the mod (Ticket 082 in the GOATED repo). One recorded Claude Code session,
// generated into usage-log-session.ts by driving the adapter with the log on, is counted twice: from the rows Claude
// Code hands the mod, and from the log. The counts the log carries must match.

import { expect, test } from 'claude-code/testing'

import type { UsageEvent } from '../types'
import { addSession, rowEvents, summarize } from '../hooks/classify'
import { storedReason } from '../hooks/holds'
import type { Row } from '../hooks/classify'
import { loggedTotal, readUsageLog, usageLogPlace } from '../hooks/usage-log'
import { USAGE_LOG_SESSION } from './usage-log-session'

const SKILLS = ['using-goated-ai-skills', 'tdd', 'doc-sync', 'verification-before-completion', 'software-design-principles']

/** The events the mod makes of the session as it hears it: each row in turn, and each turn end. */
function heardEvents(): UsageEvent[] {
  const events: UsageEvent[] = []
  let lastBoundary: 'response' | 'results' | undefined
  for (const [n, step] of USAGE_LOG_SESSION.steps.entries()) {
    const t = (n + 1) * 1000
    if ('turnEnd' in step) {
      events.push({ kind: 'turn-end', t, reason: 'answer' })
      continue
    }
    const made = rowEvents(step.row as unknown as Row, SKILLS, t, { lastKind: events.at(-1)?.kind, lastBoundary })
    for (const e of made) if (e.kind === 'response' || e.kind === 'results') lastBoundary = e.kind
    events.push(...made)
  }
  return events
}

/** The counts the log carries: everything but writing turns, side sessions and subagent spawns, which it does not hold. */
function loggedCounts(events: readonly UsageEvent[]) {
  const { loads, nudges, holds, closeoutItems, skipReasons, refAsks, refs, refsUnloaded, refMoments, routes, routeSkills, overrides } = summarize(events, true)
  return { loads, nudges, holds, closeoutItems, skipReasons, refAsks, refs, refsUnloaded, refMoments, routes, routeSkills, overrides }
}

test('the mod counts a recorded session the same from the log as from what it heard', async () => {
  const read = readUsageLog(USAGE_LOG_SESSION.logText)
  if (!('sessions' in read)) throw new Error(read.refused)
  expect(read.sessions.map(s => [s.adapter, s.session])).toEqual([['claude-code', 'recorded-session']])
  const fromLog = loggedCounts(read.sessions[0]?.events ?? [])
  expect(fromLog).toEqual(loggedCounts(heardEvents()))
  // The session is worth comparing: it held, loaded for each cause, skipped, read a reference and overrode.
  expect(fromLog.holds).toEqual({ strict: 3, 'justified-skip': 1 })
  expect(fromLog.loads).toEqual({ 'using-goated-ai-skills': { 'hook-nudged': 1 }, tdd: { 'user-named': 1 }, 'doc-sync': { 'hook-nudged': 1 } })
  expect(Object.keys(fromLog.skipReasons ?? {}).sort()).toEqual(['doc-sync', 'verification-before-completion'])
  expect(fromLog.refs).toEqual({ tdd: { 'references/test-design.md': 1 } })
  expect(fromLog.overrides).toEqual({ 'skip routing': 1 })
  expect(fromLog.routes).toEqual({ route: 1, direct: 1 })
})

test('a log with an entry of an unknown version is refused, naming the line and the version', async () => {
  const later = `${USAGE_LOG_SESSION.logText}${JSON.stringify({ log: 3, t: 99, adapter: 'pi', session: 's', project: null, type: 'prompt' })}\n`
  expect(readUsageLog(later)).toEqual({ refused: `line ${USAGE_LOG_SESSION.log.length + 1} of the usage log is of log version 3, which the mod does not know (it knows versions 1 and 2)` })
})

test('lines that are no entry are skipped and counted, and the rest still counts', async () => {
  const common = { log: 1, t: 1, adapter: 'pi-agent', session: 's', project: null }
  const bad = ['not json', '{"log": 1, "t": 9', '[1, 2]', JSON.stringify({ ...common, type: 'load', cause: 'agent' }), JSON.stringify({ ...common, type: 'nonsense' })]
  const read = readUsageLog(`${bad.join('\n')}\n${USAGE_LOG_SESSION.logText}`)
  if (!('sessions' in read)) throw new Error(read.refused)
  expect(read.skipped).toBe(5)
  expect(loggedCounts(read.sessions[0]?.events ?? [])).toEqual(loggedCounts(heardEvents()))
  // Near miss: a whole log reads with none skipped.
  const whole = readUsageLog(USAGE_LOG_SESSION.logText)
  expect('skipped' in whole && whole.skipped).toBe(0)
})

test('the mod masks paths in skip reasons as the core does', async () => {
  for (const [reason, kept] of USAGE_LOG_SESSION.reasonCases) expect(storedReason(reason)).toBe(kept)
})

test("other adapters' sessions add to All time under their project, the mod's own adapter's do not", async () => {
  const other = USAGE_LOG_SESSION.logText.replaceAll('"adapter": "claude-code"', '"adapter": "pi-agent"')
  const read = readUsageLog(`${USAGE_LOG_SESSION.logText}${other}`)
  if (!('sessions' in read)) throw new Error(read.refused)
  expect(read.sessions.map(s => s.adapter)).toEqual(['claude-code', 'pi-agent'])
  const total = loggedTotal(read.sessions)
  const expected = addSession(null, { ...summarize(read.sessions[1]?.events ?? [], true), project: '0123456789' })
  expect(total?.sessions).toBe(1)
  expect(total?.loads).toEqual(expected.loads)
  expect(Object.keys(total?.byProject ?? {})).toEqual(['0123456789'])
  // Near miss: a log of the mod's own sessions alone adds nothing.
  const own = readUsageLog(USAGE_LOG_SESSION.logText)
  expect('sessions' in own && loggedTotal(own.sessions)).toBe(null)
})

test("the log is looked for where the option says, else where the core puts it by default", async () => {
  const windows = { configured: '', isWindows: true }
  const posix = { configured: '', isWindows: false }
  expect(usageLogPlace({ ...windows, configured: ' /logs/usage.jsonl ', localAppData: 'D:\\AppData\\Local' })).toBe('/logs/usage.jsonl')
  expect(usageLogPlace({ ...windows, localAppData: 'D:\\AppData\\Local', xdgStateHome: '/state' })).toBe('D:\\AppData\\Local\\goated\\usage-log.jsonl')
  // Without LOCALAPPDATA, the core falls back to the per-user temp folder, and so does the mod.
  expect(usageLogPlace({ ...windows, temp: 'D:\\Temp', xdgStateHome: '/state' })).toBe('D:\\Temp\\goated\\usage-log.jsonl')
  expect(usageLogPlace({ ...windows, home: 'D:\\u' })).toBe('D:\\u\\AppData\\Local\\Temp\\goated\\usage-log.jsonl')
  expect(usageLogPlace({ ...posix, xdgStateHome: '/state', localAppData: 'D:\\AppData\\Local' })).toBe('/state/goated/usage-log.jsonl')
  expect(usageLogPlace({ ...posix, home: '/srv/u/' })).toBe('/srv/u/.local/state/goated/usage-log.jsonl')
  expect(usageLogPlace(posix)).toBe(null)
})
