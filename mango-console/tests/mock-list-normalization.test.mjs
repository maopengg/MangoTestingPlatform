import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import * as vue from 'vue'
const { reactive, ref, shallowReactive } = vue
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/apitest/mock')
const row = (id = 1) => ({
  id,
  name: 'Example mock',
  mock_key: 'example',
  path: '/items/{id}',
  method: 0,
  method_name: 'GET',
  enabled: false,
  record_call_log: false,
  project_product: { id: 2, name: 'Example product' },
})
function latestRequest() {
  const exports = {}
  new Function(
    'exports',
    ts.transpileModule(readFileSync('src/hooks/use-latest-request.ts', 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS },
    }).outputText
  )(exports)
  return exports
}
function page(api = {}, lifecycle = null) {
  const table = {
    dataList: shallowReactive([]),
    tableLoading: ref(false),
    handleSuccess: (r) => table.dataList.splice(0, table.dataList.length, ...r.data),
  }
  const pagination = reactive({
      page: 1,
      pageSize: 20,
      pageCount: 0,
      setTotalSize(v) {
        this.pageCount = v
      },
    }),
    confirmations = [],
    routes = []
  const state = harness(
    'index',
    'refresh,search,onProjectChange,resetFilters,createConfig,openConfig,openLogs,copyCurl,changeState,removeConfig,clearAllLogs,deactivate,filters,logsVisible,logsTarget,listFailed,clearAllLoading,updatingIds,deletingIds,copyingIds,navigationCreateRef',
    {
      base,
      api: { getMockEndpointUrl: (path) => `https://example.com/api/mock${path}`, ...api },
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
                  const previous = lifecycle.mount
                  lifecycle.mount = () => { previous?.(); fn() }
                },
                onActivated: (fn) => {
                  const previous = lifecycle.activate
                  lifecycle.activate = () => { previous?.(); fn() }
                },
                onDeactivated: (fn) => {
                  const previous = lifecycle.deactivate
                  lifecycle.deactivate = () => { previous?.(); fn() }
                },
                onBeforeUnmount: (fn) => {
                  const previous = lifecycle.unmount
                  lifecycle.unmount = () => { previous?.(); fn() }
                },
              },
            }
          : {}),
        'vue-router': { useRouter: () => ({ push: (target) => routes.push(target) }) },
        '@/hooks/use-latest-request': latestRequest(),
        '@/hooks/table': {
          useTable: () => table,
          usePagination: () => pagination,
          useTableIndexColumn: () => ({ key: 'index', width: 100 }),
          useTableColumn: (columns) => columns,
        },
      },
    }
  )
  return { ...state, table, pagination, confirmations, routes }
}
test('Mock list and shared log panel scripts/templates compile', () => {
  for (const file of ['index.vue', 'components/MockCallLogsPanel.vue']) {
    const filename = path.join(base, file),
      { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: file })
    assert.deepEqual(
      compileTemplate({
        filename,
        id: file,
        source: descriptor.template.content,
        compilerOptions: { bindingMetadata: script.bindings },
      }).errors,
      []
    )
  }
})
test('filter factories isolate collections and ID input normalizes supported separators', () => {
  const state = page(),
    { createMockFilters } = state.load('config.ts'),
    first = createMockFilters(),
    second = createMockFilters()
  first.method.push(0)
  first.enabled.push(0)
  first.id = '5574、5577，5578'
  assert.deepEqual(second.method, [])
  assert.deepEqual(second.enabled, [])
  assert.equal(first.id, '5574,5577,5578')
  state.close()
})
test('query maps cascade product leaf, multi selections and IDs, omits blanks without losing zero', () => {
  const state = page(),
    { buildMockQuery } = state.load('query.ts')
  Object.assign(state.filters, {
    project_product: [1, 2],
    id: '1、2',
    name: '  Example ',
    mock_key: ' /example/items ',
    method: [0, 1, 0],
    enabled: [0],
    record_call_log: [0],
  })
  assert.deepEqual(buildMockQuery(state.filters, 3, 50), {
    page: 3,
    pageSize: 50,
    project_product: 2,
    id__in: '1,2',
    name: 'Example',
    mock_key: 'example',
    method__in: '0,1',
    enabled__in: '0',
    record_call_log__in: '0',
  })
  state.filters.project_product = 0
  state.filters.mock_key = '///'
  state.filters.id = ''
  assert.equal(buildMockQuery(state.filters, 1, 20).project_product, 0)
  assert.equal('mock_key' in buildMockQuery(state.filters, 1, 20), false)
  state.close()
})
test('latest list response wins and old failure cannot end current loading', async () => {
  const first = deferred(),
    second = deferred()
  let calls = 0
  const state = page({ getMockConfigs: () => (++calls === 1 ? first.promise : second.promise) })
  const a = state.refresh()
  const b = state.refresh()
  first.reject(Error('old'))
  await a
  assert.equal(state.table.tableLoading.value, true)
  assert.equal(state.listFailed.value, false)
  second.resolve({ data: [row(2)], totalSize: 1 })
  await b
  assert.equal(state.table.dataList[0].id, 2)
  assert.equal(state.table.tableLoading.value, false)
  state.close()
})
test('list failure preserves rows, releases loading and can retry', async () => {
  let fail = true
  const state = page({
    getMockConfigs: async () => {
      if (fail) throw Error('read')
      return { data: [row(2)], totalSize: 1 }
    },
  })
  state.table.dataList.push(row())
  await state.refresh()
  assert.equal(state.table.dataList[0].id, 1)
  assert.equal(state.listFailed.value, true)
  assert.equal(state.table.tableLoading.value, false)
  fail = false
  await state.refresh()
  assert.equal(state.listFailed.value, false)
  assert.equal(state.table.dataList[0].id, 2)
  state.close()
})
test('search and navigation reset pagination; reset restores arrays and product is not serialized as __in', async () => {
  const requests = [],
    state = page({
      getMockConfigs: async (params) => {
        requests.push(params)
        return { data: [], totalSize: 0 }
      },
    })
  state.pagination.page = 4
  state.search()
  await flush()
  assert.equal(requests.at(-1).page, 1)
  state.pagination.page = 4
  state.onProjectChange({ projectProduct: 0 })
  await flush()
  assert.equal(requests.at(-1).project_product, 0)
  state.filters.enabled = [0]
  state.filters.name = 'name'
  state.resetFilters()
  await flush()
  assert.deepEqual(state.filters.enabled, [])
  assert.equal(state.filters.project_product, null)
  assert.deepEqual(requests.at(-1), { page: 1, pageSize: 20 })
  state.close()
})
test('state changes wait for success, block duplicate row writes and do not mutate on failure', async () => {
  const pending = deferred(),
    calls = [],
    state = page({
      updateMockConfigState: (id, value) => {
        calls.push({ id, value })
        return pending.promise
      },
      getMockConfigs: async () => ({ data: [], totalSize: 0 }),
    })
  const target = row()
  state.table.dataList.push(target)
  const patch = { enabled: true },
    task = state.changeState(target, patch)
  patch.enabled = false
  assert.equal(target.enabled, false)
  assert.equal(await state.changeState(target, { record_call_log: true }), false)
  assert.equal(calls.length, 1)
  assert.deepEqual(calls[0].value, { enabled: true })
  pending.reject(Error('write'))
  assert.equal(await task, false)
  assert.equal(target.enabled, false)
  assert.equal(state.updatingIds.size, 0)
  state.close()
})
test('successful state response invalidates earlier list reads and does not mutate a row from old context', async () => {
  const pending = deferred(),
    list = deferred()
  const state = page({
    updateMockConfigState: () => pending.promise,
    getMockConfigs: () => list.promise,
  })
  const target = row()
  state.table.dataList.push(target)
  const old = state.refresh()
  const task = state.changeState(target, { enabled: true })
  old.catch(() => {})
  state.onProjectChange({ projectProduct: 3 })
  pending.resolve({ data: {} })
  assert.equal(await task, false)
  assert.equal(target.enabled, false)
  list.resolve({ data: [], totalSize: 0 })
  await old
  await flush()
  state.close()
})
test('successful state change patches current record and fetches authoritative list', async () => {
  const target = row(),
    requests = [],
    state = page({
      updateMockConfigState: async () => ({ data: { project_product: 2 } }),
      getMockConfigs: async (params) => {
        requests.push(params)
        return { data: [{ ...row(), enabled: true }], totalSize: 1 }
      },
    })
  state.table.dataList.push(target)
  assert.equal(await state.changeState(target, { enabled: true }), true)
  await flush()
  assert.equal(state.table.dataList[0].enabled, true)
  assert.equal(target.enabled, false)
  assert.equal(typeof target.project_product, 'object')
  assert.equal(requests.length, 1)
  state.close()
})
test('both mock switches render saved values even when the follow-up list request fails', async () => {
  const state = page({
    updateMockConfigState: async () => ({ code: 200 }),
    getMockConfigs: async () => { throw Error('list unavailable') },
  })
  state.table.dataList.push(row())
  const rendered = vue.computed(() => [state.table.dataList[0].enabled, state.table.dataList[0].record_call_log])
  assert.deepEqual(rendered.value, [false, false])
  assert.equal(await state.changeState(state.table.dataList[0], { enabled: true }), true)
  assert.deepEqual(rendered.value, [true, false])
  assert.equal(await state.changeState(state.table.dataList[0], { record_call_log: true }), true)
  assert.deepEqual(rendered.value, [true, true])
  state.close()
})

