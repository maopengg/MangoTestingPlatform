import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import { evaluationComponent } from './helpers/evaluation-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'

const record = (id = 1, extra = {}) => ({ id, name: `Dataset ${id}`, status: 'enabled', task_type: ['记忆'], ...extra })
function list(api = {}) {
  const dialogs = []
  return { ...evaluationComponent('index', 'rows,loading,listError,filters,pagination,reload:load,onSearch,onResetSearch,changeDatasetStatus,statusSaving,deleting,remove,confirmationOpen,openCreate,openEdit,openVersions,editor,contextKey', {
    filename: path.resolve('src/views/evaluation/dataset/index.vue'),
    api: { getEvaluationDatasets: async () => ({ data: [record()], totalSize: 1 }), ...api },
    Modal: { warning: config => {
      const dialog = { ...config, closed: false, close() { this.closed = true; config.onClose?.() } }
      dialogs.push(dialog)
      return dialog
    } },
  }), dialogs }
}
const editor = api => evaluationComponent('DatasetEditor', 'form,visible,savingDataset,saveError,open,closeEditor:close,saveDataset,updateTaskTypes,onEnter,isSaving', {
  filename: path.resolve('src/views/evaluation/dataset/components/DatasetEditor.vue'),
  props: { contextKey: 1 }, api,
})

test('list queries retain JSON membership and status collections while cleaning empty parameters', async () => {
  const queries = []
  const s = list({ getEvaluationDatasets: async query => { queries.push(query); return { data: [], totalSize: 0 } } })
  try {
    await flush()
    assert.deepEqual(queries[0], { page: 1, pageSize: 10 })
    Object.assign(s.filters, { name: 'name', task_type: ['记忆，问答', ' 记忆 '], status: ['enabled', 'draft'] })
    s.pagination.page = 4
    await s.onSearch()
    assert.deepEqual(queries.at(-1), { page: 1, pageSize: 10, name: 'name', task_types: '["记忆","问答"]', status__in: 'enabled,draft' })
    const taskTypes = s.filters.task_type, statuses = s.filters.status
    await s.onResetSearch()
    assert.deepEqual(queries.at(-1), { page: 1, pageSize: 10 })
    assert.notEqual(s.filters.task_type, taskTypes)
    assert.notEqual(s.filters.status, statuses)
  } finally { s.dispose() }
})

test('latest list response wins and zero totals do not fall back to the visible row count', async () => {
  const first = deferred(), second = deferred()
  let calls = 0
  const s = list({ getEvaluationDatasets: () => ++calls === 1 ? first.promise : second.promise })
  try {
    s.filters.name = 'new'
    const task = s.onSearch()
    second.resolve({ data: [record(2, { task_type: 'retrieval' })], totalSize: 0 })
    await task
    first.resolve({ data: [record(1)], totalSize: 1 })
    await flush()
    assert.equal(s.rows.value[0].id, 2)
    assert.deepEqual(s.rows.value[0].task_type, ['retrieval'])
    assert.equal(s.pagination.pageCount, 0)
    assert.equal(s.loading.value, false)
  } finally { s.dispose() }
})

test('list errors retain current data, release loading, and support explicit retry', async () => {
  let fail = false
  const s = list({ getEvaluationDatasets: async () => { if (fail) throw Error('offline'); return { data: [record()] } } })
  try {
    await flush()
    fail = true
    assert.equal(await s.reload(), false)
    assert.equal(s.rows.value.length, 1)
    assert.ok(s.listError.value)
    assert.equal(s.loading.value, false)
    fail = false
    assert.equal(await s.reload(), true)
    assert.equal(s.listError.value, '')
  } finally { s.dispose() }
})

test('identity and cached lifecycle invalidate old rows, close windows and reload on activation', async () => {
  const pending = deferred()
  let calls = 0, closes = 0
  const s = list({ getEvaluationDatasets: async () => ++calls === 1 ? pending.promise : ({ data: [record(calls)] }) })
  try {
    s.editor.value = { close: () => closes++ }
    s.filters.task_type = ['old identity']
    s.pagination.page = 3
    s.user.roleId++
    await flush()
    assert.equal(s.filters.task_type.length, 0)
    assert.equal(s.pagination.page, 1)
    pending.resolve({ data: [record(1)] })
    await flush()
    assert.equal(s.rows.value[0].id, 2)
    s.lifecycle.deactivate()
    assert.deepEqual(s.rows.value, [])
    assert.ok(closes >= 2)
    s.lifecycle.activate()
    await flush()
    assert.equal(s.rows.value[0].id, 3)
  } finally { s.dispose() }
})

test('environment changes preserve search intent while rejecting old reads', async () => {
  const pending = deferred()
  let calls = 0
  const s = list({ getEvaluationDatasets: () => ++calls === 1 ? pending.promise : Promise.resolve({ data: [record(2)] }) })
  try {
    s.filters.name = 'retain'
    s.user.selected_environment++
    await flush()
    pending.resolve({ data: [record(1)] })
    await flush()
    assert.equal(s.rows.value[0].id, 2)
    assert.equal(s.filters.name, 'retain')
  } finally { s.dispose() }
})

