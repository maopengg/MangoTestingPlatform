import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { compileScript, compileTemplate, parse } from '@vue/compiler-sfc'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/components/business')
const row = (id = 1, target_id = 10, target_type = 'pytest_case') => ({ id, target_id, target_type, status: 0, is_latest: false, label: `记录 ${id}`, source_type: 'page' })
const response = data => ({ code: 200, data })
const detail = (id = 1, target_id = 10, result_data = []) => response({ ...row(id, target_id), result_data, trace_id: 'trace-example' })
const settle = async () => { await flush(); await new Promise(setImmediate) }

function setup(options = {}) {
  const mounted = [], activated = [], deactivated = [], unmounted = [], listeners = new Set(), calls = { list: [], detail: [], options: [], share: [], enum: 0, enumShare: 0 }
  globalThis.document = { hidden: false, addEventListener: (_, fn) => listeners.add(fn), removeEventListener: (_, fn) => listeners.delete(fn) }
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'test-session', selected_environment: 0 }), route = vue.reactive({ fullPath: '/pytest/case/index' })
  const api = {
    getExecutionResultList: query => { calls.list.push(query); return options.list ? options.list(query) : Promise.resolve(response([row()])) },
    getExecutionResultDetailResolved: id => { calls.detail.push(id); return options.detail ? options.detail(id) : Promise.resolve(detail(id)) },
    getSystemTestSuiteDetailsResultOptionsShare: (...args) => { calls.options.push(args); return options.options ? options.options(...args) : Promise.resolve(response([row()])) },
    getSystemTestSuiteDetailsResultShare: (...args) => { calls.share.push(args); return options.share ? options.share(...args) : Promise.resolve(response({ children: [{ parameter_id: 0, status: 0, response: { data: false } }] })) },
  }
  const h = harness('ExecutionResultHistoryDrawer', 'records,selectedId,selectedDetail,loading,detailLoading,listFailed,detailFailed,historyItems,stepOptions,selectedStepKey,selectedScenarioKey,selectedTreeKey,selectedApiResult,showResultNavigator,selectedErrorMessage,loadList,selectResult,retryDetail,updateVisible,openExecutionTrace,selectTreeNode,statusColor,statusText', {
    base, filename: path.join(base, 'ExecutionResultHistoryDrawer.vue'), api,
    props: { visible: false, title: '执行历史', caseId: undefined, query: { target_type: 'pytest_case', target_id: 10 }, ...options.props },
    modules: {
      vue: { ...vue, useSlots: () => options.slots || {}, onMounted: fn => mounted.push(fn), onActivated: fn => activated.push(fn), onDeactivated: fn => deactivated.push(fn), onBeforeUnmount: fn => unmounted.push(fn) },
      'vue-router': { useRoute: () => route },
      '@/store/modules/user': { default: () => user },
      '@/store/modules/get-enum': { useEnum: () => ({ getEnum: () => { calls.enum++; return options.enum ? options.enum() : Promise.resolve() }, getEnumShare: async () => { calls.enumShare++ }, task_status: { 0: { title: '失败' }, 1: { title: '通过' } } }) },
      '@arco-design/web-vue/es/icon': { IconHistory: {} },
    },
  })
  mounted.forEach(fn => fn())
  return { ...h, user, route, calls, listeners, open: () => { h.props.visible = true }, pause: () => deactivated.forEach(fn => fn()), resume: () => activated.forEach(fn => fn()), visibility: hidden => { document.hidden = hidden; listeners.forEach(fn => fn()) }, dispose: () => { unmounted.forEach(fn => fn()); h.close() } }
}

test('normal list and detail load independently; repeated reads coalesce and enum failure does not block', async () => {
  const list = deferred(), pendingDetail = deferred(), h = setup({ list: () => list.promise, detail: () => pendingDetail.promise, enum: async () => { throw Error('enum unavailable') } })
  h.open()
  const first = h.loadList(), second = h.loadList()
  assert.equal(first, second)
  await settle()
  assert.equal(h.calls.list.length, 1)
  list.resolve(response([row()]))
  await first
  await settle()
  assert.equal(h.loading.value, false)
  assert.equal(h.detailLoading.value, true)
  assert.equal(h.records.value.length, 1)
  h.selectResult(1)
  assert.equal(h.calls.detail.length, 1)
  pendingDetail.resolve(detail())
  await settle()
  assert.equal(h.detailLoading.value, false)
  assert.equal(h.selectedDetail.value.id, 1)
  assert.equal(h.historyItems.value[0].latest, false)
  h.dispose()
})

