import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/report')
const response = (data, extra = {}) => ({ code: 200, data, ...extra })
const reportPage = (id = 1, status = 3) => response([{ id, status, execution_summary: { fail: 1 } }], { totalSize: 1 })
const chartPage = count => response({ status_distribution: [{ status: 1, value: count }], trend: [] })
function setup(settings = {}) {
  const route = vue.reactive({ path: '/report/index', fullPath: '/report/index', query: {} })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 0 })
  const permission = vue.reactive({ permissionKeys: ['report:read'] })
  const life = { mount: [], activate: [], deactivate: [], unmount: [] }, calls = [], navigations = [], dialogs = [], messages = []
  const doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  const polling = { enabled: false, callback: null, start() { this.enabled = true }, stop() { this.enabled = false }, isRunning: () => false }
  const table = { indexColumn: { title: 'ID', key: 'index', width: 100 } }
  const h = harness('index', 'conditionItems,buildFilterValue,applyRouteFilters,sidebarModuleIds,pagination,onSearchRefresh,onResetSearch,doRefresh,rows,listLoading,listError,charts,enumLoading,enumError,searchLoading,searchErrors,loadTaskOptions,loadTaskGroupOptions,loadUserOptions,onNavigationFilterChange,loadReportOverview,activeReportIds,retryState,noticeState,diagnosticDrawer,offlineExport,retryModalRef,onRetry,onRetryFailed,onCancelRetryModal,onConfirmRetryModal,onStop,stopLoadingId,onSendNotice,onCancelNoticeModal,onConfirmNoticeModal,noticeForm,loadNoticeOptions,onClick,openOfflineExport,groupExportId', {
    base,
    api: {
      getSystemTestSuite: query => { calls.push(['list', query]); return settings.list ? settings.list(query) : Promise.resolve(reportPage()) },
      getSystemTestSuiteDetailsReport: query => { calls.push(['charts', query]); return settings.charts ? settings.charts(query) : Promise.resolve(chartPage(1)) },
      getSystemTasks: query => { calls.push(['tasks', query]); return settings.tasks ? settings.tasks(query) : Promise.resolve(response([{ id: 0, name: 'Example' }])) },
      getScheduledTaskGroupOptions: product => { calls.push(['groups', product]); return settings.groups ? settings.groups(product) : Promise.resolve(response([{ key: 0, title: 'Example group' }])) },
      getUserName: () => { calls.push(['users']); return settings.users ? settings.users() : Promise.resolve(response([{ key: 0, title: 'Example user' }])) },
      getSystemTestSuiteDetailsExecutionOptions: () => { calls.push(['executionOptions']); return settings.executionOptions ? settings.executionOptions() : Promise.resolve(response({ api_platform_limit: 4 })) },
      getSystemTestSuiteDetailsAllRetry: (...args) => { calls.push(['retry', ...args]); return settings.retry ? settings.retry(...args) : Promise.resolve(response({})) },
      retryFailedReportCases: id => { calls.push(['retryFailed', id]); return settings.retryFailed ? settings.retryFailed(id) : Promise.resolve(response({ retry_count: 1 })) },
      postSystemTestSuiteStop: id => { calls.push(['stop', id]); return settings.stop ? settings.stop(id) : Promise.resolve(response({})) },
      getSystemNoticeName: id => { calls.push(['noticeOptions', id]); return settings.noticeOptions ? settings.noticeOptions(id) : Promise.resolve(response([{ value: 0, label: 'Zero' }])) },
      postSystemTestSuiteSendNotice: payload => { calls.push(['notice', payload]); return settings.notice ? settings.notice(payload) : Promise.resolve(response({})) },
      get: config => config.data(),
    },
    modules: {
      vue: { ...vue, onMounted: fn => life.mount.push(fn), onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn), onBeforeUnmount: fn => life.unmount.push(fn) },
      '@arco-design/web-vue': {
        Message: Object.fromEntries(['success', 'error', 'warning', 'info'].map(kind => [kind, value => messages.push([kind, value])])),
        Modal: { confirm: config => { const dialog = { config, closed: false, close() { this.closed = true }, update() {} }; dialogs.push(dialog); return dialog } },
      },
      'vue-router': { useRoute: () => route, useRouter: () => ({ push: query => navigations.push(query) }) },
      '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
      '@/store/modules/get-enum': { useEnum: () => ({ getEnum: () => settings.enums ? settings.enums() : Promise.resolve(), colors: {}, environment_type: [] }) },
      '@/hooks/table': { useTable: () => table, useTableColumn: columns => columns, useRowKey: () => 'id' },
      '@/hooks/use-page-polling': { usePagePolling: callback => { polling.callback = callback; return polling }, isPendingExecution: record => [2, 3].includes(record.status) },
      '@/store/page-data': { usePageData: () => ({ setRecord() {} }) },
    },
  })
  let mounted = false, previous
  return { ...h, route, user, permission, life, calls, navigations, dialogs, messages, doc, polling, item: key => h.conditionItems.find(item => item.key === key),
    mount() { mounted = true; previous = globalThis.document; globalThis.document = doc; life.mount.forEach(fn => fn()); life.activate.forEach(fn => fn()) },
    async visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')); await flush() },
    async poll() { await polling.callback({ isCurrent: () => doc.visibilityState === 'visible' && route.path === '/report/index' }) },
    close() { if (mounted) { life.unmount.forEach(fn => fn()); globalThis.document = previous }; h.close() },
  }
}

