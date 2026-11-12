import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { deferred, flush as microtasks, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/report/details')
const response = data => ({ code: 200, data })
const summary = patch => response({ count: 10, api_count: 10, stay_begin_count: 10, ...patch })
async function flush() { await microtasks(); await new Promise(resolve => setImmediate(resolve)) }
function setup(overrides = {}, cachedRecord = null) {
  const route = vue.reactive({ path: '/report/details', fullPath: '/report/details?id=1', query: { id: '1' } })
  const user = vue.reactive({ userId: null, roleId: null, token: '', selected_environment: 0 })
  const life = { mount: [], unmount: [], activate: [], deactivate: [] }, calls = [], listeners = new Set()
  const originalDocument = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  const add = doc.addEventListener.bind(doc), remove = doc.removeEventListener.bind(doc)
  doc.addEventListener = (type, fn) => { listeners.add(fn); add(type, fn) }
  doc.removeEventListener = (type, fn) => { listeners.delete(fn); remove(type, fn) }
  globalThis.document = doc
  const polling = { enabled: false, refresh: null, pause: null }, store = { record: cachedRecord, writes: [] }
  const defaults = {
    getSystemTestSuiteShare: id => response({ id, execution_name: 'Example', test_env: 0, api_concurrency_limit: 0, is_notice: 0 }),
    getSystemTestSuiteDetailsSummaryShare: () => summary(),
    getSystemTestSuiteDetailsFailureReasonsShare: () => response({ items: [], category_count: 0, failure_count: 0 }),
    getSystemTestSuiteDetailsShare: () => ({ ...response([{ id: 1 }]), totalSize: 10 }),
  }
  const api = Object.fromEntries(Object.entries({ ...defaults, ...overrides }).map(([name, fn]) => [name, (...args) => {
    calls.push([name, ...args]); return Promise.resolve().then(() => fn(...args))
  }]))
  const h = harness('index', 'reportId,reportInfo,summary,failureReasonSummary,cases,activeType,caseStatus,caseKeyword,lastSearchedCaseKeyword,excludedFilter,pagination,reportInfoLoading,reportInfoError,summaryLoading,summaryError,failureReasonLoading,failureReasonError,caseLoading,caseError,loadReportInfo,loadSummary,loadFailureReasons,loadCases,refreshLoadedCases,reloadCases,initializeReport,searchCases,searchCasesOnBlur,onCasePageChange,onCasePageSizeChange,showDetails,currentTypeLabel,executionResultDrawer,apiHistoryDrawer,canRetry,showCaseHistory,openCaseDetail,caseDetailDrawer', {
    base, api,
    modules: {
      vue: { ...vue, onMounted: fn => life.mount.push(fn), onBeforeUnmount: fn => life.unmount.push(fn), onUnmounted: fn => life.unmount.push(fn), onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn) },
      'vue-router': { useRoute: () => route },
      '@/store/modules/user': { useUserStoreContext: () => user },
      '@/store/page-data': { usePageData: () => ({ ...store, setRecord: value => store.writes.push(value) }) },
      '@/store/modules/get-enum': { useEnum: () => ({ task_status: [{ key: 0, title: '失败' }], environment_type: [], test_suite_notice: [] }) },
      '@/hooks/use-page-polling': { isPendingExecution: record => [2, 3].includes(Number(record?.status)), usePagePolling(refresh, pause) {
        polling.refresh = refresh; polling.pause = pause
        return { start() { polling.enabled = true }, stop() { polling.enabled = false } }
      } },
    },
  })
  return { ...h, calls, route, user, life, doc, polling, store, listeners,
    data: h.load('report-overview.ts'), sessions: h.load('report-read-session.ts'),
    mount() { life.mount.forEach(fn => fn()); life.activate.forEach(fn => fn()) },
    close() { life.unmount.forEach(fn => fn()); h.close(); globalThis.document = originalDocument } }
}

