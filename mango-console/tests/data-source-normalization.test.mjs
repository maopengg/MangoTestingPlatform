import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { setupSource, source } from './helpers/source-harness.mjs'
const base = path.resolve('src/views/config/data-source')
const editor = (api) =>
  setupSource(
    'DataSourceEditor',
    'draft,editingId,visible,saving,save,open,close,sourceTypeOptions,visibleFields,onCategoryChange,onSourceTypeChange',
    api,
    { optionsLoading: false }
  )
const page = (api) =>
  setupSource(
    'index',
    'sources,loading,loadFailed,doRefresh,onTest,onDelete,testingIds,editorRef',
    api
  )
const workbench = (api = {}, sources = [source(1), source(2)]) =>
  setupSource(
    'DataSourceWorkbench',
    'selectedId,selected,activeTab,bindings,databases,errors,bindingLoading,databaseLoading,loadBindings,loadDatabases,selectSource,bindingPage,databaseQuery,openDatabaseQuery,openBindingPage,bindingPagination,databasePagination,databaseKeyword,pagedBindings,pagedDatabases',
    api,
    { sources, loading: false, testingIds: [] }
  )
const drawer = (api) =>
  setupSource('DataSourceSqlQueryDrawer', 'query,clear,statement,result,loading', api, {
    visible: true,
    sourceId: 1,
    sourceName: 'Source',
    databaseName: 'example',
  })

