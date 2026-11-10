import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { setupEntity, entity, field } from './helpers/factory-entity-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/data-factory/entity')
const page = (api = {}) =>
  setupEntity(
    'index',
    'rows,listLoading,loadError,pagination,entityConditionItems,doRefresh,onSearch,onResetSearch,onNavigationFilterChange,loadUsers,loadEnums,usersLoading,usersError,enumsError,aliases,editorRef,batchRef,fieldsRef,logsRef,navigationCreateRef,openEntity,openFields,openBatchGenerate,openStatusLogs,onEntitySaving,onFieldSaving,switchEntityStatus,removeEntity,statusIds,deletingIds',
    api
  )
const editor = (api = {}) =>
  setupEntity(
    'EntityEditor',
    'entityForm,editingId,entityVisible,entitySaving,syncFieldsAfterSave,open,saveEntity,loadEntityTables,onEntityTableChange,onEntityProjectChange,onEntityDatasourceChange,entityTableOptions,entityTableLoading,entityTableRefreshLoading,entityDiscoveredColumns,schemaLoading,discoveryError,syncError,aliases',
    api
  )
const batch = (api = {}) =>
  setupEntity(
    'EntityBatchDrawer',
    'batchForm,batchRows,batchSelectedKeys,batchVisible,batchLoading,batchGenerating,loadError,generateError,open,loadBatchTables,onBatchSelectionChange,batchGenerateEntities',
    api
  )
const fields = (api = {}) =>
  setupEntity(
    'EntityFieldsEditor',
    'open,fieldRows,fieldVisible,fieldLoading,fieldSaving,fieldSyncLoading,fieldPreviewLoading,loadError,operationError,currentEntity,replaceFields,saveFields,syncCurrentEntityFields,previewFieldValues,dependencies,applyEnum',
    api
  )
const logs = (api = {}) =>
  setupEntity(
    'EntityStatusLogs',
    'open,visible,rows,loading,loadError,pagination,reload:load,onSizeChange',
    api
  )
const enums = (api = {}) =>
  setupEntity('EntityEnumEditor', 'open,enumOptionRows,enumEditorVisible,saveEnumOptions', api)
function valid(s) {
  Object.assign(s.entityForm, {
    project_product: 10,
    module: 20,
    datasource_alias: 30,
    name: 'Example',
    table_name: 'records',
    schema_name: 'public',
  })
}

