"""Read user configuration and render private Compose/browser configuration."""
import argparse
import copy
import contextlib
import io
import runpy
import json
import os
from pathlib import Path
import re
import secrets
import ipaddress
from urllib.parse import urlsplit

SECRET_NAMES = ('MYSQL_ROOT_PASSWORD', 'MYSQL_PASSWORD', 'DJANGO_SECRET_KEY',
                'LIVE_STREAM_SIGNING_KEY', 'MANGO_INITIAL_ADMIN_PASSWORD', 'MANGO_INITIAL_GUEST_PASSWORD')
PRIVATE_INPUT_NAMES = set(SECRET_NAMES) | {
    'S3_ACCESS_KEY', 'S3_SECRET_KEY', 'ACTUATOR_PASSWORD',
    'MINIO_ROOT_PASSWORD', 'MINIO_STORAGE_ACCESS_KEY', 'MINIO_STORAGE_SECRET_KEY',
}



def read_env(path):
    """Read literal dotenv values, including quoted #/$/quotes; never execute shell code."""
    return parse_env(path.read_text(), path.name)


def parse_env(text, label='配置文件'):
    result = {}
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)', line)
        if not match or match[1] in result:
            raise ValueError(f'{label} 第 {number} 行格式错误或变量重复')
        key, raw = match.groups()
        if raw[:1] in {"'", '"'}:
            quote = raw[0]
            end = raw.rfind(quote)
            if end == 0 or (raw[end+1:].strip() and not raw[end+1:].lstrip().startswith('#')):
                raise ValueError(f'{label} 第 {number} 行引号未闭合')
            value = raw[1:end]
        else:
            value = re.split(r'\s+#', raw, maxsplit=1)[0].rstrip()
        result[key] = value
    return result


# Keep defaults independent of the user's editable, Git-tracked configuration.
DEFAULTS = read_env(Path(__file__).resolve().parent / 'defaults.env')
BACKEND_SERVICES = ('mango_server', 'scheduler_service', 'api_worker_1', 'mcp_service', 'realtime_service', 'monitoring_service')


def boolean(values, key, default=False):
    raw = values.get(key, str(default)).lower()
    if raw not in {'true', 'false', '1', '0', 'yes', 'no', 'on', 'off'}:
        raise ValueError(f'{key} 必须填写 true 或 false')
    return raw in {'true', '1', 'yes', 'on'}


def url(value, key, schemes=('http', 'https')):
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise ValueError(f'{key} 地址格式不正确，请修改 .env.example') from None
    if parsed.scheme not in schemes or not parsed.hostname or parsed.username or parsed.password or re.search(r'[\s;{}$\\"\x00-\x1f]', value):
        raise ValueError(f'{key} 必须是合法地址，不能包含凭据或配置指令')
    if port is not None and not 1 <= port <= 65535:
        raise ValueError(f'{key} 地址端口必须在 1 到 65535 之间')
    return parsed


def placeholder(value):
    return bool(re.search(r'change[_-]?me|replace[_-]?me|your[_-](?:server|host|ip|domain|database|password|access|secret)|请填写|待填写|填写', str(value), re.I))


def validate_user_inputs(values):
    """Reject missing deployment inputs without exposing their values or writing state."""
    required = ['PUBLIC_URL', 'MYSQL_DATABASE', 'MYSQL_USER']
    if values.get('MYSQL_MODE') == 'external':
        required += ['MYSQL_HOST', 'MYSQL_PASSWORD']
    elif values.get('MYSQL_MODE') == 'settings':
        required = ['PUBLIC_URL']  # Database values are checked after reading the selected settings.
    if values.get('FILE_STORAGE_BACKEND') in {'minio', 'tos'}:
        required += ['S3_BUCKET']
        if values.get('FILE_STORAGE_BACKEND') == 'tos' or values.get('MINIO_MODE') == 'external':
            required += ['S3_ENDPOINT', 'S3_ACCESS_KEY', 'S3_SECRET_KEY', 'S3_PUBLIC_BASE_URL']
        if values.get('FILE_STORAGE_BACKEND') == 'tos':
            required += ['S3_REGION']
    if boolean(values, 'ACTUATOR_ENABLED'):
        required += ['ACTUATOR_HOST', 'ACTUATOR_USERNAME', 'ACTUATOR_PASSWORD']
    invalid = [key for key in required if not str(values.get(key, '')).strip() or placeholder(values.get(key, ''))]
    public = values.get('PUBLIC_URL', '')
    if public and not placeholder(public):
        host = url(public, 'PUBLIC_URL').hostname.rstrip('.')
        try:
            address = ipaddress.ip_address(host)
            local_only = address.is_loopback or address.is_unspecified or address.is_multicast
            if getattr(address, 'ipv4_mapped', None):
                local_only = local_only or address.ipv4_mapped.is_loopback or address.ipv4_mapped.is_unspecified
        except ValueError:
            local_only = host == 'localhost' or host.endswith('.localhost') or '*' in host
        if local_only:
            invalid.append('PUBLIC_URL')
    if invalid:
        hint = '；PUBLIC_URL 必须为客户端实际访问的 IP 或域名，不能使用占位符、localhost 或监听地址' if 'PUBLIC_URL' in invalid else ''
        raise ValueError('请在 .env.example 填写真实有效的必填配置：' + ', '.join(dict.fromkeys(invalid)) + hint)


