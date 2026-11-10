import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { setupExecution, execution as row } from './helpers/factory-execution-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/data-factory/execution')
const page = (api = {}) =>
  setupExecution(
    'index',
    'rows,listLoading,loadError,pagination,executionConditionItems,doRefresh,onSearch,onResetSearch,onNavigationFilterChange,onSelectionChange,selectedRowKeys,executionActions,cleanup,batchCleanup,cleanupIds,batchCleanupLoading,detailRef,loadEnums,enumsLoading,enumsError',
    api
  )
const detail = (api = {}) =>
  setupExecution(
    'ExecutionDetailDrawer',
    'open,visible,detail,detailLoading,loadError,reload:load,refreshFor,copyCellValue,copying,cleanupResourceRows',
    api
  )

test('list and full detail drawer compile', () => {
  for (const file of ['index.vue', 'components/ExecutionDetailDrawer.vue']) {
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
test('cleanability preserves all original business statuses and never depends on role', () => {
  const s = page()
  try {
    const { canCleanup } = s.load('display.ts')
    for (const status of [0, 1])
      for (const cleanup_status of [0, 2, 4])
        assert.equal(canCleanup(row(1, { status, cleanup_status })), true)
    for (const status of [2, 3]) assert.equal(canCleanup(row(1, { status })), false)
    for (const cleanup_status of [1, 3]) assert.equal(canCleanup(row(1, { cleanup_status })), false)
    s.user.roleId = 4
    assert.deepEqual(
      s.executionActions(row()).map((a) => a.label),
      ['详情', '清理']
    )
  } finally {
    s.dispose()
  }
})
test('search factory isolates state; empty parameters cleaned, product/module resolved and multi status retained', async () => {
  const calls = [],
    s = page({
      getDataFactoryExecution: async (p) => {
        calls.push(p)
        return { data: [], totalSize: 0 }
      },
    }),
    other = page()
  try {
    s.executionConditionItems.find((i) => i.key === 'project_product').value = [2, 10]
    s.executionConditionItems.find((i) => i.key === 'module').value = 20
    s.executionConditionItems.find((i) => i.key === 'status').value = [0, 1]
    s.executionConditionItems.find((i) => i.key === 'cleanup_status').value = [0, 4]
    s.pagination.page = 5
    await s.onSearch()
    assert.deepEqual(calls[0], {
      project_product: 10,
      module: 20,
      status__in: '0,1',
      cleanup_status__in: '0,4',
      page: 1,
      pageSize: 20,
    })
    assert.deepEqual(other.executionConditionItems.find((i) => i.key === 'status').value, [])
    await s.onResetSearch()
    assert.deepEqual(calls.at(-1), { page: 1, pageSize: 20 })
  } finally {
    s.dispose()
    other.dispose()
  }
})
test('latest list controls loading and data; failed read retains rows and enables retry', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const s = page({
    getDataFactoryExecution: () =>
      ++count === 1 ? a.promise : count === 2 ? b.promise : Promise.reject(Error('fixture')),
  })
  try {
    const first = s.doRefresh(),
      second = s.doRefresh()
    a.resolve({ data: [row(1)], totalSize: 1 })
    await first
    assert.equal(s.listLoading.value, true)
    b.resolve({ data: [row(2)], totalSize: 4 })
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
test('route execution number updates within cached page and clears obsolete route input', async () => {
  const calls = [],
    s = page({
      getDataFactoryExecution: async (p) => {
        calls.push(p)
        return { data: [], totalSize: 0 }
      },
    })
  try {
    s.route.query.execution_no = 'E2'
    await flush()
    assert.equal(calls.at(-1).execution_no, 'E2')
    s.pagination.page = 4
    delete s.route.query.execution_no
    await flush()
    assert.equal('execution_no' in calls.at(-1), false)
    assert.equal(calls.at(-1).page, 1)
  } finally {
    s.dispose()
  }
})
test('selection accepts only visible cleanable rows; detail and clean actions remain business-controlled', () => {
  const s = page()
  try {
    s.rows.value = [row(1), row(2, { status: 3 }), row(3, { cleanup_status: 1 })]
    s.onSelectionChange([1, 2, 3, 99])
    assert.deepEqual(s.selectedRowKeys.value, [1])
    s.cleanupIds.add(1)
    s.onSelectionChange([1])
    assert.deepEqual(s.selectedRowKeys.value, [])
    assert.deepEqual(
      s.executionActions(row(2, { status: 3 })).map((a) => a.label),
      ['详情']
    )
  } finally {
    s.dispose()
  }
})
test('single cleanup snapshots ID, serializes pending requests and supports network/partial retries', async () => {
  const pending = deferred(),
    calls = [],
    s = page({
      postDataFactoryExecutionCleanup: (p) => {
        calls.push(p)
        return calls.length === 1
          ? pending.promise
          : calls.length === 2
          ? Promise.resolve({ data: { fail: 1, message: 'partial' } })
          : Promise.resolve({ data: { fail: 0 }, msg: 'ok' })
      },
    })
  try {
    const record = row(7)
    s.rows.value = [record]
    s.cleanup(record)
    record.id = 8
    const config = s.confirmations[0].config,
      cleaning = config.onBeforeOk()
    assert.equal(await config.onBeforeOk(), false)
    assert.deepEqual(calls, [{ execution_id: 7 }])
    pending.reject(Error('fixture'))
    assert.equal(await cleaning, false)
    assert.equal(s.cleanupIds.size, 0)
    assert.equal(await config.onBeforeOk(), false)
    assert.equal(await config.onBeforeOk(), true)
    assert.equal(calls.length, 3)
    assert.equal(s.cleanupIds.size, 0)
  } finally {
    s.dispose()
  }
})
test('batch cleanup snapshots selected IDs, blocks overlapping cleanup and keeps partial failures retryable', async () => {
  const pending = deferred(),
    calls = [],
    s = page({
      postDataFactoryExecutionBatchCleanup: (p) => {
        calls.push(p)
        return pending.promise
      },
    })
  try {
    s.rows.value = [row(1), row(2)]
    s.onSelectionChange([1, 2])
    s.batchCleanup()
    s.selectedRowKeys.value = [9]
    const config = s.confirmations[0].config,
      cleaning = config.onBeforeOk()
    assert.equal(await config.onBeforeOk(), false)
    s.cleanup(row(3))
    assert.equal(s.confirmations.length, 1)
    assert.deepEqual(calls, [{ execution_ids: [1, 2] }])
    pending.resolve({ data: { fail: 1 }, msg: 'partial' })
    assert.equal(await cleaning, false)
    assert.equal(s.batchCleanupLoading.value, false)
    assert.equal(s.cleanupIds.size, 0)
  } finally {
    s.dispose()
  }
})
test('navigation invalidates cleanup confirmations and identity change discards old success while preserving physical lock', async () => {
  const pending = deferred()
  let calls = 0
  const s = page({
    postDataFactoryExecutionCleanup: () => {
      calls++
      return pending.promise
    },
  })
  try {
    s.cleanup(row())
    await s.onNavigationFilterChange({ projectProduct: 10, module: 20 })
    assert.equal(s.confirmations[0].closed, true)
    assert.equal(await s.confirmations[0].config.onBeforeOk(), false)
    assert.equal(calls, 0)
    s.cleanup(row())
    const cleaning = s.confirmations[1].config.onBeforeOk()
    s.user.roleId = 2
    assert.equal(s.cleanupIds.has(1), true)
    pending.resolve({ data: { fail: 0 }, msg: 'stale' })
    await cleaning
    assert.equal(s.notices.includes('stale'), false)
    assert.equal(s.cleanupIds.size, 0)
  } finally {
    s.dispose()
  }
})
test('cleaning refreshes only matching visible detail via its scoped handle', async () => {
  const refreshed = [],
    s = page({ postDataFactoryExecutionCleanup: async () => ({ data: { fail: 0 }, msg: 'ok' }) })
  try {
    s.detailRef.value = { open() {}, close() {}, refreshFor: (id) => refreshed.push(id) }
    s.cleanup(row(7))
    assert.equal(await s.confirmations[0].config.onBeforeOk(), true)
    assert.deepEqual(refreshed, [7])
  } finally {
    s.dispose()
  }
})
test('detail opens before response with local loading, handles latest record and retries failure', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const s = detail({
    getDataFactoryExecutionDetail: () =>
      ++count === 1 ? a.promise : count === 2 ? b.promise : Promise.reject(Error('fixture')),
  })
  try {
    s.open(row(1))
    assert.equal(s.visible.value, true)
    assert.equal(s.detailLoading.value, true)
    s.open(row(2))
    a.resolve({ data: { execution: row(1) } })
    await flush()
    assert.equal(s.detailLoading.value, true)
    b.resolve({ data: { execution: row(2), items: [] } })
    await flush()
    assert.equal(s.detail.value.execution.id, 2)
    await s.reload()
    assert.equal(s.loadError.value, true)
    assert.equal(s.detailLoading.value, false)
    assert.equal(s.detail.value.execution.id, 2)
  } finally {
    s.dispose()
  }
})
test('detail close and cache stop discard late reply; resume never automatically reopens drawer', async () => {
  const pending = deferred()
  let count = 0
  const s = detail({
    getDataFactoryExecutionDetail: () => {
      count++
      return pending.promise
    },
  })
  try {
    s.open(row())
    s.lifecycle.deactivate()
    pending.resolve({ data: { execution: row() } })
    await flush()
    assert.equal(s.visible.value, false)
    assert.equal(s.detail.value, null)
    s.lifecycle.activate()
    assert.equal(count, 1)
  } finally {
    s.dispose()
  }
})
test('resource snapshots tolerate missing rule and use distinct keys; indexed and legacy results preserve semantics', () => {
  const s = detail()
  try {
    const { cleanupResources } = s.load('display.ts')
    const values = cleanupResources({
      execution: row(),
      items: [
        {
          id: 1,
          alias: 'a',
          cleanup_resources: {
            sql_cleaned: true,
            snapshots: [
              { index: 'i', document_id: '1' },
              { index: 'i', document_id: '1' },
            ],
            results: [
              { snapshot_index: 0, success: true },
              { snapshot_index: 1, success: false, error: 'failed' },
            ],
          },
        },
      ],
    })
    assert.equal(values[0].status, '已确认消失')
    assert.equal(values[1].status, '失败')
    assert.notEqual(values[0].key, values[1].key)
    assert.equal(values[0].sql_status, '已清理')
    assert.deepEqual(cleanupResources(null), [])
  } finally {
    s.dispose()
  }
})
test('clipboard async copy has local duplicate guard and suppresses messages after closing context', async () => {
  const originalNavigator = globalThis.navigator,
    originalWindow = globalThis.window,
    pending = deferred(),
    calls = [],
    s = detail()
  Object.defineProperty(globalThis, 'navigator', {
    configurable: true,
    value: {
      clipboard: {
        writeText: (text) => {
          calls.push(text)
          return pending.promise
        },
      },
    },
  })
  globalThis.window = { isSecureContext: true }
  try {
    s.open(row())
    const copying = s.copyCellValue({ x: 0 }, '创建数据')
    await s.copyCellValue('second', 'SQL')
    assert.equal(s.copying.value, true)
    assert.deepEqual(calls, ['{"x":0}'])
    s.close()
    pending.resolve()
    await copying
    assert.equal(s.copying.value, false)
    assert.equal(s.notices.length, 0)
  } finally {
    s.dispose()
    Object.defineProperty(globalThis, 'navigator', { configurable: true, value: originalNavigator })
    globalThis.window = originalWindow
  }
})
