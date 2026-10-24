def auth(context):
    import requests

    base_url = context.test_data.get_cache('url') or ''
    raw_token = context.test_data.get_cache('token')
    tenant_id = context.test_data.get_cache('tenant_id')
    if not base_url:
        raise Exception('缺少全局变量 url')
    if not raw_token:
        raise Exception('缺少全局变量 token')

    base_url = str(base_url).rstrip('/')
    raw_token = str(raw_token).strip()
    if raw_token.lower().startswith('bearer '):
        authorization = raw_token
    else:
        authorization = 'Bearer ' + raw_token

    response = requests.get(
        base_url + '/clm/api/login/getJWTV2',
        headers={
            'Authorization': authorization,
            'tenant_id': str(tenant_id or ''),
            'accept': 'application/json, text/plain, */*',
        },
        timeout=30,
        proxies={'http': None, 'https': None},
    )
    response.raise_for_status()
    body = response.json()
    if body.get('code') != 200 or not body.get('success', True):
        raise Exception('getJWTV2 返回异常: %s' % body)
    v2_token = str(body.get('data') or '').strip()
    if not v2_token:
        raise Exception('getJWTV2 未返回 data')
    if v2_token.lower().startswith('bearer '):
        v2_token = v2_token.split(' ', 1)[1].strip()
    return {
        'v2token': v2_token,
    }
if __name__ == '__main__':
    pass
