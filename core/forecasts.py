"""Append-only forecasts journal; immutable initial probability for Brier score."""
from __future__ import annotations
import json
from pathlib import Path

VALID={"Confermata":1,"Smentita":0,"Parziale":None,"Non verificabile":None}


def read_events(path):
    p=Path(path)
    if not p.exists(): return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]

def append_event(path, item):
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("a",encoding="utf-8") as f: f.write(json.dumps(item,ensure_ascii=False,sort_keys=True)+"\n")

def project(events):
    rows={}
    for e in events:
        if e["op"]=="open":
            if e["id"] in rows: raise ValueError(f"ID forecast duplicated: {e['id']}")
            if not 0<=e["probability"]<=1: raise ValueError("Probability outside 0..1")
            rows[e["id"]]={"id":e["id"],"claim":e["claim"],"probability":e["probability"],"date":e["date"],"due":e["due"],"criterion":e["criterion"],"base_value":e["base_value"],"status":"Aperta","revisions":[]}
        elif e["op"]=="revise":
            if e["id"] not in rows: raise ValueError("Revision without forecast")
            rows[e["id"]]["revisions"].append({"at":e["at"],"note":e["note"],"probability_new":e.get("probability_new")})
        elif e["op"]=="resolve":
            if e["id"] not in rows: raise ValueError("Resolution without forecast")
            if e["status"] not in VALID: raise ValueError("Invalid forecast outcome")
            if rows[e["id"]]["status"]!="Aperta": raise ValueError("Forecast already closed")
            rows[e["id"]].update({"status":e["status"],"resolved_at":e["at"],"proof":e["proof"]})
        else: raise ValueError(f"Unknown op: {e['op']}")
    allrows=list(rows.values())
    scored=[(r["probability"]-VALID[r["status"]])**2 for r in allrows if r["status"] in ("Confermata","Smentita")]
    return {"items":allrows,"brier":round(sum(scored)/len(scored),4) if scored else None,"brier_n":len(scored),"open":sum(1 for r in allrows if r["status"]=="Aperta")}
