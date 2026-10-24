import {
  buildApiConfigVersionDetailRequest,
  buildApiConfigVersionListRequest,
} from '../../src/api/apitest/config-version-request'
import {
  formatApiConfigVersionDiffValue,
  formatApiConfigVersionValue,
  getApiConfigVersionActionMeta,
  getApiConfigVersionDiffMeta,
  getApiConfigVersionSourceLabel,
  maskApiConfigVersionSnapshotPair,
  maskApiConfigVersionValue,
} from '../../src/utils/api-config-version'

function assertEqual(actual: unknown, expected: unknown, message: string) {
  const actualJson = JSON.stringify(actual)
  const expectedJson = JSON.stringify(expected)

  if (actualJson !== expectedJson) {
    throw new Error(`${message}: expected ${expectedJson}, received ${actualJson}`)
  }
}

assertEqual(
  getApiConfigVersionActionMeta('sort_steps'),
  { label: '调整步骤顺序', color: 'purple' },
  'sort_steps should use the configured action metadata'
)
assertEqual(
  getApiConfigVersionActionMeta('custom_action'),
  { label: 'custom_action', color: 'gray' },
  'unknown actions should use a safe fallback'
)
assertEqual(getApiConfigVersionSourceLabel('mcp'), 'MCP', 'mcp source should use the MCP label')
assertEqual(
  getApiConfigVersionSourceLabel('custom_source'),
  'custom_source',
  'unknown sources should keep their original value'
)
assertEqual(
  getApiConfigVersionDiffMeta('removed'),
  { label: '删除', color: 'red' },
  'removed diff should use the configured metadata'
)
assertEqual(formatApiConfigVersionValue(null), '-', 'null should be formatted as a placeholder')
assertEqual(
  formatApiConfigVersionValue({ name: '接口A' }),
  '{\n  "name": "接口A"\n}',
  'objects should use two-space JSON formatting'
)
assertEqual(
  maskApiConfigVersionValue({
    headers: {
      Authorization: 'Bearer test-token',
      Accept: 'application/json',
    },
    parameters: [
      {
        password: 'plain-password',
        name: '普通参数',
      },
    ],
  }),
  {
    headers: {
      Authorization: '***',
      Accept: 'application/json',
    },
    parameters: [
      {
        password: '***',
        name: '普通参数',
      },
    ],
  },
  'nested sensitive values should be masked without changing normal fields'
)
assertEqual(
  maskApiConfigVersionValue('Bearer test-token', 'headers.Authorization'),
  '***',
  'a scalar value should be masked when its path is sensitive'
)
assertEqual(
  maskApiConfigVersionValue({
    authorization: 'authorization-value',
    token: 'token-value',
    password: 'password-value',
    secret: 'secret-value',
    cookie: 'cookie-value',
    access_key: 'access-key-value',
    refresh_token: 'refresh-token-value',
    app_secret: 'app-secret-value',
    cache_data: 'cache-data-value',
  }),
  {
    authorization: '***',
    token: '***',
    password: '***',
    secret: '***',
    cookie: '***',
    access_key: '***',
    refresh_token: '***',
    app_secret: '***',
    cache_data: '***',
  },
  'direct sensitive object properties should remain masked'
)
assertEqual(
  maskApiConfigVersionValue(
    '{"account_id":9007199254740993,"password":"secret"}',
    'params'
  ),
  '{"account_id":9007199254740993,"password":"***"}',
  'JSON string masking should preserve integers larger than MAX_SAFE_INTEGER'
)
const maskedJsonString = maskApiConfigVersionValue(
  '{"password":"secret","name":"ok"}',
  'params'
)
assertEqual(typeof maskedJsonString, 'string', 'masked JSON strings should remain strings')
assertEqual(
  maskedJsonString,
  '{"password":"***","name":"ok"}',
  'JSON strings should mask nested sensitive values and preserve normal values'
)
for (const value of [
  '{"password":"secret",}',
  '{"password":"secret","x":NaN}',
  '{"password":"truncated-secret"',
  '{"key":"Authorization","value":{"credential":"semantic-secret"',
  '{key: Authorization,value:"bare-semantic-secret",}',
  '{"key":/*comment*/"Authorization","value":"comment-semantic-secret","x":NaN}',
  '{"password: "quote-secret"}',
  '{"value":"raw-secret","key":"Authorization',
  '{password/*comment*/:"raw-secret",}',
  '{"value":"raw-secret","key":"Authoriz\\u0061tion',
  "{'p\\u0061ssword':'raw-secret'}",
  "{'value':'raw-secret','key':'Authoriz\\u0061tion'}",
]) {
  assertEqual(
    maskApiConfigVersionValue(value, 'payload'),
    '***',
    'malformed JSON-like strings with sensitive property hints should fail closed'
  )
}
assertEqual(
  maskApiConfigVersionValue('\ufeff{"password":"bom-secret"}', 'payload'),
  '\ufeff{"password":"***"}',
  'BOM-prefixed JSON-like strings should not expose sensitive values'
)
for (const value of [
  '{"note":"password and token are ordinary value text",}',
  '{"token_count":1,}',
  '{"passwordless_enabled":true,}',
  '{"x":NaN}',
  '{"note":"password: ordinary value text',
  '["ok","password: ordinary value text",]',
  '["ok","token: ordinary value text",]',
  'password=secret',
]) {
  assertEqual(
    maskApiConfigVersionValue(value, 'payload'),
    value,
    'malformed strings without sensitive property hints should remain unchanged'
  )
}
assertEqual(
  maskApiConfigVersionValue([
    { key: 'Authorization', value: 'Bearer secret' },
    { key: 'X-API-Key', value: 'x-api-key-secret' },
    { name: 'apiKey', value: 'camel-case-secret' },
    { key: 'Proxy-Authorization', value: 'proxy-authorization-secret' },
    { key: 'normal', value: 'ok' },
  ]),
  [
    { key: 'Authorization', value: '***' },
    { key: 'X-API-Key', value: '***' },
    { name: 'apiKey', value: '***' },
    { key: 'Proxy-Authorization', value: '***' },
    { key: 'normal', value: 'ok' },
  ],
  'semantic key-value entries should only mask values whose key is sensitive'
)
assertEqual(
  maskApiConfigVersionValue({
    'api.key': 'dotted-direct-secret',
    'Proxy-Authorization': 'proxy-direct-secret',
    token_count: 128,
    passwordless_enabled: true,
  }),
  {
    'api.key': '***',
    'Proxy-Authorization': '***',
    token_count: 128,
    passwordless_enabled: true,
  },
  'direct object keys should use normalized sensitive-key matching before path composition'
)
assertEqual(
  maskApiConfigVersionValue({ 'token.count': 128 }),
  { 'token.count': 128 },
  'a direct dotted key should not be split into false-positive sensitive segments'
)
assertEqual(
  maskApiConfigVersionSnapshotPair(
    { fields: [{ key: 'normal', value: 'transition-secret' }] },
    { fields: [{ key: 'Authorization', value: 'transition-secret' }] }
  ),
  [
    { fields: [{ key: 'normal', value: '***' }] },
    { fields: [{ key: 'Authorization', value: '***' }] },
  ],
  'snapshot pairs should mask both sides when either semantic classification is sensitive'
)
assertEqual(
  maskApiConfigVersionSnapshotPair({ normal: '***' }, { normal: 'visible' }),
  [{ normal: '***' }, { normal: 'visible' }],
  'a literal mask string should not taint an ordinary paired value'
)
assertEqual(
  maskApiConfigVersionSnapshotPair(
    { field: { key: 'Authorization', value: 'object-side-secret' } },
    { field: 'scalar-side-secret' }
  ),
  [{ field: '***' }, { field: '***' }],
  'snapshot pairs should mask both sides when a sensitive structure changes type'
)
for (const [before, after] of [
  [
    '{"key":"normal","value":"valid-json-transition-secret"}',
    '{"key":"Authorization","value":"valid-json-transition-secret"}',
  ],
  [
    '{key: normal,value:"malformed-json-transition-secret",}',
    '{key: Authorization,value:"malformed-json-transition-secret",}',
  ],
]) {
  assertEqual(
    maskApiConfigVersionSnapshotPair(before, after),
    ['***', '***'],
    'JSON-string snapshot transitions should fail closed on both sides'
  )
}
assertEqual(
  maskApiConfigVersionValue([
    { name: 'token_count', value: 128 },
    { key: 'passwordless_enabled', value: true },
  ]),
  [
    { name: 'token_count', value: 128 },
    { key: 'passwordless_enabled', value: true },
  ],
  'non-sensitive key-value entries should not be masked by keyword substrings'
)
const semanticDiffSnapshot = {
  body_config: {
    fields: [
      { key: 'Authorization', value: 'authorization-value' },
      { name: 'apiKey', value: 'api-key-value' },
      { key: 'normal', value: 'normal-value' },
    ],
  },
}
assertEqual(
  formatApiConfigVersionDiffValue(
    'authorization-value',
    'body_config.fields.0.value',
    semanticDiffSnapshot
  ),
  '***',
  'diff values should use a sensitive key from the snapshot parent object'
)
assertEqual(
  formatApiConfigVersionDiffValue(
    'api-key-value',
    'body_config.fields.1.value',
    semanticDiffSnapshot
  ),
  '***',
  'diff values should use a sensitive name from the snapshot parent object'
)
assertEqual(
  formatApiConfigVersionDiffValue(
    'normal-value',
    'body_config.fields.2.value',
    semanticDiffSnapshot
  ),
  'normal-value',
  'diff values should preserve normal semantic key entries'
)
assertEqual(
  formatApiConfigVersionDiffValue(
    { password: 'fallback-secret' },
    'body_config.fields.99.value',
    semanticDiffSnapshot
  ),
  '{\n  "password": "***"\n}',
  'missing snapshot paths should fall back to the existing formatter'
)
assertEqual(
  formatApiConfigVersionDiffValue(
    'dotted-secret-value',
    'payload.with.dot.0.value',
    {
      'payload.with.dot': [{ key: 'Authorization', value: 'dotted-secret-value' }],
    }
  ),
  '***',
  'diff values should resolve semantic parents beneath snapshot keys containing dots'
)
assertEqual(
  formatApiConfigVersionDiffValue(
    'dotted-normal-value',
    'payload.with.dot.0.value',
    {
      'payload.with.dot': [{ key: 'normal', value: 'dotted-normal-value' }],
    }
  ),
  'dotted-normal-value',
  'diff values beneath normal dotted keys should remain visible'
)
assertEqual(
  formatApiConfigVersionDiffValue(
    'direct-dotted-secret',
    'api.key',
    { 'api.key': 'direct-dotted-secret' }
  ),
  '***',
  'diff values should normalize a direct sensitive snapshot key containing dots'
)
assertEqual(
  formatApiConfigVersionDiffValue(128, 'token.count', { 'token.count': 128 }),
  '128',
  'diff formatting should preserve a normal direct dotted snapshot key'
)
assertEqual(
  formatApiConfigVersionDiffValue(
    'unproven-authorization-value',
    'headers.Authorization',
    {}
  ),
  '***',
  'diff formatting should fail closed when a sensitive path is absent from the snapshot'
)
assertEqual(
  buildApiConfigVersionListRequest({
    object_type: 'api_case',
    object_id: 21,
    page: 2,
    pageSize: 20,
  }),
  {
    url: '/api/config/version',
    params: {
      object_type: 'api_case',
      object_id: 21,
      page: 2,
      pageSize: 20,
    },
  },
  'list request should use the version endpoint and preserve query parameters'
)
assertEqual(
  buildApiConfigVersionDetailRequest(33),
  {
    url: '/api/config/version/detail',
    params: { id: 33 },
  },
  'detail request should use the detail endpoint and id parameter'
)

console.log('api config version utility tests passed')
