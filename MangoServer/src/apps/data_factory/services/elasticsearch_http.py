import io
from time import monotonic
from contextlib import contextmanager
from urllib.error import HTTPError, URLError

import httpx

from src.apps.data_factory.services.protocol_pool import ProtocolPoolRegistry
from src.apps.data_factory.services.datasource_timing import DatasourceTimingService as Timing
from src.apps.data_factory.enums.performance import DatasourceTimingPhaseEnum as Phase
from src.apps.data_factory.services.data_source_error import DataSourceErrorService


class ElasticsearchResponseReader:
    def __init__(self, response):
        self.status = response.status_code
        self.headers = response.headers
        self._chunks = response.iter_bytes(chunk_size=65536)
        self._buffer = b''

    def read(self, amount=1_048_577):
        with Timing.measure(Phase.FETCH):
            return self._read(amount)

    def _read(self, amount):
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
            from contextlib import ExitStack
            connecting = {}

            def trace(name, info):
                # httpcore 仅提供阶段名；不读取 info 中的 URL、请求头或 socket。
                stage, _, event = name.rpartition('.')
                if stage not in {'connection.connect_tcp', 'connection.start_tls'}:
                    return
                if event == 'started':
                    connecting[stage] = monotonic()
                elif event in {'complete', 'failed'} and stage in connecting:
                    Timing.add(Phase.CONNECT, monotonic() - connecting.pop(stage))

            with ExitStack() as stack:
                with Timing.measure(Phase.EXECUTE):
                    response = stack.enter_context(client.stream(
                        request.get_method(), request.full_url, headers=dict(request.header_items()),
                        content=request.data, timeout=httpx.Timeout(timeout), extensions={'trace': trace}))
                reader = ElasticsearchResponseReader(response)
                if response.status_code >= 300:
                    raise HTTPError(request.full_url, response.status_code, 'Elasticsearch HTTP error',
                                    response.headers, io.BytesIO(reader.read()))
                yield reader
    except httpx.TimeoutException as error:
        raise DataSourceErrorService.preserve_execution_state(
            error, TimeoutError('Elasticsearch request deadline exceeded')) from error
    except httpx.HTTPError as error:
        raise DataSourceErrorService.preserve_execution_state(
            error, URLError('Elasticsearch transport failed')) from error
