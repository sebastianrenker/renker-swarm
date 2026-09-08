"""Implant the swarm's agents into RenkerNet's save files as real in-game avatars.

Reads _rnwork/agent.roster.json + _rnwork/agent.save.json (copied out of the
app's workspace), clones the matching RenkerNet specialist for each swarm agent
(guaranteeing a schema-valid entry), colours it by department, points it at
Gemini, and appends it to both roster.agents and doc.agents. Idempotent: skips
ids already present. Writes the files back in place.

    python tools/rn_implant.py --per 2      # up to 2 new agents per department (test)
    python tools/rn_implant.py --per 9999   # everything
"""
from __future__ import annotations
import copy
import json
import pathlib
import sys
import time
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = ROOT / "_rnwork"
sys.path.insert(0, str(ROOT))
from swarm.runner import load_roster  # noqa: E402

# swarm department -> (RenkerNet specialist template id, avatar colour)
DEPT_MAP = {
    "Kommando":  ("chief",       "#e8a838"),
    "Recherche": ("researcher",  "#4f93ea"),
    "Bau":       ("webdesigner", "#2ad4d4"),
    "Chancen":   ("opportunist", "#3fc96f"),
    "Kunden":    ("support",     "#a36ff2"),
    "Finanzen":  ("treasurer",   "#e0b73e"),
}


def main():
    per = 9999
    if "--per" in sys.argv:
        per = int(sys.argv[sys.argv.index("--per") + 1])

    rn_roster = json.loads((WORK / "agent.roster.json").read_text(encoding="utf-8"))
    rn_save = json.loads((WORK / "agent.save.json").read_text(encoding="utf-8"))
    doc = rn_save["doc"]
    doc_agents = doc["agents"]
    roster_agents = rn_roster["agents"]
    doc_by_id = {a["id"]: a for a in doc_agents}
    ros_by_id = {a["agentId"]: a for a in roster_agents}
    existing = set(doc_by_id) | set(ros_by_id)

    swarm = load_roster()["agents"]
    byd = defaultdict(list)
    for s in swarm:
        byd[s.get("department", "Chancen")].append(s)

    now = int(time.time() * 1000)
    added = 0
    for dept, lst in byd.items():
        spec, color = DEPT_MAP.get(dept, ("opportunist", "#3fc96f"))
        tdoc, tros = doc_by_id.get(spec), ros_by_id.get(spec)
        if not tdoc or not tros:
            continue
        cnt = 0
        for s in lst:
            if cnt >= per:
                break
            nid = "sw_" + s["id"].replace("-", "_")
            if nid in existing:
                continue
            purpose = (s.get("task") or tdoc.get("purpose", "")).strip()[:600]

            nd = copy.deepcopy(tdoc)
            nd["id"] = nid
            nd["name"] = s.get("name", nid)
            nd["color"] = color
            nd["model"] = "gemini-3.6-flash"
            nd["provider"] = "gemini"
            nd["purpose"] = purpose
            if isinstance(nd.get("docs"), dict):
                nd["docs"] = dict(nd["docs"])
                nd["docs"]["purpose"] = purpose
            nd["createdAt"] = now
            doc_agents.append(nd)

            nr = copy.deepcopy(tros)
            nr["agentId"] = nid
            nr["name"] = s.get("name", nid)
            nr["model"] = "gemini-3.6-flash"
            nr["provider"] = "gemini"
            sysp = (s.get("system", "") + "\n\nAUFGABE: " + s.get("task", "")).strip()
            if sysp:
                nr["system"] = sysp[:2000]
            roster_agents.append(nr)

            existing.add(nid)
            added += 1
            cnt += 1

    (WORK / "agent.roster.json").write_text(
        json.dumps(rn_roster, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (WORK / "agent.save.json").write_text(
        json.dumps(rn_save, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"added {added} agents -> doc.agents={len(doc_agents)} roster={len(roster_agents)}")


if __name__ == "__main__":
    main()
