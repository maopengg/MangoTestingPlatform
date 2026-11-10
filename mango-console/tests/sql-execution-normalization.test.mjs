import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/system/sql-execution')
const record = (values = {}) => ({ id: 0, request_id: 'example-request', datasource_type_name: 'MySQL', datasource_type: 0, create_time: '2026-11-09 10:00:00',
  project_product_name: 'Example', datasource_alias_name: 'Example alias', database_name: 'example', test_env: 0, test_env_name: 'Example environment',
  source_type: 'data_factory', source_id: 0, source_stage: 'execute', source_detail: { values: [false, 0] }, status: 'success', duration_ms: '0.00',
  is_slow: false, row_count: 0, affected_rows: -1, sql_text: 'SELECT 1', sql_parameters: [0, false], result_preview: '0', result_truncated: false, error_message: null, ...values })
const ok = (data, totalSize = 1) => ({ code: 200, data, totalSize })
function options() { return { datasource_type_options: [{ key: 'unrecorded', title: '历史未记录' }], project_product_options: [],
  source_type_options: [{ key: 'data_factory', title: '数据工厂' }], source_stage_options: [], environment_options: [{ key: 0, title: 'Example environment' }],
  datasource_alias_options: [], status_options: [], slow_options: [{ key: false, title: '正常' }, { key: true, title: '慢执行' }] } }
function actualModule(filename, dependencies) {
  const exports = {}
  const source = ts.transpileModule(readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  new Function('exports', 'require', source)(exports, name => {
    if (name in dependencies) return dependencies[name]
    { if (['@/utils/load-error', '@/utils/api-response'].includes(name)) return loadFeedbackModule(name); throw Error('Unexpected dependency: ' + name) }
  })
  return exports
}
function setup(overrides = {}) {
  const priorDocument = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, calls = [], messages = []
  const route = vue.reactive({ path: '/system/sql-execution/index', fullPath: '/system/sql-execution/index' })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'example', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: [] })
  const h = harness('index', 'rows,options,conditionItems,pagination,listLoading,optionsLoading,listError,optionsError,doRefresh,onSearch,onResetSearch,loadOptions,openDetail,closeDetail,detailVisible,selectedRecord,buildQuery,optionTitle,statusText,formatDuration', {
    base, api: { getSqlExecutionList: query => { calls.push(structuredClone(query)); return overrides.read?.(query) ?? Promise.resolve(ok([record()])) },
      getSqlExecutionOptions: () => overrides.options?.() ?? Promise.resolve(ok(options())) }, modules: {
      vue: { ...vue, onMounted: f => callbacks.mount.push(f), onActivated: f => callbacks.activate.push(f), onDeactivated: f => callbacks.deactivate.push(f), onBeforeUnmount: f => callbacks.unmount.push(f) },
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
      '@/hooks/table': actualModule('src/hooks/table.ts', { vue }), '@/hooks/use-latest-request': actualModule('src/hooks/use-latest-request.ts', {}),
      '@/store/modules/get-enum': { useEnum: () => ({ colors: ['blue'], getEnum: overrides.enums || (async () => {}) }) },
      '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'warning', 'error'].map(key => [key, value => messages.push([key, value])])) },
    },
  })
  return { ...h, route, user, permission, callbacks, calls, messages,
    mount() { callbacks.mount.forEach(f => f()); callbacks.activate.forEach(f => f()) },
    visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { callbacks.unmount.forEach(f => f()); h.close(); globalThis.document = priorDocument },
  }
}

test('audit DTOs preserve zero, long IDs, decimal strings, false and driver row counts without sharing JSON', t => {
  const h = setup(); t.after(h.close); const m = h.load('execution-records.ts'), raw = record({ obsolete: 'omit' })
  const copied = m.copyExecutionRecord(raw)
  assert.equal(copied.id, 0); assert.equal(copied.source_id, 0); assert.equal(copied.test_env, 0); assert.equal(copied.duration_ms, '0.00')
  assert.equal(copied.is_slow, false); assert.equal(copied.affected_rows, -1); assert.equal('obsolete' in copied, false)
  copied.source_detail.values[0] = true; assert.equal(raw.source_detail.values[0], false)
  const long = m.copyExecutionRecord(record({ id: '90071992547409931234', source_id: null, test_env: null, project_product_name: undefined, datasource_alias_name: undefined }))
  assert.equal(long.id, '90071992547409931234'); assert.equal(long.project_product_name, ''); assert.equal(long.source_id, null)
  assert.equal(h.formatDuration(0), '0.00 ms'); assert.equal(h.formatDuration(null), '-')
})

