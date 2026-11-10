import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import { evaluationComponent } from './helpers/evaluation-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'

const version = (id = 10, status = 'draft') => ({ id, status, version_no: id, schema_snapshot: {} })
function details(api = {}) {
  const dialogs = []
  const modal = options => {
    const handle = { ...options, closed: false, close() { this.closed = true; options.onClose?.() } }
    dialogs.push(handle)
    return handle
  }
  return { ...evaluationComponent('index', 'activeDataset,activeVersion,versions,items,versionPagination,itemPagination,versionLoading,versionLoadingMore,versionLoadError,itemLoading,itemLoadError,loadVersions,loadMoreVersions,retryVersions,selectVersion,createVersion,cloneVersion,publishVersion,removeVersion,removeItem,versionCreating,publishingVersionId,deletingVersionId,deletingItems,confirmationOpen,graderCatalog,catalogLoading,catalogError,loadCatalog,qualityReport,documentVisible,viewItem,documentData,contextKey', {
    filename: path.resolve('src/views/evaluation/dataset/details/index.vue'),
    Modal: { warning: modal, confirm: modal },
    api: { getDatasetVersions: async () => ({ data: { items: [version()], count: 1 } }), getEvaluationDatasetItems: async () => ({ data: { items: [], count: 0 } }), ...api },
  }), dialogs }
}
const editor = api => evaluationComponent('DatasetItemEditor', 'open,closeEditor:close,itemForm,itemVersion,itemEditorVisible,itemSaving,saveError,saveItem', {
  filename: path.resolve('src/views/evaluation/dataset/details/components/DatasetItemEditor.vue'),
  props: { contextKey: 1, graderCatalog: [] }, api,
})

test('dataset changes discard old version reads and cached activation reloads the current scope', async () => {
  const old = deferred(), ids = []
  const s = details({ getDatasetVersions: id => { ids.push(id); return id === 1 ? old.promise : Promise.resolve({ data: { items: [version(20)], count: 1 } }) } })
  try {
    s.route.query.id = '2'
    await flush()
    assert.equal(s.activeVersion.value.id, 20)
    old.resolve({ data: { items: [version(10)], count: 1 } })
    await flush()
    assert.equal(s.activeVersion.value.id, 20)
    s.lifecycle.deactivate()
    assert.deepEqual(s.versions.value, [])
    s.lifecycle.activate()
    await flush()
    assert.deepEqual(ids, [1, 2, 2])
    assert.equal(s.activeVersion.value.id, 20)
  } finally { s.dispose() }
})

test('version scrolling retries the failed page and deduplicates overlap without losing selection', async () => {
  const queries = []
  let fail = true
  const s = details({ getDatasetVersions: async (_id, query) => {
    queries.push({ ...query })
    if (query.page === 1) return { data: { items: Array.from({ length: 20 }, (_, i) => version(i + 1)), count: 22 } }
    if (fail) throw Error('offline')
    return { data: { items: [version(20), version(21), version(22)], count: 22 } }
  } })
  try {
    await flush()
    await s.loadMoreVersions()
    assert.equal(s.versionLoadError.value, true)
    assert.equal(s.versionPagination.page, 1)
    fail = false
    await s.retryVersions()
    assert.equal(s.versions.value.length, 22)
    assert.equal(s.activeVersion.value.id, 1)
    assert.equal(s.versionLoadingMore.value, false)
    await s.loadMoreVersions()
    assert.deepEqual(queries.map(query => [query.page, query.pageSize]), [[1, 20], [2, 20], [2, 20]])
  } finally { s.dispose() }
})

test('item reads use latest selection and expose a retryable local error', async () => {
  const old = deferred()
  let fail = true
  const s = details({ getEvaluationDatasetItems: id => {
    if (id === 10) return old.promise
    if (fail) return Promise.reject(Error('offline'))
    return Promise.resolve({ data: { items: [{ id: 9 }], count: 1 } })
  } })
  try {
    await flush()
    await s.selectVersion(version(20))
    assert.equal(s.itemLoadError.value, true)
    assert.equal(s.itemLoading.value, false)
    fail = false
    await s.selectVersion(version(20), false)
    old.resolve({ data: { items: [{ id: 1 }], count: 1 } })
    await flush()
    assert.deepEqual(s.items.value.map(item => item.id), [9])
  } finally { s.dispose() }
})

