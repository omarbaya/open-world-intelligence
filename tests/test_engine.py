import unittest
from datetime import datetime,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
from core.sources import parse_feed
from core.markets import parse_fred_csv
from core.intelligence import categorise,similarity,cluster_articles,analyse
from core.forecasts import project
from core.engine import compute_stress
from core.indicators_original import market_stress,war_escalation,global_risk,conviction

NOW=datetime(2026,10,22,7,0,tzinfo=timezone.utc)
SOURCE={'name':'Test BBC','type':'media','url':'https://example.org/feed'}
RSS=b'''<?xml version="1.0"?><rss version="2.0"><channel><title>Test</title><item><title>Ukraine conflict briefing</title><link>https://example.org/post?utm_source=tracking</link><description>Officials stated news, unverified.</description><pubDate>Thu, 22 Oct 2026 05:40:00 GMT</pubDate></item><item><title>Without date</title><link>https://example.org/undated</link></item></channel></rss>'''
CSV=b'observation_date,DGS10\n2026-10-19,4.1\n2026-10-20,4.2\n2026-10-21,.\n'

class TestData(unittest.TestCase):
    def test_rss_date_and_dedup_url(self):
        res=parse_feed(RSS,SOURCE,NOW)
        self.assertEqual(len(res),1)
        self.assertEqual(res[0]['url'],'https://example.org/post')
        self.assertEqual(res[0]['published_at'],'2026-10-22T05:40:00Z')
    def test_fred(self):
        result=parse_fred_csv(CSV,'DGS10')
        self.assertEqual(result[-1][1],4.2)
    def test_categorize(self):
        self.assertIn('Russia–Ucraina',categorise('Ukraine faces Russia',''))
    def test_bare_title_not_verified(self):
        article=parse_feed(RSS,SOURCE,NOW)
        items,topics,groups,alerts=analyse(article,NOW)
        self.assertIn('non verificata indipendentemente',items[0]['verification'])
        self.assertEqual(len(groups),0)
    def test_similarity(self):
        self.assertGreater(similarity('European Central Bank keeps interest rates unchanged','European Central Bank keeps interest rates unchanged today'),.65)
    def test_metrics_original(self):
        war=war_escalation({'gulf':80,'yemen':78,'ukraine':78,'me':60,'taiwan':33})
        stress=market_stress(18.44,.41,-2,.41,-.22)
        self.assertEqual((war,stress,global_risk(war,stress,50),conviction(7,3,2)),(90,16,56,20))
    def test_missing_inputs_no_fabrication(self):
        score=compute_stress([],NOW)
        self.assertIsNone(score['value'])
        self.assertEqual(score['coverage'],'0/5')
    def test_forecast_immutability_and_brier(self):
        initial={'op':'open','id':'P-1','claim':'Event occurs','probability':.6,'date':'2026-10-01','due':'2026-10-22','criterion':'Official data','base_value':'10'}
        result=project([initial,{'op':'revise','id':'P-1','at':'2026-10-10','note':'New evidence','probability_new':.9},{'op':'resolve','id':'P-1','at':'2026-10-22','status':'Confermata','proof':'https://example.org'}])
        self.assertAlmostEqual(result['brier'],.16)
        self.assertEqual(result['items'][0]['probability'],.6)
        with self.assertRaises(ValueError):project([initial,initial])

if __name__=='__main__':unittest.main()
