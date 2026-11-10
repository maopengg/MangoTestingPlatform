import assert from 'node:assert/strict'
import test from 'node:test'
import * as vue from 'vue'
import { readFileSync } from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { loadModule } from './helpers/auth-config-harness.mjs'
import { deferred, flush, method } from './helpers/case-details-harness.mjs'

const assets = loadModule('src/components/business/ui-case-step-create.ts')
const dto = loadModule('src/views/uitest/case/details/step-list.ts', { '@/components/business/ui-case-step-create': assets })
const long = '90071992547409931234'
const row = (id = 0, overrides = {}) => ({ id, case: { id: 0 }, page_step: { id: 0, name: 'Step', page: { id: 0, name: 'Page' }, module: { id: 0, name: 'Child', full_path: 'Parent/Child' }, project_product: { id: 0, name: 'Product', project: { id: 0, name: 'Project' }, ui_client_type: 0 } }, status: 2, switch_step_open_url: 0, case_data: [{ page_step_details_id: long, value: 'keep' }], error_retry: null, error_message: null, ...overrides })
const response = (...rows) => ({ code: 200, data: rows.length ? rows : [row()] })
function setup(read = async id => response(row(0, { case: { id } }))) {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, reads = [], loaded = []
  const state = vue.reactive({ caseId: 0, running: false }), route = vue.reactive({ path: '/uitest/case/details', fullPath: '/uitest/case/details?id=0' })
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['ui.case:read'] })
  const module = loadModule('src/views/uitest/case/details/composables/useCaseStepList.ts', {
    vue: { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) },
    'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
    '@/components/business/ui-case-step-create': assets, '../step-list': dto,
    '@/api/uitest/case-steps-detailed': { getUiCaseStepsDetailed: id => { reads.push(id); return read(id) } },
  })
  const scope = vue.effectScope(), h = scope.run(() => module.useCaseStepList({ caseId: () => state.caseId, running: () => state.running, loaded: current => loaded.push(current) }))
  return { ...h, state, route, user, permission, callbacks, reads, loaded,
    mount() { callbacks.mount.forEach(fn => fn()) }, visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { callbacks.unmount.forEach(fn => fn()); scope.stop(); globalThis.document = previous },
  }
}
test('finite step projection preserves zero/long IDs, full paths, nullable fields and input evidence', () => {
  const source = row(long, { audit: 'omit', case_data: [{ arbitrary: { nested: 'keep' } }] }), [value] = dto.readCaseStepRows(response(source), 0)
  assert.equal(value.id, long); assert.equal(value.page_step.page.id, 0); assert.equal(value.page_step.project_product.ui_client_type, 0); assert.equal(value.page_step.module.full_path, 'Parent/Child')
  assert.equal(value.error_retry, null); assert.equal('audit' in value, false); assert.equal('case' in value, false); assert.deepEqual(value.case_data, source.case_data); assert.notEqual(value.case_data, source.case_data)
  assert.equal(dto.readCasePageStep(0).id, 0); assert.equal(dto.readCasePageStep(null), null)
})
test('non-success, malformed, duplicate, unsafe ID and wrong-case data are rejected', () => {
  for (const value of [{ code: 403, data: [] }, { code: 200, data: {} }, response(row(), row('0')), response(row(0, { case: 2 })), response(row(Number(long))), response(row(0, { case_data: {} })), response(row(0, { status: 'x' })), response(row(0, { switch_step_open_url: 2 }))]) assert.throws(() => dto.readCaseStepRows(value, 0))
  assert.deepEqual(dto.readCaseStepRows({ code: 200, data: [] }, 0), [])
})
test('active execution merge preserves final progress while accepting incoming completed steps', () => {
  const values = [0, 1, 2, 3].flatMap(status => [0, 1, 2, 3].map(incoming => [status, incoming]))
  for (const [status, incoming] of values) {
    const current = dto.readCaseStepRows(response(row(0, { status, error_message: 'Current' })), 0), next = dto.readCaseStepRows(response(row(0, { status: incoming, error_message: 'Incoming' })), 0)
    const [merged] = dto.mergeActiveCaseSteps(next, current)
    const expected = [0, 1].includes(status) ? status : status === 3 && [0, 1].includes(incoming) ? incoming : status === 3 || incoming === 3 ? 3 : 2
    assert.equal(merged.status, expected); assert.equal(merged.error_message, status === 3 && [0, 1].includes(incoming) ? 'Incoming' : 'Current'); assert.equal(current[0].status, status)
  }
})
test('list loading deduplicates requests and selects the actual row, preserving ID zero', async t => {
  const pending = deferred(), h = setup(() => pending.promise); t.after(h.close)
  const first = h.load(), duplicate = h.load(); assert.equal(first, duplicate); await flush(); assert.deepEqual(h.reads, [0]); assert.equal(h.loading.value, true); assert.equal(h.selected.value, null)
  pending.resolve(response(row(0), row(long))); assert.equal(await first, true); assert.equal(h.selected.value, h.rows.value[0]); h.select(long); assert.equal(h.selected.value.id, long)
  h.replace(h.rows.value.map(item => item.id === long ? { ...item, error_retry: 5 } : item)); assert.equal(h.selected.value.error_retry, 5)
  h.replace(h.rows.value.filter(item => item.id !== long)); assert.equal(h.selected.value.id, 0)
  h.replace([]); assert.equal(h.selected.value, null)
})
test('refresh replaces selected record by canonical ID and removal does not resurrect old selection', async t => {
  let data = response(row(0), row(long)), h = setup(async () => data); t.after(h.close)
  await h.load(); h.select(long); data = response(row('0'), row(long, { error_retry: 8 })); await h.load(false); assert.equal(h.selected.value.error_retry, 8); assert.equal(h.loading.value, false)
  data = response(row(0)); await h.load(); assert.equal(h.selected.value.id, 0); data = response(row(0), row(long)); await h.load(); assert.equal(h.selected.value.id, 0)
})
test('failed reads retain rows and selection, expose retry and release loading', async t => {
  let fail = false; const h = setup(async () => fail ? { code: 403 } : response()); t.after(h.close)
  await h.load(); const selected = h.selected.value; fail = true; assert.equal(await h.load(), false); assert.equal(h.selected.value, selected); assert.match(h.error.value, /失败/); assert.equal(h.loading.value, false)
  fail = false; assert.equal(await h.load(), true); assert.equal(h.error.value, '')
})
test('silent refresh merges the latest socket state received while HTTP was pending', async t => {
  const pending = deferred(), h = setup(() => pending.promise); t.after(h.close); h.state.running = true
  const loading = h.load(false); await flush(); assert.equal(h.loading.value, false)
  h.replace(dto.readCaseStepRows(response(row(0, { status: 1 })), 0)); pending.resolve(response(row(0, { status: 2 }))); await loading; assert.equal(h.rows.value[0].status, 1)
})
test('structure commit invalidates pending GET without hiding a later request loading', async t => {
  const first = deferred(), second = deferred(); let calls = 0; const h = setup(() => ++calls === 1 ? first.promise : second.promise); t.after(h.close)
  const old = h.load(); await flush(); h.invalidate(); h.replace(dto.readCaseStepRows(response(row(long)), 0)); const current = h.load(); await flush()
  first.resolve(response()); assert.equal(await old, false); assert.equal(h.rows.value[0].id, long); assert.equal(h.loading.value, true)
  second.resolve(response(row(long))); assert.equal(await current, true); assert.equal(h.loading.value, false)
})
const changes = [h => h.state.caseId = 2, h => h.user.userId++, h => h.user.roleId++, h => h.user.token = 'example-new', h => h.user.selected_environment++, h => h.permission.permissionKeys.push('example:read'), h => h.route.path = '/other', h => h.route.fullPath += '&other=1', h => { h.state.caseId = 2; h.state.caseId = 0 }]
test('all identities and A-B-A invalidate prior responses, selected rows and derived callback contexts', async () => {
  for (const change of changes) {
    const pending = deferred(); let reads = 0; const h = setup(id => ++reads === 1 ? pending.promise : Promise.resolve(response(row(long, { case: id }))))
    try { const current = h.capture(), old = h.load(); await flush(); change(h); await flush(); pending.resolve(response()); assert.equal(await old, false); assert.equal(current(), false); assert.notEqual(h.rows.value[0]?.id, 0); assert.equal(h.error.value, '') } finally { h.close() }
  }
})
test('background/KeepAlive pause work and silently reload without accepting pre-pause requests', async () => {
  for (const leave of [h => h.visibility('hidden'), h => h.callbacks.deactivate.forEach(fn => fn())]) {
    const pending = deferred(); let reads = 0; const h = setup(() => ++reads === 1 ? pending.promise : Promise.resolve(response(row(long))))
    try { h.mount(); const old = h.load(); await flush(); leave(h); assert.equal(await h.load(), false); pending.resolve(response()); assert.equal(await old, false); assert.deepEqual(h.rows.value, []); h.visibility('visible'); h.callbacks.activate.forEach(fn => fn()); await flush(); assert.equal(h.selected.value.id, long); assert.equal(h.loading.value, false) } finally { h.close() }
  }
})
test('unmount rejects late data and clears canonical selection', async t => {
  const pending = deferred(), h = setup(() => pending.promise); t.after(h.close)
  const old = h.load(); await flush(); h.callbacks.unmount.forEach(fn => fn()); pending.resolve(response()); assert.equal(await old, false); assert.deepEqual(h.rows.value, []); assert.equal(h.selected.value, null); assert.equal(h.loading.value, false)
})
test('external polling cancellation cannot apply late reads and missing IDs never query globally', async t => {
  const pending = deferred(), h = setup(() => pending.promise); t.after(h.close); let valid = true
  const old = h.load(false, () => valid); await flush(); valid = false; pending.resolve(response()); assert.equal(await old, false); assert.deepEqual(h.rows.value, []); h.state.caseId = null; assert.equal(await h.load(), false); assert.deepEqual(h.reads, [0])
})
test('integrated parent compiles with canonical selected row and local read error/retry', () => {
  const filename = 'src/views/uitest/case/details/index.vue', { descriptor, errors } = parse(readFileSync(filename, 'utf8')); assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'ui-case-step-list' }), template = compileTemplate({ source: descriptor.template.content, filename, id: 'ui-case-step-list', compilerOptions: { bindingMetadata: script.bindings } }); assert.deepEqual(template.errors, [])
  assert.ok(script.bindings.selectedCaseStep); assert.ok(script.bindings.stepListError)
})
test('parent relation getters preserve zero and paths use the public full-path formatter', () => {
  const filename = 'src/views/uitest/case/details/index.vue', [value] = dto.readCaseStepRows(response(), 0)
  assert.equal(method('getPageStepId', {}, filename)(value), 0); assert.equal(method('getPageId', {}, filename)(value), 0)
  const format = loadModule('src/utils/business-format.ts'), path = method('getCaseStepPath', { formatModulePath: format.formatModulePath }, filename)
  assert.equal(path(value), 'Project / Product / Parent/Child / Page'); assert.equal(method('getPageStepId', {}, filename)(null), '')
})
test('parent retries pending results silently and stops polling only after a successful current read', async () => {
  const filename = 'src/views/uitest/case/details/index.vue', pending = deferred(), calls = []; let valid = true
  const loaded = method('handleCaseStepsLoaded', { caseSteps: { value: [] }, latestUiCaseResultPending: { value: true }, isPendingExecution: () => false, pagePolling: { start: () => calls.push('start'), stop: () => calls.push('stop') }, loadLatestUiCaseExecutionResult: (...args) => { calls.push(args); return pending.promise } }, filename)
  loaded(() => valid); assert.deepEqual(calls, ['start', [true, false]]); valid = false; pending.resolve(true); await flush(); assert.deepEqual(calls, ['start', [true, false]])
})
