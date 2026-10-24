import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout

from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.services.api_info.curl_import import parse_import_curl


class CurlImportTests(unittest.TestCase):
    def test_browser_url_option_preserves_json_headers_and_query(self):
        command = '''curl --url 'https://example.com/api/recall?page=1' \\
  -H 'content-type: application/json' \\
  -H 'user-agent: Browser' \\
  --data-raw '{"query":"我有哪些记忆","trace":true,"include":{"chunks":null}}' '''
        parsed = parse_import_curl(command)
        self.assertEqual(parsed.url, 'https://example.com/api/recall?page=1')
        self.assertEqual(parsed.method, 'POST')
        self.assertEqual(parsed.header['user-agent'].strip(), 'Browser')
        self.assertEqual(parsed.json['query'], '我有哪些记忆')
        self.assertIsNone(parsed.json['include']['chunks'])

    def test_single_line_and_browser_flags(self):
        for command in (
            'curl https://example.com/api',
            'curl --url=https://example.com/api --compressed',
            'curl -s -S -L --insecure https://example.com/api',
            'curl -H "accept: */*" --url https://example.com/api --location',
            '  curl https://example.com/api  ',
        ):
            with self.subTest(command=command):
                parsed = parse_import_curl(command)
                self.assertEqual(parsed.url, 'https://example.com/api')
                self.assertEqual(parsed.method, 'GET')

    def test_json_empty_object_and_array_are_not_discarded(self):
        for body in ('{}', '[]'):
            parsed = parse_import_curl(f"curl https://example.com/api --data-raw '{body}'")
            self.assertEqual(parsed.method, 'POST')
            self.assertEqual(parsed.json, json.loads(body))

    def test_explicit_method_and_head(self):
        self.assertEqual(parse_import_curl('curl -I https://example.com/api').method, 'HEAD')
        self.assertEqual(parse_import_curl("curl https://example.com/api -X PUT -d '{}' ").method, 'PUT')

    def test_windows_newlines_and_option_like_payload_are_preserved(self):
        parsed = parse_import_curl('curl --url https://example.com/api \\\r\n --data-raw "--compressed"')
        self.assertEqual(parsed.data, '--compressed')
        self.assertEqual(parsed.method, 'POST')

    def test_invalid_input_is_business_error_without_printing_command(self):
        output = io.StringIO()
        for command in (None, '', 'curl', 'curl --url', 'curl --url https://example.com -H',
                        "curl 'https://example.com", 'curl ftp://example.com/a',
                        'curl --unknown secret https://example.com', 'curl --help',
                        'curl https://example.com https://example.org', 'echo https://example.com'):
            with self.subTest(command=command), redirect_stderr(output), redirect_stdout(output):
                with self.assertRaises(AutoApiError) as raised:
                    parse_import_curl(command)
                self.assertEqual(raised.exception.code, 31216)
        self.assertEqual(output.getvalue(), '')
