import json
import unittest
from pathlib import Path
from core.original_bridge import build_rows,FIELDS

class DefenseCompleteTest(unittest.TestCase):
    def test_twenty_sections_seven_defense_titles(self):
        root=Path(__file__).resolve().parents[1]
        payload=json.loads((root/'site/data/latest.json').read_text())
        payload['articles']=[{'id':'test','title':'Notizia test','source':'BBC','url':'https://example.org/test','topics':['Altre notizie'],'published_at':'2026-10-22T12:00:00Z'}]
        rows=build_rows(payload,None)
        self.assertEqual(len({x['section'] for x in rows}),20)
        self.assertEqual({x['id'] for x in rows if x['section']=='defense'},
                         {'NPK','IA','DRS','DCO','CW','MOG.A','KTOS'})
        self.assertTrue(all(tuple(x)==FIELDS for x in rows))
        self.assertEqual(len(rows),len({(x['section'],x['id']) for x in rows}))

if __name__=='__main__':
    unittest.main()
