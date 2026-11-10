import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import {
  setupProduct,
  base,
  alias,
  binding,
  connection,
} from './helpers/product-datasource-harness.mjs'
const page = (api = {}) =>
  setupProduct(
    'index',
    'rows,selectedId,selectedDatasource,bindings,bindingsLoading,listLoading,listFailed,productId,doRefresh,loadDatasourceBindings,onSelectDatasource,onStatusChange,onBindingPermissionChange,onDelete,onUnbindDatasource,supportsDatasourceTables,detailTab,aliasEditorRef,bindingEditorRef,queryRef',
    api,
    { projectProductId: 10 }
  )
const editor = (api = {}) =>
  setupProduct(
    'LogicalSourceEditor',
    'draft,visible,editingId,saving,open,close,save,onAliasCategoryChange,aliasSourceTypeOptions',
    api,
    { productId: 10, optionsLoading: false }
  )
const bindingEditor = (api = {}) =>
  setupProduct(
    'LogicalBindingEditor',
    'draft,visible,editingId,saving,open,close,save,dataSourceOptions,optionsLoading,optionsError,loadOptions,bindingEnvironmentOptions',
    api,
    { productId: 10, alias: alias(), bindings: [] }
  )
const query = (api = {}) =>
  setupProduct(
    'LogicalSourceQueryDrawer',
    'open,close,queryDrawer,onQueryDatasource,resetQueryInput',
    api,
    { productId: 10, aliasId: 1 }
  )
const tables = (api = {}, props = {}) =>
  setupProduct(
    'ProductDataSourceTables',
    'bindingId,binding,selectedSchema,schemaOptions,schemasLoading,schemasError,tables,loading,error,loadTables,viewSchema,schema,schemaVisible,schemaLoading,selectedKeys,generateForm,generationResults,generationTotal,generateVisible,generating,openGenerate,generate,pagination,pagedTables,keyword',
    api,
    { aliasId: 1, productId: 10, bindings: [binding()], ...props }
  )
const fields = (api = {}, props = {}) =>
  setupProduct(
    'Fields',
    'target,databaseName,schemaName,redisDb,databases,schemas,loading,testTarget',
    api,
    {
      sourceId: 1,
      sourceType: 0,
      modelValue: { database_name: 'example', schema_name: '', redis_db: null },
      ...props,
    },
    path.resolve('src/components/forms/DataSourceTargetFields.vue')
  )

