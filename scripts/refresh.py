#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.engine import refresh, load, ROOT
from core.original_bridge import save_original

if __name__=='__main__':
    payload=refresh()
    ai=load(ROOT/"site"/"data"/"latest_ai.json",{})
    # Never present a previous AI analysis as current.
    if ai.get("date") != payload.get("generated_at", "")[:10]:
        ai=None
    save_original(payload,ai,ROOT/"site")
    print(f"OPEN WORLD 2 | feeds {payload['quality']['feeds_ok']}/{payload['quality']['feeds_total']} | articles {len(payload['articles'])} | market figures {sum(v['value'] is not None for v in payload['markets'])}/12")
    if not payload['quality']['feeds_ok']:
        print('WARNING: all news feeds failed; snapshot is explicitly flagged unavailable')