test('报告元信息失败不阻断摘要、失败原因和 API 列表，公开入口不要求登录', async t => {
  const h = setup({ getSystemTestSuiteShare: () => { throw new Error('failed') } }); t.after(h.close)
  h.mount(); await flush()
  assert.ok(h.reportInfoError.value); assert.equal(h.reportInfo.value, null)
  assert.equal(h.summary.value.count, 10); assert.equal(h.activeType.value, '1')
  assert.equal(h.failureReasonError.value, ''); assert.deepEqual(h.cases.value, [{ id: 1 }])
  assert.equal(h.reportInfoLoading.value, false); assert.equal(h.caseLoading.value, false)
  assert.equal(h.polling.enabled, true)
  assert.equal(h.calls.filter(c => c[0] === 'getSystemTestSuiteDetailsShare').length, 1)
})

test('缓存记录不跳过真实读取，也不把详情投影写回跨页面 store', async t => {
  const h = setup({}, { id: 1, execution_name: 'old' }); t.after(h.close)
  await h.loadReportInfo()
  assert.equal(h.reportInfo.value.execution_name, 'Example')
  assert.equal(h.reportInfo.value.test_env, 0); assert.equal(h.reportInfo.value.api_concurrency_limit, 0)
  assert.deepEqual(h.store.writes, [])
})

test('摘要和失败原因分区 loading 不互相等待', async t => {
  const pending = deferred(), h = setup({ getSystemTestSuiteDetailsFailureReasonsShare: () => pending.promise }); t.after(h.close)
  const failures = h.loadFailureReasons(); await h.loadSummary(); await flush()
  assert.equal(h.summaryLoading.value, false); assert.equal(h.failureReasonLoading.value, true)
  pending.resolve(response({ items: [], category_count: 0, failure_count: 0 })); await failures
  assert.equal(h.failureReasonLoading.value, false)
})

test('报告同路由 ID A-B-A 只展示最后一份元信息和统计', async t => {
  const reads = [deferred(), deferred(), deferred()]; let index = 0
  const h = setup({ getSystemTestSuiteShare: () => reads[index++].promise }); t.after(h.close)
  const old = h.loadReportInfo(); await flush()
  h.route.query.id = '2'; h.route.fullPath = '/report/details?id=2'
  const b = h.loadReportInfo(); await flush()
  h.route.query.id = '1'; h.route.fullPath = '/report/details?id=1'
  const last = h.loadReportInfo(); await flush()
  reads[0].resolve(response({ id: 1, execution_name: 'old' })); await old
  assert.equal(h.reportInfo.value, null); assert.equal(h.reportInfoLoading.value, true)
  reads[1].reject(new Error('old')); await b
  assert.equal(h.reportInfoError.value, '')
  reads[2].resolve(response({ id: 1, execution_name: 'latest' })); await last
  assert.equal(h.reportInfo.value.execution_name, 'latest')
})

test('筛选/分页不会因旧 loading 丢请求，旧响应不覆盖也不回退当前页', async t => {
  const reads = [deferred(), deferred(), deferred()]; let index = 0
  const h = setup({ getSystemTestSuiteDetailsShare: () => reads[index++].promise }); t.after(h.close)
  const old = h.loadCases(); await flush()
  h.pagination.page = 2
  const page2 = h.loadCases(); await flush()
  h.caseStatus.value = 0
  const filtered = h.loadCases(true); await flush()
  assert.equal(h.calls.length, 3)
  assert.equal(h.calls[2][1].status, 0); assert.equal(h.calls[2][1].page, 1)
  reads[0].resolve({ ...response([{ id: 99 }]), totalSize: 99 }); await old
  assert.equal(h.caseLoading.value, true); assert.deepEqual(h.cases.value, [])
  reads[1].reject(new Error('old')); await page2
  assert.equal(h.pagination.page, 1); assert.equal(h.caseError.value, '')
  reads[2].resolve({ ...response([{ id: 3 }]), totalSize: 0 }); await filtered
  assert.deepEqual(h.cases.value, [{ id: 3 }]); assert.equal(h.pagination.total, 0)
})

