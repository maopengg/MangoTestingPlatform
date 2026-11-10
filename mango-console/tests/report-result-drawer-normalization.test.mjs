import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { readFileSync } from 'node:fs'
import { deferred, flush as microtasks, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/report/details')
const response = data => ({ code: 200, data })
async function flush() { await microtasks(); await new Promise(resolve => setImmediate(resolve)) }
function setup(overrides = {}) {
  const route = vue.reactive({ fullPath: '/report/details?id=1' })
  const user = vue.reactive({ userId: null, roleId: null, token: '', selected_environment: 0 })
  const life = { mount: [], unmount: [], activate: [], deactivate: [] }, calls = [], listeners = new Set()
  const originalDocument = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  const add = doc.addEventListener.bind(doc), remove = doc.removeEventListener.bind(doc)
  doc.addEventListener = (type, fn) => { listeners.add(fn); add(type, fn) }
  doc.removeEventListener = (type, fn) => { listeners.delete(fn); remove(type, fn) }
  globalThis.document = doc
  const api = Object.fromEntries(Object.entries(overrides).map(([name, fn]) => [name, (...args) => {
    calls.push([name, ...args]); return Promise.resolve().then(() => fn(...args))
  }]))
  const h = harness('ReportExecutionResultDrawer', 'drawerVisible:visible,detailLoading,detailHistoryLoading:historyLoading,detailResultOptions:options,selectedCase,selectedResultId,detailError,detailHistoryError:historyError,loadDetailHistory:loadHistory,loadDetailResult:loadResult,changeDetailResult:selectResult,open,drawerClose:close', {
    base, props: { reportId: '1' }, api,
    modules: {
      vue: { ...vue, onMounted: fn => life.mount.push(fn), onBeforeUnmount: fn => life.unmount.push(fn), onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn) },
      'vue-router': { useRoute: () => route },
      '@/store/modules/user': { useUserStoreContext: () => user },
    },
  })
  life.mount.forEach(fn => fn()); life.activate.forEach(fn => fn())
  const data = h.load('report-result.ts')
  return { ...h, calls, route, user, life, doc, listeners,
    showDetails: row => h.open(data.reportResultTarget(row, '2')),
    close() { life.unmount.forEach(fn => fn()); h.close(); globalThis.document = originalDocument } }
}

test('重复打开同一结果合并物理读取，首屏无需登录', async t => {
  const history = deferred(), detail = deferred()
  const h = setup({ getSystemTestSuiteDetailsResultOptionsShare: () => history.promise, getSystemTestSuiteDetailsResultShare: () => detail.promise }); t.after(h.close)
  const row = { test_suite_detail_id: 1, case_type: 2 }
  const first = h.showDetails(row), second = h.showDetails(row)
  assert.equal(first, second); await flush()
  assert.equal(h.calls.length, 2); assert.equal(h.user.token, '')
  detail.resolve(response({ id: 1, name: 'ready' })); history.resolve(response([])); await first
  assert.equal(h.selectedCase.value.name, 'ready')
})

for (const field of ['reportId', 'route', 'userId', 'roleId', 'token', 'selected_environment']) {
  test(`${field} A-B-A 同步关闭结果，旧读取和 finally 不影响重开窗口`, async t => {
    const old = deferred(); let reads = 0
    const h = setup({ getSystemTestSuiteDetailsResultOptionsShare: () => response([]), getSystemTestSuiteDetailsResultShare: () => ++reads === 1 ? old.promise : response({ id: 1, name: 'new' }) }); t.after(h.close)
    const first = h.showDetails({ test_suite_detail_id: 1, case_type: 2 }); await flush()
    if (field === 'reportId') { h.props.reportId = '2'; h.props.reportId = '1' }
    else if (field === 'route') { h.route.fullPath = '/report/details?id=2'; h.route.fullPath = '/report/details?id=1' }
    else { const before = h.user[field]; h.user[field] = field === 'token' ? 'fixture-b' : 2; h.user[field] = before }
    assert.equal(h.drawerVisible.value, false); assert.equal(h.selectedCase.value, null)
    await h.showDetails({ test_suite_detail_id: 1, case_type: 2 })
    old.resolve(response({ id: 1, name: 'old' })); await first
    assert.equal(h.selectedCase.value.name, 'new'); assert.equal(h.detailLoading.value, false)
  })
}

test('后台与 KeepAlive 暂停读取，返回重读当前选择；卸载释放监听', async t => {
  const old = deferred(); let reads = 0
  const h = setup({ getSystemTestSuiteDetailsResultOptionsShare: () => response([{ id: 0 }]), getSystemTestSuiteDetailsResultShare: () => ++reads === 1 ? old.promise : response({ id: 1, name: `read-${reads}` }) }); t.after(h.close)
  const first = h.showDetails({ test_suite_detail_id: 1, case_type: 2 }); await flush()
  h.doc.visibilityState = 'hidden'; h.doc.dispatchEvent(new Event('visibilitychange'))
  assert.equal(h.detailLoading.value, false); assert.equal(h.selectedCase.value, null)
  old.resolve(response({ id: 1, name: 'old' })); await first
  assert.equal(h.selectedCase.value, null)
  h.doc.visibilityState = 'visible'; h.doc.dispatchEvent(new Event('visibilitychange')); await flush()
  await h.changeDetailResult(0)
  h.life.deactivate.forEach(fn => fn()); assert.equal(h.selectedCase.value, null)
  const before = h.calls.length
  await h.loadDetailResult(); assert.equal(h.calls.length, before)
  h.life.activate.forEach(fn => fn()); await flush()
  assert.equal(h.selectedResultId.value, '0')
  assert.equal(h.calls.filter(c => c[0] === 'getSystemTestSuiteDetailsResultShare').at(-1)[2], '0')
  h.life.unmount.forEach(fn => fn()); assert.equal(h.listeners.size, 0)
  assert.equal(h.drawerVisible.value, false)
})

