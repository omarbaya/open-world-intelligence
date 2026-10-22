"""Regole deterministiche OPEN WORLD kit: evidenze, date, numeri e indicatori."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse
import json, re
from . import indicators_original as ind

ROOT=Path(__file__).resolve().parents[1]
FONTS=json.loads((ROOT/'config/fonti.yaml').read_text(encoding='utf-8'))
NUMBER=re.compile(r'(?<![\w])\d+(?:[.,]\d+)?(?![\w])')


def datetime_value(value):
    if not isinstance(value,str): return None
    try:
        value=value.replace('Z','+00:00')
        dt=datetime.fromisoformat(value)
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except ValueError: return None


def recent_documents(articles, now, max_age_hours=48):
    """Reject old/undated RSS items as new; original input can still be context."""
    now=now.astimezone(timezone.utc)
    keep=[];excluded=[]
    for item in articles:
        dt=datetime_value(item.get('published_at'))
        if dt and -timedelta(minutes=15)<=(now-dt)<=timedelta(hours=max_age_hours):
            keep.append(item)
        else:
            excluded.append({'id':item.get('id'),'reason':'fuori finestra o data non dimostrata'})
    return keep, excluded


def verify_ids(ids,allowed):
    return [x for x in (ids if isinstance(ids,list) else []) if isinstance(x,str) and x in allowed]


def attribution(article):
    src=article.get('source','')
    if src in FONTS['media_di_stato']:
        return 'Dichiarazione di parte', 'Media statale attribuito a '+FONTS['media_di_stato'][src]
    if src in FONTS['aggregatori']:
        return 'Non verificato','Aggregatore: non conta come seconda testata indipendente'
    if article.get('source_type') in ('official','primary') and src in FONTS['primarie']:
        return 'Fonte primaria','Fonte primaria per dati/atti propri, non per ogni accusa'
    return 'Non verificato','Notizia attribuita alla testata; nessuna corroborazione indipendente automatica'


def contradictory_quotes(quotes, threshold_pct=.5):
    """Compare ONLY same instrument and comparable timestamp; preserve conflicts."""
    out=[]
    for a in quotes:
        for b in quotes:
            if str(a.get('source'))>=str(b.get('source')):continue
            if a.get('id')!=b.get('id') or a.get('instrument')!=b.get('instrument'):continue
            if a.get('observation_date')!=b.get('observation_date'):continue
            v,w=a.get('value'),b.get('value')
            if not isinstance(v,(int,float)) or not isinstance(w,(int,float)) or not max(abs(v),abs(w)):continue
            delta=100*abs(v-w)/max(abs(v),abs(w))
            if delta>threshold_pct:out.append({'id':a['id'],'delta_pct':round(delta,3),'sources':[a['source'],b['source']],'status':'conflitto'})
    return out


def numeric_tokens(text):
    return {m.group().replace(',','.') for m in NUMBER.finditer(str(text))}


def numeric_guard(text, evidence, *, allow=()):
    """Remove unsupported numeric literals rather than fabricate numbers.
    This is an intentionally conservative literal guard; it cannot verify arithmetic.
    """
    allowed=numeric_tokens(evidence)|{str(a) for a in allow}
    errors=[]
    def replace(m):
        token=m.group()
        if token.replace(',','.') in allowed:return token
        errors.append(token)
        return 'n.d.'
    return NUMBER.sub(replace,str(text)),errors


def calculate_indicators(payload,geo=None,macro=None):
    """No estimate when the input is absent; AI never supplies price numbers."""
    existing=payload.get('indicators',{})
    stress=(existing.get('market_stress') or {}).get('value')
    documented={a['id'] for a in payload.get('articles',[]) if 'id' in a}
    tensions={}
    for f in (geo or {}).get('fronti',[]):
        ids=verify_ids(f.get('source_ids',[]),documented)
        n=f.get('tensione')
        # Proposed model number needs at least corroborating independent reporting or a primary fact.
        outlets={next((a.get('source') for a in payload.get('articles',[]) if a.get('id')==k),None) for k in ids}
        outlets.discard(None)
        # A syndicated wire copied by two outlets can still be one source; never claim definitive verification.
        credible=outlets.difference(set(FONTS['aggregatori'])).difference(set(FONTS['media_di_stato']))
        if isinstance(n,int) and not isinstance(n,bool) and 0<=n<=100 and len(credible)>=2:
            tensions[f['id']]=n
    war=ind.war_escalation(tensions)
    # Macro 50 baseline only when a dated primary-series evidence exists; otherwise unknown.
    macro_num=(macro or {}).get('macro_risk_verified')
    macro_score=macro_num if isinstance(macro_num,int) and 0<=macro_num<=100 and (macro or {}).get('primary_source_ids') else None
    global_score=ind.global_risk(war,stress,macro_score) if all(isinstance(v,(int,float)) for v in (war,stress,macro_score)) else None
    missing=sum((m.get('value') is None or m.get('stale',False)) for m in payload.get('markets',[]))
    singles=sum(1 for a in (geo or {}).get('voci',[]) if len(verify_ids(a.get('fonti',[]),documented))<=1)
    conviction=ind.conviction(missing,singles,0)
    return {'global_risk':{'value':global_score,'coverage':'3/3' if global_score is not None else 'incompleto'},
            'market_stress':existing.get('market_stress',{'value':None}),
            'war_escalation':{'value':war,'coverage':len(tensions),'note':'Tensioni IA ammesse soltanto con due evidenze; non prova di indipendenza'},
            'macro_risk':{'value':macro_score,'note':'n.d. senza confronti macro ufficiali e verificati'},
            'conviction':{'value':conviction,'note':'Misura di completezza, NON probabilità di verità','missing_quotes':missing}}
