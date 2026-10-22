"""Independent offline acceptance tests for the Claude-method adaptation."""
from datetime import datetime,date,timezone,timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json,unittest
from jsonschema import ValidationError
from core.desk_method import schema,call_role,build_daily_method,ROLE_ORDER
from core.desk_checks import recent_documents,contradictory_quotes,numeric_guard,calculate_indicators
from core.forecast_rules import validate_open,validate_resolve,brier
from core import forecasts
from core.original_bridge import build_rows,FIELDS
ROOT=Path(__file__).resolve().parents[1]

class MethodKitTest(unittest.TestCase):
 def test_seven_roles_and_eight_prompt_files(self):
  self.assertEqual(len(ROLE_ORDER),7)
  for role in (*ROLE_ORDER,'common'):
   self.assertGreater((ROOT/'config/prompts'/f'{role}.md').stat().st_size,300)
 def test_jsonschema_retries_once_for_invalid_schema(self):
  given=[{'voci':[]}, {'voci':[],'fronti':[],'previsioni':[],'nulla_di_rilevante':[]}]
  def fake(*args,**kwargs):return given.pop(0)
  with patch('core.desk_method.generate_json',side_effect=fake) as f:
   out=call_role('geopolitica',{},datetime(2026,10,22,12,tzinfo=timezone.utc),key='testing')
  self.assertEqual(len(out['fronti']),0)
  self.assertEqual(f.call_count,2)
 def test_null_cot_schema_is_valid(self):
  from jsonschema import validate
  macro={k:({} if v is dict else None if isinstance(v,tuple) else []) for k,v in __import__('core.desk_method',fromlist=['SCHEMAS']).SCHEMAS['macro'].items()}
  validate(macro,schema('macro'))
 def test_48_hour_window_rejects_old_articles(self):
  now=datetime(2026,10,22,9,tzinfo=timezone.utc)
  rows=[{'id':'old','published_at':(now-timedelta(hours=49)).isoformat()},
        {'id':'new','published_at':(now-timedelta(hours=47)).isoformat()},
        {'id':'undated','published_at':'unproven'}]
  valid,excluded=recent_documents(rows,now)
  self.assertEqual([x['id'] for x in valid],['new'])
  self.assertEqual(len(excluded),2)
 def test_quote_conflicts_only_same_instrument_and_day(self):
  q=[{'id':'GC','instrument':'XAU/USD spot','source':'Kitco','value':4000,'observation_date':'2026-10-22'},
     {'id':'GC','instrument':'XAU/USD spot','source':'Reuters','value':4050,'observation_date':'2026-10-22'},
     {'id':'GC','instrument':'GC futures','source':'CME','value':4100,'observation_date':'2026-10-22'}]
  self.assertEqual(len(contradictory_quotes(q)),1)
  self.assertGreater(contradictory_quotes(q)[0]['delta_pct'],.5)
 def test_numeric_guard_replaces_unseen_numbers(self):
  cleaned,flags=numeric_guard('CPI: 3,5% e 9,99%', 'CPI ufficiale: 3,5%')
  self.assertIn('3,5%',cleaned)
  self.assertIn('n.d.',cleaned)
  self.assertEqual(flags,['9,99'])
 def test_brier_and_immutable_initial_probability(self):
  event={'op':'open','id':'P-20261022-1','date':'2026-10-22','due':'2026-10-29',
         'claim':'Evento preciso','probability':.75,'criterion':'criterio preciso',
         'base_value':'4000 USD','source':'CME','reference_time':'12:00 Atene',
         'source_outcome':'CME','counts':'conta se confermato','does_not_count':'non contano voci'}
  validate_open(event,[],date(2026,10,22))
  proj=forecasts.project([event])
  self.assertEqual(proj['items'][0]['probability'],.75)
  with self.assertRaises(AssertionError):validate_open(dict(event,probability=.95,id='P-20261022-2'),[event],date(2026,10,22))
  with self.assertRaises(AssertionError):validate_resolve({'op':'resolve','id':event['id'],'status':'Confermata','proof':'CME','source':'CME','at':'2026-10-29'},[event],date(2026,10,29))
  self.assertAlmostEqual(brier(.75,'Smentita'),.5625)
  self.assertIsNone(brier(.75,'Parziale'))
 def test_exact_26_keys_unique_sections(self):
  obj=json.loads((ROOT/'site/data/latest.json').read_text(encoding='utf-8'))
  rows=build_rows(obj,None)
  self.assertTrue(all(tuple(x)==FIELDS for x in rows))
  self.assertEqual(len(rows),len({(x['section'],x['id']) for x in rows}))
 def test_math_known_case(self):
  from core.indicators_original import war_escalation,market_stress,macro_risk,global_risk,conviction
  self.assertEqual(war_escalation({'a':80,'b':78,'c':78}),90)
  self.assertEqual(market_stress(vix=18.44,spx_pct=.41,us10y_bp=-2,brent_pct=.41,dxy_pct=-.22),16)
  self.assertEqual(global_risk(90,16,50),56)
  self.assertEqual(conviction(7,3,2),20)
 def test_no_google_key_patterns_in_text_files(self):
  needle='AI'+'za'
  for p in ROOT.rglob('*'):
   if any(part.startswith('.') and part not in ('.github',) for part in p.relative_to(ROOT).parts):continue
   if p.is_file() and p.suffix in ('.py','.md','.js','.html','.json','.yaml','.yml','.toml','.txt'):
    self.assertNotIn(needle,p.read_text(encoding='utf-8',errors='replace'),str(p))
 def test_deterministic_missing_indicators_remain_null(self):
  payload={'articles':[],'markets':[{'id':'GC','value':None}], 'indicators':{'market_stress':{'value':None}}}
  result=calculate_indicators(payload)
  self.assertIsNone(result['global_risk']['value'])
  self.assertIsNone(result['war_escalation']['value'])

