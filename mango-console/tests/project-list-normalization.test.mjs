import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/config/project')
const record = (id = 1, extra = {}) => ({ id, name: `Project ${id}`, status: 1, ...extra })
function setup(api = {}) {
  const lifecycle = {},
    route = vue.reactive({ path: '/config/project/index', query: {} }),
    user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-session' }),
    dialogs = [],
    notices = []
  const cache = { invalidations: 0, projects: 0, products: 0 },
    navigation = { record: null, targets: [] }
  const s = harness(
    'index',
    'rows,listLoading,listError,userOptions,usersLoading,usersError,conditionItems,pagination,editor,editorTitle,draft,saving,requestParams,doRefresh,onSearch,onResetSearch,loadUsers,onAdd,onUpdate,closeEditor,save,onDelete,onModifyStatus,deletingIds,statusUpdatingIds,clickNotice',
    {
      base,
      api,
      modules: {
        vue: {
          ...vue,
          onMounted: (f) => (lifecycle.mount = f),
          onActivated: (f) => (lifecycle.activate = f),
          onDeactivated: (f) => (lifecycle.deactivate = f),
          onBeforeUnmount: (f) => (lifecycle.unmount = f),
        },
        'vue-router': {
          useRoute: () => route,
          useRouter: () => ({ push: async (target) => navigation.targets.push(target) }),
        },
        '@/store/modules/user': { default: () => user },
        '@/store/modules/get-project': {
          useProject: () => ({
            invalidateProjectOptionsCache() {
              cache.invalidations++
            },
            getProject: async () => {
              cache.projects++
            },
            projectProductName: async () => {
              cache.products++
            },
          }),
        },
        '@/store/page-data': {
          usePageData: () => ({
            setRecord(value) {
              navigation.record = value
            },
          }),
        },
        '@/hooks/table': {
          useTableIndexColumn: () => ({ key: 'index' }),
          useTableColumn: (rows) => rows,
          usePagination: (callback, loading) =>
            vue.reactive({
              page: 1,
              pageSize: 20,
              pageCount: 0,
              setTotalSize(total) {
                this.pageCount = total
              },
              onChange() {
                loading.value = true
                return callback()
              },
            }),
        },
        '@arco-design/web-vue': {
          Message: { success: (m) => notices.push(m), error: (m) => notices.push(m) },
          Modal: {
            confirm: (config) => {
              const d = {
                config,
                closed: false,
                close() {
                  d.closed = true
                  config.onClose?.()
                },
              }
              dialogs.push(d)
              return d
            },
          },
        },
      },
    }
  )
  return {
    ...s,
    lifecycle,
    route,
    user,
    dialogs,
    notices,
    cache,
    navigation,
    dispose() {
      lifecycle.unmount?.()
      s.close()
    },
  }
}

