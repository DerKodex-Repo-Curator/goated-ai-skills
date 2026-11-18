"""A summary of the usage log (Ticket 082), as Markdown.

`report(entries, project=..., adapter=...)` counts what the entries of
`usage_log.read_entries` hold: skill loads by skill and cause, holds by
gate with what became of them, closeout items, route lines by form, and
reference reads. A project key or an adapter name keeps only that
project's or adapter's entries. `goated_usage_report.py`, beside this
package, is the same summary as a command.

Holds count each time one was shown; outcomes count once per gate and
turn, as the core settles them (`friction.py`), so a gate held three times
in a turn and then met has three holds and one `answered`.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from .friction import ANSWERED, DECLINED, STOOD_DOWN, UNANSWERED
from .usage_log import CAUSES

OUTCOMES = (ANSWERED, DECLINED, STOOD_DOWN, UNANSWERED)


def report(entries: list[dict], project: str | None = None, adapter: str | None = None) -> str:
    """The Markdown summary of `entries`, only those of `project` (a key)
    and `adapter` (a name) when given."""

    kept = [e for e in entries
            if (project is None or e.get("project") == project)
            and (adapter is None or e.get("adapter") == adapter)]
    sessions = {(e.get("adapter"), e.get("session")) for e in kept}
    loads: dict[str, Counter] = defaultdict(Counter)
    holds: Counter = Counter()
    outcomes: dict[str, Counter] = defaultdict(Counter)
    items: Counter = Counter()
    routes: Counter = Counter()
    refs: Counter = Counter()
    whole: Counter = Counter()
    for e in kept:
        kind = e.get("type")
        if kind == "load":
            loads[e["skill"]][e["cause"]] += 1
        elif kind == "hold":
            holds[e["gate"]] += 1
            for item in e.get("items", []):
                items[item["label"]] += 1
        elif kind == "outcome":
            outcomes[e["gate"]][e["outcome"]] += 1
        elif kind == "route":
            routes[e["intensity"] if e["form"] == "route" else e["form"]] += 1
        elif kind == "ref":
            name = f"{e['skill']}/{e['file']}"
            refs[name] += 1
            if e.get("read_tool") and not e.get("partial"):
                whole[name] += 1

    where = []
    if project:
        where.append(f"project `{project}`")
    if adapter:
        where.append(f"adapter `{adapter}`")
    lines = [f"# GOATED usage log{': ' + ', '.join(where) if where else ''}", "",
             f"{len(sessions)} sessions, from "
             + (", ".join(f"`{a}`" for a in sorted({str(a) for a, _ in sessions})) or "none")
             + ".", ""]
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
