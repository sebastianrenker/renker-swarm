"""build_results.py — erzeugt docs/results.json (VOLLTEXT) fuer die Ergebnis-Seite.
Liest outputs/<dept>/<agent>/<ts>.md, gruppiert nach Abteilung, mit dem kompletten Text.
Wird von run_once.py am Ende aufgerufen (auch von GitHub Actions), kann aber auch allein laufen."""
import json, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"
DOCS = ROOT / "docs"
ORDER = ["Kommando", "Chancen", "Recherche", "Kunden", "Bau", "Finanzen"]


def parse(p: Path):
    raw = p.read_text(encoding="utf-8")
    head, _, body = raw.partition("\n\n")
    title, via = "", "?"
    for line in head.splitlines():
        s = line.strip()
        if s.startswith("#"):
            title = s.lstrip("#").strip()
        elif s.startswith(">") and "via" in s:
            via = s.split("via", 1)[1].strip()
    if not title:
        title = p.parent.name
    return title, via, body.strip()


def build():
    now = datetime.datetime.now().timestamp()
    latest = {}  # (dept,agent) -> file (newest)
    for p in OUT.glob("*/*/*.md"):
        parts = p.relative_to(OUT).parts
        if len(parts) < 3:
            continue
        dept, agent = parts[0], parts[1]
        key = (dept, agent)
        if key not in latest or p.stat().st_mtime > latest[key].stat().st_mtime:
            latest[key] = p

    items = []
    for (dept, agent), p in latest.items():
        title, via, text = parse(p)
        mt = p.stat().st_mtime
        items.append({
            "dept": dept, "agent": agent, "title": title, "via": via,
            "text": text,
            "ts": datetime.datetime.fromtimestamp(mt).strftime("%Y-%m-%d %H:%M"),
            "age_min": int((now - mt) / 60), "_mt": mt,
        })

    # aktiv jetzt = die 8 neuesten
    active = [dict(x) for x in sorted(items, key=lambda x: x["_mt"], reverse=True)[:8]]

    # nach Abteilung gruppieren, innerhalb nach Zeit
    by = {}
    for it in items:
        by.setdefault(it["dept"], []).append(it)
    depts = []
    names = ORDER + sorted(d for d in by if d not in ORDER)
    for d in names:
        if d not in by:
            continue
        lst = sorted(by[d], key=lambda x: x["_mt"], reverse=True)
        for x in lst:
            x.pop("_mt", None)
        depts.append({"id": d, "count": len(lst), "items": lst})
    for x in active:
        x.pop("_mt", None)

    data = {
        "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "total_results": len(items),
        "total_depts": len(depts),
        "active": active,
        "departments": depts,
    }
    DOCS.mkdir(exist_ok=True)
    (DOCS / "results.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(items)


if __name__ == "__main__":
    n = build()
    print(f"results.json geschrieben: {n} Ergebnisse")
