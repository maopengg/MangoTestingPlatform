import { getApiInfoRevisionLabel, getApiInfoRequestSnapshot } from '../../../../src/utils/api-info-revision'

function assertEqual(actual: unknown, expected: unknown, message: string) {
  const actualJson = JSON.stringify(actual)
  const expectedJson = JSON.stringify(expected)
  if (actualJson !== expectedJson) {
    throw new Error(`${message}: expected ${expectedJson}, received ${actualJson}`)
  }
}

assertEqual(getApiInfoRevisionLabel({ revision_no: 3, release: null }), '草稿 r3', 'draft label')
assertEqual(
  getApiInfoRevisionLabel({
    revision_no: 2,
    release: { version_label: 'V1', is_current: true },
  }),
  'V1（当前已发布）',
  'release label'
)
assertEqual(
  getApiInfoRequestSnapshot({
    method: 1,
    url: '/open-apis/contracts',
    headers: { 'X-Trace': '${trace_id}' },
    params: { tenantId: '${tenant_id}' },
    body_type: 'json',
    body_config: { json: { name: '${contract_name}' } },
    ass_schema: { type: 'object' },
    ignored: true,
  }),
  {
    method: 1,
    url: '/open-apis/contracts',
    headers: { 'X-Trace': '${trace_id}' },
    params: { tenantId: '${tenant_id}' },
    body_type: 'json',
    body_config: { json: { name: '${contract_name}' } },
    ass_schema: { type: 'object' },
  },
  'comparison only shows executable request contract fields'
)
