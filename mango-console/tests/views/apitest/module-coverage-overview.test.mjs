import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import ts from 'typescript'

const base = new URL('../../../src/views/apitest/module-coverage/', import.meta.url)
const source = fs.readFileSync(new URL('components/CoverageOverview.vue', base), 'utf8')
const index = fs.readFileSync(new URL('index.vue', base), 'utf8')
const config = fs.readFileSync(new URL('config.ts', base), 'utf8')

test('overview shows scan, interface entry, interface coverage and Case automation charts', () => {
  assert.match(source, /模块扫描进度/)
  assert.match(source, /接口录入状态/)
  assert.match(source, /用例自动化进度/)
  assert.match(source, /接口覆盖率/)
  assert.doesNotMatch(source, /自动化场景状态/)
  assert.match(source, /__charts\s*\{[^}]*repeat\(4/)
  assert.match(source, /mango-workbench-scroll-x mango-coverage-overview__charts-scroll/)
  assert.match(source, /min-width: var\(--mango-workbench-min-width\)/)
  assert.doesNotMatch(source, /@container[^}]*\{\s*\.mango-coverage-overview__charts\s*\{/)
  assert.doesNotMatch(source, /各模块待补接口与场景|rateChart|getModuleGapRows/)
  assert.doesNotMatch(index, /coverage_gap|clearGapFilter/)
})

test('module scan pie uses project-level scan summary', () => {
  assert.match(source, /props.data\?\.project_scan_summary/)
  assert.match(source, /value: projectScanSummary.value\?\.scanned_count/)
  assert.match(source, /不随左侧模块选择变化/)
  assert.doesNotMatch(source, /value: props.data.summary.scanned_count/)
})

test('interface entry pie partitions discovered interfaces and supports module filtering', () => {
  const code = source.slice(source.indexOf('const entryData ='), source.indexOf('const entryDescription ='))
  const calculate = new Function('props', 'computed', `${code}; return entryData`)
  const compute = (fn) => fn()
  assert.deepEqual(calculate({ data: { summary: { interface_count: 560, bound_count: 547 } } }, compute), [
    { name: '已正确录入', value: 547 },
    { name: '待录入/绑定异常', value: 13 },
  ])
  assert.ok(calculate({}, compute).every((item) => item.value === 0))
  assert.match(source, /event\.dataIndex === 1 \? 'entry' : 'all'/)
  assert.match(source, /scanChart\.value, entryChart\.value, coverageChart\.value, statusChart\.value/)
})

test('interface coverage pie partitions interfaces, independently of Case and ApiInfo counts', () => {
  const code = config.slice(config.indexOf('export function getInterfaceCoverageData'),
    config.indexOf('export function getAutomationStatusData'))
  const { outputText } = ts.transpileModule(code, {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  })
  const exports = {}
  new Function('exports', outputText)(exports)
  const rows = exports.getInterfaceCoverageData({
    covered_interface_count: 100,
    partial_interface_count: 20,
    uncovered_interface_count: 50,
    deferred_interface_count: 30,
    completed_count: 1000,
    bound_count: 180,
  })
  assert.deepEqual(rows, [
    { name: '已覆盖', value: 100 }, { name: '部分覆盖', value: 20 },
    { name: '未覆盖', value: 50 }, { name: '暂不处理', value: 30 },
  ])
  assert.equal(rows.reduce((sum, row) => sum + row.value, 0), 200)
  assert.match(source, /rate\(props.data.summary.interface_coverage_rate\)/)
})

test('automation pie uses mutually exclusive Case counts, not interface counts', () => {
  const code = config.slice(config.indexOf('export function getAutomationStatusData'))
  const { outputText } = ts.transpileModule(code, {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  })
  const exports = {}
  new Function('exports', outputText)(exports)
  const rows = exports.getAutomationStatusData({
    completed_count: 1740,
    target_count: 2222,
    deferred_count: 1089,
    incomplete_interface_count: 277,
  })
  assert.deepEqual(rows, [
    { name: '已完成', value: 1740 },
    { name: '未完成', value: 482 },
    { name: '暂不处理', value: 1089 },
  ])
  assert.equal(
    rows.reduce((sum, row) => sum + row.value, 0),
    3311
  )
  assert.ok(
    exports
      .getAutomationStatusData({ completed_count: 0, target_count: 0, deferred_count: 0 })
      .every((row) => row.value === 0)
  )
  assert.match(source, /用例自动化进度/)
  assert.match(source, /statusPercent\(item.value\)/)
  assert.doesNotMatch(source, /title: '自动化未完成接口'/)
})

test('detail tabs no longer show or fetch the removed summary cards', () => {
  assert.doesNotMatch(
    index,
    /metricCards|loadMetrics|getCoverageMetrics|__metrics|代码链路完整率|有效自动化覆盖率/
  )
  assert.match(index, /<CoverageOverview/)
})

test('deferred-only scenarios are not described as missing automation scenarios', () => {
  assert.match(source, /: item\.deferred_count\s*\? `暂不处理 \$\{item\.deferred_count\} 个场景`/)
  assert.match(source, /item\.target_count && item\.deferred_count/)
})

test('overview component and integration compile with the Vue compiler', () => {
  for (const [filename, content] of [
    ['CoverageOverview.vue', source],
    ['index.vue', index],
  ]) {
    const { descriptor, errors } = parse(content, { filename })
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: filename })
    const result = compileTemplate({
      source: descriptor.template.content,
      filename,
      id: filename,
      compilerOptions: { bindingMetadata: script.bindings },
    })
    assert.deepEqual(result.errors, [])
  }
})