test('真实页面 setup 的搜索配置实例隔离，包括 ID customRef、数组、选项和重置', t => {
  const a = setup(), b = setup(); t.after(a.close); t.after(b.close)
  a.item('id').value = '5574、5577，5578'
  a.item('status').value.push(0)
  a.item('tasks_id').optionItems.push({ label: 'Example', value: 1 })
  assert.equal(a.item('id').value, '5574,5577,5578')
  assert.equal(b.item('id').value, '')
  assert.deepEqual(b.item('status').value, [])
  assert.deepEqual(b.item('tasks_id').optionItems, [])
  const filters = a.load('filters.ts')
  const saved = a.item('status').value
  filters.resetReportConditions(a.conditionItems)
  assert.notEqual(saved, a.item('status').value)
  assert.equal(a.item('id').value, '')
  for (const item of a.conditionItems) if (item.multiple || item.type === 'date-range') assert.deepEqual(item.value, [])
  a.item('status').value.push(3); filters.resetReportConditions(a.conditionItems)
  assert.deepEqual(b.buildFilterValue(), {})
})

test('白名单参数：集合去重保留0、级联转真实ID、子模块范围、来源布尔及长字符串ID', t => {
  const h = setup(); t.after(h.close)
  h.item('id').value = '5574、5577、5574、'
  h.item('project_product').value = [4, 0]
  h.item('module').value = 8
  h.sidebarModuleIds.value = [0, '90071992547409931234', 0]
  h.item('tasks_id').value = 0
  h.item('tasks__task_group_id').value = [0, 2, 0]
  h.item('status').value = [0, '3', 0, '', null]
  h.item('test_env').value = [0]
  h.item('execution_scene').value = [1, 2]
  h.item('execution_scope').value = [0, 1]
  h.item('case_type').value = [0, 2]
  h.item('user').value = [0]
  h.item('report_source').value = 'scheduled'
  h.item('date_range').value = ['2024-02-29', '2024-03-01']
  const query = h.buildFilterValue()
  assert.deepEqual(query, {
    id__in: '5574,5577', project_product: 0, tasks_id: 0,
    module__in: '0,90071992547409931234', tasks__task_group_id__in: '0,2', status__in: '0,3',
    test_env__in: '0', execution_scene__in: '1,2', execution_scope__in: '0,1', case_type__in: '0,2', user__in: '0',
    tasks__isnull: false, create_time__gte: '2024-02-29 00:00:00', create_time__lte: '2024-03-01 23:59:59',
  })
  h.item('status').value.push(5); h.sidebarModuleIds.value.push(7)
  assert.equal(query.status__in, '0,3'); assert.equal(query.module__in, '0,90071992547409931234')
  h.item('report_source').value = 'non_scheduled'; assert.equal(h.buildFilterValue().tasks__isnull, true)
})

