"""OPEN WORLD Claude-method kit: 7 bounded Gemini roles, Python owns all facts and math.
This is an orchestrator, not seven permanently running models. No API key leaves Actions.
"""
from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import json,re
from jsonschema import validate,ValidationError
from .cloud_ai import generate_json,dossier_items,shortlist,LLMError
from .desk_checks import recent_documents,attribution,verify_ids,numeric_guard,calculate_indicators

ROOT=Path(__file__).resolve().parents[1]
PROMPTS=ROOT/'config/prompts'
ROLE_ORDER=('geopolitica','macro','difesa','capo_desk','verificatore','apprendimento','revisore_finale')
SCHEMAS={
 'geopolitica':{'voci':list,'fronti':list,'previsioni':list,'nulla_di_rilevante':list},
 'macro':{'voci':list,'mercati':list,'agenda':list,'livelli':dict,'calendario_30g':list,'cot':(list,type(None)),'previsioni':list},
 'difesa':{'voci':list,'titoli':list,'limiti':list},
 'capo_desk':{'brief_markdown':str,'inclinazione':dict,'mappa_forze':list,'snapshot':list,'scenari':list,'warning':list,'cambiamenti':list},
 'verificatore':{'errori':list,'esito':str},
 'apprendimento':{'titolo':str,'area':str,'livello':str,'spiegazione':str,'esempio_oggi':str,'domanda':str,'risposta':str,'parole':list},
 'revisore_finale':{'note':list}
}

def schema(role):
    required=SCHEMAS[role]
    def type_of(value):
        if value is str:return 'string'
        if value is dict:return 'object'
        if value is list:return 'array'
        if value is type(None):return 'null'
        if isinstance(value,tuple):return [type_of(v) for v in value]
        raise ValueError('Invalid schema')
    return {'type':'object','required':list(required),'properties':{k:{'type':type_of(v)} for k,v in required.items()},'additionalProperties':True}

def load_prompt(role,local):
    common=(PROMPTS/'common.md').read_text(encoding='utf-8')
    for k,v in {'DATA_ORA_ATENE':local.isoformat(),'INIZIO':(local.replace(hour=0,minute=0)).isoformat(),
                'FINE':local.isoformat(),'DATA_ULTIMO_BRIEF':'ultimo dato disponibile'}.items():
        common=common.replace('{'+k+'}',v)
    return common+'\n\n'+(PROMPTS/(role+'.md')).read_text(encoding='utf-8')

def call_role(role,packet,now, *, key=None):
    prompt=load_prompt(role,now)+"\nRispetta esattamente le chiavi dello schema. Non inventare ID."
    for attempt in range(2):
        try:
            data=generate_json(role,prompt,packet,key=key,max_output_tokens=5700 if role=='capo_desk' else 2800)
            validate(data,schema(role))
            return data
        except (ValidationError,LLMError) as exc:
            # Do not retry quota/403 errors; only malformed JSON or schema gets one repair call.
            if isinstance(exc,LLMError) and 'JSON' not in str(exc):raise
            if attempt:raise LLMError(role+': output non valido dopo un solo tentativo di riparazione: '+type(exc).__name__) from None
            prompt+='\nLA RISPOSTA PRECEDENTE NON È VALIDA ('+str(exc)[:350]+'). Riprova usando tutte le chiavi obbligatorie, senza testo esterno al JSON.'
    raise LLMError(role+' errore')

def sanitize_claims(result,allowed_ids,documented):
    """Never elevate self-declared 'Verificato' in model output."""
    clean=[]
    for v in result.get('voci',[]):
        if not isinstance(v,dict):continue
        ids=verify_ids(v.get('fonti',[]),allowed_ids)
        if v.get('id') not in allowed_ids or not ids:continue
        item=dict(v)
        item['fonti']=ids
        # A document can be primary for its own release; claims of conflict still attributed.
        item['etichetta']=documented[item['id']]['attribution'][0]
        clean.append(item)
    result['voci']=clean[:15]
    return result

