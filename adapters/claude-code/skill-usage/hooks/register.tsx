// Skill usage: watches every row added to the conversation, turns the ones
// that matter into neutral events (classify.ts labels them), and shows the
// result in a pane, the status line and `/skill-usage report`.
//
// The session's events live in $.state. Each finished main turn writes the
// session's summary to $.store under its own key (`s:<session id>`), and the
// all-time view is the sum of the other sessions' summaries plus this one,
// live. Observing never breaks the conversation: a failure is kept in
// `lastError` and shown in the pane until the next successful save.

import { atom, read, update } from 'claude-code'
import type { EngineInterface as Dollar, Register, SessionAppendInput } from 'claude-code'

import type { AllTime, Available, SessionSummary, Tab, UsageEvent } from '../types'
import { addSession, closeOpen, historyEvents, hookEvents, markerEvents, mergeSummaries, overrideEvents, promptEvents, short, summarize, textOf, toolUseEvents } from './classify'
import type { HistoryMessage } from './classify'
import { allTimeTab, forgetPictures, PANE_COLUMNS, PREVIEW_MS, reportText, sessionTab, statusText, unusedTab } from './view'
import type { View } from './view'

const PANE = 'skill-usage'
const SESSION_KEY = 's:'
const LEGACY_STORE_KEY = 'sessions' // v0.1.0 kept every session under one key
const MAX_EVENTS = 5000
const MAX_SESSIONS = 300
// The attachment rows that carry hook output; other hook_* rows repeat it.
const HOOK_ATTACHMENTS = new Set(['hook_additional_context', 'hook_blocking_error'])
// The attachment row of a hook's notice to you, where the adapter says it recorded an override.
const NOTICE_ATTACHMENT = 'hook_system_message'
const OWN_SOURCES = new Set(['userSettings', 'projectSettings'])

const events = atom({ plugin: 'skill-usage', key: 'events' } as const, [], { shape: 'events-1' })
const owner = atom({ plugin: 'skill-usage', key: 'owner' } as const, null)
const backfilled = atom({ plugin: 'skill-usage', key: 'backfilled' } as const, null)
const baseline = atom({ plugin: 'skill-usage', key: 'baseline' } as const, null, { shape: 'summary-1' })
const available = atom({ plugin: 'skill-usage', key: 'available' } as const, null, { shape: 'available-2' })
const allTime = atom({ plugin: 'skill-usage', key: 'allTime' } as const, null, { shape: 'all-time-1' })
const tab = atom({ plugin: 'skill-usage', key: 'tab' } as const, 'session')
const lastError = atom({ plugin: 'skill-usage', key: 'lastError' } as const, null)
const preview = atom({ plugin: 'skill-usage', key: 'preview' } as const, null)

type Stored = { t: number; summary: SessionSummary }

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    await $.command.register({ name: 'skill-usage', description: 'Skill usage pane; `/skill-usage preview` plays every animation, `/skill-usage report` prints the all-time report' })
    try {
      await claimSession($)
      await knownSkills($, true)
      await backfill($)
      showStatus($, await liveSummary($))
    } catch (error) {
      await noteError($, error)
    }
    void $.ui.open({ id: PANE, title: 'Skill usage' })
    return started
  })

  on('session.append', async ($, e, next) => {
    const appended = await next(e)
    try {
      await observeRow($, e)
    } catch (error) {
      await noteError($, error)
    }
    return appended
  })

  on('turn.complete', async ($, e, next) => {
    // Every hook hears a subagent's turn end too: it settles that subagent's nudges. Only the main loop's is saved.
    try {
      await record($, [{ kind: 'turn-end', t: await $.clock.now(), ...(e.agentId ? { agent: e.agentId } : {}) }])
      if (!e.agentId) await persist($, false)
    } catch (error) {
      await noteError($, error)
    }
    return next(e)
  })

  on('session.end', async ($, e, next) => {
    try {
      await persist($, true)
    } catch (error) {
      await noteError($, error)
    }
    return next(e)
  })

  on('command.run', { command: 'skill-usage' }, async ($, e) => {
    const arg = e.args.trim()
    if (arg === 'report') return { text: reportText(addSession(await read($, allTime), await liveSummary($)), await read($, available)) }
    await $.ui.open({ id: PANE, title: 'Skill usage' })
    if (arg === 'preview') {
      // The picture shows the Session tab's map, so the preview switches to it.
      await update($, tab, () => 'session')
      forgetPictures()
      const start = await $.clock.now()
      await update($, preview, () => start)
      return { text: `Playing every animation on the Session tab's picture for about ${Math.round(PREVIEW_MS / 1000)} seconds. Nothing in it is counted.` }
    }
    return { text: 'Skill usage pane opened. `/skill-usage preview` plays every animation; `/skill-usage report` prints the all-time report.' }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const v: View = { ui: $.ui.resolve(e), surface: e.surface }
    const { Box, Button, Text } = v.ui
    const current = await read($, tab)
    const session = summarize(await read($, events))
    const live = mergeSummaries(await read($, baseline), session)
    const error = await read($, lastError)
    // The Work Map's feed length: enough to follow a turn, short enough to stay under the picture.
    const rows = 16
    const tabs: [Tab, string][] = [['session', 'Session'], ['all', 'All time'], ['unused', 'Unused']]
    const now = await $.clock.now()
    const body =
      current === 'session' ? sessionTab(v, live, session.timeline, rows, now, await read($, preview))
      : current === 'all' ? allTimeTab(v, addSession(await read($, allTime), live), rows)
      : unusedTab(v, addSession(await read($, allTime), live), await read($, available))

    return (
      <Box flexDirection="column" gap={1} paddingX={1}>
        <Box gap={1}>
          {tabs.map(([id, label]) => (
            <Button key={`tab-${id}`} label={label} variant={current === id ? 'primary' : 'secondary'} onPress={() => (forgetPictures(), update($, tab, () => id))} />
          ))}
        </Box>
        {error && (
          <Box borderStyle="round" borderColor="#E5735F" paddingX={1}>
            <Text color="#E5735F" wrap="truncate-end">Observer error: {error}</Text>
          </Box>
        )}
        {/* Inside the pane's padding, and no wider than the picture, so each row's columns stay together. */}
        <Box flexDirection="column" width={Math.min(e.props.bodyColumns - 2, PANE_COLUMNS)}>
          {body}
        </Box>
      </Box>
    )
  })
}

