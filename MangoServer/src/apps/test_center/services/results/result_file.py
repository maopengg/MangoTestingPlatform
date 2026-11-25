"""执行结果文件的无损编码、兼容读取及 HTTP 传输协商。"""
import gzip
from contextlib import contextmanager


class OwnedGzipReader(gzip.GzipFile):
    """HTTP 响应关闭解压流时，同时释放底层存储文件。"""
    def close(self):
        source = self.fileobj
        try:
            super().close()
        finally:
            if source is not None:
                source.close()

    def seekable(self):
        # FileResponse 不应为计算 Content-Length 先完整解压一次。
        return False


class ExecutionResultFileService:
    @staticmethod
    def encode(content: bytes) -> bytes:
        return gzip.compress(content, compresslevel=6, mtime=0)

    @staticmethod
    def is_gzip(source) -> bool:
        position = source.tell()
        try:
            return source.read(2) == b'\x1f\x8b'
        finally:
            source.seek(position)

    @classmethod
    @contextmanager
    def decoded(cls, source):
        with source:
            if cls.is_gzip(source):
                with gzip.GzipFile(fileobj=source, mode='rb') as decoded:
                    yield decoded
            else:
                yield source

    @classmethod
    def read(cls, source, limit=None):
        """限额始终针对解压后的字节；多读一字节供调用方识别超限。"""
        with cls.decoded(source) as decoded:
            return decoded.read() if limit is None else decoded.read(max(0, limit) + 1)

    @staticmethod
    def accepts_gzip(accept_encoding):
        qualities = {}
        for entry in (accept_encoding or '').lower().split(','):
            parts = [part.strip() for part in entry.split(';')]
            quality = 1.0
            for parameter in parts[1:]:
                if parameter.startswith('q='):
                    try:
                        quality = float(parameter[2:])
                    except ValueError:
                        quality = 0.0
            qualities[parts[0]] = quality
        return 0 < qualities.get('gzip', qualities.get('*', 0)) <= 1

    @classmethod
    def transport(cls, source, accept_encoding):
        if not cls.is_gzip(source):
            return source, None
        if cls.accepts_gzip(accept_encoding):
            return source, 'gzip'
        return OwnedGzipReader(fileobj=source, mode='rb'), None