test('malformed lists and flags are rejected rather than displayed as successful empty data', t => {
  const h = setup(); t.after(h.close); const m = h.load('execution-records.ts')
  for (const value of [{ code: 403, data: [record()], totalSize: 1 }, ok({}), ok([record()], '1'), ok([record(), record()], 2),
    ok([record({ is_slow: 'false' })]), ok([record({ result_truncated: 0 })]), ok([record({ duration_ms: false })]),
    ok([record({ row_count: null })]), ok([record({ id: Number.MAX_SAFE_INTEGER + 1 })])]) assert.throws(() => m.parseExecutionList(value))
  assert.deepEqual(m.parseExecutionList(ok([], 0)), { rows: [], total: 0 })
})

test('finite options preserve false and zero, omit unrelated fields and reject malformed groups', t => {
  const h = setup(); t.after(h.close); const m = h.load('execution-records.ts'), raw = options()
  const copied = m.parseAuditOptions(ok({ ...raw, unrelated: [] }))
  assert.equal(copied.slow_options[0].key, false); assert.equal(copied.environment_options[0].key, 0); assert.equal('unrelated' in copied, false)
  copied.environment_options[0].title = 'new'; assert.notEqual(raw.environment_options[0].title, 'new')
  assert.throws(() => m.parseAuditOptions(ok({}))); assert.throws(() => m.parseAuditOptions(ok({ ...raw, slow_options: [{ key: {}, title: 'bad' }] })))
})

test('search factories are independent and all supported select fields retain multi-select protocol', t => {
  const h = setup(); t.after(h.close); const factory = h.load('config.ts').createConditionItems
  const a = factory(), b = factory()
  a.find(item => item.key === 'status').value.push('running'); assert.deepEqual(b.find(item => item.key === 'status').value, [])
  for (const item of a.filter(item => item.type === 'select')) { assert.equal(item.multiple, true); assert.equal(item.searchOperator, 'in') }
  const id = a.find(item => item.key === 'id'); id.value = '5574、5577'; assert.equal(id.value, '5574,5577'); assert.equal(b.find(item => item.key === 'id').value, '')
})

test('queries preserve multi-select false/zero, large IDs and ranges while omitting empty and extra fields', t => {
  const h = setup(); t.after(h.close)
  for (const [key, value] of Object.entries({ id: '90071992547409931234,5574', test_env: [0], is_slow: [false], datasource_type: ['unrecorded'], duration_min: '0', create_time: ['2026-11-01 00:00:00', '2026-11-09 23:59:59'] })) {
    h.conditionItems.find(item => item.key === key).value = value
  }
  const query = h.buildQuery()
  assert.equal(query.id__in, '90071992547409931234,5574'); assert.equal('id' in query, false)
  assert.equal(query.test_env__in, '0'); assert.equal(query.is_slow__in, 'false'); assert.equal(query.datasource_type__in, 'unrecorded')
  assert.equal(query.duration_min, '0'); assert.equal(query.create_time_start, '2026-11-01 00:00:00'); assert.equal('create_time' in query, false)
  const m = h.load('execution-records.ts'); assert.deepEqual(m.executionQuery({ is_slow: false, test_env: 0, unrelated: 'omit', sql_keyword: '' }), { test_env: 0, is_slow: false })
})

test('list starts independently of options and identical requests coalesce', async t => {
  const list = deferred(), lookup = deferred(), h = setup({ read: () => list.promise, options: () => lookup.promise }); t.after(h.close)
  h.mount(); const first = h.doRefresh(); assert.equal(h.doRefresh(), first); await flush()
  assert.equal(h.calls.length, 1); assert.equal(h.listLoading.value, true); assert.equal(h.optionsLoading.value, true)
  list.resolve(ok([record()])); await first; assert.equal(h.rows.value.length, 1); assert.equal(h.listLoading.value, false)
  assert.equal(h.optionsLoading.value, true); lookup.resolve(ok(options())); await flush(); assert.equal(h.optionsLoading.value, false)
})

