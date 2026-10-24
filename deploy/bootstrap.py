"""Create private deployment settings without overwriting existing credentials."""
import argparse
import os
from pathlib import Path
import secrets
from urllib.parse import urlsplit


SECRET_NAMES = (
    'MYSQL_ROOT_PASSWORD', 'MYSQL_PASSWORD', 'DJANGO_SECRET_KEY',
    'LIVE_STREAM_SIGNING_KEY', 'MANGO_INITIAL_ADMIN_PASSWORD',
    'MANGO_INITIAL_GUEST_PASSWORD',
)


def read_env(path):
    result = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, separator, value = line.partition('=')
        if not separator or key in result:
            raise ValueError('部署配置存在无效行或重复键')
        result[key] = value.strip().strip('"\'')
    return result


def validate(values):
    if any(not values.get(name) for name in SECRET_NAMES):
        raise ValueError('部署凭据缺失，请补全私有部署配置，不要删除已有数据库后重新生成凭据')
    port = int(values.get('WEB_PORT', '8000'))
    if not 1 <= port <= 65535:
        raise ValueError('WEB_PORT 必须在 1 到 65535 之间')
    public_url = urlsplit(values.get('PUBLIC_URL', ''))
    if public_url.scheme not in {'http', 'https'} or not public_url.netloc or public_url.username:
        raise ValueError('PUBLIC_URL 必须是完整的 http(s) 访问地址')
    if not Path(values.get('MANGO_DATA_DIR', '')).is_absolute():
        raise ValueError('MANGO_DATA_DIR 必须是绝对路径')


def initialize(path):
    if path.exists():
        values = read_env(path)
        validate(values)
        path.chmod(0o600)
        return values
    port = os.getenv('WEB_PORT', '8000')
    values = {
        'WEB_PORT': port,
        'WEB_BIND': os.getenv('WEB_BIND', '0.0.0.0'),
        'PUBLIC_URL': os.getenv('PUBLIC_URL', 'http://localhost:' + port),
        'MANGO_DATA_DIR': os.getenv('MANGO_DATA_DIR', '/mango_data'),
        'MYSQL_DATABASE': 'mango_server',
        'MYSQL_USER': 'mango',
        'NODE_HEAP_MB': '2560',
        **{name: secrets.token_hex(24) for name in SECRET_NAMES},
    }
    validate(values)
    if any('\n' in value or '\r' in value for value in values.values()):
        raise ValueError('配置值不可包含换行')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write('# 私有部署配置：请备份，不要提交到 Git。\n')
        stream.write('\n'.join(key + '=' + value for key, value in values.items()) + '\n')
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['init', 'get'])
    parser.add_argument('path', type=Path)
    parser.add_argument('key', nargs='?')
    args = parser.parse_args()
    try:
        values = initialize(args.path) if args.action == 'init' else read_env(args.path)
        if args.action == 'get':
            if args.key not in {'MANGO_DATA_DIR', 'PUBLIC_URL', 'WEB_PORT'}:
                raise ValueError('此命令只显示非敏感的部署参数')
            print(values[args.key])
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
