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
from core.cloud_ai import LLMError
from core.desk_method import build_daily_method
from core import forecasts
from core.forecast_rules import ingest_proposals
from core.original_bridge import save_original
from core.free_data import calculate_conservative_sentiments
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
    if previous.get('status') in ('ok','partial'):
        store(DATA/'ai_status.json',{'status':previous['status'],'date':previous.get('date'),
             'model':previous.get('model'),'agent_audit':previous.get('agent_audit',[]),
             'message':'Briefing IA eseguito e controllato.'})
    if not should_run(local,previous,force):
        # Gli articoli e i prezzi continuano ad aggiornare la dashboard originale ogni ora,
        # mentre il rapporto generativo quotidiano resta immutato fino al prossimo briefing.
        current_ai=previous if previous.get('status') in ('ok','partial') and previous.get('date')==day else None
        payload=dict(latest)
        if current_ai:
            payload['indicators']={**latest.get('indicators',{}),**current_ai.get('indicatori_python',{})}
        payload['sentiments_python']=calculate_conservative_sentiments(payload)
        save_original(payload,current_ai,SITE)
        return {'status':'skipped','message':'Dashboard dati aggiornata; briefing IA già disponibile o non ancora dovuto.'}
    if not os.getenv('GEMINI_API_KEY'):
        if not previous or previous.get('status') in ('not_configured','error'):
            store(DATA/'latest_ai.json',{'status':'not_configured','date':day,'generated_at':local.isoformat(),
                   'message':'Servizio AI cloud non configurato. Aggiungi il secret GEMINI_API_KEY nel repository GitHub.',
                   'provider':'Google Gemini Free API','model':os.getenv('GEMINI_MODEL','gemini-3.5-flash-lite')})
        save_original(latest,previous if previous.get('status') in ('ok','partial') and previous.get('date')==day else None,SITE)
        return {'status':'not_configured','message':'GEMINI_API_KEY mancante; RSS e dashboard originali attivi, NON gli agenti IA.'}
    prior=load(DATA/'ai/history.json',[])
    forecaster=latest.get('forecasts') or {}
    try:
        result=(agent or build_daily_method)(latest,history=prior,forecaster=forecaster,prior_learning=[x.get('learning',{}) for x in prior[-10:]])
    except LLMError as e:
        if previous.get('status') not in ('ok','partial'):
            store(DATA/'latest_ai.json',{'status':'error','date':day,'generated_at':local.isoformat(),
                   'message':str(e),'provider':'Gemini API, quota gratuita'})
        save_original(latest,previous if previous.get('status') in ('ok','partial') and previous.get('date')==day else None,SITE)
        return {'status':'error','message':str(e)}
    # Event-log only, never change the baseline of an existing forecast.
    journal=ROOT/'state/forecast_events.jsonl'
    events=forecasts.read_events(journal)
    proposals=result.get('forecast_proposals_unpublished',[])
    accepted,rejected=ingest_proposals(proposals,events,latest.get('markets',[]),result.get('sources',[]),local.date())
    for event in accepted:forecasts.append_event(journal,event)
    result['forecast_validation']={'accepted_ids':[x['id'] for x in accepted],'rejected':rejected}
    result['date']=day  # data locale di Atene, non UTC, anche per avvio manuale notturno
    if result.get('status') not in ('ok','partial'):
        return {'status':'error','message':'Non ci sono risultati IA pubblicabili.'}
    store(DATA/'ai'/f'{day}.json',result)
    store(DATA/'latest_ai.json',result)
    store(DATA/'ai_status.json',{'status':result['status'],'date':day,
         'model':result.get('model'),'agent_audit':result.get('agent_audit',[]),
         'message':'Briefing IA con sette ruoli generato.'})
    brief_path=DATA/'briefs'/f'{day}_method.md'
    brief_path.parent.mkdir(parents=True,exist_ok=True)
    brief_path.write_text(result.get('brief',{}).get('brief_markdown','n.d.'),encoding='utf-8')
    by_date={x['date']:x for x in prior if isinstance(x,dict) and 'date' in x}
    by_date[day]={'date':day,'generated_at':result['generated_at'],'status':result['status'],
                 'agent_audit':result.get('agent_audit',[]),'learning':result.get('learning',{})}
    store(DATA/'ai/history.json',list(by_date.values())[-365:])
    payload=dict(latest)
    payload['indicators']={**latest.get('indicators',{}),**result.get('indicatori_python',{})}
    payload['forecasts']=forecasts.project(forecasts.read_events(journal))
    payload['sentiments_python']=calculate_conservative_sentiments(payload)
    count=save_original(payload,result,SITE)
    return {'status':result['status'],'agents':len(result.get('agent_audit',[])),'original_rows':count}

if __name__=='__main__':
    forced=('--force' in sys.argv or os.getenv('AI_FORCE','false').lower()=='true')
    report=run(force=forced)
    print('OPEN WORLD V3 AI: '+json.dumps(report,ensure_ascii=False))
