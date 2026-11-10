import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import ts from 'typescript'
import { readFileSync } from 'node:fs'
import * as vue from 'vue'
const { reactive, ref } = vue
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/apitest/public')
const columns = {
  useTableIndexColumn: () => ({ key: 'index', width: 100 }),
  useTableColumn: (items) => items,
}
function latest() {
  const out = {}
  new Function(
    'exports',
    ts.transpileModule(readFileSync('src/hooks/use-latest-request.ts', 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS },
    }).outputText
  )(out)
  return out
}
function page(api = {}, lifecycle = null) {
  const selection = ref([]),
    table = {
      dataList: reactive([]),
      tableLoading: ref(false),
      handleSuccess: (response) =>
        table.dataList.splice(0, table.dataList.length, ...response.data),
    }
  const pagination = reactive({
      page: 1,
      pageSize: 20,
      pageCount: 0,
      setTotalSize(v) {
        this.pageCount = v
      },
    }),
    confirmations = []
  const state = harness(
    'index',
    'conditionItems,projectProductCondition,requestParams,doRefresh,onSearchRefresh,onSidebarFilterChange,onResetSearch,onAdd,onUpdate,onDelete,onModifyStatus,onSaved,loadUsers,deactivate,editorRef,navigationCreateRef,listFailed,usersFailed,userOptions,userOptionsLoading,statusUpdatingIds,deletingIds',
    {
      base,
      api,
      Modal: {
        confirm: (config) => {
          const handle = {
            config,
            closed: false,
            close() {
              handle.closed = true
              config.onClose?.()
            },
          }
          confirmations.push(handle)
          return handle
        },
      },
      modules: {
        ...(lifecycle
          ? {
              vue: {
                ...vue,
                onMounted: (fn) => {
                  lifecycle.mount = fn
                },
                onActivated: (fn) => {
                  lifecycle.activate = fn
                },
                onDeactivated: (fn) => {
                  lifecycle.deactivate = fn
                },
                onBeforeUnmount: (fn) => {
                  lifecycle.unmount = fn
                },
              },
            }
          : {}),
        '@/hooks/use-latest-request': latest(),
        '@/hooks/table': {
          ...columns,
          useTable: () => table,
          usePagination: () => pagination,
          useRowKey: () => 'id',
          useRowSelection: () => ({
            selectedRowKeys: selection,
            onSelectionChange: (keys) => {
              selection.value = keys
            },
            showCheckedAll: ref(true),
          }),
        },
      },
    }
  )
  return { ...state, selection, table, pagination, confirmations }
}
function editor(api = {}) {
  return harness(
    'PublicVariableEditor',
    'open,save,draft,visible,saving,editingId,loadAliases,aliasOptions,aliasesLoading,aliasesFailed,onProductChange,onTypeChange,onEnvironmentChange',
    {
      base,
      api,
      modules: {
        '@/hooks/table': columns,
        '@/store/modules/get-enum': {
          useEnum: () => ({ environment_type: [], api_public_type: [], colors: [] }),
        },
      },
    }
  )
}
const record = (id = 1, extra = {}) => ({
  id,
  project_product: { id: 2, name: 'Example product' },
  type: 0,
  name: 'Example',
  key: 'example',
  value: 'raw value',
  status: 1,
  test_envs: [],
  ...extra,
})
const valid = (state) =>
  Object.assign(state.draft, {
    project_product: 2,
    type: 0,
    name: 'Example',
    key: 'example',
    value: 'value',
  })
