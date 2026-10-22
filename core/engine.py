"""OPEN WORLD 2 — orchestrator. Zero third-party Python dependencies / API credits."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import os
from . import sources, markets, intelligence, briefing, forecasts
from .indicators_original import market_stress

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'site'/'data'
ATHENS=ZoneInfo('Europe/Athens')

def load(path,default):
    try: return json.loads(Path(path).read_text(encoding='utf-8'))
    except (ValueError, OSError): return default

def store(path,obj):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    os.replace(tmp,path)

def compute_stress(quotes,now):
    """Strictly follow source formula; no DXY proxy, no stress score from very old quotes."""
    q={item['id']:item for item in quotes}
    def safe(symbol,key='value'):
        m=q.get(symbol,{})
        return m.get(key) if m.get('value') is not None and not m.get('stale') else None
    vix=safe('VIX')
    spx=safe('SP500','change_pct')
    ty=safe('US10Y','change')
    oil=safe('BRENT','change_pct')
    dxy=safe('DXY','change_pct')
    available=sum(v is not None for v in (vix,spx,ty,oil,dxy))
    return {"value":market_stress(vix,spx,ty*100 if ty is not None else None,oil,dxy) if available>=3 else None,
            "coverage":f"{available}/5","experimental":False,
            "method":"PASSO 3: media delle componenti disponibili; soltanto se almeno 3 input verificati e non vecchi",
            "missing":[name for name,value in zip(('VIX','S&P 500','Treasury 10y','Brent','DXY'),(vix,spx,ty,oil,dxy)) if value is None]}

def refresh(now=None, fetcher=None, market_fetcher=None):
    now=now or datetime.now(timezone.utc)
    now=now.astimezone(timezone.utc)
    old=load(DATA/'latest.json',{})
    feed_config=load(ROOT/'config'/'feeds.json',[])
    market_config=load(ROOT/'config'/'markets.json',[])
    fetched, feed_status=sources.collect(feed_config,now,fetcher=fetcher or sources.fetch_bytes)
    enough=sum(1 for h in feed_status if h['ok'])
    if enough:
        fetched_by_id={item['id']:item for item in fetched}
        # Retain recent articles from previous successful runs, not just new feed items.
        for item in old.get('articles',[]):
            if item['id'] not in fetched_by_id:
                clean={key:item[key] for key in ('id','title','summary','url','source','source_type','published_at','language','collected_at') if key in item}
                fetched_by_id[item['id']]=clean
        last_success=now.isoformat().replace('+00:00','Z')
        input_articles=list(fetched_by_id.values())
    else:
        input_articles=old.get('articles',[])
        last_success=old.get('last_news_success')
    articles,topics,clusters,alerts=intelligence.analyse(input_articles,now)
    last_market_fetch=old.get('last_market_fetch')
    elapsed_market=float('inf')
    if last_market_fetch:
        try: elapsed_market=(now-datetime.fromisoformat(last_market_fetch.replace('Z','+00:00'))).total_seconds()/3600
        except ValueError: pass
    market_skip = 0 <= elapsed_market < 4 and len(old.get('markets',[]))==len(market_config)
    raw_quotes=old['markets'] if market_skip else markets.collect_markets(market_config,fetcher=market_fetcher or sources.fetch_bytes,now=now)
    prior_quotes={x['id']:x for x in old.get('markets',[])}
    quotes=[]
    for item in raw_quotes:
        if item['value'] is None and item['id'] in prior_quotes and prior_quotes[item['id']].get('value') is not None:
            prev=prior_quotes[item['id']]
            # Preserve observation date while marking cache status, do not pretend this is new.
            for key in ('value','previous','change','change_pct','observation_date','previous_date','url'):
                item[key]=prev.get(key)
            item['stale']=True
            item['error']='Fonte irraggiungibile: dato in cache, NON aggiornato'
        if market_skip and item.get('observation_date'):
            try:
                item['stale']=item.get('stale',False) or (now.date()-datetime.fromisoformat(item['observation_date']).date()).days>5
            except ValueError: item['stale']=True
        quotes.append(item)
    generated=now.isoformat().replace('+00:00','Z')
    historical=load(DATA/'history.json',[])
    coverage_pct=int(round(100*enough/len(feed_config))) if feed_config else 0
    old_date=old.get('last_news_success')
    payload={
      'version':'2.0.0', 'generated_at':generated,'timezone':'Europe/Athens',
      'last_news_success':last_success,'last_market_fetch':last_market_fetch if market_skip else now.isoformat().replace('+00:00','Z'),'news_unavailable':not bool(enough),
      'articles':articles[:155], 'topics':topics, 'clusters':clusters,
      'alerts':alerts, 'markets':quotes,
      'quality':{'feeds_total':len(feed_config),'feeds_ok':enough,'feeds_failed':len(feed_config)-enough,
                 'source_coverage_pct':coverage_pct,'status':feed_status,
                 'articles_48h':len(articles),'method':'RSS/Atom: titoli e descrizioni; classificazione deterministica, non fact checking indipendente.'},
      'indicators':{
        'market_stress':compute_stress(quotes,now),
        'war_escalation':{'value':None,'note':'Richiede tensioni dei fronti fondate su eventi verificati; n.d. senza analista.'},
        'macro_risk':{'value':None,'note':'Richiede confronti actual/consensus e probabilità dei tassi; n.d. senza dati.'},
        'global_risk':{'value':None,'note':'Richiede escalation, stress e rischio macro; n.d. senza componenti.'}
      },
      'forecasts':forecasts.project(forecasts.read_events(ROOT/'state'/'forecast_events.jsonl'))
    }
    warnings=[]
    if not enough: warnings.append('Tutti i feed irraggiungibili: nessuna notizia recente verificata. Dati precedenti eventualmente in cache.')
    if coverage_pct<60: warnings.append('Copertura fonti ridotta: interpretare la rassegna con prudenza.')
    if not any(m['id']=='GOLD' and m['value'] is not None for m in quotes): warnings.append('Oro live, DXY e futures non collegati: non sostituiti con dati simulati.')
    payload['warnings']=warnings
    store(DATA/'latest.json',payload)
    d=now.astimezone(ATHENS).date().isoformat()
    # Append once per Athenian calendar day after local 08:50; reruns update the same daily brief.
    local=now.astimezone(ATHENS)
    if (local.hour,local.minute)>=(8,50):
        b=briefing.brief_payload(payload)
        store(DATA/'briefs'/f'{d}.json',b)
        (DATA/'briefs'/f'{d}.md').write_text(briefing.brief_markdown(b),encoding='utf-8')
        payload['daily_brief']=f'briefs/{d}.json'
        # Re-save after adding brief path.
        store(DATA/'latest.json',payload)
    by_date={row['date']:row for row in historical if isinstance(row,dict) and 'date' in row}
    old_entry=by_date.get(d,{})
    by_date[d]={
      'date':d,'as_of':generated,'articles':len(articles),
      'sources_ok':enough,'sources_total':len(feed_config),
      'market_stress':payload['indicators']['market_stress']['value'],
      'data_available':bool(enough),
      'first_seen':old_entry.get('first_seen',generated)
    }
    hist=[by_date[k] for k in sorted(by_date)][-400:]
    store(DATA/'history.json',hist)
    return payload
