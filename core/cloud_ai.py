"""OPEN WORLD V3 · real generative agents using the Google Gemini free API.

No API keys in source/site. Only server-side GitHub Actions uses GEMINI_API_KEY.
Every output carries public source IDs; model text is not independent corroboration.
"""
from __future__ import annotations
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
import json
import os
import re
import ipaddress
import time

MODEL_RE = re.compile(r'^[A-Za-z0-9._-]+$')
class LLMError(RuntimeError): pass


def model_name():
    selected = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite')
    if not MODEL_RE.fullmatch(selected): raise ValueError('Invalid GEMINI_MODEL')
    return selected


def generate_json(role, instructions, data, *, requester=None, key=None, max_output_tokens=2500):
    """Request a machine-checkable JSON result; no other providers, no hidden fallback."""
    key = key if key is not None else os.getenv('GEMINI_API_KEY', '')
    if not key: raise LLMError('GEMINI_API_KEY non configurata: nessuna IA cloud è stata eseguita.')
    url = 'https://generativelanguage.googleapis.com/v1beta/models/' + model_name() + ':generateContent'
    request_data = {
      'systemInstruction': {'parts':[{'text': (
        'Sei '+ role + ' del progetto OPEN WORLD. Rispondi SOLO con JSON valido in italiano. '
        'Usa ESCLUSIVAMENTE il dossier fornito: non inventare prezzi, link, date, percentuali, citazioni o verifiche. '
        'Un titolo RSS non equivale a una notizia verificata. Se mancano prove scrivi n.d. o non verificato. '
        'Ogni affermazione su una notizia usa gli id fonte del dossier, non inventare ID. '
        'Separa sempre FATTO PUBBLICATO, LETTURA IPOTETICA e POSSIBILE IMPATTO CONDIZIONALE. '
        'NON dare ordini di trading, ingressi, target o stop. Non usare segreti o dati personali.') }]},
      'contents':[{'role':'user','parts':[{'text': instructions+'\n\nDOSSIER (JSON):\n'+json.dumps(data,ensure_ascii=False, separators=(',',':'))[:50000]}]}],
      'generationConfig': {'temperature':0.15, 'maxOutputTokens':max_output_tokens,
                           'responseMimeType':'application/json'}
    }
    body=json.dumps(request_data,ensure_ascii=False).encode('utf-8')
    req=Request(url, data=body, headers={'Content-Type':'application/json', 'x-goog-api-key':key},method='POST')
    send=requester or urlopen
    try:
        with send(req,timeout=65) as res:
            response=json.loads(res.read(550000).decode('utf-8'))
    except HTTPError as e:
        # Never reveal credential-bearing request URL: key is in header.
        reason={400:'richiesta API non valida',401:'chiave rifiutata',403:'permesso insufficiente',404:'modello non disponibile',429:'limite quota gratuita raggiunto',500:'errore server',503:'servizio temporaneamente indisponibile'}.get(e.code,'HTTP '+str(e.code))
        raise LLMError(reason) from None
    except (TimeoutError, URLError, OSError, ValueError) as e:
        raise LLMError('servizio IA non raggiungibile o risposta non valida: '+type(e).__name__) from None
    candidates=response.get('candidates') or []
    try:
        parts=candidates[0]['content']['parts']
        text=''.join(p.get('text','') for p in parts)
        result=json.loads(text)
        if not isinstance(result,dict): raise ValueError('not object')
        return result
    except (ValueError, IndexError, KeyError, TypeError) as e:
        raise LLMError('il modello non ha restituito JSON valido') from None

class SafeNewsRedirect(HTTPRedirectHandler):
    """Allow only HTTPS redirects within the original publisher hostname."""
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        current=urlparse(req.full_url)
        new=urlparse(newurl)
        if new.scheme != 'https' or new.hostname != current.hostname:
            raise HTTPError(newurl,403,'Redirect outside original publisher blocked',headers,fp)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def safe_news_hostname(host):
    if not host or host in ('localhost','metadata.google.internal') or host.endswith(('.local','.internal')):
        return False
    try:
        address=ipaddress.ip_address(host)
        return address.is_global
    except ValueError:
        return '.' in host and not host.endswith('.localhost')

class ArticleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.exclude=0; self.output=[]; self.in_main=False
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style','svg','nav','footer','header','noscript','form'): self.exclude+=1
        if tag in ('article','main'): self.in_main=True
    def handle_endtag(self,tag):
        if tag in ('script','style','svg','nav','footer','header','noscript','form'): self.exclude=max(0,self.exclude-1)
        if tag in ('p','h1','h2','h3','li','div'): self.output.append('\n')
    def handle_data(self,data):
        if not self.exclude and data.strip(): self.output.append(data.strip()+' ')
    def text(self):
        x=''.join(self.output)
        x=re.sub(r'[ \t]+',' ',x)
        x=re.sub(r'\n{3,}','\n\n',x)
        return x[:4500].strip()


