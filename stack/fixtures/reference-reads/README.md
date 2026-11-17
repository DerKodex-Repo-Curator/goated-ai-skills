# Reference Reads Fixtures

Each skill's entry in `stack/goated-stack.yaml` lists every file under its
`references/` folder. Each file has either a `signal`, which makes its read
enforced, or `advisory` with a short reason no signal fits. The registry
schema, `$defs/referenceEntry` and `$defs/referenceSignal` in
`stack/schemas/stack-registry.schema.json`, owns the shape; this folder holds
the cases that pin it down.

`entries.yaml` holds one accepted entry per signal kind, an advisory entry,
and near misses the schema must reject. `scripts/validation/references.py`
checks each case, and also checks that each skill's declared files, the files
in its `references/` folder, and the files its `SKILL.md` links are one set.

## Signal Kinds

| Kind | Parameters | Required read when |
| --- | --- | --- |
| `edit-adds-pattern` | `pattern`, optional `file_kind` | an edit adds text matching a pattern named in the registry's `reference_patterns`, in a file of that kind if one is given |
| `edit-of-file-kind` | `file_kind`, optional `min_added_lines` | an edit of a file of that kind adds at least that many lines |
| `write-under-path` | `path`, ending in `/` | a write under that project-relative folder |
| `gate-fires` | `gate`: one of the adapter gate names the schema lists, and one the Claude Code adapter observes, which today is `repeated-failure` only | another gate of the adapter fires, such as `repeated-failure` |
| `sensitive-category-count` | `min_categories` | the turn's security-sensitive changes span at least that many categories |
| `spawn-with-brief` | none | an agent or session is started with a brief |
| `existing-rule` | `gate`: `closeout`, `design-reads`, or `spawn` | an adapter rule that enforces the read today, unchanged |

A new kind needs a schema change and an adapter change. A new reference of an
existing kind needs only its registry entry. A `gate-fires` entry is the exception: the schema
allows every gate name, but `validate_skills.py` fails on a gate the Claude
Code adapter does not observe, since that entry would never be enforced.
Observing another gate is an adapter change. A signal applies only once its
skill counts as loaded; a framework adapter decides how it observes each kind.

Installed skills never read the registry. A skill installed alone keeps its
"read when" sentences in `SKILL.md` and works as before.
