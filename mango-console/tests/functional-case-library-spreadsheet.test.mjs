import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import * as XLSX from 'xlsx'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/case-library')
const row = (name = 'Case') => ({ 用例编号: name, 用例标题: name, 项目产品ID: 2, 模块ID: 3, 负责人ID: 1, 测试类型: '[0]', 测试场景: 'Scene', 自动化状态: 'not_automated' })
function setup(options = {}) {
  const prior = globalThis.HTMLInputElement
  class Input { constructor(file = { arrayBuffer: async () => new ArrayBuffer(0) }) { this.files = [file]; this.value = 'selected' } }
  globalThis.HTMLInputElement = Input
  const hooks = { stop: [], activate: [], unmount: [] }, messages = [], writes = [], downloads = [], queries = []
  const errors = {}, state = vue.reactive({ context: 'A', available: true })
  let reloads = 0, entries = options.entries ?? [row()], rejectRead = false
  const workbook = { SheetNames: ['Cases'], Sheets: { Cases: {} } }
  const xlsx = { read() { if (rejectRead) throw Error('Invalid workbook'); return workbook }, utils: {
    sheet_to_json: () => entries,
    book_new: () => ({}),
    json_to_sheet: values => values,
    book_append_sheet: (book, sheet) => { book.sheet = sheet },
  }, writeFile: book => downloads.push(book) }
  const f = harness('CaseEditor', '', { base,
    modules: {
      vue: { ...vue, onDeactivated: fn => hooks.stop.push(fn), onActivated: fn => hooks.activate.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) },
      xlsx, '@/api/errors': errors,
      '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'error', 'warning'].map(key => [key, message => messages.push([key, message])])) },
    },
    api: {
      postManualCase: async body => { writes.push(body); return options.write ? options.write(body, writes.length) : { data: { id: writes.length } } },
      getManualCaseExport: async query => { queries.push(query); return options.read ? options.read(query) : { data: [{ ...query, case_no: 'Exported' }] } },
    },
  })
  Object.assign(errors, f.load('../../../api/errors.ts'))
  const scope = vue.effectScope()
  const transfer = scope.run(() => f.load('composables/useCaseSpreadsheet.ts').useCaseSpreadsheet({
    context: () => state.context, available: () => state.available,
    exportQuery: () => ({ page: 1, pageSize: 10000, id__in: state.context, status: 0, empty: '', nil: null, missing: undefined }),
    flush: options.flush ?? (async () => {}),
    reload: async () => { ++reloads; if (options.reload) await options.reload() },
  }))
  return { ...transfer, state, hooks, writes, downloads, queries, messages, errors, Input,
    reloads: () => reloads, mapping: f.load('spreadsheet.ts'),
    setEntries: value => { entries = value }, badRead: () => { rejectRead = true },
    cleanup: () => { hooks.unmount.forEach(fn => fn()); scope.stop(); f.close(); globalThis.HTMLInputElement = prior },
  }
}

test('spreadsheet mapping preserves zero values, narrows arrays and steps and whitelists fields', () => {
  const f = setup()
  try {
    const source = { ...row(), 优先级: 0, 资产状态: '0', 测试层级: 0, 验证类型: '0', 测试步骤JSON: '[{"action":"Act","expected":"OK","secret":"ignored"}]', update_user: 'ignored', 自动化绑定: 'display-only' }
    const actual = f.mapping.caseImportPayload(source)
    assert.equal(actual.priority, 0); assert.equal(actual.status, 0); assert.equal(actual.scenario_layer, 0); assert.equal(actual.scenario_type, 0)
    assert.deepEqual(actual.test_types, [0]); assert.deepEqual(actual.test_steps, [{ action: 'Act', expected: 'OK' }])
    assert.equal('bindings' in actual, false); assert.equal('update_user' in actual, false); assert.equal('project_product_id' in actual, false)
    assert.deepEqual(actual.scenario_tags, ['routine_regression']); assert.equal(actual.project_product, 2)
    const first = f.mapping.caseImportPayload(row()), second = f.mapping.caseImportPayload(row())
    first.scenario_tags.push('inspection'); assert.deepEqual(second.scenario_tags, ['routine_regression'])
  } finally { f.cleanup() }
})

test('export mapping preserves JSON, normalized IDs and read-only binding descriptions', () => {
  const f = setup()
  try {
    const [actual] = f.mapping.caseExportRows([{ case_no: 'Case', project_product_id: 9, project_product: { id: 2 }, module: { id: 3 }, owner: { id: 1 }, test_types: [0], test_steps: [{ action: 'Act', expected: 'OK' }], bindings: [{ automation_type: 0, automation_case_id: 7 }] }])
    assert.equal(actual['项目产品ID'], 9); assert.equal(actual['模块ID'], 3); assert.equal(actual['负责人ID'], 1)
    assert.equal(actual['测试类型'], '[0]'); assert.match(actual['自动化绑定'], /API Case ID: 7/)
    assert.equal('id' in actual, false)
  } finally { f.cleanup() }
})

