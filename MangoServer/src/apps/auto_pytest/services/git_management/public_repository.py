import io
import stat
import tarfile
import tempfile
import zipfile
from urllib.parse import urlsplit

from dulwich import porcelain
from dulwich.config import ConfigFile

from src.apps.auto_pytest.exceptions import AutoPytestError, PYTEST_REPOSITORY_FAILED


def download_public_git_archive(repo_url: str, commit_hash: str) -> bytes:
    parsed = urlsplit(repo_url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
        raise AutoPytestError(PYTEST_REPOSITORY_FAILED, value=('公开仓库请使用不含凭证的 HTTP(S) 地址',))
    try:
        with tempfile.TemporaryDirectory(prefix='mango-public-repository-') as directory:
            # Gitee 的 zipball API 要求 Token；公开代码改走 Git 协议，且不读取本机凭证配置。
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
                if not (member.isfile() or member.issym()):
                    raise AutoPytestError(PYTEST_REPOSITORY_FAILED, value=('仓库快照包含不支持的文件类型',))
                # 保留链接类型，由统一快照安装器拒绝链接；不将链接静默转成普通文件。
                info = zipfile.ZipInfo('repository/' + member.name)
                info.create_system = 3
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = ((stat.S_IFLNK if member.issym() else stat.S_IFREG) | member.mode) << 16
                if member.issym():
                    data = member.linkname.encode('utf-8')
                else:
                    with archive.extractfile(member) as source:
                        data = source.read()
                zipped.writestr(info, data)
        return output.getvalue()
    except AutoPytestError:
        raise
    except Exception as error:
        raise AutoPytestError(
            PYTEST_REPOSITORY_FAILED, value=('公开仓库下载失败，请检查仓库地址、网络及访问权限',),
        ) from error
