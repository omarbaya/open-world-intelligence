#!/usr/bin/env python3
"""Scheduled Gemini agents. Never exposes GEMINI_API_KEY in repository or site."""
from __future__ import annotations
from pathlib import Path
import json
import os
import sys
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.cloud_ai import build_daily, LLMError
from core.original_bridge import save_original
from core.engine import load,store,ROOT

SITE=ROOT/'site'
DATA=SITE/'data'


def current_athens(now=None):
    return (now or datetime.now(timezone.utc)).astimezone(ZoneInfo('Europe/Athens'))


def should_run(local,existing=None,force=False):
    if not force and (local.hour,local.minute)<(8,50): return False
    if existing and existing.get('date')==local.date().isoformat() and existing.get('status') in ('ok','partial') and not force: return False
    return True


def run(force=False, now=None, agent=None):
    local=current_athens(now)
    day=local.date().isoformat()
    latest=load(DATA/'latest.json',{})
    if not latest.get('articles'):
        return {'status':'skipped','message':'Nessun articolo pubblicato dalle fonti: non creo un briefing fittizio.'}
    previous=load(DATA/'latest_ai.json',{})
    if not should_run(local,previous,force):
        return {'status':'skipped','message':'Non è ancora l’ora del briefing, oppure quello odierno è già stato generato.'}
    if not os.getenv('GEMINI_API_KEY'):
        if not previous or previous.get('status') in ('not_configured','error'):
            store(DATA/'latest_ai.json',{'status':'not_configured','date':day,'generated_at':local.isoformat(),
                   'message':'Servizio AI cloud non configurato. Aggiungi il secret GEMINI_API_KEY nel repository GitHub.',
                   'provider':'Google Gemini Free API','model':os.getenv('GEMINI_MODEL','gemini-3.5-flash-lite')})
        save_original(latest,previous if previous.get('status') in ('ok','partial') else None,SITE)
        return {'status':'not_configured','message':'GEMINI_API_KEY mancante; RSS e dashboard originali attivi, NON gli agenti IA.'}
    prior=load(DATA/'ai/history.json',[])
    forecaster=latest.get('forecasts') or {}
    try:
        result=(agent or build_daily)(latest,history=prior,forecaster=forecaster,prior_learning=[x.get('learning',{}) for x in prior[-7:]])
    except LLMError as e:
        if previous.get('status') not in ('ok','partial'):
            store(DATA/'latest_ai.json',{'status':'error','date':day,'generated_at':local.isoformat(),
                   'message':str(e),'provider':'Gemini API, quota gratuita'})
        save_original(latest,previous if previous.get('status') in ('ok','partial') else None,SITE)
        return {'status':'error','message':str(e)}
    result['date']=day  # data locale di Atene, non UTC, anche per avvio manuale notturno
    if result.get('status') not in ('ok','partial'):
        return {'status':'error','message':'Non ci sono risultati IA pubblicabili.'}
    store(DATA/'ai'/f'{day}.json',result)
    store(DATA/'latest_ai.json',result)
    by_date={x['date']:x for x in prior if isinstance(x,dict) and 'date' in x}
    by_date[day]={'date':day,'generated_at':result['generated_at'],'status':result['status'],
                 'agent_audit':result.get('agent_audit',[]),'learning':result.get('learning',{})}
    store(DATA/'ai/history.json',list(by_date.values())[-365:])
    count=save_original(latest,result,SITE)
    return {'status':result['status'],'agents':len(result.get('agent_audit',[])),'original_rows':count}

if __name__=='__main__':
    forced=('--force' in sys.argv or os.getenv('AI_FORCE','false').lower()=='true')
    report=run(force=forced)
    print('OPEN WORLD V3 AI: '+json.dumps(report,ensure_ascii=False))
