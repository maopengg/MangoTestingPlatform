import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'
import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/index')
const trend = (value = 0) => ({ code: 200, data: { labels: ['01/01-01/07', '01/08-01/14'], api_count: [value, 1], ui_count: [0, 2], pytest_count: [0, 3] } })
const activity = (ids = [0], total = ids.length) => ({ code: 200, data: {
  user_ids: ids, name: ids.map(id => `User ${id}`), total_logins: ids.map(id => id), rank_total: total,
  active_users: total, activity_rate: 0, visit_count: 0, daily_activity: [{ date: '11-07', active_users: 0 }],
} })
const groups = {
  uiStats: ['elementCount', 'pageCount', 'stepCount', 'caseCount', 'publicCount', 'authConfigCount'],
  apiStats: ['interfaceCount', 'caseCount', 'scenarioCount', 'publicCount', 'headerCount', 'authConfigCount'],
  pytestStats: ['projectCount', 'caseCount', 'fileCount', 'boundProjectCount', 'boundProductCount'],
  dataFactoryStats: ['datasourceCount', 'datasourceBindingCount', 'entityCount', 'fieldCount', 'templateCount', 'caseConfigCount'],
  testConfigStats: ['projectCount', 'projectProductCount', 'databaseCount', 'testObjectCount', 'testFileCount'],
  scheduledTaskStats: ['taskCount', 'strategyCount', 'fireRecordCount', 'systemJobCount'],
}
const statistics = (value = 0) => ({ code: 200, data: Object.fromEntries(Object.entries(groups).map(([key, fields]) => [key, Object.fromEntries(fields.map(field => [field, value]))])) })
function panel(name, api = {}) {
  const hooks = { mount: [], activate: [], deactivate: [], unmount: [] }, listeners = new Map(), frames = new Map(), observers = [], charts = [], calls = []
  let frameId = 0, palette = 'example-color'
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'test-token', selected_environment: 0 })
  const route = vue.reactive({ path: '/index/home', fullPath: '/index/home' }), scale = vue.ref(1)
  const vueModule = { ...vue, onMounted: fn => hooks.mount.push(fn), onActivated: fn => hooks.activate.push(fn), onDeactivated: fn => hooks.deactivate.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) }
  const window = {
    addEventListener(event, fn) { if (!listeners.has(event)) listeners.set(event, new Set()); listeners.get(event).add(fn) },
    removeEventListener(event, fn) { listeners.get(event)?.delete(fn) },
    requestAnimationFrame(fn) { const id = ++frameId; frames.set(id, fn); return id }, cancelAnimationFrame: id => frames.delete(id),
  }
  class ResizeObserver {
    constructor(callback) { this.callback = callback; this.disconnected = false; observers.push(this) }
    observe(target) { this.target = target }
    disconnect() { this.disconnected = true }
  }
  const getComputedStyle = () => ({ columnGap: '8', getPropertyValue: () => palette })
  const document = { documentElement: {}, createElement: () => ({ getContext: () => ({ font: '', measureText: text => ({ width: text.length * 7 * scale.value }) }) }) }
  const chartByDom = new Map()
  const useEcharts = dom => {
    if (!chartByDom.has(dom)) {
      const chart = { dom, options: [], resizes: 0, disposed: false, setOption(option) { this.options.push(option) }, resize() { this.resizes++ },
        isDisposed() { return this.disposed }, dispose() { this.disposed = true; chartByDom.delete(dom) },
      }
      chartByDom.set(dom, chart); charts.push(chart)
    }
    return chartByDom.get(dom)
  }
  const method = name === 'AutomationStats' ? 'getSystemIndexStatistics' : name === 'HotProductChart' ? 'getSystemActivityLevel' : 'getSystemCaseResultWeekSum'
  const endpoints = { [method]: args => { calls.push(args); return api.read ? api.read(args) : Promise.resolve(name === 'AutomationStats' ? statistics() : name === 'HotProductChart' ? activity() : trend()) } }
  const modules = {
    vue: vueModule, 'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user },
    '@/hooks/useDisplayDensity': { displayDensityScale: scale, scaleDensityPixels: value => value * scale.value },
    '@/views/index/composables/use-home-menu-icon': { useHomeMenuIcon: () => ({ resolveMenuIcon: (_path, fallback) => fallback }) },
    '@arco-design/web-vue/es/icon': Object.fromEntries(['IconCalendar', 'IconCode', 'IconDesktop', 'IconSettings', 'IconStorage', 'IconThunderbolt'].map(name => [name, { name }])),
    '@/hooks/useEcharts': { default: useEcharts }, 'echarts/core': { dispose(dom) { const chart = chartByDom.get(dom); if (chart) chart.disposed = true; chartByDom.delete(dom) } },
  }
  const cache = new Map()
  function load(filename) {
    if (cache.has(filename)) return cache.get(filename)
    const exports = {}; cache.set(filename, exports)
    const source = filename.endsWith('.vue') ? parse(readFileSync(filename, 'utf8')).descriptor.script.content : readFileSync(filename, 'utf8')
    const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
    new Function('exports', 'require', 'window', 'document', 'getComputedStyle', 'ResizeObserver', code)(exports, id => {
      if (id in modules) return modules[id]
      if (id.startsWith('@/api/')) return endpoints
      if (id.startsWith('.')) return load(path.resolve(path.dirname(filename), id) + '.ts')
      { if (['@/utils/load-error', '@/utils/api-response'].includes(id)) return loadFeedbackModule(id); throw Error(`Unmocked ${id}`) }
    }, window, document, getComputedStyle, ResizeObserver)
    return exports
  }
  let p, scope
  const filename = name === 'StatusChart' ? path.resolve('src/components/chart/StatusChart.vue') : path.join(base, name === 'AutomationStats' ? 'components/AutomationStats.vue' : `components/chart/${name}.vue`)
  if (name === 'FullYearSalesChart') { scope = vue.effectScope(); p = scope.run(() => load(filename).default.setup()) }
  else {
    const bindings = name === 'StatusChart' ? 'pieChart,chartItems,total,resizeChart'
      : name === 'ProjectQualityChart' ? 'chartRef,chartData,renderChart,resizeChart'
      : name === 'AutomationStats'
      ? 'statistics,loading,loadFailed,fetchStatistics,capabilityGridRef,capabilityColumns,capabilityGroups,scheduleCapabilityLayout,formatValue'
      : 'activity,loading,loadingMore,loadFailed,loadMoreFailed,currentPage,rankItems,hasMore,activityLevel,loadNextPage'
    // DOM globals are scoped to script evaluation; no application runtime or real network is used.
    const globals = { window: globalThis.window, document: globalThis.document, getComputedStyle: globalThis.getComputedStyle, ResizeObserver: globalThis.ResizeObserver }
    globalThis.window = window; globalThis.document = document; globalThis.getComputedStyle = getComputedStyle; globalThis.ResizeObserver = ResizeObserver
    p = harness(name, bindings, { base, filename, api: endpoints, modules, props: api.props })
    p.restoreGlobals = () => Object.assign(globalThis, globals)
  }
  return { ...p, user, route, calls, observers, frames, listeners, charts, scale,
    mount: () => hooks.mount.forEach(fn => fn()), activate: () => hooks.activate.forEach(fn => fn()), deactivate: () => hooks.deactivate.forEach(fn => fn()),
    emit(event) { listeners.get(event)?.forEach(fn => fn()) },
    setPalette(value) { palette = value },
    flushFrames() { const pending = [...frames.values()]; frames.clear(); pending.forEach(fn => fn()) },
    records: () => load(path.join(base, 'records.ts')),
    close() { hooks.unmount.forEach(fn => fn()); if (scope) scope.stop(); else { p.close(); p.restoreGlobals() } },
  }
}