test('overview starts with charts instead of duplicate metrics and explanations', () => {
  assert.match(index, /activeTab = ref\('overview'\)/)
  assert.doesNotMatch(source, /__summary|__metrics|__metric|__note|const cards|完整模块扫描已校验并生效/)
  assert.match(source, /模块扫描进度/)
  assert.match(source, /value == null \? '—'/)
  assert.match(source, /尚无自动化场景/)
})

test('overview reuses global sections, spacing and typography without nested module cards', () => {
  assert.match(source, /mango-section-card mango-coverage-overview__panel/)
  assert.match(source, /mango-section-title__main/)
  assert.match(source, /padding: var\(--m-page-gap\)/)
  assert.match(source, /@container mango-coverage-overview/)
  assert.doesNotMatch(source, /<h3|\.mango-coverage-overview__panel\s*\{[^}]*border:/)
  assert.doesNotMatch(source, /__module-grid|<article/)
})

test('module progress uses a bounded native-scroll table and global actions', () => {
  assert.match(source, /<a-table[\s\S]*?:data="visibleModules"/)
  assert.match(source, /:columns="overviewModuleColumns"/)
  assert.match(source, /完成率 \{\{ rate\(record.automation_rate\) \}\}/)
  assert.match(source, /:pagination="false"/)
  assert.match(source, /class="mango-native-scroll-table"/)
  assert.match(source, /:scroll="\{ x: overviewModuleScrollX, y: overviewModuleScrollY \}"/)
  assert.match(config, /overviewModuleScrollY = 400/)
  assert.match(source, /\.mango-coverage-overview__table :deep\(\.arco-table-body\)\s*\{\s*overscroll-behavior: contain/)
  assert.match(source, /<StickyHorizontalTable/)
  assert.match(source, /__table\s*\{[^}]*height: 440px/)
  assert.match(source, /<MangoTableActions/)
  assert.match(source, /permission: 'api.module_coverage:detail'/)
  const code = config.slice(config.indexOf('export const overviewModuleColumns'),
    config.indexOf('export function getInterfaceCoverageData'))
  const { outputText } = ts.transpileModule(code, {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  })
  const exports = {}
  new Function('exports', outputText)(exports)
  assert.deepEqual(exports.overviewModuleColumns.slice(-3).map((item) => item.title), ['项目/产品', '模块', '操作'])
  assert.equal(exports.overviewModuleColumns.at(-1).fixed, 'right')
  assert.equal(exports.overviewModuleScrollX,
    exports.overviewModuleColumns.reduce((sum, column) => sum + column.width, 0))
})

test('module pagination reuses global footer and page-size state', () => {
  assert.match(source, /<TableFooter/)
  assert.doesNotMatch(source, /<a-pagination|page\.value/)
  assert.match(source, /usePagination\(\(\) => \{\}\)/)
  assert.match(source, /pagination\.page \* pagination\.pageSize/)
  assert.match(source, /pagination\.setTotalSize\(rows\.length\)/)
  assert.match(source, /pagination\.page = 1/)
})

test('overview owns a bounded keyboard-accessible vertical scroll region', () => {
  assert.match(source, /mango-coverage-overview__scroll mango-native-scrollbar/)
  assert.match(source, /aria-label="覆盖概览内容"[\s\S]*?tabindex="0"/)
  assert.match(source, /overflow-y: scroll/)
  assert.match(source, /scrollbar-gutter: stable/)
  assert.doesNotMatch(source, /class="mango-coverage-overview__spin"/)
})

test('overview loads individual charts, module table and gap list without a parent mask', () => {
  assert.equal((source.match(/<MangoPanelSpin :loading="loading" class="mango-coverage-overview__chart-spin"/g) || []).length, 4)
  assert.match(source, /:columns="overviewModuleColumns"\s*:loading="loading"/)
  assert.match(source, /<MangoPanelSpin :loading="loading" class="mango-coverage-overview__gaps-spin"/)
  assert.match(source, /v-else-if="data \|\| loading"/)
  assert.match(source, /v-if="!loading && !data\?\.modules.length"/)
  assert.match(source, /v-if="error && !data"/)
  assert.match(source, /覆盖概览刷新失败，当前保留上次结果/)
})

test('same-scope refresh retains results, changed scopes clear them, and stale requests stay ignored', async () => {
  const start = index.indexOf('  async function loadOverview()')
  const end = index.indexOf('  function drillOverview(', start)
  const code = ts.transpileModule(index.slice(start, end), { compilerOptions: { target: ts.ScriptTarget.ES2020 } }).outputText
  const state = { overview: { value: undefined }, overviewLoading: { value: false }, overviewError: { value: false }, projectProductId: { value: 1 }, filters: {} }
  const pending = []
  const load = new Function('state', 'getCoverageOverview', `
    const { overview, overviewLoading, overviewError, projectProductId, filters } = state;
    let overviewRequest = 0, overviewScope = '';
    const applyModuleFilter = () => {};
    ${code}
    return loadOverview;
  `)(state, () => new Promise((resolve, reject) => pending.push({ resolve, reject })))
  const first = load()
  assert.equal(state.overviewLoading.value, true)
  const initial = { modules: [{ id: 1 }] }
  pending[0].resolve({ data: initial })
  await first
  const refresh = load()
  assert.equal(state.overview.value, initial)
  pending[1].reject(new Error('temporary'))
  await refresh
  assert.equal(state.overview.value, initial)
  assert.equal(state.overviewError.value, true)
  assert.equal(state.overviewLoading.value, false)
  const stale = load()
  state.projectProductId.value = 2
  const changed = load()
  assert.equal(state.overview.value, undefined)
  pending[2].resolve({ data: initial })
  await stale
  assert.equal(state.overview.value, undefined)
  assert.equal(state.overviewLoading.value, true)
  const next = { modules: [{ id: 2 }] }
  pending[3].resolve({ data: next })
  await changed
  assert.equal(state.overview.value, next)
  assert.equal(state.overviewLoading.value, false)
})

test('overview is read-only, detail links are permission guarded, and stale results are ignored', () => {
  assert.match(source, /v-permission="'api.module_coverage:detail'"/)
  assert.match(index, /request === overviewRequest/)
  assert.match(source, /emit\('drill'/)
  assert.doesNotMatch(source, /archiveCoverage|bindCoverage|createCoverage|updateCoverage/)
})

test('bound API assets open the global embedded panel with exact IDs, without navigation', () => {
  const start = index.indexOf('  function openApiCase(')
  const end = index.indexOf('  function openInterfaceFlow(', start)
  const { outputText } = ts.transpileModule(index.slice(start, end), {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  })
  const panel = { visible: false, kind: '', id: 0 }
  let allowed = true
  const actions = new Function(
    'assetPanel',
    'permissionStore',
    `${outputText}; return { openApiCase, openApiInfo }`
  )(panel, { hasPermission: () => allowed })
  actions.openApiInfo(2205)
  assert.deepEqual(panel, { visible: true, kind: 'info', id: 2205 })
  actions.openApiCase(2192)
  assert.deepEqual(panel, { visible: true, kind: 'case', id: 2192 })
  allowed = false
  actions.openApiInfo(999)
  assert.equal(panel.id, 2192)
  assert.doesNotMatch(outputText, /router|push\(/)
  assert.match(index, /<BaseSidePanel[\s\S]*?mode="page"/)
  assert.match(index, /:api-info-id="assetPanel.id"/)
  assert.match(index, /:case-id="assetPanel.id"/)
  assert.match(
    index,
    /defineAsyncComponent\([\s\S]*?import\('@\/views\/apitest\/info\/details\/index.vue'\)/
  )
})
