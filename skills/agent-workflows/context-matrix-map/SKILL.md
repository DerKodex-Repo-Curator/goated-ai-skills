---
name: context-matrix-map
description: Use when agents in a project keep searching for the same sources, read the wrong docs first, or lack a map of which files to load for which kind of task, typically found while onboarding or refreshing a project.
metadata:
  goated-category: agent-workflows
---

# Context Matrix Map

## Purpose

Create or incrementally refresh a durable, source-grounded map so future agents
know where to look first, what to defer, and which sources are specialized.

Activate it only when the onboarding artifact budget includes a source map
because retrieval is repeated, cross-area, stale, or unreliable. A lightweight
project can stop at thin policy and routing without this artifact.

A project with no `docs/agents/context-matrix.md` is a candidate for this
skill, not a reason to activate it; an installed enforcement adapter may name
it once per project as a notice that never blocks.

## Inputs

- User request or onboarding goal, and the target-project root path.
- Existing agent instruction files and root `CONTEXT.md`, if present.
- Existing project docs, ADRs, issue or PRD folders, test layout, build metadata, and command definitions.
- Existing `docs/agents/` artifacts, external-doc lookup notes, or context packs, if present.
- Selected onboarding profile, artifact budget, and shared evidence bundle when
  running inside the integrated stack.

## Dependencies

Hard: None.

Soft:
- project-standards-calibration after mapping when standards need durable profile
- verification-before-completion before complete/evidence-backed/future-agent claims

Fallback: If companion skills are unavailable, inspect minimal project files and state lower confidence.

## Workflow

1. Confirm the target-project boundary:
   - Identify the project root from the user's request, current directory, or repository metadata.
   - Keep installed-skill instructions separate from target-project artifacts.
   - If the root is ambiguous, inspect one local source such as `git rev-parse --show-toplevel`, a package manifest, or a README before asking the user.

2. Reuse the shared onboarding evidence:
   - Start from fresh entries already collected during onboarding discovery.
   - Read more only when the bundle is stale, contradictory, or too shallow to
     place a source safely.
   - Add compact locator, provenance, freshness, finding, and confidence
     updates for other selected onboarding artifacts to reuse.

3. Discover remaining candidate sources without bulk-reading:
   - List top-level files and directories.
   - Search for likely instruction files, README files, docs indexes, ADRs, issue folders, PRDs, context packs, optional `docs/agents/external-docs/` lookup notes, package manifests, build scripts, test folders, and config files.
   - Prefer fast file discovery commands and targeted file opens over recursive reading.
   - Open generated output, dependency folders, lockfiles, binary assets, or large data dumps only when they are the only source for a required fact.

4. Sample sources just enough to classify them:
   - Read short indexes, headings, manifests, command definitions, and nearby docs that explain project conventions.
   - For code areas, identify entrypoints, feature directories, shared libraries, data-access boundaries, and integration surfaces from filenames and shallow reads.
   - For tests, identify test frameworks, locations, naming patterns, and the smallest useful commands.
   - For ADRs and specs, record titles, paths, dates when available, and the decision or product area they govern.

5. Build the matrix using progressive-disclosure tiers:
   - **First-read**: sources future agents should read at the start of most serious sessions.
   - **Second-read**: sources to read after the task surface is known or before changing a relevant area.
   - **Only-if-needed**: deep references, large docs, historical specs, generated files, specialized commands, or narrow subsystems.
   - Put external-doc lookup notes in the lowest useful tier, usually **Only-if-needed**, unless a captured source is central to most serious work in the target project.
   - Put each source in the lowest-context tier that still keeps future agents safe.

6. Cover only relevant source types:
   - Docs and README files.
   - Existing project context files, such as root `CONTEXT.md`.
   - Code areas and important boundaries.
   - Tests and verification commands.
   - Build, run, lint, format, or release commands.
   - ADRs, PRDs, issues, or decision records.
   - Agent instructions, external-doc lookup notes, and existing context packs under paths such as `docs/agents/`.

7. Write or incrementally refresh the default tracked artifact:
   - Use `docs/agents/context-matrix.md` unless the user requested another tracked path.
   - Create `docs/agents/` if needed.
   - Read the existing file first. Preserve accurate entries, update only stale
     or affected rows, and remove content only when current evidence disproves
     it.
   - Mark uncertainty explicitly instead of filling gaps with speculation.

8. Stop when the map can route future reading:
   - Leave module-by-module explanation out of scope.
   - Defer architecture diagrams, standards profiles, security review, or detailed delivery planning to companion skills.
   - If the project is too large to map in one pass, write a partial matrix with clear gaps and recommended next scans.
   - Use `verification-before-completion` before claiming the matrix is complete, evidence-backed, or ready for future agents.

## Output Contract

Write `docs/agents/context-matrix.md` with this shape by default:

```markdown
# Context Matrix

## Purpose

One short paragraph describing how future agents should use this map.

## First-Read Sources

| Source | Why read it | When to read | Notes |
| --- | --- | --- | --- |

## Second-Read Sources

| Source | Why read it | When to read | Notes |
| --- | --- | --- | --- |

## Only-If-Needed Sources

| Source | Why read it | When to read | Notes |
| --- | --- | --- | --- |

## Code Areas

| Area | Paths | What lives there | Read before |
| --- | --- | --- | --- |

## Tests And Commands

| Command or path | Purpose | When to use | Evidence |
| --- | --- | --- | --- |

## Decisions, External Docs, And Context Packs

| Source | Scope | Status | Notes |
| --- | --- | --- | --- |

## Gaps And Assumptions

- <unknown, stale, or inferred item>

## Last Updated

- Date: <YYYY-MM-DD>
- Updated by: <agent or user label>
- Evidence used: <brief list of commands and paths>
```

After writing the file, report:

- artifact path;
- key first-read sources;
- notable gaps or assumptions;
- verification or discovery commands used.

In integrated use, return these items as an internal envelope delta unless a
conflict, blocker, material route change, or explicit user request justifies a
visible report.

## Delegation

Main owns the target-project boundary, tiering judgment, final artifact, and user communication. Delegate only bounded independent scans: find docs, ADRs, and context packs; identify code-area entrypoints, test frameworks, or commands; or summarize one named folder/source family. Require paths inspected, commands run, source docs/files used, assumptions, confidence, and unresolved gaps; without subagents, run the same scans sequentially with a narrower context budget, and never promote unevidenced summaries to project facts.

## Guardrails

- Keep the matrix a routing map with brief, evidence-based, path-oriented entries, not an architecture essay, exhaustive file inventory, onboarding tutorial, or handoff.
- Tier sources by when future agents need them, not by personal preference.
- Keep credentials, client data, and private or ignored notes out of the tracked matrix unless the user explicitly requests a private artifact.
- Record GOATED artifacts, ADRs, tests, agent instruction files, and external-doc lookup notes only when found; treat lookup notes that are present as dated optional evidence and re-check external sources when freshness matters.
- Claim a command works only when it was discovered from project files or actually run.
- Prefer "unknown" or "not found in this pass" over guessing.
