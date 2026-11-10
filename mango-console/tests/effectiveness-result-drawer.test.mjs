import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, deferred, flush as microtasks } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/components/reports'), response = data => ({ code: 200, data })
async function flush() { await microtasks(); await new Promise(resolve => setImmediate(resolve)); await microtasks() }
function setup(settings = {}) {
  const life = { mount: [], unmount: [], activate: [], deactivate: [] }, calls = []
  const route = vue.reactive({ path: '/report/effectiveness/index', fullPath: '/report/effectiveness/index' })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 0 })
  const originalDocument = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }), listeners = new Set()
  const add = doc.addEventListener.bind(doc), remove = doc.removeEventListener.bind(doc)
  doc.addEventListener = (event, callback) => { listeners.add(callback); add(event, callback) }
  doc.removeEventListener = (event, callback) => { listeners.delete(callback); remove(event, callback) }
  globalThis.document = doc
  const h = harness('TestReportResultDrawer', 'localVisible,loadDetail,loadHistory,changeResult,resultData,resultOptions,selectedResultId,detailLoading,historyLoading,loadError,historyError,historyItems,drawerTitle,hasDetail', {
    base, filename: path.join(base, 'TestReportResultDrawer.vue'), props: { visible: true, testSuiteDetailId: 0, caseType: 1, caseId: 0, ...settings.props },
    api: {
      getSystemTestSuiteDetailsResultShare: (...args) => { calls.push(['detail', ...args]); return settings.detail ? settings.detail(...args) : response({ id: args[0], name: 'ready' }) },
      getSystemTestSuiteDetailsResultOptionsShare: (...args) => { calls.push(['history', ...args]); return settings.history ? settings.history(...args) : response([{ id: 0, test_suite_detail_id: args[0], is_latest: true }]) },
    },
    modules: {
      vue: { ...vue, onMounted: fn => life.mount.push(fn), onBeforeUnmount: fn => life.unmount.push(fn), onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn) },
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { useUserStoreContext: () => user }, '@arco-design/web-vue/es/icon': {},
    },
  })
  return { ...h, life, calls, user, route, doc, listeners,
    mount() { life.mount.forEach(fn => fn()); life.activate.forEach(fn => fn()) },
    close() { life.unmount.forEach(fn => fn()); h.close(); globalThis.document = originalDocument },
  }
}

test('初始可见即加载，ID0有效；历史与详情独立反馈，重复读取合并', async t => {
  const history = deferred(), detail = deferred(), h = setup({ history: () => history.promise, detail: () => detail.promise }); t.after(h.close)
  h.mount(); await flush(); assert.equal(h.calls.length, 2); assert.match(h.drawerTitle.value, /ID 0/)
  const first = h.loadDetail(); assert.equal(first, h.loadDetail()); assert.equal(h.loadHistory(), h.loadHistory())
  detail.resolve(response({ id: 0, name: 'ready' })); await first
  assert.equal(h.detailLoading.value, false); assert.equal(h.historyLoading.value, true); assert.equal(h.resultData.value.name, 'ready')
  history.resolve(response([{ id: 0, test_suite_detail_id: 0, is_latest: true }])); await flush(); assert.equal(h.selectedResultId.value, 0)
})

test('历史失败不丢弃成功详情，独立重试；详情失败不清空历史', async t => {
  let failHistory = true, failDetail = false
  const h = setup({ history: () => { if (failHistory) throw Error('network'); return response([{ id: 0 }]) }, detail: () => failDetail ? { code: 403 } : response({ id: 0, name: 'ready' }) }); t.after(h.close)
  h.mount(); await flush(); assert.ok(h.historyError.value); assert.equal(h.resultData.value.name, 'ready'); assert.equal(h.loadError.value, '')
  failHistory = false; await h.loadHistory(); assert.equal(h.historyError.value, ''); assert.equal(h.historyItems.value.length, 1)
  failDetail = true; await h.loadDetail(); assert.ok(h.loadError.value); assert.equal(h.historyItems.value.length, 1)
  failDetail = false; await h.loadDetail(); assert.equal(h.loadError.value, ''); assert.equal(h.resultData.value.name, 'ready')
})

test('关闭与换目标A-B-A使迟到详情、历史和finally失效，重开正常', async t => {
  const old = deferred(); let count = 0
  const h = setup({ detail: id => ++count === 1 ? old.promise : response({ id, name: `read-${count}` }) }); t.after(h.close)
  h.mount(); await flush(); h.localVisible.value = false; assert.equal(h.resultData.value, null)
  old.resolve(response({ id: 0, name: 'old' })); await flush(); assert.equal(h.resultData.value, null)
  h.props.visible = false; h.props.visible = true; await flush(); assert.equal(h.resultData.value.name, 'read-2')
  h.props.testSuiteDetailId = 1; h.props.testSuiteDetailId = 0; await flush(); assert.equal(h.resultData.value.name, 'read-3')
  assert.equal(h.detailLoading.value, false)
})