def validate(v):
    heap = v.get('NODE_HEAP_MB', 'auto')
    if heap != 'auto' and (not heap.isdigit() or not 512 <= int(heap) <= 65536):
        raise ValueError('NODE_HEAP_MB 使用 auto 或 512～65536 的整数')
    for key, modes in [('MYSQL_MODE', {'internal','external','settings'}),('MINIO_MODE', {'internal','external'})]:
        if v[key] not in modes:
            raise ValueError(key+' 的模式不合法')
    if v['FILE_STORAGE_BACKEND'] not in {'local', 'minio', 'tos'}:
        raise ValueError('FILE_STORAGE_BACKEND 只支持 local / minio / tos')
    for key in ('WEB_PORT', 'MYSQL_PORT', 'API_PORT', 'MYSQL_EXPOSE_PORT', 'MINIO_CONSOLE_PORT'):
        if key not in {'WEB_PORT','MYSQL_PORT'} and not v.get(key):
            continue
        try:
            valid = 1 <= int(v[key]) <= 65535
        except (ValueError, TypeError):
            valid = False
        if not valid:
            raise ValueError(f'{key} 必须在 1 到 65535 之间')
    if v.get('API_PORT') == v['WEB_PORT']:
        raise ValueError('API_PORT 与 WEB_PORT 不可相同；同源部署请留空 API_PORT')
    if v['DEPLOY_TARGET'] not in {'compose','k8s'}:
        raise ValueError('DEPLOY_TARGET 只支持 compose / k8s')
    for key in ('MONITORING_ENABLED','MYSQL_BINLOG','ACTUATOR_ENABLED'):
        boolean(v,key)
    if not v['API_WORKER_COUNT'].isdigit() or not 1<=int(v['API_WORKER_COUNT'])<=8:raise ValueError('API_WORKER_COUNT 必须在 1 到 8 之间')
    for key in ('LOG_MAX_FILE','API_THREAD_POOL_SIZE','UVICORN_WORKERS','ACTUATOR_WEB_PARALLEL','ACTUATOR_PYTEST_PARALLEL','ACTUATOR_QUEUE_SIZE'):
        if not str(v[key]).isdigit() or int(v[key])<1:raise ValueError(key+' 必须为正整数')
    if not re.fullmatch(r'[1-9][0-9]*[kmg]',v['LOG_MAX_SIZE']):raise ValueError('LOG_MAX_SIZE 使用 10m 等正整数大小')
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*',v['COMPOSE_PROJECT_NAME']):raise ValueError('COMPOSE_PROJECT_NAME 格式不合法')
    try:routes=json.loads(v['EXTRA_HTTP_ROUTES'])
    except (ValueError,TypeError):raise ValueError('EXTRA_HTTP_ROUTES 必须为 JSON 对象') from None
    if not isinstance(routes,dict):raise ValueError('EXTRA_HTTP_ROUTES 必须为 JSON 对象')
    for prefix,upstream in routes.items():
        if not re.fullmatch(r'/[a-zA-Z0-9_-]+/',prefix) or prefix in {'/api/','/ws/','/mcp/','/minio/','/mango-file/'}:
            raise ValueError('EXTRA_HTTP_ROUTES 路径不合法或与平台路径冲突')
        u=url(upstream,'EXTRA_HTTP_ROUTES')
        if u.path not in {'','/'} or u.query or u.fragment:raise ValueError('EXTRA_HTTP_ROUTES 上游不能含路径')
    if v.get('API_PUBLIC_URL'):url(v['API_PUBLIC_URL'],'API_PUBLIC_URL')
    if boolean(v,'ACTUATOR_ENABLED'):
        url(v['ACTUATOR_HOST'],'ACTUATOR_HOST')
        if not v.get('ACTUATOR_PASSWORD'):raise ValueError('启用执行器必须填写 ACTUATOR_PASSWORD')
    required = ['PUBLIC_URL', 'BACKEND_UPSTREAM', 'MANGO_DATA_DIR', 'MYSQL_DATABASE' , 'MYSQL_USER', 'MYSQL_PASSWORD', 'DJANGO_SECRET_KEY',
                'LIVE_STREAM_SIGNING_KEY', 'MANGO_INITIAL_ADMIN_PASSWORD', 'MANGO_INITIAL_GUEST_PASSWORD']
    required += ['MYSQL_ROOT_PASSWORD'] if v['MYSQL_MODE'] == 'internal' else ['MYSQL_HOST']
    if v['MYSQL_MODE'] == 'internal' and v['MYSQL_USER'] == 'root':
        raise ValueError('内置 MySQL 请配置独立 MYSQL_USER（例如 mango），不能使用 root')
    if v['FILE_STORAGE_BACKEND'] != 'local':
        if not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]', v.get('S3_BUCKET','')):
            raise ValueError('S3_BUCKET 必须是合法的 S3 桶名')
        required += ['S3_ENDPOINT', 'S3_BUCKET', 'S3_ACCESS_KEY', 'S3_SECRET_KEY', 'S3_PUBLIC_BASE_URL']
        if v['FILE_STORAGE_BACKEND'] == 'tos':
            required += ['S3_REGION']
        if v.get('S3_ENDPOINT'):
            endpoint = v['S3_ENDPOINT']
            parsed = url(endpoint if '://' in endpoint else 'https://' + endpoint, 'S3_ENDPOINT')
            if parsed.path not in {'', '/'} or parsed.query or parsed.fragment:
                raise ValueError('S3_ENDPOINT 只填写主机和端口，不含桶名或路径')
        if v.get('S3_PUBLIC_BASE_URL'):
            url(v['S3_PUBLIC_BASE_URL'], 'S3_PUBLIC_BASE_URL')
        for key in ('S3_USE_HTTPS', 'S3_PRESIGNED', 'S3_AUTO_CREATE_BUCKET', 'S3_VIRTUAL_HOST_STYLE'):
            boolean(v, key)
    missing = [key for key in required if not v.get(key)]
    if missing:
        raise ValueError('请在 .env.example 补齐：' + ', '.join(missing))
    active = required + ['API_PUBLIC_URL', 'FRONTEND_API_BASE', 'FRONTEND_SOCKET_URL', 'CORS_ALLOWED_ORIGINS']
    if boolean(v, 'ACTUATOR_ENABLED'):
        active += ['ACTUATOR_HOST', 'ACTUATOR_USERNAME', 'ACTUATOR_PASSWORD']
    unresolved = [key for key in active if v.get(key) and placeholder(v[key])]
    if unresolved:
        raise ValueError('请在 .env.example 替换以下占位配置：' + ', '.join(dict.fromkeys(unresolved)))
    for key in ('PUBLIC_URL', 'BACKEND_UPSTREAM'):
        p = url(v[key], key)
        if p.path not in {'', '/'} or p.query or p.fragment:
            raise ValueError(f'{key} 只填写站点地址，不含路径、查询或片段')
    if not Path(v['MANGO_DATA_DIR']).is_absolute():
        raise ValueError('MANGO_DATA_DIR 必须是绝对路径')
    api = v['FRONTEND_API_BASE']
    if api != '/api':
        p = url(api, 'FRONTEND_API_BASE')
        if p.path.rstrip('/') != '/api' or p.query or p.fragment:
            raise ValueError('FRONTEND_API_BASE 使用 /api 或完整的 https://域名/api')
        if urlsplit(v['PUBLIC_URL']).scheme == 'https' and p.scheme != 'https':
            raise ValueError('HTTPS 前端不能直连 HTTP API')
    if v.get('FRONTEND_SOCKET_URL'):
        socket = url(v['FRONTEND_SOCKET_URL'], 'FRONTEND_SOCKET_URL', ('ws', 'wss'))
        if urlsplit(v['PUBLIC_URL']).scheme == 'https' and socket.scheme != 'wss':
            raise ValueError('HTTPS 前端必须使用 WSS')
    for origin in filter(None, (x.strip() for x in v['CORS_ALLOWED_ORIGINS'].split(','))):
        p = url(origin, 'CORS_ALLOWED_ORIGINS')
        if p.path not in {'', '/'} or p.query or p.fragment:
            raise ValueError('跨域来源只能填写协议、域名和端口')