/**
 * The skills the session lists for the model, read once and kept. Reading the
 * listing needs a bound session, so only `refresh` callers (session start, a
 * prompt) try again when it was not available yet.
 */
async function knownSkills($: Dollar, refresh = false): Promise<string[]> {
  const kept = await read($, available)
  if (kept || !refresh) return kept?.names ?? []
  const usage = await $.session.usage({ breakdown: 'summary' })
  const skills = usage.context.breakdown?.skills
  if (!skills) return []
  const list: Available = {
    names: skills.skillFrontmatter.map(s => short(s.name)),
    own: skills.skillFrontmatter.filter(s => OWN_SOURCES.has(s.source)).map(s => short(s.name)),
    total: skills.totalSkills,
    included: skills.includedSkills,
  }
  await update($, available, () => list)
  return list.names
}

/**
 * Makes sure the kept events belong to the running session. Another id means
 * `/clear` started a new session (session.start does not run for it): the old
 * one is saved as finished and the events start over. Fresh state for an id
 * the store already has means a resume: what was stored becomes the baseline.
 */
async function claimSession($: Dollar): Promise<string> {
  const id = await $.session.id()
  const held = await read($, owner)
  if (held === id) return id
  if (held !== null) {
    await save($, held, true)
    await update($, events, () => [])
  }
  const stored = (await $.store.get(SESSION_KEY + id)) as Stored | undefined
  await update($, baseline, () => (stored ? closeOpen(stored.summary) : null))
  await update($, owner, () => id)
  await loadAllTime($, id)
  return id
}

/**
 * Once per session, rebuilds the events from the session's history, so a mod
 * that loaded mid-session (a hot reload, an install) shows what came before.
 * History covers what was observed live too, so it replaces the events. A
 * resumed session the store already has keeps its stored baseline instead.
 * Runs from session.start alone: after `/clear` the new session is observed
 * from its first row.
 */
async function backfill($: Dollar) {
  const id = await $.session.id()
  if ((await read($, backfilled)) === id) return
  await update($, backfilled, () => id)
  if (await read($, baseline)) return
  const history = (await $.session.messages({ as: 'api' })) as HistoryMessage[]
  const rebuilt = historyEvents(history, await knownSkills($), await $.clock.now())
  await update($, events, () => rebuilt.slice(-MAX_EVENTS))
}

/** All-time totals from every other stored session, pruning the oldest past the cap. */
async function loadAllTime($: Dollar, id: string) {
  await $.store.delete(LEGACY_STORE_KEY)
  // A trace left by an animation diagnosis; nothing reads it.
  await $.store.delete('diag-trail')
  const keys = (await $.store.keys()).filter(k => k.startsWith(SESSION_KEY))
  const sessions: [string, Stored][] = []
  for (const key of keys) {
    const value = (await $.store.get(key)) as Stored | undefined
    if (value) sessions.push([key, value])
  }
  sessions.sort(([, a], [, b]) => b.t - a.t)
  for (const [key] of sessions.slice(MAX_SESSIONS)) await $.store.delete(key)
  const others = sessions.slice(0, MAX_SESSIONS).filter(([key]) => key !== SESSION_KEY + id)
  await update($, allTime, () => others.reduce<AllTime | null>((acc, [, v]) => addSession(acc, closeOpen(v.summary)), null))
}