def form_research(result,documented,ids):
    items=[]
    for v in result.get('voci',[]):
        src=documented.get(v.get('id'))
        if not src:continue
        txt=v.get('fatto','')
        items.append({'id':v['id'],'traduzione':v.get('fatto',''),
                      'fatto':txt,'perche_conta':v.get('perche_conta',''),
                      'mercati':'Se questo evento persiste, allora un impatto è possibile (non misurato).',
                      'certezza':v['etichetta'],'source_ids':v.get('fonti',[])})
    return items

def parse_sections(markdown):
    """Keep Markdown untouched in archive; existing dashboard needs named fields."""
    headings=re.split(r'(?m)^##\s+(?=\d+\.)',str(markdown))
    found={}
    for part in headings[1:]:
        m=re.match(r'(\d+)\.[^\n]*\n(.*)',part,re.S)
        if m:found[int(m.group(1))]=m.group(2).strip()
    return found

def sanitize_markdown(md,evidence,local):
    allowed={'1','2','3','4','5','6','7','8','9','10','11','12','13','20','24','25','30','48','60','75','85','90','100',
             str(local.day),str(local.month),str(local.year)}
    flags=[];clean=[]
    for ln in md.splitlines():
        if ln.startswith('#'):
            clean.append(ln);continue
        text,unknown=numeric_guard(ln,evidence,allow=allowed)
        flags.extend(unknown)
        clean.append(text)
    return '\n'.join(clean),sorted(set(flags))

def daily_packet(payload,now,history,forecaster,previous_lessons):
    docs,excluded=recent_documents(payload.get('articles',[]),now.astimezone(timezone.utc))
    src={a['id']:dict(a,attribution=attribution(a)) for a in docs if isinstance(a,dict) and a.get('id')}
    buckets=shortlist({'articles':docs})
    return docs,src,buckets,excluded