test('list failure keeps prior same-context rows and allows retry', async t => {
  let n = 0; const h = setup({ read: async () => { n++; if (n === 2) throw Error('offline'); if (n === 3) return ok({}); return ok([record()]) } }); t.after(h.close)
  h.mount(); await flush(); await h.doRefresh(); assert.match(h.listError.value, /重试/); assert.equal(h.rows.value.length, 1)
  await h.doRefresh(); assert.match(h.listError.value, /重试/); await h.doRefresh(); assert.equal(h.listError.value, ''); assert.equal(h.listLoading.value, false)
})

test('new search resets page and late old responses cannot replace it', async t => {
  const first = deferred(), second = deferred(); let n = 0
  const h = setup({ read: () => ++n === 1 ? first.promise : second.promise }); t.after(h.close)
  h.mount(); await flush(); h.pagination.page = 3; h.conditionItems.find(item => item.key === 'test_env').value = [0]
  const latest = h.onSearch(); await flush(); assert.equal(h.calls.at(-1).page, 1); assert.equal(h.calls.at(-1).test_env__in, '0')
  second.resolve(ok([record({ id: 2 })])); await latest; first.resolve(ok([record({ id: 1 })])); await flush()
  assert.equal(h.rows.value[0].id, 2); assert.equal(h.pagination.page, 1); assert.equal(h.listLoading.value, false)
})

test('pagination sends page/pageSize, and a shrinking list clamps and refetches the last page', async t => {
  const h = setup(); t.after(h.close); h.pagination.page = 10; h.pagination.pageSize = 50; h.mount(); await flush()
  assert.deepEqual(h.calls.map(query => query.page), [10, 1]); assert.equal(h.calls.at(-1).pageSize, 50); assert.equal('size' in h.calls.at(-1), false)
  assert.equal(h.pagination.pageCount, 1); assert.equal(h.pagination.page, 1)
})

test('reset clears all selections and custom ID state before requesting page one', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush()
  for (const item of h.conditionItems) item.value = item.type === 'select' ? [0] : item.type === 'range' ? ['a', 'b'] : '1'
  h.pagination.page = 4; await h.onResetSearch()
  assert.deepEqual(h.calls.at(-1), { page: 1, pageSize: 20 })
  for (const item of h.conditionItems) assert.deepEqual(item.value, item.type === 'range' || item.multiple ? [] : '')
})

test('read-only details are independent snapshots, close cleanly and reopen from the current row', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush()
  const row = h.rows.value[0]; h.openDetail(row); assert.equal(h.detailVisible.value, true)
  h.selectedRecord.value.source_detail.values[0] = true; assert.equal(row.source_detail.values[0], false)
  h.closeDetail(); assert.equal(h.selectedRecord.value, null); assert.equal(h.detailVisible.value, false)
  row.result_preview = 'new preview'; h.openDetail(row); assert.equal(h.selectedRecord.value.result_preview, 'new preview')
})

test('options and enum failures do not discard records or valid options and permit retry', async t => {
  let n = 0; const h = setup({ options: async () => { if (++n === 1) throw Error('offline'); return ok(options()) }, enums: async () => { if (n === 2) throw Error('offline') } }); t.after(h.close)
  h.mount(); await flush(); assert.equal(h.rows.value.length, 1); assert.match(h.optionsError.value, /重试/)
  await h.loadOptions(); assert.match(h.optionsError.value, /枚举/); assert.equal(h.options.value.slow_options[0].key, false)
  await h.loadOptions(); assert.equal(h.optionsError.value, ''); assert.equal(h.optionTitle('test_env', 0), 'Example environment')
})

test('identity changes clear scopes and details, reset search, and ignore old reads', async t => {
  const pending = deferred(); let n = 0
  const h = setup({ read: () => ++n === 2 ? pending.promise : Promise.resolve(ok([record({ id: n })])) }); t.after(h.close)
  h.mount(); await flush(); h.openDetail(h.rows.value[0]); h.conditionItems.find(item => item.key === 'test_env').value = [0]
  const old = h.onSearch(); await flush(); h.user.roleId++
  assert.equal(h.rows.value.length, 0); assert.equal(h.detailVisible.value, false); assert.equal(h.selectedRecord.value, null)
  assert.deepEqual(h.conditionItems.find(item => item.key === 'test_env').value, []); await flush()
  pending.resolve(ok([record({ id: 99 })])); await old; assert.equal(h.rows.value[0].id, 3)
})