test('project page compiles with compact horizontal guarded modal and controlled status', () => {
  const filename = path.join(base, 'index.vue'),
    { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'project' })
  assert.deepEqual(
    compileTemplate({
      source: descriptor.template.content,
      filename,
      id: 'project',
      compilerOptions: { bindingMetadata: script.bindings },
    }).errors,
    []
  )
  assert.match(descriptor.template.content, /:model-value="record.status === 1"/)
  assert.doesNotMatch(descriptor.template.content, /default-checked|v-permission/)
  assert.doesNotMatch(
    descriptor.scriptSetup.content,
    /setTimeout|console\.log|as any|reactive<any>/
  )
})
test('search instances isolate multi-select state and submit clean page/pageSize parameters', () => {
  const a = setup(),
    b = setup()
  try {
    a.conditionItems.find((i) => i.key === 'update_user').value = [7, 8]
    a.pagination.page = 3
    a.pagination.pageSize = 50
    assert.deepEqual(a.requestParams(), { update_user__in: '7,8', page: 3, pageSize: 50 })
    assert.deepEqual(b.requestParams(), { page: 1, pageSize: 20 })
    assert.equal(a.conditionItems.find((i) => i.key === 'update_user').multiple, true)
  } finally {
    a.dispose()
    b.dispose()
  }
})
test('global ID input separators remain normalized and zero is not removed as an empty search value', () => {
  const s = setup()
  try {
    s.conditionItems.find((i) => i.key === 'id').value = '5574、5577'
    assert.equal(s.requestParams().id, '5574,5577')
    s.conditionItems.find((i) => i.key === 'name').value = 0
    assert.equal(s.requestParams().name, 0)
  } finally {
    s.dispose()
  }
})
test('search resets page one; reset clears fields and restores multi-select arrays', async () => {
  const calls = [],
    s = setup({
      getUserDepartmentList: async (p) => {
        calls.push(p)
        return { data: [], totalSize: 0 }
      },
    })
  try {
    s.pagination.page = 5
    s.conditionItems.find((i) => i.key === 'update_user').value = [7]
    await s.onSearch()
    assert.equal(calls[0].page, 1)
    s.pagination.page = 3
    await s.onResetSearch()
    assert.deepEqual(calls[1], { page: 1, pageSize: 20 })
    assert.deepEqual(s.conditionItems.find((i) => i.key === 'update_user').value, [])
  } finally {
    s.dispose()
  }
})
test('pagination supplies loading and uses server total; finally releases loading on failure', async () => {
  const gate = deferred(),
    s = setup({ getUserDepartmentList: () => gate.promise })
  try {
    s.pagination.page = 2
    const pending = s.pagination.onChange()
    assert.equal(s.listLoading.value, true)
    gate.resolve({ data: [record()], totalSize: 45 })
    await pending
    assert.equal(s.pagination.pageCount, 45)
    assert.equal(s.rows.value[0].id, 1)
    assert.equal(s.listLoading.value, false)
  } finally {
    s.dispose()
  }
  let fail = true
  const f = setup({
    getUserDepartmentList: async () => {
      if (fail) throw Error()
      return { data: [record()], totalSize: 1 }
    },
  })
  try {
    await f.doRefresh()
    assert.equal(f.listLoading.value, false)
    assert.equal(f.listError.value, '项目加载失败，请重试')
    fail = false
    await f.doRefresh()
    assert.equal(f.listError.value, '')
    assert.equal(f.rows.value.length, 1)
  } finally {
    f.dispose()
  }
})
test('late list responses cannot replace current rows or release the latest request loading', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const s = setup({ getUserDepartmentList: () => (++count === 1 ? a.promise : b.promise) })
  try {
    const old = s.doRefresh(),
      fresh = s.doRefresh()
    a.resolve({ data: [record(1)], totalSize: 1 })
    await old
    assert.deepEqual(s.rows.value, [])
    assert.equal(s.listLoading.value, true)
    b.resolve({ data: [record(2)], totalSize: 99 })
    await fresh
    assert.equal(s.rows.value[0].id, 2)
    assert.equal(s.pagination.pageCount, 99)
  } finally {
    s.dispose()
  }
})
test('new/edit/cancel/reopen resets typed draft and never changes original row', () => {
  const a = setup(),
    b = setup()
  try {
    const row = record(4, { update_time: 'audit' })
    a.onUpdate(row)
    a.draft.name = 'Changed'
    assert.equal(row.name, 'Project 4')
    assert.equal(b.draft.name, '')
    assert.equal(a.editorTitle.value, '编辑')
    a.closeEditor()
    a.onAdd()
    assert.deepEqual(a.draft, { name: '' })
    assert.equal(a.editor.recordId, null)
    assert.equal(a.editorTitle.value, '新增')
  } finally {
    a.dispose()
    b.dispose()
  }
})
test('save validation, immutable edit whitelist and duplicate guard preserve fields', async () => {
  const gate = deferred(),
    calls = [],
    s = setup({
      putUserDepartmentList: (p) => {
        calls.push(p)
        return gate.promise
      },
    })
  try {
    s.onAdd()
    assert.equal(await s.save(), false)
    s.onUpdate(record(4, { status: 0, update_time: 'audit' }))
    const pending = s.save()
    s.draft.name = 'Later'
    assert.equal(await s.save(), false)
    assert.deepEqual(calls, [{ id: 4, name: 'Project 4' }])
    gate.resolve({ code: 200, msg: 'ok' })
    assert.equal(await pending, true)
    assert.equal(s.editor.visible, false)
    assert.equal(s.saving.value, false)
    assert.deepEqual(s.cache, { invalidations: 1, projects: 1, products: 1 })
  } finally {
    s.dispose()
  }
})
test('new project sends status one; failed save keeps name and can retry', async () => {
  const calls = []
  let fail = true
  const s = setup({
    postUserDepartmentList: async (p) => {
      calls.push(p)
      if (fail) throw Error()
      return { code: 200, msg: 'ok' }
    },
  })
  try {
    s.onAdd()
    s.draft.name = ' New '
    assert.equal(await s.save(), false)
    assert.equal(s.editor.visible, true)
    assert.equal(s.draft.name, ' New ')
    assert.equal(s.cache.invalidations, 0)
    fail = false
    assert.equal(await s.save(), true)
    assert.deepEqual(calls[1], { name: ' New ', status: 1 })
  } finally {
    s.dispose()
  }
})
test('edit pending across identity change still invalidates physical cache but cannot close new UI or refresh old catalog', async () => {
  const gate = deferred(),
    s = setup({ putUserDepartmentList: () => gate.promise })
  try {
    s.onUpdate(record())
    const pending = s.save()
    s.user.roleId = 2
    assert.equal(s.editor.visible, false)
    s.onAdd()
    assert.equal(s.editor.visible, false)
    gate.resolve({ code: 200, msg: 'ok' })
    assert.equal(await pending, false)
    assert.equal(s.cache.invalidations, 1)
    assert.equal(s.cache.projects, 0)
    assert.equal(s.cache.products, 0)
    s.onAdd()
    assert.equal(s.editor.visible, true)
    assert.equal(s.editor.recordId, null)
  } finally {
    s.dispose()
  }
})
test('delete freezes its ID, serializes pending writes, keeps failure retryable and invalidates caches only after success', async () => {
  const gate = deferred(),
    ids = []
  let fail = true
  const s = setup({
    deleteUserDepartmentList: (id) => {
      ids.push(id)
      return fail ? gate.promise : Promise.resolve({ code: 200, msg: 'ok' })
    },
  })
  try {
    const row = record()
    s.onDelete(row)
    row.id = 99
    const dialog = s.dialogs[0],
      pending = dialog.config.onBeforeOk()
    assert.equal(await dialog.config.onBeforeOk(), false)
    assert.equal(await s.onModifyStatus(record(), false), false)
    gate.reject(Error())
    assert.equal(await pending, false)
    assert.equal(s.cache.invalidations, 0)
    fail = false
    assert.equal(await dialog.config.onBeforeOk(), true)
    assert.deepEqual(ids, [1, 1])
    assert.equal(dialog.config.okButtonProps.status, 'danger')
    assert.deepEqual(s.cache, { invalidations: 1, projects: 1, products: 1 })
  } finally {
    s.dispose()
  }
})
test('deleting final row of a later page moves back before requesting current list', async () => {
  const params = [],
    s = setup({
      getUserDepartmentList: async (p) => {
        params.push(p)
        return { data: [], totalSize: 20 }
      },
    })
  try {
    s.rows.value = [record()]
    s.pagination.page = 2
    s.onDelete(record())
    assert.equal(await s.dialogs[0].config.onBeforeOk(), true)
    assert.equal(s.pagination.page, 1)
    assert.equal(params[0].page, 1)
  } finally {
    s.dispose()
  }
})
test('status success updates only after API completion and uses project-only refresh semantics', async () => {
  const gate = deferred(),
    reload = deferred(),
    calls = [],
    s = setup({
      putUserDepartmentList: (p) => {
        calls.push(p)
        return gate.promise
      },
      getUserDepartmentList: () => reload.promise,
    })
  try {
    s.rows.value = [record(4)]
    const pending = s.onModifyStatus(s.rows.value[0], false)
    assert.equal(s.rows.value[0].status, 1)
    assert.equal(await s.onModifyStatus(s.rows.value[0], true), false)
    gate.resolve({ code: 200, msg: 'ok' })
    await flush()
    assert.equal(s.rows.value[0].status, 0)
    assert.deepEqual(calls, [{ id: 4, name: 'Project 4', status: 0 }])
    reload.resolve({ data: [record(4, { status: 0 })], totalSize: 1 })
    assert.equal(await pending, true)
    assert.deepEqual(s.cache, { invalidations: 1, projects: 1, products: 0 })
  } finally {
    s.dispose()
  }
})
test('status failure leaves controlled switch unchanged and permits retry', async () => {
  let fail = true
  const s = setup({
    putUserDepartmentList: async () => {
      if (fail) throw Error()
      return { code: 200, msg: 'ok' }
    },
  })
  try {
    s.rows.value = [record()]
    assert.equal(await s.onModifyStatus(s.rows.value[0], false), false)
    assert.equal(s.rows.value[0].status, 1)
    assert.equal(s.statusUpdatingIds.size, 0)
    fail = false
    assert.equal(await s.onModifyStatus(s.rows.value[0], false), true)
    assert.equal(s.cache.invalidations, 1)
  } finally {
    s.dispose()
  }
})
test('pending editor and row status/delete operations cannot overlap', async () => {
  const gate = deferred()
  let count = 0
  const s = setup({
    putUserDepartmentList: () => {
      count++
      return gate.promise
    },
  })
  try {
    s.onUpdate(record())
    const pending = s.save()
    assert.equal(await s.onModifyStatus(record(), false), false)
    s.onDelete(record())
    assert.equal(s.dialogs.length, 0)
    assert.equal(count, 1)
    gate.resolve({ code: 200, msg: 'ok' })
    await pending
  } finally {
    s.dispose()
  }
})
test('list launched before a status mutation cannot restore the previous status', async () => {
  const list = deferred(),
    put = deferred()
  let reads = 0
  const s = setup({
    getUserDepartmentList: () =>
      ++reads === 1
        ? list.promise
        : Promise.resolve({ data: [record(1, { status: 0 })], totalSize: 1 }),
    putUserDepartmentList: () => put.promise,
  })
  try {
    s.rows.value = [record()]
    const old = s.doRefresh(),
      mutation = s.onModifyStatus(s.rows.value[0], false)
    list.resolve({ data: [record()], totalSize: 1 })
    await old
    put.resolve({ code: 200, msg: 'ok' })
    assert.equal(await mutation, true)
    assert.equal(s.rows.value[0].status, 0)
  } finally {
    s.dispose()
  }
})
test('late status write after switching identity cannot change new rows or refresh old catalog', async () => {
  const gate = deferred(),
    s = setup({ putUserDepartmentList: () => gate.promise })
  try {
    const original = record()
    s.rows.value = [original]
    const pending = s.onModifyStatus(s.rows.value[0], false)
    s.user.token = 'fixture-next-session'
    await flush()
    s.rows.value = [record(2)]
    gate.resolve({ code: 200, msg: 'ok' })
    assert.equal(await pending, false)
    assert.equal(s.rows.value[0].id, 2)
    assert.equal(original.status, 1)
    assert.equal(s.cache.projects, 0)
    assert.equal(s.cache.invalidations, 1)
  } finally {
    s.dispose()
  }
})
test('user options loading failure and retry remain independent of list loading', async () => {
  let fail = true
  const s = setup({
    getUserName: async () => {
      if (fail) throw Error()
      return { data: [{ key: 0, title: 'Fixture user' }] }
    },
  })
  try {
    await s.loadUsers()
    assert.equal(s.usersLoading.value, false)
    assert.equal(s.usersError.value, '更新人选项加载失败，请重试')
    assert.equal(s.listLoading.value, false)
    fail = false
    await s.loadUsers()
    assert.deepEqual(s.userOptions.value, [{ key: 0, title: 'Fixture user' }])
    assert.equal(s.usersError.value, '')
  } finally {
    s.dispose()
  }
})
test('old user options and confirm callbacks are invalidated on identity change', async () => {
  const old = deferred(),
    fresh = deferred()
  let reads = 0,
    writes = 0
  const s = setup({
    getUserName: () => (++reads === 1 ? old.promise : fresh.promise),
    deleteUserDepartmentList: async () => {
      writes++
      return { code: 200, msg: 'ok' }
    },
  })
  try {
    const pending = s.loadUsers()
    s.onDelete(record())
    s.user.userId = 2
    s.user.roleId = 2
    old.resolve({ data: [{ key: 1, title: 'Old' }] })
    await pending
    assert.deepEqual(s.userOptions.value, [])
    assert.equal(s.dialogs[0].closed, true)
    assert.equal(await s.dialogs[0].config.onBeforeOk(), false)
    assert.equal(writes, 0)
    fresh.resolve({ data: [{ key: 2, title: 'New' }] })
    await flush()
    assert.deepEqual(s.userOptions.value, [{ key: 2, title: 'New' }])
  } finally {
    s.dispose()
  }
})
test('mount/first activation deduplicate, cached leave suspends and reactivation reloads', async () => {
  const old = deferred()
  let count = 0
  const s = setup({
    getUserDepartmentList: () =>
      ++count === 1 ? old.promise : Promise.resolve({ data: [record(2)], totalSize: 1 }),
  })
  try {
    s.lifecycle.mount()
    s.lifecycle.activate()
    assert.equal(count, 1)
    s.onUpdate(record())
    s.lifecycle.deactivate()
    assert.equal(s.editor.visible, false)
    old.resolve({ data: [record(1)], totalSize: 1 })
    await flush()
    assert.deepEqual(s.rows.value, [])
    await s.doRefresh()
    assert.equal(count, 1)
    s.lifecycle.activate()
    await flush()
    assert.equal(count, 2)
    assert.equal(s.rows.value[0].id, 2)
  } finally {
    s.dispose()
  }
})
test('navigation away rejects late list results and notification navigation uses a fixed whitelist snapshot', async () => {
  const gate = deferred(),
    s = setup({ getUserDepartmentList: () => gate.promise })
  try {
    const row = record(5, { update_time: 'audit' })
    s.clickNotice(row)
    row.name = 'Changed'
    assert.deepEqual(s.navigation.record, { id: 5, name: 'Project 5' })
    assert.deepEqual(s.navigation.targets, [
      { path: '/config/project/notice', query: { id: 5, name: 'Project 5' } },
    ])
    const pending = s.doRefresh()
    s.route.path = '/config/project/notice'
    gate.resolve({ data: [record()], totalSize: 1 })
    await pending
    assert.deepEqual(s.rows.value, [])
  } finally {
    s.dispose()
  }
})
