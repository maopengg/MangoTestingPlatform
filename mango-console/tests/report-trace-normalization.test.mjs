import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/report/details')
const node = (id = 0, patch = {}) => ({ id, parent_step_id: null, label: 'Example', step_type: 'request', status: 1, duration_ms: 0, summary: false, ...patch })
const response = (name = 'example-trace', nodes = [node()]) => ({ code: 200, data: { trace: { trace_id: name, status: null, duration_ms: 0, source_type: 1 }, nodes } })
function setup(api = () => Promise.resolve(response())) {
  const user = vue.reactive({ userId: 1, roleId: 1, token: '', selected_environment: 0 })
  const route = vue.reactive({ fullPath: '/report/details?id=1' })
  const original = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  const life = { mount: [], activate: [], deactivate: [], unmount: [] }, calls = [], listeners = new Set()
  const add = doc.addEventListener.bind(doc), remove = doc.removeEventListener.bind(doc)
  doc.addEventListener = (name, fn) => { listeners.add(fn); add(name, fn) }
  doc.removeEventListener = (name, fn) => { listeners.delete(fn); remove(name, fn) }
  globalThis.document = doc
  const h = harness('ReportExecutionTraceDrawer', 'visible,loading,errorText,trace,nodes,selectedId,selectedNode,expandedIds,visibleNodes,open,drawerClose:close,loadTrace,selectNode,toggleNode,nodeDepth,statusColor', {
    base, props: { reportId: '1' },
    modules: {
      vue: { ...vue, onMounted: fn => life.mount.push(fn), onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn), onBeforeUnmount: fn => life.unmount.push(fn) },
      'vue-router': { useRoute: () => route },
      '@/store/modules/user': { useUserStoreContext: () => user },
      '@/store/modules/get-enum': { useEnum: () => ({ status_colors: { 0: 'red', 1: 'green' } }) },
    },
    api: { getSystemTestSuiteDetailsExecutionTrace(query) { calls.push(query); return api(query) } },
  })
  life.mount.forEach(fn => fn())
  life.activate.forEach(fn => fn())
  return { ...h, user, route, doc, life, calls, listeners, data: h.load('execution-trace.ts'),
    close() { life.unmount.forEach(fn => fn()); h.close(); globalThis.document = original } }
}

test('公开报告不要求 token；查询白名单保留 ID 0，未知状态不显示失败', async t => {
  const h = setup(); t.after(h.close)
  await h.open({ result_id: 0, arbitrary: 'discard' })
  assert.deepEqual(h.calls, [{ result_id: '0', include_list: true }])
  assert.equal(h.trace.value.duration_ms, 0)
  assert.equal(h.trace.value.status, null)
  assert.equal(h.selectedId.value, '0')
  assert.equal(h.data.formatTraceSummary(h.nodes.value[0].summary), 'false')
  assert.equal(h.data.traceStatusText(null), '未知')
  assert.equal(h.statusColor(null), 'gray')
})

test('相同查询读取期间合并 Promise，加载状态持续到真实请求完成', async t => {
  const read = deferred(), h = setup(() => read.promise); t.after(h.close)
  const a = h.open({ result_id: 1 }), b = h.open({ result_id: 1 })
  assert.equal(a, b)
  await flush(); assert.equal(h.calls.length, 1); assert.equal(h.loading.value, true)
  read.resolve(response()); await a
  assert.equal(h.loading.value, false)
})

test('A-B-A 结果切换忽略旧响应和旧 finally', async t => {
  const reads = [deferred(), deferred(), deferred()]; let index = 0
  const h = setup(() => reads[index++].promise); t.after(h.close)
  const a = h.open({ result_id: 1 }); await flush()
  const b = h.open({ result_id: 2 }); await flush()
  const latest = h.open({ result_id: 1 }); await flush()
  reads[0].resolve(response('old')); await a
  assert.equal(h.loading.value, true); assert.equal(h.trace.value, null)
  reads[1].reject(new Error('old failed')); await b
  assert.equal(h.errorText.value, ''); assert.equal(h.loading.value, true)
  reads[2].resolve(response('current')); await latest
  assert.equal(h.trace.value.trace_id, 'current'); assert.equal(h.loading.value, false)
})

test('关闭后旧结果不回填，重新打开同一查询发起新读取', async t => {
  const old = deferred(); let count = 0
  const h = setup(() => count++ ? Promise.resolve(response('new')) : old.promise); t.after(h.close)
  const pending = h.open({ result_id: 1 }); await flush()
  h.visible.value = false
  await h.open({ result_id: 1 })
  old.resolve(response('old')); await pending
  assert.equal(h.trace.value.trace_id, 'new'); assert.equal(h.visible.value, true)
})

