"""OPEN WORLD FREE DATA: independent, rate-budgeted research connectors.

Every field carries provenance; futures are NEVER inferred from proxies.
No key is transmitted to static Pages or saved in any JSON. Best-effort
connectors fail closed, with stale flags and structured provider health.
"""
from __future__ import annotations
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import csv
import io
import json
import os
import re
import zipfile

ATHENS=ZoneInfo('Europe/Athens')
BASE_FC='https://www.financecalendar.com/wp-json/fc/v1/calendar'
BASE_ECB='https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A'
BASE_GOLD='https://api.gold-api.com/price/XAU'
BASE_XAUS='https://xaus.com/api/v1/spot'
BASE_METALS='https://api.metals.dev/v1/latest'
BASE_COT='https://www.cftc.gov/files/dea/history/deacot{year}.zip'
BASE_AV='https://www.alphavantage.co/query'
DEFENSE={ 'NPK':'National Presto', 'DRS':'Leonardo DRS', 'DCO':'Ducommun',
          'CW':'Curtiss-Wright','MOG.A':'Moog','KTOS':'Kratos Defense'}

class SourceFailure(Exception):pass

def http_bytes(url, headers=None, *, timeout=14, limit=9_000_000):
    """Only use approved URL bases; NEVER interpolate secrets into error text."""
    req=Request(url,headers={'User-Agent':'OpenWorldIntelligence/3.2 (research; user-owned project)',
                             'Accept':'application/json, text/csv, application/zip, */*',**(headers or {})})
    try:
        with urlopen(req,timeout=timeout) as res:
            chunk=res.read(limit+1)
            if len(chunk)>limit:raise SourceFailure('payload_too_large')
            return chunk
    except HTTPError as exc:raise SourceFailure(f'http_{exc.code}') from None
    except (TimeoutError,URLError,OSError) as exc:raise SourceFailure(type(exc).__name__) from None

def get_json(url, *, key=None, transport=http_bytes):
    headers={'X-API-Key':key} if key else None
    try:return json.loads(transport(url,headers=headers).decode('utf-8-sig'))
    except (UnicodeDecodeError,json.JSONDecodeError) as exc:raise SourceFailure('invalid_json') from None

def safe_number(v):
    if isinstance(v,bool) or v in (None,'','n.d.'):return None
    try:
        n=float(str(v).replace(',','').strip())
        return n if n==n and abs(n)<1e12 else None
    except (ValueError,TypeError,OverflowError):return None

def timestamp(value):
    if not isinstance(value,str) or not value:return None
    try:
        d=datetime.fromisoformat(value.replace('Z','+00:00'))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except ValueError:return None

def iso_utc(d):return d.astimezone(timezone.utc).isoformat().replace('+00:00','Z')

def cache_valid(cache,part,now,hours):
    d=timestamp((cache.get('fetched_at') or {}).get(part))
    return bool(d and timedelta(0)<=(now-d)<timedelta(hours=hours))

def health(name,status,now, **details):
    return {'name':name,'status':status,'checked_at':iso_utc(now),**details}

def calendar_events(raw, now):
    if not isinstance(raw,dict) or not isinstance(raw.get('events'),list):raise SourceFailure('calendar_schema')
    out=[]
    today=now.astimezone(ATHENS).date();end=today+timedelta(days=30)
    for a in raw['events']:
        if not isinstance(a,dict):continue
        dt=a.get('date','')
        try:d=date.fromisoformat(dt)
        except (ValueError,TypeError):continue
        if not today<=d<=end:continue
        released=timestamp(a.get('release_at_utc') or a.get('time_utc'))
        time_precision=a.get('time_precision')
        at=iso_utc(released) if released and time_precision not in ('day','range','unknown') else None
        local=released.astimezone(ATHENS).strftime('%H:%M') if at else None
        out.append({'id':str(a.get('id') or a.get('series_code') or dt)[:100],
            'date':d.isoformat(),'name':str(a.get('title') or a.get('name') or a.get('series_name') or 'Evento economico')[:180],
            'country':a.get('country'),'impact':a.get('impact'),'state':a.get('status') or 'Da confermare',
            'time_athens':local,'release_at_utc':at,'time_precision':time_precision or 'unknown',
            'actual':a.get('actual'),'consensus':a.get('consensus'),'previous':a.get('prior'),
            'unit':a.get('unit'),'source':a.get('source_name') or 'Finance Calendar',
            'source_url':a.get('source_url') or a.get('url') or 'https://www.financecalendar.com',
            'attribution':'https://www.financecalendar.com'})
    # Keep decision/release events across the full 30-day horizon, rather than
    # filling the dashboard entirely with the earliest low-impact rows.
    high=[x for x in out if x.get('impact')=='high']
    medium=[x for x in out if x.get('impact')=='medium']
    low=[x for x in out if x.get('impact') not in ('high','medium')]
    picked=(high+medium+low)[:100]
    picked.sort(key=lambda x:(x['date'],x['time_athens'] or '99:99',x['id']))
    return picked