def read_public_article(url, *, opener=None):
    """Public HTTP(S) news pages only; do not work around blocks or paywalls."""
    u=urlparse(url)
    if u.scheme!='https' or not safe_news_hostname(u.hostname) or u.username or u.password: return None
    req=Request(url,headers={'User-Agent':'OpenWorldIntelligence/3.0 (+research; public pages)','Accept':'text/html,application/xhtml+xml'})
    try:
        safe_open = opener or build_opener(SafeNewsRedirect()).open
        with safe_open(req,timeout=11) as r:
            typ=r.headers.get('Content-Type','')
            final=urlparse(r.geturl())
            if final.scheme != 'https' or not safe_news_hostname(final.hostname) or 'html' not in typ: return None
            raw=r.read(230000)
        parser=ArticleText(); parser.feed(raw.decode('utf-8','replace'))
        text=parser.text()
        return text if len(text)>250 else None
    except (HTTPError,URLError,OSError,TimeoutError,ValueError):
        return None

ROLES={
 'geopolitica': ('Russia–Ucraina; Israele/Iran/Libano; Yemen/Golfo/Hormuz; Cina/Taiwan; energia. Analizza SOLO le notizie indicate. Traduci titoli e spiegali in italiano comprensibile. Rispondi {"items":[{"id":"<id fonte>","traduzione":"...","fatto":"Secondo ...", "perche_conta":"...", "mercati":"Se ..., allora ...", "certezza":"riportato da una testata|dichiarazione di parte|fonte primaria"}],"quadro":"..."}. Massimo 7 items.'),
 'macro': ('Macro, banche centrali, EUR/USD, oro, S&P 500 e dati energia. Non dichiarare prezzi di mercato live e non assegnare cause certe senza fonti. Traduci e interpreta. Rispondi {"items":[{"id":"<id fonte>","traduzione":"...","fatto":"...","perche_conta":"...","mercati":"Se ..., allora ...","certezza":"riportato da una testata|dichiarazione di parte|fonte primaria"}],"quadro":"..."}. Massimo 7 items.'),
 'difesa': ('Titoli e contratti difesa: DRS, DCO, NPK, IA, CW, MOG.A, KTOS. Se non ci sono notizie scrivi nessuna novità documentata. Rispondi {"items":[{"id":"<id fonte>","traduzione":"...","fatto":"...","perche_conta":"...","mercati":"...","certezza":"riportato da una testata|dichiarazione di parte|fonte primaria"}],"quadro":"..."}. Massimo 5 items.'),
 'verificatore': ('Sei revisore scettico, non prova automatica della verità. Esamina tutte le dichiarazioni e controlla che siano compatibili con gli estratti forniti. Contrassegna come dubbio quelle non sostenute. Rispondi {"segnalazioni":[{"id":"id fonte", "problema":"...", "correzione":"..."}],"giudizio":"..."}. Non scrivere mai Verificato per una sola testata.'),
 'capo_desk': ('Prepara il briefing didattico in italiano SENZA inventare nuove informazioni. Ogni fatto attribuito e la sua condizione di mercato. Rispondi {"sintesi_60s":["..."],"guerre_e_crisi":"...","mercati":"...","macro_banche_centrali":"...","geopolitica_mercati":"...","agenda":"n.d. senza calendari ufficiali", "difesa":"...","scenari_7_30_90":"...","previsioni":"Non creare previsioni numeriche senza criteri osservabili e orizzonte verificabile", "valutazione_finale":"...","lezione":"...","limiti":"..."}. Sintesi max 5 fatti; scenari sempre ipotetici.'),
 'apprendimento': ('Usa il registro verificabile e i dati di copertura: rileva errori ripetuti, precisione, notizie senza prove, previsioni valutate. NON alterare i dati storici né dichiarare che il modello impara dai pesi. Rispondi {"osservazioni":["..."],"correzioni_proposte":["..."],"metriche":{"previsioni_valutate":0,"brier":null}}. Se insufficiente, ammettilo.')
}

def shortlist(payload):
    a=payload.get('articles',[])
    roles={k:[] for k in ('geopolitica','macro','difesa')}
    seen=set()
    for article in a:
        tags=' '.join(article.get('topics',[])).lower()
        if 'mercati e difesa' in tags or 'defense' in article.get('title','').lower(): group='difesa'
        elif 'macro' in tags or 'energia' in tags or 'business' in article.get('source','').lower(): group='macro'
        else: group='geopolitica'
        if len(roles[group])>=9 or article['id'] in seen: continue
        seen.add(article['id']);roles[group].append(article)
    # Fallback retain broad selection if a bucket empty.
    if not roles['macro']: roles['macro']=[x for x in a if 'business' in x.get('source','').lower()][:4]
    return roles

def dossier_items(items, *, article_reader=None):
    out=[]
    reader=article_reader or read_public_article
    for a in items:
        page=reader(a['url']) if len(out)<8 else None
        out.append({'id':a['id'],'title':a['title'],'description':a.get('summary','')[:700],
           'publisher':a['source'],'source_type':a.get('source_type'),'published_at':a['published_at'],
           'url':a['url'],'page_opened':page is not None, 'page_excerpt':(page or '')[:1900],
           'epistemic_status':'testata letta (non conferma indipendente)' if page else 'solo RSS, articolo non aperto'})
    return out

