import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs
from urllib.request import urlopen

from django.test import SimpleTestCase

from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService as Resources


class EsDeleteRefreshTransportTests(SimpleTestCase):
    def test_concurrent_conditional_deletes_do_not_wait_for_refresh_or_force_it(self):
        requests = []
        lock = threading.Lock()

        class Handler(BaseHTTPRequestHandler):
            def do_DELETE(self):
                query = parse_qs(urlparse(self.path).query)
                # 模拟刷新周期超过客户端预算；老 wait_for 路径会等待并超时。
                if query.get('refresh') == ['wait_for']:
                    time.sleep(1)
                with lock:
                    requests.append(query)
                doc_id = urlparse(self.path).path.rsplit('/', 1)[-1]
                body = json.dumps({'_index': 'example_index', '_id': doc_id, 'result': 'deleted'}).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        class Server(ThreadingHTTPServer):
            request_queue_size = 32

        server = Server(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        target = SimpleNamespace(extra_config={}, host='127.0.0.1', port=server.server_port, user='', password='')
        try:
            with patch('src.apps.data_factory.services.cleanup.cleanup_resource.open_elasticsearch_request',
                       side_effect=lambda req, **kw: urlopen(req, timeout=0.5)), ThreadPoolExecutor(max_workers=10) as pool:
                results = list(pool.map(lambda i: Resources.request_document(target, 'example_index', str(i),
                    delete=True, timeout=0.5, expected={'_seq_no': i, '_primary_term': 1}), range(20)))
            self.assertEqual(len(results), 20)
            self.assertEqual(len(requests), 20)
            self.assertTrue(all(q['refresh'] == ['false'] and q['if_primary_term'] == ['1'] for q in requests))
            self.assertEqual({int(q['if_seq_no'][0]) for q in requests}, set(range(20)))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