test('status writes submit a fixed id/status snapshot and apply only after acknowledgment', async () => {
  const pending = deferred(), writes = []
  const s = list({ updateEvaluationDataset: data => { writes.push(data); return pending.promise } })
  try {
    await flush()
    const row = s.rows.value[0]
    const task = s.changeDatasetStatus(row)
    assert.equal(row.status, 'enabled')
    assert.equal(await s.changeDatasetStatus(row), false)
    assert.equal(s.statusSaving.has(1), true)
    row.name = 'edited label'
    pending.resolve({})
    assert.equal(await task, true)
    assert.deepEqual(writes, [{ id: 1, status: 'archived' }])
    assert.equal(s.statusSaving.size, 0)
  } finally { s.dispose() }
})

test('failed status writes leave the record unchanged and retry uses the correct restore state', async () => {
  const writes = []
  let fail = true
  const s = list({ updateEvaluationDataset: async data => { writes.push(data); if (fail) throw Error('rejected') } })
  try {
    await flush()
    const row = s.rows.value[0]
    assert.equal(await s.changeDatasetStatus(row), false)
    assert.equal(row.status, 'enabled')
    assert.equal(s.statusSaving.size, 0)
    fail = false
    await s.changeDatasetStatus(record(2, { status: 'archived', current_version: 0 }))
    await s.changeDatasetStatus(record(3, { status: 'archived', current_version: 2 }))
    assert.deepEqual(writes, [{ id: 1, status: 'archived' }, { id: 2, status: 'draft' }, { id: 3, status: 'enabled' }])
  } finally { s.dispose() }
})

test('different status rows can progress independently and stale success cannot refresh a new identity', async () => {
  const first = deferred(), second = deferred()
  let reads = 0
  const s = list({ getEvaluationDatasets: async () => { reads++; return { data: [record()] } }, updateEvaluationDataset: data => data.id === 1 ? first.promise : second.promise })
  try {
    await flush()
    const a = s.changeDatasetStatus(record(1)), b = s.changeDatasetStatus(record(2))
    assert.deepEqual([...s.statusSaving], [1, 2])
    s.user.roleId++
    await flush()
    const before = reads
    assert.equal(await s.changeDatasetStatus(record(1)), false)
    first.resolve({}); second.resolve({})
    assert.equal(await a, false)
    assert.equal(await b, false)
    assert.equal(reads, before)
    assert.equal(s.statusSaving.size, 0)
  } finally { s.dispose() }
})

test('deletion retries on rejection and successful deletion backs up a final empty page exactly once', async () => {
  let writes = 0
  const s = list({ deleteEvaluationDataset: async () => { if (++writes === 1) throw Error('protected asset') } })
  try {
    await flush()
    s.pagination.page = 3
    s.remove(record())
    const dialog = s.dialogs[0]
    assert.equal(await dialog.onBeforeOk(), false)
    assert.equal(s.pagination.page, 3)
    assert.equal(s.deleting.size, 0)
    assert.equal(await dialog.onBeforeOk(), true)
    assert.equal(s.pagination.page, 2)
    assert.equal(await dialog.onBeforeOk(), false)
    assert.equal(writes, 2)
  } finally { s.dispose() }
})

test('closed or identity-invalidated confirmations never submit and pending deletes stay locked', async () => {
  const pending = deferred()
  let writes = 0
  const s = list({ deleteEvaluationDataset: () => { writes++; return pending.promise } })
  try {
    await flush()
    s.remove(record())
    s.dialogs[0].close()
    assert.equal(await s.dialogs[0].onBeforeOk(), false)
    s.remove(record())
    const obsolete = s.dialogs[1]
    s.user.roleId++
    await flush()
    assert.equal(await obsolete.onBeforeOk(), false)
    s.remove(record())
    const task = s.dialogs[2].onBeforeOk()
    assert.equal(await s.dialogs[2].onBeforeOk(), false)
    s.user.roleId++
    assert.equal(s.deleting.has(1), true)
    pending.resolve({})
    assert.equal(await task, false)
    assert.equal(s.deleting.size, 0)
    assert.equal(writes, 1)
  } finally { s.dispose() }
})

test('list delegates minimal editor inputs and navigates without loading detail assets', async () => {
  const opened = []
  const s = list()
  try {
    await flush()
    s.editor.value = { open: value => opened.push(value), close() {}, isSaving: () => false }
    s.openCreate(); s.openEdit(record())
    assert.deepEqual(opened, [undefined, record()])
    s.statusSaving.add(1)
    s.openEdit(record())
    assert.equal(opened.length, 2)
    await s.openVersions(record())
    assert.deepEqual(s.navigations, [{ path: '/evaluation/dataset/details', query: { id: 1, name: 'Dataset 1' } }])
  } finally { s.dispose() }
})