def parse_ecb_csv(content,now):
    reader=csv.DictReader(io.StringIO(content.decode('utf-8-sig',errors='replace')))
    observations=[]
    for r in reader:
        try:
            d=date.fromisoformat(r.get('TIME_PERIOD') or '')
            rate=safe_number(r.get('OBS_VALUE'))
            if rate and rate>0 and d<=now.astimezone(ATHENS).date():observations.append((d,rate))
        except ValueError:continue
    observations.sort()
    if not observations:raise SourceFailure('ecb_no_observations')
    day,v=observations[-1]
    previous=observations[-2][1] if len(observations)>1 else None
    out={'id':'EURUSD','name':'EUR/USD fixing BCE','unit':'USD per EUR','type':'fx',
         'source':'BCE · EXR/D.USD.EUR.SP00.A','instrument':'EUR/USD spot reference ECB',
         'value':v,'previous':previous,'change':round(v-previous,6) if previous is not None else None,
         'change_pct':round(100*(v-previous)/previous,4) if previous else None,
         'observation_date':day.isoformat(),'previous_date':observations[-2][0].isoformat() if previous is not None else None,
         'stale':(now.astimezone(ATHENS).date()-day).days>4,'delayed':True,'error':None,
         'url':'https://data.ecb.europa.eu/data/datasets/EXR/EXR.D.USD.EUR.SP00.A',
         'verified_source':'primary','quote_quality':'official_daily_reference'}
    return out

def goldapi_quote(raw,now):
    if not isinstance(raw,dict):raise SourceFailure('goldapi_schema')
    v=safe_number(raw.get('price'))
    d=timestamp(raw.get('updatedAt') or raw.get('updated_at') or raw.get('timestamp'))
    if not v or not 100<v<25000:raise SourceFailure('goldapi_price_invalid')
    return {'source':'Gold API','value':v,'as_of':iso_utc(d) if d else None,'url':'https://gold-api.com/'}

def xaus_quote(raw,now):
    if not isinstance(raw,dict):raise SourceFailure('xaus_schema')
    v=safe_number(raw.get('spot_usd_oz') or (raw.get('xau') or {}).get('price'))
    state=raw.get('data_state') or {}
    if not v or not 100<v<25000:raise SourceFailure('xaus_price_invalid')
    if state.get('status') in ('stale','unavailable','error'):raise SourceFailure('xaus_stale')
    d=timestamp(state.get('as_of') or raw.get('updated_at'))
    return {'source':'XAUS','value':v,'as_of':iso_utc(d) if d else None,'url':'https://xaus.com/api/v1/spot'}

def metals_quote(raw,now):
    if not isinstance(raw,dict) or raw.get('status')!='success':raise SourceFailure('metals_api_status')
    v=safe_number((raw.get('metals') or {}).get('gold'))
    if not v or not 100<v<25000:raise SourceFailure('metals_gold_missing')
    d=timestamp(raw.get('timestamp'))
    return {'source':'Metals.Dev','value':v,'as_of':iso_utc(d) if d else None,'url':'https://metals.dev'}

