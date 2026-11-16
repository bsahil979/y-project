import unittest
from unittest.mock import patch, Mock
from services import sentiment_analyzer as s

class SentimentTests(unittest.TestCase):
    def test_transformers_shapes(self):
        scores = [{'label':'positive','score':.8},{'label':'negative','score':.1},{'label':'neutral','score':.1}]
        for output in (scores, [scores]):
            with patch.object(s, '_get_finbert', return_value=Mock(return_value=output)):
                self.assertAlmostEqual(s._score_with_finbert('Profit rises')['compound'], .7)
    def test_inference_fallback(self):
        with patch.object(s, '_get_finbert', return_value=Mock(side_effect=RuntimeError('offline'))):
            self.assertEqual(s._score_with_finbert('Profit rises')['model'], 'VADER')
    def test_no_news(self):
        with patch.object(s, '_fetch_yahoo_news', return_value=[]), patch.object(s, '_fetch_google_news', return_value=[]):
            result=s.get_sentiment_analysis(' tcs.ns ')
            self.assertEqual(result['ticker'], 'TCS.NS')
            self.assertEqual(result['status'], 'no_news')
            self.assertEqual(result['confidence'], 0)
    def test_indian_search(self):
        with patch.object(s, 'GNews') as news, patch.object(s, '_news_identity', return_value='Tata Consultancy Services'):
            news.return_value.get_news.return_value=[]
            s._fetch_google_news('TCS.NS')
            self.assertEqual(news.call_args.kwargs['country'], 'IN')
            self.assertIn('Tata Consultancy Services', news.return_value.get_news.call_args.args[0])
    def test_invalid_symbol(self):
        with self.assertRaises(ValueError): s.get_sentiment_analysis('bad/ticker')

if __name__ == '__main__': unittest.main()
