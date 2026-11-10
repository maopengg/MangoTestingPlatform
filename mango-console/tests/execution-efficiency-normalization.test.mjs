import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import dayjs from 'dayjs'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, deferred, flush as microtasks } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/report/execution-efficiency'), response = data => ({ code: 200, data })
const overview = (count = 1) => response({ summary: { pending: count, running: 0, longest_wait_ms: null }, items: [], count })
async function flush() { await microtasks(); await new Promise(resolve => setImmediate(resolve)); await microtasks() }
function setup(settings = {}) {
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['report:read'] })
  const route = vue.reactive({ path: '/report/execution-efficiency/index', fullPath: '/report/execution-efficiency/index' })
  const life = { mount: [], unmount: [], activate: [], deactivate: [] }, calls = [], navigations = [], timers = new Map(), listeners = new Set()
  const previous = { document: globalThis.document, setTimeout: globalThis.setTimeout, clearTimeout: globalThis.clearTimeout }
  const doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }), add = doc.addEventListener.bind(doc), remove = doc.removeEventListener.bind(doc)
  doc.addEventListener = (event, callback) => { listeners.add(callback); add(event, callback) }
  doc.removeEventListener = (event, callback) => { listeners.delete(callback); remove(event, callback) }
  let timerSequence = 0
  Object.assign(globalThis, { document: doc, setTimeout: (fn, delay) => { const id = ++timerSequence; timers.set(id, { fn, delay }); return id }, clearTimeout: id => timers.delete(id) })
  const h = harness('index', 'section,loading,error,snapshot,conditions,navigation,dateRange,pagination,slowPage,reportPage,slowCases,slowReports,metrics,chartHeight,history,optionState,refresh,search,reset,onNavigation,changeSection,buildQuery,openOptions,searchOptions,moreOptions,retryOptions,reportActions,caseActions,trendOption,phaseOption,formatStartedAt,options,environment', {
    base, filename: path.join(base, 'index.vue'),
    api: {
      getExecutionEfficiency: query => { calls.push(['overview', query]); return settings.overview ? settings.overview(query) : overview() },
      getExecutionEfficiencyOptions: query => { calls.push(['options', query]); return settings.options ? settings.options(query) : response({ items: [{ id: 0, name: 'Zero' }], has_more: false }) },
    },
    modules: {
      vue: { ...vue, onMounted: fn => life.mount.push(fn), onBeforeUnmount: fn => life.unmount.push(fn), onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn) },
      dayjs: { default: dayjs }, 'vue-router': { useRoute: () => route, useRouter: () => ({ push: value => navigations.push(value) }) },
      '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
      '@/store/modules/get-enum': { useEnum: () => ({ environment_type: [{ key: 0, title: 'Zero' }], getEnum: () => settings.enums ? settings.enums() : Promise.resolve() }) },
    },
  })
  return { ...h, user, permission, route, life, calls, navigations, timers, listeners, doc,
    mount() { life.mount.forEach(fn => fn()); life.activate.forEach(fn => fn()) },
    async runTimers() { for (const [id, timer] of [...timers]) { timers.delete(id); assert.equal(timer.delay, 250); timer.fn() }; await flush() },
    close() { life.unmount.forEach(fn => fn()); h.close(); Object.assign(globalThis, previous) },
  }
}

test('初始化等待枚举且合并重复读取，成功后才查统计；首次失败可重试', async t => {
  const enums = deferred(), read = deferred(), h = setup({ enums: () => enums.promise, overview: () => read.promise }); t.after(h.close)
  h.mount(); await flush(); assert.equal(h.loading.value, true); assert.equal(h.calls.length, 0)
  const first = h.refresh(); assert.equal(first, h.refresh()); enums.resolve(); await flush()
  assert.equal(h.calls.length, 1); read.resolve(overview()); await first; assert.equal(h.loading.value, false); assert.equal(h.snapshot.value.count, 1)
  let attempts = 0
  const other = setup({ enums: () => { if (++attempts === 1) throw Error('network'); return Promise.resolve() } })
  try { other.mount(); await flush(); assert.ok(other.error.value); assert.equal(other.loading.value, false); assert.equal(other.calls.length, 0); await other.refresh(); assert.equal(other.snapshot.value.count, 1); assert.equal(other.error.value, '') } finally { other.close() }
})

