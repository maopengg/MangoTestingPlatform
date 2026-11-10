import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import * as vue from 'vue'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/gray/config-file')
const binding = (id = 21) => ({
  id,
  yaml_file: 11,
  file_path: 'config/example.yml',
  status: 0,
  repository: { id: 31, name: 'Example repository', branch: 'main', test_env: 0 },
})
const row = (extra = {}) => ({
  id: 11,
  name: 'Example config',
  project_product: { id: 2, name: 'Example product', project: { id: 1, name: 'Example project' } },
  effect_wait_seconds: 0,
  status: 0,
  bindings: [binding()],
  ...extra,
})
const response = (rows = [row()], total = rows.length) => ({
  code: 200,
  data: rows,
  totalSize: total,
})
function page(api = {}, enumApi) {
  const hooks = { mount: [], deactivate: [], activate: [], unmount: [] },
    calls = [],
    dialogs = [],
    messages = []
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'test-token', selected_environment: 0 })
  const route = vue.reactive({ fullPath: '/gray/config-file/index' })
  const f = harness(
    'index',
    [
      'rows,listLoading,listError,enumLoading,enumError,query,pagination,sidebarResetKey,bindings,bindingDrawer',
      'onSearch,onSidebarFilterChange,onSearchRefresh,onReset,loadEnums,onAdd,onEdit,onBindingManage,onBindingAdd,onBindingEdit,onBindingContent',
      'onModifyYamlStatus,onModifyBindingStatus,onDelete,onDeleteBinding,onYamlSaved,onBindingSaved',
      'navigationCreateRef,yamlEditorRef,bindingEditorRef,contentDrawerRef,yamlSaving,bindingSaving,yamlEditorVisible,bindingEditorVisible',
      'mutations,writeBusy,canCloseBindings,actionBlocked,formatEnvironmentText,environmentColor,repositoryLabel,visibleBindings,hiddenBindings',
    ].join(','),
    {
      base,
      api: {
        getGrayYamlFile: async (p) => {
          calls.push(p)
          return response()
        },
        getGrayYamlFileBinding: async () => ({ code: 200, data: [binding()], totalSize: 1 }),
        putGrayYamlFile: async (p) => ({ code: 200, data: { ...p, project_product: 2 } }),
        putGrayYamlFileBinding: async (p) => ({ code: 200, data: { ...p, yaml_file: 11 } }),
        deleteGrayYamlFile: async () => ({ code: 200 }),
        deleteGrayYamlFileBinding: async () => ({ code: 200 }),
        ...api,
      },
      modules: {
        vue: {
          ...vue,
          onMounted: (fn) => hooks.mount.push(fn),
          onDeactivated: (fn) => hooks.deactivate.push(fn),
          onActivated: (fn) => hooks.activate.push(fn),
          onBeforeUnmount: (fn) => hooks.unmount.push(fn),
        },
        '@/store/modules/user': { default: () => user },
        'vue-router': { useRoute: () => route },
        '@/store/modules/get-enum': {
          useEnum: () => ({
            environment_type: [{ key: 0, title: 'Example environment' }],
            colors: ['blue'],
            getEnum: enumApi || (async () => {}),
          }),
        },
        '@/hooks/table': {
          usePagination: (callback) =>
            vue.reactive({
              page: 1,
              pageSize: 20,
              pageCount: 0,
              onChange: callback,
              setTotalSize(total) {
                this.pageCount = total
              },
            }),
        },
        '@arco-design/web-vue': {
          Message: {
            success: (m) => messages.push(['success', m]),
            error: (m) => messages.push(['error', m]),
            warning: (m) => messages.push(['warning', m]),
          },
          Modal: {
            confirm(options) {
              const dialog = {
                options,
                closed: false,
                close() {
                  this.closed = true
                  options.onClose?.()
                },
              }
              dialogs.push(dialog)
              return dialog
            },
          },
        },
      },
    }
  )
  return {
    ...f,
    calls,
    user,
    route,
    hooks,
    dialogs,
    messages,
    cleanup() {
      hooks.unmount.forEach((fn) => fn())
      f.close()
    },
  }
}

