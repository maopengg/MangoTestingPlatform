import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'

const filename = new URL('../../../src/views/apitest/module-coverage/index.vue', import.meta.url)
const source = fs.readFileSync(filename, 'utf8')
const { descriptor, errors } = parse(source)

test('manual policy and reason are distinct columns from computed progress and lifecycle', () => {
  const config = fs.readFileSync(new URL('../../../src/views/apitest/module-coverage/config.ts', import.meta.url), 'utf8')
  assert.match(config, /title: '覆盖策略', dataIndex: 'coverage_policy'/)
  assert.match(config, /title: '处理原因', dataIndex: 'coverage_reason'/)
  assert.match(config, /title: '调用链解析'/)
  assert.match(config, /title: '接口存续'/)
  assert.match(config, /title: '自动化覆盖进度'/)
  assert.match(source, /label: '编辑', onClick: \(\) => openCoveragePolicy\(row\)/)
  assert.doesNotMatch(source, /selectedInterfaceKeys|row-selection|批量设置策略/)
  assert.match(source, /policy: row.coverage_policy \|\| 'included'/)
  assert.match(source, /updateCoverageInterfacePolicy\(\[policyForm.id\]/)
  assert.doesNotMatch(config, /title: '覆盖范围'/)
  assert.doesNotMatch(config, /title: '接口归属模块'/)
  assert.match(config, /title: '模块'/)
  assert.doesNotMatch(source, /template #owner_module/)
  assert.doesNotMatch(source, /v-permission|permissionStore|permission:/)
})

test('policy modal requires reason for deferred/excluded and stays open on error', () => {
  assert.match(source, /:on-before-ok="saveCoveragePolicy"/)
  assert.match(source, /:ok-loading="policyLoading"/)
  assert.match(source, /policyForm.policy !== 'included' && !policyForm.reason.trim\(\)/)
  assert.match(source, /catch\s*\{\s*return false/)
  assert.match(source, /:max-length="2000"/)
  assert.match(source, /enumStore.module_coverage_policy/)
})

test('bound ApiInfo renders as a plain link while unbound states retain tags', () => {
  const binding = source.split('<template #api_info_binding="{ record }">')[1].split('</template>')[0]
  const link = binding.match(/<a-link[\s\S]*?<\/a-link>/)[0]
  assert.match(link, /@click="openApiInfo\(record.api_info_id\)"/)
  assert.match(link, /ApiInfo #\{\{ record.api_info_id \}\}/)
  assert.doesNotMatch(link, /a-tag/)
  assert.match(binding, /<a-tag v-else/)
})

test('interface search exposes missing statuses as multi-selects and sends collection filters', () => {
  const config = fs.readFileSync(new URL('../../../src/views/apitest/module-coverage/config.ts', import.meta.url), 'utf8')
  for (const key of ['resolution_statuses', 'coverage_statuses', 'sync_actions', 'methods']) {
    assert.match(config, new RegExp(`key: '${key}'`))
    assert.ok((source.match(new RegExp(`${key}: \\[\\]`, 'g')) || []).length >= 3)
  }
  assert.match(source, /v-model="filters\[item.key\]" multiple allow-clear :max-tag-count="1"/)
  for (const field of ['resolution_status__in', 'coverage_status__in', 'sync_action__in', 'method__in'])
    assert.ok(source.includes(field))
  assert.match(source, /filters\[key\]\.join\(','\)/)
  assert.match(source, /query.coverage_reason = filters.coverage_reason \|\| undefined/)
  assert.match(source, /query.api_info_id = filters.api_info_id \|\| undefined/)
})

test('policy request submits policy and exact interface IDs through standard HTTP', () => {
  const api = fs.readFileSync(new URL('../../../src/api/apitest/module-coverage.ts', import.meta.url), 'utf8')
  const start = api.indexOf('export function updateCoverageInterfacePolicy(')
  const end = api.indexOf('\n}', start) + 2
  const code = ts.transpileModule(api.slice(start, end), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
  const exports = {}
  let sent
  new Function('exports', 'post', 'base', code)(exports, options => { sent = options }, '/api/module-coverage')
  exports.updateCoverageInterfacePolicy([1, 2], 'excluded', '专用集成')
  assert.equal(sent.url, '/api/module-coverage/interfaces/policy')
  assert.deepEqual(sent.data(), { interface_ids: [1, 2], policy: 'excluded', reason: '专用集成' })
})

test('index script, template, and styles compile', () => {
  assert.deepEqual(errors, [])
  assert.ok(compileScript(descriptor, { id: 'module-coverage-exclusion' }))
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename: filename.pathname, id: 'module-coverage-exclusion' }).errors, [])
  for (const style of descriptor.styles)
    assert.deepEqual(compileStyle({ source: style.content, filename: filename.pathname, id: 'module-coverage-exclusion', scoped: true }).errors, [])
})

test('coverage overview explains the excluded denominator and count', () => {
  const overview = fs.readFileSync(new URL('../../../src/views/apitest/module-coverage/components/CoverageOverview.vue', import.meta.url), 'utf8')
  assert.match(overview, /已排除接口不计入/)
  assert.match(overview, /summary.excluded_interface_count/)
})

test('switching scope clears old rows even when the new request fails', async () => {
  const ast = ts.createSourceFile('module-coverage.ts', descriptor.scriptSetup.content, ts.ScriptTarget.Latest, true)
  const functions = ['resetRowScope', 'loadRows'].map(name => ast.statements.find(
    node => ts.isFunctionDeclaration(node) && node.name?.text === name
  ).getText(ast)).join('\n')
  const code = ts.transpileModule(functions, { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const rows = { value: [{ id: 10, module: 1 }] }
  const loading = { value: false }
  let rejectRequest
  const request = new Promise((resolve, reject) => { rejectRequest = reject })
  const inputs = {
    rows, loading, activeTab: { value: 'interfaces' },
    projectProductId: { value: 2 }, filters: { resolution_statuses: [], coverage_statuses: [], sync_actions: [], methods: [] }, pagination: { page: 1, pageSize: 20, setTotalSize() {} },
    applyModuleFilter(query) { query.module = 2 },
    getCoverageInterfaces(query) { assert.equal(query.module, 2); return request },
  }
  const runtime = new Function(...Object.keys(inputs), `let rowsRequest = 0; ${code}; return {loadRows}`)(...Object.values(inputs))
  const loadingRequest = runtime.loadRows()
  assert.deepEqual(rows.value, [])
  rejectRequest(new Error('request failed'))
  await assert.rejects(loadingRequest)
  assert.deepEqual(rows.value, [])
  assert.equal(loading.value, false)
  assert.match(source, /function resetTabFilters\(\) \{\s*resetRowScope\(\)/)
})