test('page and all three business components compile scripts and templates', () => {
  for (const name of [
    'index.vue',
    'components/DataSourceEditor.vue',
    'components/DataSourceWorkbench.vue',
    'components/DataSourceSqlQueryDrawer.vue',
  ]) {
    const filename = path.join(base, name),
      { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: name })
    assert.deepEqual(
      compileTemplate({
        source: descriptor.template.content,
        filename,
        id: name,
        compilerOptions: { bindingMetadata: script.bindings },
      }).errors,
      []
    )
  }
})
test('drafts isolate instances, preserve zero enums, and never read stored credentials', () => {
  const a = editor(),
    b = editor()
  try {
    const record = source(1, { password: 'not-a-returned-field', extra_config: { ssl: true } })
    a.open(record)
    a.draft.display_name = 'Draft'
    assert.equal(a.draft.password, '')
    assert.equal(a.draft.db_type, 0)
    assert.equal(record.display_name, 'Source 1')
    assert.equal(b.draft.display_name, '')
    a.close()
    a.open()
    assert.equal(a.editingId.value, null)
    assert.equal(a.draft.port, 3306)
    assert.equal(a.draft.display_name, '')
  } finally {
    a.dispose()
    b.dispose()
  }
})
test('editing submits a frozen whitelist and omits blank password', async () => {
  const gate = deferred(),
    calls = [],
    s = editor({
      putSystemDataSource: (payload) => {
        calls.push(payload)
        return gate.promise
      },
    })
  try {
    s.open(source(5, { update_time: 'audit', extra_config: { unknown: 'not sent' } }))
    const saving = s.save()
    s.draft.host = 'changed.example.org'
    assert.equal(await s.save(), false)
    assert.equal(calls.length, 1)
    assert.equal(calls[0].host, 'db.example.com')
    assert.equal(calls[0].id, 5)
    assert.equal('password' in calls[0], false)
    assert.equal('update_time' in calls[0], false)
    assert.deepEqual(calls[0].extra_config, {})
    gate.resolve({ msg: 'ok' })
    assert.equal(await saving, true)
    assert.deepEqual(s.events, [['saved']])
    assert.equal(s.visible.value, false)
  } finally {
    s.dispose()
  }
})
test('failed save keeps input and allows explicit retry', async () => {
  let count = 0
  const s = editor({
    postSystemDataSource: async () => {
      if (++count === 1) throw Error('failed')
      return { msg: 'ok' }
    },
  })
  try {
    s.open()
    Object.assign(s.draft, source(1), { password: 'fixture-secret' })
    assert.equal(await s.save(), false)
    assert.equal(s.saving.value, false)
    assert.equal(s.visible.value, true)
    assert.equal(s.draft.password, 'fixture-secret')
    assert.equal(await s.save(), true)
    assert.equal(count, 2)
    assert.equal(s.draft.password, '')
  } finally {
    s.dispose()
  }
})
test('type/category changes reset supported extra config and default ports', () => {
  const s = editor()
  try {
    s.open()
    assert.equal(
      s.sourceTypeOptions.value.some((item) => item.key === 3),
      false
    )
    s.draft.source_category = 1
    s.onCategoryChange()
    assert.equal(s.draft.db_type, 10)
    assert.equal(s.draft.port, 6379)
    assert.deepEqual(s.draft.extra_config, { ssl: false })
    s.draft.source_category = 2
    s.onCategoryChange()
    assert.equal(s.draft.db_type, 20)
    assert.equal(s.draft.port, 9200)
    assert.deepEqual(s.draft.extra_config, { scheme: 'http', path_prefix: '', verify_certs: true })
    s.draft.db_type = 2
    s.onSourceTypeChange()
    assert.deepEqual(s.draft.extra_config, {})
    assert.equal(
      s.visibleFields.value.some((item) => item.key === 'host'),
      false
    )
  } finally {
    s.dispose()
  }
})
test('SQLite payload excludes hidden network credentials; ES false flags survive', async () => {
  const calls = [],
    s = editor({
      postSystemDataSource: async (payload) => {
        calls.push(payload)
        return { msg: 'ok' }
      },
    })
  try {
    s.open()
    Object.assign(s.draft, {
      display_name: 'SQLite',
      db_type: 2,
      file_path: '/tmp/example.db',
      password: 'fixture-secret',
    })
    assert.equal(await s.save(), true)
    assert.equal('host' in calls[0], false)
    assert.equal('password' in calls[0], false)
    s.open(
      source(2, {
        db_type: 20,
        source_category: 2,
        extra_config: { scheme: 'https', path_prefix: 'search', verify_certs: false },
      })
    )
    assert.equal(s.draft.extra_config.verify_certs, false)
    s.draft.extra_config.path_prefix = 'new'
    assert.equal(await s.save(), true)
  } finally {
    s.dispose()
  }
})
test('validation retains required name/address/user and valid zero DB type', async () => {
  const s = editor()
  try {
    s.open()
    assert.equal(await s.save(), false)
    Object.assign(s.draft, source())
    s.draft.user = ''
    assert.equal(await s.save(), false)
    s.draft.user = 'fixture'
    assert.equal(await s.save(), true)
  } finally {
    s.dispose()
  }
})
test('late save after cache deactivation cannot close/rewrite a new context', async () => {
  const gate = deferred(),
    s = editor({ putSystemDataSource: () => gate.promise })
  try {
    s.open(source())
    const pending = s.save()
    s.lifecycle.deactivate()
    assert.equal(s.visible.value, false)
    s.lifecycle.activate()
    s.open(source(2))
    assert.equal(s.visible.value, false)
    gate.resolve({ msg: 'ok' })
    assert.equal(await pending, false)
    assert.deepEqual(s.events, [])
    s.open(source(2))
    assert.equal(s.editingId.value, 2)
  } finally {
    s.dispose()
  }
})
test('latest list request controls rows and loading; failure supports retry', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const s = page({ getSystemDataSource: () => (++count === 1 ? a.promise : b.promise) })
  try {
    const first = s.doRefresh(),
      second = s.doRefresh()
    a.resolve({ data: [source(1)] })
    await first
    assert.equal(s.loading.value, true)
    assert.deepEqual(s.sources.value, [])
    b.resolve({ data: [source(2)] })
    await second
    assert.equal(s.sources.value[0].id, 2)
  } finally {
    s.dispose()
  }
  let fail = true
  const s2 = page({
    getSystemDataSource: async () => {
      if (fail) throw Error()
      return { data: [source()] }
    },
  })
  try {
    await s2.doRefresh()
    assert.equal(s2.loadFailed.value, true)
    assert.equal(s2.loading.value, false)
    fail = false
    await s2.doRefresh()
    assert.equal(s2.loadFailed.value, false)
  } finally {
    s2.dispose()
  }
})
test('identity changes discard old lists and close edit/confirmation state', async () => {
  const gate = deferred(),
    resumed = deferred()
  let count = 0
  const s = page({ getSystemDataSource: () => (++count === 1 ? gate.promise : resumed.promise) })
  try {
    let closes = 0
    s.editorRef.value = { close: () => closes++ }
    const pending = s.doRefresh()
    s.onDelete(source())
    s.user.roleId = 2
    await flush()
    assert.equal(s.confirmations[0].closed, true)
    assert.ok(closes > 0)
    gate.resolve({ data: [source()] })
    await pending
    await flush()
    assert.deepEqual(s.sources.value, [])
    assert.equal(s.loading.value, true)
    resumed.resolve({ data: [source(2)] })
    await flush()
    assert.equal(s.sources.value[0].id, 2)
    assert.equal(s.loading.value, false)
  } finally {
    s.dispose()
  }
})
test('deletion freezes ID, blocks duplicates, keeps confirmation on failure, retries', async () => {
  const gate = deferred(),
    ids = []
  let fail = true
  const s = page({
    deleteSystemDataSource: (id) => {
      ids.push(id)
      return fail ? gate.promise : Promise.resolve({ msg: 'ok' })
    },
  })
  try {
    const record = source(1)
    s.onDelete(record)
    record.id = 2
    const config = s.confirmations[0].config,
      pending = config.onBeforeOk()
    assert.equal(await config.onBeforeOk(), false)
    gate.reject(Error())
    assert.equal(await pending, false)
    fail = false
    assert.equal(await config.onBeforeOk(), true)
    assert.deepEqual(ids, [1, 1])
    assert.equal(config.okButtonProps.status, 'danger')
  } finally {
    s.dispose()
  }
})
test('connection test deduplicates each source and preserves execution API protocol', async () => {
  const gate = deferred(),
    calls = [],
    s = page({
      postDataSourceExecution: (payload) => {
        calls.push(payload)
        return gate.promise
      },
    })
  try {
    const first = s.onTest(source())
    await s.onTest(source())
    assert.deepEqual(calls, [{ action: 'test_connection', data_source_id: 1 }])
    s.lifecycle.deactivate()
    gate.resolve({ data: { connected: true, checks: [] }, msg: 'ok' })
    await first
    assert.deepEqual(s.testingIds.value, [])
    assert.equal(s.notices.length, 0)
  } finally {
    s.dispose()
  }
})
test('A→B→A binding requests reject the first A and reset pagination/windows', async () => {
  const gates = [deferred(), deferred(), deferred()]
  let count = 0
  const s = workbench({ getDataSourceBindings: () => gates[count++].promise })
  try {
    s.bindingPagination.page = 3
    s.bindingPage.visible = true
    s.databaseQuery.visible = true
    s.selectedId.value = 2
    await flush()
    s.selectedId.value = 1
    await flush()
    gates[0].resolve({ data: [{ id: 99 }] })
    await flush()
    assert.deepEqual(s.bindings.value, [])
    assert.equal(s.bindingLoading.value, true)
    assert.equal(s.bindingPage.visible, false)
    assert.equal(s.databaseQuery.visible, false)
    gates[2].resolve({ data: [{ id: 3 }] })
    gates[1].resolve({ data: [{ id: 2 }] })
    await flush()
    assert.equal(s.bindings.value[0].id, 3)
    assert.equal(s.bindingPagination.page, 1)
  } finally {
    s.dispose()
  }
})
test('database discovery errors surface locally and can retry; latest request wins', async () => {
  let count = 0
  const a = deferred(),
    b = deferred()
  const s = workbench({
    getDataSourceDatabases: () => {
      count++
      if (count === 1) throw Error('discovery failed')
      return count === 2 ? a.promise : b.promise
    },
  })
  try {
    await s.loadDatabases()
    assert.equal(s.errors.databases, 'discovery failed')
    assert.equal(s.databaseLoading.value, false)
    const old = s.loadDatabases(),
      fresh = s.loadDatabases()
    b.resolve({ data: [{ name: 'new' }] })
    await fresh
    a.resolve({ data: [{ name: 'old' }] })
    await old
    assert.equal(s.databases.value[0].name, 'new')
    assert.equal(s.errors.databases, '')
  } finally {
    s.dispose()
  }
})
test('workbench keeps query selection, leaf binding target and discovered SQL target', async () => {
  const s = workbench()
  try {
    s.route.query.data_source_id = '2'
    await flush()
    assert.equal(s.selectedId.value, 2)
    s.openDatabaseQuery({ name: 'example' })
    assert.equal(s.databaseQuery.sourceId, 2)
    s.openBindingPage({
      datasource_alias__project_product_id: 10,
      datasource_alias_id: 30,
      datasource_alias__project_product__name: 'Product',
    })
    assert.equal(s.bindingPage.productId, '10')
    assert.equal(s.bindingPage.datasourceId, '30')
    s.props.sources = [source(1)]
    await flush()
    assert.equal(s.selectedId.value, 1)
    assert.equal(s.databaseQuery.visible, false)
  } finally {
    s.dispose()
  }
})
test('client paging counts and slices filtered rows without extra API requests', async () => {
  const s = workbench()
  try {
    await flush()
    s.bindings.value = Array.from({ length: 45 }, (_, id) => ({ id }))
    s.databases.value = Array.from({ length: 65 }, (_, id) => ({ name: `database-${id}` }))
    await flush()
    assert.equal(s.bindingPagination.pageCount, 45)
    assert.equal(s.databasePagination.pageCount, 65)
    s.bindingPagination.page = 2
    s.databasePagination.page = 4
    assert.equal(s.pagedBindings.value[0].id, 20)
    assert.equal(s.pagedDatabases.value.length, 5)
    s.databaseKeyword.value = 'database-6'
    await flush()
    assert.equal(s.databasePagination.page, 1)
    assert.equal(s.databasePagination.pageCount, 6)
    s.databaseKeyword.value = 'missing'
    await flush()
    assert.deepEqual(s.pagedDatabases.value, [])
    s.bindings.value = []
    await flush()
    assert.equal(s.bindingPagination.page, 1)
  } finally {
    s.dispose()
  }
})
test('SQL query freezes target, prevents duplicates and retains statement after failure', async () => {
  const gate = deferred(),
    calls = [],
    s = drawer({
      queryDataSourceDatabase: (payload) => {
        calls.push(payload)
        return gate.promise
      },
    })
  try {
    s.statement.value = ' SELECT 1 LIMIT 20 '
    const pending = s.query()
    await s.query()
    assert.deepEqual(calls, [
      { data_source_id: 1, database_name: 'example', sql: 'SELECT 1 LIMIT 20' },
    ])
    gate.reject(Error())
    await pending
    assert.equal(s.loading.value, false)
    assert.equal(s.statement.value, ' SELECT 1 LIMIT 20 ')
    s.clear()
    assert.equal(s.statement.value, '')
  } finally {
    s.dispose()
  }
})
test('SQL close/reopen and target changes discard late results and loading', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const s = drawer({ queryDataSourceDatabase: () => (++count === 1 ? a.promise : b.promise) })
  try {
    s.statement.value = 'SELECT 1 LIMIT 20'
    const old = s.query()
    s.props.visible = false
    s.props.visible = true
    s.props.sourceId = 2
    assert.equal(s.statement.value, '')
    s.statement.value = 'SELECT 2 LIMIT 20'
    const fresh = s.query()
    a.resolve({ data: { old: true } })
    await old
    assert.equal(s.loading.value, true)
    assert.equal(s.result.value, null)
    b.resolve({ data: { new: true } })
    await fresh
    assert.deepEqual(s.result.value, { new: true })
  } finally {
    s.dispose()
  }
})
test('SQL cache deactivation invalidates results; activation permits a new explicit query', async () => {
  const gate = deferred(),
    s = drawer({ queryDataSourceDatabase: () => gate.promise })
  try {
    s.statement.value = 'SELECT 1 LIMIT 20'
    const pending = s.query()
    s.lifecycle.deactivate()
    s.lifecycle.activate()
    gate.resolve({ data: ['late'] })
    await pending
    assert.equal(s.result.value, null)
    assert.equal(s.loading.value, false)
  } finally {
    s.dispose()
  }
})