test('失败的相同关键词可以再次搜索；请求保留状态 0 和清理空关键字', async t => {
  let count = 0
  const h = setup({ getSystemTestSuiteDetailsShare: () => { if (!count++) throw new Error('failed'); return { ...response([]), totalSize: 0 } } }); t.after(h.close)
  h.caseStatus.value = 0; h.caseKeyword.value = ' example '
  h.searchCases(); await flush(); assert.ok(h.caseError.value)
  h.searchCases(); await flush()
  assert.equal(h.calls.length, 2); assert.equal(h.calls[1][1].case_keyword, 'example'); assert.equal(h.calls[1][1].status, 0)
  assert.equal(h.caseError.value, '')
  h.caseKeyword.value = ' '; h.searchCases(); await flush()
  assert.equal('case_keyword' in h.calls[2][1], false)
})

test('待开始/进行中静默轮询同时更新摘要、报告状态和当前分页，失败继续启用', async t => {
  let failed = false
  const h = setup({ getSystemTestSuiteDetailsSummaryShare: () => { if (failed) throw new Error('poll failed'); return summary() } }); t.after(h.close)
  h.mount(); await flush(); h.pagination.page = 2
  const start = h.calls.length
  await h.polling.refresh({ isCurrent: () => true })
  assert.equal(h.summaryLoading.value, false); assert.equal(h.caseLoading.value, false); assert.equal(h.reportInfoLoading.value, false)
  const reads = h.calls.slice(start)
  assert.ok(reads.every(call => call.at(-1) === true))
  assert.equal(reads.find(call => call[0] === 'getSystemTestSuiteDetailsShare')[1].page, 2)
  failed = true
  await assert.rejects(h.polling.refresh({ isCurrent: () => true }))
  assert.equal(h.polling.enabled, true); assert.equal(h.summaryError.value, ''); assert.equal(h.summary.value.count, 10)
})

test('执行中每轮更新失败原因 Top，失败保留历史数据并在最终刷新成功后停止', async t => {
  let message = '首次失败', failed = false, finished = false
  const h = setup({
    getSystemTestSuiteDetailsSummaryShare: () => summary({ stay_begin_count: finished ? 0 : 10 }),
    getSystemTestSuiteDetailsFailureReasonsShare: () => {
      if (failed) throw new Error('failure reasons unavailable')
      return response({ category_count: 1, failure_count: 1, items: [{ message, count: 1, percent: 100 }] })
    },
  }); t.after(h.close)
  h.mount(); await flush()
  assert.equal(h.failureReasonSummary.value.items[0].message, '首次失败')
  message = '最新失败'
  await h.polling.refresh({ isCurrent: () => true })
  assert.equal(h.failureReasonSummary.value.items[0].message, '最新失败')
  assert.equal(h.failureReasonLoading.value, false)
  assert.equal(h.polling.enabled, true)
  failed = true; finished = true
  await assert.rejects(h.polling.refresh({ isCurrent: () => true }))
  assert.equal(h.failureReasonSummary.value.items[0].message, '最新失败')
  assert.equal(h.failureReasonError.value, '')
  assert.equal(h.polling.enabled, true)
  failed = false; message = '最终失败'
  await h.polling.refresh({ isCurrent: () => true })
  assert.equal(h.failureReasonSummary.value.items[0].message, '最终失败')
  assert.equal(h.failureReasonLoading.value, false)
  assert.equal(h.polling.enabled, false)
})

test('首次摘要失败保留重试入口并启用轮询，恢复后加载真实类型', async t => {
  let failed = true
  const h = setup({ getSystemTestSuiteDetailsSummaryShare: () => { if (failed) throw new Error('failed'); return summary() } }); t.after(h.close)
  h.mount(); await flush(); assert.ok(h.summaryError.value); assert.equal(h.polling.enabled, true)
  failed = false
  await h.polling.refresh({ isCurrent: () => true }); await flush()
  assert.equal(h.summaryError.value, ''); assert.equal(h.activeType.value, '1')
})

