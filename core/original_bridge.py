"""Translate OPEN WORLD V3 feed+AI into the immutable Claude dashboard's 26-field schema.
The ORIGINAL HTML/CSS/JS is never changed; only original/data/oggi.json and storico.json.
Missing evidence remains null or n.d.; 2026-10-20 export is never mislabelled as live.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import re

FIELDS=('section','id','order','title','category','value','prev','change','change_unit','unit','label','level','score','text','detail','extra','levels','catalysts','invalidation','status','time','source','url','lat','lon','horizon')
FRONTS={
 'gulf':('Hormuz e Golfo',26.5,56.3,'Golfo e Mar Rosso'),
 'yemen':('Yemen e Arabia Saudita',15.4,44.2,'Golfo e Mar Rosso'),
 'ru-ua':('Russia–Ucraina',49,32,'Russia–Ucraina'),
 'me':('Israele, Iran e Libano',33,35,'Medio Oriente'),
 'tw':('Cina–Taiwan',24,121,'Cina–Taiwan')}

def row(section,id,**kw):
    x={k:None for k in FIELDS};x.update({'section':section,'id':str(id)});
    for k,v in kw.items():
        if k not in FIELDS: raise ValueError('Unknown field '+k)
        x[k]=v
    return x

def ai_sources(ai):
    all_sources={x['id']:x for x in (ai or {}).get('sources',[])}
    claims=[]
    for part in (ai or {}).get('research',{}).values():
        for i in part.get('items',[]):
            src=all_sources.get(i['id']);
            if src: claims.append((i,src))
    return claims

def build_rows(payload,ai=None):
    stamp=payload.get('generated_at') or datetime.now(ZoneInfo('Europe/Athens')).isoformat()
    loc=datetime.fromisoformat(stamp.replace('Z','+00:00')).astimezone(ZoneInfo('Europe/Athens'))
    date=loc.date().isoformat()
    title='Brief di '+loc.strftime('%A %d %B %Y')
    short=(ai or {}).get('brief',{}).get('sintesi_60s') or []
    if not isinstance(short,list): short=[]
    summary='\n'.join(str(x) for x in short[:3]) if short else 'IA non configurata: aggiornamenti delle fonti disponibili; analisi e spiegazioni non ancora attive.'
    if payload.get('news_unavailable'):
        summary='ATTENZIONE: nessuna nuova raccolta RSS riuscita. Dati precedenti in cache.\n'+summary
    rows=[row('header','main',title=title,category=date,time=loc.strftime('%d/%m/%Y, %H:%M ora di Atene'),
              text=summary,detail='ultime 48 ore · ultimi dati FRED ritardati')]
    indicators=payload.get('indicators',{})
    for n,(key,title) in enumerate([('global_risk','Rischio globale'),('market_stress','Stress di mercato'),('war_escalation','Escalation guerre'),('conviction','Convinzione dell’agente')],1):
        item=indicators.get(key) or {}
        value=item.get('value')
        rows.append(row('gauge',key,order=n,title=title,value=value if isinstance(value,(int,float)) else None,
          label='n.d.' if value is None else 'Calcolato da Python',detail='Indicatore disponibile solo con sufficienti dati verificati.',
          text=str(item.get('method') or item.get('note') or 'n.d.'),extra='Nessun punteggio inventato.'))
    research=(ai or {}).get('research',{})
    for i,(claim,source) in enumerate(ai_sources(ai)[:10],1):
        role=next((k for k,x in research.items() if claim in x.get('items',[])),'geopolitica')
        category={'macro':'Macro','difesa':'Difesa','geopolitica':'Guerre'}.get(role,'Politica')
        rows.append(row('snapshot',f'live-{i}',order=i,title=claim.get('traduzione') or source.get('title'),category=category,
            level='Media',text=claim.get('fatto')+' Perché conta: '+claim.get('perche_conta',''),
            detail=claim.get('mercati'),status='Non verificato indipendentemente',time=source.get('published_at'),
            source=source.get('publisher'),url=source.get('url')))
    if not any(r['section']=='snapshot' for r in rows):
        for i,a in enumerate(payload.get('articles',[])[:8],1):
            rows.append(row('snapshot',f'feed-{i}',order=i,title=a.get('title'),category=(a.get('topics') or ['News'])[0],
                level='Media',text='Titolo RSS pubblicato da '+a.get('source','n.d.')+'. Analisi IA non disponibile.',
                detail='n.d.',status='Non verificato',time=a.get('published_at'),source=a.get('source'),url=a.get('url')))
    front_scores=(payload.get('indicators',{}).get('war_escalation') or {}).get('front_scores') or {}
    for i,(key,(name,lat,lon,topic)) in enumerate(FRONTS.items(),1):
        topic_articles=[a for a in payload.get('articles',[]) if topic in a.get('topics',[])][:2]
        summary='; '.join(a['title'] for a in topic_articles) if topic_articles else 'Nessun fatto nuovo verificato.'
        score=front_scores.get(key)
        if not (isinstance(score,int) and not isinstance(score,bool) and 0<=score<=100):score=None
        rows.append(row('front',key,order=i,title=name,lat=lat,lon=lon,value=score,prev=None,
            label='Stima IA corroborata (non prova definitiva)' if score is not None else 'n.d.',
            text=summary,detail='Tensione stimata sulla base di almeno due testate distinte; indipendenza non dimostrata.' if score is not None else 'Tensione non stimabile senza prove sufficienti.',
            extra='Effetto sui mercati: scenario condizionale, non segnale operativo.',status='Interpretazione IA' if score is not None else 'Non verificato'))
    market_map={'ES':'SP500','GC':'GOLD','EURUSD':'EURUSD','DXY':'DXY','VIX':'VIX','US2Y':'US2Y','US10Y':'US10Y','BRENT':'BRENT','WTI':'WTI','TTF':'TTF'}
    proxy_titles={'ES':'S&P 500 cash · NON ES/MES futures','GC':'Oro XAU/USD spot · NON GC/MGC futures'}
    mk={x['id']:x for x in payload.get('markets',[])}
    for i,(id,symbol) in enumerate(market_map.items(),1):
        q=mk.get(symbol,{})
        value=q.get('value')
        is_gld=q.get('id')=='GOLD'
        quality=q.get('quote_quality')
        text_note=(q.get('verification_note') or q.get('error') or
          ('Dato spot indicativo, non future GC/MGC.' if is_gld else
           'Indice S&P 500 cash, non contratto ES/MES.' if id=='ES' else
           'Osservazione datata; non quotazione real-time.'))
        rows.append(row('market',id,order=i,title=proxy_titles.get(id,q.get('name') or id),category=id,unit=q.get('unit',''),
            value=value,prev=q.get('previous'),change=q.get('change_pct'),change_unit='%',
            label=('Indicativo, non indipendente' if quality=='indicative_shared_upstream' else
                   'Ritardato' if value is not None and (q.get('stale') or q.get('delayed')) else
                   'Dato indicativo' if value is not None else 'n.d.'),
            level='Medio',text=text_note,detail='Nessuna causa di mercato attribuita senza fonte primaria.',
            extra='Strumento spot / cash distinto dal future' if id in ('ES','GC') else
                  'Dato ritardato' if q.get('stale') else 'Data di osservazione disponibile.',
            time=q.get('as_of') or q.get('observation_date') or 'n.d.',
            source=q.get('source','n.d.'),url=q.get('url'))) 
    # Preserve every original UI module with blank/no-evidence states rather than old facts.
    lesson=(ai or {}).get('learning',{}).get('lezione',{})
    rows.append(row('lesson','main',title=lesson.get('titolo') or 'Una notizia non è una prova',
        category=lesson.get('area') or 'Strumenti',level=lesson.get('livello') or 'Base',
        text=lesson.get('spiegazione') or 'Una notizia RSS da sola non è una verifica indipendente.',
        detail=lesson.get('esempio_oggi') or 'n.d.',extra=lesson.get('domanda') or 'Le prove disponibili bastano?',
        catalysts=lesson.get('risposta') or 'n.d.'))
    leanings=(ai or {}).get('brief',{}).get('inclinazione',{}) or {}
    for i,(instrument,description) in enumerate([('ES','S&P 500 · ES / MES'),('GC','Oro · GC / MGC'),('6E','Euro · 6E / M6E')],1):
        proposal=leanings.get(instrument,{}) if isinstance(leanings,dict) else {}
        score=proposal.get('rilevanza')
        if not isinstance(score,int) or isinstance(score,bool) or not 0<=score<=10:score=None
        label=proposal.get('studio')
        if label not in ('Rialzista','Neutrale','Ribassista'):label='n.d.'
        rows.append(row('trading',instrument,order=i,title=description,category='Interpretazione IA · solo studio',
            score=score,label=label,level='Lettura IA',text=str(proposal.get('motivi') or 'n.d.; servono più dati aggiornati.'),
            detail=str(proposal.get('rischio') or 'Scenario non validato sui mercati.')+' Non è un segnale operativo.',
            levels='Non verificati',invalidation=str(proposal.get('invalidazione') or 'n.d.')))
    level_titles={'ES':'S&P 500 cash · riferimento, NON ES/MES future',
                  'GC':'Oro spot XAU/USD · riferimento, NON GC/MGC future',
                  '6E':'Cambio EUR/USD spot · riferimento, NON 6E/M6E future'}
    free_levels=payload.get('levels') or {}
    for sym,t in level_titles.items():
        entry=free_levels.get(sym) or {}
        for i,(suffix,label,kind) in enumerate([('h','Massimo di ieri','high'),('l','Minimo di ieri','low'),('c','Chiusura di ieri','close'),('wh','Massimo della settimana','wkhigh'),('wl','Minimo della settimana','wklow')],1):
            price=entry.get(suffix)
            rows.append(row('level',sym+'-'+suffix,order=i,title=t,category=sym,value=price,
              label=label,status=kind,unit='USD' if sym=='GC' else '',
              detail=entry.get('instrument') or 'n.d.; fonte OHLC non collegata',
              time=entry.get('day') or 'n.d.',source=entry.get('source') or 'Non verificato',
              url=entry.get('source_url')))
    cot_data=payload.get('cot') or {}
    for i,(k,v) in enumerate([('GC','Oro (COMEX)'),('EUR','Euro (CME)'),('ES','E-mini S&P 500 (CME)')],1):
        cot=cot_data.get(k) or {}
        rows.append(row('cot',k,order=i,title=v,value=cot.get('value'),prev=cot.get('previous'),
          change=cot.get('change'),change_unit='contratti',label='Legacy Futures Only · non-commerciali' if cot else 'n.d.',
          detail='Net = long - short; dato del martedì, pubblicato venerdì' if cot else
                 'Report CFTC non disponibile nel momento del controllo',
          time=cot.get('date') or 'n.d.',source=cot.get('source') or 'CFTC',url=cot.get('url') or
          'https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm'))
    # Sections designed to remain honest when data is missing.
    brief=(ai or {}).get('brief',{})
    def article_section(section,field,title):
        text=brief.get(field) or 'n.d. Nessuna analisi IA pubblicata per questo giorno.'
        if isinstance(text,(dict,list)): text=json.dumps(text,ensure_ascii=False)
        rows.append(row(section,section+'-1',order=1,title=title,text=str(text)[:1500]))
    article_section('warning','limiti','Avvertenze e limiti dei dati')
    article_section('scenario','scenari_7_30_90','Scenari condizionali 7–30–90 giorni')
    article_section('change','valutazione_finale','Cosa cambia e perché')
    # A model can propose forces, but Python admits only the discrete -1/0/+1 scheme.
    force_proposals=(ai or {}).get('brief',{}).get('mappa_forze',[]) or []
    validated=[]
    for item in force_proposals if isinstance(force_proposals,list) else []:
        if not isinstance(item,dict):continue
        if all(isinstance(item.get(asset),list) and len(item[asset])==3
               and isinstance(item[asset][0],int) and not isinstance(item[asset][0],bool)
               and item[asset][0] in (-1,0,1) and item[asset][1] in ('Forte','Debole')
               for asset in ('oro','eur','sp')):
            validated.append(item)
    if validated:
        for j,item in enumerate(validated[:5],1):
            for suffix,label,asset in (('oro','Oro','oro'),('eur','EUR/USD','eur'),('sp','S&P 500','sp')):
                degree,weight,why=item[asset]
                rows.append(row('force',f'forza{j}-{suffix}',order=j,title=str(item.get('forza','Forza')),category=label,
                    value=degree,level=weight,text=str(item.get('fatto','n.d.'))[:800],
                    detail=str(why)[:700],status='Lettura IA (non segnale di trading)'))
    else:
        for j,name in enumerate(('Geopolitica','Inflazione','Banche centrali'),1):
            for x,label in enumerate(('Oro','EUR/USD','S&P 500'),1):
                rows.append(row('force',f'{j}-{x}',order=j,title=name,category=label,value=0,level='Debole',
                    text='Direzione non stimabile senza input verificati.',detail='Matrice informativa, non segnale di trading.'))
    sentiment=payload.get('sentiments_python') or {}
    sentiment_values=sentiment.get('values') or {}
    sentiment_notes=sentiment.get('notes') or {}
    for n,(key,name) in enumerate((('global','Globale'),('riskon','Risk-on'),('equity','Azioni'),('gold','Oro'),('eurusd','EUR/USD'),('oil','Petrolio'),('war','Guerre')),1):
        value=sentiment_values.get(key)
        rows.append(row('sentiment',key,order=n,title='Sentiment '+name,value=value,
           label='Formula Python verificata' if isinstance(value,(int,float)) else 'n.d.',
           text=sentiment_notes.get(key,'Componenti insufficienti'),
           detail='Solo ricerca, mai un segnale di ingresso/uscita'))
    for i,a in enumerate(payload.get('articles',[])[:28],1):
        rows.append(row('source','src'+str(i),order=i,title=a.get('source','')+' — '+a.get('title',''),category=(a.get('topics') or ['News'])[0],url=a.get('url')))
    for i,(term,description) in enumerate([('CPI','Indice dei prezzi al consumo'),('PPI','Prezzi all’ingrosso'),('DXY','Indice del dollaro USA'),('VIX','Volatilità implicita dell’S&P 500'),('Tassi','Costo del denaro'),('Rendimento','Interesse percentuale di un titolo'),('Futures','Contratto con scadenza'),('Risk-off','Preferenza per attività considerate meno rischiose'),('Fed','Banca centrale USA'),('BCE','Banca centrale dell’eurozona')],1):
        rows.append(row('glossary','g'+str(i),order=i,title=term,text=description))
    # Preserve the 22 predictions issued by the original desk, without pretending
    # they have been verified or recalculating missing probability scores.
    archived_path=Path(__file__).resolve().parents[1]/'state'/'original_forecasts.json'
    archived=json.loads(archived_path.read_text(encoding='utf-8')) if archived_path.exists() else []
    for f in archived:
        archived_row=f.copy()
        when=str(archived_row.get('time') or '')
        if when and when <= date and archived_row.get('label') == 'Aperta':
            archived_row['label']='Esito da verificare'
            archived_row['status']='Non verificata alla scadenza'
        # No changes to the original forecast definition, base value or probability.
        rows.append(archived_row)
    known_ids={r['id'] for r in rows if r['section']=='forecast'}
    for i,f in enumerate(payload.get('forecasts',{}).get('items',[]) if isinstance(payload.get('forecasts'),dict) else [],1):
        if str(f.get('id',i)) in known_ids: continue
        rows.append(row('forecast',str(f.get('id',i)),order=len(known_ids)+i,title=f.get('claim','n.d.'),category=str(f.get('date','')),time=str(f.get('due','')),text='Registro verificabile',status=str(f.get('status','Aperta'))))
    # Seven defense securities remain visible even if verified closes/contracts are absent.
    defense_symbols=(('NPK','National Presto'),('IA','Innovative Aerosystems'),
                     ('DRS','Leonardo DRS'),('DCO','Ducommun'),('CW','Curtiss-Wright'),
                     ('MOG.A','Moog'),('KTOS','Kratos Defense'))
    reported=(ai or {}).get('research',{}).get('difesa',{}).get('items',[]) or []
    for i,(ticker,company) in enumerate(defense_symbols,1):
        linked=[x for x in reported if (re.search(r'(?<!\w)'+re.escape(ticker)+r'(?!\w)',
                ' '.join(str(x.get(k,'')) for k in ('traduzione','fatto','perche_conta')), re.IGNORECASE)
                or company.lower() in ' '.join(str(x.get(k,'')) for k in ('traduzione','fatto','perche_conta')).lower())]
        brief_text='; '.join(str(x.get('fatto',''))[:250] for x in linked[:2]) if linked else 'Nessuna novità rilevante nelle fonti raccolte; non equivale a controllo esaustivo.'
        quote=(payload.get('defense_eod') or {}).get(ticker) or {}
        close=quote.get('close')
        rows.append(row('defense',ticker,order=i,title=company,category=ticker,
            value=close,change=quote.get('pct'),change_unit='%',
            label='Chiusura EOD del fornitore' if close is not None else 'Chiusura: n.d.',
            text=brief_text,detail='Dato EOD vendor, non prova di chiusura certificata exchange.' if close is not None else
                       'Contratti e prezzi non verificati: n.d.',
            status='EOD verificato da vendor' if close is not None else 'Copertura limitata',
            time=quote.get('date') or 'n.d.',source=quote.get('source') or 'n.d.',
            url=quote.get('url'))) 

    # Calendar events are recorded from the primary publisher via Finance Calendar,
    # whose own attribution is available at site/sources/; missing times remain unknown.
    upcoming=payload.get('calendar') or []
    today_events=[x for x in upcoming if x.get('date')==date][:25]
    for i,event in enumerate(today_events,1):
        ident=str(event.get('id') or 'event-'+str(i))
        rows.append(row('calendar',ident,order=i,title=event.get('name') or 'Evento macro',
          category=event.get('country') or 'Macro',value=event.get('actual'),
          prev=event.get('previous'),label='Atteso: '+str(event.get('consensus') if event.get('consensus') is not None else 'n.d.'),
          text='Orario fonte: '+str(event.get('time_precision') or 'da verificare')+
               '. Fonte del calendario: financecalendar.com',
          detail='Periodo: '+str(event.get('date'))+' · Evento pubblicato da: '+str(event.get('source') or 'n.d.'),
          status='Confermato' if event.get('state')=='confirmed' else 'Da confermare',
          time=event.get('time_athens') or 'Orario da confermare',source='Finance Calendar · '+str(event.get('source') or ''),
          url=event.get('source_url')))
    selected=sorted((x for x in upcoming if x.get('date')>date),key=lambda e:
        (e.get('date',''),e.get('time_athens') or '99:99'))[:25]
    for i,event in enumerate(selected,1):
        rows.append(row('upcoming',str(event.get('id') or 'upcoming-'+str(i)),order=i,
          title=event.get('name') or 'Evento futuro',category=event.get('country') or 'Macro',
          text='Finance Calendar · evento in programma, non ancora avvenuto',
          detail='Stato: '+str(event.get('state') or 'Da confermare'),
          status='Confermato' if event.get('state')=='confirmed' else 'Da confermare',
          time=str(event.get('date'))+' '+str(event.get('time_athens') or 'Ora da confermare'),
          source='Finance Calendar · '+str(event.get('source') or ''),
          url=event.get('source_url')))
    if not today_events: rows.append(row('calendar','none',order=1,title='Nessuna pubblicazione macro verificata oggi',
          text='Calendario non disponibile o nessun evento previsto',time='n.d.',source='financecalendar.com',
          url='https://www.financecalendar.com'))
    if not selected: rows.append(row('upcoming','none',order=1,title='Calendario prossimo mese non disponibile',
          text='n.d. senza data ufficiale',source='financecalendar.com',
          url='https://www.financecalendar.com'))
    pairs=[(x['section'],x['id']) for x in rows]
    if len(pairs)!=len(set(pairs)): raise AssertionError('non-unique (section,id)')
    if any(tuple(x)!=FIELDS for x in rows): raise AssertionError('schema mismatch')
    return rows

def save_original(payload,ai,site_dir, *, history_seed=None):
    dest=Path(site_dir)/'original'/'data'; dest.mkdir(parents=True,exist_ok=True)
    items=build_rows(payload,ai)
    (dest/'oggi.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
    old=dest/'storico.json'; history=json.loads(old.read_text(encoding='utf-8')) if old.is_file() else (history_seed or [])
    if not isinstance(history,list): history=[]
    stamp=payload.get('generated_at') or datetime.now(ZoneInfo('Europe/Athens')).isoformat()
    date=datetime.fromisoformat(stamp.replace('Z','+00:00')).astimezone(ZoneInfo('Europe/Athens')).date().isoformat()
    seen={(x.get('date'),x.get('series')) for x in history if isinstance(x,dict)}
    def record(series,value):
        if not isinstance(value,(int,float)) or isinstance(value,bool):return
        if (date,series) not in seen:
            history.append({'date':date,'series':series,'value':value});seen.add((date,series))
    # Only documented, numeric, non-stale metrics appear in historical series.
    for name,x in payload.get('indicators',{}).items():
        if name in ('global_risk','market_stress','war_escalation','conviction') and isinstance(x,dict):
            record('gauge:'+name,x.get('value'))
    for row_ in items:
        kind=row_['section'];id_=row_['id'];value=row_.get('value')
        if kind=='sentiment':record('sent:'+id_,value)
        if kind=='front':record('front:'+id_,value)
        if kind=='trading':
            label=row_.get('label')
            if label in ('Rialzista','Ribassista','Neutrale'):
                record('lettura:'+('EURUSD' if id_=='6E' else id_),{'Rialzista':1,'Neutrale':0,'Ribassista':-1}[label])
    for quote in payload.get('markets',[]):
        if not quote.get('stale') and isinstance(quote.get('value'),(int,float)):
            record('mkt:'+quote.get('id','n.d.'),quote['value'])
    dates=sorted({x['date'] for x in history if isinstance(x,dict) and isinstance(x.get('date'),str)})[-400:]
    history=[x for x in history if isinstance(x,dict) and x.get('date') in dates]
    (dest/'storico.json').write_text(json.dumps(history,ensure_ascii=False,indent=2),encoding='utf-8')
    return len(items)