test('cached page suspends on leave and reloads once on reactivation', async () => {
  const gate = deferred()
  let count = 0
  const s = page({
    getSystemDataSource: () =>
      ++count === 1 ? gate.promise : Promise.resolve({ data: [source(2)] }),
  })
  try {
    s.lifecycle.mount()
    s.lifecycle.activate()
    assert.equal(count, 1)
    s.route.path = '/config/product/index'
    await s.doRefresh()
    assert.equal(count, 1)
    s.lifecycle.deactivate()
    gate.resolve({ data: [source(1)] })
    await flush()
    assert.deepEqual(s.sources.value, [])
    s.route.path = '/config/data-source/index'
    s.lifecycle.activate()
    await flush()
    assert.equal(count, 2)
    assert.equal(s.sources.value[0].id, 2)
  } finally {
    s.dispose()
  }
})

test('old deletion confirmation cannot execute after identity changes', async () => {
  let count = 0
  const s = page({
    deleteSystemDataSource: async () => {
      count++
      return { msg: 'ok' }
    },
  })
  try {
    s.onDelete(source())
    const dialog = s.confirmations[0]
    s.user.token = 'new-fixture-session'
    assert.equal(await dialog.config.onBeforeOk(), false)
    assert.equal(count, 0)
  } finally {
    s.dispose()
  }
})

