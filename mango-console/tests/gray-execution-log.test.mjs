import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/gray/execution-log')
const row = (extra = {}) => ({
  id: 11,
  create_time: '2026-11-07 10:00:00',
  feature_key: 'example.enabled',
  target_value: '0',
  status: 1,
  case_name: null,
  case_id: null,
  source_branch: null,
  target_branch: null,
  merge_request_url: null,
  merge_request_id: null,
  merge_request_iid: null,
  merge_request_state: null,
  error_message: null,
  before_snapshot: { enabled: false },
  after_snapshot: { enabled: true },
  ...extra,
})
const response = (rows = [row()], total = rows.length) => ({
  code: 200,
  data: rows,
  totalSize: total,
})
function page(api = {}) {
  const hooks = { mount: [], deactivate: [], activate: [], unmount: [] },
    calls = [],
    dialogs = [],
    messages = []
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'test-token', selected_environment: 0 })
  const route = vue.reactive({ fullPath: '/gray/execution-log/index' })
  const f = harness(
    'index',
    [
      'query,rows,listLoading,listError,optionRows,yamlOptions,optionsLoading,optionsError,pagination,detail,actions,actionBusy',
      'loadOptions,onSearch,onSearchRefresh,onReset,rowActions,onDetail,closeDetail,onRetryRestore,onCleanupExpired,requestParams,statusText,executionStatusColor',
    ].join(','),
    {
      base,
      api: {
        getGrayExecutionLog: async (params) => {
          calls.push(['list', params])
          return response()
        },
        getGrayYamlFile: async (params) => {
          calls.push(['options', params])
          return { code: 200, data: [{ id: 31, name: 'Example config' }] }
        },
        postGrayExecutionRetryRestore: async (params) => {
          calls.push(['restore', params])
          return { code: 200, data: { execution_log_id: 22, status: 1 } }
        },
        postGrayExecutionLogCleanupExpired: async (params) => {
          calls.push(['cleanup', params])
          return { code: 200, data: { retention_days: 30, deleted_count: 0 } }
        },
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
        '@/hooks/table': {
          usePagination: (callback) =>
            vue.reactive({
              page: 1,
              pageSize: 20,
              pageCount: 0,
              onChange: callback,
              setTotalSize(value) {
                this.pageCount = value
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
    user,
    route,
    hooks,
    calls,
    dialogs,
    messages,
    cleanup() {
      hooks.unmount.forEach((fn) => fn())
      f.close()
    },
  }
}

test('first list read is independent of options and initial activation does not read twice', async () => {
  const list = deferred(),
    options = deferred(),
    calls = []
  const p = page({
    getGrayExecutionLog: (params) => {
      calls.push(params)
      return list.promise
    },
    getGrayYamlFile: () => options.promise,
  })
  p.hooks.mount.forEach((fn) => fn())
  p.hooks.activate.forEach((fn) => fn())
  assert.equal(p.listLoading.value, true)
  assert.equal(p.optionsLoading.value, true)
  list.resolve(response())
  await flush()
  assert.equal(p.rows.value.length, 1)
  assert.equal(p.listLoading.value, false)
  assert.equal(p.optionsLoading.value, true)
  assert.equal(calls.length, 1)
  options.resolve({ code: 200, data: [] })
  await flush()
  assert.equal(p.optionsLoading.value, false)
  p.cleanup()
})

test('multiple search protocol preserves status zero, distinct IDs and text without empty conditions', async () => {
  const p = page()
  p.query.status = [0, 1, 0]
  p.query.config_type = [1, 2]
  p.query.case_type = [2]
  p.query.yaml_file = [31, 32]
  p.query.target_value = '0'
  p.query.case_id = '１２'
  p.query.test_suite_id = '9007199254740993'
  await p.onSearch()
  assert.deepEqual(p.calls[0], [
    'list',
    {
      page: 1,
      pageSize: 20,
      target_value: '0',
      status__in: '0,1',
      config_type__in: '1,2',
      case_type__in: '2',
      yaml_file__in: '31,32',
      case_id: '12',
      test_suite_id: '9007199254740993',
    },
  ])
  p.query.case_id = '12,13'
  assert.equal(p.query.case_id, '12')
  p.cleanup()
})

test('reset initializes all fields, fresh arrays and single-ID refs without undefined values', async () => {
  const p = page(),
    previous = p.query.status
  p.query.status = [0]
  p.query.yaml_file = [31]
  p.query.feature_key = 'Example'
  p.query.case_id = '12'
  p.pagination.page = 3
  p.onReset()
  await flush()
  assert.equal(p.pagination.page, 1)
  assert.equal(p.query.case_id, '')
  assert.equal(p.query.feature_key, '')
  assert.deepEqual(p.query.status, [])
  assert.notEqual(p.query.status, previous)
  assert.deepEqual(p.calls.at(-1), ['list', { page: 1, pageSize: 20 }])
  p.cleanup()
})

test('failed list read retains current data, unlocks and supports retry', async () => {
  let calls = 0
  const p = page({
    getGrayExecutionLog: async () => {
      if (++calls === 2) throw Error('Network')
      return response()
    },
  })
  await p.onSearch()
  assert.equal(await p.onSearch(), false)
  assert.equal(p.rows.value.length, 1)
  assert.equal(p.listError.value, true)
  assert.equal(p.listLoading.value, false)
  assert.equal(await p.onSearch(), true)
  assert.equal(p.listError.value, false)
  p.cleanup()
})

test('options failure is independent and selected missing configurations get explicit ID labels', async () => {
  let calls = 0
  const p = page({
    getGrayYamlFile: async () => {
      if (++calls === 1) throw Error('Network')
      return { code: 200, data: [{ id: 31, name: 'Example config' }] }
    },
  })
  p.query.yaml_file = [31, 32]
  await Promise.all([p.loadOptions(), p.onSearch()])
  assert.equal(p.listError.value, false)
  assert.equal(p.optionsError.value, true)
  assert.deepEqual(p.yamlOptions.value, [
    { label: 'ID 31', value: 31 },
    { label: 'ID 32', value: 32 },
  ])
  await p.loadOptions()
  assert.equal(p.optionsError.value, false)
  assert.deepEqual(p.yamlOptions.value, [
    { label: 'Example config', value: 31 },
    { label: 'ID 32', value: 32 },
  ])
  p.cleanup()
})

test('latest list request owns data and loading after older response', async () => {
  const first = deferred(),
    second = deferred()
  let calls = 0
  const p = page({ getGrayExecutionLog: () => (++calls === 1 ? first.promise : second.promise) })
  const old = p.onSearch(),
    next = p.onSearch()
  first.resolve(response([row({ feature_key: 'old' })]))
  await old
  assert.deepEqual(p.rows.value, [])
  assert.equal(p.listLoading.value, true)
  second.resolve(response([row({ feature_key: 'new' })]))
  await next
  assert.equal(p.rows.value[0].feature_key, 'new')
  p.cleanup()
})

test('options requests isolate out-of-order success and failure', async () => {
  const first = deferred(),
    second = deferred()
  let calls = 0
  const p = page({ getGrayYamlFile: () => (++calls === 1 ? first.promise : second.promise) })
  const old = p.loadOptions(),
    next = p.loadOptions()
  first.reject(Error('Old request'))
  await old
  assert.equal(p.optionsLoading.value, true)
  assert.equal(p.optionsError.value, false)
  second.resolve({ code: 200, data: [{ id: 32, name: 'Next config', audit: 'Readonly' }] })
  await next
  assert.deepEqual(p.optionRows.value, [{ label: 'Next config', value: 32 }])
  p.cleanup()
})

test('query edits invalidate reads and close existing details before search is submitted', async () => {
  const pending = deferred()
  let calls = 0
  const p = page({
    getGrayExecutionLog: () => (++calls === 1 ? Promise.resolve(response()) : pending.promise),
  })
  await p.onSearch()
  p.onDetail(p.rows.value[0])
  const old = p.onSearch()
  p.query.feature_key = 'Next'
  assert.equal(p.detail.id, null)
  pending.resolve(response())
  assert.equal(await old, false)
  assert.deepEqual(p.rows.value, [])
  assert.equal(p.listLoading.value, false)
  p.cleanup()
})

test('pagination uses page/pageSize and corrects an obsolete page after backend clamping', async () => {
  const p = page()
  p.pagination.page = 3
  p.pagination.pageSize = 10
  await p.pagination.onChange()
  assert.deepEqual(
    p.calls.map(([, params]) => params.page),
    [3, 1]
  )
  assert.equal(p.pagination.page, 1)
  assert.equal(p.pagination.pageCount, 1)
  p.cleanup()
})

test('empty generic response may omit totalSize', async () => {
  const p = page({ getGrayExecutionLog: async () => ({ code: 200, data: [] }) })
  assert.equal(await p.onSearch(), true)
  assert.equal(p.pagination.pageCount, 0)
  p.cleanup()
})

for (const field of ['userId', 'roleId', 'token', 'selected_environment'])
  test(`identity ${field} A-B-A invalidates old list and option responses`, async () => {
    const list = deferred(),
      options = deferred(),
      p = page({ getGrayExecutionLog: () => list.promise, getGrayYamlFile: () => options.promise })
    const one = p.onSearch(),
      two = p.loadOptions(),
      old = p.user[field]
    p.user[field] = field === 'token' ? 'next-test-token' : 9
    p.user[field] = old
    list.resolve(response())
    options.resolve({ code: 200, data: [{ id: 31, name: 'Old' }] })
    await Promise.all([one, two])
    assert.deepEqual(p.rows.value, [])
    assert.deepEqual(p.optionRows.value, [])
    assert.equal(p.listLoading.value, false)
    assert.equal(p.optionsLoading.value, false)
    p.cleanup()
  })

test('mounted identity switch reloads list and options independently in the new scope', async () => {
  const old = deferred()
  let reads = 0
  const p = page({
    getGrayExecutionLog: () => (++reads === 1 ? old.promise : Promise.resolve(response())),
  })
  p.hooks.mount.forEach((fn) => fn())
  p.user.selected_environment = 1
  await flush()
  assert.equal(reads, 2)
  assert.equal(p.rows.value.length, 1)
  old.resolve(response([row({ feature_key: 'old' })]))
  await flush()
  assert.equal(p.rows.value[0].feature_key, 'example.enabled')
  p.cleanup()
})

test('KeepAlive deactivation discards reads and details; activation loads once', async () => {
  const old = deferred()
  let reads = 0
  const p = page({
    getGrayExecutionLog: () => (++reads === 1 ? old.promise : Promise.resolve(response())),
  })
  p.hooks.mount.forEach((fn) => fn())
  p.hooks.deactivate.forEach((fn) => fn())
  old.resolve(response())
  await flush()
  assert.deepEqual(p.rows.value, [])
  assert.equal(await p.onSearch(), false)
  p.hooks.activate.forEach((fn) => fn())
  await flush()
  assert.equal(reads, 2)
  p.hooks.activate.forEach((fn) => fn())
  assert.equal(reads, 2)
  p.cleanup()
})

test('route departure clears records and blocks reads and operations', async () => {
  const p = page()
  await p.onSearch()
  p.onDetail(p.rows.value[0])
  p.route.fullPath = '/gray/feature/index'
  assert.deepEqual(p.rows.value, [])
  assert.equal(p.detail.id, null)
  assert.equal(await p.onSearch(), false)
  p.onCleanupExpired()
  assert.equal(p.dialogs.length, 0)
  p.cleanup()
})

test('details preserve complete source JSON, are isolated from source edits and can close and reopen', async () => {
  const source = row({ custom_audit: { name: 'Readonly' } })
  const p = page({ getGrayExecutionLog: async () => response([source]) })
  await p.onSearch()
  p.onDetail(p.rows.value[0])
  source.after_snapshot.enabled = false
  const detail = JSON.parse(p.detail.content)
  assert.equal(detail.after_snapshot.enabled, true)
  assert.equal(detail.custom_audit.name, 'Readonly')
  assert.equal('before_snapshot' in p.rows.value[0], false)
  p.closeDetail()
  assert.equal(p.detail.id, null)
  assert.equal(p.detail.content, '')
  p.onDetail(p.rows.value[0])
  assert.equal(p.detail.id, 11)
  p.cleanup()
})

for (const status of [0, 1, 2, 3, 4])
  test(`restoration action eligibility preserves status ${status}`, async () => {
    const p = page({ getGrayExecutionLog: async () => response([row({ status })]) })
    await p.onSearch()
    assert.equal(
      p.rowActions(p.rows.value[0]).some((item) => item.label === '恢复'),
      [1, 2, 4].includes(status)
    )
    assert.notEqual(p.statusText(status), '-')
    p.onRetryRestore(p.rows.value[0])
    assert.equal(p.dialogs.length, [1, 2, 4].includes(status) ? 1 : 0)
    p.cleanup()
  })

test('restore freezes its original ID and accepts the new execution record returned by the backend', async () => {
  const p = page()
  await p.onSearch()
  const source = p.rows.value[0]
  p.onRetryRestore(source)
  source.id = 99
  await p.dialogs[0].options.onBeforeOk()
  assert.deepEqual(
    p.calls.find(([kind]) => kind === 'restore'),
    ['restore', { execution_log_id: 11 }]
  )
  assert.equal(p.dialogs[0].closed, true)
  assert.equal(p.messages[0][1], '恢复成功')
  p.cleanup()
})

test('failed restoration outcome is recorded, closes the confirmation and refreshes rather than reporting success', async () => {
  const p = page({
    postGrayExecutionRetryRestore: async () => ({
      code: 200,
      data: { execution_log_id: 22, status: 2 },
    }),
  })
  await p.onSearch()
  p.onRetryRestore(p.rows.value[0])
  await p.dialogs[0].options.onBeforeOk()
  assert.equal(p.dialogs[0].closed, true)
  assert.equal(p.messages[0][0], 'error')
  assert.match(p.messages[0][1], /恢复失败/)
  assert.equal(p.calls.filter(([kind]) => kind === 'list').length, 2)
  p.cleanup()
})

test('cleanup keeps a fixed thirty-day global payload and accepts an explicit zero deletion count', async () => {
  const p = page()
  p.query.status = [1]
  p.query.yaml_file = [31]
  p.onCleanupExpired()
  await p.dialogs[0].options.onBeforeOk()
  assert.deepEqual(
    p.calls.find(([kind]) => kind === 'cleanup'),
    ['cleanup', { retention_days: 30 }]
  )
  assert.match(p.messages[0][1], /0 条/)
  assert.equal(p.dialogs[0].closed, true)
  p.cleanup()
})

for (const kind of ['restore', 'cleanup'])
  test(`${kind} physical lock blocks duplicate confirmation, cross-action and cancel until request settles`, async () => {
    const pending = deferred(),
      calls = []
    const api =
      kind === 'restore' ? 'postGrayExecutionRetryRestore' : 'postGrayExecutionLogCleanupExpired'
    const p = page({
      [api]: (params) => {
        calls.push(params)
        return pending.promise
      },
    })
    await p.onSearch()
    kind === 'restore' ? p.onRetryRestore(p.rows.value[0]) : p.onCleanupExpired()
    const dialog = p.dialogs[0],
      work = dialog.options.onBeforeOk()
    await dialog.options.onBeforeOk()
    p.onCleanupExpired()
    p.onRetryRestore(p.rows.value[0])
    assert.equal(dialog.options.onBeforeCancel(), false)
    assert.equal(calls.length, 1)
    assert.equal(p.dialogs.length, 1)
    pending.resolve({
      code: 200,
      data:
        kind === 'restore'
          ? { execution_log_id: 22, status: 1 }
          : { retention_days: 30, deleted_count: 1 },
    })
    await work
    assert.equal(p.actions.pending.value, null)
    assert.equal(dialog.closed, true)
    p.cleanup()
  })

for (const kind of ['restore', 'cleanup'])
  test(`${kind} request failure unlocks and permits retry within its confirmation`, async () => {
    let calls = 0
    const api =
      kind === 'restore' ? 'postGrayExecutionRetryRestore' : 'postGrayExecutionLogCleanupExpired'
    const p = page({
      [api]: async () => {
        if (++calls === 1) throw Error('Network')
        return {
          code: 200,
          data:
            kind === 'restore'
              ? { execution_log_id: 22, status: 1 }
              : { retention_days: 30, deleted_count: 1 },
        }
      },
    })
    await p.onSearch()
    kind === 'restore' ? p.onRetryRestore(p.rows.value[0]) : p.onCleanupExpired()
    const dialog = p.dialogs[0]
    await dialog.options.onBeforeOk()
    assert.equal(dialog.closed, false)
    assert.equal(p.actions.pending.value, null)
    await dialog.options.onBeforeOk()
    assert.equal(dialog.closed, true)
    p.cleanup()
  })

for (const [kind, ack] of [
  ['restore', { execution_log_id: null, status: 1 }],
  ['restore', { execution_log_id: 22, status: 7 }],
  ['cleanup', { retention_days: 7, deleted_count: 1 }],
  ['cleanup', { retention_days: 30 }],
  ['cleanup', { retention_days: 30, deleted_count: -1 }],
])
  test(`invalid ${kind} acknowledgment remains unconfirmed: ${JSON.stringify(ack)}`, async () => {
    const api =
      kind === 'restore' ? 'postGrayExecutionRetryRestore' : 'postGrayExecutionLogCleanupExpired'
    const p = page({ [api]: async () => ({ code: 200, data: ack }) })
    await p.onSearch()
    kind === 'restore' ? p.onRetryRestore(p.rows.value[0]) : p.onCleanupExpired()
    await p.dialogs[0].options.onBeforeOk()
    assert.equal(p.dialogs[0].closed, false)
    assert.equal(
      p.messages.some(([type]) => type === 'success'),
      false
    )
    p.cleanup()
  })

test('idle confirmation closes on query change and its old callback becomes inert', async () => {
  const p = page()
  p.onCleanupExpired()
  const dialog = p.dialogs[0]
  p.query.feature_key = 'Next'
  assert.equal(dialog.closed, true)
  await dialog.options.onBeforeOk()
  assert.equal(
    p.calls.some(([kind]) => kind === 'cleanup'),
    false
  )
  p.cleanup()
})

test('canceling an idle confirmation permits a new one and late old close cannot clear the new owner', async () => {
  const p = page()
  p.onCleanupExpired()
  const old = p.dialogs[0]
  assert.equal(old.options.onBeforeCancel(), true)
  old.close()
  assert.equal(p.actions.confirming.value, false)
  p.onCleanupExpired()
  old.options.onClose()
  assert.equal(p.actions.confirming.value, true)
  await old.options.onBeforeOk()
  assert.equal(
    p.calls.some(([kind]) => kind === 'cleanup'),
    false
  )
  await p.dialogs[1].options.onBeforeOk()
  assert.equal(p.dialogs[1].closed, true)
  p.cleanup()
})

for (const kind of ['restore', 'cleanup'])
  test(`${kind} non-success envelope cannot apply an otherwise valid acknowledgment`, async () => {
    const api =
      kind === 'restore' ? 'postGrayExecutionRetryRestore' : 'postGrayExecutionLogCleanupExpired'
    const p = page({
      [api]: async () => ({
        code: 400,
        data: { execution_log_id: 22, status: 1, retention_days: 30, deleted_count: 1 },
      }),
    })
    await p.onSearch()
    kind === 'restore' ? p.onRetryRestore(p.rows.value[0]) : p.onCleanupExpired()
    await p.dialogs[0].options.onBeforeOk()
    assert.equal(p.dialogs[0].closed, false)
    assert.equal(
      p.messages.some(([type]) => type === 'success'),
      false
    )
    assert.equal(p.calls.filter(([type]) => type === 'list').length, 1)
    p.cleanup()
  })

for (const invalid of [
  { code: 400, data: [{ id: 31, name: 'Example config' }] },
  { code: 200, data: [{ id: null, name: 'Invalid' }] },
])
  test(
    'invalid configuration options stay locally retryable: ' + JSON.stringify(invalid),
    async () => {
      const p = page({ getGrayYamlFile: async () => invalid })
      assert.equal(await p.loadOptions(), false)
      assert.equal(p.optionsError.value, true)
      assert.equal(p.optionsLoading.value, false)
      assert.deepEqual(p.optionRows.value, [])
      p.cleanup()
    }
  )

for (const kind of ['restore', 'cleanup'])
  test(`${kind} ignores stale response after identity A-B-A while retaining its physical lock`, async () => {
    const pending = deferred(),
      calls = []
    const api =
      kind === 'restore' ? 'postGrayExecutionRetryRestore' : 'postGrayExecutionLogCleanupExpired'
    const p = page({
      [api]: (params) => {
        calls.push(params)
        return pending.promise
      },
    })
    await p.onSearch()
    kind === 'restore' ? p.onRetryRestore(p.rows.value[0]) : p.onCleanupExpired()
    const work = p.dialogs[0].options.onBeforeOk()
    p.user.roleId = 9
    p.user.roleId = 2
    p.onCleanupExpired()
    assert.ok(p.actions.pending.value)
    assert.equal(calls.length, 1)
    assert.equal(p.dialogs.length, 1)
    pending.resolve({
      code: 200,
      data:
        kind === 'restore'
          ? { execution_log_id: 22, status: 1 }
          : { retention_days: 30, deleted_count: 1 },
    })
    await work
    assert.deepEqual(p.messages, [])
    assert.equal(p.actions.pending.value, null)
    p.cleanup()
  })

for (const hook of ['deactivate', 'unmount'])
  test(`${hook} ignores a late cleanup and keeps a lock until the request actually ends`, async () => {
    const pending = deferred(),
      p = page({ postGrayExecutionLogCleanupExpired: () => pending.promise })
    p.onCleanupExpired()
    const work = p.dialogs[0].options.onBeforeOk()
    p.hooks[hook].forEach((fn) => fn())
    p.hooks.activate.forEach((fn) => fn())
    p.onCleanupExpired()
    assert.equal(p.dialogs.length, 1)
    assert.ok(p.actions.pending.value)
    pending.resolve({ code: 200, data: { retention_days: 30, deleted_count: 0 } })
    await work
    assert.deepEqual(p.messages, [])
    assert.equal(p.actions.pending.value, null)
    p.cleanup()
  })

test('operation completion is distinguished from a failed refresh and closes stale details', async () => {
  let reads = 0
  const p = page({
    getGrayExecutionLog: async () => {
      if (++reads > 1) throw Error('Reload')
      return response()
    },
  })
  await p.onSearch()
  p.onDetail(p.rows.value[0])
  p.onRetryRestore(p.rows.value[0])
  await p.dialogs[0].options.onBeforeOk()
  assert.equal(p.dialogs[0].closed, true)
  assert.equal(p.detail.id, null)
  assert.equal(p.messages[0][1], '恢复成功')
  assert.equal(p.messages[1][1], '加载失败，请重试')
  assert.equal(p.messages.length, 2)
  assert.equal(p.listError.value, true)
  p.cleanup()
})

for (const invalid of [
  response([row({ id: null })]),
  response([row({ status: 7 })]),
  response([row(), row()]),
  { code: 400, data: [row()], totalSize: 1 },
  { code: 200, data: [], totalSize: -1 },
])
  test('invalid list data is retryable: ' + JSON.stringify(invalid), async () => {
    const p = page({ getGrayExecutionLog: async () => invalid })
    assert.equal(await p.onSearch(), false)
    assert.equal(p.listError.value, true)
    assert.deepEqual(p.rows.value, [])
    p.cleanup()
  })

test('merge request links accept HTTP(S) only', () => {
  const p = page()
  const { externalUrl } = p.load('records.ts')
  assert.equal(externalUrl('https://example.com/merge/1'), 'https://example.com/merge/1')
  assert.equal(externalUrl('javascript:alert(1)'), null)
  assert.equal(externalUrl('/relative-path'), null)
  assert.equal(externalUrl(null), null)
  p.cleanup()
})

test('execution page script, template and scoped styles compile', () => {
  const filename = path.join(base, 'index.vue'),
    { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'gray-execution-log' })
  assert.deepEqual(
    compileTemplate({
      source: descriptor.template.content,
      filename,
      id: 'gray-execution-log',
      compilerOptions: { bindingMetadata: script.bindings },
    }).errors,
    []
  )
  for (const style of descriptor.styles)
    assert.deepEqual(
      compileStyle({
        source: style.content,
        filename,
        id: 'gray-execution-log',
        scoped: style.scoped,
      }).errors,
      []
    )
})