test('six owned SFCs compile with explicit setup bindings', () => {
  for (const file of [
    'index.vue',
    'components/EntityEditor.vue',
    'components/EntityBatchDrawer.vue',
    'components/EntityFieldsEditor.vue',
    'components/EntityEnumEditor.vue',
    'components/EntityStatusLogs.vue',
  ]) {
    const filename = path.join(base, file),
      { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: file })
    assert.deepEqual(
      compileTemplate({
        source: descriptor.template.content,
        filename,
        id: file,
        compilerOptions: { bindingMetadata: script.bindings },
      }).errors,
      []
    )
  }
})
test('search config isolates instances, converts product/module values, supports collections and resets pagination', async () => {
  const calls = [],
    s = page({
      getDataFactoryEntity: async (p) => {
        calls.push(p)
        return { data: [], totalSize: 0 }
      },
    }),
    other = page()
  try {
    s.entityConditionItems.find((i) => i.key === 'project_product').value = [2, 10]
    s.entityConditionItems.find((i) => i.key === 'module').value = 20
    s.entityConditionItems.find((i) => i.key === 'status').value = [0, 1]
    s.entityConditionItems.find((i) => i.key === 'datasource_alias').value = [30, 31]
    s.entityConditionItems.find((i) => i.key === 'update_user').value = [1, 2]
    s.pagination.page = 5
    await s.onSearch()
    assert.deepEqual(calls[0], {
      project_product: 10,
      module: 20,
      status__in: '0,1',
      datasource_alias__in: '30,31',
      update_user__in: '1,2',
      page: 1,
      pageSize: 20,
    })
    assert.deepEqual(other.entityConditionItems.find((i) => i.key === 'status').value, [])
    await s.onResetSearch()
    assert.deepEqual(calls.at(-1), { page: 1, pageSize: 20 })
  } finally {
    s.dispose()
    other.dispose()
  }
})
test('latest list controls data and loading; failure recovers without clearing valid data', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const s = page({
    getDataFactoryEntity: () =>
      ++count === 1 ? a.promise : count === 2 ? b.promise : Promise.reject(Error('fixture')),
  })
  try {
    const first = s.doRefresh(),
      second = s.doRefresh()
    a.resolve({ data: [entity(1)], totalSize: 1 })
    await first
    assert.equal(s.listLoading.value, true)
    b.resolve({ data: [entity(2)], totalSize: 4 })
    await second
    assert.equal(s.rows.value[0].id, 2)
    assert.equal(s.pagination.pageCount, 4)
    await s.doRefresh()
    assert.equal(s.loadError.value, true)
    assert.equal(s.listLoading.value, false)
    assert.equal(s.rows.value[0].id, 2)
  } finally {
    s.dispose()
  }
})
test('environment change clears visible old list and re-reads; cached stop ignores late replies', async () => {
  const pending = deferred()
  let count = 0
  const s = page({
    getDataFactoryEntity: () =>
      ++count === 1 ? pending.promise : Promise.resolve({ data: [entity(2)], totalSize: 1 }),
  })
  try {
    const first = s.doRefresh()
    s.lifecycle.deactivate()
    pending.resolve({ data: [entity()], totalSize: 10 })
    await first
    assert.deepEqual(s.rows.value, [])
    s.lifecycle.activate()
    await flush()
    assert.equal(count, 2)
    s.user.selected_environment = 1
    await flush()
    assert.equal(count, 3)
    assert.equal(s.rows.value[0].id, 2)
  } finally {
    s.dispose()
  }
})
test('each alias list owns its request lifecycle and retry; editor product change cannot overwrite page options', async () => {
  const a = deferred(),
    b = deferred()
  const s = page({
      getDataFactoryDatasourceAlias: (p) => (p.project_product === 10 ? a.promise : b.promise),
    }),
    e = editor()
  try {
    const first = s.aliases.load(10),
      second = s.aliases.load(11)
    a.resolve({ data: [{ id: 30, name: 'Old' }] })
    await first
    assert.equal(s.aliases.loading.value, true)
    b.resolve({ data: [{ id: 31, name: 'New' }] })
    await second
    assert.equal(s.aliases.options.value[0].id, 31)
    e.open(undefined, { projectProduct: 12, module: 20 })
    await flush()
    assert.equal(s.aliases.options.value[0].id, 31)
  } finally {
    s.dispose()
    e.dispose()
  }
})
test('entity draft preserves cleanup zero, copies IDs and resets create defaults synchronously', () => {
  const s = editor()
  try {
    s.open(entity())
    assert.equal(s.entityForm.cleanup_order, 0)
    assert.equal(s.entityForm.datasource_alias, 30)
    s.close()
    s.open(undefined, { projectProduct: 10, module: 20 })
    assert.equal(s.editingId.value, null)
    assert.equal(s.entityForm.module, 20)
    assert.equal(s.syncFieldsAfterSave.value, true)
    assert.equal(s.entityForm.cleanup_order, 100)
  } finally {
    s.dispose()
  }
})
test('entity create snapshots leaf IDs, excludes editor ID, blocks duplicate save and synchronizes selected schema', async () => {
  const pending = deferred(),
    created = [],
    synced = [],
    discovered = [],
    s = editor({
      postDataFactoryEntity: (p) => {
        created.push(p)
        return pending.promise
      },
      postDataFactoryDiscoverTable: async (p) => {
        discovered.push(p)
        return { data: { columns: [field()] } }
      },
      postDataFactoryFieldBatchSave: async (p) => {
        synced.push(p)
        return { msg: 'ok' }
      },
    })
  try {
    s.open()
    valid(s)
    s.entityForm.project_product = [2, 10]
    const saving = s.saveEntity()
    assert.equal(await s.saveEntity(), false)
    s.entityForm.name = 'Later'
    pending.resolve({ data: { id: 8 }, msg: 'ok' })
    assert.equal(await saving, true)
    assert.equal(created.length, 1)
    assert.equal(created[0].name, 'Example')
    assert.equal(created[0].project_product, 10)
    assert.equal('id' in created[0], false)
    assert.equal(discovered[0].schema_name, 'public')
    assert.equal(discovered[0].test_env, 0)
    assert.equal(synced[0].entity_id, 8)
    assert.equal(synced[0].replace, true)
    assert.equal(s.entityVisible.value, false)
    assert.equal(s.entitySaving.value, false)
  } finally {
    s.dispose()
  }
})
test('partial entity save failure retains returned ID, notifies list, and retry updates instead of duplicate create', async () => {
  let creates = 0,
    updates = 0,
    syncs = 0
  const s = editor({
    postDataFactoryEntity: async () => {
      creates++
      return { data: { id: 7 }, msg: 'ok' }
    },
    putDataFactoryEntity: async (p) => {
      updates++
      assert.equal(p.id, 7)
      return { data: { id: 7 }, msg: 'ok' }
    },
    postDataFactoryDiscoverTable: async () => ({ data: { columns: [field()] } }),
    postDataFactoryFieldBatchSave: async () => {
      if (++syncs === 1) throw Error('fixture')
      return { msg: 'ok' }
    },
  })
  try {
    s.open()
    valid(s)
    assert.equal(await s.saveEntity(), false)
    assert.equal(s.editingId.value, 7)
    assert.match(s.syncError.value, /实体已保存/)
    assert.equal(s.entityVisible.value, true)
    assert.equal(s.events.filter((e) => e[0] === 'saved').length, 1)
    assert.equal(await s.saveEntity(), true)
    assert.equal(creates, 1)
    assert.equal(updates, 1)
    assert.equal(syncs, 2)
  } finally {
    s.dispose()
  }
})
test('entity metadata save failure retains draft and can retry; no schema discovery when synchronization off', async () => {
  let count = 0,
    discovery = 0
  const s = editor({
    putDataFactoryEntity: async () => {
      if (++count === 1) throw Error('fixture')
      return { data: { id: 1 }, msg: 'ok' }
    },
    postDataFactoryDiscoverTable: async () => {
      discovery++
      return { data: { columns: [] } }
    },
  })
  try {
    s.open(entity())
    await flush()
    assert.equal(await s.saveEntity(), false)
    assert.equal(s.entityVisible.value, true)
    assert.equal(s.entityForm.name, 'Entity 1')
    assert.equal(await s.saveEntity(), true)
    assert.equal(discovery, 0)
  } finally {
    s.dispose()
  }
})
test('table discovery and schema changes discard old responses, preserve manual name input, clear loading on clear', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const s = editor({ postDataFactoryDiscoverTable: () => (++count === 1 ? a.promise : b.promise) })
  try {
    s.open()
    valid(s)
    s.entityForm.table_name = 'first'
    const first = s.onEntityTableChange('first')
    s.entityForm.table_name = 'second'
    const second = s.onEntityTableChange('second')
    a.resolve({ data: { columns: [field('old')], table_comment: 'Old' } })
    await first
    assert.equal(s.schemaLoading.value, true)
    s.entityForm.name = 'Manual'
    b.resolve({
      data: { columns: [field('new')], table_comment: 'Suggested', schema_name: 'public' },
    })
    await second
    assert.equal(s.entityForm.name, 'Manual')
    assert.equal(s.entityDiscoveredColumns.value[0].name, 'new')
    s.entityForm.table_name = ''
    await s.onEntityTableChange('')
    assert.equal(s.schemaLoading.value, false)
  } finally {
    s.dispose()
  }
})
test('entity environment change after commit prevents follow-up sync and stale saved events', async () => {
  const pending = deferred()
  let syncs = 0
  const s = editor({
    postDataFactoryEntity: () => pending.promise,
    postDataFactoryFieldBatchSave: async () => {
      syncs++
      return { msg: 'ok' }
    },
  })
  try {
    s.open()
    valid(s)
    const saving = s.saveEntity()
    s.user.selected_environment = 1
    pending.resolve({ data: { id: 8 }, msg: 'ok' })
    assert.equal(await saving, false)
    assert.equal(syncs, 0)
    assert.equal(s.entityVisible.value, false)
    assert.equal(
      s.events.some((e) => e[0] === 'saved'),
      false
    )
  } finally {
    s.dispose()
  }
})
test('batch table identity distinguishes schemas, existing rows are disabled and selection excludes them', async () => {
  const s = batch({
    postDataFactoryDiscoverTables: async () => ({
      data: [
        { name: 'items', schema_name: 'first' },
        { name: 'items', schema_name: 'second' },
      ],
    }),
    getDataFactoryEntity: async () => ({
      data: [entity(1, { table_name: 'items', schema_name: 'first' })],
    }),
  })
  try {
    s.open({ projectProduct: 10, module: 20 })
    s.batchForm.datasource_alias = 30
    await s.loadBatchTables()
    assert.equal(s.batchRows.value.length, 2)
    assert.notEqual(s.batchRows.value[0].key, s.batchRows.value[1].key)
    assert.equal(s.batchRows.value[0].disabled, true)
    s.onBatchSelectionChange(s.batchRows.value.map((row) => row.key))
    assert.deepEqual(s.batchSelectedKeys.value, [s.batchRows.value[1].key])
    s.batchForm.module = 21
    assert.deepEqual(s.batchRows.value, [])
    assert.deepEqual(s.batchSelectedKeys.value, [])
  } finally {
    s.dispose()
  }
})
test('batch writes immutable selected rows and options, supports partial failures and explicit retry', async () => {
  const calls = [],
    pending = deferred()
  const s = batch({
    postDataFactoryDiscoverTables: async () => ({ data: ['first', 'second'] }),
    getDataFactoryEntity: async () => ({ data: [] }),
    postDataFactoryEntityBatchGenerate: (p) => {
      calls.push(p)
      return pending.promise
    },
  })
  try {
    s.open({ projectProduct: 10, module: 20 })
    s.batchForm.datasource_alias = 30
    await s.loadBatchTables()
    const saving = s.batchGenerateEntities()
    await s.batchGenerateEntities()
    s.batchRows.value[0].name = 'Later'
    assert.equal(calls.length, 1)
    assert.equal(calls[0].tables[0].name, 'first')
    assert.equal(calls[0].test_env, 0)
    pending.resolve({
      data: {
        items: [
          { table_name: 'first', status: 'success', message: 'ok' },
          { table_name: 'second', status: 'failed', message: 'fixture' },
        ],
        success: 1,
        failed: 1,
      },
    })
    await saving
    assert.equal(s.batchVisible.value, true)
    assert.equal(s.batchRows.value[0].disabled, true)
    assert.deepEqual(s.batchSelectedKeys.value, [s.batchRows.value[1].key])
    assert.equal(s.batchGenerating.value, false)
  } finally {
    s.dispose()
  }
})
test('batch failure retains selections, close invalidates late success and prevents duplicate physical requests', async () => {
  let count = 0
  const pending = deferred(),
    s = batch({
      postDataFactoryDiscoverTables: async () => ({ data: ['records'] }),
      getDataFactoryEntity: async () => ({ data: [] }),
      postDataFactoryEntityBatchGenerate: () =>
        ++count === 1 ? Promise.reject(Error('fixture')) : pending.promise,
    })
  try {
    s.open({ projectProduct: 10, module: 20 })
    s.batchForm.datasource_alias = 30
    await s.loadBatchTables()
    await s.batchGenerateEntities()
    assert.equal(s.generateError.value, true)
    assert.equal(s.batchSelectedKeys.value.length, 1)
    const saving = s.batchGenerateEntities()
    s.close()
    s.open()
    assert.equal(s.batchVisible.value, false)
    pending.resolve({ data: { items: [], success: 1, failed: 0 } })
    await saving
    assert.equal(
      s.events.some((e) => e[0] === 'saved'),
      false
    )
    assert.equal(s.batchGenerating.value, false)
  } finally {
    s.dispose()
  }
})
test('field normalization and payload do not mutate records and omit preview/audit state for every generator', () => {
  const s = fields()
  try {
    const g = s.load('generators.ts'),
      original = field('kind', {
        generator_type: 9,
        generator_config: { options: [{ label: 'Zero', value: 0 }], value: '0' },
        enum_values: [0],
      })
    const row = g.normalizeFieldRow(original)
    row.preview_message = 'UI'
    row.generator_config.options[0].label = 'Edited'
    assert.equal(original.generator_config.options[0].label, 'Zero')
    const payload = g.buildFieldPayloadItem(row)
    assert.equal(payload.generator_config.value, 0)
    assert.equal('preview_message' in payload, false)
    assert.equal('generator_config_value' in payload, false)
    assert.equal(row.generator_config.value, '0')
    assert.equal(
      g.buildFieldPayloadItem(
        g.normalizeFieldRow(
          field('skip', {
            generator_type: 0,
            generator_config: { reason: 'auto', value: 'unused' },
          })
        )
      ).generator_config.value,
      undefined
    )
    for (const type of [1, 2, 3, 4, 5, 6, 7, 9, 11, 13])
      assert.equal(
        g.buildFieldPayloadItem(g.normalizeFieldRow(field('f', { generator_type: type })))
          .generator_type,
        type
      )
  } finally {
    s.dispose()
  }
})
test('field rules load independently; failed initial reads cannot accidentally submit an empty replacement', async () => {
  let count = 0,
    writes = 0
  const s = fields({
    getDataFactoryField: async () => {
      if (++count === 1) throw Error('fixture')
      return { data: [field()] }
    },
    postDataFactoryFieldBatchSave: async () => {
      writes++
      return { msg: 'ok' }
    },
  })
  try {
    s.open(entity())
    await flush()
    assert.equal(s.loadError.value, true)
    assert.equal(await s.saveFields(), false)
    assert.equal(writes, 0)
    s.close()
    s.open(entity())
    await flush()
    assert.equal(s.fieldRows.value.length, 1)
    assert.equal(await s.saveFields(), true)
    assert.equal(writes, 1)
  } finally {
    s.dispose()
  }
})
test('field saves snapshot rules and replace switch, fail without losing edits, and allow retry', async () => {
  const calls = [],
    pending = deferred(),
    s = fields({
      getDataFactoryField: async () => ({ data: [field()] }),
      postDataFactoryFieldBatchSave: (p) => {
        calls.push(p)
        return calls.length === 1 ? pending.promise : Promise.resolve({ msg: 'ok' })
      },
    })
  try {
    s.open(entity(7))
    await flush()
    s.replaceFields.value = false
    const saving = s.saveFields()
    assert.equal(await s.saveFields(), false)
    s.fieldRows.value[0].label = 'Later'
    assert.equal(calls[0].fields[0].label, 'id')
    assert.equal(calls[0].entity_id, 7)
    assert.equal(calls[0].replace, false)
    pending.reject(Error('fixture'))
    assert.equal(await saving, false)
    assert.equal(s.fieldRows.value[0].label, 'Later')
    assert.equal(s.fieldVisible.value, true)
    assert.equal(await s.saveFields(), true)
  } finally {
    s.dispose()
  }
})
test('field previews protect newer draft revisions and release loading after failures or stale data', async () => {
  const pending = deferred(),
    s = fields({
      getDataFactoryField: async () => ({ data: [field()] }),
      postDataFactoryFieldPreviewValues: () => pending.promise,
    })
  try {
    s.open(entity())
    await flush()
    const preview = s.previewFieldValues()
    s.fieldRows.value[0].generator_config_value = 'New'
    pending.resolve({ data: { fields: [{ name: 'id', value: 99, valid: true }] } })
    await preview
    assert.equal(s.fieldRows.value[0].preview_value, undefined)
    assert.equal(s.fieldPreviewLoading.value, false)
  } finally {
    s.dispose()
  }
})
test('field schema sync retains chosen generator settings, includes schema and discards after environment change', async () => {
  const calls = [],
    pending = deferred(),
    s = fields({
      getDataFactoryField: async () => ({
        data: [
          field('id', {
            generator_type: 3,
            generator_config: { min: 10, max: 20 },
            label: 'Custom',
          }),
        ],
      }),
      postDataFactoryDiscoverTable: (p) => {
        calls.push(p)
        return pending.promise
      },
    })
  try {
    s.open(entity())
    await flush()
    const syncing = s.syncCurrentEntityFields()
    assert.equal(calls[0].schema_name, 'public')
    pending.resolve({ data: { columns: [field('id', { label: 'Discovered' }), field('extra')] } })
    await syncing
    assert.equal(s.fieldRows.value[0].label, 'Custom')
    assert.equal(s.fieldRows.value[0].generator_type, 3)
    assert.equal(s.fieldRows.value.length, 2)
    s.user.selected_environment = 1
    assert.equal(s.fieldVisible.value, false)
    assert.deepEqual(s.fieldRows.value, [])
  } finally {
    s.dispose()
  }
})
test('enum dialog edits a private draft, casts integer/boolean zero, validates and emits only explicit apply', () => {
  const s = enums(),
    row = field('state', {
      platform_type: 'integer',
      generator_type: 9,
      generator_config: { values: [0, 1], value: 0 },
    })
  try {
    s.open({ ...row, generator_config_value: '0', preview_valid: true, preview_message: '' })
    s.enumOptionRows.value[0].label = 'Zero'
    assert.equal(row.generator_config.options, undefined)
    assert.equal(s.events.length, 0)
    assert.equal(s.saveEnumOptions(), true)
    assert.deepEqual(s.events[0], [
      'apply',
      'state',
      [
        { label: 'Zero', value: 0 },
        { label: '1', value: 1 },
      ],
    ])
    s.open({ ...row, generator_config_value: '0', preview_valid: true, preview_message: '' })
    s.enumOptionRows.value = [{ label: 'Bad', value: 'x' }]
    assert.equal(s.saveEnumOptions(), false)
    assert.equal(s.enumEditorVisible.value, true)
    s.close()
    assert.equal(s.enumEditorVisible.value, false)
  } finally {
    s.dispose()
  }
})
test('field enum apply targets named row and does not commit to backend until save', async () => {
  let writes = 0
  const s = fields({
    getDataFactoryField: async () => ({ data: [field('kind', { generator_type: 9 })] }),
    postDataFactoryFieldBatchSave: async () => {
      writes++
      return { msg: 'ok' }
    },
  })
  try {
    s.open(entity())
    await flush()
    s.applyEnum('kind', [
      { label: 'No', value: false },
      { label: 'Yes', value: true },
    ])
    assert.equal(writes, 0)
    assert.equal(s.fieldRows.value[0].generator_config.value, false)
    await s.saveFields()
    assert.equal(writes, 1)
  } finally {
    s.dispose()
  }
})
test('dependency options use product-scoped modules, preload saved entity/field paths and settle lazy failure callbacks', async () => {
  const s = fields({
    getDataFactoryField: async (p) => ({
      data:
        p.entity === 1
          ? [
              field('dep', {
                generator_type: 11,
                generator_config: { dependency_entity_id: 2, field: 'other' },
              }),
            ]
          : [field('other')],
    }),
    getUserModuleName: async () => ({
      data: [{ key: 20, name: 'Module', full_path: 'Root/Module' }],
    }),
    getDataFactoryEntity: async (p) => ({ data: p.id ? [entity(2)] : [entity(1), entity(2)] }),
  })
  try {
    s.open(entity())
    await flush()
    await s.dependencies.load(entity(), s.fieldRows.value)
    assert.deepEqual(s.dependencies.path(2, 'other'), ['module:20', 'entity:2', 'field:other'])
    assert.equal(
      s.dependencies.options.value[0].children.some((item) => item.raw_id === 1),
      false
    )
    s.close()
    assert.deepEqual(s.dependencies.options.value, [])
    let called = false
    await s.dependencies.loadMore({ level: 'module', raw_id: 20, value: 'module:20' }, (items) => {
      called = true
      assert.deepEqual(items, [])
    })
    assert.equal(called, true)
  } finally {
    s.dispose()
  }
})
test('status logs keep latest entity/page and failed requests recover loading for retry', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const s = logs({
    getDataFactoryEntityStatusLog: () =>
      ++count === 1 ? a.promise : count === 2 ? b.promise : Promise.reject(Error('fixture')),
  })
  try {
    s.open(entity(1))
    s.open(entity(2))
    a.resolve({ data: [{ id: 1 }], totalSize: 1 })
    await flush()
    assert.equal(s.loading.value, true)
    b.resolve({ data: [{ id: 2 }], totalSize: 5 })
    await flush()
    assert.equal(s.rows.value[0].id, 2)
    assert.equal(s.pagination.total, 5)
    await s.reload()
    assert.equal(s.loadError.value, true)
    assert.equal(s.loading.value, false)
  } finally {
    s.dispose()
  }
})
test('controlled status switch changes only after successful server response and prevents concurrent mutations', async () => {
  const pending = deferred()
  let calls = 0
  const s = page({
    putDataFactoryEntityStatus: () => {
      calls++
      return pending.promise
    },
    getDataFactoryEntity: async () => ({ data: [entity(1, { status: 0 })], totalSize: 1 }),
  })
  try {
    s.rows.value = [entity()]
    const switching = s.switchEntityStatus(false, 1)
    assert.equal(s.rows.value[0].status, 1)
    assert.equal(await s.switchEntityStatus(true, 1), false)
    s.removeEntity(entity())
    assert.equal(s.confirmations.length, 0)
    pending.resolve({ code: 200, msg: 'ok' })
    assert.equal(await switching, true)
    assert.equal(calls, 1)
    assert.equal(s.rows.value[0].status, 0)
    assert.equal(s.statusIds.size, 0)
  } finally {
    s.dispose()
  }
})
test('entity delete snapshots ID, retains failed confirmation and fallback last page on success', async () => {
  const pending = deferred(),
    calls = [],
    s = page({
      deleteDataFactoryEntity: (id) => {
        calls.push(id)
        return calls.length === 1 ? pending.promise : Promise.resolve({ msg: 'ok' })
      },
    })
  try {
    const row = entity(7)
    s.removeEntity(row)
    row.id = 8
    const config = s.confirmations[0].config,
      deleting = config.onBeforeOk()
    assert.equal(await config.onBeforeOk(), false)
    pending.reject(Error('fixture'))
    assert.equal(await deleting, false)
    assert.equal(s.deletingIds.size, 0)
    s.rows.value = [entity(7)]
    s.pagination.page = 2
    assert.equal(await config.onBeforeOk(), true)
    assert.deepEqual(calls, [7, 7])
    assert.equal(s.pagination.page, 1)
  } finally {
    s.dispose()
  }
})
test('navigation invalidates open panels/confirmations and snapshots navigation for create and batch independently', async () => {
  const opens = [],
    closed = [],
    s = page()
  try {
    s.navigationCreateRef.value = { getCreateDefaults: () => ({ projectProduct: 10, module: 20 }) }
    s.editorRef.value = { open: (...args) => opens.push(args), close: () => closed.push('editor') }
    s.batchRef.value = { open: (arg) => opens.push(arg), close: () => closed.push('batch') }
    s.openEntity()
    s.openBatchGenerate()
    assert.deepEqual(opens, [
      [undefined, { projectProduct: 10, module: 20 }],
      { projectProduct: 10, module: 20 },
    ])
    s.removeEntity(entity())
    await s.onNavigationFilterChange({ projectProduct: 11, module: 21 })
    assert.equal(s.confirmations[0].closed, true)
    assert.equal(await s.confirmations[0].config.onBeforeOk(), false)
    assert.ok(closed.includes('batch'))
  } finally {
    s.dispose()
  }
})

