"""Environment-only HTTP deployment overrides shared by Compose and Kubernetes."""
import os
from urllib.parse import urlsplit


def _origin(value,key):
    parsed=urlsplit(value)
    if parsed.scheme not in {'http','https'} or not parsed.hostname or parsed.username or parsed.password or parsed.path not in {'','/'} or parsed.query or parsed.fragment:
        raise ValueError(key+' 必须是完整来源，不含路径或凭据')
    return value.rstrip('/')


def apply_http_environment(settings):
    if 'CORS_ALLOWED_ORIGINS' not in os.environ:return
    origins=[_origin(x.strip(),'CORS_ALLOWED_ORIGINS') for x in os.environ['CORS_ALLOWED_ORIGINS'].split(',') if x.strip()]
    settings.update(CORS_ORIGIN_ALLOW_ALL=False,CORS_ALLOW_ALL_ORIGINS=False,CORS_ORIGIN_WHITELIST=origins,
                    CORS_ALLOWED_ORIGINS=origins,CSRF_TRUSTED_ORIGINS=origins)
    # Browser origins and the public API Host may differ in split deployments.
    public=[_origin(os.environ[k],k) for k in ('PUBLIC_URL','API_PUBLIC_URL') if os.environ.get(k)]
    trusted=list(dict.fromkeys(origins+public))
    settings['MCP_ALLOWED_ORIGINS']=trusted
    settings['MCP_ALLOWED_HOSTS']=list(dict.fromkeys([urlsplit(x).netloc for x in trusted]+['localhost:*','127.0.0.1:*','[::1]:*']))
