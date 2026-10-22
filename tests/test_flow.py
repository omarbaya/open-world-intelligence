import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path
from datetime import datetime,timezone
import json
from core import engine
NOW=datetime(2026,10,22,6,0,tzinfo=timezone.utc)
RSS=b'''<rss><channel><item><title>European Central Bank keeps interest rates unchanged</title><link>https://example.org/news?id=39&amp;utm_source=rss</link><description>Official rates story</description><pubDate>Thu, 22 Oct 2026 05:00:00 GMT</pubDate></item></channel></rss>'''
CSV=b'observation_date,VIXCLS\n2026-10-20,18\n2026-10-21,19\n'

class TestPipeline(unittest.TestCase):
    def test_success_then_offline_cache_marked(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/'config').mkdir()
            (p/'site/data').mkdir(parents=True)
            (p/'state').mkdir()
            (p/'config/feeds.json').write_text(json.dumps([{'name':'BBC World','url':'https://example.org/feed','type':'media'}]))
            (p/'config/markets.json').write_text(json.dumps([{'id':'VIX','name':'VIX','unit':'pt','source':'FRED','series':'VIXCLS','type':'index'}]))
            with patch.object(engine,'ROOT',p),patch.object(engine,'DATA',p/'site/data'):
                obj=engine.refresh(NOW,fetcher=lambda url:RSS,market_fetcher=lambda url:CSV)
                self.assertEqual(obj['quality']['feeds_ok'],1)
                self.assertEqual(len(obj['articles']),1)
                self.assertEqual(obj['articles'][0]['url'],'https://example.org/news?id=39')
                self.assertEqual(obj['markets'][0]['value'],19)
                self.assertTrue((p/'site/data/briefs/2026-10-22.md').exists())
                def error(url):raise OSError('Disconnected')
                obj2=engine.refresh(NOW.replace(hour=11),fetcher=error,market_fetcher=error)
                self.assertTrue(obj2['news_unavailable'])
                self.assertEqual(obj2['last_news_success'],obj['last_news_success'])
                self.assertEqual(len(obj2['articles']),1)
                self.assertTrue(obj2['markets'][0]['stale'])
                self.assertTrue(obj2['warnings'])
if __name__=='__main__':unittest.main()
