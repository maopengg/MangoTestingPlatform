import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import {
  setupDatasource,
  alias,
  connection,
  binding,
} from './helpers/factory-datasource-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/data-factory/datasource')
const page = (api = {}) =>
  setupDatasource(
    'index',
    'conditionItems,rows,listLoading,loadError,pagination,doRefresh,onSearch,onResetSearch,onFilterChange,loadEnums,loadUsers,enumsLoading,enumsError,usersLoading,usersError,editorRef,bindingsRef,navigationRef,openAlias,openBinding,removeAlias,onAliasSaving,onBindingWriting,aliasSaving,deletingIds,bindingWritingIds',
    api
  )
const aliasEditor = (api = {}) =>
  setupDatasource(
    'DatasourceAliasEditor',
    'draft,visible,saving,editingId,open,save,onCategoryChange,sourceTypeOptions',
    api,
    { optionsLoading: false }
  )
const bindingEditor = (api = {}) =>
  setupDatasource(
    'DatasourceBindingEditor',
    'draft,visible,saving,editingId,open,save,optionsLoading,optionsError,dataSourceOptions,loadOptions',
    api
  )
const drawer = (api = {}) =>
  setupDatasource(
    'DatasourceBindingsDrawer',
    'visible,alias,rows,loading,loadError,bindingSaving,open,loadBindings,openEditor,editorRef,onSaved,onEditorSaving,removeBinding,deletingIds,changeWriting',
    api
  )