def build_daily_method(payload, *, history=None, forecaster=None, prior_learning=None, key=None, reader=None):
    """Exactly seven logical roles, sequence Claude: specialists→chief→checker→teacher→reviewer."""
    now=datetime.now(timezone.utc).astimezone(ZoneInfo('Europe/Athens'))
    docs,source_index,buckets,excluded=daily_packet(payload,now,history,forecaster,prior_learning)
    if not docs:raise LLMError('Nessuna notizia recente con timestamp verificabile: non genero un briefing.')
    allowed=set(source_index)
    audit=[];outputs={};research={};raw_sources={}
    def step(role,packet,optional=True):
        try:
            response=call_role(role,packet,now,key=key)
            audit.append({'role':role,'status':'ok'})
            return response
        except LLMError as exc:
            audit.append({'role':role,'status':'error','message':str(exc)[:160]})
            if not optional:raise
            return {}
    for role in ('geopolitica','macro','difesa'):
        samples=dossier_items(buckets.get(role,[])[:12],article_reader=reader)[:12]
        for d in samples:
            d['attribution']=source_index[d['id']]['attribution']
        raw_sources[role]=samples
        packet={'date_athens':now.isoformat(),'articles':samples,'previous_10_days':(history or [])[-10:],
                'markets':payload.get('markets',[])[:14] if role=='macro' else [],
                'forecast_registry':forecaster or {},'information_scope':'24h/48h max, timestamp mandatory'}
        response=step(role,packet)
        response=sanitize_claims(response,allowed,source_index)
        outputs[role]=response
        research[role]={'items':form_research(response,source_index,allowed),
                        'quadro':str(response.get('limiti') or response.get('nulla_di_rilevante') or '')[:600]}
    if not any(x.get('voci') for x in outputs.values()):
        raise LLMError('Nessuno specialista ha prodotto risultati fondati su ID esistenti.')
    indicators=calculate_indicators(payload,outputs.get('geopolitica'),outputs.get('macro'))
    packet={'specialists':outputs,'indicatori_python':indicators,'mercati_originali':payload.get('markets',[]),
            'sources':raw_sources,'brief_ieri':(history or [])[-1:] if history else [],
            'lesson_history':(prior_learning or [])[-10:],'forecasts':forecaster or {},
            'scope':'NO numeri nuovi, NO dati da fonti non incluse'}
    chief=step('capo_desk',packet,optional=False)
    original_md=chief.get('brief_markdown','')
    evidence=json.dumps(packet,ensure_ascii=False)
    clean_md,invalid_numbers=sanitize_markdown(original_md,evidence,now)
    chief['brief_markdown']=clean_md
    verify=step('verificatore',{'draft':chief,'sources':raw_sources,'indicators':indicators,'source_date_rejections':excluded})
    if verify.get('errori'):
        # Chief is NOT silently allowed to publish factually disputed paragraphs as verified.
        chief['brief_markdown']='AVVISO: il verificatore ha trovato errori nella bozza; interpretazioni non confermate.\n\n'+chief['brief_markdown']
    if invalid_numbers:
        verify.setdefault('errori',[]).append({'testo_errato':'Numeri non presenti negli input: '+', '.join(invalid_numbers[:15]),
             'correzione':'Sostituiti con n.d. automaticamente','fonte':'controllo Python','gravita':'alta'})
        verify['esito']='Errori trovati'
    lesson=step('apprendimento',{'today':chief,'sources':raw_sources,'recent_lessons':(prior_learning or [])[-10:]})
    recent_titles={str((x.get('lezione') or {}).get('titolo','')).casefold().strip() for x in (prior_learning or [])[-10:] if isinstance(x,dict)}
    if lesson.get('titolo','').casefold().strip() in recent_titles:
        audit.append({'role':'controllo_lezione','status':'errore','message':'Titolo ripetuto nelle ultime dieci lezioni'})
        lesson={}
    reviewer=step('revisore_finale',{'brief':chief,'verification':verify,'forecasts_resolved':[],
                                  'previous_lessons':(prior_learning or [])[-7:]})
    section=parse_sections(chief['brief_markdown'])
    brief={'brief_markdown':chief['brief_markdown'],
           'sintesi_60s':[x.get('titolo','')+': '+x.get('testo','') for x in chief.get('snapshot',[]) if isinstance(x,dict)][:5],
           'guerre_e_crisi':section.get(2,'n.d.'),'mercati':section.get(3,'n.d.'),
           'macro_banche_centrali':section.get(4,'n.d.'),'geopolitica_mercati':section.get(5,'n.d.'),
           'agenda':section.get(6,'n.d.'),'difesa':section.get(7,'n.d.'),
           'scenari_7_30_90':section.get(8,'n.d.'),'previsioni':section.get(9,'n.d.'),
           'valutazione_finale':section.get(10,'n.d.'),'lezione':lesson.get('spiegazione','n.d.'),
           'limiti':'Numeri non verificati sostituiti: '+', '.join(invalid_numbers[:10]) if invalid_numbers else 'La verifica automatica non equivale a verifica indipendente.',
           'inclinazione':chief.get('inclinazione',{}), 'mappa_forze':chief.get('mappa_forze',[])}
    sources=[{'id':d['id'],'title':d.get('title'), 'publisher':d.get('source'),
              'url':d.get('url'),'published_at':d.get('published_at'),
              'attribution':source_index[d['id']]['attribution'][0]} for d in docs[:100]]
    learning={'osservazioni':[n.get('problema') for n in reviewer.get('note',[]) if isinstance(n,dict)],
              'correzioni_proposte':[n.get('regola_proposta') for n in reviewer.get('note',[]) if isinstance(n,dict)],
              'lezione':lesson,'diario':reviewer.get('note',[])[:5],
              'metriche':{'previsioni_valutate':(forecaster or {}).get('brier_n',0),
                         'brier':(forecaster or {}).get('brier')}}
    status='ok' if all(x['status']=='ok' for x in audit) else 'partial'
    return {'version':'3.1-kit','date':now.date().isoformat(),'generated_at':now.isoformat(),
            'provider':'Google Gemini API','model':__import__('os').environ.get('GEMINI_MODEL','gemini-3.5-flash-lite'),'status':status,
            'research':research,'verification':verify,'brief':brief,'learning':learning,'agent_audit':audit,
            'sources':sources,'indicatori_python':indicators,'source_exclusions':excluded,
            'forecast_proposals_unpublished':chief.get('proposte_previsioni',[])[:3],
            'disclaimer':'Le fonti RSS non sono prova indipendente; indicatori e citazioni mancanti restano n.d. Nessun segnale di trading.'}
