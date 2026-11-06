import io
from contextlib import contextmanager
from urllib.error import HTTPError, URLError

import httpx

from src.apps.data_factory.services.protocol_pool import ProtocolPoolRegistry


class ElasticsearchResponseReader:
    def __init__(self, response):
        self.status = response.status_code
        self.headers = response.headers
        self._chunks = response.iter_bytes(chunk_size=65536)
        self._buffer = b''

    def read(self, amount=1_048_577):
        if amount is None or amount < 0:
            amount = 1_048_577
        while len(self._buffer) < amount:
            chunk = next(self._chunks, None)
            if chunk is None:
                break
            self._buffer += chunk
        result, self._buffer = self._buffer[:amount], self._buffer[amount:]
        return result


@contextmanager
def open_elasticsearch_request(request, *, timeout, target, context=None):
    def factory(size):
        return httpx.Client(verify=context if context is not None else True, trust_env=False,
                            follow_redirects=False,
                            limits=httpx.Limits(max_connections=size, max_keepalive_connections=size,
                                               keepalive_expiry=30))

    try:
        with ProtocolPoolRegistry.borrow(target, 'elasticsearch', factory) as client:
            with client.stream(request.get_method(), request.full_url, headers=dict(request.header_items()),
                               content=request.data, timeout=httpx.Timeout(timeout)) as response:
                reader = ElasticsearchResponseReader(response)
                if response.status_code >= 300:
                    raise HTTPError(request.full_url, response.status_code, 'Elasticsearch HTTP error',
                                    response.headers, io.BytesIO(reader.read()))
                yield reader
    except httpx.TimeoutException as error:
        raise TimeoutError('Elasticsearch request deadline exceeded') from error
    except httpx.HTTPError as error:
        raise URLError('Elasticsearch transport failed') from error
