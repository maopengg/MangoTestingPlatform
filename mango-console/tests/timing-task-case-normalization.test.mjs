import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { deferred, flush, harness, method } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/timing/tasks/case'), filename = path.join(base, 'index.vue')
function actual(file, dependencies = {}) {
  const exports = {}, source = ts.transpileModule(readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  new Function('exports', 'require', source)(exports, name => {
    if (name in dependencies) return dependencies[name]
    if (name === '@/utils/api-response') return actual(path.resolve('src/utils/api-response.ts'))
    { if (['@/utils/load-error', '@/utils/api-response'].includes(name)) return loadFeedbackModule(name); throw Error('Unexpected dependency ' + name) }
  })
  return exports
}
const { parseTaskCaseConfig } = actual(path.join(base, 'task-config.ts'))
const records = actual(path.join(base, 'case-records.ts'), { '@/utils/business-format': actual('src/utils/business-format.ts') })
const row = (overrides = {}) => ({ id: 0, name: 'Example task', execution_scope: 'manual', case_types: [0, 1], execution_scenes: ['regression'],
  project_product: { id: 0, name: 'Example product', project: { id: 0, name: 'Example project' } }, module: { id: 0, name: 'Example module', full_path: 'Example/Module' }, ...overrides })
const ok = data => ({ code: 200, msg: 'ok', data, totalSize: Array.isArray(data) ? data.length : 1 })
function configReader(api = async () => ok([row()])) {
  const dependencies = {
    taskConfigRequestId: 0, currentTaskId: vue.ref(0), taskConfigLoading: vue.ref(false), taskConfigError: vue.ref(''), taskConfig: vue.ref(null),
    addForm: vue.reactive({ type: 1, projectProduct: '', module: '' }), boundFilter: vue.reactive({ projectProduct: '', module: '' }),
    getSystemTasks: api, parseTaskCaseConfig,
    available: () => true,
  }
  dependencies.captureContext = () => { const id = dependencies.currentTaskId.value; return () => id === dependencies.currentTaskId.value }
  return { ...dependencies, load: method('loadTaskConfig', dependencies, filename) }
}
function page(overrides = {}, getEnum = async () => {}) {
  const previousDocument = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const calls = [], confirms = [], messages = []
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['timing.tasks:read'] })
  const route = vue.reactive({ path: '/timing/case', fullPath: '/timing/case?id=1', query: { id: '1' } })
  const api = Object.fromEntries(['getSystemTasks', 'getSystemTasksRunCase', 'getSystemTasksTypeCaseName', 'getUserName', 'getPytestProductName', 'getSystemTaskSelectionCases', 'postSystemTasksRunCase', 'deleteSystemTasksRunCase'].map(name => [name, (...args) => {
    calls.push([name, ...args])
    return overrides[name]?.(...args) ?? Promise.resolve(name === 'getSystemTasks' ? ok([row({ id: 1 })]) : name === 'postSystemTasksRunCase' ? ok({ created_count: 1, updated_count: 0, skipped_count: 0 }) : ok([]))
  }]))
  const h = harness('index', 'taskConfig,taskConfigLoading,taskConfigError,initializeTaskCases,loadTaskConfig,enumError,enumLoading,loadEnums,addForm,boundFilter,ruleFilter,rulePagination,candidatePagination,pagination,candidateCases,boundRows,ruleCases,ruleSelectedCount,ownerOptions,boundModuleOptions,addSelectionKeys,selectedRowKeys,boundCaseKeySet,boundCaseKeysError,candidateError,boundError,ruleError,ownerError,boundModuleError,bindingError,deletionError,candidateLoading,boundLoading,ruleLoading,ownerLoading,boundModuleLoading,addLoading,deleteLoading,writeBusy,deletingIds,loadCandidateCases,loadBoundCaseKeys,doRefresh,loadRuleCases,getNickName,loadBoundPytestModules,onAddSelectedCases,onDelete,changeType,isCandidateSelectable', {
    base, props: { taskId: 1 }, api,
    modules: { vue: { ...vue, onMounted: callback => callbacks.mount.push(callback), onActivated: callback => callbacks.activate.push(callback), onDeactivated: callback => callbacks.deactivate.push(callback), onBeforeUnmount: callback => callbacks.unmount.push(callback) },
      'vue-router': { useRoute: () => route }, '@/hooks/table': actual('src/hooks/table.ts', { vue }),
      '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
      '@/hooks/useDisplayDensity': { scaleDensityLength: value => value },
      '@/store/modules/get-enum': { useEnum: () => ({ test_case_type: [], getEnum }) },
      '@arco-design/web-vue': { Message: Object.fromEntries(['error','success','warning'].map(name => [name, value => messages.push([name,value])])),
        Modal: { confirm(options) { const handle = { options, closed: false, close() { this.closed = true } }; confirms.push(handle); return handle } } },
    } })
  h.taskConfig.value = parseTaskCaseConfig(ok([row({ id: 1 })]), 1)
  h.addForm.projectProduct = 0; h.addForm.module = 0
  h.candidateCases.value = [{ key: 4, title: 'Example case', module: null, published_release_id: 8 }]
  return { ...h, calls, confirms, messages, callbacks, user, permission, route,
    mount() { callbacks.mount.forEach(fn => fn()); callbacks.activate.forEach(fn => fn()) },
    visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { callbacks.unmount.forEach(fn => fn()); h.close(); globalThis.document = previousDocument },
  }
}