test('能力统计完整替换白名单快照，缺失字段不沿用旧值；指标保留 0/null 且默认值互不共享', async () => {
  const p = panel('AutomationStats'); p.mount(); p.activate(); await flush()
  assert.equal(p.calls.length, 1); assert.equal(p.loading.value, false); assert.equal(p.statistics.value.uiStats.pageCount, 0)
  const records = p.records(), input = statistics(2); input.data.uiStats.extra = 99; input.data.uiStats.pageCount = null
  const parsed = records.readStatistics(input); assert.equal(parsed.uiStats.pageCount, null); assert.equal('extra' in parsed.uiStats, false)
  delete input.data.uiStats.caseCount; assert.equal(records.readStatistics(input).uiStats.caseCount, null)
  const first = records.emptyStatistics(), second = records.emptyStatistics(); first.uiStats.pageCount = 2; assert.equal(second.uiStats.pageCount, null)
  assert.throws(() => records.readStatistics({ code: 500, data: statistics().data })); p.close()
})

function renderCapabilities(panel) {
  const filename = path.join(base, 'components/AutomationStats.vue')
  const { descriptor } = parse(readFileSync(filename, 'utf8'))
  const compiled = compileTemplate({ source: descriptor.template.content, filename, id: 'capability-content' })
  const code = ts.transpileModule(compiled.code, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
  const exports = {}
  new Function('require', 'exports', code)(() => ({ ...vue, resolveComponent: name => name }), exports)
  const root = exports.render(vue.proxyRefs(panel), [])
  const nodes = []
  function visit(node) {
    if (!node) return
    if (Array.isArray(node)) { node.forEach(visit); return }
    nodes.push(node)
    visit(node.children)
    if (typeof node.children?.default === 'function') visit(node.children.default())
  }
  visit(root)
  return nodes
}

test('成功加载与零统计都渲染六组能力卡片，失败保留重试且不吞掉恢复后的内容', async t => {
  const p = panel('AutomationStats', { read: async () => statistics(2) }); t.after(p.close)
  p.mount(); await flush()
  let nodes = renderCapabilities(p)
  assert.equal(nodes.filter(node => node.type === 'article').length, 6)
  for (const name of ['UI自动化', 'API自动化', 'Pytest自动化', '数据工厂', '测试配置', '定时任务']) {
    assert.ok(nodes.some(node => node.children === name), name)
  }
  assert.ok(nodes.some(node => node.type === 'dd' && node.children === '2'))
  p.statistics.value = p.records().readStatistics(statistics(0))
  nodes = renderCapabilities(p)
  assert.equal(nodes.filter(node => node.type === 'article').length, 6)
  assert.ok(nodes.some(node => node.type === 'dd' && node.children === '0'))
  p.loadFailed.value = true
  nodes = renderCapabilities(p)
  assert.equal(nodes.filter(node => node.type === 'article').length, 0)
  assert.ok(nodes.some(node => node.children?.default?.().some?.(child => child.children === '重新加载')) || nodes.some(node => node.children === '重新加载'))
  await p.fetchStatistics(); await flush()
  assert.equal(renderCapabilities(p).filter(node => node.type === 'article').length, 6)
})

for (const name of ['AutomationStats', 'FullYearSalesChart']) {
  test(`${name} 失败可重试且只接收最新快照，旧 finally 不结束当前 loading`, async () => {
    const requests = [], p = panel(name, { read: () => { const r = deferred(); requests.push(r); return r.promise } })
    const reload = name === 'AutomationStats' ? p.fetchStatistics : p.caseResultWeekSum
    p.mount(); const work = reload(); requests[0].resolve(name === 'AutomationStats' ? statistics(1) : trend(1)); await flush()
    assert.equal(p.loading.value, true); requests[1].reject(Error('failed')); await work
    assert.equal(p.loadFailed.value, true); assert.equal(p.loading.value, false)
    const retry = reload(); requests[2].resolve(name === 'AutomationStats' ? statistics(2) : trend(2)); await retry; await flush()
    assert.equal(p.loadFailed.value, false); p.close()
  })
  for (const field of ['userId', 'roleId', 'token', 'selected_environment']) {
    test(`${name} ${field} 同步往返清空旧快照，旧响应不复活`, async () => {
      const requests = [], p = panel(name, { read: () => { const r = deferred(); requests.push(r); return r.promise } })
      p.mount(); const previous = p.user[field]; p.user[field] = field === 'token' ? 'changed' : 9; p.user[field] = previous
      assert.equal(requests.length, 3); requests[0].resolve(name === 'AutomationStats' ? statistics(9) : trend(9)); requests[1].reject(Error('old')); await flush()
      assert.equal(p.loading.value, true); requests[2].resolve(name === 'AutomationStats' ? statistics(0) : trend(0)); await flush()
      assert.equal(p.loading.value, false); assert.equal(p.loadFailed.value, false); p.close()
    })
  }
  test(`${name} 缓存停用、切页和卸载不接收旧结果，返回重新读取`, async () => {
    const requests = [], p = panel(name, { read: () => { const r = deferred(); requests.push(r); return r.promise } })
    p.mount(); p.deactivate(); requests[0].resolve(name === 'AutomationStats' ? statistics(9) : trend(9)); await flush()
    assert.equal(p.loading.value, false); p.route.path = '/other'; p.route.fullPath = '/other'; p.activate(); assert.equal(requests.length, 1)
    p.route.path = '/index/home'; p.route.fullPath = '/index/home'; assert.equal(requests.length, 2)
    p.close(); requests[1].reject(Error('late')); await flush(); assert.equal(p.loadFailed.value, false)
  })
}

test('能力网格在错误后 DOM 重建时重新观察，停用清理帧和观察器，密度使用真实容器宽度', async () => {
  const p = panel('AutomationStats'); p.capabilityGridRef.value = { clientWidth: 600 }; p.mount(); await flush(); p.flushFrames()
  assert.equal(p.capabilityColumns.value, 2); const first = p.observers.at(-1)
  p.capabilityGridRef.value = null; await flush(); assert.equal(first.disconnected, true)
  p.capabilityGridRef.value = { clientWidth: 600 }; await flush(); p.scale.value = 1.35; await flush(); p.flushFrames()
  assert.equal(p.capabilityColumns.value, 1); assert.notEqual(p.observers.at(-1), first)
  p.scheduleCapabilityLayout(); p.deactivate(); assert.equal(p.frames.size, 0); assert.equal(p.observers.at(-1).disconnected, true)
  p.activate(); await flush(); assert.equal(p.observers.at(-1).disconnected, false); p.close()
})

test('趋势图聚合口径不变，主题、密度与 resize 只作用于当前实例；停用销毁且阻止迟到绘制', async () => {
  const p = panel('FullYearSalesChart'); p.fullYearSalesChart.value = { clientWidth: 600 }; p.mount(); p.activate(); await flush(); p.flushFrames()
  assert.deepEqual(p.summary.value, { api: 1, ui: 2, pytest: 3 })
  const chart = p.charts.at(-1), option = chart.options.findLast(option => option.series)
  assert.deepEqual(option.series.map(series => series.yAxisIndex), [1, 0, 1]); assert.deepEqual(option.series[1].data, [0, 1])
  p.setPalette('changed-token'); p.emit('mango-theme-change'); await flush(); assert.equal(p.charts.at(-1).options.at(-1).color[0], 'changed-token')
  p.scale.value = 1.35; p.emit('mango-density-change'); p.flushFrames(); assert.ok(p.charts.at(-1).resizes > 0)
  p.updateChart(); const callback = [...p.frames.values()][0], count = p.charts.length
  p.deactivate(); callback(); await flush(); assert.equal(p.charts.length, count); assert.equal(chart.disposed, true)
  assert.ok([...p.listeners.values()].every(set => set.size === 0)); assert.equal(p.frames.size, 0)
  p.activate(); await flush(); assert.equal(p.charts.at(-1).disposed, false); p.close(); assert.equal(p.charts.at(-1).disposed, true)
})

test('API 统计名称同步到趋势卡片、坐标轴和 tooltip 系列名称', async () => {
  const p = panel('FullYearSalesChart', { read: async () => ({
    ...trend(2), data: { ...trend(2).data, api_label: 'API 用例' },
  }) })
  p.fullYearSalesChart.value = { clientWidth: 600 }; p.mount(); await flush(); p.flushFrames()
  const option = p.charts.at(-1).options.findLast(option => option.series)
  assert.equal(p.apiLabel.value, 'API 用例')
  assert.equal(option.yAxis[0].name, 'API 用例（个）')
  assert.equal(option.series[1].name, 'API 用例')
  assert.equal(p.records().readExecutionTrend(trend()).api_label, 'API 场景')
  p.close()
})

test('趋势解析拒绝错位数组；活跃排行有限解析保留 0 并拒绝失败和错位数组', () => {
  const p = panel('FullYearSalesChart'), records = p.records()
  assert.throws(() => records.readExecutionTrend({ code: 200, data: { ...trend().data, api_count: [] } }))
  assert.deepEqual(records.readHomeActivity(activity([0], 0)).rows, [{ id: '0', name: 'User 0', count: 0 }])
  assert.throws(() => records.readHomeActivity({ code: 500, data: activity().data }))
  assert.throws(() => records.readHomeActivity({ code: 200, data: { ...activity().data, user_ids: [] } })); p.close()
})

test('活跃排行首次失败与空结果分开，滚动分页去重、失败重试及零总数清理', async () => {
  let mode = 'failed'
  const p = panel('HotProductChart', { read: async ({ page }) => {
    if (mode === 'failed') throw Error('read failed')
    return mode === 'empty' ? activity([], 0) : activity(page === 1 ? [0, 1] : [1, 2, 2], 3)
  } })
  p.mount(); await flush(); assert.equal(p.loadFailed.value, true); assert.equal(p.loading.value, false)
  mode = 'ready'; await p.activityLevel(true); assert.equal(p.loadFailed.value, false)
  mode = 'failed'; await p.loadNextPage(); assert.equal(p.currentPage.value, 1); assert.equal(p.loadMoreFailed.value, true)
  mode = 'ready'; await p.loadNextPage(); assert.equal(p.currentPage.value, 2); assert.equal(p.rankItems.value.length, 3); assert.equal(p.hasMore.value, false)
  assert.deepEqual(p.calls.at(-1), { page: 2, pageSize: 30 })
  mode = 'empty'; await p.activityLevel(true); assert.deepEqual(p.rankItems.value, []); assert.equal(p.activity.value.total, 0); p.close()
})

for (const field of ['userId', 'roleId', 'token', 'selected_environment']) {
  test(`活跃排行 ${field} 同步往返不串数据，旧请求不关闭当前 loading`, async () => {
    const requests = [], p = panel('HotProductChart', { read: () => { const r = deferred(); requests.push(r); return r.promise } })
    p.mount(); const previous = p.user[field]; p.user[field] = field === 'token' ? 'changed' : 9; p.user[field] = previous
    assert.equal(requests.length, 3); requests[0].resolve(activity([9])); requests[1].reject(Error('old')); await flush()
    assert.deepEqual(p.activity.value.rows, []); assert.equal(p.loading.value, true)
    requests[2].resolve(activity([0])); await flush(); assert.equal(p.activity.value.rows[0].id, '0'); p.close()
  })
}

test('活跃排行分页防重复，停用/卸载丢弃迟到结果，激活恢复读取', async () => {
  const requests = [], p = panel('HotProductChart', { read: () => { const r = deferred(); requests.push(r); return r.promise } })
  p.mount(); p.activate(); await p.activityLevel(true); assert.equal(requests.length, 1)
  p.deactivate(); requests[0].resolve(activity([9])); await flush(); assert.deepEqual(p.rankItems.value, [])
  p.activate(); assert.equal(requests.length, 2); p.close(); requests[1].resolve(activity([8])); await flush(); assert.deepEqual(p.rankItems.value, [])
})

test('项目图画布移除与重建释放旧实例并重新观察；停用期间数据变化和旧 resize 不创建实例', async () => {
  const row = { project_id: 0, project_name: 'Example project', report_count: 2, success_count: 0, fail_count: 1, warning_count: 1, other_count: 0, pass_rate: 0 }
  const p = panel('ProjectQualityChart', { props: { data: [row], loading: false } })
  p.chartRef.value = { clientWidth: 500 }; p.mount(); p.activate(); await flush()
  const first = p.charts.at(-1), firstObserver = p.observers.at(-1)
  assert.deepEqual(first.options.at(-1).series[0].data, [0])
  assert.ok(first.options.at(-1).tooltip.formatter([{ dataIndex: 0, value: 0 }]).includes('0.00%'))
  p.props.data = []; p.chartRef.value = null; await flush()
  assert.equal(first.disposed, true); assert.equal(firstObserver.disconnected, true)
  p.props.data = [row]; p.chartRef.value = { clientWidth: 600 }; await flush()
  const second = p.charts.at(-1); assert.notEqual(second, first); assert.notEqual(p.observers.at(-1), firstObserver)
  p.resizeChart(); const callback = [...p.frames.values()][0]; p.deactivate(); const count = p.charts.length
  p.props.data = [{ ...row, report_count: 9 }]; callback(); await flush()
  assert.equal(second.disposed, true); assert.equal(p.charts.length, count); assert.equal(p.frames.size, 0)
  p.activate(); await flush(); assert.equal(p.charts.at(-1).disposed, false); p.close(); assert.equal(p.charts.at(-1).disposed, true)
})

test('公共状态图保持所有调用方的可选状态/零值/中心文案协议，缓存恢复使用新主题并清理旧实例', async () => {
  const p = panel('StatusChart', { props: { success: 0, fail: 1, warning: 0, pending: 2, todo: 3, stopped: 4, other: 5, centerValue: 0, centerLabel: 'Example total' } })
  p.pieChart.value = { clientWidth: 500 }; p.mount(); p.activate(); await flush()
  assert.equal(p.total.value, 15); assert.deepEqual(p.chartItems.value.map(row => row.name), ['通过', '失败', '警告', '进行中', '待开始', '已停止', '其他'])
  const first = p.charts.at(-1); assert.equal(first.options.at(-1).series[0].data[0].value, 0)
  p.resizeChart(); const callback = [...p.frames.values()][0]; p.deactivate(); assert.equal(first.disposed, true)
  p.props.success = 6; p.setPalette('changed-token'); callback(); await flush()
  assert.equal(p.charts.at(-1), first); assert.ok([...p.listeners.values()].every(set => set.size === 0))
  p.activate(); await flush(); const second = p.charts.at(-1)
  assert.notEqual(second, first); assert.equal(second.options.at(-1).series[0].data[0].value, 6); assert.equal(second.options.at(-1).series[0].data[0].itemStyle.color, 'changed-token')
  p.pieChart.value = null; await flush(); assert.equal(second.disposed, true); p.close()
})

test('能力统计、三块首页图表及公共状态图的 SFC 脚本、模板和 LESS 编译', () => {
  const files = ['components/AutomationStats.vue', 'components/chart/FullYearSalesChart.vue', 'components/chart/HotProductChart.vue', 'components/chart/ProjectQualityChart.vue'].map(file => path.join(base, file))
  files.push(path.resolve('src/components/chart/StatusChart.vue'))
  for (const filename of files) {
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename }); assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: filename })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: filename, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    for (const style of descriptor.styles) assert.deepEqual(compileStyle({ source: style.content, filename, id: filename, scoped: style.scoped, preprocessLang: style.lang }).errors, [])
  }
})