test('initial reads run independently and activation does not duplicate initial mount', async () => {
  const list = deferred(),
    enums = deferred(),
    p = page({ getGrayYamlFile: () => list.promise }, () => enums.promise)
  p.hooks.mount.forEach((fn) => fn())
  p.hooks.activate.forEach((fn) => fn())
  assert.equal(p.listLoading.value, true)
  assert.equal(p.enumLoading.value, true)
  list.resolve(response())
  await flush()
  assert.equal(p.listLoading.value, false)
  assert.equal(p.rows.value.length, 1)
  assert.equal(p.enumLoading.value, true)
  enums.resolve()
  await flush()
  assert.equal(p.enumLoading.value, false)
  p.cleanup()
})
test('query payload strips blanks, preserves status zero and converts navigation paths to leaf ID', async () => {
  const calls = [],
    p = page({
      getGrayYamlFile: async (q) => {
        calls.push(q)
        return response()
      },
    })
  p.query.status = [0, 1]
  p.pagination.page = 3
  p.onSidebarFilterChange({ projectProduct: [1, '2'] })
  await flush()
  assert.deepEqual(calls, [{ page: 1, pageSize: 20, project_product: 2, status__in: '0,1' }])
  p.onSidebarFilterChange({ projectProduct: '2' })
  assert.equal(calls.length, 1)
  p.cleanup()
})
test('reset restores fresh multi-select arrays, navigation and first-page blank search', async () => {
  const p = page()
  p.query.name = 'Example'
  p.query.status = [0]
  p.query.project_product = 2
  p.pagination.page = 3
  p.onReset()
  await flush()
  assert.deepEqual(p.query, { name: '', status: [], project_product: null })
  assert.equal(p.pagination.page, 1)
  assert.equal(p.sidebarResetKey.value, 1)
  assert.deepEqual(p.calls.at(-1), { page: 1, pageSize: 20 })
  p.cleanup()
})
test('failed reload keeps displayed data, reports local error and remains retryable', async () => {
  let calls = 0
  const p = page({
    getGrayYamlFile: async () => {
      if (++calls === 2) throw Error('Network')
      return response()
    },
  })
  await p.onSearch()
  assert.equal(await p.onSearch(), false)
  assert.equal(p.rows.value.length, 1)
  assert.equal(p.listLoading.value, false)
  assert.equal(p.listError.value, true)
  assert.equal(await p.onSearch(), true)
  assert.equal(p.listError.value, false)
  p.cleanup()
})
test('out-of-order searches preserve the newest rows and loading owner', async () => {
  const first = deferred(),
    second = deferred()
  let calls = 0
  const p = page({ getGrayYamlFile: () => (++calls === 1 ? first.promise : second.promise) })
  const one = p.onSearch(),
    two = p.onSearch()
  first.resolve(response([row({ name: 'Old' })]))
  await one
  assert.equal(p.listLoading.value, true)
  assert.deepEqual(p.rows.value, [])
  second.resolve(response([row({ name: 'New' })]))
  await two
  assert.equal(p.rows.value[0].name, 'New')
  p.cleanup()
})
test('query change invalidates pending results even before the next search event', async () => {
  const pending = deferred(),
    p = page({ getGrayYamlFile: () => pending.promise })
  const work = p.onSearch()
  p.query.name = 'Next search'
  pending.resolve(response())
  assert.equal(await work, false)
  assert.deepEqual(p.rows.value, [])
  assert.equal(p.listLoading.value, false)
  p.cleanup()
})
test('pagination uses public page/pageSize protocol and moves back when backend clamps an obsolete page', async () => {
  const calls = [],
    p = page({
      getGrayYamlFile: async (q) => {
        calls.push(q)
        return response()
      },
    })
  p.pagination.page = 3
  p.pagination.pageSize = 10
  assert.equal(await p.pagination.onChange(), true)
  assert.deepEqual(
    calls.map((q) => q.page),
    [3, 1]
  )
  assert.equal(p.pagination.page, 1)
  assert.equal(p.pagination.pageCount, 1)
  assert.equal(p.listLoading.value, false)
  p.cleanup()
})
test('empty generic CRUD response without totalSize is a successful zero', async () => {
  const p = page({ getGrayYamlFile: async () => ({ code: 200, data: [] }) })
  assert.equal(await p.onSearch(), true)
  assert.equal(p.pagination.pageCount, 0)
  assert.equal(p.listError.value, false)
  p.cleanup()
})
test('read boundary keeps only finite fields and preserves zero wait, status and environment', async () => {
  const p = page({
    getGrayYamlFile: async () =>
      response([
        {
          ...row(),
          audit: 'Readonly',
          project_product: { ...row().project_product, case_people: [99] },
          bindings: [
            { ...binding(), repository: { ...binding().repository, access_token: 'masked' } },
          ],
        },
      ]),
  })
  await p.onSearch()
  assert.deepEqual(p.rows.value, [row()])
  assert.equal(p.formatEnvironmentText(0), 'Example environment')
  assert.equal(p.environmentColor(0), 'blue')
  assert.equal(p.formatEnvironmentText(null), '环境通用')
  p.cleanup()
})
for (const invalid of [
  { code: 400, data: [row()], totalSize: 1 },
  response([row({ id: null })]),
  response([row({ status: 7 })]),
  response([row({ effect_wait_seconds: -1 })]),
  response([row({ project_product: { id: 2, name: 'Product', project: { id: null } } })]),
  response([row({ bindings: [binding(), binding()] })]),
  response([row({ bindings: [{ ...binding(), yaml_file: 12 }] })]),
])
  test(
    'malformed configuration data becomes a local retryable error: ' + JSON.stringify(invalid),
    async () => {
      const p = page({ getGrayYamlFile: async () => invalid })
      assert.equal(await p.onSearch(), false)
      assert.equal(p.listError.value, true)
      assert.deepEqual(p.rows.value, [])
      p.cleanup()
    }
  )