test('query A-B-A snapshots ignore old list responses and stale finally cannot end current loading', async () => {
  const requests = [], h = setup({ list: () => { const d = deferred(); requests.push(d); return d.promise } })
  h.open(); await settle()
  h.props.query = { target_type: 'pytest_case', target_id: 20 }; await settle()
  h.props.query = { target_type: 'pytest_case', target_id: 10 }; await settle()
  requests[0].resolve(response([row(8)])); requests[1].reject(Error('old failure')); await settle()
  assert.equal(h.loading.value, true)
  assert.deepEqual(h.records.value, [])
  requests[2].resolve(response([row(3)])); await settle()
  assert.deepEqual(h.records.value.map(item => item.id), [3])
  assert.deepEqual(h.calls.list.map(query => query.target_id), [10, 20, 10])
  assert.ok(h.calls.list.every(query => query.page === 1 && query.pageSize === 20))
  h.dispose()
})

test('changing a field in query object is observed without requiring replacement', async () => {
  const h = setup({ list: query => Promise.resolve(response([row(1, query.target_id)])), detail: id => Promise.resolve(detail(id, 20)) })
  h.open(); await settle()
  h.props.query.target_id = 20
  await settle()
  assert.equal(h.calls.list.at(-1).target_id, 20)
  assert.equal(h.selectedDetail.value.target_id, 20)
  h.dispose()
})

test('close during list read clears state; reopening same target rejects the old response', async () => {
  const requests = [], h = setup({ list: () => { const d = deferred(); requests.push(d); return d.promise } })
  h.open(); await settle()
  h.updateVisible(false)
  assert.equal(h.loading.value, false)
  assert.deepEqual(h.events.at(-1), ['update:visible', false])
  await h.loadList()
  assert.equal(h.calls.list.length, 1)
  h.props.visible = false; h.open(); await settle()
  requests[0].resolve(response([row(9)])); await settle()
  assert.deepEqual(h.records.value, [])
  assert.equal(h.loading.value, true)
  requests[1].resolve(response([row()])); await settle()
  assert.equal(h.selectedDetail.value.id, 1)
  h.dispose()
})

test('detail A-B-A captures id and ignores old success/error/finally', async () => {
  const requests = [], h = setup({ list: async () => response([row(1), row(2)]), detail: id => { const d = deferred(); requests.push({ id, ...d }); return d.promise } })
  h.open(); await settle()
  h.selectResult(2); await settle()
  h.selectResult(1); await settle()
  requests[0].resolve(detail(1)); requests[1].reject(Error('stale')); await settle()
  assert.equal(h.selectedDetail.value, null)
  assert.equal(h.detailLoading.value, true)
  assert.equal(h.detailFailed.value, false)
  requests[2].resolve(detail(1)); await settle()
  assert.equal(h.selectedDetail.value.id, 1)
  assert.equal(h.detailLoading.value, false)
  h.dispose()
})

test('list and detail failures have independent retries; invalid responses are not empty success', async () => {
  let lists = 0, details = 0
  const h = setup({ list: async () => ++lists === 1 ? { code: 200, data: {} } : response([row()]), detail: async () => ++details === 1 ? detail(2) : detail() })
  h.open(); await settle()
  assert.equal(h.listFailed.value, true)
  assert.equal(h.loading.value, false)
  await h.loadList(); await settle()
  assert.equal(h.listFailed.value, false)
  assert.equal(h.detailFailed.value, true)
  assert.equal(h.selectedDetail.value, null)
  await h.retryDetail()
  assert.equal(h.detailFailed.value, false)
  assert.equal(h.selectedDetail.value.id, 1)
  h.dispose()
})

test('target mismatch is rejected in summaries and selected detail', async () => {
  let count = 0
  const h = setup({ list: async () => response([row(1, ++count === 1 ? 20 : 10)]), detail: async () => detail(1, 20) })
  h.open(); await settle()
  assert.equal(h.listFailed.value, true)
  await h.loadList(); await settle()
  assert.equal(h.detailFailed.value, true)
  assert.equal(h.selectedDetail.value, null)
  h.dispose()
})

test('identity, role, token, environment and route A-B-A close and invalidate pending work', async () => {
  for (const field of ['userId', 'roleId', 'token', 'selected_environment', 'fullPath']) {
    const pending = deferred(), h = setup({ list: () => pending.promise })
    h.open(); await settle()
    const owner = field === 'fullPath' ? h.route : h.user, old = owner[field]
    owner[field] = typeof old === 'number' ? old + 1 : old + '-changed'
    owner[field] = old
    pending.resolve(response([row()])); await settle()
    assert.deepEqual(h.records.value, [], field)
    assert.equal(h.loading.value, false, field)
    assert.equal(h.events.at(-1)[1], false, field)
    h.dispose()
  }
})

