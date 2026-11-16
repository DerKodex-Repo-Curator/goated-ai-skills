// What the pane says and how it reads: the words for stations, causes, hooks
// and outcomes, the tones that carry meaning, and the rates the pane, the
// picture and the report share. No drawing here.

import type { ElementTable, RenderSurface } from 'claude-code'

import type { Counts, Origin, Outcome, RouteForm } from '../types'
import { ROUTE_LINE } from './classify'

/** Where a drawing goes: the surface's elements and its name. */
export type View = { ui: ElementTable<RenderSurface>; surface: RenderSurface }

// ---------- words -----------------------------------------------------------------

/** The map's stations: who caused a skill to load. Short enough to sit under a node. */
export const STATION: Record<Origin, string> = {
  'user-slash': 'Your /cmd',
  'user-named': 'You asked',
  'hook-nudged': 'Hooks',
  'router-routed': 'Router',
  'self-initiated': 'Agent',
  subagent: 'Subagents',
}
/** Why a skill loaded, as the feed says it. */
export const BECAUSE: Record<Origin, string> = {
  'user-slash': 'you typed it',
  'user-named': 'you asked for it',
  'hook-nudged': 'after a hook',
  'router-routed': 'router picked it',
  'self-initiated': 'the agent chose it',
  subagent: 'a subagent chose it',
}
/** The GOATED hooks by what they do, not by their internal labels: the adapter's gates first, then the hooks that summaries stored by earlier versions name. */
export const HOOK: Record<string, string> = {
  'router-first': 'router-first hold',
  'route-line': 'route-line hold',
  pipeline: 'pipeline hold',
  commit: 'commit hold',
  'pull-request': 'pull-request hold',
  spawn: 'spawn hold',
  // Earlier versions recorded tips under these three keys; the adapter's meaning wins.
  design: 'design hold',
  security: 'security hold',
  closeout: 'closeout hold',
  'router-rule': 'GOATED router rule',
  'route-hold': 'route check',
  'design-hold': 'design check',
  'design-new-file': 'new-file tip',
  'security-hold': 'security check',
  'commit-hold': 'commit check',
  'pr-hold': 'PR check',
  'spawn-hold': 'spawn brief check',
  'merge-conflict': 'merge conflict',
  diagnose: 'repeated failure',
}
export const hookName = (hook: string) => HOOK[hook] ?? hook
/** What became of one skill a hook asked for. */
export const RESULT: Record<Outcome, string> = {
  followed: 'loaded',
  'read files': 'files read',
  'already loaded': 'already loaded',
  declined: 'declined',
  ignored: 'not loaded',
  pending: 'waiting',
}
export const skillName = (skill: string) => (skill === ROUTE_LINE ? 'a route line' : skill)
/** A route line's form, as the pane counts it. */
export const ROUTE_FORM: Record<RouteForm, string> = { direct: 'direct', continue: 'continue', route: 'routed' }
export const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

// ---------- meaning ---------------------------------------------------------------

/**
 * How a piece of the pane reads: plain, dim, one of the three meanings, a
 * decline (`declined`, a paler green: handled, by saying why the skill does not
 * apply), or a reference read (`read`), in the picture's pink.
 */
export type Meaning = 'good' | 'waiting' | 'bad'
export type Tone = 'plain' | 'dim' | Meaning | 'declined' | 'read'
/** A paler green than success, readable on a light or a dark theme; no theme key is one. */
export const DECLINED_COLOR = '#8fcfa8'
/** Reference reads' pink, between the picture's dark and light pinks, readable on either theme. */
export const READ_COLOR = '#e0679b'
/**
 * Theme keys, so the meanings follow the person's theme: green, amber, red. No
 * theme key is pink or pale green, so reference reads and declines take fixed
 * colours between the picture's dark and light ones, readable on either.
 */
export const COLOR: Record<Tone, string | undefined> = { plain: undefined, dim: undefined, good: 'success', waiting: 'warning', bad: 'error', declined: DECLINED_COLOR, read: READ_COLOR }
export const OUTCOME_TONE: Record<Outcome, Meaning | 'declined'> = { followed: 'good', 'read files': 'good', 'already loaded': 'good', declined: 'declined', ignored: 'bad', pending: 'waiting' }
/** Outcomes that count as handled: the skill acted on, or declined with a reason. */
export const isHandled = (o: Outcome) => OUTCOME_TONE[o] === 'good' || o === 'declined'

/** What the agent handled (acted on or declined), of the nudges that are settled; `declined`: how many of those were declines. */
export function followCounts(c: Counts<Outcome>): { acted: number; settled: number; pending: number; declined: number } {
  const declined = c.declined ?? 0
  const acted = (c.followed ?? 0) + (c['read files'] ?? 0) + (c['already loaded'] ?? 0) + declined
  return { acted, settled: acted + (c.ignored ?? 0), pending: c.pending ?? 0, declined }
}

/** A follow rate's meaning: green from 80%, amber from 40%, red below. */
export const rateTone = (acted: number, settled: number): 'dim' | Meaning => (settled === 0 ? 'dim' : acted / settled >= 0.8 ? 'good' : acted / settled >= 0.4 ? 'waiting' : 'bad')
