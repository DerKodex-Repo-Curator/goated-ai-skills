// The skill references the installed GOATED registry declares, and the counts the mod keeps for each. The registry
// (`stack/goated-stack.yaml` in a GOATED distribution) gives each reference either a signal, which a hold enforces, or
// an advisory reason. Pure: hooks/register.tsx reads the file and hands its text here.

import type { AllTime, Counts, DeclaredReferences, RefAskOutcome } from '../types'

/** Where the registry sits from the mod's folder (`<goated-root>/adapters/claude-code/skill-usage`), as the adapter finds it from its own. */
export const REGISTRY_FROM_MOD = '../../../stack/goated-stack.yaml'

// The block-style YAML the registry is written in, as far as the references need: the top-level `skills:` list, each
// skill's `- name:`, its `references:` list, and each entry's `- file:` with a `signal:` or an `advisory:` key.
const TOP_KEY = /^(\S[^:]*):/
const SKILL = /^ {2}- name:\s*(\S+)\s*$/
const REFERENCES = /^ {4}references:\s*(\[\])?\s*$/
const SKILL_KEY = /^ {4}\S/
const FILE = /^ {6}- file:\s*(\S+)\s*$/
const STATUS = /^ {8}(signal|advisory):/

/**
 * The references a registry's text declares, by skill, then file name, each `enforced` or `advisory`. A skill with no
 * references is left out. Null for text with no top-level `skills:` list, such as an empty or unrelated file, so the
 * caller shows reads as it would with no registry at all.
 */
export function declaredReferences(text: string): DeclaredReferences | null {
  const declared: DeclaredReferences = {}
  let hasSkills = false
  let isInSkills = false
  let skill: string | undefined
  let isInReferences = false
  let file: string | undefined
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.replace(/\s+#.*$/, '')
    if (line.trim() === '' || line.trimStart().startsWith('#')) continue
    const top = TOP_KEY.exec(line)
    if (top) {
      isInSkills = top[1] === 'skills'
      hasSkills ||= isInSkills
      skill = file = undefined
      isInReferences = false
      continue
    }
    if (!isInSkills) continue
    const named = SKILL.exec(line)
    if (named) {
      skill = named[1]
      file = undefined
      isInReferences = false
      continue
    }
    if (SKILL_KEY.test(line)) {
      const list = REFERENCES.exec(line)
      isInReferences = list !== null && list[1] === undefined
      file = undefined
      continue
    }
    if (!isInReferences || skill === undefined) continue
    const entry = FILE.exec(line)
    if (entry) {
      file = entry[1]
      continue
    }
    const status = STATUS.exec(line)
    if (status && file !== undefined) (declared[skill] ??= {})[file] = status[1] === 'signal' ? 'enforced' : 'advisory'
  }
  return hasSkills ? declared : null
}

/** How a reference stands now: as the registry declares it, or `retired` when it no longer does. */
export type ReferenceStatus = 'enforced' | 'advisory' | 'retired'

/**
 * One reference's counts: what became of the holds that asked for it (`asks`), and how often it was read in all
 * (`reads`), asked or not.
 */
export type ReferenceRow = { file: string; status: ReferenceStatus; asks: Counts<RefAskOutcome>; reads: number }

/** A skill's declared and retired references, with how often the skill loaded. */
export type SkillReferences = { skill: string; loads: number; rows: ReferenceRow[] }

const sum = (counts: Counts<string> | undefined) => Object.values(counts ?? {}).reduce<number>((n, c) => n + (c ?? 0), 0)
const REFERENCE_PATH = /^references\/([^/]+)$/

/**
 * The counts of every reference `declared` names, by skill A to Z, each skill's references in the registry's order and
 * then its retired ones A to Z. A retired reference is one the counts hold under `references/` that the registry no
 * longer declares: asked for by a hold, or read from a skill the registry still declares references for. A skill
 * shows only once it loaded, had a reference read, or was asked for one, so a skill never used adds no rows.
 */
export function referenceCounts(all: Pick<AllTime, 'loads' | 'refs' | 'refAsks'>, declared: DeclaredReferences): SkillReferences[] {
  const filesIn = (table: Record<string, unknown> | undefined) => Object.keys(table ?? {}).flatMap(path => REFERENCE_PATH.exec(path)?.[1] ?? [])
  const skills = new Set([...Object.keys(declared), ...Object.keys(all.refAsks ?? {})])
  return [...skills]
    .sort((a, b) => a.localeCompare(b))
    .flatMap(skill => {
      const own = declared[skill] ?? {}
      const retired = [...new Set([...filesIn(all.refAsks?.[skill]), ...(declared[skill] ? filesIn(all.refs?.[skill]) : [])])]
        .filter(file => own[file] === undefined)
        .sort((a, b) => a.localeCompare(b))
      const rows: ReferenceRow[] = [
        ...Object.entries(own).map(([file, status]) => ({ file, status })),
        ...retired.map(file => ({ file, status: 'retired' as const })),
      ].map(r => ({ ...r, asks: all.refAsks?.[skill]?.[`references/${r.file}`] ?? {}, reads: all.refs?.[skill]?.[`references/${r.file}`] ?? 0 }))
      const loads = sum(all.loads[skill])
      const isUsed = loads > 0 || rows.some(r => r.reads > 0 || sum(r.asks) > 0)
      return isUsed && rows.length > 0 ? [{ skill, loads, rows }] : []
    })
}

/**
 * A reference's counts in words: an advisory one's reads in its skill's loads, so its read rate shows; an enforced or
 * retired one's fired, read and skipped holds.
 */
export function referenceWords(row: ReferenceRow, loads: number): string {
  if (row.status === 'advisory') return `advisory · read ${row.reads} in ${loads} ${loads === 1 ? 'load' : 'loads'}`
  return `${row.status} · fired ${row.asks.fired ?? 0} · read ${row.asks.read ?? 0} · skipped ${row.asks.skipped ?? 0}`
}