test('version creation stays physically locked across identity changes and suppresses stale refreshes', async () => {
  const pending = deferred(), writes = []
  const s = details({ createDatasetVersion: (id, data) => { writes.push({ id, data }); return pending.promise } })
  try {
    await flush()
    const task = s.createVersion()
    s.user.roleId++
    await flush()
    assert.equal(await s.createVersion(), false)
    assert.equal(s.versionCreating.value, true)
    pending.resolve({ data: version() })
    assert.equal(await task, false)
    assert.equal(writes.length, 1)
    assert.equal(s.versionCreating.value, false)
    assert.equal(s.notices.length, 0)
  } finally { s.dispose() }
})

test('quality failure can retry and reports validation errors without publishing', async () => {
  let calls = 0, writes = 0
  const s = details({ getDatasetQuality: async () => {
    if (++calls === 1) throw Error('offline')
    return { data: { errors: [{ key: 'missing', item_id: 5, message: 'missing input' }] } }
  }, publishDatasetVersion: async () => { writes++ } })
  try {
    await flush()
    assert.equal(await s.publishVersion(version()), false)
    assert.equal(s.publishingVersionId.value, undefined)
    await s.publishVersion(version())
    assert.equal(s.qualityReport.value.errors[0].item_id, 5)
    assert.equal(writes, 0)
  } finally { s.dispose() }
})

test('publish warning confirmation becomes inert on environment change and after acknowledgment begins', async () => {
  const ack = deferred(), writes = []
  const s = details({ getDatasetQuality: async () => ({ data: { warnings: [{ message: 'duplicate', groups: [[5, 6]] }] } }),
    acknowledgeDatasetQuality: id => { writes.push(['ack', id]); return ack.promise },
    publishDatasetVersion: async id => { writes.push(['publish', id]) },
  })
  try {
    await flush()
    await s.publishVersion(version())
    const first = s.dialogs[0]
    assert.match(first.content, /5、6/)
    s.user.selected_environment++
    await flush()
    assert.equal(first.closed, true)
    assert.equal(await first.onBeforeOk(), false)
    assert.deepEqual(writes, [])
    await s.publishVersion(version())
    const task = s.dialogs[1].onBeforeOk()
    assert.equal(await s.dialogs[1].onBeforeOk(), false)
    s.user.roleId++
    ack.resolve({})
    assert.equal(await task, false)
    assert.deepEqual(writes, [['ack', 10]])
  } finally { s.dispose() }
})

test('failed deletion retains confirmation, successful final-row deletion backs up one page', async () => {
  let calls = 0
  const queries = []
  const s = details({ deleteEvaluationDatasetItem: async () => { if (++calls === 1) throw Error('offline') },
    getEvaluationDatasetItems: async (_id, query) => { queries.push({ ...query }); return { data: { items: [{ id: 9 }], count: 21 } } },
  })
  try {
    await flush()
    s.itemPagination.page = 2
    s.removeItem({ id: 9 })
    const dialog = s.dialogs[0]
    assert.equal(await dialog.onBeforeOk(), false)
    assert.equal(s.deletingItems.size, 0)
    assert.equal(s.itemPagination.page, 2)
    assert.equal(await dialog.onBeforeOk(), true)
    assert.equal(s.itemPagination.page, 1)
    assert.equal(queries.at(-1).page, 1)
    assert.equal(calls, 2)
  } finally { s.dispose() }
})

test('delete and copy confirmations cannot submit after a route/identity round trip', async () => {
  const writes = []
  const s = details({ deleteDatasetVersion: async id => writes.push(id), createDatasetVersion: async id => writes.push(id) })
  try {
    await flush()
    s.removeVersion(version())
    const obsolete = s.dialogs[0]
    s.route.query.id = '2'; s.route.query.id = '1'
    await flush()
    assert.equal(await obsolete.onBeforeOk(), false)
    s.cloneVersion(version())
    const copy = s.dialogs[1]
    s.user.roleId++
    await flush()
    assert.equal(await copy.onBeforeOk(), false)
    assert.deepEqual(writes, [])
  } finally { s.dispose() }
})

test('cancelled and successfully submitted confirmations cannot be submitted again', async () => {
  let writes = 0
  const s = details({ createDatasetVersion: async () => { writes++ } })
  try {
    await flush()
    s.cloneVersion(version())
    const cancelled = s.dialogs[0]
    cancelled.close()
    assert.equal(await cancelled.onBeforeOk(), false)
    s.cloneVersion(version())
    const saved = s.dialogs[1]
    assert.equal(await saved.onBeforeOk(), true)
    assert.equal(await saved.onBeforeOk(), false)
    assert.equal(writes, 1)
  } finally { s.dispose() }
})