def database_from_settings(root, environment):
    environment='master' if environment=='prod' else environment
    if environment not in {'dev','test','master'}:
        raise ValueError('DJANGO_ENV 只支持 dev / test / master / prod')
    server=root/'MangoServer'
    previous=Path.cwd()
    try:
        os.chdir(server)
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            data=runpy.run_path(str((server/'src/settings'/(environment+'.py')).resolve()))
        fields={'MYSQL_HOST':'MYSQL_IP','MYSQL_PORT':'MYSQL_PORT','MYSQL_DATABASE':'MYSQL_DB_NAME','MYSQL_USER':'MYSQL_USER','MYSQL_PASSWORD':'MYSQL_PASSWORD'}
        result={key:str(data[source]) for key,source in fields.items()}
        if any(not value for value in result.values()):raise ValueError()
        return result
    except Exception:
        raise ValueError('无法读取所选环境配置中的 MySQL 参数，请检查 DJANGO_ENV 和 MangoServer/src/settings 对应文件') from None
    finally:
        os.chdir(previous)


def resolve(raw, root=None):
    v = {**DEFAULTS, **raw}
    # Legacy .env using an explicit database host means external MySQL unless a mode is specified.
    if 'MYSQL_MODE' not in raw and raw.get('MYSQL_HOST') not in {None, '', 'db'}:
        v['MYSQL_MODE'] = 'external'
    if v['MYSQL_MODE'] == 'settings':
        v.update(database_from_settings((root or Path(__file__).resolve().parent.parent).resolve(),v['DJANGO_ENV']))
    if v['MYSQL_MODE'] == 'internal':
        v['MYSQL_HOST'], v['MYSQL_PORT'] = 'db', '3306'
    for target, old in {
        'S3_ENDPOINT': 'MINIO_STORAGE_ENDPOINT', 'S3_BUCKET': 'MINIO_STORAGE_MEDIA_BUCKET_NAME',
        'S3_ACCESS_KEY': 'MINIO_STORAGE_ACCESS_KEY', 'S3_SECRET_KEY': 'MINIO_STORAGE_SECRET_KEY',
        'S3_PUBLIC_BASE_URL': 'MINIO_PUBLIC_BASE_URL', 'S3_REGION': 'MINIO_STORAGE_REGION',
        'S3_USE_HTTPS': 'MINIO_STORAGE_USE_HTTPS', 'S3_PRESIGNED': 'MINIO_STORAGE_MEDIA_USE_PRESIGNED',
    }.items():
        if target not in raw and old in raw:
            v[target] = raw[old]
    if v['FILE_STORAGE_BACKEND'] == 'minio' and v['MINIO_MODE'] == 'internal':
        v['S3_ENDPOINT'] = 'minio:9000'
        v['S3_ACCESS_KEY'] = raw.get('MINIO_ROOT_USER') or raw.get('S3_ACCESS_KEY') or 'mango'
        v['S3_SECRET_KEY'] = raw.get('MINIO_ROOT_PASSWORD') or raw.get('S3_SECRET_KEY', '')
        v['S3_USE_HTTPS'] = 'false'
        v['S3_PUBLIC_BASE_URL'] = raw.get('S3_PUBLIC_BASE_URL') or v['PUBLIC_URL'].rstrip('/') + '/minio/' + (raw.get('S3_BUCKET') or 'mango-file')
    v.setdefault('S3_BUCKET', 'mango-file')
    endpoint = v.get('S3_ENDPOINT', '')
    if '://' in endpoint:
        parsed = url(endpoint, 'S3_ENDPOINT')
        if parsed.path not in {'', '/'} or parsed.query or parsed.fragment:
            raise ValueError('S3_ENDPOINT 不应包含桶名或路径')
        v['S3_ENDPOINT'] = parsed.netloc
        v['S3_USE_HTTPS'] = str(parsed.scheme == 'https').lower()
    cloud = v['FILE_STORAGE_BACKEND'] == 'tos'
    v.setdefault('S3_USE_HTTPS', 'true')
    v.setdefault('S3_PRESIGNED', 'true')
    if not v.get('S3_AUTO_CREATE_BUCKET'): v['S3_AUTO_CREATE_BUCKET'] = 'false' if cloud else 'true'
    if not v.get('S3_VIRTUAL_HOST_STYLE'): v['S3_VIRTUAL_HOST_STYLE'] = 'true' if cloud else 'false'
    validate(v)
    return v


