#!/usr/bin/env python3
"""Hourly news + free, documented, quota-safe data; old dashboard remains untouched."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.engine import refresh, load, store, ROOT
from core.free_data import enrich
from core.original_bridge import save_original

if __name__=='__main__':
    payload=refresh()
    cache_path=ROOT/'site'/'data'/'free_data.json'
    try:
        payload,new_cache=enrich(payload,load(cache_path,{}))
        store(cache_path,new_cache)
        store(ROOT/'site'/'data'/'latest.json',payload)
    except Exception as exc:
        # Never show URLs with keys: report only a safe exception class.
        payload.setdefault('warnings',[]).append('Connettori gratuiti non disponibili: '+type(exc).__name__)
        store(ROOT/'site'/'data'/'latest.json',payload)
    ai=load(ROOT/'site'/'data'/'latest_ai.json',{})
    if ai.get('date') != payload.get('generated_at','')[:10]:ai=None
    save_original(payload,ai,ROOT/'site')
    q=payload.get('free_sources',{}).get('providers',{})
    success=sum(v.get('status') in ('cached','ok') for v in q.values())
    print('OPEN WORLD 3.2 | news',payload['quality']['feeds_ok'],'/',payload['quality']['feeds_total'],
          '| free providers',success,'/',len(q),'| articles',len(payload['articles']))