test('background and KeepAlive pause old requests and restore reads without reopening details', async t => {
  for (const pause of [h => h.visibility('hidden'), h => h.callbacks.deactivate.forEach(f => f())]) {
    const pending = deferred(); let n = 0; const h = setup({ read: () => ++n === 2 ? pending.promise : Promise.resolve(ok([record({ id: n })])) })
    try {
      h.mount(); await flush(); h.openDetail(h.rows.value[0]); const old = h.doRefresh(); await flush(); pause(h)
      pending.resolve(ok([record({ id: 99 })])); await old; assert.equal(h.rows.value[0].id, 1); assert.equal(h.detailVisible.value, false)
      h.visibility('visible'); h.callbacks.activate.forEach(f => f()); await flush(); assert.equal(h.rows.value[0].id, 3)
      assert.equal(h.detailVisible.value, false); assert.equal(h.listLoading.value, false)
    } finally { h.close() }
  }
})

test('execution page compiles with typed filters, readonly JSON and token styles', async () => {
  const filename = path.join(base, 'index.vue'), { descriptor, errors } = parse(readFileSync(filename, 'utf8')); assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'sql-execution' })
  assert.deepEqual(compileTemplate({ filename, id: 'sql-execution', source: descriptor.template.content, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ filename, id: 'sql-execution', source: style.content, scoped: style.scoped })).errors, [])
})

test('user, token, environment, permission and query changes invalidate prior list contexts', async () => {
  for (const change of [h => h.user.userId++, h => h.user.token = 'next-example', h => h.user.selected_environment = 1,
    h => h.permission.permissionKeys = ['example:read'], h => h.route.fullPath += '?example=1']) {
    const pending = deferred(); let n = 0
    const h = setup({ read: () => ++n === 2 ? pending.promise : Promise.resolve(ok([record({ id: n })])) })
    try {
      h.mount(); await flush(); const old = h.doRefresh(); await flush(); change(h)
      assert.equal(h.rows.value.length, 0); await flush(); pending.resolve(ok([record({ id: 99 })])); await old
      assert.equal(h.rows.value[0].id, 3)
    } finally { h.close() }
  }
})

test('late option responses cannot replace a new role scope', async t => {
  const pending = deferred(); let n = 0
  const h = setup({ options: () => ++n === 1 ? pending.promise : Promise.resolve(ok({ ...options(), environment_options: [{ key: 0, title: 'New scope' }] })) }); t.after(h.close)
  h.mount(); await flush(); h.user.roleId++; await flush()
  pending.resolve(ok({ ...options(), environment_options: [{ key: 0, title: 'Old scope' }] })); await flush()
  assert.equal(h.optionTitle('test_env', 0), 'New scope'); assert.equal(h.optionsLoading.value, false)
})

test('invalid filters stay local and correction retries without retaining an error', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush()
  const field = h.conditionItems.find(item => item.key === 'duration_min')
  field.value = Infinity; await h.onSearch(); assert.equal(h.calls.length, 1); assert.match(h.listError.value, /搜索条件/)
  assert.equal(h.listLoading.value, false); field.value = '0'; await h.onSearch()
  assert.equal(h.calls.at(-1).duration_min, '0'); assert.equal(h.listError.value, '')
  const m = h.load('execution-records.ts'); assert.throws(() => m.executionQuery({ create_time: {} }))
})

test('unmount and leaving the route discard pending reads without reopening details', async t => {
  const pending = deferred(); let n = 0
  const h = setup({ read: () => ++n === 2 ? pending.promise : Promise.resolve(ok([record()])) }); t.after(h.close)
  h.mount(); await flush(); h.openDetail(h.rows.value[0]); const old = h.doRefresh(); await flush()
  h.route.path = '/other'; h.route.fullPath = '/other'; h.callbacks.unmount.forEach(f => f())
  pending.resolve(ok([record({ id: 99 })])); await old
  assert.equal(h.detailVisible.value, false); assert.equal(h.selectedRecord.value, null); assert.equal(h.rows.value.length, 0)
})