test('rows from a different selected product are rejected', async () => {
  const p = page()
  p.query.project_product = 3
  assert.equal(await p.onSearch(), false)
  assert.equal(p.listError.value, true)
  p.cleanup()
})
for (const field of ['userId', 'roleId', 'token', 'selected_environment'])
  test(`identity or environment ${field} A-B-A invalidates in-flight list reads`, async () => {
    const pending = deferred(),
      p = page({ getGrayYamlFile: () => pending.promise })
    const work = p.onSearch(),
      original = p.user[field]
    p.user[field] = field === 'token' ? 'next-test-token' : 9
    p.user[field] = original
    pending.resolve(response())
    await work
    assert.deepEqual(p.rows.value, [])
    assert.equal(p.listLoading.value, false)
    p.cleanup()
  })
test('mounted environment switch independently reloads current list and invalidates old results', async () => {
  const first = deferred(),
    next = deferred()
  let calls = 0
  const p = page({ getGrayYamlFile: () => (++calls === 1 ? first.promise : next.promise) })
  p.hooks.mount.forEach((fn) => fn())
  p.user.selected_environment = 1
  first.resolve(response([row({ name: 'Old environment' })]))
  await flush()
  assert.deepEqual(p.rows.value, [])
  assert.equal(p.listLoading.value, true)
  next.resolve(response([row({ name: 'Current environment' })]))
  await flush()
  assert.equal(p.rows.value[0].name, 'Current environment')
  p.cleanup()
})
test('route departure stops reads, clears data and blocks entry actions', async () => {
  const p = page(),
    opened = []
  await p.onSearch()
  p.yamlEditorRef.value = { open: (...args) => opened.push(args) }
  p.route.fullPath = '/gray/execution-log/index'
  assert.deepEqual(p.rows.value, [])
  assert.equal(await p.onSearch(), false)
  p.onAdd()
  assert.deepEqual(opened, [])
  p.cleanup()
})
test('KeepAlive deactivation clears data and late reads; activation loads once with current context', async () => {
  const first = deferred()
  let calls = 0
  const p = page({
    getGrayYamlFile: () => (++calls === 1 ? first.promise : Promise.resolve(response())),
  })
  p.hooks.mount.forEach((fn) => fn())
  p.hooks.deactivate.forEach((fn) => fn())
  first.resolve(response([row({ name: 'Old cache' })]))
  await flush()
  assert.deepEqual(p.rows.value, [])
  assert.equal(await p.onSearch(), false)
  p.hooks.activate.forEach((fn) => fn())
  await flush()
  assert.equal(calls, 2)
  assert.equal(p.rows.value[0].name, 'Example config')
  p.hooks.activate.forEach((fn) => fn())
  assert.equal(calls, 2)
  p.cleanup()
})
test('enum failure is independent of list success and can retry', async () => {
  let calls = 0
  const p = page({}, async () => {
    if (++calls === 1) throw Error('Network')
  })
  await Promise.all([p.onSearch(), p.loadEnums()])
  assert.equal(p.rows.value.length, 1)
  assert.equal(p.enumError.value, true)
  assert.equal(p.listError.value, false)
  await p.loadEnums()
  assert.equal(p.enumError.value, false)
  p.cleanup()
})
test('navigation default is captured synchronously and cross-window editor/save guards remain effective', async () => {
  const p = page(),
    opened = []
  p.yamlEditorRef.value = { open: (...args) => opened.push(args) }
  p.navigationCreateRef.value = { getCreateDefaults: () => ({ projectProduct: 9, module: 8 }) }
  p.onAdd()
  assert.deepEqual(opened, [[undefined, 9]])
  p.bindingSaving.value = true
  p.onAdd()
  assert.equal(opened.length, 1)
  p.bindingSaving.value = false
  await p.onSearch()
  p.onBindingManage(row())
  await flush()
  p.onAdd()
  assert.equal(opened.length, 1)
  p.cleanup()
})
test('controlled status only changes after successful acknowledgment and retains acknowledged state on refresh failure', async () => {
  const pending = deferred()
  let calls = 0
  const p = page({
    getGrayYamlFile: async () => {
      if (++calls > 1) throw Error('Reload')
      return response()
    },
    putGrayYamlFile: () => pending.promise,
  })
  await p.onSearch()
  const work = p.onModifyYamlStatus(true, 11)
  assert.equal(p.rows.value[0].status, 0)
  assert.equal(p.writeBusy.value, true)
  pending.resolve({ code: 200, data: { id: 11, status: 1, project_product: 2 } })
  assert.equal(await work, false)
  assert.equal(p.rows.value[0].status, 1)
  assert.equal(p.listError.value, true)
  assert.equal(p.writeBusy.value, false)
  assert.match(p.messages.at(-1)[1], /状态已更新/)
  p.cleanup()
})
test('binding write applies to the fixed owner and blocks manager close until both refreshes settle', async () => {
  const pending = deferred(),
    reload = deferred()
  let reads = 0
  const p = page({
    getGrayYamlFileBinding: () =>
      ++reads === 1
        ? Promise.resolve({ code: 200, data: [binding()], totalSize: 1 })
        : reload.promise,
    putGrayYamlFileBinding: () => pending.promise,
  })
  await p.onSearch()
  p.onBindingManage(row())
  await flush()
  const work = p.onModifyBindingStatus(true, 21)
  assert.equal(p.canCloseBindings(), false)
  p.bindings.onVisibleChange(false)
  assert.equal(p.bindingDrawer.visible, true)
  pending.resolve({ code: 200, data: { id: 21, status: 1, yaml_file: 11 } })
  await flush()
  assert.equal(p.bindingDrawer.dataList[0].status, 1)
  assert.equal(p.writeBusy.value, true)
  reload.resolve({ code: 200, data: [{ ...binding(), status: 1 }], totalSize: 1 })
  await work
  assert.equal(p.canCloseBindings(), true)
  p.cleanup()
})
test('fixed delete target, successful confirmation close and last-row pagination adjustment are coordinated', async () => {
  const ids = []
  let first = true
  const p = page({
    getGrayYamlFile: async () => (first ? response([row()], 21) : response([], 20)),
    deleteGrayYamlFile: async (id) => {
      ids.push(id)
      first = false
      return { code: 200 }
    },
  })
  p.pagination.page = 2
  await p.onSearch()
  p.onDelete(p.rows.value[0])
  const dialog = p.dialogs[0]
  assert.equal(p.canCloseBindings(), false)
  await dialog.options.onBeforeOk()
  assert.deepEqual(ids, [11])
  assert.equal(dialog.closed, true)
  assert.equal(p.pagination.page, 1)
  assert.equal(p.pagination.pageCount, 20)
  p.cleanup()
})
test('saving succeeded with a failed list reload is not presented as save failure', async () => {
  const p = page({
    getGrayYamlFile: async () => {
      throw Error('Network')
    },
  })
  await p.onYamlSaved()
  assert.match(p.messages.at(-1)[1], /配置已保存/)
  p.cleanup()
})

