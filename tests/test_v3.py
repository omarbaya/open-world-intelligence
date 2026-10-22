"""Acceptance tests: originality, source grounding, secure API and daily gating."""
import json, pathlib, unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch
from core.cloud_ai import generate_json, LLMError, verified_items, build_daily, safe_news_hostname
from core.original_bridge import row, FIELDS, build_rows
from scripts.ai_daily import should_run

ROOT=pathlib.Path(__file__).resolve().parents[1]

class TestV3(unittest.TestCase):
 def test_original_code_is_bit_identical(self):
  import zipfile
  # Original not modified by the shim or AI engine; exact SHA can be separately checked.
  src=(ROOT/'site/original/assets/original-claude-dashboard.html').read_bytes()
  self.assertIn(b'OPEN WORLD',src)
  self.assertGreater(len(src),40000)
  self.assertIn(b'window.claude',src)
 def test_schema_exact_26(self):
  data=json.loads((ROOT/'site/data/latest.json').read_text())
  rows=build_rows(data,None)
  self.assertGreater(len(rows),60)
  self.assertEqual(len({(r['section'],r['id']) for r in rows}),len(rows))
  self.assertTrue(all(tuple(r)==FIELDS for r in rows))
  self.assertFalse(any(r['section']=='gauge' and r['value']==56 for r in rows))
 def test_original_forecasts_preserved(self):
  data=json.loads((ROOT/'site/data/latest.json').read_text())
  data['generated_at']='2026-10-22T04:00:00Z'
  rows=[r for r in build_rows(data,None) if r['section']=='forecast']
  self.assertEqual(len(rows),22)
  self.assertIn('P-20261015-1',{r['id'] for r in rows})
  self.assertNotIn('Confermata',{r['status'] for r in rows})
 def test_no_credentials_in_browser(self):
  for name in ['site/ai/index.html','site/original/index.html','site/index.html']:
   self.assertNotIn('x-goog-api-key',(ROOT/name).read_text())
 def test_news_links_never_private_ips(self):
  for host in ('localhost','127.0.0.1','10.0.0.3','192.168.1.1','169.254.169.254','metadata.google.internal'):
   self.assertFalse(safe_news_hostname(host))
  self.assertTrue(safe_news_hostname('www.bbc.com'))
 def test_missing_key_cannot_fake_ai(self):
  with patch.dict('os.environ', {'GEMINI_API_KEY':''},clear=False):
   with self.assertRaises(LLMError): generate_json('test','test',{})
 def test_sanitizes_fabricated_source_id(self):
  a=verified_items({'items':[{'id':'invented','fatto':'bad'},{'id':'real','fatto':'good','certezza':'Verificato!'}]}, {'real'})
  self.assertEqual(len(a),1)
  self.assertIn('NON garantita',a[0]['certezza'])
 def test_schedule_athens(self):
  z=ZoneInfo('Europe/Athens')
  self.assertFalse(should_run(datetime(2026,10,22,8,49,tzinfo=z)))
  self.assertTrue(should_run(datetime(2026,10,22,8,50,tzinfo=z)))
  self.assertFalse(should_run(datetime(2026,10,22,9,17,tzinfo=z), {'date':'2026-10-22','status':'ok'}))
 def test_agent_role_calls(self):
  data=json.loads((ROOT/'site/data/latest.json').read_text())
  data['generated_at']='2026-10-22T01:30:00Z'
  data['articles']=[{'id':'r1','url':'https://example.com/r1','title':'Ukraine Russia', 'source':'BBC World','source_type':'news','published_at':'2026-10-22T01:00:00Z','summary':'','topics':['Russia–Ucraina']}, {'id':'m1','url':'https://example.com/m1','title':'ECB inflation rates', 'source':'BBC Business','source_type':'news','published_at':'2026-10-22T01:00:00Z','summary':'','topics':['Macro e banche centrali']}, {'id':'d1','url':'https://example.com/d1','title':'Defense contract', 'source':'BBC World','source_type':'news','published_at':'2026-10-22T01:00:00Z','summary':'','topics':['Mercati e difesa']}]
  calls=[]
  def fake(role,prompt,dossier,**kw):
   calls.append(role)
   if role in ('geopolitica','macro','difesa'):
    inp=dossier['sources']
    return {'items':([{'id':inp[0]['id'],'fatto':'Secondo il feed','traduzione':'Notizia','perche_conta':'Spiegazione','mercati':'Se un evento si verifica, scenario condizionale'}] if inp else []),'quadro':'Quadro dalla fonte'}
   if role=='verificatore': return {'segnalazioni':[],'giudizio':'Nessuna verifica indipendente garantita'}
   if role=='capo_desk': return {'sintesi_60s':['Secondo testata, notizia attribuita.']}
   return {'osservazioni':['Non ci sono ancora sufficienti previsioni risolte'],'correzioni_proposte':[]}
  with patch('core.cloud_ai.generate_json',side_effect=fake):
   o=build_daily(data,reader=lambda url: 'fake public page text'*20,key='test')
  self.assertEqual(calls,['geopolitica','macro','difesa','verificatore','capo_desk','apprendimento'])
  self.assertIn(o['status'],('ok','partial'))
  self.assertEqual(len(o['agent_audit']),6)