test('业务失败、坏响应和网络失败都恢复局部重试，不展示上次范围的统计', async t => {
  const values = [overview(), { code: 403 }, response({ summary: null }), new Error('internal'), overview(2)]
  const h = setup({ overview: () => { const value = values.shift(); if (value instanceof Error) throw value; return value } }); t.after(h.close)
  h.mount(); await flush(); assert.equal(h.snapshot.value.count, 1)
  for (let i = 0; i < 3; i++) { await h.search(); assert.equal(h.snapshot.value, null); assert.ok(h.error.value); assert.equal(h.loading.value, false); assert.equal(h.pagination.pageCount, 0) }
  await h.refresh(); assert.equal(h.snapshot.value.count, 2); assert.equal(h.error.value, '')
})

test('搜索/Tab A-B-A和分页请求序号保护当前结果，重复相同查询合并至实际完成', async t => {
  const reads = [deferred(), deferred(), deferred()]; let index = 0
  const h = setup({ overview: () => reads[index++].promise }); t.after(h.close); h.mount(); await flush()
  const first = h.refresh(); assert.equal(first, h.refresh())
  h.section.value = 'anomalies'; const second = h.changeSection(); await flush()
  h.section.value = 'queue'; const last = h.changeSection(); await flush()
  reads[0].resolve(overview(10)); reads[1].reject(Error('stale')); await Promise.all([first, second]); assert.equal(h.loading.value, true)
  reads[2].resolve(overview(3)); await last; assert.equal(h.snapshot.value.count, 3); assert.equal(h.pagination.pageCount, 3); assert.equal(h.error.value, '')
  assert.deepEqual(h.calls.map(item => item[1].section), ['queue', 'anomalies', 'queue'])
})

for (const field of ['userId', 'roleId', 'token', 'selected_environment', 'permissionKeys', 'route']) {
  test(`${field}切换使旧响应失效，关闭历史并清空旧筛选/任务选项`, async t => {
    const old = deferred(); let reads = 0
    const h = setup({ overview: () => ++reads === 1 ? old.promise : overview(2) }); t.after(h.close); h.mount(); await flush()
    h.history.visible = true; h.conditions[2].value = [1]
    if (field === 'permissionKeys') h.permission.permissionKeys = ['report:read', 'other:read']
    else if (field === 'route') { h.route.fullPath = '/report/index'; h.route.path = '/report/index' }
    else { const before = h.user[field]; h.user[field] = field === 'token' ? '' : 2; h.user[field] = before }
    await flush(); old.resolve(overview(99)); await flush()
    assert.equal(h.history.visible, false); assert.equal(h.history.query, undefined); assert.deepEqual(h.conditions[2].value, [])
    assert.notEqual(h.snapshot.value?.count, 99); assert.equal(h.loading.value, false)
  })
}

test('后台/KeepAlive暂停统计和选项定时器，返回恢复；卸载清理监听和迟到结果', async t => {
  const old = deferred(); let reads = 0
  const h = setup({ overview: () => ++reads === 1 ? old.promise : overview(reads) }); t.after(h.close); h.mount(); await flush()
  h.searchOptions('task_ids', 'pending'); assert.equal(h.timers.size, 1)
  h.doc.visibilityState = 'hidden'; h.doc.dispatchEvent(new Event('visibilitychange')); assert.equal(h.timers.size, 0)
  old.resolve(overview(99)); await flush(); await h.refresh(); assert.equal(reads, 1); assert.equal(h.snapshot.value, null)
  h.doc.visibilityState = 'visible'; h.doc.dispatchEvent(new Event('visibilitychange')); await flush(); assert.equal(h.snapshot.value.count, 2)
  h.life.deactivate.forEach(fn => fn()); await h.refresh(); assert.equal(reads, 2)
  h.life.activate.forEach(fn => fn()); await flush(); assert.equal(h.snapshot.value.count, 3)
  h.life.unmount.forEach(fn => fn()); await h.refresh(); assert.equal(h.listeners.size, 0); assert.equal(reads, 3)
})