test('catalog failure retries independently and snapshots are cleared across identity changes', async () => {
  let calls = 0
  const s = details({ getDatasetGraderCatalog: async () => { if (++calls === 1) throw Error('offline'); return { data: [{ name: 'Grader' }] } } })
  try {
    await flush()
    s.viewItem({ id: 5, context: { text: 'source' }, grading_config: { mode: 'replace', graders: [] } })
    await flush()
    assert.ok(s.catalogError.value)
    await s.loadCatalog()
    assert.equal(s.catalogLoading.value, false)
    assert.equal(s.graderCatalog.value.length, 1)
    s.user.roleId++
    assert.equal(s.documentVisible.value, false)
    assert.equal(s.documentData.value, null)
    assert.deepEqual(s.graderCatalog.value, [])
  } finally { s.dispose() }
})

test('item draft snapshots preserve falsy values and submit only whitelisted fields', async () => {
  const writes = []
  const s = editor({ updateEvaluationDatasetItem: async payload => writes.push(payload) })
  try {
    const original = { id: 5, input_data: false, expected_output: 0, context: { nested: 0 }, enabled: false, audit: 'do not submit' }
    s.open(version(), original)
    s.itemForm.context_text = '{"nested":1}'
    assert.equal(await s.saveItem(), true)
    assert.equal(original.context.nested, 0)
    assert.equal(writes[0].input_data, false)
    assert.equal(writes[0].expected_output, 0)
    assert.equal(writes[0].enabled, false)
    assert.equal('audit' in writes[0], false)
    assert.deepEqual(s.events.at(-1), ['saved', 10])
  } finally { s.dispose() }
})

test('invalid item JSON and backend rejection retain drafts and allow explicit retry', async () => {
  let calls = 0
  const s = editor({ createEvaluationDatasetItem: async () => { if (++calls === 1) throw Error('rejected') } })
  try {
    s.open(version())
    s.itemForm.input_text = '{'
    assert.equal(await s.saveItem(), false)
    assert.equal(calls, 0)
    assert.match(s.saveError.value, /JSON/)
    s.itemForm.input_text = 'false'
    assert.equal(await s.saveItem(), false)
    assert.equal(s.itemEditorVisible.value, true)
    assert.equal(s.itemForm.input_text, 'false')
    assert.equal(s.itemSaving.value, false)
    assert.equal(await s.saveItem(), true)
  } finally { s.dispose() }
})

test('item editor context invalidation does not unlock the pending save or emit stale success', async () => {
  const pending = deferred()
  let writes = 0
  const s = editor({ createEvaluationDatasetItem: () => { writes++; return pending.promise } })
  try {
    s.open(version())
    const task = s.saveItem()
    s.props.contextKey++
    s.open(version(20))
    assert.equal(s.itemEditorVisible.value, false)
    assert.equal(s.itemSaving.value, true)
    await s.saveItem()
    pending.resolve({})
    assert.equal(await task, false)
    assert.equal(s.events.length, 0)
    assert.equal(writes, 1)
    assert.equal(s.itemSaving.value, false)
    s.open(version(20))
    assert.equal(s.itemVersion.value.id, 20)
  } finally { s.dispose() }
})

test('source search retries preserve selected labels and discard old searches and deactivated responses', async () => {
  const old = deferred(), late = deferred()
  let fail = true
  const s = evaluationComponent('ItemDataSourceEditor', 'loadResources,retryResources,resources,loadError,loading,page', {
    props: { versionId: 10, modelValue: { kind: 'api_info', module_id: 2, binding: { ref_id: 50, project_product_id: 1, name: 'Selected' } } },
    api: { getDatasetWorkflowResources: (_id, query) => {
      if (query.search === 'old') return old.promise
      if (query.search === 'late') return late.promise
      if (fail) return Promise.reject(Error('offline'))
      return Promise.resolve({ data: { items: [{ id: 60, name: 'New', available: true }], count: 1 } })
    } },
  })
  try {
    const obsolete = s.loadResources('old')
    await s.loadResources('new')
    assert.ok(s.loadError.value)
    fail = false
    await s.retryResources()
    old.resolve({ data: { items: [{ id: 1, name: 'obsolete', available: true }], count: 1 } })
    await obsolete
    assert.deepEqual(s.resources.value.map(item => item.value), [60, 50])
    assert.equal(s.resources.value.find(item => item.value === 50).label, 'Selected')
    const pending = s.loadResources('late')
    s.lifecycle.deactivate()
    late.resolve({ data: { items: [{ id: 1 }], count: 1 } })
    await pending
    assert.deepEqual(s.resources.value, [])
    assert.equal(s.loading.value, false)
  } finally { s.dispose() }
})