def verified_items(result,allowed_ids):
    out=[]
    for item in result.get('items',[]):
        if not isinstance(item,dict) or item.get('id') not in allowed_ids: continue
        row={'id':item['id']}
        for key in ('traduzione','fatto','perche_conta','mercati','certezza'):
            row[key]=str(item.get(key,'n.d.'))[:850]
        row['certezza']='interpretazione IA su fonte attribuita; verifica indipendente NON garantita'
        out.append(row)
    return out[:9]

def build_daily(payload, *, history=None, forecaster=None, prior_learning=None, requester=None, key=None, reader=None):
    """Execute five distinct role calls + chief + learning; fail explicitly without fabricated AI."""
    if not (key if key is not None else os.getenv('GEMINI_API_KEY')):
        raise LLMError('Chiave Gemini gratuita assente: aggiungila ai Secrets di GitHub Actions.')
    buckets=shortlist(payload)
    results={}; evidence={}; audit=[]
    for role in ('geopolitica','macro','difesa'):
        items=dossier_items(buckets[role],article_reader=reader)
        evidence[role]=items
        try:
            answer=generate_json(role,ROLES[role],{'sources':items,'past_quality_notes':(prior_learning or [])[-5:]},requester=requester,key=key,max_output_tokens=2400)
            results[role]={'items':verified_items(answer,{x['id'] for x in items}), 'quadro':str(answer.get('quadro','n.d.'))[:1500]}
            audit.append({'role':role,'status':'ok','items':len(results[role]['items'])})
        except LLMError as e:
            results[role]={'items':[],'quadro':'n.d.'}
            audit.append({'role':role,'status':'error','message':str(e)})
    if not any(results[k]['items'] for k in results): raise LLMError('Nessun agente di analisi ha restituito dati utilizzabili.')
    claims=[dict(role=role,**i) for role,x in results.items() for i in x['items']]
    published=[{'id':i['id'],'url':i['url'],'title':i['title'],'publisher':i['publisher'],'page_opened':i['page_opened'],
                'description':i['description']} for items in evidence.values() for i in items]
    try:
        check=generate_json('verificatore',ROLES['verificatore'], {'claims':claims,'evidence':published}, requester=requester,key=key,max_output_tokens=1800)
        review={'segnalazioni':[x for x in check.get('segnalazioni',[]) if isinstance(x,dict)][:30],
                'giudizio':str(check.get('giudizio','non verificato'))[:1000]}
        audit.append({'role':'verificatore','status':'ok','flags':len(review['segnalazioni'])})
    except LLMError as e:
        review={'segnalazioni':[],'giudizio':'Verifica IA non completata; tutti i fatti restano attribuiti alle testate.'}
        audit.append({'role':'verificatore','status':'error','message':str(e)})
    try:
        chief=generate_json('capo_desk',ROLES['capo_desk'],{'research':results,'review':review,'sources':published,'markets':payload.get('markets',[])[:12]},requester=requester,key=key,max_output_tokens=3600)
        audit.append({'role':'capo_desk','status':'ok'})
    except LLMError as e:
        chief={'sintesi_60s':['Capo desk non disponibile. Consulta analisi attribuite alle testate.'],'limiti':str(e)}
        audit.append({'role':'capo_desk','status':'error','message':str(e)})
    scored=(forecaster or {}).get('scored',0) if isinstance(forecaster,dict) else 0
    stats={'previous_days':len(history or []),'articles_48h':payload.get('quality',{}).get('articles_48h',0),
           'feeds_ok':payload.get('quality',{}).get('feeds_ok',0),'forecasts':forecaster or {},
           'audit':audit,'review_flags':review['segnalazioni'],'previous_lessons':(prior_learning or [])[-7:]}
    try:
        learn=generate_json('apprendimento',ROLES['apprendimento'],stats, requester=requester,key=key,max_output_tokens=1200)
        audit.append({'role':'apprendimento','status':'ok'})
    except LLMError as e:
        learn={'osservazioni':['Non disponibile'],'correzioni_proposte':[],'metriche':{'previsioni_valutate':scored,'brier':None}}
        audit.append({'role':'apprendimento','status':'error','message':str(e)})
    date=payload['generated_at'][:10]
    return {'version':'3.0','date':date,'generated_at':datetime.now(timezone.utc).isoformat(),
      'provider':'Gemini API (free tier, quota non garantita)','model':model_name(),
      'status':'ok' if any(e['role']=='capo_desk' and e['status']=='ok' for e in audit) else 'partial',
      'research':results,'verification':review,'brief':chief,'learning':learn,'agent_audit':audit,
      'sources':published,'disclaimer':'Analisi IA su testi pubblicati. Verifica indipendente non garantita; nessun consiglio finanziario.'}