test('初始化枚举及选项HTTP迟到时不能在后台触发后续查询，返回重读当前上下文', async t => {
  const enums = deferred(), option = deferred(); let attempts = 0
  const h = setup({ enums: () => ++attempts === 1 ? enums.promise : Promise.resolve(), options: () => option.promise }); t.after(h.close)
  h.mount(); await flush(); h.doc.visibilityState = 'hidden'; h.doc.dispatchEvent(new Event('visibilitychange'))
  enums.resolve(); await flush(); assert.equal(h.calls.length, 0)
  h.doc.visibilityState = 'visible'; h.doc.dispatchEvent(new Event('visibilitychange')); await flush(); assert.equal(h.snapshot.value.count, 1)
  const pending = h.openOptions('task_ids'); await flush()
  h.doc.visibilityState = 'hidden'; h.doc.dispatchEvent(new Event('visibilitychange'))
  option.resolve(response({ items: [{ id: 1, name: 'old' }], has_more: false })); await pending
  assert.deepEqual(h.options('task_ids'), []); assert.equal(h.optionState.task_ids.loading, false)
})

test('导航与查询复制路径和多值，只发白名单参数，产品/环境0不被丢弃，重置清空', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush()
  const navigation = { projectProduct: 0, module: 0, moduleIds: [1, 2] }; await h.onNavigation(navigation); navigation.moduleIds.push(3)
  assert.deepEqual(h.navigation.moduleIds, [1, 2]); h.section.value = 'timing'
  h.conditions[0].value = [0, 1]; h.conditions[1].value = [0, 2]; h.conditions[2].value = [5]; h.conditions[3].value = [6]; h.conditions[4].value = ' 123 '
  h.pagination.page = 2; h.pagination.pageSize = 50; const query = h.buildQuery()
  assert.equal(query.project_product_id, 0); assert.equal(query.module_ids__in, '1,2'); assert.equal(query.test_env__in, '0,1'); assert.equal(query.case_type__in, '0,2')
  assert.equal(query.task_ids__in, '5'); assert.equal(query.task_group_ids__in, '6'); assert.equal(query.report_id, '123'); assert.equal(query.page_size, 50); assert.ok(query.start_at)
  await h.pagination.onChange(); assert.deepEqual(h.calls.at(-1)[1], query)
  h.slowPage.value = 99; h.reportPage.value = 99; await h.refresh(); assert.equal(h.slowPage.value, 1); assert.equal(h.reportPage.value, 1)
  await h.reset(); assert.equal(h.navigation.projectProduct, null); assert.equal(h.pagination.page, 1); assert.deepEqual(h.conditions[0].value, []); assert.equal(h.conditions[4].value, '')
})

test('远程选项独立失败可重试，分页去重，关键字防抖与旧响应失效', async t => {
  let failed = true
  const h = setup({ options: query => { if (failed) throw Error('network'); return response({ items: [{ id: 0, name: query.keyword || 'zero' }, { id: query.page, name: 'page' }], has_more: query.page < 2 }) } }); t.after(h.close)
  h.mount(); await flush(); await h.openOptions('task_ids'); assert.ok(h.optionState.task_ids.error); assert.equal(h.optionState.task_ids.loading, false)
  failed = false; await h.retryOptions('task_ids'); assert.equal(h.optionState.task_ids.error, ''); assert.equal(h.optionState.task_ids.page, 1)
  await h.moreOptions('task_ids'); assert.deepEqual(h.options('task_ids').map(item => item.value), [0, 1, 2])
  h.searchOptions('task_ids', 'old'); h.searchOptions('task_ids', 'latest'); assert.equal(h.timers.size, 1); await h.runTimers()
  assert.equal(h.calls.at(-1)[1].keyword, 'latest'); assert.equal(h.options('task_ids')[0].label, 'latest'); assert.equal(h.optionState.task_ids.page, 1)
  assert.deepEqual(h.options('test_env'), [{ value: 0, label: 'Zero' }]); assert.equal(h.environment(0), 'Zero')
})

test('旧选项及其finally不能覆盖换产品后的新请求，重复打开合并', async t => {
  const reads = [deferred(), deferred()]; let index = 0
  const h = setup({ options: () => reads[index++].promise }); t.after(h.close); h.mount(); await flush()
  const first = h.openOptions('task_ids'); assert.equal(first, h.openOptions('task_ids')); await flush()
  await h.onNavigation({ projectProduct: 2, module: null }); const second = h.openOptions('task_ids'); await flush()
  reads[0].resolve(response({ items: [{ id: 1, name: 'old' }], has_more: false })); await first; assert.equal(h.optionState.task_ids.loading, true)
  reads[1].resolve(response({ items: [{ id: 2, name: 'new' }], has_more: false })); await second; assert.equal(h.options('task_ids')[0].label, 'new')
})