for (const field of ['userId', 'roleId', 'token', 'selected_environment', 'reportId', 'route']) {
  test(`${field} 上下文切换同步关闭，迟到响应不能展示原记录`, async t => {
    const read = deferred(), h = setup(() => read.promise); t.after(h.close)
    const pending = h.open({ result_id: 1 }); await flush()
    if (field === 'reportId') h.props.reportId = '2'
    else if (field === 'route') h.route.fullPath = '/report/details?id=2'
    else h.user[field] = field === 'token' ? 'fixture-b' : 2
    assert.equal(h.visible.value, false); assert.equal(h.loading.value, false)
    read.resolve(response('old')); await pending
    assert.equal(h.trace.value, null)
  })
}

test('后台暂停并清空旧证据，回来恢复当前窗口请求，卸载清理监听', async t => {
  const old = deferred(); let index = 0
  const h = setup(() => index++ ? Promise.resolve(response('resumed')) : old.promise); t.after(h.close)
  const pending = h.open({ result_id: 1 }); await flush()
  h.doc.visibilityState = 'hidden'; h.doc.dispatchEvent(new Event('visibilitychange'))
  assert.equal(h.loading.value, false); assert.equal(h.trace.value, null)
  old.resolve(response('old')); await pending
  assert.equal(h.trace.value, null)
  h.doc.visibilityState = 'visible'; h.doc.dispatchEvent(new Event('visibilitychange')); await flush()
  assert.equal(h.trace.value.trace_id, 'resumed')
  assert.equal(h.calls.length, 2)
  h.life.unmount.forEach(fn => fn())
  assert.equal(h.listeners.size, 0)
})

test('KeepAlive 停用时忽略迟到失败，激活只恢复一次', async t => {
  const old = deferred(); let index = 0
  const h = setup(() => index++ ? Promise.resolve(response('resumed')) : old.promise); t.after(h.close)
  const pending = h.open({ result_id: 1 }); await flush()
  h.life.deactivate.forEach(fn => fn()); old.reject(new Error('late')); await pending
  assert.equal(h.errorText.value, '')
  h.life.activate.forEach(fn => fn()); await flush()
  h.life.activate.forEach(fn => fn()); await flush()
  assert.equal(h.trace.value.trace_id, 'resumed'); assert.equal(h.calls.length, 2)
})

test('同步抛错和失败响应均可重试，失败不伪装成空链路', async t => {
  let count = 0
  const h = setup(() => { if (!count++) throw new Error('sync'); return Promise.resolve(count === 2 ? { code: 403, data: response().data } : response()) }); t.after(h.close)
  await h.open({ result_id: 1 }); assert.ok(h.errorText.value); assert.equal(h.loading.value, false)
  await h.loadTrace(); assert.ok(h.errorText.value)
  await h.loadTrace(); assert.equal(h.errorText.value, ''); assert.ok(h.trace.value)
})

test('空链路合法；不合法查询不发请求，过大 number ID 不损失精度提交', async t => {
  const h = setup(() => Promise.resolve({ code: 200, data: { trace: null, nodes: [] } })); t.after(h.close)
  await h.open({ result_id: '' }); await h.open({ result_id: Number.MAX_SAFE_INTEGER + 1 })
  assert.equal(h.calls.length, 0)
  await h.open({ result_id: '9007199254740993' })
  assert.equal(h.calls[0].result_id, '9007199254740993'); assert.equal(h.errorText.value, '')
  assert.equal(h.trace.value, null)
})

test('节点解析拒绝重复、缺失父节点和循环关系，保留 false/null/0 摘要', t => {
  const h = setup(); t.after(h.close)
  for (const nodes of [[node(), node()], [node(1, { parent_step_id: 99 })], [node(1, { parent_step_id: 1 })], [node(1, { parent_step_id: 2 }), node(2, { parent_step_id: 1 })]]) {
    assert.throws(() => h.data.parseReportTrace(response('example', nodes), {}))
  }
  assert.throws(() => h.data.parseReportTrace(response('other'), { trace_id: 'expected' }))
  for (const summary of [false, null, 0]) assert.equal(h.data.parseReportTrace(response('example', [node(0, { summary })]), {}).nodes[0].summary, summary)
})

test('嵌套重试默认展开所选失败节点祖先，收起时选中父节点', async t => {
  const h = setup(() => Promise.resolve(response('example', [node(0, { step_type: 'retry_round' }), node(1, { parent_step_id: 0, step_type: 'retry_round' }), node(2, { parent_step_id: 1, status: 0 })]))); t.after(h.close)
  await h.open({ result_id: 1 })
  assert.equal(h.selectedId.value, '2'); assert.deepEqual(h.visibleNodes.value.map(n => n.id), ['0', '1', '2'])
  h.toggleNode(h.nodes.value[0])
  assert.equal(h.selectedId.value, '0'); assert.deepEqual(h.visibleNodes.value.map(n => n.id), ['0'])
  h.selectNode(h.nodes.value[2]); assert.equal(h.selectedId.value, '0')
})

test('主页面与独立抽屉的 SFC 脚本/模板编译通过', () => {
  for (const relative of ['index.vue', 'components/ReportExecutionTraceDrawer.vue']) {
    const filename = path.join(base, relative), { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
    assert.deepEqual(errors, [])
    compileScript(descriptor, { id: 'report70' })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: 'report70' }).errors, [])
  }
})
