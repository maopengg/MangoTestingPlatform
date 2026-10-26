"""通过匿名 Git 协议获取 Gitee 的指定提交，不读取本机凭证。"""
import io
import stat
import tarfile
import tempfile
import zipfile
from urllib.parse import urlsplit

from dulwich import porcelain
from dulwich.config import ConfigFile


def download_public_git_archive(repo_url: str, commit_hash: str) -> bytes:
    parsed = urlsplit(repo_url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('公开仓库必须使用不含凭证的 HTTP(S) 地址')
    with tempfile.TemporaryDirectory(prefix='mango-pytest-public-') as directory:
        repository = porcelain.clone(
            repo_url, directory, bare=True, checkout=False, depth=1,
            config=ConfigFile(), errstream=io.BytesIO(),
        )
        try:
            identifier = commit_hash.encode('ascii')
            if identifier not in repository.object_store:
                porcelain.fetch(repository, repo_url, depth=None, errstream=io.BytesIO(), outstream=io.StringIO())
            stream = io.BytesIO()
            porcelain.archive(repository, identifier, outstream=stream, errstream=io.BytesIO())
        finally:
            repository.close()
    output = io.BytesIO()
    with tarfile.open(fileobj=io.BytesIO(stream.getvalue()), mode='r:*') as archive, \
            zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
        for member in archive.getmembers():
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError('Pytest 仓库快照只允许普通文件')
            info = zipfile.ZipInfo('repository/' + member.name)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | member.mode) << 16
            with archive.extractfile(member) as source:
                zipped.writestr(info, source.read())
    return output.getvalue()