test('轮询自动切换类型时，后台列表失败不会成为游离的未处理拒绝', async t => {
  const metadata = deferred()
  const h = setup({ getSystemTestSuiteShare: () => metadata.promise, getSystemTestSuiteDetailsShare: () => { throw new Error('list failed') } }); t.after(h.close)
  const pending = h.polling.refresh({ isCurrent: () => true })
  const rejected = assert.rejects(pending)
  await flush()
  metadata.resolve(response({ id: 1 }))
  await rejected
  assert.equal(h.caseLoading.value, false); assert.equal(h.caseError.value, '')
})

test('结束统计为 0 时只在最后失败原因读取成功后停止轮询', async t => {
  let finished = false
  const h = setup({ getSystemTestSuiteDetailsSummaryShare: () => summary(finished ? { stay_begin_count: 0 } : {}) }); t.after(h.close)
  h.mount(); await flush(); finished = true
  await h.polling.refresh({ isCurrent: () => true })
  assert.equal(h.polling.enabled, false)
})

test('尚未生成明细的待开始/进行中报告仍持续轮询，报告结束后停止', async t => {
  let status = 2
  const h = setup({ getSystemTestSuiteShare: id => response({ id, status }), getSystemTestSuiteDetailsSummaryShare: () => response({ count: 0 }) }); t.after(h.close)
  h.mount(); await flush(); assert.equal(h.polling.enabled, true)
  status = 3
  await h.polling.refresh({ isCurrent: () => true }); assert.equal(h.polling.enabled, true)
  status = 1
  await h.polling.refresh({ isCurrent: () => true }); assert.equal(h.polling.enabled, false)
})

test('轮询中的身份 A-B-A 不继续旧流程，也不停止新上下文轮询', async t => {
  const read = deferred(), h = setup({ getSystemTestSuiteDetailsSummaryShare: () => read.promise }); t.after(h.close)
  h.polling.enabled = true
  const pending = h.polling.refresh({ isCurrent: () => true }); await flush()
  h.user.roleId = 2; h.user.roleId = null
  h.polling.enabled = true
  read.resolve(summary({ stay_begin_count: 0 })); await pending
  assert.equal(h.summary.value.count, 0)
  assert.equal(h.calls.filter(call => call[0] === 'getSystemTestSuiteDetailsShare').length, 0)
  assert.equal(h.polling.enabled, true)
})

for (const key of ['userId', 'roleId', 'token', 'selected_environment']) {
  test(`${key} 切换同步清空旧记录，迟到失败不能改变当前界面`, async t => {
    const read = deferred(), h = setup({ getSystemTestSuiteShare: () => read.promise }); t.after(h.close)
    const pending = h.loadReportInfo(); await flush()
    h.reportInfo.value = { id: '1' }; h.user[key] = key === 'token' ? 'fixture-b' : 2
    assert.equal(h.reportInfo.value, null); assert.equal(h.reportInfoLoading.value, false)
    read.reject(new Error('old')); await pending
    assert.equal(h.reportInfoError.value, '')
  })
}

test('后台与 KeepAlive 旧读取失效，返回恢复，离开路由不误读别页 ID', async t => {
  const old = deferred(); let count = 0
  const h = setup({ getSystemTestSuiteShare: id => count++ ? response({ id, execution_name: 'new' }) : old.promise }); t.after(h.close)
  h.mount(); await flush()
  h.doc.visibilityState = 'hidden'; h.doc.dispatchEvent(new Event('visibilitychange'))
  old.resolve(response({ id: 1, execution_name: 'old' })); await flush()
  assert.equal(h.reportInfo.value, null)
  h.doc.visibilityState = 'visible'; h.doc.dispatchEvent(new Event('visibilitychange')); await flush()
  assert.equal(h.reportInfo.value.execution_name, 'new')
  h.life.deactivate.forEach(fn => fn()); assert.equal(h.reportInfo.value, null)
  h.life.activate.forEach(fn => fn()); await flush(); assert.equal(h.reportInfo.value.execution_name, 'new')
  const calls = h.calls.length
  h.route.path = '/config/product/index'; h.route.query.id = '99'; h.route.fullPath = '/config/product/index?id=99'
  await flush(); assert.equal(h.reportId.value, '1'); assert.equal(h.calls.length, calls)
  h.life.unmount.forEach(fn => fn()); assert.equal(h.listeners.size, 0)
})


