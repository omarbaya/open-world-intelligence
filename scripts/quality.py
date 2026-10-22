"""Accountable learning metrics; never confuse reviewer agreement with truth."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"site"/"data"

def read(name,default):
    try: return json.loads((DATA/name).read_text(encoding="utf-8"))
    except (OSError,ValueError): return default

def main():
    ai=read("ai_analysis.json",{})
    daily=ai.get("daily") or {}
    when=daily.get("date")
    if not when or ai.get("status") not in ("ready","partial"): return
    issues=daily.get("verification",{}).get("issues",[])
    evidence=daily.get("evidence",[])
    rows=read("ai_quality.json",[])
    rows=[r for r in rows if r.get("date") != when]
    rows.append({"date":when, "model":ai.get("model"),
        "reviewer_issues":len(issues),
        "sources_referenced":len(evidence),
        "pages_opened":sum(bool(x.get("page_opened")) for x in evidence),
        "note":"Misura la copertura delle prove, non la verità delle notizie."})
    (DATA/"ai_quality.json").write_text(json.dumps(sorted(rows,key=lambda x:x["date"])[-365:],ensure_ascii=False,indent=2),encoding="utf-8")
    print("Quality journal updated",when)

if __name__ == "__main__": main()