def compare_gold(quotes,now,previous=None,threshold_pct=.5):
    """Only same instrument and comparable time; no invented market value on conflict."""
    values=[q for q in quotes if safe_number(q.get('value')) is not None]
    recent=[]
    for q in values:
        d=timestamp(q.get('as_of'))
        if d and -timedelta(minutes=5)<=now-d<=timedelta(minutes=90):recent.append((d,q))
    recent.sort(key=lambda x:x[0],reverse=True)
    recent=recent[:3]
    base={'id':'GOLD','name':'Oro XAU/USD spot','unit':'USD/oncia','source':'n.d.','type':'commodity',
        'instrument':'XAU/USD spot, non future COMEX GC', 'value':None,'previous':None,'change':None,
        'change_pct':None,'observation_date':None,'previous_date':None,'stale':True,'delayed':False,
        'error':None,'quotes':values,'url':'https://gold-api.com/','quote_quality':'unavailable'}
    if len(recent)<2:
        base['error']='Meno di due fonti spot aggiornate, prezzo non verificato'
        return base
    vals=[q['value'] for _,q in recent]
    delta=100*(max(vals)-min(vals))/max(vals)
    if delta>threshold_pct:
        base['error']='Conflitto fra due fonti (scostamento oltre 0,5%)'
        base['conflict_pct']=round(delta,3)
        base['quote_quality']='conflict'
        return base
    newest=recent[0][1]
    independent=any(q['source']=='Metals.Dev' for _,q in recent)
    base.update({'value':newest['value'],'stale':not independent,'source':' + '.join(q['source'] for _,q in recent),
        'observation_date':newest['as_of'][:10],'as_of':newest['as_of'],
        'url':newest['url'],'quote_quality':'independently_correlated' if independent else 'indicative_shared_upstream',
        'verification_note':'Due fonti indipendenti' if independent else 'Gold API e XAUS possono condividere lo stesso fornitore a monte: accordo non significa doppia verifica.',
        'difference_pct':round(delta,3)})
    old=previous or {}
    # A spot tick over 24h cannot be labelled a previous exchange close.
    base['previous']=None
    base['change_pct']=None
    return base

def cot_numeric(x):
    return int(float(str(x).replace(',','').replace(' ','')))

def cot_column(row,needle):
    key=next((k for k in row if re.sub('[^a-z0-9]','',k.lower()).startswith(re.sub('[^a-z0-9]','',needle.lower()))),None)
    return row.get(key) if key else None