test('page, editors, query, discovery and shared target compile scripts and templates', () => {
  for (const filename of [
    'index.vue',
    'components/LogicalSourceEditor.vue',
    'components/LogicalBindingEditor.vue',
    'components/LogicalSourceQueryDrawer.vue',
    'components/ProductDataSourceTables.vue',
  ]
    .map((file) => path.join(base, file))
    .concat(path.resolve('src/components/forms/DataSourceTargetFields.vue'))) {
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: filename })
    assert.deepEqual(
      compileTemplate({
        source: descriptor.template.content,
        filename,
        id: filename,
        compilerOptions: { bindingMetadata: script.bindings },
      }).errors,
      []
    )
  }
})
test('alias drafts are instance-local and reset without changing original records', () => {
  const a = editor(),
    b = editor()
  try {
    const row = alias()
    a.open(row)
    a.draft.name = 'Changed'
    assert.equal(row.name, 'Alias 1')
    assert.equal(b.draft.name, '')
    a.close()
    a.open()
    assert.equal(a.editingId.value, null)
    assert.equal(a.draft.name, '')
    assert.equal(a.draft.dbType, 0)
  } finally {
    a.dispose()
    b.dispose()
  }
})
test('alias save freezes whitelist, preserves type zero and guards duplicate submissions', async () => {
  const gate = deferred(),
    calls = [],
    s = editor({
      putDataFactoryDatasourceAlias: (payload) => {
        calls.push(payload)
        return gate.promise
      },
    })
  try {
    s.open(alias(5, { update_time: 'audit' }))
    s.draft.description = ' Description '
    const pending = s.save()
    s.draft.name = 'Later'
    assert.equal(await s.save(), false)
    assert.equal(calls.length, 1)
    assert.equal(calls[0].name, 'Alias 5')
    assert.equal(calls[0].id, 5)
    assert.equal(calls[0].db_type, 0)
    assert.equal(calls[0].description, 'Description')
    assert.equal('update_time' in calls[0], false)
    gate.resolve({ msg: 'ok' })
    assert.equal(await pending, true)
    assert.deepEqual(s.events, [['saved']])
    assert.equal(s.visible.value, false)
  } finally {
    s.dispose()
  }
})
test('alias validation, failed save and retry retain prior save semantics', async () => {
  let fail = true
  const s = editor({
    postDataFactoryDatasourceAlias: async () => {
      if (fail) throw Error()
      return { msg: 'ok' }
    },
  })
  try {
    s.open()
    assert.equal(await s.save(), false)
    s.draft.name = ' New '
    s.draft.description = 'x'.repeat(51)
    assert.equal(await s.save(), false)
    s.draft.description = ''
    assert.equal(await s.save(), false)
    assert.equal(s.visible.value, true)
    assert.equal(s.draft.name, ' New ')
    fail = false
    assert.equal(await s.save(), true)
  } finally {
    s.dispose()
  }
})
test('alias save arriving after product/identity switch cannot emit success', async () => {
  const gate = deferred(),
    s = editor({ putDataFactoryDatasourceAlias: () => gate.promise })
  try {
    s.open(alias())
    const pending = s.save()
    s.props.productId = 11
    assert.equal(s.visible.value, false)
    gate.resolve({ msg: 'ok' })
    assert.equal(await pending, false)
    assert.deepEqual(s.events, [])
  } finally {
    s.dispose()
  }
})
test('logical source list uses actual product, stable sorting and embedded requested alias', async () => {
  const calls = [],
    s = page({
      getDataFactoryDatasourceAlias: async (payload) => {
        calls.push(payload)
        return { data: [alias(2, { db_type: 10 }), alias(1), alias(3, { db_type: 20 })] }
      },
    })
  try {
    s.props.datasourceId = 2
    await s.doRefresh()
    assert.deepEqual(calls, [{ project_product: 10 }])
    assert.deepEqual(
      s.rows.value.map((row) => row.id),
      [1, 2, 3]
    )
    assert.equal(s.selectedId.value, 2)
    assert.equal(s.supportsDatasourceTables.value, false)
    s.detailTab.value = 'tables'
    s.onSelectDatasource(s.rows.value[0])
    assert.equal(s.supportsDatasourceTables.value, true)
  } finally {
    s.dispose()
  }
})
test('latest product list request owns rows/loading, and cache return reloads once', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const s = page({ getDataFactoryDatasourceAlias: () => (++count === 1 ? a.promise : b.promise) })
  try {
    const first = s.doRefresh()
    s.props.projectProductId = 11
    a.resolve({ data: [alias(1)] })
    await first
    assert.deepEqual(s.rows.value, [])
    assert.equal(s.listLoading.value, true)
    b.resolve({ data: [alias(2)] })
    await flush()
    assert.equal(s.rows.value[0].id, 2)
    s.lifecycle.deactivate()
    assert.deepEqual(s.rows.value, [])
    s.lifecycle.activate()
    await flush()
    assert.equal(count, 3)
  } finally {
    s.dispose()
  }
})
test('list failure recovers through explicit retry', async () => {
  let fail = true
  const s = page({
    getDataFactoryDatasourceAlias: async () => {
      if (fail) throw Error()
      return { data: [alias()] }
    },
  })
  try {
    await s.doRefresh()
    assert.equal(s.listFailed.value, true)
    assert.equal(s.listLoading.value, false)
    fail = false
    await s.doRefresh()
    assert.equal(s.listFailed.value, false)
  } finally {
    s.dispose()
  }
})
test('A→B→A binding responses reject old A and close target windows', async () => {
  const gates = [deferred(), deferred(), deferred()]
  let count = 0
  const s = page({
    getDataFactoryDatasourceAlias: async () => ({ data: [alias(), alias(2)] }),
    getDataFactoryDatasourceBinding: () => gates[count++].promise,
  })
  try {
    await s.doRefresh()
    let closed = 0
    s.bindingEditorRef.value = { close: () => closed++ }
    s.queryRef.value = { close: () => closed++ }
    s.onSelectDatasource(s.rows.value[1])
    s.onSelectDatasource(s.rows.value[0])
    gates[0].resolve({ data: [binding(99)] })
    await flush()
    assert.deepEqual(s.bindings.value, [])
    assert.equal(s.bindingsLoading.value, true)
    gates[2].resolve({ data: [binding(3)] })
    gates[1].resolve({ data: [binding(2)] })
    await flush()
    assert.equal(s.bindings.value[0].id, 3)
    assert.ok(closed >= 2)
  } finally {
    s.dispose()
  }
})
test('status switch only changes current rows after success and deduplicates writes', async () => {
  const gate = deferred(),
    calls = [],
    s = page({
      putDataFactoryDatasourceAlias: (payload) => {
        calls.push(payload)
        return gate.promise
      },
    })
  try {
    s.rows.value = [alias()]
    const pending = s.onStatusChange(s.rows.value[0], false)
    assert.equal(s.rows.value[0].status, 1)
    assert.equal(await s.onStatusChange(s.rows.value[0], false), false)
    gate.resolve({ msg: 'ok' })
    assert.equal(await pending, true)
    assert.equal(s.rows.value[0].status, 0)
    assert.equal(calls.length, 1)
    assert.equal(calls[0].project_product, 10)
  } finally {
    s.dispose()
  }
})
test('binding switches serialize per row, preserve failed values and forbid production writes', async () => {
  const gate = deferred(),
    calls = [],
    s = page({
      putDataFactoryDatasourceBinding: (payload) => {
        calls.push(payload)
        return gate.promise
      },
    })
  try {
    s.bindings.value = [binding()]
    const pending = s.onBindingPermissionChange(s.bindings.value[0], 'db_c_status', false)
    assert.equal(
      await s.onBindingPermissionChange(s.bindings.value[0], 'db_rud_status', true),
      false
    )
    gate.reject(Error())
    assert.equal(await pending, false)
    assert.equal(s.bindings.value[0].db_c_status, 1)
    assert.equal(
      await s.onBindingPermissionChange(binding(2, { environment: 2 }), 'db_rud_status', true),
      false
    )
    assert.equal(calls.length, 1)
  } finally {
    s.dispose()
  }
})
test('delete confirmation freezes ID, keeps failure retryable and guards stale identities', async () => {
  let fail = true
  const ids = [],
    s = page({
      deleteDataFactoryDatasourceAlias: async (id) => {
        ids.push(id)
        if (fail) throw Error()
        return { msg: 'ok' }
      },
    })
  try {
    const record = alias()
    s.onDelete(record)
    record.id = 2
    const dialog = s.confirmations[0]
    assert.equal(dialog.config.okButtonProps.status, 'danger')
    assert.equal(await dialog.config.onBeforeOk(), false)
    fail = false
    assert.equal(await dialog.config.onBeforeOk(), true)
    assert.deepEqual(ids, [1, 1])
    dialog.close()
    s.onDelete(alias(3))
    s.user.roleId = 2
    assert.equal(s.confirmations[1].closed, true)
    assert.equal(await s.confirmations[1].config.onBeforeOk(), false)
  } finally {
    s.dispose()
  }
})
test('binding editor keeps environment zero, masks bound choices, filters source type', async () => {
  const s = bindingEditor({
    getSystemDataSource: async () => ({
      data: [connection(1), connection(2, { db_type: 10, source_category: 1 })],
    }),
  })
  try {
    s.props.bindings = [binding()]
    s.open()
    await flush()
    assert.equal(s.bindingEnvironmentOptions.value[0].disabled, true)
    assert.equal(s.dataSourceOptions.value.length, 1)
    assert.equal(s.dataSourceOptions.value[0].value, 1)
    s.close()
    s.open(binding(5, { redis_db: 0 }))
    assert.equal(s.draft.environment, 0)
    assert.equal(s.draft.target.redis_db, 0)
    assert.equal(s.editingId.value, 5)
  } finally {
    s.dispose()
  }
})
test('binding save snapshots target and uses distinct create/edit payloads', async () => {
  const calls = [],
    gate = deferred(),
    s = bindingEditor({
      postDataFactoryDatasourceBinding: (payload) => {
        calls.push(payload)
        return gate.promise
      },
      putDataFactoryDatasourceBinding: async (payload) => {
        calls.push(payload)
        return { msg: 'ok' }
      },
    })
  try {
    s.open()
    await flush()
    s.draft.environment = 0
    s.draft.dataSource = 1
    s.draft.target.redis_db = 0
    const pending = s.save()
    s.draft.target.redis_db = 2
    assert.equal(await s.save(), false)
    assert.equal(calls[0].environment, 0)
    assert.equal(calls[0].redis_db, 0)
    assert.equal(calls[0].datasource_alias, 1)
    gate.resolve({ msg: 'ok' })
    assert.equal(await pending, true)
    s.open(binding(7, { environment: 2, db_rud_status: 1 }))
    await flush()
    assert.equal(await s.save(), true)
    assert.equal(calls[1].id, 7)
    assert.equal(calls[1].db_rud_status, 0)
    assert.equal('environment' in calls[1], false)
    assert.equal('datasource_alias' in calls[1], false)
  } finally {
    s.dispose()
  }
})
test('binding option failure retries and closed/stale requests cannot overwrite new options', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const s = bindingEditor({ getSystemDataSource: () => (++count === 1 ? a.promise : b.promise) })
  try {
    s.open()
    s.close()
    s.open()
    a.resolve({ data: [connection(99)] })
    await flush()
    assert.deepEqual(s.dataSourceOptions.value, [])
    assert.equal(s.optionsLoading.value, true)
    b.reject(Error('options unavailable'))
    await flush()
    assert.equal(s.optionsError.value, 'options unavailable')
    assert.equal(s.optionsLoading.value, false)
  } finally {
    s.dispose()
  }
})
test('binding rejects duplicate environment and failed submit leaves draft intact', async () => {
  const s = bindingEditor({
    postDataFactoryDatasourceBinding: async () => {
      throw Error()
    },
  })
  try {
    s.open()
    await flush()
    s.draft.environment = 0
    s.draft.dataSource = 1
    s.props.bindings = [binding()]
    assert.equal(await s.save(), false)
    s.props.bindings = []
    s.draft.target.database_name = 'chosen'
    assert.equal(await s.save(), false)
    assert.equal(s.draft.target.database_name, 'chosen')
    assert.equal(s.visible.value, true)
  } finally {
    s.dispose()
  }
})
test('SQL drawer uses logical query protocol and allows environment zero', async () => {
  const calls = [],
    gate = deferred(),
    s = query({
      queryLogicalDataSource: (payload) => {
        calls.push(payload)
        return gate.promise
      },
    })
  try {
    s.open(alias())
    s.queryDrawer.statement = ' SELECT 1 LIMIT 20 '
    const pending = s.onQueryDatasource()
    await s.onQueryDatasource()
    assert.deepEqual(calls, [
      { datasource_alias_id: 1, project_product_id: 10, test_env: 0, sql: 'SELECT 1 LIMIT 20' },
    ])
    gate.resolve({ data: { rows: [1] }, msg: 'ok' })
    await pending
    assert.deepEqual(s.queryDrawer.result, { rows: [1] })
  } finally {
    s.dispose()
  }
})
test('Redis and ES drawers preserve operation protocol and reject nonobject DSL', async () => {
  const calls = [],
    s = query({
      postDataSourceExecution: async (payload) => {
        calls.push(payload)
        return { data: { ok: true }, msg: 'ok' }
      },
    })
  try {
    s.open(alias(1, { db_type: 10 }))
    s.queryDrawer.statement = 'GET example'
    await s.onQueryDatasource()
    assert.equal(calls[0].operation_config, 'GET example')
    assert.equal(calls[0].action, 'execute')
    s.open(alias(2, { db_type: 20 }))
    s.queryDrawer.index = 'example-*'
    s.queryDrawer.statement = '[]'
    await s.onQueryDatasource()
    assert.equal(calls.length, 1)
    s.queryDrawer.statement = '{"query":{"match_all":{}}}'
    await s.onQueryDatasource()
    assert.deepEqual(calls[1].operation_config, {
      index: 'example-*',
      query: { query: { match_all: {} } },
    })
  } finally {
    s.dispose()
  }
})
test('query target, environment, close and cache changes discard late results', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const s = query({ queryLogicalDataSource: () => (++count === 1 ? a.promise : b.promise) })
  try {
    s.open(alias())
    s.queryDrawer.statement = 'SELECT 1 LIMIT 20'
    const old = s.onQueryDatasource()
    s.queryDrawer.testEnv = 1
    s.queryDrawer.statement = 'SELECT 2 LIMIT 20'
    const fresh = s.onQueryDatasource()
    a.resolve({ data: { old: 1 } })
    await old
    assert.equal(s.queryDrawer.loading, true)
    assert.equal(s.queryDrawer.result, null)
    s.close()
    b.resolve({ data: { new: 1 } })
    await fresh
    assert.equal(s.queryDrawer.result, null)
    assert.equal(s.queryDrawer.visible, false)
    s.open(alias())
    s.lifecycle.deactivate()
    assert.equal(s.queryDrawer.visible, false)
  } finally {
    s.dispose()
  }
})
test('query failure releases loading and retains statement for retry', async () => {
  const s = query({
    queryLogicalDataSource: async () => {
      throw Error()
    },
  })
  try {
    s.open(alias())
    s.queryDrawer.statement = 'SELECT 1 LIMIT 20'
    await s.onQueryDatasource()
    assert.equal(s.queryDrawer.loading, false)
    assert.equal(s.queryDrawer.statement, 'SELECT 1 LIMIT 20')
  } finally {
    s.dispose()
  }
})
test('table discovery includes product, alias, environment zero and paginates filtered rows', async () => {
  const calls = [],
    s = tables({
      postDataFactoryDiscoverTables: async (payload) => {
        calls.push(payload)
        return { data: Array.from({ length: 45 }, (_, i) => ({ name: `table-${i}` })) }
      },
    })
  try {
    await flush()
    assert.equal(calls[0].test_env, 0)
    assert.equal(calls[0].project_product, 10)
    assert.equal(s.pagination.pageCount, 45)
    s.pagination.page = 3
    assert.equal(s.pagedTables.value.length, 5)
    s.keyword.value = 'table-4'
    await flush()
    assert.equal(s.pagination.page, 1)
    assert.equal(s.pagination.pageCount, 6)
  } finally {
    s.dispose()
  }
})
test('table discovery ignores old responses after binding changes and cache suspension', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const s = tables({ postDataFactoryDiscoverTables: () => (++count === 1 ? a.promise : b.promise) })
  try {
    s.props.bindings = [binding(2, { environment: 1 })]
    await flush()
    a.resolve({ data: [{ name: 'old' }] })
    await flush()
    assert.deepEqual(s.tables.value, [])
    assert.equal(s.loading.value, true)
    s.lifecycle.deactivate()
    b.resolve({ data: [{ name: 'new' }] })
    await flush()
    assert.deepEqual(s.tables.value, [])
  } finally {
    s.dispose()
  }
})
test('schema drawer close prevents a late result from updating a reopened target', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const s = tables({ postDataFactoryDiscoverTable: () => (++count === 1 ? a.promise : b.promise) })
  try {
    await flush()
    const old = s.viewSchema({ name: 'old' })
    s.schemaVisible.value = false
    const fresh = s.viewSchema({ name: 'new' })
    a.resolve({ data: { columns: [{ name: 'old' }] } })
    await old
    assert.equal(s.schema.value, null)
    assert.equal(s.schemaLoading.value, true)
    b.resolve({ data: { columns: [{ name: 'new' }] } })
    await fresh
    assert.equal(s.schema.value.columns[0].name, 'new')
  } finally {
    s.dispose()
  }
})
test('generation submits batches of five with module leaf and retains failed selection', async () => {
  const calls = [],
    s = tables({
      postDataFactoryEntityBatchGenerate: async (payload) => {
        calls.push(payload)
        return {
          data: {
            items: payload.tables.map((row, i) => ({
              table_name: row.table_name,
              status: i === 1 ? 'failed' : 'success',
              message: 'fixture',
            })),
          },
        }
      },
    })
  try {
    await flush()
    s.tables.value = Array.from({ length: 6 }, (_, i) => ({
      name: `table-${i}`,
      key: `key-${i}`,
      schema_name: 'public',
    }))
    s.selectedKeys.value = s.tables.value.map((row) => row.key)
    s.openGenerate()
    s.generateForm.module = [1, 9]
    assert.equal(await s.generate(), false)
    assert.equal(calls.length, 2)
    assert.equal(calls[0].tables.length, 5)
    assert.equal(calls[1].tables.length, 1)
    assert.equal(calls[0].module, 9)
    assert.equal(calls[0].test_env, 0)
    assert.deepEqual(s.selectedKeys.value, ['key-1'])
  } finally {
    s.dispose()
  }
})
test('generation prevents duplicates and stops further batches after context changes', async () => {
  const gate = deferred(),
    calls = [],
    s = tables({
      postDataFactoryEntityBatchGenerate: (payload) => {
        calls.push(payload)
        return gate.promise
      },
    })
  try {
    await flush()
    s.tables.value = Array.from({ length: 7 }, (_, i) => ({ name: `t${i}`, key: `k${i}` }))
    s.selectedKeys.value = s.tables.value.map((row) => row.key)
    s.openGenerate()
    s.generateForm.module = 9
    const pending = s.generate()
    assert.equal(await s.generate(), false)
    s.props.productId = 11
    await flush()
    gate.resolve({ data: { items: [] } })
    await pending
    assert.equal(calls.length, 1)
    assert.equal(s.generating.value, false)
    assert.deepEqual(s.generationResults.value, [])
  } finally {
    s.dispose()
  }
})
test('generation request failure creates retryable per-table results', async () => {
  const s = tables({
    postDataFactoryEntityBatchGenerate: async () => {
      throw Error('fixture failure')
    },
  })
  try {
    await flush()
    s.tables.value = [{ name: 'example', key: 'key' }]
    s.selectedKeys.value = ['key']
    s.openGenerate()
    s.generateForm.module = 9
    await s.generate()
    assert.equal(s.generationResults.value[0].status, 'failed')
    assert.deepEqual(s.selectedKeys.value, ['key'])
    assert.equal(s.generateVisible.value, true)
  } finally {
    s.dispose()
  }
})
test('shared target edits emit replacement values without mutating parent objects', async () => {
  const original = Object.freeze({ database_name: 'old', schema_name: 'public', redis_db: null }),
    s = fields({}, { modelValue: original })
  try {
    s.databaseName.value = 'new'
    assert.equal(original.database_name, 'old')
    assert.deepEqual(s.events.at(-1), [
      'update:modelValue',
      { database_name: 'new', schema_name: 'public', redis_db: null },
    ])
    s.schemaName.value = 'other'
    assert.equal(original.schema_name, 'public')
  } finally {
    s.dispose()
  }
})
test('shared target preserves Redis DB zero and resets only when changing connection', async () => {
  const s = fields(
    {},
    { sourceType: 10, modelValue: { database_name: '', schema_name: '', redis_db: 0 } }
  )
  try {
    assert.equal(s.redisDb.value, 0)
    assert.equal(s.events.length, 0)
    s.props.sourceId = 2
    await flush()
    assert.equal(s.events.at(-1)[1].redis_db, 0)
  } finally {
    s.dispose()
  }
})
test('shared target discoveries and tests cannot update after close or target change', async () => {
  const a = deferred(),
    b = deferred(),
    testGate = deferred()
  let count = 0
  const s = fields({
    getDataSourceDatabases: () => (++count === 1 ? a.promise : b.promise),
    postDataSourceExecution: () => testGate.promise,
  })
  try {
    const pending = s.testTarget()
    await s.testTarget()
    s.props.sourceId = 2
    a.resolve({ data: [{ name: 'old' }] })
    await flush()
    assert.deepEqual(s.databases.value, [])
    assert.equal(s.loading.databases, true)
    testGate.resolve({ data: { connected: true } })
    await pending
    assert.deepEqual(s.notices, [])
    s.lifecycle.unmount()
    b.resolve({ data: [{ name: 'late' }] })
    await flush()
    assert.deepEqual(s.databases.value, [])
  } finally {
    s.dispose()
  }
})