test('bound DTO copies only display data, preserving zero enums, paths and nested Pytest product ownership', () => {
  const asset = { name: 'Example case', project_product: { project_product: row().project_product }, module: row().module, case_people: { name: 'Example owner' },
    level: 0, scenario_layer: 0, scenario_type: 'normal', scenario_tags: ['regression'], execution_config: { omit: true } }
  const result = records.parseBoundCases(ok([{ id: '90071992547409931234', type: 2, pytest_case: asset, task: { omit: true } }]))
  assert.equal(result.total, 1); assert.equal(result.rows[0].id, '90071992547409931234'); assert.equal(result.rows[0].product_path, 'Example project/Example product')
  assert.equal(result.rows[0].module_path, 'Example/Module'); assert.equal(result.rows[0].owner_name, 'Example owner'); assert.equal(result.rows[0].level, 0)
  assert.equal('task' in result.rows[0], false); assert.equal('pytest_case' in result.rows[0], false)
  result.rows[0].scenario_tags.push('other'); assert.deepEqual(asset.scenario_tags, ['regression'])
})
test('candidate, option, key and rule parsers reject invalid responses instead of empty success', () => {
  for (const parser of [records.parseCandidateCases, records.parseTaskCaseOptions, records.parseBoundCaseKeys, records.parseBoundCases, records.parseRuleCases]) {
    assert.throws(() => parser({ code: 403, data: [] })); assert.throws(() => parser(ok({})))
  }
  assert.throws(() => records.parseTaskCaseOptions(ok([{ key: 0, title: 'A' }, { key: '0', title: 'B' }])))
  const candidate = records.parseCandidateCases(ok([{ key: 0, title: 'Example', module: null, published_release_id: '90071992547409931234', release_options: ['omit'] }]))[0]
  assert.equal(candidate.key, 0); assert.equal(candidate.published_release_id, '90071992547409931234'); assert.equal('release_options' in candidate, false)
  assert.equal(records.taskCaseLeaf([8, 0]), 0); assert.equal(records.taskCaseLeaf(null), '')
})
test('rule rows use automation type plus case ID and retain finite summary counts', () => {
  const item = { case_id: 0, case_name: 'Example', case_type: 0, project_product_id: 0, module_id: null, module_full_path: '', scenario_tags: [], publication_status: 'published' }
  const result = records.parseRuleCases(ok({ items: [item, { ...item, case_type: 1 }], count: 2, summary: { selected_count: 2, omit: 'unused' } }))
  assert.deepEqual(result.rows.map(row => row.row_key), ['0:0', '1:0']); assert.equal(result.selectedCount, 2)
  assert.throws(() => records.parseRuleCases(ok({ items: [item, item], count: 2, summary: { selected_count: 2 } })))
})
test('actual page binding uses a fixed payload, prevents duplicates and preserves selection after failure', async t => {
  const pending = deferred(); let fail = true
  const h = page({ postSystemTasksRunCase: () => fail ? pending.promise : Promise.resolve(ok({ created_count: 1, updated_count: 0, skipped_count: 0 })) }); t.after(h.close)
  h.addSelectionKeys.value = [4]; const request = h.onAddSelectedCases()
  assert.equal(h.addLoading.value, true); await h.onAddSelectedCases(); assert.equal(h.calls.filter(([name]) => name === 'postSystemTasksRunCase').length, 1)
  assert.deepEqual(h.calls[0], ['postSystemTasksRunCase', { type: 1, task: 1, api_case: [4] }])
  h.addSelectionKeys.value.push(99); assert.deepEqual(h.calls[0][1].api_case, [4])
  pending.reject(Error('network')); await request; assert.equal(h.addLoading.value, false); assert.deepEqual(h.addSelectionKeys.value, [4,99]); assert.match(h.bindingError.value, /失败/)
  fail = false; h.addSelectionKeys.value = [4]; await h.onAddSelectedCases(); assert.deepEqual(h.addSelectionKeys.value, []); assert.equal(h.bindingError.value, '')
})
test('binding success is separate from follow-up list read failure', async t => {
  const h = page({ getSystemTasksRunCase: () => Promise.reject(Error('read failure')) }); t.after(h.close)
  h.addSelectionKeys.value = [4]; await h.onAddSelectedCases()
  assert.equal(h.bindingError.value, ''); assert.match(h.boundError.value, /失败/); assert.match(h.boundCaseKeysError.value, /失败/); assert.equal(h.addLoading.value, false)
  assert.equal(h.messages.filter(([name]) => name === 'success').length, 1)
})
test('batch delete freezes checked IDs and remains open on failure before explicit retry', async t => {
  let fail = true
  const h = page({ deleteSystemTasksRunCase: () => fail ? Promise.reject(Error('network')) : Promise.resolve(ok(null)) }); t.after(h.close)
  h.selectedRowKeys.value = ['0','2']; h.onDelete(null); const dialog = h.confirms[0]
  h.selectedRowKeys.value = ['3']
  assert.equal(await dialog.options.onBeforeOk(), false); assert.equal(dialog.closed, false); assert.deepEqual(h.calls[0], ['deleteSystemTasksRunCase', ['0','2']])
  assert.deepEqual(h.selectedRowKeys.value, ['3']); assert.equal(h.deleteLoading.value, false); assert.match(h.deletionError.value, /失败/)
  fail = false; assert.equal(await dialog.options.onBeforeOk(), true); assert.equal(dialog.closed, true); assert.deepEqual(h.selectedRowKeys.value, ['3'])
})
test('cancelled deletion retains physical write lock until settlement and cannot close a later dialog', async t => {
  const pending = deferred(), h = page({ deleteSystemTasksRunCase: () => pending.promise }); t.after(h.close)
  h.onDelete({ id: 0 }); const dialog = h.confirms[0], request = dialog.options.onBeforeOk()
  dialog.options.onCancel(); assert.equal(h.writeBusy.value, true); h.onDelete({ id: 2 }); assert.equal(h.confirms.length, 1)
  pending.resolve(ok(null)); assert.equal(await request, false); assert.equal(h.writeBusy.value, false); assert.equal(h.messages.length, 0)
  h.onDelete({ id: 2 }); assert.equal(h.confirms.length, 2); assert.equal(h.confirms[1].closed, false)
})
test('bound read keeps last good typed rows on failure and corrects out-of-range pages', async t => {
  let fail = true
  const h = page({ getSystemTasksRunCase: () => fail ? Promise.reject(Error('network')) : Promise.resolve(ok([{ id: 0, type: 1, api_case: { name: 'New' } }])) }); t.after(h.close)
  h.boundRows.value = records.parseBoundCases(ok([{ id: 2, type: 0, ui_case: { name: 'Previous' } }])).rows
  await h.doRefresh(); assert.equal(h.boundRows.value[0].case_name, 'Previous'); assert.match(h.boundError.value, /失败/); assert.equal(h.boundLoading.value, false)
  fail = false; h.pagination.page = 8; await h.doRefresh(); assert.equal(h.pagination.page, 1); assert.equal(h.boundRows.value[0].id, 0); assert.equal(h.boundError.value, '')
  assert.equal(h.calls.filter(([name]) => name === 'getSystemTasksRunCase').length, 3)
})
test('late bound responses cannot overwrite newer queries or clear their loading', async t => {
  const a = deferred(), b = deferred(); let request = 0
  const h = page({ getSystemTasksRunCase: () => request++ === 0 ? a.promise : b.promise }); t.after(h.close)
  const old = h.doRefresh(), current = h.doRefresh(); a.resolve(ok([{ id: 0, type: 1, api_case: { name: 'Old' } }]))
  await old; assert.equal(h.boundLoading.value, true); assert.deepEqual(h.boundRows.value, [])
  b.resolve(ok([{ id: 2, type: 0, ui_case: { name: 'New' } }])); await current; assert.equal(h.boundRows.value[0].case_name, 'New'); assert.equal(h.boundLoading.value, false)
})
test('candidate pagination remains local and failed bound-key reads prevent adding stale candidates', async t => {
  const h = page({ getSystemTasksRunCase: () => Promise.reject(Error('network')) }); t.after(h.close)
  h.candidatePagination.page = 2; h.candidatePagination.onChange(); assert.equal(h.calls.length, 0); assert.equal(h.candidateLoading.value, false)
  await h.loadBoundCaseKeys(); assert.match(h.boundCaseKeysError.value, /失败/); assert.equal(h.isCandidateSelectable(h.candidateCases.value[0]), false)
})
test('local pagination cannot clear a pending candidate request or enable stale selections', async t => {
  const pending = deferred(), h = page({ getSystemTasksTypeCaseName: () => pending.promise }); t.after(h.close)
  const request = h.loadCandidateCases(false); h.candidatePagination.onChange()
  assert.equal(h.candidateLoading.value, true); assert.equal(h.isCandidateSelectable(h.candidateCases.value[0]), false)
  pending.resolve(ok([])); await request; assert.equal(h.candidateLoading.value, false)
})
test('rule search resets pagination, trims text and preserves zero and collection filters', async t => {
  const item = { case_id: 0, case_name: 'Example', case_type: 0, project_product_id: 0, module_id: 0, module_full_path: 'Example/Module', scenario_tags: [], publication_status: 'published' }
  const h = page({ getSystemTaskSelectionCases: () => Promise.resolve(ok({ items: [item], count: 1, summary: { selected_count: 1 } })) }); t.after(h.close)
  h.taskConfig.value.execution_scope = 'module_full'; h.rulePagination.page = 8
  Object.assign(h.ruleFilter, { caseId: ' 0 ', caseName: ' Example ', caseTypes: [0,2], moduleId: 0, scenarioTags: ['routine_regression'] })
  await h.loadRuleCases(true)
  assert.deepEqual(h.calls[0][1], { task_id: 1, case_id: '0', case_name: 'Example', case_types: '0,2', module_id: 0, scenario_tags: 'routine_regression', page: 1, pageSize: 20 })
  assert.equal(h.ruleCases.value[0].row_key, '0:0'); assert.equal(h.ruleSelectedCount.value, 1); assert.equal(h.ruleLoading.value, false)
})
test('rule failure retains data and an older response cannot replace the latest result', async t => {
  const pending = deferred(); let call = 0
  const h = page({ getSystemTaskSelectionCases: () => call++ === 0 ? pending.promise : Promise.reject(Error('network')) }); t.after(h.close)
  h.taskConfig.value.execution_scope = 'module_full'; h.ruleCases.value = [{ row_key: '0:2', case_id: 2 }]
  const old = h.loadRuleCases(); await h.loadRuleCases(); const error = h.ruleError.value
  pending.resolve(ok({ items: [], count: 0, summary: { selected_count: 0 } })); await old
  assert.equal(h.ruleCases.value[0].case_id, 2); assert.match(error, /失败/); assert.equal(h.ruleError.value, error); assert.equal(h.ruleLoading.value, false)
})
test('owner and module options have independent loading, failures, retry and product context guards', async t => {
  const pending = deferred(); let fail = true
  const h = page({ getUserName: () => fail ? Promise.reject(Error('network')) : Promise.resolve(ok([{ key: 0, title: 'Example' }])), getPytestProductName: () => pending.promise }); t.after(h.close)
  h.boundFilter.type = 2; h.boundFilter.projectProduct = 0
  const modules = h.loadBoundPytestModules(0); await h.getNickName()
  assert.equal(h.boundModuleLoading.value, true); assert.equal(h.ownerLoading.value, false); assert.match(h.ownerError.value, /失败/)
  fail = false; await h.getNickName(); assert.equal(h.ownerOptions.value[0].key, 0); assert.equal(h.ownerError.value, '')
  h.boundFilter.projectProduct = 2; pending.resolve(ok([{ key: 0, title: 'Old product module' }])); await modules
  assert.deepEqual(h.boundModuleOptions.value, []); assert.equal(h.boundModuleLoading.value, false)
})
test('each identity dimension invalidates old reads, selection and confirmation without authorizing writes in the frontend', async t => {
  for (const change of [h => h.user.userId++, h => h.user.roleId++, h => h.user.token = 'example-new-session', h => h.user.selected_environment++,
    h => h.permission.permissionKeys = ['timing.tasks:change'], h => h.route.fullPath = '/timing/case?id=1&name=Changed', h => h.props.taskId = 2]) {
    const pending = deferred(), h = page({ getSystemTasksRunCase: () => pending.promise })
    try {
      h.selectedRowKeys.value = ['1']; h.addSelectionKeys.value = [4]; h.onDelete({ id: 1 }); const dialog = h.confirms[0]
      const request = h.doRefresh(); change(h)
      assert.equal(dialog.closed, true); assert.deepEqual(h.selectedRowKeys.value, []); assert.deepEqual(h.addSelectionKeys.value, []); assert.equal(h.taskConfig.value, null)
      pending.resolve(ok([{ id: 1, type: 1, api_case: { name: 'Old identity' } }])); await request
      assert.deepEqual(h.boundRows.value, []); assert.equal(h.boundLoading.value, false); assert.equal(await dialog.options.onBeforeOk(), false)
    } finally { h.close() }
  }
})
test('background pause ignores old reads and automatically resumes without resetting filters', async t => {
  const pending = deferred(); let delayed = false
  const h = page({ getSystemTasksRunCase: params => params.case_ids_only ? Promise.resolve(ok([])) : delayed ? pending.promise : Promise.resolve(ok([{ id: 3, type: 1, api_case: { name: 'Current' } }])) }); t.after(h.close)
  h.mount(); await flush(); await flush(); h.boundFilter.caseName = 'Keep this filter'; delayed = true
  const request = h.doRefresh(); h.visibility('hidden'); pending.resolve(ok([{ id: 4, type: 1, api_case: { name: 'Obsolete' } }])); await request
  assert.equal(h.boundRows.value[0].case_name, 'Current'); assert.equal(h.boundLoading.value, false)
  const count = h.calls.length; await h.doRefresh(); assert.equal(h.calls.length, count)
  delayed = false; h.visibility('visible'); await flush(); await flush()
  assert.ok(h.calls.length > count); assert.equal(h.boundFilter.caseName, 'Keep this filter'); assert.equal(h.boundRows.value[0].case_name, 'Current')
})
test('KeepAlive pauses requests and returns to a single initialization without replaying writes', async t => {
  const h = page(); t.after(h.close); h.mount(); await flush(); await flush()
  const count = h.calls.filter(([name]) => name === 'getSystemTasks').length
  h.callbacks.deactivate.forEach(fn => fn()); await h.doRefresh(); assert.equal(h.calls.filter(([name]) => name === 'getSystemTasks').length, count)
  h.callbacks.activate.forEach(fn => fn()); h.callbacks.activate.forEach(fn => fn()); await flush(); await flush()
  assert.equal(h.calls.filter(([name]) => name === 'getSystemTasks').length, count + 1)
  assert.equal(h.calls.filter(([name]) => name === 'postSystemTasksRunCase' || name === 'deleteSystemTasksRunCase').length, 0)
})
test('identity change during binding keeps the physical lock, suppresses old feedback and reloads the new task only after settlement', async t => {
  const pending = deferred(), h = page({ postSystemTasksRunCase: () => pending.promise, getSystemTasks: params => Promise.resolve(ok([row({ id: params.id })])) }); t.after(h.close)
  h.mount(); await flush(); await flush(); h.candidateCases.value = [{ key: 4, title: 'Example', published_release_id: 8 }]; h.addSelectionKeys.value = [4]
  const request = h.onAddSelectedCases(), reads = h.calls.filter(([name]) => name === 'getSystemTasks').length
  h.props.taskId = 2; assert.equal(h.writeBusy.value, true); assert.equal(h.taskConfig.value, null)
  await h.initializeTaskCases(); assert.equal(h.calls.filter(([name]) => name === 'getSystemTasks').length, reads)
  pending.resolve(ok({ created_count: 1, updated_count: 0, skipped_count: 0 })); await request; await flush(); await flush()
  assert.equal(h.writeBusy.value, false); assert.equal(h.taskConfig.value.id, 2); assert.equal(h.messages.filter(([name]) => name === 'success').length, 0)
  assert.equal(h.calls.filter(([name]) => name === 'postSystemTasksRunCase').length, 1)
})
test('background closes a delete confirmation and prevents its stale callback from sending a request', async t => {
  const h = page(); t.after(h.close); h.mount(); await flush(); await flush()
  h.onDelete({ id: 1 }); const dialog = h.confirms[0]; h.visibility('hidden')
  assert.equal(dialog.closed, true); assert.equal(await dialog.options.onBeforeOk(), false); assert.equal(h.calls.filter(([name]) => name === 'deleteSystemTasksRunCase').length, 0)
})
test('unmounted page ignores a successful late write and cannot start another read or write', async () => {
  const pending = deferred(), h = page({ postSystemTasksRunCase: () => pending.promise })
  h.addSelectionKeys.value = [4]; const request = h.onAddSelectedCases(); h.close()
  pending.resolve(ok({ created_count: 1, updated_count: 0, skipped_count: 0 })); await request
  assert.equal(h.messages.length, 0); assert.equal(h.addLoading.value, false)
  const count = h.calls.length; await h.doRefresh(); await h.onAddSelectedCases(); assert.equal(h.calls.length, count)
})
test('enum failure exposes its own retry and releases loading independently', async t => {
  let fail = true; const h = page({}, async () => { if (fail) throw Error('network') }); t.after(h.close)
  await h.loadEnums(); assert.match(h.enumError.value, /失败/); assert.equal(h.enumLoading.value, false)
  fail = false; await h.loadEnums(); assert.equal(h.enumError.value, ''); assert.equal(h.enumLoading.value, false)
})