def private_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary=path.with_name(path.name+'.tmp-'+secrets.token_hex(6))
    try:
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()


def initialize(path, overrides=None, dry_run=False):
    existed = path.exists()
    raw = read_env(path) if existed else {}
    original = dict(raw)
    # Keep historical deployment credentials; migrate the file only when .env is absent.
    old = path.with_name('.env.deploy')
    if not existed and old.exists():
        raw = read_env(old)
    elif old.exists():
        previous = read_env(old)
        for key in SECRET_NAMES[2:]:
            if not raw.get(key) and previous.get(key):
                raw[key] = previous[key]
    if overrides is not None:
        raw.update({key: value for key, value in overrides.items()
                    if value or key not in PRIVATE_INPUT_NAMES or not raw.get(key)})
        for canonical, aliases in {
            'S3_SECRET_KEY': ('MINIO_ROOT_PASSWORD', 'MINIO_STORAGE_SECRET_KEY'),
            'S3_ACCESS_KEY': ('MINIO_ROOT_USER', 'MINIO_STORAGE_ACCESS_KEY'),
        }.items():
            if overrides.get(canonical):
                for alias in aliases:
                    raw.pop(alias, None)
    if raw.get('MYSQL_MODE', 'external' if raw.get('MYSQL_HOST') not in {None, '', 'db'} else 'internal') == 'external' and not raw.get('MYSQL_PASSWORD'):
        raise ValueError('请在 .env.example 填写外部数据库 MYSQL_PASSWORD，不自动生成外部数据库密码')
    generated = {}
    for name in SECRET_NAMES:
        if raw.get('MYSQL_MODE')=='settings' and name in {'MYSQL_PASSWORD','MYSQL_ROOT_PASSWORD'}:continue
        if not raw.get(name):
            generated[name] = secrets.token_hex(24)
    if raw.get('FILE_STORAGE_BACKEND') == 'minio' and raw.get('MINIO_MODE', 'internal') == 'internal' and not (raw.get('MINIO_ROOT_PASSWORD') or raw.get('S3_SECRET_KEY')):
        generated['S3_SECRET_KEY'] = secrets.token_hex(24)
    # Never invent a new password for an existing database configuration.
    if raw.get('MYSQL_MODE','internal')=='internal' and existed and not raw.get('MYSQL_PASSWORD') and raw.get('MYSQL_DATABASE') and any((Path(raw.get('MANGO_DATA_DIR') or DEFAULTS['MANGO_DATA_DIR'])/'mysql').glob('*')):
        raise ValueError('已有数据库缺少 MYSQL_PASSWORD，请在 .env.example 填写原密码')
    v = resolve({**raw, **generated},path.parent)
    if dry_run:
        return v
    inputs = {**DEFAULTS, **raw, **generated}
    # Persist user inputs, not derived URLs; blank automatic values must stay automatic.
    for key,old in {'S3_ENDPOINT':'MINIO_STORAGE_ENDPOINT','S3_BUCKET':'MINIO_STORAGE_MEDIA_BUCKET_NAME',
                    'S3_ACCESS_KEY':'MINIO_STORAGE_ACCESS_KEY','S3_SECRET_KEY':'MINIO_STORAGE_SECRET_KEY',
                    'S3_PUBLIC_BASE_URL':'MINIO_PUBLIC_BASE_URL','S3_REGION':'MINIO_STORAGE_REGION',
                    'S3_USE_HTTPS':'MINIO_STORAGE_USE_HTTPS','S3_PRESIGNED':'MINIO_STORAGE_MEDIA_USE_PRESIGNED'}.items():
        if key not in raw and old in raw:inputs[key]=v[key]
    if 'MYSQL_MODE' not in raw and raw.get('MYSQL_HOST') not in {None,'','db'}:inputs['MYSQL_MODE']='external'
    if overrides is not None:
        private_write(path, '\n'.join(key + "='" + value + "'" for key, value in inputs.items()) + '\n')
        return v
    if not existed:
        template = path.with_name('.env.example')
        text = template.read_text() if template.exists() else ''
        lines = []
        seen = set()
        for line in text.splitlines():
            m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=', line)
            if m:
                key = m[1]; seen.add(key)
                line = key + '=' + "'" + inputs.get(key, '') + "'"
            lines.append(line)
        for key, value in {**raw, **generated}.items():
            if key not in seen:
                lines.append(key + '=' + "'" + value + "'")
        private_write(path, '\n'.join(lines) + '\n')
    else:
        template = path.with_name('.env.example')
        missing = {key: value for key, value in {**raw, **generated}.items() if key not in original}
        if template.exists():
            for line in template.read_text().splitlines():
                match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=', line)
                if match and match[1] not in original:
                    missing[match[1]] = inputs.get(match[1], '')
        text=path.read_text()
        for key,value in generated.items():
            if key in original and not original[key]:
                text=re.sub(r'^(?:export\s+)?'+re.escape(key)+r'\s*=.*$',lambda _:key+"='"+value+"'",text,flags=re.M)
        if text!=path.read_text():private_write(path,text)
        if missing:
            with path.open('a') as stream:
                stream.write('\n# 补齐的部署选项和密钥；已有配置保留，说明见 .env.example。\n')
                stream.write('\n'.join(k + '=' + "'" + val + "'" for k, val in missing.items()) + '\n')
        path.chmod(0o600)
    return v