test('结果窗口由主页面传有限目标并在报告上下文失效时关闭，API 仍走公共历史', async t => {
  const h = setup(); t.after(h.close)
  const targets = []; let closed = 0
  h.executionResultDrawer.value = { open: async target => targets.push(target), close: () => closed++ }
  await h.showDetails({ test_suite_detail_id: 0, id: 'fixture', parameter_id: 0, case_type: 2, name: 'Example', unrelated: 'discard' })
  assert.equal(targets[0].detailId, '0'); assert.equal(targets[0].source.parameter_id, '0')
  assert.equal(targets[0].source.unrelated, undefined)
  await h.showDetails({ test_suite_detail_id: 1, case_type: 1 })
  assert.equal(targets.length, 1); assert.equal(h.apiHistoryDrawer.visible, true)
  h.user.roleId = 2
  assert.equal(closed, 1); assert.equal(h.apiHistoryDrawer.visible, false)
})

test('操作展示只受保留摘要/评测业务条件影响，Case ID0 的历史和详情可打开', t => {
  const h = setup(); t.after(h.close)
  assert.equal(h.user.token, ''); assert.equal(h.canRetry.value, true)
  h.reportInfo.value = { id: '1', retained_summary: true }; assert.equal(h.canRetry.value, false)
  h.reportInfo.value = null; h.summary.value.evaluation_count = 1; assert.equal(h.canRetry.value, false)
  h.summary.value.evaluation_count = 0
  h.showCaseHistory({ __caseId: 0, __caseName: 'Example' })
  assert.equal(h.apiHistoryDrawer.caseId, '0'); assert.equal(h.apiHistoryDrawer.visible, true)
  h.openCaseDetail({ __caseId: 0, case_type: 1 })
  assert.equal(h.caseDetailDrawer.caseId, '0'); assert.equal(h.caseDetailDrawer.visible, true)
})

test('纯响应转换保留 totalSize 0、原始类型回退、0 值；拒绝错误码/错报告和异常统计', t => {
  const h = setup(); t.after(h.close)
  assert.equal(h.data.parseReportSummary(summary({ raw_api_count: 0 })).raw_api_count, 0)
  assert.equal(h.data.parseReportSummary(summary()).raw_api_count, 10)
  assert.equal(h.data.parseReportCasePage({ ...response([]), totalSize: 0, total: 20 }).total, 0)
  assert.throws(() => h.data.parseReportOverview(response({ id: 2 }), '1'))
  assert.throws(() => h.data.parseReportSummary({ code: 403, data: summary().data }))
  assert.throws(() => h.data.parseReportSummary(summary({ count: '10' })))
  assert.throws(() => h.data.parseReportFailureReasons(response({ items: [{ message: 'bad', count: 1, percent: 101 }] })))
})

test('读取会话提升静默请求为手动反馈，失效 polling 上下文不被重试合并', async t => {
  const h = setup(); t.after(h.close)
  const session = h.sessions.createReportReadSession(() => true), read = deferred()
  const loading = vue.ref(false), error = vue.ref(''), values = []
  let current = true, count = 0
  const options = () => ({ key: 'a', silent: true, loading, error, message: 'failed', isCurrent: () => current,
    read: () => { count++; return read.promise }, apply: value => values.push(value) })
  const first = session.run(options()); await flush()
  const promoted = session.run({ ...options(), silent: false }); assert.equal(first, promoted); assert.equal(loading.value, true)
  read.reject(new Error('failed')); await first; assert.equal(error.value, 'failed'); assert.equal(loading.value, false)
  const stale = deferred(), fresh = deferred(); current = true
  const old = session.run({ ...options(), read: () => stale.promise }); await flush()
  current = false
  const last = session.run({ ...options(), silent: false, isCurrent: () => true, read: () => fresh.promise }); await flush()
  stale.resolve('old'); await old; assert.equal(loading.value, true)
  fresh.resolve('new'); await last
  assert.deepEqual(values, ['new']); assert.equal(count, 1)
})
