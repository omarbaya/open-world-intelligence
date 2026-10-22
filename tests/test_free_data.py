"""Network-free acceptance suite for free providers & no fabricated data."""
import io
import json
import unittest
import zipfile
from datetime import datetime,timezone
from core.free_data import (
    calendar_events,parse_ecb_csv,compare_gold,parse_cot_zip,parse_xaus_history,
    parse_alpha_fx_levels,alpha_daily,fmp_daily,calculate_conservative_sentiments,
    enrich,cache_valid)
T=datetime(2026,10,22,12,30,tzinfo=timezone.utc)

class FreeDataTest(unittest.TestCase):
    def test_calendar_timezone_and_no_assumed_consensus(self):
        sample={'events':[{'id':'cpi','date':'2026-10-22','release_at_utc':'2026-10-22T12:00:00Z',
             'time_precision':'minute','name':'CPI US','source_url':'https://www.bls.gov',
             'impact':'high','status':'confirmed'},
             {'id':'range','date':'2026-10-23','release_at_utc':'2026-10-23T12:00:00Z',
              'time_precision':'range','name':'Release range'},
             {'id':'past','date':'2026-10-10','name':'Old'}]}
        items=calendar_events(sample,T)
        self.assertEqual(len(items),2)
        self.assertEqual(items[0]['time_athens'],'15:00')
        self.assertIsNone(items[0]['consensus'])
        self.assertIsNone(items[1]['time_athens'])
    def test_ecb_primary_and_dates(self):
        csv=b'TIME_PERIOD,OBS_VALUE\n2026-10-20,1.1050\n2026-10-21,1.1060\n'
        x=parse_ecb_csv(csv,T)
        self.assertEqual(x['value'],1.106)
        self.assertEqual(x['source'],'BCE · EXR/D.USD.EUR.SP00.A')
        self.assertFalse(x['stale'])
        self.assertEqual(x['change_pct'],round(100*.001/1.105,4))
    def test_gold_requires_two_recent(self):
        q=[{'source':'A','value':4100,'as_of':'2026-10-22T12:10:00Z','url':'https://a.example'},
           {'source':'B','value':4105,'as_of':'2026-10-22T12:11:00Z','url':'https://b.example'}]
        x=compare_gold(q,T)
        self.assertEqual(x['value'],4105)
        self.assertEqual(x['quote_quality'],'indicative_shared_upstream')
        self.assertTrue(x['stale'])
    def test_gold_conflict_excludes_price(self):
        q=[{'source':'A','value':4100,'as_of':'2026-10-22T12:10:00Z'},
           {'source':'B','value':4230,'as_of':'2026-10-22T12:11:00Z'}]
        x=compare_gold(q,T)
        self.assertIsNone(x['value'])
        self.assertEqual(x['quote_quality'],'conflict')
        self.assertGreater(x['conflict_pct'],.5)
    def test_gold_one_or_stale_is_nd(self):
        q=[{'source':'A','value':4100,'as_of':'2026-10-22T08:10:00Z'},
           {'source':'B','value':4101,'as_of':'2026-10-22T12:11:00Z'}]
        self.assertIsNone(compare_gold(q,T)['value'])
    def test_cot_legacy_zip_and_net(self):
        rows=('Market and Exchange Names,As of Date in Form YYYY-MM-DD,CFTC Contract Market Code,Noncommercial Positions-Long (All),Noncommercial Positions-Short (All)\n'
          'GOLD - COMMODITY EXCHANGE INC.,2026-10-13,088691,100,75\n'
          'GOLD - COMMODITY EXCHANGE INC.,2026-10-20,088691,110,70\n'
          'EURO FX - CHICAGO MERCANTILE EXCHANGE,2026-10-20,099741,60,90\n'
          'E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE,2026-10-20,13874A,70,65\n'
          'E-MINI S&P CONSUMER DISC INDEX - CHICAGO MERCANTILE EXCHANGE,2026-10-20,138747,999,1\n')
        buff=io.BytesIO()
        with zipfile.ZipFile(buff,'w') as z:z.writestr('cftc.txt',rows)
        data=parse_cot_zip(buff.getvalue(),T)
        self.assertEqual(data['GC']['value'],40)
        self.assertEqual(data['GC']['change'],15)
        self.assertEqual(data['EUR']['value'],-30)
        self.assertEqual(data['ES']['value'],5)
    def test_spot_levels_correct_close_only(self):
        x=parse_xaus_history({'points':[
             {'d':'2026-10-19','c':4000,'h':4060,'l':3980},
             {'d':'2026-10-20','c':4010,'h':4070,'l':3990},
             {'d':'2026-10-21','c':4020,'h':4090,'l':4000},
             {'d':'2026-10-22','c':4030,'h':4100,'l':4010}]},T)
        self.assertEqual(x['c'],4020)
        self.assertEqual(x['wh'],4090)
        self.assertEqual(x['wl'],3980)
        self.assertIn('spot',x['instrument'])
    def test_alpha_daily_vendor_not_exchange(self):
        rows={'Time Series (Daily)':{'2026-10-21':{'4. close':'100.25'},'2026-10-20':{'4. close':'100'}}}
        x=alpha_daily(rows,'KTOS','Kratos')
        self.assertEqual(x['pct'],.25)
        self.assertIn('vendor',x['status'])
    def test_fmp_rejects_wrong_symbol(self):
        with self.assertRaises(Exception):fmp_daily([{'symbol':'WRONG','date':'2026-10-21','close':100}], 'NPK','National Presto')
    def test_no_unfounded_market_sentiment(self):
        z=calculate_conservative_sentiments({'markets':[],'indicators':{'war_escalation':{'value':80}}})
        self.assertIsNone(z['values']['gold'])
        self.assertEqual(z['values']['war'],60)
    def test_missing_provider_leaves_existing_news(self):
        # All network calls fail; the engine remains usable and no key leaks.
        def offline(url,**kwargs):raise OSError('network off')
        data,cache=enrich({'articles':[{'id':'news1'}],'markets':[],'indicators':{'market_stress':{'value':None}}},
                          now=T,transport=offline,environ={})
        self.assertEqual(data['articles'][0]['id'],'news1')
        self.assertIsNone(data['markets'][0]['value'] if data['markets'] else None)
        self.assertEqual(data['free_sources']['providers']['calendar']['status'],'error')
        self.assertNotIn('secretvalue',json.dumps(data['free_sources']).lower())
    def test_cache_avoids_calls(self):
        stamp={'fetched_at':{'calendar':'2026-10-22T12:00:00Z'}}
        self.assertTrue(cache_valid(stamp,'calendar',T,6))
        self.assertFalse(cache_valid(stamp,'calendar',T,0.25))

if __name__=='__main__':unittest.main()
