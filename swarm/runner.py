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
    return ran


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