test('an older read cannot overwrite acknowledged status after the post-write reload fails', async () => {
  const oldRead = deferred()
  let reads = 0
  const p = page({
    getGrayYamlFile: async () => {
      if (++reads === 1) return response()
      if (reads === 2) return oldRead.promise
      throw Error('Reload failure')
    },
  })
  await p.onSearch()
  const previous = p.onSearch()
  await p.onModifyYamlStatus(true, 11)
  assert.equal(p.rows.value[0].status, 1)
  oldRead.resolve(response())
  assert.equal(await previous, false)
  assert.equal(p.rows.value[0].status, 1)
  assert.equal(p.listError.value, true)
  p.cleanup()
})

test('superseded post-save read is not mislabeled as a reload failure', async () => {
  const pending = deferred(),
    p = page({ getGrayYamlFile: () => pending.promise })
  const work = p.onYamlSaved()
  p.query.name = 'Different query'
  pending.resolve(response())
  await work
  assert.deepEqual(p.messages, [])
  p.cleanup()
})

test('parent mutation lock survives context invalidation and blocks opening an editor until the request settles', async () => {
  const pending = deferred(),
    opened = []
  const p = page({ putGrayYamlFile: () => pending.promise })
  await p.onSearch()
  p.yamlEditorRef.value = { open: (...args) => opened.push(args) }
  const work = p.onModifyYamlStatus(true, 11)
  p.user.selected_environment = 1
  p.onAdd()
  assert.deepEqual(opened, [])
  assert.equal(p.writeBusy.value, true)
  pending.resolve({ code: 200, data: { id: 11, status: 1, project_product: 2 } })
  await work
  assert.equal(p.writeBusy.value, false)
  assert.deepEqual(p.messages, [])
  p.onAdd()
  assert.equal(opened.length, 1)
  p.cleanup()
})