def configuration_text(text, values):
    """Replace literal assignments while retaining the maintained comments."""
    seen = set()
    lines = []
    for line in text.splitlines():
        match = re.match(r'^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=', line)
        if match and match[1] in values:
            key = match[1]
            seen.add(key)
            line = key + "='" + values[key] + "'"
        lines.append(line)
    lines.extend(key + "='" + value + "'" for key, value in values.items() if key not in seen)
    return '\n'.join(lines) + '\n'


def initialize_example(path, dry_run=False):
    root = path.parent
    editable = read_env(path)
    marker = root / 'deploy/generated/example-input.json'
    private = path.with_name('.env')
    legacy = private if private.exists() else path.with_name('.env.deploy')
    adopted = False
    if not marker.exists() and legacy.exists():
        # First upgrade: carry forward previous settings where the template is untouched.
        previous = read_env(legacy)
        if editable.get('NODE_HEAP_MB') == 'auto' and previous.get('NODE_HEAP_MB') == '2560':
            previous['NODE_HEAP_MB'] = 'auto'
        explicit = {key: value for key, value in editable.items() if value != DEFAULTS.get(key)}
        editable = {**previous, **explicit}
        adopted = True
    prior = read_env(legacy) if legacy.exists() else {}
    effective = {**DEFAULTS, **prior}
    effective.update({key: value for key, value in editable.items()
                      if value or key not in PRIVATE_INPUT_NAMES or not effective.get(key)})
    validate_user_inputs(effective)
    values = initialize(private, overrides=editable, dry_run=dry_run)
    if dry_run:
        return values
    if adopted:
        public = {key: value for key, value in editable.items() if key not in PRIVATE_INPUT_NAMES}
        private_write(path, configuration_text(path.read_text(), public))
    path.chmod(0o600)
    private_write(marker, json.dumps({'configuration_entry': '.env.example'}) + '\n')
    return values