test('background/KeepAlive pause invalidates reads, resumes current record and unregisters listener', async () => {
  const requests = [], h = setup({ list: () => { const d = deferred(); requests.push(d); return d.promise } })
  h.open(); await settle()
  h.visibility(true)
  requests[0].resolve(response([row(9)])); await settle()
  assert.deepEqual(h.records.value, [])
  h.visibility(false); await settle()
  requests[1].resolve(response([row()])); await settle()
  h.pause()
  await h.loadList()
  assert.equal(h.calls.list.length, 2)
  h.resume(); await settle()
  h.dispose()
  requests[2].resolve(response([row()])); await settle()
  assert.equal(h.selectedDetail.value, null)
  assert.equal(h.listeners.size, 0)
})

test('history tree uses data attributes instead of the readonly DOM nodeType property', async () => {
  const h = setup()
  const state = harness('ExecutionResultHistoryDrawer', 'selectedDetail,resultTreeData', {
    base, filename: path.join(base, 'ExecutionResultHistoryDrawer.vue'),
    props: h.props,
    modules: {
      vue: { ...vue, useSlots: () => ({}), onMounted() {}, onActivated() {}, onDeactivated() {}, onBeforeUnmount() {} },
      'vue-router': { useRoute: () => ({ fullPath: '/' }) },
      '@/store/modules/user': { default: () => ({}) },
      '@/store/modules/get-enum': { useEnum: () => ({}) },
      '@arco-design/web-vue/es/icon': { IconHistory: {} },
    },
  })
  state.selectedDetail.value = { result_data: [{ id: 1, parameter_id: 2, status: 1 }] }
  const tree = state.resultTreeData.value
  assert.equal(tree[0]['data-result-kind'], 'step')
  assert.equal(tree[0].children[0]['data-result-kind'], 'scenario')
  assert.equal('nodeType' in tree[0], false)
  assert.equal('nodeType' in tree[0].children[0], false)
  state.close();h.dispose()
})

test('public report history uses share endpoints without a logged-in user and preserves parameter zero', async () => {
  const h = setup({ props: { query: undefined, testSuiteDetailId: 0, preferredParameterId: 0, currentTestSuiteId: 0 }, options: async () => response([{ id: 7, test_suite_id: 0, status_text: '通过', is_case_latest: false }]), share: async () => response({ children: [{ parameter_id: 8, status: 1 }, { parameter_id: 0, status: 0, response: { body: false } }] }) })
  h.user.token = ''; h.user.userId = 0
  h.open(); await settle()
  assert.deepEqual(h.calls.options, [[0, 20]])
  assert.deepEqual(h.calls.share, [[0, 7]])
  assert.equal(h.calls.list.length, 0)
  assert.equal(h.calls.detail.length, 0)
  assert.equal(h.calls.enum, 0)
  assert.equal(h.calls.enumShare, 1)
  assert.equal(h.selectedApiResult.value.parameter_id, 0)
  assert.equal(h.selectedApiResult.value.status, 0)
  assert.equal(h.selectedApiResult.value.response.body, false)
  assert.equal(h.historyItems.value[0].sourceText, '本测试报告')
  assert.equal(h.historyItems.value[0].latest, false)
  h.dispose()
})

test('api case compatibility overrides target with exact caseId while retaining revision and environment zero', async () => {
  const h = setup({ props: { caseId: 0, query: { target_type: 'api_info', target_id: 20, revision_id: 0, test_env: 0 } }, list: async () => response([row(0, 0, 'api_case')]), detail: async () => response({ ...row(0, 0, 'api_case'), result_data: { steps: [{ id: 0, parameter_id: 0, status: 0, response: { body: false } }] } }) })
  h.open(); await settle()
  assert.deepEqual(h.calls.list[0], { target_type: 'api_case', target_id: 0, revision_id: 0, test_env: 0, page: 1, pageSize: 20 })
  assert.equal(h.selectedId.value, 0)
  assert.equal(h.selectedApiResult.value.parameter_id, 0)
  assert.equal(h.selectedStepKey.value, '0')
  assert.equal(h.statusText(null), '未知')
  assert.equal(h.statusColor(null), 'gray')
  h.dispose()
})

