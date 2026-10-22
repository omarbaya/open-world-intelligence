import unittest
from scripts.ai_pipeline import normalize_items, SECTIONS

class AITest(unittest.TestCase):
    def test_sections(self):
        self.assertEqual(len(SECTIONS), 13)
    def test_unknown_article_rejected(self):
        self.assertEqual(normalize_items([{'article_id':'invalid'}], {'valid'}), [])

if __name__ == '__main__':
    unittest.main()