test('路由筛选按专用协议映射，拒绝额外参数透传；非法日期、空值和非法 ID 不查询', t => {
  const h = setup(); t.after(h.close)
  Object.assign(h.route.query, {
    project_product: ['0'], module: '2', tasks_id: '3', status: ['0,3', '3,5'], case_type: '0,2', user: '0',
    tasks__task_group_id: ['0', '7'], report_source: 'non_scheduled',
    start_date: '2024-02-29', end_date: '2024-03-01',
    group_execution_id: '90071992547409931234', test_suite_ids: '4,5,4', role: 'admin', pageSize: 9999,
  })
  h.applyRouteFilters()
  const query = h.buildFilterValue()
  assert.equal(query.group_execution_id, '90071992547409931234')
  assert.equal(query.id__in, '4,5'); assert.equal(query.project_product, '0')
  assert.equal(query.status__in, '0,3,5'); assert.equal(query.case_type__in, '0,2')
  assert.equal(query.tasks__isnull, true)
  assert.equal(query.role, undefined); assert.equal(query.pageSize, undefined)
  h.load('filters.ts').resetReportConditions(h.conditionItems)
  h.route.query = { project_product: { id: 9 }, status: [false, -1, 1.5, {}, null], start_date: '2025-02-29', end_date: '2025-03-01' }
  h.applyRouteFilters(); assert.deepEqual(h.buildFilterValue(), {})
  h.item('date_range').value = ['2026-05-02', '2026-05-01']; assert.deepEqual(h.buildFilterValue(), {})
})

test('单个ID保持精确查询，空搜索不发送null、undefined或空集合', t => {
  const h = setup(); t.after(h.close)
  assert.deepEqual(h.buildFilterValue(), {})
  h.item('id').value = '90071992547409931234'
  assert.deepEqual(h.buildFilterValue(), { id: '90071992547409931234' })
  h.item('id').value = ''; h.item('project_product').value = null; h.item('module').value = []
  assert.deepEqual(h.buildFilterValue(), {})
  for (const key of ['status', 'tasks__task_group_id', 'test_env', 'execution_scene', 'execution_scope', 'case_type', 'user']) {
    assert.equal(h.item(key).multiple, true); assert.equal(h.item(key).searchOperator, 'in')
  }
  assert.notEqual(h.item('tasks_id').multiple, true)
})

test('主动搜索和重置回到第一页，分页查询本身不被无条件重置', async t => {
  const h = setup(); t.after(h.close)
  h.pagination.page = 5; await h.onSearchRefresh(); assert.equal(h.pagination.page, 1)
  h.pagination.page = 6; h.item('status').value = [3]
  await h.onResetSearch(); assert.equal(h.pagination.page, 1); assert.deepEqual(h.item('status').value, [])
})

