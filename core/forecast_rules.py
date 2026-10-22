"""Immutabilità, limiti giornalieri e scoring del registro di previsioni."""
from __future__ import annotations
from datetime import date, datetime, timedelta
import re
from . import forecasts

ID_RE=re.compile(r'^P-\d{8}-\d+$')


def validate_open(event, events, today:date):
    assert event.get('op')=='open', 'Solo apertura nel controllo open'
    assert ID_RE.fullmatch(event.get('id','')), 'ID non valido'
    assert event['date']==today.isoformat(), 'Data non odierna'
    due=date.fromisoformat(event['due'])
    assert due>today, 'Scadenza non futura'
    assert .20<=event['probability']<=.85, 'Probabilità fuori 20–85%'
    for field in ('claim','criterion','base_value','source','reference_time','source_outcome','counts','does_not_count'):
        assert event.get(field) not in (None,''), 'Previsione incompleta: '+field
    projection=forecasts.project(events)
    assert projection['open']<40, 'Troppe aperte'
    assert sum(1 for x in events if x['op']=='open' and x['date']==today.isoformat())<3,'Massimo 3 nuove/giorno'
    assert not any(x['op']=='open' and x['claim'].strip().lower()==event['claim'].strip().lower() for x in events),'Doppione'
    assert not any(x['op']=='open' and x['id']==event['id'] for x in events),'ID già in uso'
    return True


def validate_resolve(event,events,today:date):
    assert event.get('op')=='resolve'
    rec=next((x for x in forecasts.project(events)['items'] if x['id']==event['id']),None)
    assert rec is not None and rec['status']=='Aperta', 'Previsione non aperta'
    assert today>date.fromisoformat(rec['due']), 'Non chiudere il giorno di scadenza'
    assert event.get('proof') and event.get('source'), 'Esito senza prova pubblica'
    assert event['status'] in forecasts.VALID, 'Esito invalido'
    return True


def brier(original_probability,outcome):
    assert .20<=original_probability<=.85
    if outcome not in ('Confermata','Smentita'):return None
    return (original_probability-(1 if outcome=='Confermata' else 0))**2


def ingest_proposals(proposals,previous_events,market_quotes,sources,today:date):
    """Record at most 3 grounded projections, not vague suggestions from the LLM.
    A numerical reference must equal a fresh, real market input; otherwise reject.
    """
    events=list(previous_events)
    accepted=[];rejected=[]
    allowed={x['id'] for x in sources if isinstance(x,dict) and x.get('id')}
    start=sum(e['op']=='open' and e['date']==today.isoformat() for e in events)+1
    quotes=[q for q in market_quotes if isinstance(q.get('value'),(int,float)) and not q.get('stale')]
    for i,p in enumerate((proposals if isinstance(proposals,list) else [])[:3],start):
        if not isinstance(p,dict):continue
        match=next((q for q in quotes if isinstance(p.get('riferimento_valore'),(int,float))
          and abs(q['value']-p['riferimento_valore']) < max(.000001,abs(q['value'])*.000001)
          and q.get('source') and q['source'] in p.get('riferimento_fonte','')),None)
        ids=p.get('source_ids') or []
        if not match or not ids or not all(a in allowed for a in ids):
            rejected.append({'proposal':i,'reason':'Riferimento numerico o fonte non comprovati dagli input'})
            continue
        event={'op':'open','id':f'P-{today.strftime("%Y%m%d")}-{i}',
               'date':today.isoformat(),'claim':str(p.get('evento','')),
               'probability':float(p.get('probabilita',0))/100,
               'due':p.get('scadenza'),'criterion':p.get('criterio'),
               'base_value':str(match['value'])+' '+str(match.get('unit','')),
               'source':match['source'],'reference_time':match.get('observation_date'),
               'source_outcome':p.get('fonte_esito'),
               'counts':p.get('conta'),'does_not_count':p.get('non_conta'),
               'source_ids':ids}
        try:validate_open(event,events,today)
        except (AssertionError,KeyError,TypeError,ValueError) as exc:
            rejected.append({'proposal':i,'reason':str(exc)[:180]});continue
        events.append(event);accepted.append(event)
    return accepted,rejected