test('page, alias editor, binding drawer and binding editor compile', () => {
  for (const file of [
    'index.vue',
    'components/DatasourceAliasEditor.vue',
    'components/DatasourceBindingsDrawer.vue',
    'components/DatasourceBindingEditor.vue',
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
test('search instances isolate conditions; product paths become leaf IDs and collection filters retain zero', async () => {
  const calls = [],
    s = page({
      getDataFactoryDatasourceAlias: async (p) => {
        calls.push(p)
        return { data: [], totalSize: 0 }
      },
    }),
    other = page()
  try {
    s.conditionItems.find((i) => i.key === 'project_product').value = [2, 10]
    s.conditionItems.find((i) => i.key === 'db_type').value = [0, 10]
    s.conditionItems.find((i) => i.key === 'update_user').value = [1, 3]
    s.pagination.page = 4
    await s.onSearch()
    assert.deepEqual(calls[0], {
      project_product: 10,
      db_type__in: '0,10',
      update_user__in: '1,3',
      page: 1,
      pageSize: 20,
    })
    assert.deepEqual(other.conditionItems.find((i) => i.key === 'db_type').value, [])
    await s.onResetSearch()
    assert.deepEqual(calls.at(-1), { page: 1, pageSize: 20 })
    assert.deepEqual(s.conditionItems.find((i) => i.key === 'update_user').value, [])
  } finally {
    s.dispose()
    other.dispose()
  }
})
test('latest list wins and old finally cannot release new loading', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const s = page({ getDataFactoryDatasourceAlias: () => (++count === 1 ? a.promise : b.promise) })
  try {
    const first = s.doRefresh(),
      second = s.doRefresh()
    a.resolve({ data: [alias(1)], totalSize: 1 })
    await first
    assert.equal(s.listLoading.value, true)
    assert.deepEqual(s.rows.value, [])
    b.resolve({ data: [alias(2)], totalSize: 4 })
    await second
    assert.equal(s.rows.value[0].id, 2)
    assert.equal(s.pagination.pageCount, 4)
    assert.equal(s.listLoading.value, false)
  } finally {
    s.dispose()
  }
})
test('list, enum and updater errors have independent retries', async () => {
  let count = 0,
    users = 0
  const pending = deferred(),
    s = page({
      getDataFactoryDatasourceAlias: async () => {
        if (++count === 1) throw Error('fixture')
        return { data: [alias()], totalSize: 1 }
      },
      getUserName: async () => {
        if (++users === 1) throw Error('fixture')
        return { data: [{ key: 1, title: 'User' }] }
      },
    })
  try {
    s.enums.getEnum = () => pending.promise
    const enums = s.loadEnums()
    await s.doRefresh()
    await s.loadUsers()
    assert.equal(s.loadError.value, true)
    assert.equal(s.usersError.value, true)
    assert.equal(s.enumsLoading.value, true)
    pending.reject(Error('fixture'))
    await enums
    assert.equal(s.enumsError.value, true)
    assert.equal(s.enumsLoading.value, false)
    s.enums.getEnum = async () => {}
    await s.loadEnums()
    await s.loadUsers()
    await s.doRefresh()
    assert.equal(s.loadError.value, false)
    assert.equal(s.usersError.value, false)
    assert.equal(s.enumsError.value, false)
  } finally {
    s.dispose()
  }
})
test('deactivation discards stale lists/options and activation rereads without writes', async () => {
  const a = deferred(),
    b = deferred()
  let reads = 0
  const s = page({
    getDataFactoryDatasourceAlias: () =>
      ++reads === 1 ? a.promise : Promise.resolve({ data: [alias(2)], totalSize: 1 }),
    getUserName: () => b.promise,
  })
  try {
    const first = s.doRefresh(),
      users = s.loadUsers()
    s.lifecycle.deactivate()
    a.resolve({ data: [alias()], totalSize: 3 })
    b.resolve({ data: [{ key: 1, title: 'Old' }] })
    await Promise.all([first, users])
    assert.deepEqual(s.rows.value, [])
    assert.deepEqual(s.conditionItems.find((i) => i.key === 'update_user').optionItems, [])
    s.lifecycle.activate()
    await flush()
    assert.equal(reads, 2)
    assert.equal(s.rows.value[0].id, 2)
  } finally {
    s.dispose()
  }
})
test('alias editor owns draft and navigation defaults; category change preserves DB zero and filters types', () => {
  const s = aliasEditor()
  try {
    s.open(alias())
    s.draft.name = 'Changed'
    assert.equal(s.draft.project_product, 10)
    s.close()
    s.open(undefined, 12)
    assert.equal(s.editingId.value, null)
    assert.equal(s.draft.project_product, 12)
    assert.equal(s.draft.name, '')
    s.draft.source_category = 1
    s.onCategoryChange()
    assert.equal(s.draft.db_type, 10)
    s.draft.source_category = 0
    s.onCategoryChange()
    assert.equal(s.draft.db_type, 0)
  } finally {
    s.dispose()
  }
})
test('alias save snapshots whitelist and real product ID; prevents duplicates, preserves failed draft and retries', async () => {
  const pending = deferred(),
    calls = [],
    s = aliasEditor({
      putDataFactoryDatasourceAlias: (p) => {
        calls.push(p)
        return calls.length === 1 ? pending.promise : Promise.resolve({ msg: 'ok' })
      },
    })
  try {
    s.open(alias(7))
    s.draft.project_product = [2, 10]
    const saving = s.save()
    assert.equal(await s.save(), false)
    s.draft.name = 'Later'
    assert.deepEqual(calls[0], {
      id: 7,
      project_product: 10,
      name: 'Alias 7',
      source_category: 0,
      db_type: 0,
      description: '',
      status: 1,
    })
    pending.reject(Error('fixture'))
    assert.equal(await saving, false)
    assert.equal(s.visible.value, true)
    assert.equal(s.saving.value, false)
    assert.equal(s.draft.name, 'Later')
    assert.equal(await s.save(), true)
    assert.equal(calls.length, 2)
  } finally {
    s.dispose()
  }
})
test('alias create validates required fields but allows zero; stale save after identity change emits no saved', async () => {
  const pending = deferred(),
    calls = [],
    s = aliasEditor({
      postDataFactoryDatasourceAlias: (p) => {
        calls.push(p)
        return pending.promise
      },
    })
  try {
    s.open()
    assert.equal(await s.save(), false)
    s.draft.project_product = 0
    s.draft.name = 'Example'
    s.draft.db_type = 0
    const saving = s.save()
    assert.equal(calls[0].project_product, 0)
    assert.equal('id' in calls[0], false)
    s.user.roleId = 2
    assert.equal(s.visible.value, false)
    s.open()
    assert.equal(s.visible.value, false)
    pending.resolve({ msg: 'ok' })
    assert.equal(await saving, false)
    assert.equal(
      s.events.some((e) => e[0] === 'saved'),
      false
    )
    s.open()
    assert.equal(s.draft.name, '')
  } finally {
    s.dispose()
  }
})
test('binding drafts handle data_source numeric/object and legacy database, copy targets and retain Redis DB zero', async () => {
  const s = bindingEditor({ getSystemDataSource: async () => ({ data: [connection(1)] }) })
  try {
    for (const row of [
      binding(),
      binding(1, { data_source: 1 }),
      binding(1, { data_source: null, database: connection(1) }),
    ]) {
      s.open(alias(), row)
      await flush()
      assert.equal(s.draft.data_source, 1)
    }
    const row = binding(2, { redis_db: 0 })
    s.open(alias(), row)
    s.draft.target.database_name = 'changed'
    assert.equal(row.database_name, 'example')
    assert.equal(s.draft.target.redis_db, 0)
    s.close()
    s.open(alias())
    assert.equal(s.draft.allowQuery, false)
    assert.equal(s.draft.allowWrite, false)
    assert.equal(s.draft.environment, null)
  } finally {
    s.dispose()
  }
})
test('source options are category/type filtered and an unavailable saved source clears only after success', async () => {
  const s = bindingEditor({
    getSystemDataSource: async () => ({
      data: [
        connection(1),
        connection(2, { db_type: 10, source_category: 1 }),
        connection(3, { db_type: 1 }),
      ],
    }),
  })
  try {
    s.open(alias(), binding(1, { data_source: connection(99) }))
    await flush()
    assert.deepEqual(
      s.dataSourceOptions.value.map((i) => i.id),
      [1]
    )
    assert.equal(s.draft.data_source, null)
    assert.equal(s.optionsLoading.value, false)
  } finally {
    s.dispose()
  }
})
test('late source options never clear a manual choice or a different alias editor', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const s = bindingEditor({ getSystemDataSource: () => (++count === 1 ? a.promise : b.promise) })
  try {
    s.open(alias(1), binding(1, { data_source: connection(99) }))
    s.open(alias(2, { db_type: 10, source_category: 1 }))
    s.draft.data_source = 2
    a.resolve({ data: [connection()] })
    await flush()
    assert.equal(s.optionsLoading.value, true)
    assert.equal(s.draft.data_source, 2)
    assert.deepEqual(s.dataSourceOptions.value, [])
    b.resolve({ data: [connection(2, { db_type: 10, source_category: 1 })] })
    await flush()
    assert.equal(s.draft.data_source, 2)
    assert.equal(s.dataSourceOptions.value[0].id, 2)
  } finally {
    s.dispose()
  }
})
test('option failure preserves selection and can retry; pending/failed discovery blocks save', async () => {
  let count = 0,
    writes = 0
  const pending = deferred(),
    s = bindingEditor({
      getSystemDataSource: () =>
        ++count === 1 ? pending.promise : Promise.resolve({ data: [connection()] }),
      postDataFactoryDatasourceBinding: async () => {
        writes++
        return { msg: 'ok' }
      },
    })
  try {
    s.open(alias())
    s.draft.environment = 0
    s.draft.data_source = 1
    assert.equal(await s.save(), false)
    pending.reject(Error('fixture'))
    await flush()
    assert.equal(s.optionsError.value, true)
    assert.equal(s.draft.data_source, 1)
    assert.equal(await s.save(), false)
    await s.loadOptions()
    assert.equal(s.optionsError.value, false)
    assert.equal(await s.save(), true)
    assert.equal(writes, 1)
  } finally {
    s.dispose()
  }
})
test('binding payload snapshots alias ID, target, description and permission flags; string production environment forces write off', async () => {
  const pending = deferred(),
    calls = [],
    s = bindingEditor({
      getSystemDataSource: async () => ({ data: [connection()] }),
      putDataFactoryDatasourceBinding: (p) => {
        calls.push(p)
        return pending.promise
      },
    })
  try {
    s.open(alias(7), binding(8, { description: 'Existing', redis_db: 0 }))
    await flush()
    s.draft.environment = '2'
    s.draft.allowWrite = true
    const saving = s.save()
    assert.equal(await s.save(), false)
    s.draft.target.redis_db = 3
    assert.deepEqual(calls[0], {
      id: 8,
      datasource_alias: 7,
      environment: '2',
      data_source: 1,
      database_name: 'example',
      schema_name: '',
      redis_db: 0,
      description: 'Existing',
      db_c_status: 1,
      db_rud_status: 0,
    })
    pending.resolve({ msg: 'ok' })
    assert.equal(await saving, true)
    assert.equal(s.visible.value, false)
    assert.deepEqual(
      s.events.filter((e) => e[0] === 'saved'),
      [['saved', 7]]
    )
  } finally {
    s.dispose()
  }
})
test('binding failure keeps draft for retry; close and late success cannot emit saved to another context', async () => {
  const pending = deferred()
  let count = 0
  const s = bindingEditor({
    getSystemDataSource: async () => ({ data: [connection()] }),
    postDataFactoryDatasourceBinding: () =>
      ++count === 1 ? Promise.reject(Error('fixture')) : pending.promise,
  })
  try {
    s.open(alias())
    await flush()
    s.draft.environment = 0
    s.draft.data_source = 1
    s.draft.description = 'Keep'
    assert.equal(await s.save(), false)
    assert.equal(s.draft.description, 'Keep')
    assert.equal(s.visible.value, true)
    const saving = s.save()
    s.close()
    s.open(alias(2))
    assert.equal(s.visible.value, false)
    pending.resolve({ msg: 'ok' })
    assert.equal(await saving, false)
    assert.equal(
      s.events.some((e) => e[0] === 'saved'),
      false
    )
    assert.equal(s.saving.value, false)
  } finally {
    s.dispose()
  }
})
test('switching binding drawers rejects old alias response; old finally does not drop current loading', async () => {
  const a = deferred(),
    b = deferred()
  const s = drawer({
    getDataFactoryDatasourceBinding: (p) => (p.datasource_alias === 1 ? a.promise : b.promise),
  })
  try {
    s.open(alias(1))
    s.open(alias(2))
    a.resolve({ data: [binding(1)] })
    await flush()
    assert.equal(s.loading.value, true)
    assert.deepEqual(s.rows.value, [])
    b.resolve({ data: [binding(2)] })
    await flush()
    assert.equal(s.rows.value[0].id, 2)
    assert.equal(s.alias.value.id, 2)
    assert.equal(s.loading.value, false)
    s.close()
    assert.deepEqual(s.rows.value, [])
    assert.equal(s.alias.value, null)
  } finally {
    s.dispose()
  }
})
test('drawer loading failures retry, explicit editor scopes its alias, and closed drawers do not reload on old saved events', async () => {
  let count = 0
  const opens = [],
    s = drawer({
      getDataFactoryDatasourceBinding: async () => {
        if (++count === 1) throw Error('fixture')
        return { data: [binding()] }
      },
    })
  try {
    s.open(alias(7))
    await flush()
    assert.equal(s.loadError.value, true)
    assert.equal(s.loading.value, false)
    await s.loadBindings()
    assert.equal(s.loadError.value, false)
    s.editorRef.value = { open: (...args) => opens.push(args), close() {} }
    s.openEditor(binding(3))
    assert.equal(opens[0][0].id, 7)
    assert.equal(opens[0][1].id, 3)
    s.close()
    s.onSaved(7)
    await flush()
    assert.equal(count, 2)
  } finally {
    s.dispose()
  }
})
test('drawer writer counts remain locked until all physical mutations end across alias changes', async () => {
  const s = drawer()
  try {
    s.changeWriting(1, true)
    s.changeWriting(1, true)
    s.changeWriting(2, true)
    s.close()
    s.changeWriting(1, false)
    assert.deepEqual(s.events, [
      ['writing-change', 1, true],
      ['writing-change', 2, true],
    ])
    s.changeWriting(1, false)
    s.changeWriting(2, false)
    assert.deepEqual(s.events.slice(-2), [
      ['writing-change', 1, false],
      ['writing-change', 2, false],
    ])
  } finally {
    s.dispose()
  }
})
test('binding deletes snapshot ID, block duplicate submit and retry failures', async () => {
  const pending = deferred(),
    calls = [],
    s = drawer({
      deleteDataFactoryDatasourceBinding: (id) => {
        calls.push(id)
        return calls.length === 1 ? pending.promise : Promise.resolve({ msg: 'ok' })
      },
    })
  try {
    s.open(alias(7))
    await flush()
    const row = binding(8)
    s.removeBinding(row)
    row.id = 9
    const config = s.confirmations[0].config,
      deleting = config.onBeforeOk()
    assert.equal(await config.onBeforeOk(), false)
    assert.deepEqual(calls, [8])
    pending.reject(Error('fixture'))
    assert.equal(await deleting, false)
    assert.equal(s.deletingIds.size, 0)
    assert.equal(await config.onBeforeOk(), true)
    assert.deepEqual(calls, [8, 8])
    assert.equal(s.deletingIds.size, 0)
  } finally {
    s.dispose()
  }
})
test('binding confirmation and pending reads invalidate on drawer close and identity change', async () => {
  const pending = deferred()
  let writes = 0
  const s = drawer({
    getDataFactoryDatasourceBinding: () => pending.promise,
    deleteDataFactoryDatasourceBinding: async () => {
      writes++
      return { msg: 'ok' }
    },
  })
  try {
    s.open(alias())
    s.removeBinding(binding())
    s.close()
    assert.equal(s.confirmations[0].closed, true)
    assert.equal(await s.confirmations[0].config.onBeforeOk(), false)
    assert.equal(writes, 0)
    s.open(alias(2))
    s.user.roleId = 2
    pending.resolve({ data: [binding()] })
    await flush()
    assert.equal(s.visible.value, false)
    assert.deepEqual(s.rows.value, [])
  } finally {
    s.dispose()
  }
})
test('page navigation snapshots create defaults and closes obsolete windows; writers prevent conflicting alias mutations', async () => {
  const opens = [],
    closed = [],
    s = page(),
    defaults = { projectProduct: 10, module: null }
  try {
    s.navigationRef.value = { getCreateDefaults: () => defaults }
    s.editorRef.value = { open: (...args) => opens.push(args), close: () => closed.push('editor') }
    s.bindingsRef.value = { open: (a) => opens.push(a.id), close: () => closed.push('bindings') }
    s.openAlias()
    defaults.projectProduct = 11
    assert.deepEqual(opens, [[undefined, 10]])
    s.onBindingWriting(1, true)
    s.openAlias(alias())
    s.openBinding(alias())
    s.removeAlias(alias())
    assert.equal(s.confirmations.length, 0)
    assert.equal(opens.length, 1)
    s.onBindingWriting(1, false)
    s.pagination.page = 3
    await s.onFilterChange({ projectProduct: 11 })
    assert.equal(s.pagination.page, 1)
    assert.ok(closed.includes('bindings'))
  } finally {
    s.dispose()
  }
})
test('alias deletes retain ID and failure retry, fallback last page and ignore old product confirmations', async () => {
  const pending = deferred(),
    calls = [],
    s = page({
      deleteDataFactoryDatasourceAlias: (id) => {
        calls.push(id)
        return calls.length === 1 ? pending.promise : Promise.resolve({ msg: 'ok' })
      },
    })
  try {
    const row = alias(7)
    s.removeAlias(row)
    row.id = 8
    const config = s.confirmations[0].config,
      deleting = config.onBeforeOk()
    assert.equal(await config.onBeforeOk(), false)
    pending.reject(Error('fixture'))
    assert.equal(await deleting, false)
    assert.equal(s.deletingIds.size, 0)
    s.rows.value = [alias(7)]
    s.pagination.page = 2
    assert.equal(await config.onBeforeOk(), true)
    assert.deepEqual(calls, [7, 7])
    assert.equal(s.pagination.page, 1)
    s.confirmations[0].close()
    s.removeAlias(alias(2))
    await s.onFilterChange({ projectProduct: 20 })
    assert.equal(await s.confirmations[1].config.onBeforeOk(), false)
    assert.deepEqual(calls, [7, 7])
  } finally {
    s.dispose()
  }
})
test('source labels preserve Elasticsearch prefix and local file names without exposing arbitrary objects', () => {
  const s = page()
  try {
    const { displayDataSource } = s.load('form.ts')
    assert.equal(
      displayDataSource(connection(1, { db_type: 20, extra_config: { path_prefix: '/api/' } })),
      'Source 1 · db.example.com:3306/api'
    )
    assert.equal(
      displayDataSource(connection(2, { file_path: 'fixture.db' })),
      'Source 2 · fixture.db'
    )
    assert.equal(displayDataSource(null), '-')
    assert.equal(displayDataSource(7), 7)
  } finally {
    s.dispose()
  }
})