test('远程追加失败保留已选标签，重试同一分页；坏选项响应可恢复', async t => {
  let fail = true, malformed = false
  const h = setup({ options: query => {
    if (query.page === 2 && fail) throw Error('append failed')
    if (malformed) return response({ items: null })
    return response({ items: [{ id: query.page, name: `page-${query.page}` }], has_more: query.page === 1 })
  } }); t.after(h.close); h.mount(); await flush()
  await h.openOptions('task_group_ids'); await h.moreOptions('task_group_ids')
  assert.equal(h.optionState.task_group_ids.page, 1); assert.ok(h.optionState.task_group_ids.error); assert.equal(h.options('task_group_ids')[0].label, 'page-1')
  fail = false; await h.retryOptions('task_group_ids'); assert.equal(h.calls.at(-1)[1].page, 2); assert.deepEqual(h.options('task_group_ids').map(item => item.value), [1, 2])
  malformed = true; h.searchOptions('task_group_ids', 'new'); await h.runTimers(); assert.ok(h.optionState.task_group_ids.error); assert.equal(h.optionState.task_group_ids.loading, false)
  malformed = false; await h.retryOptions('task_group_ids'); assert.equal(h.optionState.task_group_ids.error, '')
})

test('有限模型保留0/缺失计时和完整路径，不透传任意对象；错误结构失败', t => {
  const h = setup(); t.after(h.close); const model = h.load('overview.ts'), config = h.load('config.ts')
  for (const value of [false, '', {}, NaN, Infinity, -1]) { assert.equal(model.efficiencyNumber(value), null); assert.equal(config.duration(value), '—') }
  const input = response({ summary: { p50_ms: 0 }, phases: [{ name: 'Unknown', duration_ms: null }], trend: [{ time: 'example', p50_ms: null, p95_ms: 0 }], slow_cases: [{ trace_id: 'example', detail_id: '9223372036854775807', report_id: 0, project_product: { name: 'Product', project: { name: 'Project' } }, module: { full_path: 'A/B/C' } }] })
  const parsed = model.parseEfficiencyOverview(input); assert.equal(parsed.summary.p50_ms, 0); assert.equal(parsed.summary.p95_ms, null); assert.equal(parsed.slow_cases[0].detail_id, '9223372036854775807'); assert.equal(parsed.slow_cases[0].module.full_path, 'A/B/C')
  h.snapshot.value = parsed; assert.equal(h.chartHeight, '240px'); assert.equal(h.phaseOption.value.series[0].data[0], null); assert.deepEqual(h.trendOption.value.series[1].data, [null]); assert.deepEqual(h.trendOption.value.series[2].data, [0])
  for (const value of [{ code: 403 }, response(null), response({ summary: {}, items: {} }), response({ summary: {}, trend: [null] })]) assert.throws(() => model.parseEfficiencyOverview(value))
  assert.equal(h.formatStartedAt('bad'), '—'); assert.equal(h.formatStartedAt('2026-01-01T12:00:00'), '2026-01-01 12:00:00')
})

test('报告和历史操作保护缺失ID且保留ID0，不打开无范围历史', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush()
  h.reportActions({ report_id: 0 })[0].onClick(); assert.equal(h.navigations.at(-1).query.id, 0)
  h.reportActions({ report_id: null })[0].onClick(); assert.equal(h.navigations.length, 1)
  const row = { report_id: 0, detail_id: null, case_name: 'Example' }; h.caseActions(row)[0].onClick(); assert.equal(h.history.visible, false)
  row.detail_id = 0; h.caseActions(row)[0].onClick(); assert.equal(h.history.visible, true); assert.equal(h.history.query.test_suite_detail_id, 0)
})

test('页面及共享导航、图表和历史窗口SFC脚本/模板/样式编译', async () => {
  for (const filename of [path.join(base, 'index.vue'), 'src/components/business/ProjectProductNavigationWorkbench.vue', 'src/components/business/ExecutionResultHistoryDrawer.vue', 'src/views/report/effectiveness/components/EffectivenessChart.vue']) {
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename }); assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: filename }); assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: filename, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ id: filename, filename, source: style.content, scoped: style.scoped, preprocessLang: style.lang })).errors, [])
  }
})