test('global variables entry, editor and shared search compile', () => {
  for (const filename of [
    base + '/index.vue',
    base + '/components/PublicVariableEditor.vue',
    path.resolve('src/components/business/ApiResourceSearchFilters.vue'),
  ]) {
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: filename })
    assert.deepEqual(
      compileTemplate({
        filename,
        id: filename,
        source: descriptor.template.content,
        compilerOptions: { bindingMetadata: script.bindings },
      }).errors,
      []
    )
  }
})
test('factories isolate search arrays, preserve zero and ID delimiter normalization', () => {
  const state = page(),
    { createConditionItems } = state.load('config.ts'),
    first = createConditionItems(),
    second = createConditionItems()
  for (const key of ['status', 'type', 'update_user']) {
    const item = first.find((i) => i.key === key)
    item.value = [0, 1]
    assert.equal(item.multiple, true)
    assert.deepEqual(second.find((i) => i.key === key).value, [])
    item.reset()
    assert.deepEqual(item.value, [])
  }
  first.find((i) => i.key === 'id').value = '１２、13，14'
  assert.equal(first.find((i) => i.key === 'id').value, '12,13,14')
  state.close()
})
test('query keeps common environment mixed with specific environments under the dedicated protocol', () => {
  const state = page()
  state.projectProductCondition.value.value = [1, 2]
  state.conditionItems.find((i) => i.key === 'test_envs').value = ['__common__', 0, 1]
  state.conditionItems.find((i) => i.key === 'status').value = [0]
  state.conditionItems.find((i) => i.key === 'type').value = [0]
  state.pagination.page = 3
  const query = state.requestParams()
  assert.equal(query.project_product, 2)
  assert.equal(query.test_envs, '__common__,0,1')
  assert.equal(query.status__in, '0')
  assert.equal(query.type__in, '0')
  assert.equal(query.page, 3)
  assert.equal('test_envs__in' in query, false)
  assert.equal('value' in query, false)
  state.close()
})
test('list ignores old requests, releases latest loading and retains data on read failure', async () => {
  const pending = [],
    state = page({
      getApiPublic: () => new Promise((resolve, reject) => pending.push({ resolve, reject })),
    })
  state.table.dataList.push(record())
  const old = state.doRefresh(),
    next = state.doRefresh()
  pending[0].reject(Error())
  await old
  assert.equal(state.table.tableLoading.value, true)
  assert.equal(state.listFailed.value, false)
  pending[1].reject(Error())
  await next
  assert.equal(state.listFailed.value, true)
  assert.equal(state.table.dataList[0].id, 1)
  assert.equal(state.table.tableLoading.value, false)
  state.close()
})
test('search/reset/navigation reset pagination and selection; page reads retain only present selections', async () => {
  const state = page({ getApiPublic: async () => ({ data: [record()], totalSize: 1 }) })
  state.pagination.page = 3
  state.selection.value = [1, 2]
  state.onSearchRefresh()
  await flush()
  assert.equal(state.pagination.page, 1)
  assert.deepEqual(state.selection.value, [])
  state.selection.value = [1, 2]
  await state.doRefresh()
  assert.deepEqual(state.selection.value, [1])
  state.conditionItems.find((i) => i.key === 'type').value = [0]
  state.pagination.page = 3
  state.onResetSearch()
  await flush()
  assert.equal(state.pagination.page, 1)
  assert.deepEqual(state.conditionItems.find((i) => i.key === 'test_envs').value, [])
  assert.deepEqual(state.conditionItems.find((i) => i.key === 'type').value, [])
  state.close()
})
test('editor defaults and payload whitelist isolate records and preserve raw values', () => {
  const state = editor(),
    { createPublicDraft, publicPayload } = state.load('form.ts'),
    source = record(1, { test_envs: [0, 1], datasource_alias: { id: 4, name: 'SQL' } })
  const draft = createPublicDraft(source)
  draft.test_envs.push(2)
  assert.deepEqual(source.test_envs, [0, 1])
  Object.assign(draft, {
    project_product: [1, 2],
    value: '  raw\nvalue  ',
    update_time: 'old',
    type: 0,
  })
  const payload = publicPayload(draft)
  assert.equal(payload.project_product, 2)
  assert.equal(payload.datasource_alias, null)
  assert.equal(payload.value, '  raw\nvalue  ')
  assert.equal('update_time' in payload, false)
  assert.equal('test_env' in payload, false)
  state.close()
})
test('environment common marker is exclusive in edits and maps to empty list; legacy fields still echo', () => {
  const state = editor(),
    { normalizeEnvironmentSelection, normalizeEnvironmentValues, environmentSelectValue } =
      state.load('form.ts')
  assert.deepEqual(normalizeEnvironmentSelection([]), ['__common__'])
  assert.deepEqual(normalizeEnvironmentSelection([0, '__common__']), ['__common__'])
  assert.deepEqual(normalizeEnvironmentSelection(['__common__', 0]), [0])
  assert.deepEqual(normalizeEnvironmentValues(['__common__']), [])
  assert.deepEqual(normalizeEnvironmentValues(['0', 0, 1]), [0, 1])
  assert.deepEqual(environmentSelectValue(record(1, { test_envs: null, test_env: 0 })), [0])
  state.close()
})
test('editor cancel does not mutate source, create resets ID and uses product prefill', async () => {
  const state = editor(),
    source = record()
  await state.open(source)
  state.draft.value = 'changed'
  state.exposed.close()
  assert.equal(source.value, 'raw value')
  await state.open(undefined, 3)
  assert.equal(state.editingId.value, null)
  assert.equal(state.draft.project_product, 3)
  assert.equal(state.draft.value, '')
  assert.deepEqual(state.draft.test_envs, ['__common__'])
  state.close()
})
test('code example is filled only for empty code, exact example clears on type exit and custom code is kept', async () => {
  const state = editor(),
    { codeVariableExample } = state.load('config.ts')
  await state.open()
  state.onTypeChange(2)
  assert.equal(state.draft.value, codeVariableExample)
  state.onTypeChange(0)
  assert.equal(state.draft.value, '')
  state.draft.value = 'custom code'
  state.onTypeChange(2)
  state.onTypeChange(0)
  assert.equal(state.draft.value, 'custom code')
  state.close()
})
test('SQL aliases use leaf product, supported engines/status and latest context; product/type changes clear selection', async () => {
  const pending = [],
    state = editor({
      getDataFactoryDatasourceAlias: (query) =>
        new Promise((resolve) => pending.push({ query, resolve })),
    })
  const first = state.open(
    record(1, { type: 1, datasource_alias: { id: 4, name: 'Old database' } })
  )
  assert.equal(state.aliasesLoading.value, true)
  assert.equal(state.aliasOptions.value[0].name, 'Old database')
  const next = state.onProductChange([1, 3])
  assert.equal(state.draft.datasource_alias, null)
  assert.equal(pending[1].query.project_product, 3)
  pending[1].resolve({
    data: [
      { id: 5, name: 'Allowed', status: 1, db_type: 0 },
      { id: 6, status: 0, db_type: 0 },
      { id: 7, status: 1, db_type: 3 },
    ],
  })
  await next
  pending[0].resolve({ data: [{ id: 4, status: 1, db_type: 0 }] })
  await first
  assert.deepEqual(
    state.aliasOptions.value.map((i) => i.id),
    [5]
  )
  state.onTypeChange(0)
  assert.deepEqual(state.aliasOptions.value, [])
  state.close()
})
test('SQL option errors release loading, block save and retry inside the window', async () => {
  let fail = true,
    writes = 0
  const state = editor({
    getDataFactoryDatasourceAlias: async () => {
      if (fail) throw Error()
      return { data: [{ id: 4, name: 'DB', status: 1, db_type: 1 }] }
    },
    putApiPublic: async () => {
      writes++
      return { msg: 'ok' }
    },
  })
  await state.open(record(1, { type: 1, datasource_alias: 4 }))
  assert.equal(state.aliasesFailed.value, true)
  assert.equal(state.aliasesLoading.value, false)
  assert.equal(await state.save(), false)
  assert.equal(writes, 0)
  fail = false
  await state.loadAliases()
  assert.equal(state.aliasesFailed.value, false)
  assert.equal(await state.save(), true)
  assert.equal(writes, 1)
  state.close()
})
test('save freezes identity and nested environments, blocks duplicate submit and retains form on failure', async () => {
  const pending = deferred(),
    writes = [],
    state = editor({
      putApiPublic: (payload) => {
        writes.push(payload)
        return pending.promise
      },
    })
  await state.open(record(1, { test_envs: [0] }))
  const task = state.save()
  assert.equal(await state.save(), false)
  state.draft.test_envs.push(1)
  state.draft.value = 'changed'
  assert.deepEqual(writes[0].test_envs, [0])
  assert.equal(writes[0].value, 'raw value')
  pending.reject(Error())
  assert.equal(await task, false)
  assert.equal(state.saving.value, false)
  assert.equal(state.visible.value, true)
  assert.equal(state.draft.value, 'changed')
  state.close()
})
test('create submits status once; closing prevents late save events from affecting list', async () => {
  const pending = deferred(),
    writes = [],
    state = editor({
      postApiPublic: (payload) => {
        writes.push(payload)
        return pending.promise
      },
    })
  await state.open()
  valid(state)
  const task = state.save()
  assert.equal(writes[0].status, 1)
  state.exposed.close()
  pending.resolve({ msg: 'ok' })
  await task
  assert.equal(state.events.length, 0)
  assert.equal(state.saving.value, false)
  state.close()
})
test('validation requires project/type/key/value and SQL alias while preserving enum zero', () => {
  const state = editor(),
    { publicValidation } = state.load('form.ts')
  assert.ok(publicValidation(state.draft))
  valid(state)
  assert.equal(publicValidation(state.draft), '')
  state.draft.type = 1
  assert.match(publicValidation(state.draft), /逻辑数据库/)
  state.draft.type = 2
  state.draft.value = ''
  assert.match(publicValidation(state.draft), /自定义代码/)
  state.close()
})
test('batch delete freezes selection, retains selection on failure and clears only deleted IDs on success', async () => {
  let fail = true
  const writes = [],
    state = page({
      deleteApiPublic: async (ids) => {
        writes.push(ids)
        if (fail) throw Error()
        return { msg: 'ok' }
      },
      getApiPublic: async () => ({ data: [record(3)], totalSize: 1 }),
    })
  state.selection.value = [1, 2]
  state.onDelete(null)
  state.selection.value = [1, 2, 3]
  const confirm = state.confirmations[0].config
  assert.equal(await confirm.onBeforeOk(), false)
  assert.deepEqual(state.selection.value, [1, 2, 3])
  assert.equal(state.confirmations[0].closed, false)
  fail = false
  assert.equal(await confirm.onBeforeOk(), true)
  assert.deepEqual(writes, [
    [1, 2],
    [1, 2],
  ])
  assert.deepEqual(state.selection.value, [3])
  state.close()
})
test('delete and status are mutually exclusive; stale confirmation cannot run after leaving', async () => {
  let writes = 0
  const state = page({
    deleteApiPublic: async () => {
      writes++
      return { msg: 'ok' }
    },
  })
  state.onDelete(record())
  state.deactivate()
  assert.equal(await state.confirmations[0].config.onBeforeOk(), false)
  assert.equal(writes, 0)
  assert.equal(state.confirmations[0].closed, true)
  state.close()
})
test('status switch waits for backend, freezes value and ignores delayed completion in new context', async () => {
  const pending = deferred(),
    requests = [],
    state = page({
      putApiPublicPutStatus: (id, status) => {
        requests.push({ id, status })
        return pending.promise
      },
      getApiPublic: async () => ({ data: [record()], totalSize: 1 }),
    })
  const source = record()
  state.table.dataList.push(source)
  const task = state.onModifyStatus(false, 1)
  assert.equal(source.status, 1)
  assert.equal(await state.onModifyStatus(true, 1), false)
  state.onSearchRefresh()
  pending.resolve({ code: 200, msg: 'ok' })
  assert.equal(await task, false)
  assert.deepEqual(requests, [{ id: 1, status: 0 }])
  assert.equal(source.status, 1)
  assert.equal(state.statusUpdatingIds.size, 0)
  state.close()
})
test('status failures preserve original value and successful retry reads authoritative rows', async () => {
  let fail = true
  const state = page({
    putApiPublicPutStatus: async () => {
      if (fail) throw Error()
      return { msg: 'ok' }
    },
    getApiPublic: async () => ({ data: [record(1, { status: 0 })], totalSize: 1 }),
  })
  const source = record()
  state.table.dataList.push(source)
  assert.equal(await state.onModifyStatus(false, 1), false)
  assert.equal(source.status, 1)
  fail = false
  assert.equal(await state.onModifyStatus(false, 1), true)
  assert.equal(state.table.dataList[0].status, 0)
  assert.equal(state.table.tableLoading.value, false)
  state.close()
})
test('users loading fails independently, retries and cannot repopulate after deactivation', async () => {
  let fail = true
  const pending = deferred(),
    state = page({
      getUserName: () => {
        if (fail) return Promise.reject(Error())
        return pending.promise
      },
    })
  await state.loadUsers()
  assert.equal(state.usersFailed.value, true)
  assert.equal(state.userOptionsLoading.value, false)
  fail = false
  const task = state.loadUsers()
  state.deactivate()
  pending.resolve({ data: [{ key: 1, title: 'User' }] })
  await task
  assert.deepEqual(state.userOptions.value, [])
  assert.equal(state.userOptionsLoading.value, false)
  state.close()
})
test('create uses navigation prefill and editing opens independent editor with exact record', () => {
  const calls = [],
    state = page()
  state.navigationCreateRef.value = { getCreateDefaults: () => ({ projectProduct: 2 }) }
  state.editorRef.value = { open: (...args) => calls.push(args), close() {} }
  state.onAdd()
  const source = record()
  state.onUpdate(source)
  assert.deepEqual(calls[0], [undefined, 2])
  assert.equal(calls[1][0], source)
  state.close()
})