test('field preview errors restore controls and retry installs values only for unchanged configuration', async () => {
  let count = 0
  const s = fields({
    getDataFactoryField: async () => ({ data: [field()] }),
    postDataFactoryFieldPreviewValues: async () => {
      if (++count === 1) throw Error('fixture')
      return { data: { fields: [{ name: 'id', value: 0, valid: true }] } }
    },
  })
  try {
    s.open(entity())
    await flush()
    await s.previewFieldValues()
    assert.match(s.operationError.value, /生成失败/)
    assert.equal(s.fieldPreviewLoading.value, false)
    await s.previewFieldValues()
    assert.equal(s.fieldRows.value[0].preview_value, 0)
    assert.equal(s.operationError.value, '')
  } finally {
    s.dispose()
  }
})
test('dependency discovery failure preserves field draft and lazy errors always finish callback for retry', async () => {
  const s = fields({
    getDataFactoryField: async () => ({ data: [field()] }),
    getUserModuleName: async () => ({ data: [{ key: 20, name: 'Module' }] }),
    getDataFactoryEntity: async () => {
      throw Error('fixture')
    },
  })
  try {
    s.open(entity())
    await flush()
    await s.dependencies.load(entity(), s.fieldRows.value)
    let completed = 0
    await s.dependencies.loadMore(s.dependencies.options.value[0], (items) => {
      completed++
      assert.deepEqual(items, [])
    })
    assert.equal(completed, 1)
    assert.equal(s.dependencies.error.value, true)
    assert.equal(s.fieldRows.value[0].name, 'id')
  } finally {
    s.dispose()
  }
})
test('batch table loads discard stale product selections and failed reloads restore local loading', async () => {
  const a = deferred()
  let count = 0
  const s = batch({
    postDataFactoryDiscoverTables: () =>
      ++count === 1 ? a.promise : Promise.reject(Error('fixture')),
    getDataFactoryEntity: async () => ({ data: [] }),
  })
  try {
    s.open({ projectProduct: 10, module: 20 })
    s.batchForm.datasource_alias = 30
    const pending = s.loadBatchTables()
    s.batchForm.datasource_alias = 31
    a.resolve({ data: ['old'] })
    await pending
    assert.deepEqual(s.batchRows.value, [])
    assert.equal(s.batchLoading.value, false)
    await s.loadBatchTables()
    assert.equal(s.loadError.value, true)
    assert.equal(s.batchLoading.value, false)
  } finally {
    s.dispose()
  }
})
test('status update failure retains original state and retry succeeds; late success under new identity is ignored', async () => {
  let count = 0
  const pending = deferred(),
    s = page({
      putDataFactoryEntityStatus: () =>
        ++count === 1 ? Promise.reject(Error('fixture')) : pending.promise,
    })
  try {
    s.rows.value = [entity()]
    assert.equal(await s.switchEntityStatus(false, 1), false)
    assert.equal(s.rows.value[0].status, 1)
    assert.equal(s.statusIds.size, 0)
    const switching = s.switchEntityStatus(false, 1)
    s.user.roleId = 2
    pending.resolve({ code: 200, msg: 'old' })
    assert.equal(await switching, false)
    assert.equal(s.statusIds.size, 0)
  } finally {
    s.dispose()
  }
})
test('status drawer close drops old pagination results and does not refresh itself after activation', async () => {
  const pending = deferred()
  let calls = 0
  const s = logs({
    getDataFactoryEntityStatusLog: () => {
      calls++
      return pending.promise
    },
  })
  try {
    s.open(entity())
    s.close()
    pending.resolve({ data: [{ id: 1 }], totalSize: 10 })
    await flush()
    assert.deepEqual(s.rows.value, [])
    assert.equal(s.loading.value, false)
    s.lifecycle.deactivate()
    s.lifecycle.activate()
    assert.equal(calls, 1)
  } finally {
    s.dispose()
  }
})