def escape_compose(obj):
    if isinstance(obj, str): return obj.replace('$', '$$')
    if isinstance(obj, list): return [escape_compose(v) for v in obj]
    if isinstance(obj, dict): return {k: escape_compose(v) for k, v in obj.items()}
    return obj


def public_config(v):
    api=v['FRONTEND_API_BASE']
    origin=v['PUBLIC_URL'] if api.startswith('/') else api.rsplit('/api',1)[0]
    return {'apiBase':api,'socketURL':v['FRONTEND_SOCKET_URL'] or re.sub(r'^http','ws',origin.rstrip('/'))+'/ws/web/socket?',
            'storageBase':v.get('S3_PUBLIC_BASE_URL','') if v['FILE_STORAGE_BACKEND']!='local' else ''}


def backend_environment(v, original):
    env=copy.deepcopy(original)
    for key in ['MYSQL_HOST','MYSQL_PORT','MYSQL_DATABASE','MYSQL_USER','MYSQL_PASSWORD','FILE_STORAGE_BACKEND','PUBLIC_URL','DJANGO_ENV']:
        env[key]=v[key]
    env['CORS_ALLOWED_ORIGINS']=v['CORS_ALLOWED_ORIGINS'] or v['PUBLIC_URL'].rstrip('/')
    env['API_PUBLIC_URL']=v['API_PUBLIC_URL'] or (v['FRONTEND_API_BASE'].rsplit('/api',1)[0] if not v['FRONTEND_API_BASE'].startswith('/') else v['PUBLIC_URL'])
    for target,source in {
        'MINIO_STORAGE_ENDPOINT':'S3_ENDPOINT','MINIO_STORAGE_REGION':'S3_REGION',
        'MINIO_STORAGE_MEDIA_BUCKET_NAME':'S3_BUCKET','MINIO_STORAGE_ACCESS_KEY':'S3_ACCESS_KEY',
        'MINIO_STORAGE_SECRET_KEY':'S3_SECRET_KEY','MINIO_PUBLIC_BASE_URL':'S3_PUBLIC_BASE_URL',
        'MINIO_STORAGE_USE_HTTPS':'S3_USE_HTTPS','MINIO_STORAGE_MEDIA_USE_PRESIGNED':'S3_PRESIGNED',
        'MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET':'S3_AUTO_CREATE_BUCKET',
        'MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE':'S3_VIRTUAL_HOST_STYLE',
    }.items():env[target]=v.get(source,'')
    env['MINIO_STORAGE_ASSUME_MEDIA_BUCKET_EXISTS']='true' if v['FILE_STORAGE_BACKEND']=='tos' else 'false'
    return env


