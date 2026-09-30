import unittest
from unittest.mock import call, patch

from app import QUOTES, app


class QuoteGeneratorTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_home_renders_a_quote(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.content_type)
        self.assertTrue(any(quote["text"].encode() in response.data for quote in QUOTES))

    def test_home_disables_browser_caching(self):
        response = self.client.get("/")

        self.assertEqual(response.headers.get("Cache-Control"), "no-store")

    def test_each_request_selects_a_quote(self):
        with patch("app.choice", side_effect=[QUOTES[0], QUOTES[1]]) as choose_quote:
            first_response = self.client.get("/")
            second_response = self.client.get("/")

        self.assertIn(QUOTES[0]["text"].encode(), first_response.data)
        self.assertIn(QUOTES[1]["text"].encode(), second_response.data)
        self.assertEqual(choose_quote.call_args_list, [call(QUOTES), call(QUOTES)])


if __name__ == "__main__":
    unittest.main()