def parse_cot_zip(content,now):
    """CFTC annual Legacy Futures Only. Noncommercial long-short, NOT TFF leveraged money."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names=[n for n in archive.namelist() if n.lower().endswith(('.txt','.csv'))]
            if not names:raise SourceFailure('cot_no_text')
            raw=archive.read(names[0]).decode('utf-8-sig',errors='replace')
    except (zipfile.BadZipFile,RuntimeError) as ex:raise SourceFailure('cot_zip_invalid') from None
    reader=csv.DictReader(io.StringIO(raw))
    latest={}
    for row in reader:
        name=cot_column(row,'Market_and_Exchange_Names') or ''
        upper=name.upper().strip()
        contract=(cot_column(row,'CFTC Contract Market Code') or '').strip()
        if contract=='088691' and 'GOLD' in upper:code='GC'
        elif contract=='099741' and 'EURO FX' in upper:code='EUR'
        elif contract=='13874A' and upper.startswith('E-MINI S&P 500 -'):code='ES'
        else:continue
        date_text=cot_column(row,'As of Date in Form YYYY-MM-DD') or ''
        try:d=date.fromisoformat(date_text.strip())
        except ValueError:continue
        if d>now.astimezone(ATHENS).date():continue
        try:
            buy=cot_numeric(cot_column(row,'Noncommercial Positions-Long (All)'))
            sell=cot_numeric(cot_column(row,'Noncommercial Positions-Short (All)'))
        except (ValueError,TypeError):continue
        latest.setdefault(code,[]).append((d,buy-sell))
    output={}
    for code,vals in latest.items():
        vals=sorted(set(vals))
        if not vals:continue
        d,value=vals[-1]
        previous=vals[-2][1] if len(vals)>1 else None
        output[code]={'id':code,'date':d.isoformat(),'value':value,'previous':previous,
            'change':value-previous if previous is not None else None,
            'source':'CFTC Legacy Futures Only · Noncommercial net','url':'https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm',
            'unit':'contratti','status':'report settimanale pubblicato; posizioni del martedì'}
    return output

def alpha_daily(raw,symbol,company):
    if not isinstance(raw,dict) or 'Time Series (Daily)' not in raw:raise SourceFailure('alpha_unavailable_free_or_quota')
    rows=raw['Time Series (Daily)']
    if not isinstance(rows,dict):raise SourceFailure('alpha_schema')
    dates=sorted(d for d in rows if re.fullmatch(r'\d{4}-\d{2}-\d{2}',d))
    if not dates:raise SourceFailure('alpha_missing_quotes')
    d=dates[-1]
    item=rows[d]
    close=safe_number(item.get('4. close'))
    if close is None:raise SourceFailure('alpha_close_invalid')
    prev=safe_number(rows[dates[-2]].get('4. close')) if len(dates)>1 else None
    return {'symbol':symbol,'company':company,'date':d,'close':close,'previous':prev,
        'pct':round(100*(close-prev)/prev,4) if prev else None,
        'source':'Alpha Vantage EOD (vendor, non chiusura certificata exchange)',
        'url':'https://www.alphavantage.co/documentation/','status':'daily_vendor','instrument':'azione '+symbol}

def fmp_daily(raw,symbol,company):
    if not isinstance(raw,list) or not raw:raise SourceFailure('fmp_eod_unavailable_on_free')
    valid=[]
    for p in raw:
        if not isinstance(p,dict) or p.get('symbol','').upper()!=symbol.upper():continue
        try:d=date.fromisoformat(p['date'])
        except (KeyError,ValueError,TypeError):continue
        price=safe_number(p.get('close'))
        if price and price>0:valid.append((d,price))
    if not valid:raise SourceFailure('fmp_symbol_or_close_invalid')
    valid.sort()
    prev=valid[-2][1] if len(valid)>1 else None
    return {'symbol':symbol,'company':company,'date':valid[-1][0].isoformat(),
        'close':valid[-1][1],'previous':prev,'pct':round(100*(valid[-1][1]-prev)/prev,4) if prev else None,
        'source':'Financial Modeling Prep · EOD (vendor)',
        'url':'https://site.financialmodelingprep.com','status':'daily_vendor','instrument':'azione '+symbol}

def add_or_replace_markets(markets, new_quotes):
    catalog={q['id']:q for q in markets}
    for q in new_quotes:
        if q and q.get('id') in catalog:
            # Never downgrade an existing fresh verified quote into an unavailable one.
            if q.get('value') is not None or catalog[q['id']].get('value') is None or catalog[q['id']].get('stale'):
                catalog[q['id']]=q
        elif q and q.get('id'):catalog[q['id']]=q
    return [catalog[q['id']] for q in markets]+[q for k,q in catalog.items() if k not in {x['id'] for x in markets}]

def _cached_part(cache,part,now,hours):
    return cache.get(part) if cache_valid(cache,part,now,hours) else None

def enrich(payload, cache=None, now=None, *, transport=http_bytes, environ=None):
    """Resilient idempotent enrichment; returns (payload, persistable_cache)."""
    now=now or datetime.now(timezone.utc)
    env=environ if environ is not None else os.environ
    cache=dict(cache or {})
    checked=dict(cache.get('fetched_at') or {})
    # Migration: re-parse once after a provider-schema release. Previous empty
    # CFTC datasets are not considered successful caches.
    if cache.get('schema_version')!='3.2.1':
        for part in ('cot','calendar'):checked.pop(part,None)
    if not cache.get('cot'):checked.pop('cot',None)
    cache['fetched_at']=checked
    checks={}
    # Four independent keyless feeds, reused according to their publishing cadence.
    def run_cached(part,hours,fn):
        if cache_valid(cache,part,now,hours) and part in cache:
            checks[part]=health(part,'cached',now,last_fetched=checked.get(part))
            return cache[part]
        try:
            res=fn()
            if res is None:raise SourceFailure('empty_response')
            cache[part]=res
            checked[part]=iso_utc(now)
            checks[part]=health(part,'ok',now)
            return res
        except (SourceFailure,ValueError,TypeError,KeyError,OSError) as ex:
            # Only safe error tokens, never put request URLs or auth values into logs.
            reason=ex.args[0] if isinstance(ex,SourceFailure) else type(ex).__name__
            checks[part]=health(part,'error',now,reason=str(reason)[:80],cached=part in cache)
            return cache.get(part)
    def url(base,params):return base+'?'+urlencode(params)
    today=now.astimezone(ATHENS).date()
    cal=run_cached('calendar',6,lambda:calendar_events(get_json(url(BASE_FC,{'from':today.isoformat(),'to':(today+timedelta(days=30)).isoformat(),'country':'US,EU,GB,JP,DE','limit':500,'tz':'Europe/Athens'}),key=env.get('FINANCECALENDAR_API_KEY'),transport=transport),now))
    ecb=run_cached('ecb',6,lambda:parse_ecb_csv(transport(url(BASE_ECB,{'format':'csvdata','lastNObservations':3}),timeout=26),now))
    ga=run_cached('gold_api',1,lambda:goldapi_quote(get_json(BASE_GOLD,transport=transport),now))
    xb=run_cached('xaus',1,lambda:xaus_quote(get_json(BASE_XAUS,transport=transport),now))
    # A monthly-free optional third quote, one call per day (<100/month).
    metal=None
    if env.get('METALS_DEV_API_KEY'):
        metal=run_cached('metals_dev',25,lambda:metals_quote(get_json(url(BASE_METALS,{'api_key':env['METALS_DEV_API_KEY'],'currency':'USD','unit':'toz'}),transport=transport),now))
    # 2026 file rotates yearly; CFTC cache refreshed after Friday publication.
    cot=run_cached('cot',27,lambda:parse_cot_zip(transport(BASE_COT.format(year=today.year),timeout=30,limit=12_000_000),now))
    defense={}
    if env.get('ALPHAVANTAGE_API_KEY'):
        for symbol,company in DEFENSE.items():
            # 6 requests per ~26 hours, safely under 25/day (IA unverified symbol excluded).
            part='defense_'+symbol.replace('.','_')
            def fetch_alpha(sym=symbol,comp=company):
                api=url(BASE_AV,{'function':'TIME_SERIES_DAILY','symbol':sym,'outputsize':'compact','apikey':env['ALPHAVANTAGE_API_KEY']})
                return alpha_daily(get_json(api,transport=transport),sym,comp)
            defense[symbol]=run_cached(part,26,fetch_alpha)
    elif env.get('FMP_API_KEY') and env.get('FMP_PUBLIC_DISPLAY_LICENSED','').lower()=='true':
        for symbol,company in DEFENSE.items():
            part='fmp_defense_'+symbol.replace('.','_')
            def fetch_fmp(sym=symbol,comp=company):
                start=(today-timedelta(days=15)).isoformat()
                path=url('https://financialmodelingprep.com/stable/historical-price-eod/full',
                    {'symbol':sym,'from':start,'to':today.isoformat(),'apikey':env['FMP_API_KEY']})
                return fmp_daily(get_json(path,transport=transport),sym,comp)
            defense[symbol]=run_cached(part,26,fetch_fmp)
    else:
        defense=cache.get('defense',{})
    cache['defense']=defense
    xaus_levels=run_cached('gold_levels',12,lambda:parse_xaus_history(
        get_json('https://xaus.com/api/v1/history',transport=transport),now))
    fx_levels=None
    if env.get('ALPHAVANTAGE_API_KEY'):
        def fx_fetch():
            path=url(BASE_AV,{'function':'FX_DAILY','from_symbol':'EUR','to_symbol':'USD',
                'outputsize':'compact','apikey':env['ALPHAVANTAGE_API_KEY']})
            return parse_alpha_fx_levels(get_json(path,transport=transport),now)
        fx_levels=run_cached('fx_levels',26,fx_fetch)
    else:
        fx_levels=cache.get('fx_levels')
    cache['fetched_at']=checked
    cache['last_refresh']=iso_utc(now)
    cache['schema_version']='3.2.1'
    cache['provider_health']=checks
    payload=dict(payload)
    payload['calendar']=cal or []
    payload['cot']=cot or {}
    payload['defense_eod']=defense
    payload['levels']={'GC':xaus_levels,'6E':fx_levels,'ES':None}
    candidates=[x for x in (ga,xb,metal) if isinstance(x,dict)]
    gold=compare_gold(candidates,now)
    payload['markets']=add_or_replace_markets(payload.get('markets',[]),[ecb,gold])
    payload['free_sources']={'providers':checks,'attribution':{'Finance Calendar':'https://www.financecalendar.com'},
        'market_conflicts':{'GOLD':gold.get('error')} if gold.get('error') else {},
        'key_status':{k:'configured' if env.get(k) else 'optional_not_configured' for k in ('FINANCECALENDAR_API_KEY','METALS_DEV_API_KEY','ALPHAVANTAGE_API_KEY','FMP_API_KEY','FRED_API_KEY')},
        'timestamp':iso_utc(now),'notice':'Futures exchange real-time CME are not supplied; no proxies are labelled futures.'}
    if not isinstance(payload.get('warnings'),list):payload['warnings']=[]
    if gold.get('value') is None:payload['warnings'].append('Oro spot non verificato da due feed temporalmente comparabili: n.d.')
    elif gold.get('stale'):payload['warnings'].append('Oro XAU/USD indicativo da feed potenzialmente correlati: non usato nei calcoli di rischio.')
    # Engine's stress must be recomputed after refreshing any quote, not copied from prior FRED state.
    from .engine import compute_stress
    payload.setdefault('indicators',{})['market_stress']=compute_stress(payload['markets'],now)
    payload['sentiments_python']=calculate_conservative_sentiments(payload)
    return payload,cache

# OHLC reference levels. Each market names its own underlying instrument;
# a cash index/spot series MUST NOT be labelled a CME futures contract.
def levels_from_daily_bars(points, *, instrument, source, source_url, now):
    today=now.astimezone(ATHENS).date()
    clean=[]
    for x in points if isinstance(points,list) else []:
        if not isinstance(x,dict):continue
        ds=x.get('d') or x.get('date')
        try:d=date.fromisoformat(str(ds)[:10])
        except (TypeError,ValueError):continue
        c=safe_number(x.get('c',x.get('close')))
        hi=safe_number(x.get('h',x.get('high')))
        lo=safe_number(x.get('l',x.get('low')))
        # Exclude current forming bar; no partial day as 'previous close'.
        if d>=today or any(v is None for v in (c,hi,lo)) or not (lo<=c<=hi):continue
        clean.append((d,c,hi,lo))
    clean.sort(key=lambda x:x[0])
    if not clean:raise SourceFailure('ohlc_no_closed_sessions')
    previous=clean[-1]
    week_start=previous[0]-timedelta(days=previous[0].weekday())
    week=[x for x in clean if week_start<=x[0]<=previous[0]]
    if not week:week=[previous]
    return {'instrument':instrument,'h':previous[2],'l':previous[3],'c':previous[1],
            'wh':max(x[2] for x in week),'wl':min(x[3] for x in week),
            'day':previous[0].isoformat(),'week_start':week_start.isoformat(),
            'source':source,'source_url':source_url,'status':'reference_cash_or_spot_not_future',
            'session_rule':'Ultima sessione COMPLETATA; settimanale dall’inizio della settimana della sessione'}

def parse_xaus_history(raw,now):
    if not isinstance(raw,dict) or not isinstance(raw.get('points'),list):raise SourceFailure('xaus_history_schema')
    return levels_from_daily_bars(raw['points'],instrument='XAU/USD spot',source='XAUS daily candles',
                source_url='https://xaus.com/api/',now=now)

def parse_alpha_fx_levels(raw,now):
    if not isinstance(raw,dict) or not isinstance(raw.get('Time Series FX (Daily)'),dict):raise SourceFailure('alpha_fx_unavailable')
    candles=[{'d':d,'h':r.get('2. high'),'l':r.get('3. low'),'c':r.get('4. close')}
             for d,r in raw['Time Series FX (Daily)'].items()]
    return levels_from_daily_bars(candles,instrument='EUR/USD spot (vendor FX)',
                  source='Alpha Vantage FX_DAILY',source_url='https://www.alphavantage.co/documentation/',now=now)

def calculate_conservative_sentiments(payload):
    """Use exact source formulas only when required components exist; never fill missing with zero."""
    from .indicators_original import sentiments,clamp
    m={x['id']:x for x in payload.get('markets',[])}
    def pct(k):
        x=m.get(k,{})
        return x.get('change_pct') if not x.get('stale') and isinstance(x.get('change_pct'),(int,float)) else None
    w=((payload.get('indicators') or {}).get('war_escalation') or {}).get('value')
    out={k:None for k in ('global','riskon','equity','gold','eurusd','oil','war')}
    rationale={k:'Componenti necessarie mancanti' for k in out}
    if isinstance(w,(int,float)):
        out['war']=clamp((w-50)*2)
        rationale['war']='Escalation deterministica da tensioni corroborate; NON probabilità'
    # These full expressions require futures, Nikkei and rate-tone evidence.
    # No partial number disguised as canonical Claude sentiment.
    inputs=(pct('SP500'),pct('ES'),pct('NKY'),pct('VIX'),pct('GOLD'),pct('DXY'),pct('EURUSD'),pct('BRENT'))
    if all(v is not None for v in inputs) and isinstance(w,(int,float)):
        q=m.get('US10Y',{})
        change=q.get('change') if not q.get('stale') else None
        ecb=payload.get('ecb_tone_verified')
        fed=payload.get('fed_tone_verified')
        oil=payload.get('oil_supply_verified')
        if change is not None and ecb in (-1,0,1) and fed in (-1,0,1) and oil in ('attacchi','minacce','piu_offerta','nessuno'):
            out=sentiments(*inputs[:5],-1 if inputs[5]<0 else 1 if inputs[5]>0 else 0,
                -1 if change<0 else 1 if change>0 else 0,w,
                inputs[6],ecb,fed,inputs[7],None if oil=='nessuno' else oil)
            rationale={k:'Formula completa Claude; componenti verificate' for k in out}
    return {'values':out,'notes':rationale,'strict':True}
