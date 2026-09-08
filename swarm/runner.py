"""The scheduler + runner: pick the agents that are due, run a capped batch
through the provider rotation, save their output, and never exceed the daily
call budget. State (last-run times + today's call count) lives in state/.
"""
from __future__ import annotations
import datetime
import json
import pathlib
import time

import yaml

from .providers import Router

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE = ROOT / "state" / "state.json"
OUT = ROOT / "outputs"


def _load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_roster():
    """roster.yaml plus, if present, roster.generated.yaml (from expand_roster).
    Their `agents` lists are concatenated so a hand-written core and a generated
    bulk roster coexist. Later duplicates of the same id are dropped.
    """
    roster = _load_yaml(ROOT / "roster.yaml") or {}
    agents = list(roster.get("agents", []))
    gen = ROOT / "roster.generated.yaml"
    if gen.exists():
        agents += (_load_yaml(gen) or {}).get("agents", [])
    seen, merged = set(), []
    for a in agents:
        if a["id"] in seen:
            continue
        seen.add(a["id"])
        merged.append(a)
    roster["agents"] = merged
    return roster


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"day": "", "calls_today": 0, "last_run": {}}


def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def due_agents(roster, state, now):
    defaults = roster.get("defaults", {})
    due = []
    for a in roster.get("agents", []):
        interval = a.get("interval_minutes", defaults.get("interval_minutes", 120)) * 60
        last = state["last_run"].get(a["id"], 0)
        if now - last >= interval:
            due.append(a)
    # oldest-waiting first, so a big roster rotates fairly
    due.sort(key=lambda a: state["last_run"].get(a["id"], 0))
    return due


def run_cycle(verbose=True):
    cfg = _load_yaml(ROOT / "config.yaml")
    roster = load_roster()
    state = load_state()

    today = datetime.date.today().isoformat()
    if state.get("day") != today:
        state["day"] = today
        state["calls_today"] = 0

    budget = cfg.get("daily_call_budget", 800)
    if state["calls_today"] >= budget:
        if verbose:
            print(f"[budget] daily cap {budget} reached — resting until tomorrow.")
        save_state(state)
        return 0

    router = Router(cfg.get("providers", {}))
    if not router.available():
        if verbose:
            print("[providers] none available — no keys set (or all cooling). "
                  "Add GEMINI_API_KEY / GROQ_API_KEY / ... to activate the swarm.")
        return 0

    now = time.time()
    due = due_agents(roster, state, now)
    cap = cfg.get("max_agents_per_cycle", 6)
    batch = due[:cap]
    if verbose:
        print(f"[cycle] {len(due)} due, running {len(batch)} "
              f"(budget {state['calls_today']}/{budget}, providers {router.available()})")

    ran = 0
    for a in batch:
        if state["calls_today"] >= budget:
            break
        system = a.get("system", "Du bist ein praeziser, ehrlicher Arbeits-Agent.")
        task = a.get("task", "")
        # cross-run memory: let the agent build on its own last result instead of repeating
        prev = OUT / f"{a['id']}-latest.md"
        if prev.exists():
            body = prev.read_text(encoding="utf-8").split("\n\n", 1)[-1].strip()
            if body:
                task += ("\n\nDEIN LETZTES ERGEBNIS (baue darauf auf oder liefere klar etwas "
                         "Neues — wiederhole dich nicht):\n" + body[:600])
        text, prov = router.call(
            system, task, timeout=cfg.get("request_timeout_seconds", 60))
        if not text:
            # leave last_run untouched so this agent retries next cycle
            if verbose:
                print(f"  x {a['id']}: {prov}")
            continue
        _write_output(a, text, prov)
        state["last_run"][a["id"]] = time.time()
        state["calls_today"] += 1
        ran += 1
        if verbose:
            print(f"  + {a['id']} via {prov} ({len(text)} chars)")

    save_state(state)
    write_dashboard_data(roster, state, cfg)
    return ran


def write_dashboard_data(roster, state, cfg):
    """Emit docs/data.json — the live digest the GitHub Pages "station" fetches
    to render every agent as an avatar in its department room, with real output."""
    now = time.time()
    files = sorted(OUT.glob("*/*/*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    latest_by_agent, latest_by_dept, recent = {}, {}, []
    for p in files:
        parts = p.relative_to(OUT).parts  # <dept>/<agent>/<ts>.md
        if len(parts) < 3:
            continue
        dept, agent = parts[0], parts[1]
        raw = p.read_text(encoding="utf-8")
        head, _, body = raw.partition("\n\n")
        via = "?"
        for line in head.splitlines():
            if line.startswith(">") and "via" in line:
                via = line.split("via", 1)[1].strip()
        item = {
            "dept": dept, "agent": agent, "via": via,
            "text": " ".join(body.split())[:360],
            "ts": datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            "age_min": int((now - p.stat().st_mtime) / 60),
        }
        latest_by_agent.setdefault(agent, item)
        latest_by_dept.setdefault(dept, item)
        if len(recent) < 12:
            recent.append(item)

    defaults = roster.get("defaults", {})
    depts = {}
    agents = []
    for a in roster.get("agents", []):
        d = a.get("department", "Allgemein")
        depts.setdefault(d, {"id": d, "count": 0, "latest": None})
        depts[d]["count"] += 1
        lb = latest_by_agent.get(a["id"])
        agents.append({
            "id": a["id"], "name": a.get("name", a["id"]), "dept": d,
            "iv": a.get("interval_minutes", defaults.get("interval_minutes", 120)),
            "out": (lb["text"][:220] if lb else None),
            "via": (lb["via"] if lb else None),
            "age_min": (lb["age_min"] if lb else None),
        })
    for d in depts.values():
        lb = latest_by_dept.get(d["id"])
        if lb:
            d["latest"] = {"via": lb["via"], "text": lb["text"], "age_min": lb["age_min"]}

    data = {
        "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "agents_total": len(agents),
        "worked": sum(1 for a in agents if a["out"]),
        "departments": list(depts.values()),
        "agents": agents,
        "budget": {"used": state.get("calls_today", 0), "cap": cfg.get("daily_call_budget", 600)},
        "recent": recent,
    }
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "data.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # human-readable board (Memory surface) — latest result per department
    board = ["# Renker Swarm — Board", "",
             f"Stand: {data['updated']} · {data['agents_total']} Agenten · "
             f"{data['worked']} mit Ergebnis · Budget {data['budget']['used']}/{data['budget']['cap']}", ""]
    for d in data["departments"]:
        board.append(f"## {d['id']} — {d['count']} Agenten")
        lb = d.get("latest")
        board.append(f"- {lb['text']}  _(via {lb['via']}, vor {lb['age_min']} min)_" if lb
                     else "- _(noch kein Ergebnis — laeuft im naechsten Zyklus)_")
        board.append("")
    OUT.mkdir(exist_ok=True)
    (OUT / "INDEX.md").write_text("\n".join(board), encoding="utf-8")


def _write_output(a, text, provider):
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    dept = a.get("department", "Allgemein")
    folder = OUT / dept / a["id"]
    folder.mkdir(parents=True, exist_ok=True)
    header = (f"# {a.get('name', a['id'])}  ·  {dept}\n"
              f"> {ts} · via {provider}\n\n")
    body = header + text.rstrip() + "\n"
    (folder / f"{ts}.md").write_text(body, encoding="utf-8")
    (OUT / f"{a['id']}-latest.md").write_text(body, encoding="utf-8")