def gateway_config(root,v):
    text=(root/'deploy/nginx/single-server.conf').read_text().replace('http://mango_server:8000',v['BACKEND_UPSTREAM'].rstrip('/'))
    routes=''
    # Use a separate proxy prefix, preserving the local /mango-file/ media route.
    if v['FILE_STORAGE_BACKEND'] in {'minio','tos'} and v.get('S3_PUBLIC_BASE_URL'):
        public=urlsplit(v['S3_PUBLIC_BASE_URL']);platform=urlsplit(v['PUBLIC_URL'])
        path=public.path.rstrip('/')
        if public.netloc==platform.netloc and path.endswith('/'+v['S3_BUCKET']):
            prefix=path[:-len(v['S3_BUCKET'])]
            endpoint=v['S3_ENDPOINT']
            if prefix=='/':
                prefix='/'+v['S3_BUCKET']+'/'
                text=re.sub(r'    location '+re.escape(prefix)+r' \{.*?\n    \}\n','',text,flags=re.S)
                tail=''
            else:tail='/'
            scheme='https' if boolean(v,'S3_USE_HTTPS') else 'http'
            routes+=f'    location {prefix} {{ proxy_request_buffering off; proxy_buffering off; proxy_pass {scheme}://{endpoint}{tail}; }}\n'
    for i,(prefix,upstream) in enumerate(json.loads(v['EXTRA_HTTP_ROUTES']).items()):
        parsed=urlsplit(upstream)
        routes+=f'''    location = {prefix.rstrip('/')} {{ return 302 {prefix}; }}
    location {prefix} {{
        resolver 127.0.0.11 valid=30s;
        set $extra_upstream_{i} {parsed.netloc};
        rewrite ^{prefix}(.*)$ /$1 break;
        proxy_pass {parsed.scheme}://$extra_upstream_{i};
    }}
'''
    return text.replace('    location / {',routes+'    location / {')