test('editor normalizes legacy and duplicate labels and never writes into the source record', async () => {
  const writes = []
  const s = editor({ updateEvaluationDataset: async payload => writes.push(payload) })
  try {
    const original = record(5, { task_type: ['r', 'r', ' 记忆 '], project_product: 7, owner: 10 })
    s.open(original)
    assert.deepEqual(s.form.task_type, ['r', '记忆'])
    s.updateTaskTypes(['记忆，问答'])
    s.form.name = 'after'
    assert.equal(await s.saveDataset(), true)
    assert.deepEqual(writes, [{ id: 5, name: 'after', description: '', task_type: ['记忆', '问答'], status: 'enabled' }])
    assert.deepEqual(original.task_type, ['r', 'r', ' 记忆 '])
    assert.equal(original.name, 'Dataset 5')
    s.open(record(6, { task_type: 'retrieval' }))
    assert.deepEqual(s.form.task_type, ['retrieval'])
    s.updateTaskTypes([])
    assert.deepEqual(s.form.task_type, [])
  } finally { s.dispose() }
})

test('create resets every draft field and validates required labels before sending', async () => {
  const writes = []
  const s = editor({ createEvaluationDataset: async payload => writes.push(payload) })
  try {
    s.open(record(5, { description: 'old' }))
    s.closeEditor()
    s.open()
    assert.equal(s.form.id, null)
    assert.equal(s.form.description, '')
    assert.deepEqual(s.form.task_type, [])
    assert.equal(await s.saveDataset(), false)
    s.form.name = 'new'
    s.updateTaskTypes([' ', '，'])
    assert.equal(await s.saveDataset(), false)
    assert.equal(writes.length, 0)
    s.updateTaskTypes(['问答，记忆'])
    assert.equal(await s.saveDataset(), true)
    assert.deepEqual(writes[0], { id: undefined, name: 'new', description: '', task_type: ['问答', '记忆'] })
  } finally { s.dispose() }
})

test('save uses a fixed snapshot and duplicate submission never releases its physical lock', async () => {
  const pending = deferred(), writes = []
  const s = editor({ updateEvaluationDataset: payload => { writes.push(payload); return pending.promise } })
  try {
    s.open(record())
    const task = s.saveDataset()
    assert.equal(await s.saveDataset(), false)
    assert.equal(s.savingDataset.value, true)
    assert.equal(s.isSaving(1), true)
    s.updateTaskTypes(['blocked while saving'])
    s.open(record(2))
    assert.equal(s.form.id, 1)
    s.form.task_type.push('late programmatic edit')
    assert.deepEqual(writes[0].task_type, ['记忆'])
    pending.resolve({})
    assert.equal(await task, true)
    assert.equal(s.savingDataset.value, false)
    assert.deepEqual(s.events, [['saved']])
  } finally { s.dispose() }
})

test('save rejection preserves the editable draft and explicit retry succeeds', async () => {
  let calls = 0
  const s = editor({ updateEvaluationDataset: async () => { if (++calls === 1) throw Error('backend rejected') } })
  try {
    s.open(record())
    s.form.description = 'retain me'
    assert.equal(await s.saveDataset(), false)
    assert.equal(s.visible.value, true)
    assert.equal(s.form.description, 'retain me')
    assert.ok(s.saveError.value)
    assert.equal(s.savingDataset.value, false)
    assert.equal(await s.saveDataset(), true)
    assert.equal(s.visible.value, false)
  } finally { s.dispose() }
})

for (const context of ['close', 'context', 'deactivate']) {
  test(`editor ${context} suppresses late saves and keeps the request locked until settlement`, async () => {
    const pending = deferred()
    const s = editor({ updateEvaluationDataset: () => pending.promise })
    try {
      s.open(record())
      const task = s.saveDataset()
      if (context === 'close') s.visible.value = false
      if (context === 'context') s.props.contextKey++
      if (context === 'deactivate') s.lifecycle.deactivate()
      s.open(record(2))
      assert.equal(s.visible.value, false)
      assert.equal(s.isSaving(1), true)
      pending.resolve({})
      assert.equal(await task, false)
      assert.equal(s.savingDataset.value, false)
      assert.deepEqual(s.events, [])
      s.open(record(2))
      assert.equal(s.form.id, 2)
    } finally { s.dispose() }
  })
}

test('Enter confirms only ordinary inputs, not tag creation, textarea newlines or IME composition', async () => {
  let writes = 0, prevented = 0
  const s = editor({ createEvaluationDataset: async () => { writes++ } })
  try {
    s.open()
    s.form.name = 'new'; s.updateTaskTypes(['记忆'])
    const base = { preventDefault() { prevented++ } }
    s.onEnter({ ...base, isComposing: true })
    s.onEnter({ ...base, target: { tagName: 'TEXTAREA' } })
    s.onEnter({ ...base, target: { tagName: 'INPUT', closest: () => ({}) } })
    assert.equal(writes, 0)
    s.onEnter({ ...base, target: { tagName: 'INPUT', closest: () => null } })
    await flush()
    assert.equal(writes, 1)
    assert.equal(prevented, 1)
  } finally { s.dispose() }
})
