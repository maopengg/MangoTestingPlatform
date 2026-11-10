import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import ts from 'typescript'
import { coveragePage } from '../../helpers/coverage-harness.mjs'

const base = new URL('../../../src/views/apitest/module-coverage/', import.meta.url)
const source = fs.readFileSync(new URL('components/CoverageOverview.vue', base), 'utf8')
const index = fs.readFileSync(new URL('index.vue', base), 'utf8')
const querySource = fs.readFileSync(new URL('query.ts', base), 'utf8')
const config = fs.readFileSync(new URL('config.ts', base), 'utf8')

test('module search and status filter stay side by side in two fluid columns', () => {
  const css = source.match(/\.mango-coverage-overview__filters\s*\{([^}]+)\}/)?.[1]
  assert.match(css, /display:\s*grid/)
  assert.match(css, /grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/)
  for (const control of ['search', 'filter']) {
    const rule = source.match(
      new RegExp(`\\.mango-coverage-overview__${control}\\s*\\{([^}]+)\\}`)
    )?.[1]
    assert.match(rule, /width:\s*100%/)
    assert.match(rule, /min-width:\s*0/)
  }
})

test('overview shows scan, interface entry, interface coverage and Case automation charts', () => {
  assert.match(
    source,
    /① 模块接口扫描进度[\s\S]*② 接口分析进度[\s\S]*③ 用例自动化进度[\s\S]*④ 接口覆盖率/
  )
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
  assert.match(source, /props.data\?\.project_inventory_summary/)
  assert.match(source, /value: projectScanSummary.value\?\.inventoried_count/)
  assert.match(source, /完整接口清单上传生效即完成<\/p>/)
  assert.doesNotMatch(source, /不随左侧模块变化|按所选项目、产品或模块范围统计|排除接口不计入，暂缓单列|；暂不处理单列/)
  assert.doesNotMatch(source, /value: props.data.summary.scanned_count/)
})

test('interface analysis pie partitions analysis states independently of ApiInfo and supports exact drill filters', () => {
  const code = config.slice(
    config.indexOf('export function getInterfaceAnalysisData'),
    config.indexOf('export function getInterfaceCoverageData')
  )
  const { outputText } = ts.transpileModule(code, {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  })
  const exports = {}
  new Function('exports', outputText)(exports)
  const rows = exports.getInterfaceAnalysisData({
    analyzed_interface_count: 7,
    pending_analysis_count: 2,
    analysis_gap_count: 1,
    analysis_review_count: 4,
    deferred_analysis_count: 3,
    bound_count: 100,
  })
  assert.deepEqual(
    rows.map((row) => row.value),
    [7, 2, 1, 4, 3]
  )
  assert.deepEqual(
    rows.map((row) => row.status),
    ['completed', 'pending', 'gap', 'review', 'deferred']
  )
  assert.equal(
    rows.reduce((sum, row) => sum + row.value, 0),
    17
  )
  assert.match(source, /query.analysis_statuses = \[analysis.status\]/)
  assert.match(index, /filters.analysis_statuses = \[...drillQuery.analysis_statuses\]/)
  assert.match(querySource, /analysis_status__in: 'analysis_statuses'/)
  assert.match(
    source,
    /scanChart\.value,\s*entryChart\.value,\s*coverageChart\.value,\s*statusChart\.value/
  )
})

test('interface coverage pie partitions interfaces, independently of Case and ApiInfo counts', () => {
  const code = config.slice(
    config.indexOf('export function getInterfaceCoverageData'),
    config.indexOf('export function getAutomationStatusData')
  )
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
    { name: '已覆盖', value: 100 },
    { name: '部分覆盖', value: 20 },
    { name: '未覆盖', value: 50 },
    { name: '暂不处理', value: 30 },
  ])
  assert.equal(
    rows.reduce((sum, row) => sum + row.value, 0),
    200
  )
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
  assert.match(index, /activeTab = ref(?:<CoverageTab>)?\('overview'\)/)
  assert.doesNotMatch(
    source,
    /__summary|__metrics|__metric|__note|const cards|完整模块扫描已校验并生效/
  )
  assert.match(source, /模块接口扫描进度/)
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
  assert.match(
    source,
    /\.mango-coverage-overview__table :deep\(\.arco-table-body\)\s*\{\s*overscroll-behavior-x: contain;\s*overscroll-behavior-y: contain/
  )
  assert.match(source, /<StickyHorizontalTable/)
  assert.match(source, /__table\s*\{[^}]*height: 440px/)
  assert.match(source, /<MangoTableActions/)
  assert.doesNotMatch(source, /permission: 'api.module_coverage:read'/)
  const code = config.slice(
    config.indexOf('export const overviewModuleColumns'),
    config.indexOf('export function getInterfaceCoverageData')
  )
  const { outputText } = ts.transpileModule(code, {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  })
  const exports = {}
  new Function('exports', outputText)(exports)
  assert.deepEqual(
    exports.overviewModuleColumns.slice(-3).map((item) => item.title),
    ['项目/产品', '模块', '操作']
  )
  assert.equal(exports.overviewModuleColumns.at(-1).fixed, 'right')
  assert.equal(
    exports.overviewModuleScrollX,
    exports.overviewModuleColumns.reduce((sum, column) => sum + column.width, 0)
  )
})