def render(root,v):
    generated=root/'deploy/generated'
    d=json.loads((root/'deploy/compose.single.json').read_text())
    def substitute(obj):
        if isinstance(obj,str):
            return re.sub(r'\$\{([A-Za-z_][A-Za-z0-9_]*)(?:(:-|:\?)([^}]*))?\}',lambda m:v.get(m[1]) or m[3] or '',obj).replace('$$','$')
        if isinstance(obj,list):return [substitute(x) for x in obj]
        if isinstance(obj,dict):return {k:substitute(x) for k,x in obj.items()}
        return obj
    d=substitute(d);d['name']=v['COMPOSE_PROJECT_NAME'];services=d['services']
    env=backend_environment(v,d.pop('x-environment'));d.pop('x-backend',None)
    logging={'driver':'json-file','options':{'max-size':v['LOG_MAX_SIZE'],'max-file':v['LOG_MAX_FILE']}}
    for name,service in services.items():
        service['logging']=copy.deepcopy(logging)
        if name in BACKEND_SERVICES:
            service['image']=v['SERVER_IMAGE'];service['environment'].update(env)
            service.setdefault('volumes',[]).append(str(root/'deploy/deploy_check.py')+':/app/deploy_check.py:ro')
        if 'build' in service:service['build']['context']=str(root)
    services['mango_server']['environment']['UVICORN_WORKERS']=v['UVICORN_WORKERS']
    services['mango_server']['build']['args'].update(DJANGO_ENV=v['DJANGO_ENV'],PYTHON_IMAGE=v['PYTHON_IMAGE'])
    if v['DJANGO_ENV']=='dev':
        services['scheduler_service']['command'] += ' --cleanup-only'
    services['api_worker_1']['command']='python manage.py run_api_worker --worker-name=api-worker-1 --thread-pool-size='+v['API_THREAD_POOL_SIZE']+' --db-idle-seconds=1800'
    for index in range(2,int(v['API_WORKER_COUNT'])+1):
        worker=copy.deepcopy(services['api_worker_1'])
        worker['environment']['MANGO_SERVICE_INSTANCE']='api-worker-'+str(index)
        worker['command']=worker['command'].replace('api-worker-1','api-worker-'+str(index))
        services['api_worker_'+str(index)]=worker
    if not boolean(v,'MONITORING_ENABLED'):del services['monitoring_service']
    if v['MYSQL_MODE']!='internal':
        del services['db'];services['mango_server'].get('depends_on',{}).pop('db',None)
    else:
        db=services['db'];db['image']=v['MYSQL_IMAGE']
        db['command']=['--innodb-buffer-pool-size='+v['MYSQL_BUFFER_POOL_SIZE'],'--max-connections='+v['MYSQL_MAX_CONNECTIONS']]
        if not boolean(v,'MYSQL_BINLOG'):db['command'].append('--skip-log-bin')
        if v['MYSQL_EXPOSE_PORT']:db['ports']=[v['MYSQL_EXPOSE_BIND']+':'+v['MYSQL_EXPOSE_PORT']+':3306']
    services['db_tools']['image']=v['MYSQL_IMAGE']
    internal_minio=v['FILE_STORAGE_BACKEND']=='minio' and v['MINIO_MODE']=='internal'
    if internal_minio:
        minio={'image':v['MINIO_IMAGE'],'restart':'unless-stopped','logging':copy.deepcopy(logging),
               'environment':{'MINIO_ROOT_USER':v['S3_ACCESS_KEY'],'MINIO_ROOT_PASSWORD':v['S3_SECRET_KEY']},
               'volumes':[v['MANGO_DATA_DIR']+'/minio:/data'],'command':['server','/data','--console-address',':9001']}
        if v['MINIO_CONSOLE_PORT']:minio['ports']=[v['MINIO_CONSOLE_BIND']+':'+v['MINIO_CONSOLE_PORT']+':9001']
        services['minio']=minio
        services['mango_server'].setdefault('depends_on',{})['minio']={'condition':'service_started'}
    services['mango-console']['image']=v['CONSOLE_IMAGE']
    services['mango-console']['build']['args'].update(VUE_ENV=v['VUE_ENV'],NODE_IMAGE=v['NODE_IMAGE'],NGINX_IMAGE=v['NGINX_IMAGE'])
    services['mango-console']['build']['args']['NODE_HEAP_MB'] = '6144' if v['NODE_HEAP_MB'] == 'auto' else v['NODE_HEAP_MB']
    services['mango-console']['volumes']=[str(generated/'runtime-config.js')+':/usr/share/nginx/html/runtime-config.js:ro']
    gateway=services['mango_gateway'];gateway['image']=v['NGINX_IMAGE']
    gateway['networks']={'default':{'aliases':['mango-gateway']}}
    gateway['volumes'][0]=str(generated/'gateway.conf')+':/etc/nginx/conf.d/default.conf:ro'
    if v['API_PORT']:gateway['ports'].append(v['WEB_BIND']+':'+v['API_PORT']+':80')
    if boolean(v,'ACTUATOR_ENABLED'):
        actor_env={'ACTUATOR_HOST':v['ACTUATOR_HOST'],'ACTUATOR_USERNAME':v['ACTUATOR_USERNAME'],'ACTUATOR_PASSWORD':v['ACTUATOR_PASSWORD'],
                   'MANGO_ACTUATOR_PROFILE':v['ACTUATOR_PROFILE'],'MANGO_CAPABILITIES_ENABLED':v['ACTUATOR_CAPABILITIES'],
                   'ACTUATOR_WEB_PARALLEL':v['ACTUATOR_WEB_PARALLEL'],'ACTUATOR_PYTEST_PARALLEL':v['ACTUATOR_PYTEST_PARALLEL'],
                   'ACTUATOR_QUEUE_SIZE':v['ACTUATOR_QUEUE_SIZE']}
        services['actuator']={'image':v['ACTUATOR_IMAGE'],'restart':'unless-stopped','init':True,'logging':copy.deepcopy(logging),
                             'environment':actor_env,'command':['python','headless_main.py'],
                             'volumes':[v['MANGO_DATA_DIR']+'/actuator:/app/runtime'],'depends_on':{'mango_gateway':{'condition':'service_healthy'}}}
    for filename,content in [('runtime-config.js','window.__MANGO_CONFIG__ = '+json.dumps(public_config(v),ensure_ascii=True)+';\n'),('gateway.conf',gateway_config(root,v))]:
        private_write(generated/filename,content);(generated/filename).chmod(0o644)
    private_write(generated/'compose.json',json.dumps(escape_compose(d),ensure_ascii=False,indent=2)+'\n')
    return d


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['check-inputs','init','get','render','render-k8s'])
    parser.add_argument('path',type=Path)
    parser.add_argument('key',nargs='?')
    a=parser.parse_args()
    try:
        if a.path.name == '.env.example':
            v = initialize_example(a.path, dry_run=a.action == 'check-inputs')
        else:
            v=initialize(a.path, dry_run=a.action == 'check-inputs') if a.action in {'check-inputs','init','render','render-k8s'} else resolve(read_env(a.path),a.path.parent)
        if a.action=='render': render(Path(__file__).resolve().parent.parent, v)
        if a.action=='render-k8s':
            from k8s import render_k8s
            render_k8s(Path(__file__).resolve().parent.parent,v)
        if a.action in {'render', 'render-k8s'} and a.path.name == '.env.example':
            monitoring = '已纳入部署' if boolean(v, 'MONITORING_ENABLED') else '未启用'
            print(f'配置入口：.env.example；monitoring-service：{monitoring}')
        if a.action=='get':
            if a.key not in {'MANGO_DATA_DIR','PUBLIC_URL','WEB_PORT','MYSQL_MODE','FILE_STORAGE_BACKEND','MINIO_MODE','DEPLOY_TARGET','SERVER_IMAGE','CONSOLE_IMAGE','ACTUATOR_ENABLED','COMPOSE_PROJECT_NAME','K8S_NAMESPACE','K8S_WAIT_TIMEOUT','NODE_HEAP_MB'}:
                raise ValueError('只允许显示非敏感部署参数')
            print(v[a.key])
    except (ValueError,OSError,KeyError):
        # Validation messages identify keys only; never include values or parser input.
        import sys
        error=sys.exc_info()[1]
        parser.exit(1, (str(error) if isinstance(error,ValueError) else '无法读取或生成部署配置，请检查文件权限和配置完整性')+'\n')


if __name__=='__main__': main()