for (const field of ['userId', 'roleId', 'token', 'selected_environment', 'route']) {
  test(`${field}切换关闭窗口清除证据，不凭登录状态阻止请求`, async t => {
    const old = deferred(), h = setup({ detail: () => old.promise }); t.after(h.close); h.mount(); await flush()
    if (field === 'route') { h.route.fullPath = '/report/index'; h.route.path = '/report/index' }
    else { const before = h.user[field]; h.user[field] = field === 'token' ? '' : 2; h.user[field] = before }
    old.resolve(response({ id: 0, name: 'old' })); await flush()
    assert.equal(h.resultData.value, null); assert.equal(h.resultOptions.value.length, 0); assert.ok(h.events.some(event => event[0] === 'update:visible' && event[1] === false))
    const count = h.calls.length; await h.loadDetail(); assert.equal(h.calls.length, count)
  })
}

test('后台和KeepAlive失效迟到请求，恢复当前选择，卸载移除监听', async t => {
  const old = deferred(); let count = 0
  const h = setup({ detail: id => ++count === 1 ? old.promise : response({ id, name: `read-${count}` }) }); t.after(h.close)
  h.mount(); await flush(); h.doc.visibilityState = 'hidden'; h.doc.dispatchEvent(new Event('visibilitychange'))
  old.resolve(response({ id: 0, name: 'old' })); await flush(); assert.equal(h.resultData.value, null); assert.equal(h.detailLoading.value, false)
  await h.loadDetail(); assert.equal(count, 1)
  h.doc.visibilityState = 'visible'; h.doc.dispatchEvent(new Event('visibilitychange')); await flush(); assert.equal(h.resultData.value.name, 'read-2')
  h.life.deactivate.forEach(fn => fn()); await h.loadDetail(); assert.equal(count, 2); assert.equal(h.resultData.value, null)
  h.life.activate.forEach(fn => fn()); await flush(); assert.equal(h.resultData.value.name, 'read-3')
  h.life.unmount.forEach(fn => fn()); await h.loadHistory(); assert.equal(h.listeners.size, 0)
})

test('选择仅接受已加载历史，快速0-1-0仅最后响应生效，初始匹配当前明细最新项', async t => {
  const reads = []
  const h = setup({ history: () => response([{ id: 1, test_suite_detail_id: 9, is_latest: true }, { id: 0, test_suite_detail_id: 0, is_latest: true }]),
    detail: id => { if (!reads.length) { reads.push(null); return response({ id, name: 'initial' }) }; const read = deferred(); reads.push(read); return read.promise } }); t.after(h.close)
  h.mount(); await flush(); assert.equal(h.selectedResultId.value, 0)
  for (const id of ['', -1, 2, Number.MAX_SAFE_INTEGER + 1]) await h.changeResult(id)
  assert.equal(reads.length, 1)
  const first = h.changeResult(0); await flush(); const second = h.changeResult(1); await flush(); const last = h.changeResult(0); await flush()
  reads[1].resolve(response({ id: 0, name: 'old' })); reads[2].reject(Error('stale')); await Promise.all([first, second]); assert.equal(h.detailLoading.value, true)
  reads[3].resolve(response({ id: 0, name: 'latest' })); await last; assert.equal(h.resultData.value.name, 'latest'); assert.equal(h.loadError.value, '')
})

test('有限历史和只读结果边界，坏格式/错明细拒绝，保留UI false/空缓存与长ID', t => {
  const h = setup(); t.after(h.close); const model = h.load('test-report-result.ts')
  for (const data of [null, {}, [null], [{ id: false }], [{ id: 1 }, { id: '1' }]]) assert.throws(() => model.failureResultOptions(response(data)))
  assert.equal(model.failureResultTarget({ testSuiteDetailId: 0, caseType: false }), null)
  const target = model.failureResultTarget({ testSuiteDetailId: '9223372036854775807', caseType: '0', caseId: 0 })
  const record = model.failureResultRecord(response({ id: target.detailId, cache_data: { stale: true }, children: [null, { id: 0, name: 'UI', cache_data: false, data_factory_cache_data: [], status: 0 }] }), target)
  assert.equal(record.test_suite_detail_id, target.detailId); assert.equal(record.cache_data, false); assert.deepEqual(record.data_factory_cache_data, []); assert.equal(record.status, 0)
  assert.throws(() => model.failureResultRecord(response({ id: 1 }), target)); assert.equal(model.failureResultRecord(response(null), target), null)
  assert.equal(model.failureResultRecord(response({ id: target.detailId, children: { name: 'Pytest', attachments: [] } }), { ...target, caseType: 2 }).name, 'Pytest')
})