test('module pagination reuses global footer and page-size state', () => {
  assert.match(source, /<TableFooter/)
  assert.doesNotMatch(source, /<a-pagination|page\.value/)
  assert.match(source, /usePagination\(/)
  assert.match(source, /paginationLoading/)
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
  assert.equal(
    (
      source.match(
        /<MangoPanelSpin :loading="loading" class="mango-coverage-overview__chart-spin"/g
      ) || []
    ).length,
    4
  )
  assert.match(source, /:columns="overviewModuleColumns"\s*:loading="loading"/)
  assert.match(
    source,
    /<MangoPanelSpin :loading="loading" class="mango-coverage-overview__gaps-spin"/
  )
  assert.match(source, /v-else-if="data \|\| loading"/)
  assert.match(source, /v-if="!loading && !data\?\.modules.length"/)
  assert.match(source, /v-if="error && !data"/)
  assert.doesNotMatch(source, /覆盖概览刷新失败，当前保留上次结果/)
  assert.match(source, /<template v-if="error && !data"><\/template>/)
})

test('same-scope refresh retains results, changed scopes clear them, and stale requests stay ignored', async () => {
  const pending = []
  const state = coveragePage({
    getCoverageOverview: () => new Promise((resolve, reject) => pending.push({ resolve, reject })),
  })
  state.projectProductId.value = 1
  const first = state.loadOverview()
  pending[0].resolve({ data: { modules: [{ id: 1 }], summary: {} } })
  await first
  const refresh = state.loadOverview()
  assert.equal(state.overview.value.modules[0].id, 1)
  pending[1].reject(Error('temporary'))
  await refresh
  assert.equal(state.overview.value.modules[0].id, 1)
  assert.equal(state.overviewError.value, true)
  const stale = state.loadOverview()
  state.projectProductId.value = 2
  const changed = state.loadOverview()
  assert.equal(state.overview.value, undefined)
  pending[2].resolve({ data: { modules: [{ id: 1 }], summary: {} } })
  await stale
  assert.equal(state.overview.value, undefined)
  assert.equal(state.overviewLoading.value, true)
  pending[3].resolve({ data: { modules: [{ id: 2 }], summary: {} } })
  await changed
  assert.equal(state.overview.value.modules[0].id, 2)
  assert.equal(state.overviewLoading.value, false)
  state.close()
})

test('global layout leaves nested Arco vertical tables to their own scroll container', () => {
  const layout = fs.readFileSync(
    new URL('../../../src/layouts/MainLayout.vue', import.meta.url),
    'utf8'
  )
  const start = layout.indexOf('      function handleTableWheel(')
  const end = layout.indexOf('      return {', start)
  const js = ts.transpileModule(layout.slice(start, end), {
    compilerOptions: { target: ts.ScriptTarget.ES2020 },
  }).outputText
  class Element {
    constructor(root, nested) {
      this.root = root
      this.nested = nested
    }
    closest() {
      return this
    }
    classList = { contains: () => this.root }
    querySelector() {
      return this.nested ? {} : null
    }
  }
  const outer = { scrollTop: 100, clientHeight: 400, scrollHeight: 1200 }
  const handle = new Function(
    'HTMLElement',
    'findScrollableParent',
    `${js}; return handleTableWheel`
  )(Element, () => outer)
  for (const [root, nested] of [
    [true, false],
    [false, true],
    [false, false],
  ]) {
    outer.scrollTop = 100
    let prevented = false
    handle({
      defaultPrevented: false,
      deltaY: 50,
      deltaX: 0,
      target: new Element(root, nested),
      preventDefault: () => {
        prevented = true
      },
    })
    assert.equal(outer.scrollTop, root || nested ? 100 : 150)
    assert.equal(prevented, !(root || nested))
  }
})

test('header wheel scrolls the table while horizontal and zoom gestures stay native', () => {
  const start = source.indexOf('  function handleModuleTableWheel(')
  const end = source.indexOf('  const paginationLoading =', start)
  const js = ts.transpileModule(source.slice(start, end), {
    compilerOptions: { target: ts.ScriptTarget.ES2020 },
  }).outputText
  const body = { scrollTop: 0, scrollHeight: 1000, clientHeight: 400, contains: () => false }
  const handler = new Function(
    'moduleTableRegion',
    'Node',
    'scaleDensityPixels',
    `${js}; return handleModuleTableWheel`
  )({ value: { querySelector: () => body } }, class {}, (value) => value)
  let prevented = false
  const event = (overrides) => ({
    deltaX: 0,
    deltaY: 50,
    deltaMode: 0,
    cancelable: true,
    ctrlKey: false,
    preventDefault: () => {
      prevented = true
    },
    ...overrides,
  })
  handler(event())
  assert.equal(body.scrollTop, 50)
  assert.equal(prevented, true)
  for (const overrides of [{ ctrlKey: true }, { deltaX: 100 }, { cancelable: false }]) {
    prevented = false
    handler(event(overrides))
    assert.equal(body.scrollTop, 50)
    assert.equal(prevented, false)
  }
  body.scrollHeight = body.clientHeight
  handler(event())
  assert.equal(prevented, false)
})

test('overview is read-only, actions remain visible and stale results are ignored', () => {
  assert.doesNotMatch(source, /v-permission|permissionStore/)
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
  assert.equal(panel.id, 999)
  assert.doesNotMatch(outputText, /router|push\(/)
  assert.match(index, /<BaseSidePanel[\s\S]*?mode="page"/)
  assert.match(index, /:api-info-id="assetPanel.id"/)
  assert.match(index, /:case-id="assetPanel.id"/)
  assert.match(
    index,
    /defineAsyncComponent\([\s\S]*?import\('@\/views\/apitest\/info\/details\/index.vue'\)/
  )
})