test('an active delete blocks a status update and repeat confirmation cannot resubmit', async () => {
  const pending = deferred()
  let deletes = 0,
    statusWrites = 0
  const state = page({
    deleteApiPublic: () => {
      deletes++
      return pending.promise
    },
    putApiPublicPutStatus: async () => {
      statusWrites++
    },
    getApiPublic: async () => ({ data: [], totalSize: 0 }),
  })
  state.onDelete(record())
  const confirm = state.confirmations[0].config,
    task = confirm.onBeforeOk()
  assert.equal(await confirm.onBeforeOk(), false)
  assert.equal(await state.onModifyStatus(false, 1), false)
  pending.resolve({ msg: 'ok' })
  await task
  assert.equal(deletes, 1)
  assert.equal(statusWrites, 0)
  state.close()
})

test('closing the SQL editor invalidates late options and keeps the original association label isolated', async () => {
  const pending = deferred(),
    source = record(1, { type: 1, datasource_alias: { id: 4, name: 'Original database' } })
  const state = editor({ getDataFactoryDatasourceAlias: () => pending.promise })
  const task = state.open(source)
  source.datasource_alias.name = 'changed externally'
  assert.equal(state.aliasOptions.value[0].name, 'Original database')
  state.exposed.close()
  pending.resolve({ data: [{ id: 5, name: 'Late result', status: 1, db_type: 0 }] })
  await task
  assert.equal(state.aliasOptions.value[0].name, 'Original database')
  assert.equal(state.aliasesLoading.value, false)
  state.close()
})

test('KeepAlive initial activation does not duplicate requests; returning reloads list and users', async () => {
  const lifecycle = {},
    reads = []
  const state = page(
    {
      getApiPublic: async () => {
        reads.push('list')
        return { data: [record()], totalSize: 1 }
      },
      getUserName: async () => {
        reads.push('users')
        return { data: [] }
      },
    },
    lifecycle
  )
  try {
    lifecycle.mount()
    lifecycle.activate()
    await flush()
    assert.deepEqual(reads, ['list', 'users'])
    let closed = 0
    state.editorRef.value = {
      close() {
        closed++
      },
    }
    lifecycle.deactivate()
    assert.equal(closed, 1)
    lifecycle.activate()
    await flush()
    assert.deepEqual(reads, ['list', 'users', 'list', 'users'])
    assert.equal(state.table.tableLoading.value, false)
  } finally {
    lifecycle.unmount()
    state.close()
  }
})