test('关闭后迟到历史不回填，缺失ID/非法类型不请求；可见状态由父级持有', async t => {
  const history = deferred(), h = setup({ history: () => history.promise, props: { visible: false } }); t.after(h.close)
  h.mount(); await flush(); assert.equal(h.calls.length, 0)
  h.props.visible = true; await flush(); h.localVisible.value = false
  history.resolve(response([{ id: 2 }])); await flush(); assert.deepEqual(h.resultOptions.value, [])
  h.props.visible = false; h.props.testSuiteDetailId = ''; h.props.visible = true; await flush()
  assert.ok(h.loadError.value); assert.equal(h.calls.length, 2)
  h.props.testSuiteDetailId = 0; h.props.caseType = ''; await flush(); assert.ok(h.loadError.value); assert.equal(h.calls.length, 2)
})

function apiRenderer(value) {
  return harness('ApiTestReport', 'resultData,activeTab,requestMethod,requestUrl,statusCode,statusCodeClass,responseTime,responseType,assertionSummary,statusText,requestSections,responseSections,cacheData,hasDataFactory', { base, filename: path.join(base, 'ApiTestReport.vue'), props: { resultData: value } })
}
test('公共API结果以有限模型展示，空/坏结构不崩溃，不渲染任意对象', t => {
  const h = apiRenderer(null); t.after(h.close)
  for (const value of [null, false, [], {}, { request: false, response: [], ass: [null, false], recovery_errors: {} }, { name: {}, response: { time: {}, code: false } }]) {
    h.props.resultData = value
    assert.equal(h.requestMethod.value, '-'); assert.equal(h.requestUrl.value, '-'); assert.equal(h.responseTime.value, '-'); assert.equal(h.statusCode.value, '-')
    assert.equal(h.statusCodeClass.value, ''); assert.equal(h.assertionSummary.value, '暂无'); assert.equal(h.resultData.value.recovery_errors.length, 0)
    assert.equal(h.responseSections.value[0].key, 'empty'); assert.equal(h.requestSections.value.length, 0)
  }
})
test('API结果保留JSON false/0、缓存false、ID0及大字符串，原始请求/断言证据不修改', t => {
  const value = { id: 0, status: 0, ass: [null, { status: 0, evidence: { value: false } }, { status: 1 }], cache_data: false,
    request: { method: 'POST', url: 'https://example.com', json: false }, response: { code: 0, time: 0, json: false }, recovery_errors: [null, 'error'] }
  const copy = structuredClone(value), h = apiRenderer(value); t.after(h.close)
  assert.equal(h.resultData.value.id, 0); assert.equal(h.statusCode.value, 0); assert.equal(h.responseTime.value, '0.00 秒'); assert.equal(h.responseType.value, 'JSON')
  assert.equal(h.responseSections.value.find(item => item.key === 'json').data, false); assert.equal(h.requestSections.value.find(item => item.key === 'body').data, false)
  assert.equal(h.cacheData.value, false); assert.equal(h.assertionSummary.value, '1 失败 / 2 总数'); assert.deepEqual(h.resultData.value.recovery_errors, ['error'])
  assert.deepEqual(value, copy)
  h.props.resultData = { id: '9223372036854775807', status: 1, response: { json: 0 } }
  assert.equal(h.resultData.value.id, '9223372036854775807'); assert.equal(h.responseSections.value.find(item => item.key === 'json').data, 0)
})
test('公共API渲染换结果重置tab，SSE/WebSocket和快照状态继续保留', async t => {
  const h = apiRenderer({ status: 1 }); t.after(h.close); await flush(); assert.equal(h.activeTab.value, 'assertion')
  h.activeTab.value = 'cache'; h.props.resultData.status = 3; await flush(); assert.equal(h.activeTab.value, 'cache')
  h.activeTab.value = 'cache'; h.props.resultData = { status: 0, response: { sse_events: [{ data: 0 }] } }; await flush()
  assert.equal(h.activeTab.value, 'response'); assert.equal(h.responseType.value, 'SSE')
  h.props.resultData = { result_mode: 'snapshot', response: { ws_messages: [{ data: false }] } }; await flush()
  assert.equal(h.statusText.value, '执行中'); assert.equal(h.responseType.value, 'WebSocket')
})

test('抽屉及历史、API/UI/Pytest渲染调用链SFC脚本/模板/样式编译', async () => {
  for (const relative of ['TestReportResultDrawer.vue', '../business/ExecutionHistoryList.vue', '../business/ExecutionResultHistoryDrawer.vue', 'ElementTestReport.vue', 'ApiTestReport.vue', 'PytestTestReport.vue']) {
    const filename = path.join(base, relative), { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(errors, []); const script = compileScript(descriptor, { id: relative })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: relative, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ id: relative, filename, source: style.content, scoped: style.scoped, preprocessLang: style.lang })).errors, [])
  }
})