test('real XLSX workbook round trip retains headers, zero enums and JSON arrays', () => {
  const f = setup()
  try {
    const data = f.mapping.caseExportRows([{ case_no: 'Case', title: 'Title', project_product_id: 2, module_id: 3, owner_id: 1,
      priority: 0, status: 0, test_types: [0], story_refs: ['STORY-1'], test_steps: [{ action: 'Act', expected: 'OK' }],
      scenario_layer: 0, scenario_type: 0, scenario_tags: ['routine_regression'], automation_status: 'not_automated', test_point: 'Scene' }])
    const book = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(book, XLSX.utils.json_to_sheet(data), 'Cases')
    const bytes = XLSX.write(book, { type: 'buffer', bookType: 'xlsx' })
    const restored = XLSX.read(bytes, { type: 'buffer' })
    const [record] = XLSX.utils.sheet_to_json(restored.Sheets.Cases, { defval: '' })
    const payload = f.mapping.caseImportPayload(record)
    assert.equal(payload.priority, 0); assert.equal(payload.status, 0)
    assert.deepEqual(payload.test_types, [0]); assert.deepEqual(payload.story_refs, ['STORY-1'])
    assert.deepEqual(payload.test_steps, [{ action: 'Act', expected: 'OK' }])
    assert.equal(payload.project_product, 2); assert.equal(payload.module, 3); assert.equal(payload.owner, 1)
  } finally { f.cleanup() }
})

test('every workbook row is parsed before any write, malformed later rows leave no partial import', async () => {
  const f = setup({ entries: [row('First'), { ...row('Invalid'), 测试步骤JSON: 'not-a-step' }] })
  try {
    const input = new f.Input(); await f.importCases({ target: input })
    assert.equal(f.writes.length, 0); assert.match(f.importProgress.value, /第 2 条数据/)
    assert.equal(f.importing.value, false); assert.equal(input.value, '')
    f.setEntries([row('Corrected')]); await f.importCases({ target: input })
    assert.equal(f.writes.length, 1); assert.equal(f.reloads(), 1)
  } finally { f.cleanup() }
})

test('double import is prevented and progress reflects only acknowledged rows', async () => {
  const pending = deferred()
  const f = setup({ entries: [row('First'), row('Second')], write: (_, count) => count === 1 ? pending.promise : Promise.resolve({}) })
  try {
    const input = new f.Input(), loading = f.importCases({ target: input }); await flush()
    await f.importCases({ target: new f.Input() })
    assert.equal(f.importing.value, true); assert.equal(f.writes.length, 1); assert.equal(f.importProgress.value, '已导入 0 / 2 条')
    pending.resolve({}); await loading
    assert.equal(f.writes.length, 2); assert.equal(f.importing.value, false); assert.match(f.importProgress.value, /成功导入 2/)
  } finally { f.cleanup() }
})

test('explicit pre-create validation failure can resume without replaying acknowledged rows', async () => {
  let rejected = false
  const f = setup({ entries: [row('First'), row('Second'), row('Third')], write: async (_, count) => {
    if (count === 2 && !rejected) { rejected = true; throw new f.errors.ApiBusinessError('Invalid scenario', 35051) }
    return {}
  } })
  try {
    await f.importCases({ target: new f.Input() })
    assert.equal(f.importRetryable.value, true); assert.match(f.importProgress.value, /已导入 1 \/ 3/)
    await f.retryImport()
    assert.deepEqual(f.writes.map(item => item.case_no), ['First', 'Second', 'Second', 'Third'])
    assert.equal(f.importRetryable.value, false); assert.match(f.importProgress.value, /成功导入 3/)
  } finally { f.cleanup() }
})

test('network and unclassified server failures do not offer unsafe replay', async () => {
  for (const business of [false, true]) {
    const f = setup({ write: async () => { throw business ? new f.errors.ApiBusinessError('Unknown failure', 300) : Error('Disconnected') } })
    try {
      await f.importCases({ target: new f.Input() })
      assert.equal(f.importRetryable.value, false); assert.match(f.importProgress.value, /提交结果未确认/)
      await f.retryImport(); await f.importCases({ target: new f.Input() }); assert.equal(f.writes.length, 1)
      f.discardImport(); assert.equal(f.importProgress.value, '')
    } finally { f.cleanup() }
  }
})