test('connection failures release per-source guards and permit independent tests', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const s = page({ postDataSourceExecution: () => (++count === 1 ? a.promise : b.promise) })
  try {
    const first = s.onTest(source(1)),
      second = s.onTest(source(2))
    assert.deepEqual(s.testingIds.value, [1, 2])
    a.reject({ msg: 'fixture failure' })
    await first
    assert.deepEqual(s.testingIds.value, [2])
    assert.equal(s.notices[0], 'fixture failure')
    b.resolve({ data: { connected: false, error: 'fixture disconnected' }, msg: 'ok' })
    await second
    assert.deepEqual(s.testingIds.value, [])
  } finally {
    s.dispose()
  }
})

test('workbench cache deactivation discards both regions and reloads active tab', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const s = workbench({
    getDataSourceBindings: () => a.promise,
    getDataSourceDatabases: () =>
      ++count === 1 ? b.promise : Promise.resolve({ data: [{ name: 'new' }] }),
  })
  try {
    s.activeTab.value = 'databases'
    const pending = s.loadDatabases()
    s.lifecycle.deactivate()
    a.resolve({ data: [{ id: 99 }] })
    b.resolve({ data: [{ name: 'old' }] })
    await pending
    await flush()
    assert.deepEqual(s.bindings.value, [])
    assert.deepEqual(s.databases.value, [])
    s.lifecycle.activate()
    await flush()
    assert.equal(s.databases.value[0].name, 'new')
  } finally {
    s.dispose()
  }
})

test('SQL identity changes clear private query state without automatic re-execution', async () => {
  const gate = deferred()
  let count = 0
  const s = drawer({
    queryDataSourceDatabase: () => {
      count++
      return gate.promise
    },
  })
  try {
    s.statement.value = 'SELECT 1 LIMIT 20'
    const pending = s.query()
    s.user.roleId = 2
    assert.equal(s.statement.value, '')
    assert.equal(s.loading.value, false)
    gate.resolve({ data: ['old'] })
    await pending
    assert.equal(s.result.value, null)
    assert.equal(count, 1)
  } finally {
    s.dispose()
  }
})