test('报告列表与趋势组件的脚本、模板、样式可编译', async () => {
  for (const file of ['index.vue', 'components/ReportTrendChart.vue']) {
    const filename = path.join(base, file), { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: file })
    assert.deepEqual(compileTemplate({ id: file, source: descriptor.template.content, filename, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    for (const style of descriptor.styles) {
      const result = await compileStyleAsync({ id: file, source: style.content, filename, scoped: style.scoped, preprocessLang: style.lang })
      assert.deepEqual(result.errors, [])
    }
  }
})

test('枚举初始化合并；列表、统计、选项独立加载；同一查询不重复HTTP', async t => {
  const enums = deferred(), list = deferred(), chart = deferred(), users = deferred()
  let enumCalls = 0
  const h = setup({ enums: () => { enumCalls++; return enums.promise }, list: () => list.promise, charts: () => chart.promise, users: () => users.promise }); t.after(h.close)
  h.mount(); await flush(); const repeat = h.doRefresh(); await flush()
  assert.equal(enumCalls, 1); assert.equal(h.enumLoading.value, true)
  assert.equal(h.calls.filter(item => item[0] === 'list').length, 0)
  assert.equal(h.searchLoading.users, true); assert.equal(h.searchLoading.tasks, false)
  enums.resolve(); await flush()
  assert.equal(h.calls.filter(item => item[0] === 'list').length, 1)
  assert.equal(h.calls.filter(item => item[0] === 'charts').length, 1)
  assert.equal(h.listLoading.value, true); assert.equal(h.charts.loading, true)
  chart.resolve(chartPage(9)); await flush(); assert.equal(h.charts.counts.success, 9); assert.equal(h.charts.loading, false); assert.equal(h.listLoading.value, true)
  list.resolve(reportPage(0, 2)); users.resolve(response([])); await repeat; await flush()
  assert.equal(h.rows.value[0].id, 0); assert.equal(h.listLoading.value, false); assert.equal(h.polling.enabled, true)
})

test('首次失败恢复，枚举失败不查列表，列表和统计失败可分别重试', async t => {
  let enums = 0, lists = 0, charts = 0
  const h = setup({ enums: () => { if (++enums === 1) throw Error('network'); return Promise.resolve() },
    list: () => ++lists === 1 ? Promise.resolve({ code: 403 }) : Promise.resolve(reportPage(2, 1)),
    charts: () => ++charts === 1 ? Promise.resolve(response({})) : Promise.resolve(chartPage(5)),
  }); t.after(h.close); h.mount(); await flush()
  assert.ok(h.enumError.value); assert.equal(h.enumLoading.value, false); assert.equal(lists, 0)
  await h.doRefresh(); assert.ok(h.listError.value); assert.ok(h.charts.error); assert.equal(h.listLoading.value, false); assert.equal(h.polling.enabled, true)
  await h.doRefresh(); assert.equal(h.listError.value, ''); assert.equal(h.charts.error, ''); assert.equal(h.rows.value[0].id, 2); assert.equal(h.polling.enabled, false)
})

test('搜索 A-B-A 与翻页忽略旧响应和旧finally，保留真正的最新页码', async t => {
  const jobs = [deferred(), deferred(), deferred(), deferred()]; let index = 0
  const h = setup({ list: () => jobs[index++].promise }); t.after(h.close); h.mount(); await flush()
  h.item('status').value = [3]; const second = h.onSearchRefresh(); await flush()
  h.item('status').value = []; const third = h.onSearchRefresh(); await flush()
  jobs[0].resolve(reportPage(99)); jobs[1].reject(Error('old')); await second; await flush()
  assert.equal(h.rows.value.length, 0); assert.equal(h.listLoading.value, true)
  jobs[2].resolve(reportPage(3)); await third; assert.equal(h.rows.value[0].id, 3)
  h.pagination.page = 4; const fourth = h.pagination.onChange(); await flush()
  assert.equal(h.calls.filter(item => item[0] === 'list').at(-1)[1].page, 4)
  jobs[3].resolve(reportPage(4)); await fourth; assert.equal(h.pagination.page, 4); assert.equal(h.rows.value[0].id, 4)
})

test('轮询静默更新并保留失败前的数据，失败后继续重试，完成后停止', async t => {
  let calls = 0
  const h = setup({ list: () => { calls++; if (calls === 2) throw Error('network'); return Promise.resolve(reportPage(calls, calls === 3 ? 1 : 2)) } }); t.after(h.close)
  h.mount(); await flush(); assert.equal(h.rows.value[0].id, 1); assert.equal(h.polling.enabled, true)
  const poll = h.poll(); assert.equal(h.listLoading.value, false); assert.equal(h.charts.loading, false); await poll
  assert.equal(h.rows.value[0].id, 1); assert.ok(h.listError.value); assert.equal(h.polling.enabled, true)
  await h.poll(); assert.equal(h.rows.value[0].id, 3); assert.equal(h.listError.value, ''); assert.equal(h.polling.enabled, false)
})

for (const field of ['userId', 'roleId', 'token', 'selected_environment', 'permissionKeys', 'route']) {
  test(`${field}切换后拒绝旧响应，清空窗口和选项并重新初始化`, async t => {
    const old = deferred(); let requests = 0
    const h = setup({ list: () => ++requests === 1 ? old.promise : Promise.resolve(reportPage(2, 1)) }); t.after(h.close); h.mount(); await flush()
    h.diagnosticDrawer.visible = true; h.offlineExport.visible = true; h.noticeState.visible = true; h.item('status').value = [3]
    if (field === 'permissionKeys') h.permission.permissionKeys = ['report:read', 'other:read']
    else if (field === 'route') { h.route.path = '/other'; h.route.fullPath = '/other' }
    else { const previous = h.user[field]; h.user[field] = field === 'token' ? '' : 2; h.user[field] = previous }
    await flush(); old.resolve(reportPage(99)); await flush()
    assert.notEqual(h.rows.value[0]?.id, 99); assert.equal(h.diagnosticDrawer.visible, false); assert.equal(h.offlineExport.visible, false); assert.equal(h.noticeState.visible, false)
    assert.deepEqual(h.item('status').value, []); assert.equal(h.listLoading.value, false)
  })
}

test('后台、KeepAlive停用及卸载使列表/统计/选项迟到响应失效；回来重新加载', async t => {
  const oldList = deferred(), oldChart = deferred(), oldOptions = deferred(); let lists = 0, charts = 0, tasks = 0
  const h = setup({ list: () => ++lists === 1 ? oldList.promise : Promise.resolve(reportPage(lists, 1)),
    charts: () => ++charts === 1 ? oldChart.promise : Promise.resolve(chartPage(charts)),
    tasks: () => ++tasks === 1 ? oldOptions.promise : Promise.resolve(response([{ id: 0, name: 'Current' }])),
  }); t.after(h.close); h.mount(); await flush(); await h.visibility('hidden')
  oldList.resolve(reportPage(99)); oldChart.resolve(chartPage(99)); oldOptions.resolve(response([{ id: 99, name: 'Old' }])); await flush()
  assert.equal(h.rows.value.length, 0); assert.equal(h.charts.counts.success, 0); assert.deepEqual(h.item('tasks_id').optionItems, [])
  assert.equal(h.listLoading.value, false); assert.equal(h.searchLoading.tasks, false)
  await h.visibility('visible'); assert.equal(h.rows.value[0].id, 2)
  h.life.deactivate.forEach(fn => fn()); await h.doRefresh(); assert.equal(lists, 2)
  h.life.activate.forEach(fn => fn()); await flush(); assert.equal(h.rows.value[0].id, 3)
})

test('产品切换清空所属任务条件，选项失败可独立重试，不等待选项才加载列表', async t => {
  const first = deferred(); let tasks = 0
  const h = setup({ tasks: () => ++tasks === 1 ? first.promise : tasks === 2 ? Promise.reject(Error('network')) : Promise.resolve(response([{ id: 0, name: 'Current' }])) }); t.after(h.close); h.mount(); await flush()
  h.item('tasks_id').value = 9; h.item('tasks__task_group_id').value = [9]
  await h.onNavigationFilterChange({ projectProduct: 0, module: 0, moduleIds: [0, 2] }); await flush()
  assert.equal(h.calls.filter(item => item[0] === 'list').at(-1)[1].project_product, 0)
  assert.equal(h.item('tasks_id').value, ''); assert.deepEqual(h.item('tasks__task_group_id').value, [])
  assert.ok(h.searchErrors.tasks); assert.equal(h.searchLoading.tasks, false)
  first.resolve(response([{ id: 99, name: 'Old' }])); await flush(); assert.deepEqual(h.item('tasks_id').optionItems, [])
  await h.loadTaskOptions(); assert.equal(h.searchErrors.tasks, ''); assert.deepEqual(h.item('tasks_id').optionItems, [{ value: 0, label: 'Current' }])
})

test('有限模型拒绝坏响应，保留0/长ID、全路径、缺失通过率并过滤不合法选项', t => {
  const h = setup(); t.after(h.close); const m = h.load('report-list.ts')
  for (const value of [{ code: 403 }, response(null), response({}), response([], { totalSize: false })]) assert.throws(() => m.parseReportList(value))
  const parsed = m.parseReportList(response([{ id: 0, project_product: { id: 0, project: { id: 0, name: 'Project' } }, module: { full_path: 'One/Two' }, status: 0 }, { id: 0 }, { id: '90071992547409931234' }, { id: false }], { totalSize: 2 }))
  assert.deepEqual(parsed.rows.map(row => row.id), [0, '90071992547409931234'])
  assert.equal(parsed.rows[0].project_product.id, 0); assert.equal(parsed.rows[0].module.full_path, 'One/Two')
  assert.equal(parsed.rows[0].status, 0); assert.equal(parsed.rows[0].api_concurrency_limit, null)
  const snapshot = m.parseReportRow({ id: 1, execution_scope: 'module', execution_scenes: ['regression', ' data_validation ', 0, '', false, null] })
  assert.equal(snapshot.execution_scope, 'module')
  assert.deepEqual(snapshot.execution_scenes, ['regression', 'data_validation', 0])
  const overview = m.parseReportOverview(response({ status_distribution: [{ status: 1, value: 3 }, { status: 0, value: -9 }], trend: [{ label: 'Example', pass_rate: false }] }))
  assert.equal(overview.counts.success, 3); assert.equal(overview.counts.fail, 0); assert.equal(overview.trend[0].pass_rate, null)
  assert.deepEqual(m.parseReportOptions(response([{ key: 0, title: 'Zero' }, { id: false }, { key: '90071992547409931234', title: 'Long' }])), [{ value: 0, label: 'Zero' }, { value: '90071992547409931234', label: 'Long' }])
})

const completeRow = (h, overrides = {}) => h.load('report-list.ts').parseReportRow({ id: 0, status: 1, test_env: 0, execution_summary: { total: 2, fail: 1 }, ...overrides })
function retryView(h) {
  const calls = []
  h.retryModalRef.value = { show: value => calls.push(['show', value]), close: () => calls.push(['close']), setConfirmLoading: value => calls.push(['loading', value]) }
  return calls
}

test('重试窗口固定报告快照；配置读取防重复，取消后旧配置不会重新打开窗口', async t => {
  const options = deferred(); let attempts = 0
  const h = setup({ executionOptions: () => ++attempts === 1 ? options.promise : Promise.resolve(response({ api_platform_limit: 4 })) }); t.after(h.close)
  const view = retryView(h); h.mount(); await flush()
  const record = completeRow(h), first = h.onRetry(record)
  record.id = 99; await h.onRetry(completeRow(h, { id: 2 })); assert.equal(attempts, 1)
  h.onCancelRetryModal(); options.resolve(response({ api_platform_limit: 4 })); await first
  assert.equal(view.filter(item => item[0] === 'show').length, 0); assert.equal(h.retryState.loading, false)
  await h.onRetry(completeRow(h, { id: '90071992547409931234' }))
  assert.equal(h.retryState.record.id, '90071992547409931234'); assert.equal(view.at(-1)[1].testEnv, 0)
})

test('全量重试失败恢复、重复提交只发一次，环境和并发提交为固定快照', async t => {
  const pending = deferred(); let attempts = 0
  const h = setup({ retry: () => ++attempts === 1 ? Promise.resolve({ code: 403 }) : pending.promise }); t.after(h.close)
  const view = retryView(h); h.mount(); await flush(); await h.onRetry(completeRow(h))
  const config = { executionName: 'Example', testEnv: 0, apiConcurrencyLimit: 2 }
  assert.equal(await h.onConfirmRetryModal(config), false); assert.equal(h.retryState.record.id, 0); assert.equal(h.retryState.loading, false)
  const next = h.onConfirmRetryModal(config); config.testEnv = 3
  assert.equal(await h.onConfirmRetryModal(config), false)
  assert.deepEqual(h.calls.filter(item => item[0] === 'retry').at(-1), ['retry', 0, 0, 2, true])
  pending.resolve(response({})); assert.equal(await next, true); assert.equal(h.retryState.record, null)
  assert.ok(view.some(item => item[0] === 'close')); assert.equal(h.retryState.loading, false)
})

test('只重试失败与全量互斥，排除运行中/测评报告，关闭后旧成功不会影响新窗口', async t => {
  const pending = deferred(), h = setup({ retryFailed: () => pending.promise }); t.after(h.close); retryView(h); h.mount(); await flush()
  assert.equal(await h.onRetryFailed(completeRow(h, { status: 2 })), false)
  assert.equal(await h.onRetryFailed(completeRow(h, { automation_types: [4] })), false)
  await h.onRetry(completeRow(h)); const write = h.onRetryFailed(h.retryState.record)
  assert.equal(await h.onRetryFailed(h.retryState.record), false); assert.equal(h.retryState.failedId, 0)
  assert.equal(await h.onConfirmRetryModal({ executionName: 'Example', testEnv: 0, apiConcurrencyLimit: null }), false)
  h.onCancelRetryModal(); const count = h.messages.length
  pending.resolve(response({ retry_count: 1 })); assert.equal(await write, false)
  assert.equal(h.messages.length, count); assert.equal(h.retryState.failedId, null)
})

test('停止确认固定目标、防重复；失败能重试；切换上下文关闭确认且不发送旧目标', async t => {
  const pending = deferred(); let attempts = 0
  const h = setup({ stop: () => ++attempts === 1 ? Promise.resolve({ code: 403 }) : pending.promise }); t.after(h.close); h.mount(); await flush()
  const record = completeRow(h, { status: 2 }); h.onStop(record); h.onStop(record)
  assert.equal(h.dialogs.length, 1); const confirm = h.dialogs[0].config.onBeforeOk
  assert.equal(await confirm(), false); assert.equal(h.stopLoadingId.value, null)
  record.id = 9; const write = confirm(); assert.equal(await confirm(), false)
  assert.equal(h.calls.filter(item => item[0] === 'stop').at(-1)[1], 0)
  pending.resolve(response({})); assert.equal(await write, true)
  h.onStop(completeRow(h, { id: 7, status: 3 })); const old = h.dialogs.at(-1)
  h.user.selected_environment = 2; assert.equal(old.closed, true)
  assert.equal(await old.config.onBeforeOk(), false); assert.equal(attempts, 2)
})

test('通知组关闭/换目标不串回显，0产品和0通知组有效，发送失败可在原确认中重试', async t => {
  const old = deferred(); let options = 0, sends = 0
  const h = setup({ noticeOptions: () => ++options === 1 ? old.promise : Promise.resolve(response([{ value: 0, label: 'Zero' }])),
    notice: () => Promise.resolve(++sends === 1 ? { code: 403 } : response({})),
  }); t.after(h.close); h.mount(); await flush()
  h.onSendNotice(completeRow(h, { project_product: { id: 0, project: { id: 0 } } })); await flush()
  assert.deepEqual(h.noticeForm.project_product, [0, 0]); assert.equal(h.calls.filter(item => item[0] === 'noticeOptions').at(-1)[1], 0)
  h.onCancelNoticeModal(); h.onSendNotice(completeRow(h, { id: 2, project_product: { id: 2 } })); await flush()
  old.resolve(response([{ value: 99, label: 'Old' }])); await flush()
  assert.deepEqual(h.noticeState.options, [{ value: 0, label: 'Zero' }]); h.noticeForm.notice_group = 0
  let settled = false; const submitted = h.onConfirmNoticeModal().then(value => { settled = true; return value })
  const confirm = h.dialogs.at(-1).config.onBeforeOk
  assert.equal(await confirm(), false); assert.equal(h.noticeState.visible, true); assert.equal(h.noticeState.sending, false); assert.equal(settled, false)
  h.noticeForm.notice_group = 1
  assert.equal(await confirm(), true); assert.equal(await submitted, true)
  assert.deepEqual(h.calls.filter(item => item[0] === 'notice').map(item => item[1]), [{ id: 2, notice_group: 0 }, { id: 2, notice_group: 0 }])
})

test('通知写入保留物理锁，后台失效后旧成功不提示/关闭新上下文，确认取消可再次打开', async t => {
  const pending = deferred(), h = setup({ notice: () => pending.promise }); t.after(h.close); h.mount(); await flush()
  const record = completeRow(h, { tasks: { id: 0, name: 'Example task', notice_group: 0 } })
  h.onSendNotice(record); const dialog = h.dialogs.at(-1); dialog.config.onCancel()
  h.onSendNotice(record); const confirmation = h.dialogs.at(-1), send = confirmation.config.onBeforeOk()
  await h.visibility('hidden'); assert.equal(confirmation.closed, true); assert.equal(h.noticeState.sending, true)
  await h.visibility('visible'); h.onSendNotice(completeRow(h, { id: 2 })); assert.equal(h.noticeState.visible, false)
  const count = h.messages.length; pending.resolve(response({})); assert.equal(await send, false)
  assert.equal(h.messages.length, count); assert.equal(h.noticeState.sending, false)
  assert.equal(h.calls.filter(item => item[0] === 'notice').length, 1)
})

test('API参数边界不丢0产品、不舍入大ID；报告重试和通知保持原路由与字段', t => {
  const h = setup(); t.after(h.close)
  const tasks = h.load('../../api/system/tasks.ts'), notice = h.load('../../api/system/notice_group.ts'), retry = h.load('../../api/system/test_sute_details.ts')
  assert.deepEqual(tasks.getScheduledTaskGroupOptions(0), { project_product_id: 0 })
  assert.deepEqual(tasks.getScheduledTaskGroupOptions('90071992547409931234'), { project_product_id: '90071992547409931234' })
  assert.deepEqual(notice.getSystemNoticeName('90071992547409931234'), { project_product_id: '90071992547409931234' })
  assert.deepEqual(retry.getSystemTestSuiteDetailsAllRetry('90071992547409931234', 0, 2), { test_suite_id: '90071992547409931234', test_env: 0, api_concurrency_limit: 2, confirm_infrastructure_retry: false })
})
test('任务组导出使用路由首个合法ID，0保留；无效目标不打开无范围窗口', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush()
  h.route.query.group_execution_id = ['0', '2']; assert.equal(h.groupExportId.value, '0')
  h.openOfflineExport('group', h.groupExportId.value); assert.equal(h.offlineExport.id, '0'); assert.equal(h.offlineExport.visible, true)
  h.route.fullPath = '/report/index?group_execution_id=invalid'; h.route.query.group_execution_id = 'invalid'
  assert.equal(h.groupExportId.value, null); assert.equal(h.offlineExport.visible, false)
  h.openOfflineExport('group', {}); assert.equal(h.offlineExport.visible, false)
})