test('context changes during file reading prevent any old-context write, including A to B to A', async () => {
  const pending = deferred(), f = setup()
  try {
    const loading = f.importCases({ target: new f.Input({ arrayBuffer: () => pending.promise }) })
    f.state.context = 'B'; f.state.context = 'A'; pending.resolve(new ArrayBuffer(0)); await loading
    assert.equal(f.writes.length, 0); assert.equal(f.importProgress.value, ''); assert.equal(f.importing.value, false)
  } finally { f.cleanup() }
})

test('import drains pending inline saves and abandons writes when scope changes while waiting', async () => {
  const pending = deferred(), f = setup({ flush: () => pending.promise })
  try {
    const importing = f.importCases({ target: new f.Input() }); await flush()
    assert.equal(f.writes.length, 0); assert.equal(f.importing.value, true)
    f.state.context = 'B'; pending.resolve(); await importing
    assert.equal(f.writes.length, 0); assert.equal(f.importing.value, false)
  } finally { f.cleanup() }
})

test('a late failed write after unmount neither enables retry nor reloads a different page', async () => {
  const pending = deferred(), f = setup({ write: () => pending.promise })
  try {
    const importing = f.importCases({ target: new f.Input() }); await flush()
    f.hooks.unmount.forEach(fn => fn())
    pending.reject(new f.errors.ApiBusinessError('Invalid scenario', 35051)); await importing
    assert.equal(f.importRetryable.value, false); assert.equal(f.reloads(), 0); assert.equal(f.importProgress.value, '')
    assert.equal(f.messages.length, 0); assert.equal(f.importing.value, false)
  } finally { f.cleanup() }
})

test('deactivation stops serial writes and preserves the physical mutex until the in-flight write settles', async () => {
  const pending = deferred(), f = setup({ entries: [row('First'), row('Second')], write: () => pending.promise })
  try {
    const loading = f.importCases({ target: new f.Input() }); await flush()
    f.hooks.stop.forEach(fn => fn()); f.hooks.activate.forEach(fn => fn())
    await f.importCases({ target: new f.Input() }); assert.equal(f.writes.length, 1); assert.equal(f.importing.value, true)
    pending.resolve({}); await loading
    assert.equal(f.writes.length, 1); assert.equal(f.importing.value, false); assert.equal(f.reloads(), 0)
    assert.equal(f.importProgress.value, ''); assert.equal(f.messages.filter(([type]) => type === 'success').length, 0)
  } finally { f.cleanup() }
})

test('empty or unreadable workbooks release loading and input for reselection', async () => {
  const f = setup({ entries: [] })
  try {
    const input = new f.Input(); await f.importCases({ target: input })
    assert.match(f.importProgress.value, /没有数据/); assert.equal(input.value, '')
    f.badRead(); await f.importCases({ target: input })
    assert.equal(f.importing.value, false); assert.equal(f.writes.length, 0)
  } finally { f.cleanup() }
})

test('export waits for queued saves, snapshots scope and prevents duplicate downloads', async () => {
  const saving = deferred(), f = setup({ flush: () => saving.promise })
  try {
    const exporting = f.exportCases(); await flush(); await f.exportCases()
    assert.equal(f.exporting.value, true); assert.equal(f.queries.length, 0)
    saving.resolve(); await exporting
    assert.equal(f.downloads.length, 1); assert.equal(f.exporting.value, false)
    assert.deepEqual(f.queries[0], { page: 1, pageSize: 10000, id__in: 'A', status: 0 })
  } finally { f.cleanup() }
})

test('late export and save completion do not download after context invalidation', async () => {
  for (const duringSave of [false, true]) {
    const pending = deferred(), f = setup(duringSave ? { flush: () => pending.promise } : { read: () => pending.promise })
    try {
      const exporting = f.exportCases(); await flush(); f.state.context = 'B'; f.state.context = 'A'
      pending.resolve({ data: [row()] }); await exporting
      assert.equal(f.downloads.length, 0); assert.equal(f.exporting.value, false)
      assert.equal(f.queries.length, duringSave ? 0 : 1)
    } finally { f.cleanup() }
  }
})

test('export errors release loading and remain retryable without an empty download', async () => {
  let fail = true
  const f = setup({ read: async () => { if (fail) throw Error('Offline'); return { data: [{ case_no: 'Case' }] } } })
  try {
    await f.exportCases(); assert.equal(f.exporting.value, false); assert.equal(f.downloads.length, 0)
    fail = false; await f.exportCases(); assert.equal(f.downloads.length, 1)
  } finally { f.cleanup() }
})
