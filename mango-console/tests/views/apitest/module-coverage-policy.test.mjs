import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { coveragePage } from '../../helpers/coverage-harness.mjs'
import { flush } from '../../helpers/case-details-harness.mjs'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'

const filename = new URL('../../../src/views/apitest/module-coverage/index.vue', import.meta.url)
const source = fs.readFileSync(filename, 'utf8')
const { descriptor, errors } = parse(source)
const policy = fs.readFileSync(
  new URL(
    '../../../src/views/apitest/module-coverage/components/CoveragePolicyModal.vue',
    import.meta.url
  ),
  'utf8'
)
const query = fs.readFileSync(
  new URL('../../../src/views/apitest/module-coverage/query.ts', import.meta.url),
  'utf8'
)

test('manual policy and reason are distinct columns from computed progress and lifecycle', () => {
  const config = fs.readFileSync(
    new URL('../../../src/views/apitest/module-coverage/config.ts', import.meta.url),
    'utf8'
  )
  assert.match(config, /title: '覆盖策略',\s*dataIndex: 'coverage_policy'/)
  assert.match(config, /title: '处理原因', dataIndex: 'coverage_reason'/)
  assert.match(config, /title: '调用链解析'/)
  assert.match(config, /title: '接口存续'/)
  assert.match(config, /title: '自动化覆盖进度'/)
  assert.match(source, /label: '编辑', onClick: \(\) => openCoveragePolicy\(row\)/)
  assert.doesNotMatch(source, /selectedInterfaceKeys|row-selection|批量设置策略/)
  assert.match(policy, /policy: row.coverage_policy \|\| 'included'/)
  assert.match(policy, /updateCoverageInterfacePolicy\(\[payload.id\]/)
  assert.doesNotMatch(config, /title: '覆盖范围'/)
  assert.doesNotMatch(config, /title: '接口归属模块'/)
  assert.match(config, /title: '模块'/)
  assert.doesNotMatch(source, /template #owner_module/)
  assert.doesNotMatch(source, /v-permission|permissionStore|permission:/)
})

test('policy modal requires reason for deferred/excluded and stays open on error', () => {
  assert.match(policy, /:on-before-ok="save"/)
  assert.match(policy, /:ok-loading="saving"/)
  assert.match(policy, /form.policy !== 'included' && !form.reason.trim\(\)/)
  assert.match(policy, /catch\s*\{\s*return false/)
  assert.match(policy, /:max-length="2000"/)
  assert.match(source, /enumStore.module_coverage_policy/)
})

test('bound ApiInfo renders as a plain link while unbound states retain tags', () => {
  const binding = source
    .split('<template #api_info_binding="{ record }">')[1]
    .split('</template>')[0]
  const link = binding.match(/<a-link[\s\S]*?<\/a-link>/)[0]
  assert.match(link, /@click="openApiInfo\(record.api_info_id\)"/)
  assert.match(link, /ApiInfo #\{\{ record.api_info_id \}\}/)
  assert.doesNotMatch(link, /a-tag/)
  assert.match(binding, /<a-tag v-else/)
})

test('interface search exposes missing statuses as multi-selects and sends collection filters', () => {
  const config = fs.readFileSync(
    new URL('../../../src/views/apitest/module-coverage/config.ts', import.meta.url),
    'utf8'
  )
  for (const key of ['resolution_statuses', 'coverage_statuses', 'sync_actions', 'methods']) {
    assert.match(config, new RegExp(`key: '${key}'`))
    assert.ok(query.includes(`${key}: []`))
  }
  assert.match(source, /v-model="filters\[item.key\]"[\s\S]*?multiple[\s\S]*?:max-tag-count="1"/)
  for (const field of [
    'resolution_status__in',
    'coverage_status__in',
    'sync_action__in',
    'method__in',
  ])
    assert.ok(query.includes(field))
  assert.match(query, /filters\[key\]\.join\(','\)/)
  assert.match(query, /coverage_reason: filters.coverage_reason.trim\(\)/)
  assert.match(query, /api_info_id: filters.api_info_id/)
})

test('policy request submits policy and exact interface IDs through standard HTTP', () => {
  const api = fs.readFileSync(
    new URL('../../../src/api/apitest/module-coverage.ts', import.meta.url),
    'utf8'
  )
  const start = api.indexOf('export function updateCoverageInterfacePolicy(')
  const end = api.indexOf('\n}', start) + 2
  const code = ts.transpileModule(api.slice(start, end), {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  }).outputText
  const exports = {}
  let sent
  new Function('exports', 'post', 'base', code)(
    exports,
    (options) => {
      sent = options
    },
    '/api/module-coverage'
  )
  exports.updateCoverageInterfacePolicy([1, 2], 'excluded', '专用集成')
  assert.equal(sent.url, '/api/module-coverage/interfaces/policy')
  assert.deepEqual(sent.data(), { interface_ids: [1, 2], policy: 'excluded', reason: '专用集成' })
})

test('index script, template, and styles compile', () => {
  assert.deepEqual(errors, [])
  assert.ok(compileScript(descriptor, { id: 'module-coverage-exclusion' }))
  assert.deepEqual(
    compileTemplate({
      source: descriptor.template.content,
      filename: filename.pathname,
      id: 'module-coverage-exclusion',
    }).errors,
    []
  )
  for (const style of descriptor.styles)
    assert.deepEqual(
      compileStyle({
        source: style.content,
        filename: filename.pathname,
        id: 'module-coverage-exclusion',
        scoped: true,
      }).errors,
      []
    )
})

test('coverage overview explains the excluded denominator and count', () => {
  const overview = fs.readFileSync(
    new URL(
      '../../../src/views/apitest/module-coverage/components/CoverageOverview.vue',
      import.meta.url
    ),
    'utf8'
  )
  assert.match(overview, /已排除接口不计入/)
  assert.match(overview, /summary.excluded_interface_count/)
})

test('switching scope clears old rows even when the new request fails', async () => {
  const state = coveragePage({
    getCoverageInterfaces: async () => {
      throw Error('read')
    },
  })
  state.activeTab.value = 'interfaces'
  state.rows.value = [{ id: 10, module: { id: 1 } }]
  state.onNavigationFilterChange({ projectProduct: 2, module: 2 })
  await flush()
  assert.deepEqual(state.rows.value, [])
  assert.equal(state.rowsError.value, true)
  assert.equal(state.loading.value, false)
  state.close()
})