test('custom UI/Pytest result slots receive intact evidence without API scenario navigation', async () => {
  for (const target_type of ['pytest_case', 'ui_case']) {
    const payload = target_type === 'pytest_case' ? [{ name: 'test_example', status: 'broken', custom: { value: 0 } }] : { children: [{ status: 0, response: false }] }
    const h = setup({ props: { query: { target_type, target_id: 10 } }, slots: { result: () => null }, list: async () => response([row(1, 10, target_type)]), detail: async () => response({ ...row(1, 10, target_type), result_data: payload, trace_id: 'trace-example' }) })
    h.open(); await settle()
    assert.equal(h.showResultNavigator.value, false)
    assert.deepEqual(h.stepOptions.value, [])
    assert.equal(h.selectedDetail.value.result_data, payload)
    h.openExecutionTrace()
    assert.deepEqual(h.events.at(-1), ['show-trace', { result_id: 1 }])
    h.dispose()
  }
})

test('initially visible drawer loads and preserves manual scenario choice after foreground reload', async () => {
  const steps = [{ id: 1, parameter_id: 1, status: 0 }, { id: 1, parameter_id: 2, status: 1 }]
  const h = setup({ props: { visible: true }, detail: async () => detail(1, 10, steps) })
  await settle()
  assert.equal(h.selectedScenarioKey.value, '1:1')
  h.selectTreeNode(['1:2'])
  h.visibility(true); h.visibility(false)
  await settle()
  assert.equal(h.selectedScenarioKey.value, '1:2')
  h.selectTreeNode(['unknown'])
  assert.equal(h.selectedTreeKey.value, '1:2')
  h.selectTreeNode(['step:1'])
  assert.equal(h.selectedScenarioKey.value, '1:1')
  assert.equal(h.selectedTreeKey.value, h.selectedScenarioKey.value)
  h.selectTreeNode([])
  assert.equal(h.selectedTreeKey.value, '1:1')
  h.dispose()
})

test('current scenario has persistent themed selection and a non-color current marker', () => {
  const source = readFileSync(path.join(base, 'ExecutionResultHistoryDrawer.vue'), 'utf8')
  assert.match(source, /'mango-execution-result-current': nodeData.key === selectedScenarioKey/)
  assert.match(source, /:aria-current="nodeData.key === selectedScenarioKey \? 'true' : undefined"/)
  assert.match(source, /v-if="nodeData.key === selectedScenarioKey"[^>]*>当前<\/span>/)
  assert.match(source, /\.execution-result-history__tree-node\.mango-execution-result-current\s*\{\s*border-color: var\(--m-primary-border\);\s*background: var\(--m-primary-soft\);/)
})

test('closing during detail fetch clears previous evidence and fences the response', async () => {
  const pending = deferred(), h = setup({ detail: () => pending.promise })
  h.open(); await settle()
  assert.equal(h.detailLoading.value, true)
  h.updateVisible(false)
  pending.resolve(detail())
  await settle()
  assert.equal(h.selectedDetail.value, null)
  assert.equal(h.selectedId.value, null)
  assert.equal(h.detailLoading.value, false)
  assert.equal(h.detailFailed.value, false)
  h.dispose()
})

test('finite history adapters reject duplicates, preserve false, retry ordering and raw scenario evidence', () => {
  const h = setup(), { historyRecords, historySteps } = h.load('execution-history.ts')
  assert.throws(() => historyRecords(response([row(1), row('1')])) )
  assert.throws(() => historyRecords({ code: 500, data: [] }))
  assert.equal(historyRecords(response([row()]))[0].is_latest, false)
  const input = [{ id: 0, parameter_id: 0, retry_index: 2, status: 1, extra: { zero: 0 } }, { id: 0, parameter_id: 0, retry_index: 0, status: 0 }, { id: 0, parameter_id: 8, status: false }]
  const steps = historySteps(input)
  assert.equal(steps[0].scenarios[0].result, input[0])
  assert.equal(steps[0].scenarios[0].retryCount, 2)
  assert.equal(steps[0].scenarios[0].parameterId, 0)
  assert.equal(steps[0].scenarios[1].status, null)
  assert.equal(steps[0].status, null)
  h.dispose()
})

test('history drawer and shared list scripts/templates compile', () => {
  for (const name of ['ExecutionResultHistoryDrawer', 'ExecutionHistoryList']) {
    const filename = path.join(base, `${name}.vue`), { descriptor } = parse(readFileSync(filename, 'utf8'))
    const script = compileScript(descriptor, { id: name })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: name, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  }
})

test('closed drawer does not issue enum or result reads', async () => {
  const h = setup()
  await settle()
  assert.equal(h.calls.enum, 0)
  assert.equal(h.calls.enumShare, 0)
  assert.equal(h.calls.list.length, 0)
  h.dispose()
})
