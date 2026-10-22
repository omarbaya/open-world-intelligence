"""Translate OPEN WORLD V3 feed+AI into the immutable Claude dashboard's 26-field schema.
The ORIGINAL HTML/CSS/JS is never changed; only original/data/oggi.json and storico.json.
Missing evidence remains null or n.d.; 2026-10-20 export is never mislabelled as live.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json

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
          label='n.d.' if value is None else 'Parziale',detail='Indicatore disponibile solo con sufficienti dati verificati.',
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
    for i,(key,(name,lat,lon,topic)) in enumerate(FRONTS.items(),1):
        topic_articles=[a for a in payload.get('articles',[]) if topic in a.get('topics',[])][:2]
        summary='; '.join(a['title'] for a in topic_articles) if topic_articles else 'Nessun fatto nuovo verificato.'
        rows.append(row('front',key,order=i,title=name,lat=lat,lon=lon,value=None,prev=None,label='n.d.',
            text=summary,detail='Tensione numerica non assegnata senza verifica indipendente.',
            extra='Effetto di mercato: scenario condizionale, non prezzo certo.',status='Non verificato'))
    market_map={'ES':'SP500','GC':'GOLD','EURUSD':'EURUSD','DXY':'DXY','VIX':'VIX','US2Y':'US2Y','US10Y':'US10Y','BRENT':'BRENT','WTI':'WTI','TTF':'TTF'}
    mk={x['id']:x for x in payload.get('markets',[])}
    for i,(id,symbol) in enumerate(market_map.items(),1):
        q=mk.get(symbol,{})
        value=q.get('value')
        rows.append(row('market',id,order=i,title=q.get('name') or id,category=id,unit=q.get('unit',''),
            value=value,prev=q.get('previous'),change=q.get('change_pct'),change_unit='%',
            label='Ritardato' if value is not None else 'n.d.',level='Medio',
            text='FRED: osservazione storica; non quotazione live.',detail='Nessuna causa di mercato assegnata senza fonte.',
            extra='Dato ritardato' if q.get('stale') else 'Data di osservazione riportata.',
            time=q.get('observation_date') or 'n.d.',source=q.get('source','n.d.'),url=q.get('url')))
    # Preserve every original UI module with blank/no-evidence states rather than old facts.
    rows.append(row('lesson','main',title='Una notizia non è una prova',category='Strumenti',level='Base',
        text='Un articolo attribuisce un fatto alla propria fonte. Un titolo RSS non è una verifica indipendente. Una dichiarazione di un esercito va attribuita alla parte interessata. Un possibile impatto sul mercato non è una previsione garantita.',
        detail='Nel desk la lettura IA è distinta dalle osservazioni documentate.',extra='Un solo titolo RSS conferma un evento?',catalysts='No. Occorre una fonte primaria pertinente o più indagini indipendenti.'))
    for i,(instrument,description) in enumerate([('ES','S&P 500 · ES / MES'),('GC','Oro · GC / MGC'),('6E','Euro · 6E / M6E')],1):
        rows.append(row('trading',instrument,order=i,title=description,category='Sessioni e orari: n.d.',
            score=None,label='n.d.',level='n.d.',text='Solo studio: notizie attribuite e dati ritardati.',
            detail='n.d. senza calendario macro ufficiale.',levels='Non verificati',invalidation='n.d.'))
    level_titles={'ES':'S&P 500 · indice cash (riferimento per ES/MES)',
       'GC':'Oro · spot XAU/USD (riferimento per GC/MGC)', '6E':'EUR/USD · cambio spot (riferimento per 6E/M6E)'}
    for sym,t in level_titles.items():
        for i,(suffix,label,kind) in enumerate([('h','Massimo di ieri','high'),('l','Minimo di ieri','low'),('c','Chiusura di ieri','close'),('wh','Massimo della settimana','wkhigh'),('wl','Minimo della settimana','wklow')],1):
            rows.append(row('level',sym+'-'+suffix,order=i,title=t,category=sym,value=None,label=label,status=kind,unit='$' if sym=='GC' else '',
                time='n.d.',source='Non verificato'))
    for i,(k,v) in enumerate([('GC','Oro (COMEX)'),('EUR','Euro (CME)'),('ES','E-mini S&P 500 (CME)')],1):
        rows.append(row('cot',k,order=i,title=v,value=None,prev=None,change=None,label='n.d.',
            detail='Richiede pubblicazione ufficiale CFTC',time='n.d.',source='CFTC',url='https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm'))
    # Sections designed to remain honest when data is missing.
    brief=(ai or {}).get('brief',{})
    def article_section(section,field,title):
        text=brief.get(field) or 'n.d. Nessuna analisi IA pubblicata per questo giorno.'
        if isinstance(text,(dict,list)): text=json.dumps(text,ensure_ascii=False)
        rows.append(row(section,section+'-1',order=1,title=title,text=str(text)[:1500]))
    article_section('warning','limiti','Avvertenze e limiti dei dati')
    article_section('scenario','scenari_7_30_90','Scenari condizionali 7–30–90 giorni')
    article_section('change','valutazione_finale','Cosa cambia e perché')
    # The 5 thematic 'force' columns are displayed but without invented direction.
    for j,name in enumerate(('Geopolitica','Inflazione','Banche centrali'),1):
        for x,label in enumerate(('Oro','EUR/USD','S&P 500'),1):
            rows.append(row('force',f'{j}-{x}',order=j,title=name,category=label,value=0,level='Debole',
                text='Direzione non stimabile senza input verificati.',detail='Matrice informativa, non segnale di trading.'))
    for n,name in enumerate(('Globale','Oro','Euro','Azioni','Energia','Difesa','Rischio geopolitico'),1):
        rows.append(row('sentiment',str(n),order=n,title='Sentiment '+name,value=None,text='n.d.',detail='Misura non disponibile senza fonti e calcolo completo.'))
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
    # Calendar + upcoming are left blank, avoiding fictitious current schedules.
    rows.append(row('calendar','none',order=1,title='Agenda ufficiale non collegata',text='n.d.',status='Atteso',time='Tutto il giorno'))
    rows.append(row('upcoming','none',order=1,title='Calendario a 30 giorni non collegato',text='n.d.',status='Da confermare',time='n.d.'))
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
    # Do not add today's artificially estimated score; only calculated non-stale stress.
    stress=payload.get('indicators',{}).get('market_stress',{}).get('value')
    if isinstance(stress,(int,float)):
        new={'date':date,'series':'gauge:market_stress','value':stress}
        if (date,new['series']) not in seen: history.append(new)
    (dest/'storico.json').write_text(json.dumps(history,ensure_ascii=False,indent=2),encoding='utf-8')
    return len(items)