test('cleared alias type and query environment remain validation errors', async () => {
  const a = editor(),
    q = query()
  try {
    a.open()
    a.draft.name = 'Example'
    a.draft.dbType = undefined
    assert.equal(await a.save(), false)
    assert.equal(a.notices.at(-1), '请选择数据库类型')
    q.open(alias())
    q.queryDrawer.statement = 'SELECT 1 LIMIT 20'
    q.queryDrawer.testEnv = undefined
    await q.onQueryDatasource()
    assert.equal(q.notices.at(-1), '请选择测试环境')
  } finally {
    a.dispose()
    q.dispose()
  }
})

test('binding submit after alias or identity changes cannot emit saved', async () => {
  const gate = deferred(),
    s = bindingEditor({ putDataFactoryDatasourceBinding: () => gate.promise })
  try {
    s.open(binding())
    await flush()
    const pending = s.save()
    s.props.alias = alias(2)
    assert.equal(s.visible.value, false)
    gate.resolve({ msg: 'ok' })
    assert.equal(await pending, false)
    assert.deepEqual(s.events, [])
  } finally {
    s.dispose()
  }
})

test('shared PostgreSQL schema discoveries reject late results from prior databases', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const s = fields(
    { getDataSourceSchemas: () => (++count === 1 ? a.promise : b.promise) },
    { sourceType: 1 }
  )
  try {
    s.props.modelValue = { database_name: 'other', schema_name: '', redis_db: null }
    a.resolve({ data: [{ name: 'old' }] })
    await flush()
    assert.deepEqual(s.schemas.value, [])
    assert.equal(s.loading.schemas, true)
    b.resolve({ data: { items: [{ name: 'public' }, 'custom'] } })
    await flush()
    assert.deepEqual(s.schemas.value, ['public', 'custom'])
    assert.equal(s.loading.schemas, false)
  } finally {
    s.dispose()
  }
})

test('PostgreSQL binding discovery cannot install schemas from a previous binding', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const pg = connection(1, { db_type: 1 })
  const s = tables(
    { getDataSourceSchemas: () => (++count === 1 ? a.promise : b.promise) },
    { bindings: [binding(1, { data_source: pg, schema_name: 'public' })] }
  )
  try {
    await flush()
    s.props.bindings = [
      binding(2, { data_source: pg, database_name: 'other', schema_name: 'custom' }),
    ]
    await flush()
    assert.equal(s.selectedSchema.value, 'custom')
    a.resolve({ data: [{ name: 'old' }] })
    await flush()
    assert.deepEqual(s.schemaOptions.value, [])
    assert.equal(s.schemasLoading.value, true)
    b.resolve({ data: [{ name: 'custom' }] })
    await flush()
    assert.deepEqual(s.schemaOptions.value, ['custom'])
  } finally {
    s.dispose()
  }
})