test('task config is a finite copy that preserves zero IDs and parent/product display fields', () => {
  const original = row({ extra: 'omit' }), config = parseTaskCaseConfig(ok([original]), 0)
  assert.equal(config.id, 0); assert.equal(config.project_product.id, 0); assert.equal(config.module.id, 0)
  assert.equal(config.project_product.project.name, 'Example project'); assert.equal(config.module.full_path, 'Example/Module')
  assert.equal('extra' in config, false)
  config.case_types.push(2); config.project_product.name = 'Changed'; config.execution_scenes.push('changed')
  assert.deepEqual(original.case_types, [0, 1]); assert.equal(original.project_product.name, 'Example product'); assert.deepEqual(original.execution_scenes, ['regression'])
})
test('task config accepts existing list, item list and single-record envelopes without coercing long IDs', () => {
  const id = '90071992547409931234'
  for (const data of [[row({ id })], { items: [row({ id })] }, row({ id })]) assert.equal(parseTaskCaseConfig(ok(data), id).id, id)
  assert.equal(parseTaskCaseConfig(ok([]), 1), null); assert.equal(parseTaskCaseConfig(ok({ items: [] }), 1), null)
  assert.equal(parseTaskCaseConfig(ok([row({ module: null, project_product: null })]), 0).module, null)
})
test('failed, malformed, unsafe and mismatched configuration responses remain errors', () => {
  for (const response of [null, { code: 403, data: [] }, ok(null), ok([row({ id: 1 })]), ok([row({ id: Number.MAX_SAFE_INTEGER + 1 })]),
    ok([row({ case_types: ['1'] })]), ok([row({ execution_scenes: {} })]), ok([row({ module: { id: 2, full_path: {} } })])]) {
    assert.throws(() => parseTaskCaseConfig(response, 0))
  }
})
test('task config loading preserves zero ownership IDs and adjusts a disallowed case type', async () => {
  let query
  const h = configReader(async params => { query = params; return ok([row({ case_types: [0] })]) })
  assert.equal(await h.load(), true); assert.deepEqual(query, { id: 0, page: 1, pageSize: 1 })
  assert.equal(h.taskConfigLoading.value, false); assert.equal(h.taskConfigError.value, '')
  assert.equal(h.addForm.type, 0); assert.equal(h.addForm.projectProduct, 0); assert.equal(h.addForm.module, 0)
  assert.equal(h.boundFilter.projectProduct, 0); assert.equal(h.boundFilter.module, 0)
})
test('missing task ID stops initialization without a request and releases loading', async () => {
  let calls = 0; const h = configReader(async () => { calls++; return ok([]) }); h.currentTaskId.value = ''
  assert.equal(await h.load(), false); assert.equal(calls, 0); assert.match(h.taskConfigError.value, /缺少/); assert.equal(h.taskConfigLoading.value, false)
})
test('failed task reads retain last valid configuration and allow explicit retry', async () => {
  let fail = true; const h = configReader(async () => { if (fail) throw Error('network'); return ok([row()]) })
  h.taskConfig.value = row()
  assert.equal(await h.load(), false); assert.equal(h.taskConfig.value.name, 'Example task'); assert.match(h.taskConfigError.value, /失败/); assert.equal(h.taskConfigLoading.value, false)
  fail = false; assert.equal(await h.load(), true); assert.equal(h.taskConfigError.value, '')
})
test('a late task configuration cannot overwrite a newer task or clear its loading', async () => {
  const first = deferred(), second = deferred(), h = configReader(params => params.id === 0 ? first.promise : second.promise)
  const a = h.load(); h.currentTaskId.value = 2; const b = h.load()
  first.resolve(ok([row()])); assert.equal(await a, false); assert.equal(h.taskConfig.value, null); assert.equal(h.taskConfigLoading.value, true)
  second.resolve(ok([row({ id: 2, name: 'Second' })])); assert.equal(await b, true); assert.equal(h.taskConfig.value.name, 'Second'); assert.equal(h.taskConfigLoading.value, false)
})
test('rejected obsolete reads do not replace current configuration errors', async () => {
  const pending = deferred(), h = configReader(params => params.id === 0 ? pending.promise : Promise.resolve(ok([])))
  const old = h.load(); h.currentTaskId.value = 2; await h.load(); const error = h.taskConfigError.value
  pending.reject(Error('old failure')); await old; assert.equal(h.taskConfigError.value, error); assert.equal(h.taskConfigLoading.value, false)
})
test('configuration contains real static columns without creating form or table state at module import', () => {
  const config = actual(path.join(base, 'config.ts'), { '@/hooks/table': {
    useTable() { throw Error('Unexpected page state at module scope') }, useTableIndexColumn: () => ({ key: 'index', width: 100, align: 'center' }), useTableColumn: value => value,
  } })
  assert.equal('formItems' in config, false); assert.equal(config.tableColumns.find(column => column.key === 'actions').width, 160)
  assert.equal(config.candidateColumns[0].width, 54); assert.equal(config.tableColumns[0].align, 'center')
})
test('actual page initializes manual panels even when enum loading fails', async t => {
  const h = page({}, async () => { throw Error('enum unavailable') }); t.after(h.close)
  h.taskConfig.value = null; h.mount(); await flush(); await flush(); const calls = h.calls
  assert.equal(h.taskConfig.value.id, 1); assert.equal(h.taskConfigLoading.value, false); assert.equal(h.taskConfigError.value, '')
  assert.equal(calls.filter(([name]) => name === 'getSystemTasksRunCase').length, 2)
  assert.equal(calls.filter(([name]) => name === 'getSystemTasksTypeCaseName').length, 1)
  assert.equal(calls.filter(([name]) => name === 'getUserName').length, 1)
})
test('failed task configuration stops downstream candidate and binding requests', async t => {
  const h = page({ getSystemTasks: () => Promise.reject(Error('network')) }); t.after(h.close)
  await h.initializeTaskCases(); assert.deepEqual(h.calls.map(([name]) => name), ['getSystemTasks']); assert.match(h.taskConfigError.value, /失败/)
})
test('task binding page script, template and Less compile', async () => {
  const { descriptor, errors } = parse(readFileSync(filename, 'utf8')); assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'task-case86' })
  const template = compileTemplate({ source: descriptor.template.content, filename, id: 'task-case86', compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, [])
  for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ source: style.content, filename, id: 'task-case86', preprocessLang: style.lang, scoped: true })).errors, [])
})