/** This session so far: the stored baseline plus what was observed since. */
async function liveSummary($: Dollar, isFinal = false): Promise<SessionSummary> {
  const { timeline: _, ...summary } = summarize(await read($, events), isFinal)
  return mergeSummaries(await read($, baseline), summary)
}

async function persist($: Dollar, isFinal: boolean) {
  await save($, await claimSession($), isFinal)
}

/** Stores a session's summary; a session with no prompt or skill load is not one worth counting. */
async function save($: Dollar, id: string, isFinal: boolean) {
  const list = await read($, events)
  const prior = await read($, baseline)
  if (!prior && !list.some(ev => ev.kind === 'prompt' || ev.kind === 'load')) return
  await $.store.set(SESSION_KEY + id, { t: await $.clock.now(), summary: await liveSummary($, isFinal) } satisfies Stored)
  // Every write redraws the pane, and a redraw reloads the picture: clear only what is set.
  if ((await read($, lastError)) !== null) await update($, lastError, () => null)
}

async function record($: Dollar, add: UsageEvent[]) {
  if (add.length === 0) return
  await claimSession($)
  await update($, events, old => [...old, ...add].slice(-MAX_EVENTS))
  showStatus($, await liveSummary($))
}

function showStatus($: Dollar, s: SessionSummary) {
  $.ui.status(statusText(s))
}

async function noteError($: Dollar, error: unknown) {
  await update($, lastError, () => String(error))
}

/**
 * Turns one conversation row into events: the person's prompts and slash
 * commands, skill loads, skill-file reads, subagent spawns, the first tool,
 * route and skip lines, hook messages, holds, override notices and
 * compactions. Rows come in conversation order, so a prompt always
 * precedes the rows of its turn; a prompt typed mid-turn is folded into the
 * running turn by another door and starts nothing.
 */
async function observeRow($: Dollar, e: SessionAppendInput) {
  const isMain = !e.agentId
  const isHookRow = e.door === 'hook-context' || (e.door === 'attachment' && HOOK_ATTACHMENTS.has(e.message.name ?? ''))
  // Every row of the conversation passes here: leave the others at no cost.
  // Unverified which door a hook's notice comes in by; only the adapter's override wording counts, so both are read.
  const isNoticeRow = e.door === 'notice' || (e.door === 'attachment' && e.message.name === NOTICE_ATTACHMENT)
  if (!['prompt', 'command', 'response', 'tool-result', 'compaction'].includes(e.door) && !isHookRow && !isNoticeRow) return
  const blocks = e.message.content
  const t = await $.clock.now()
  const add: UsageEvent[] = []

  if ((e.door === 'prompt' || e.door === 'command') && isMain && !e.message.isMeta) {
    add.push(...promptEvents(textOf(blocks), await knownSkills($, true), t))
  } else if (e.door === 'response') {
    const uses = blocks.filter(b => b.type === 'tool_use').map(b => ({ name: String(b.name), input: (b.input ?? {}) as Record<string, unknown> }))
    const hasToolBefore = uses.length > 0 && (await read($, events)).some(ev => ev.kind === 'tool')
    add.push(...markerEvents(textOf(blocks.filter(b => b.type === 'text')), t, e.agentId), ...toolUseEvents(uses, !isMain, hasToolBefore, t, e.agentId))
  } else if (isHookRow) {
    // Which subagent a row belongs to, so its own turn end and skip lines settle its own nudges.
    add.push(...hookEvents(textOf(blocks), await knownSkills($), t, { agent: e.agentId }))
  } else if (isNoticeRow) {
    add.push(...overrideEvents(textOf(blocks), t))
  } else if (e.door === 'tool-result') {
    const skills = await knownSkills($)
    for (const b of blocks) {
      if (b.type === 'tool_result' && b.is_error) add.push(...hookEvents(textOf(b.content), skills, t, { agent: e.agentId, holdsOnly: true }))
    }
  } else if (e.door === 'compaction' && isMain) {
    // A compaction appends a boundary and a summary: count it once.
    const last = (await read($, events)).at(-1)
    if (last?.kind !== 'compact') add.push({ kind: 'compact', t })
  }
  await record($, add)
}