if __name__=='__main__':unittest.main()

class RoleChainTest(unittest.TestCase):
 def test_seven_agent_chain_and_bridge(self):
  now=datetime.now(timezone.utc)
  published=(now-timedelta(hours=1)).isoformat()
  sample=[
   {'id':'g1','title':'Ukraine conflict briefing','summary':'A published report on Ukraine.','url':'https://example.org/g1','source':'BBC','source_type':'media','published_at':published,'topics':['Russia–Ucraina']},
   {'id':'m1','title':'ECB macro inflation report','summary':'An economic article.','url':'https://example.org/m1','source':'France 24','source_type':'media','published_at':published,'topics':['Macro e banche centrali']},
   {'id':'d1','title':'Defense contract news','summary':'An industry article.','url':'https://example.org/d1','source':'Politico Europe','source_type':'media','published_at':published,'topics':['Mercati e difesa']}]
  payload={'generated_at':now.isoformat(),'articles':sample,'markets':[],
           'quality':{'articles_48h':3},'indicators':{'market_stress':{'value':None}}}
  observed=[]
  def fake(role,packet,now,key=None):
   observed.append(role)
   if role in ('geopolitica','macro','difesa'):
    ids=[x['id'] for x in packet['articles']]
    return {'voci':[{'id':ids[0],'fonti':[ids[0]],'fatto':'Secondo la fonte, notizia del giorno',
            'perche_conta':'Ha rilevanza per il rischio'}] if ids else [],
            **({'fronti':[],'previsioni':[],'nulla_di_rilevante':[]} if role=='geopolitica' else
               {'mercati':[],'agenda':[],'livelli':{},'calendario_30g':[],'cot':None,'previsioni':[]} if role=='macro' else
               {'titoli':[],'limiti':[]})}
   if role=='capo_desk':
    return {'brief_markdown':'## 1. In 60 secondi\nSecondo BBC, un fatto riportato.\n## 2. Guerre e crisi\nAttribuito alle fonti.\n## 3. Mercati\nn.d.',
            'inclinazione':{},'mappa_forze':[],'snapshot':[{'titolo':'Rapporto','testo':'Testo attribuito'}],
            'scenari':[],'warning':[],'cambiamenti':[], 'proposte_previsioni':[]}
   if role=='verificatore':return {'errori':[],'esito':'Nessun errore'}
   if role=='apprendimento':return {'titolo':'I titoli RSS','area':'Strumenti','livello':'Base',
       'spiegazione':'RSS non è verifica.','esempio_oggi':'n.d.','domanda':'Una testata basta?',
       'risposta':'No.', 'parole':[{'termine':'RSS','spiegazione':'Feed notizie'}]}
   return {'note':[]}
  with patch('core.desk_method.call_role',side_effect=fake):
   result=build_daily_method(payload,key='fake',reader=lambda _: 'testo pubblico '*40)
  self.assertEqual(observed,list(ROLE_ORDER))
  self.assertEqual(result['status'],'ok')
  self.assertEqual(result['learning']['lezione']['titolo'],'I titoli RSS')
  rows=build_rows({**payload,'indicators':result['indicatori_python']},result)
  self.assertTrue(all(tuple(r)==FIELDS for r in rows))
  self.assertEqual(len(rows),len({(r['section'],r['id']) for r in rows}))

class DashboardAgentIntegrationTest(unittest.TestCase):
 def test_front_and_trade_use_only_validated_values(self):
  p={'generated_at':'2026-10-22T10:00:00Z','articles':[],'markets':[],
     'indicators':{'market_stress':{'value':None},'war_escalation':{'value':70,'front_scores':{'gulf':70,'ru-ua':-20,'tw':150}}}}
  ai={'brief':{'inclinazione':{'ES':{'studio':'Rialzista','rilevanza':8,'motivi':'Studio condizionale','rischio':'Alta volatilità','invalidazione':'Nuovi dati'}},
       'mappa_forze':[{'forza':'Notizia test','fatto':'Fonte specificata','oro':[1,'Forte','Scenario condizionale'],
                       'eur':[-1,'Debole','Condizione'], 'sp':[0,'Debole','Neutro']},
                      {'forza':'Non valida','oro':[50,'Forte','invalid'], 'eur':[40,'Debole','invalid'], 'sp':[50,'Forte','invalid']}]},
      'learning':{'lezione':{'titolo':'Rendimenti','spiegazione':'Test'}}}
  rows=build_rows(p,ai)
  idx={(r['section'],r['id']):r for r in rows}
  self.assertEqual(idx['front','gulf']['value'],70)
  self.assertIsNone(idx['front','ru-ua']['value'])
  self.assertEqual(idx['trading','ES']['label'],'Rialzista')
  self.assertEqual(idx['trading','ES']['score'],8)
  self.assertEqual(idx['force','forza1-oro']['value'],1)
  self.assertFalse(any(r['section']=='force' and r.get('value')==50 for r in rows))
  self.assertEqual(idx['lesson','main']['title'],'Rendimenti')