test('窗口模板可编译，渲染和错误重试由私有窗口拥有', () => {
  const filename = path.join(base, 'components/ReportExecutionResultDrawer.vue')
  const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'result-drawer' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: 'result-drawer', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
})

test('结果窗口 A-B-A 和关闭后的旧读取不覆盖新选择', async t => {
  const reads = [deferred(), deferred()]; let index = 0
  const h = setup({ getSystemTestSuiteDetailsResultShare: () => reads[index++].promise, getSystemTestSuiteDetailsResultOptionsShare: () => response([{ id: 1 }]) }); t.after(h.close)
  const old = h.showDetails({ test_suite_detail_id: 1, case_type: 2 }); await flush()
  h.drawerVisible.value = false
  const fresh = h.showDetails({ test_suite_detail_id: 2, case_type: 2 }); await flush()
  reads[0].resolve(response({ id: 1, name: 'old' })); await old
  assert.equal(h.detailLoading.value, true)
  reads[1].resolve(response({ id: 2, name: 'new' })); await fresh
  assert.equal(h.selectedCase.value.name, 'new'); assert.equal(h.detailLoading.value, false)
})

test('结果窗口独立加载历史与内容，历史失败后单独重试不重读内容', async t => {
  const history = deferred(); let attempt = 0
  const h = setup({
    getSystemTestSuiteDetailsResultOptionsShare: () => ++attempt === 1 ? history.promise : response([{ id: 0, test_suite_detail_id: 0, is_latest: true }]),
    getSystemTestSuiteDetailsResultShare: () => response({ id: 0, type: 2, children: [{ name: 'ready' }] }),
  }); t.after(h.close)
  const opened = h.showDetails({ test_suite_detail_id: 0, case_type: 2 }); await flush()
  assert.equal(h.selectedCase.value.name, 'ready'); assert.equal(h.detailLoading.value, false)
  assert.equal(h.detailHistoryLoading.value, true)
  history.reject(new Error('failed')); await opened
  assert.ok(h.detailHistoryError.value); assert.equal(h.detailError.value, '')
  await h.loadDetailHistory()
  assert.equal(h.detailHistoryError.value, ''); assert.equal(h.selectedResultId.value, '0')
  assert.equal(h.calls.filter(c => c[0] === 'getSystemTestSuiteDetailsResultShare').length, 1)
})

test('历史默认选择不指向其他报告；选中结果失败清空旧证据并允许原项重试', async t => {
  let attempt = 0
  const h = setup({
    getSystemTestSuiteDetailsResultOptionsShare: () => response([{ id: 9, test_suite_detail_id: 2, is_latest: true }, { id: 0, test_suite_detail_id: 1, is_latest: true }]),
    getSystemTestSuiteDetailsResultShare: () => ++attempt === 2 ? Promise.reject(new Error('failed')) : response({ id: 1, type: 2, children: [{ name: `result-${attempt}` }] }),
  }); t.after(h.close)
  await h.showDetails({ test_suite_detail_id: 1, case_type: 2 })
  assert.equal(h.selectedResultId.value, '0')
  const failed = h.changeDetailResult(9)
  assert.equal(h.selectedCase.value, null); await failed
  assert.ok(h.detailError.value); assert.equal(h.detailLoading.value, false)
  await h.loadDetailResult()
  assert.equal(h.detailError.value, ''); assert.equal(h.selectedCase.value.name, 'result-3')
  assert.equal(h.calls.filter(c => c[0] === 'getSystemTestSuiteDetailsResultShare').at(-1)[2], '9')
})

test('历史慢响应不回退用户选择，快速切换结果只应用最后一次内容', async t => {
  const older = deferred(), newer = deferred(); let read = 0
  const h = setup({
    getSystemTestSuiteDetailsResultOptionsShare: () => response([{ id: 0 }, { id: 1 }]),
    getSystemTestSuiteDetailsResultShare: () => ++read === 1 ? response({ id: 1, name: 'initial' }) : read === 2 ? older.promise : newer.promise,
  }); t.after(h.close)
  await h.showDetails({ test_suite_detail_id: 1, case_type: 2 })
  assert.equal(h.selectedResultId.value, null)
  const first = h.changeDetailResult(0); await flush()
  const last = h.changeDetailResult(1); await flush()
  older.resolve(response({ id: 1, name: 'old' })); await first
  assert.equal(h.selectedCase.value, null); assert.equal(h.detailLoading.value, true)
  newer.resolve(response({ id: 1, name: 'new' })); await last
  assert.equal(h.selectedCase.value.name, 'new'); assert.equal(h.selectedResultId.value, '1')
})

test('结果响应拒绝错明细与错误状态码，清理后的 null 为正常空态', async t => {
  const responses = [response({ id: 2 }), { code: 403, data: { id: 1 } }, response(null)]
  const h = setup({ getSystemTestSuiteDetailsResultOptionsShare: () => response([]), getSystemTestSuiteDetailsResultShare: () => responses.shift() }); t.after(h.close)
  await h.showDetails({ test_suite_detail_id: 1, case_type: 2 })
  assert.ok(h.detailError.value); assert.equal(h.selectedCase.value, null)
  await h.loadDetailResult(); assert.ok(h.detailError.value)
  await h.loadDetailResult(); assert.equal(h.detailError.value, ''); assert.equal(h.selectedCase.value, null)
})