test('delete keeps original ID, waits for success and preserves confirmation on failure', async () => {
  let fail = true
  const calls = [],
    state = page({
      deleteMockConfig: async (id) => {
        calls.push(id)
        if (fail) throw Error('delete')
        return { data: {} }
      },
      getMockConfigs: async () => ({ data: [], totalSize: 0 }),
    })
  const target = row()
  state.removeConfig(target)
  const confirm = state.confirmations[0].config
  target.id = 9
  assert.equal(await confirm.onBeforeOk(), false)
  assert.equal(state.deletingIds.size, 0)
  assert.equal(state.confirmations[0].closed, false)
  fail = false
  assert.equal(await confirm.onBeforeOk(), true)
  assert.deepEqual(calls, [1, 1])
  state.close()
})
test('delete prevents duplicate requests, blocks switch while deleting and moves empty last page back', async () => {
  const pending = deferred()
  let calls = 0
  const state = page({
    deleteMockConfig: () => {
      calls++
      return pending.promise
    },
    getMockConfigs: async () => ({ data: [], totalSize: 20 }),
  })
  const target = row()
  state.table.dataList.push(target)
  state.pagination.page = 2
  state.removeConfig(target)
  const confirm = state.confirmations[0].config,
    task = confirm.onBeforeOk()
  assert.equal(await confirm.onBeforeOk(), false)
  assert.equal(await state.changeState(target, { enabled: true }), false)
  assert.equal(calls, 1)
  pending.resolve({ data: {} })
  await task
  assert.equal(state.pagination.page, 1)
  state.close()
})
test('stale confirmation cannot delete or clear logs after search or deactivation', async () => {
  let writes = 0
  const state = page({
    deleteMockConfig: async () => {
      writes++
    },
    clearAllMockLogs: async () => {
      writes++
    },
    getMockConfigs: async () => ({ data: [], totalSize: 0 }),
  })
  state.removeConfig(row())
  const old = state.confirmations[0]
  state.search()
  assert.equal(old.closed, true)
  assert.equal(await old.config.onBeforeOk(), false)
  state.clearAllLogs()
  const clear = state.confirmations[1]
  state.deactivate()
  assert.equal(clear.closed, true)
  assert.equal(await clear.config.onBeforeOk(), false)
  assert.equal(writes, 0)
  state.close()
})
test('clear all logs retries failures, blocks duplicates and closes stale log drawer only on success', async () => {
  let fail = true,
    calls = 0
  const pending = deferred(),
    state = page({
      clearAllMockLogs: async () => {
        calls++
        if (fail) throw Error('clear')
        return pending.promise
      },
    })
  state.openLogs(row())
  state.clearAllLogs()
  const confirm = state.confirmations[0].config
  assert.equal(await confirm.onBeforeOk(), false)
  assert.equal(state.logsVisible.value, true)
  assert.equal(state.clearAllLoading.value, false)
  fail = false
  const task = confirm.onBeforeOk()
  assert.equal(await confirm.onBeforeOk(), false)
  assert.equal(calls, 2)
  pending.resolve({ data: { deleted_count: 3 } })
  await task
  assert.equal(state.logsVisible.value, false)
  assert.equal(state.logsTarget.value, null)
  state.close()
})
test('clipboard has per-row duplicate guard and releases it after failure', async () => {
  const pending = deferred()
  let calls = 0
  const original = Object.getOwnPropertyDescriptor(globalThis, 'navigator')
  Object.defineProperty(globalThis, 'navigator', {
    configurable: true,
    value: {
      clipboard: {
        writeText: () => {
          calls++
          return pending.promise
        },
      },
    },
  })
  const state = page()
  try {
    const task = state.copyCurl(row())
    await state.copyCurl(row())
    assert.equal(calls, 1)
    pending.reject(Error('clipboard'))
    await task
    assert.equal(state.copyingIds.size, 0)
  } finally {
    state.close()
    if (original) Object.defineProperty(globalThis, 'navigator', original)
    else delete globalThis.navigator
  }
})
test('create prefill and logs target capture identities rather than row references', () => {
  const state = page(),
    target = row()
  state.navigationCreateRef.value = { getCreateDefaults: () => ({ projectProduct: 2 }) }
  state.createConfig()
  assert.deepEqual(state.routes[0].query, { project_product: 2 })
  state.openLogs(target)
  target.id = 9
  assert.equal(state.logsTarget.value.id, 1)
  state.close()
  assert.equal(state.logsVisible.value, false)
})
test('deactivation invalidates outstanding reads and resumes no work through stale callbacks', async () => {
  const pending = deferred()
  let calls = 0
  const state = page({
    getMockConfigs: () => {
      calls++
      return pending.promise
    },
  })
  const task = state.refresh()
  state.deactivate()
  pending.resolve({ data: [row()], totalSize: 1 })
  await task
  await state.refresh()
  assert.equal(calls, 1)
  assert.equal(state.table.dataList.length, 0)
  assert.equal(state.table.tableLoading.value, false)
  state.close()
})

test('KeepAlive activation avoids duplicate initial fetch and refreshes after returning', async () => {
  const lifecycle = {},
    requests = []
  const state = page(
    {
      getMockConfigs: async (params) => {
        requests.push(params)
        return { data: [row()], totalSize: 1 }
      },
    },
    lifecycle
  )
  try {
    lifecycle.mount()
    lifecycle.activate()
    await flush()
    assert.equal(requests.length, 1)
    state.openLogs(row())
    lifecycle.deactivate()
    assert.equal(state.logsVisible.value, false)
    lifecycle.activate()
    await flush()
    assert.equal(requests.length, 2)
    assert.equal(state.table.tableLoading.value, false)
  } finally {
    lifecycle.unmount()
    state.close()
  }
})

test('late close from an old confirmation does not release a newer confirmation guard', async () => {
  const state = page({ getMockConfigs: async () => ({ data: [], totalSize: 0 }) })
  state.removeConfig(row())
  const old = state.confirmations[0]
  state.search()
  await flush()
  state.clearAllLogs()
  old.config.onClose()
  state.removeConfig(row(2))
  assert.equal(state.confirmations.length, 2)
  state.close()
})
