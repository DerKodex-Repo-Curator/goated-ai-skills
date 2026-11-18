"""A summary of the usage log (Ticket 082), as Markdown.

`report(entries, project=..., adapter=..., skipped=...)` counts what the
entries of `usage_log.read_log` hold: skill loads by skill and cause, holds
by gate with what became of them, closeout items, route lines by form,
reference reads, and the projects by key with their sessions. A project
key or an adapter name keeps only that project's or adapter's entries.
`skipped` is how many lines the reader passed over; an entry whose fields
cannot be counted, such as a closeout item with no label, adds to it.
`goated_usage_report.py`, beside this package, is the same summary as a
command.

Holds count each time one was shown; outcomes count once per gate and
turn, as the core settles them (`friction.py`), so a gate held three times
in a turn and then met has three holds and one `answered`.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from .friction import ANSWERED, DECLINED, STOOD_DOWN, UNANSWERED
from .usage_log import CAUSES

OUTCOMES = (ANSWERED, DECLINED, STOOD_DOWN, UNANSWERED)


def report(entries: list[dict], project: str | None = None, adapter: str | None = None,
           skipped: int = 0) -> str:
    """The Markdown summary of `entries`, only those of `project` (a key)
    and `adapter` (a name) when given; `skipped` lines are said."""

    kept = [e for e in entries
            if (project is None or e.get("project") == project)
            and (adapter is None or e.get("adapter") == adapter)]
    sessions = {(e.get("adapter"), e.get("session")) for e in kept}
    projects: dict[str, set] = defaultdict(set)
    loads: dict[str, Counter] = defaultdict(Counter)
    holds: Counter = Counter()
    outcomes: dict[str, Counter] = defaultdict(Counter)
    items: Counter = Counter()
    routes: Counter = Counter()
    refs: Counter = Counter()
    whole: Counter = Counter()
    for e in kept:
        projects[e.get("project") or "(none)"].add((e.get("adapter"), e.get("session")))
        try:
            _count(e, loads, holds, outcomes, items, routes, refs, whole)
        except (KeyError, TypeError, AttributeError):
            skipped += 1

    where = []
    if project:
        where.append(f"project `{project}`")
    if adapter:
        where.append(f"adapter `{adapter}`")
    lines = [f"# GOATED usage log{': ' + ', '.join(where) if where else ''}", "",
             f"{len(sessions)} sessions, from "
             + (", ".join(f"`{a}`" for a in sorted({str(a) for a, _ in sessions})) or "none")
             + "."
             + (f" {skipped} lines were skipped as no entry." if skipped else ""), ""]
    lines += _table("Projects", ["project", "sessions"],
                    _counted(Counter({key: len(s) for key, s in projects.items()})))
    lines += _table("Skill loads", ["skill", *CAUSES, "total"],
                    [[skill, *(c[k] for k in CAUSES), sum(c.values())]
                     for skill, c in _by_total(loads)])
    lines += _table("Holds", ["gate", "holds", *(o.replace("_", " ") for o in OUTCOMES)],
                    [[gate, holds[gate], *(outcomes[gate][o] for o in OUTCOMES)]
                     for gate in sorted(set(holds) | set(outcomes),
                                        key=lambda g: (-holds[g], g))])
    lines += _table("Closeout items", ["item", "asked"], _counted(items))
    lines += _table("Route lines", ["form", "lines"], _counted(routes))
    lines += _table("Reference reads", ["reference", "reads", "whole by a file read"],
                    [[name, n, whole[name]] for name, n in _counted(refs)])
    return "\n".join(lines).rstrip() + "\n"


def _count(e: dict, loads, holds, outcomes, items, routes, refs, whole) -> None:
    """Add entry `e` to the tables; raises KeyError or TypeError for fields
    it cannot count, before changing any table."""

    kind = e["type"]
    if kind == "load":
        loads[str(e["skill"])][str(e["cause"])] += 1
    elif kind == "hold":
        labels = [str(item["label"]) for item in e.get("items", [])]
        holds[str(e["gate"])] += 1
        for label in labels:
            items[label] += 1
    elif kind == "outcome":
        outcomes[str(e["gate"])][str(e["outcome"])] += 1
    elif kind == "route":
        routes[str(e["intensity"] if e["form"] == "route" else e["form"])] += 1
    elif kind == "ref":
        name = f"{e['skill']}/{e['file']}"
        refs[name] += 1
        if e.get("read_tool") and not e.get("partial"):
            whole[name] += 1


def _by_total(table: dict[str, Counter]) -> list[tuple[str, Counter]]:
    return sorted(table.items(), key=lambda row: (-sum(row[1].values()), row[0]))


def _counted(counts: Counter) -> list[list]:
    return [[name, n] for name, n in sorted(counts.items(), key=lambda row: (-row[1], row[0]))]


def _table(title: str, header: list[str], rows: list[list]) -> list[str]:
    lines = [f"## {title}", ""]
    if not rows:
        return lines + ["None.", ""]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + " --- |" * len(header))
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return lines + [""]
