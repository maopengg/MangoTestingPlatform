import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { evaluationComponent } from './helpers/evaluation-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'

const row = (id = 1, extra = {}) => ({
  id,
  name: `Example ${id}`,
  status: 'enabled',
  project_product: 2,
  project_product_data: { id: 2, name: 'Product' },
  module: 3,
  module_data: { id: 3, name: 'Module', full_path: 'Root/Module' },
  ...extra,
})
function page(api = {}) {
  const dialogs = []
  const s = evaluationComponent(
    'CaseList',
    'rows,loading,loadError,reload:load,filters,moduleIds,pagination,resetKey,sidebarChanged,search,reset,openCreate,openEdit,editor,toggleStatus,statusPending,execute,executing,copy,copying,remove,deleting,isBusy',
    {
      filename: path.resolve('src/views/evaluation/case/index.vue'),
      api: { getEvaluationCases: async () => ({ data: { items: [row()], count: 1 } }), ...api },
      Modal: {
        warning(config) {
          const modal = {
            config,
            closed: false,
            close() {
              this.closed = true
              config.onClose?.()
            },
          }
          dialogs.push(modal)
          return modal
        },
      },
    }
  )
  return { ...s, dialogs }
}

test('query mapping uses true navigation IDs, multiple values and no empty conditions', async () => {
  const queries = [],
    s = page({
      getEvaluationCases: async (query) => {
        queries.push(query)
        return { data: { items: [row()], count: 1 } }
      },
    })
  try {
    await flush()
    s.filters.status = ['enabled', 'draft']
    s.filters.target_type = ['api_info', 'script']
    s.filters.name = ' Example '
    await s.sidebarChanged({ projectProduct: '2', module: '3', moduleIds: ['3', 4] })
    assert.deepEqual(queries.at(-1), {
      page: 1,
      pageSize: 10,
      name: 'Example',
      status__in: 'enabled,draft',
      target_type__in: 'api_info,script',
      project_product: 2,
      module__in: '3,4',
      test_env: 2,
    })
    assert.equal(s.rows.value[0].project_product, 2)
    assert.equal(s.rows.value[0].module_data.full_path, 'Root/Module')
    await s.reset()
    assert.deepEqual(s.filters.status, [])
    assert.deepEqual(s.filters.target_type, [])
    assert.deepEqual(queries.at(-1), { page: 1, pageSize: 10, test_env: 2 })
  } finally {
    s.dispose()
  }
})
test('latest list request owns data and loading', async () => {
  const first = deferred(),
    second = deferred()
  let reads = 0
  const s = page({ getEvaluationCases: () => (++reads === 1 ? first.promise : second.promise) })
  try {
    const task = s.search()
    first.resolve({ data: { items: [row(1)], count: 10 } })
    await flush()
    assert.equal(s.loading.value, true)
    assert.deepEqual(s.rows.value, [])
    second.resolve({ data: { items: [row(2)], count: 1 } })
    await task
    assert.equal(s.rows.value[0].id, 2)
    assert.equal(s.loading.value, false)
  } finally {
    s.dispose()
  }
})
test('list error retains existing data and can retry', async () => {
  let fail = false
  const s = page({
    getEvaluationCases: async () => {
      if (fail) throw Error('offline')
      return { data: { items: [row()], count: 1 } }
    },
  })
  try {
    await flush()
    fail = true
    assert.equal(await s.reload(), false)
    assert.equal(s.loadError.value, true)
    assert.equal(s.rows.value.length, 1)
    assert.equal(s.loading.value, false)
    fail = false
    assert.equal(await s.reload(), true)
    assert.equal(s.loadError.value, false)
  } finally {
    s.dispose()
  }
})
test('status update waits for success, rejects duplicates and submits only status', async () => {
  const pending = deferred(),
    writes = []
  let status = 'enabled'
  const s = page({
    getEvaluationCases: async () => ({ data: { items: [row(1, { status })], count: 1 } }),
    updateEvaluationCase: (value) => {
      writes.push(value)
      return pending.promise
    },
  })
  try {
    await flush()
    const task = s.toggleStatus(s.rows.value[0], false)
    assert.equal(s.rows.value[0].status, 'enabled')
    assert.equal(await s.toggleStatus(s.rows.value[0], false), false)
    status = 'draft'
    pending.resolve({ data: { status } })
    assert.equal(await task, true)
    assert.deepEqual(writes, [{ id: 1, status: 'draft' }])
    assert.equal(s.rows.value[0].status, 'draft')
    assert.equal(s.statusPending.size, 0)
  } finally {
    s.dispose()
  }
})
test('failed status update leaves the switch unchanged and unlocks', async () => {
  const s = page({
    updateEvaluationCase: async () => {
      throw Error('Forbidden')
    },
  })
  try {
    await flush()
    assert.equal(await s.toggleStatus(s.rows.value[0], false), false)
    assert.equal(s.rows.value[0].status, 'enabled')
    assert.equal(s.statusPending.size, 0)
  } finally {
    s.dispose()
  }
})
test('copy operations retain independent row locks and suppress stale success after environment changes', async () => {
  const first = deferred(),
    second = deferred()
  const s = page({ copyEvaluationCase: (id) => (id === 1 ? first.promise : second.promise) })
  try {
    await flush()
    const a = s.copy(row(1)),
      b = s.copy(row(2))
    assert.deepEqual([...s.copying], [1, 2])
    assert.equal(await s.copy(row(1)), false)
    first.resolve({})
    await a
    assert.deepEqual([...s.copying], [2])
    const notices = s.notices.length
    s.user.selected_environment = 3
    second.resolve({})
    assert.equal(await b, false)
    assert.equal(s.notices.length, notices)
    assert.equal(s.copying.size, 0)
  } finally {
    s.dispose()
  }
})
test('execution captures environment and keeps its key for failed retries', async () => {
  const writes = []
  let fail = true
  const s = page({
    executeEvaluationCase: async (id, value, key) => {
      writes.push({ id, value, key })
      if (fail) throw Error('offline')
      return { data: { id: 8 } }
    },
  })
  try {
    await flush()
    assert.equal(await s.execute(row()), false)
    fail = false
    assert.equal(await s.execute(row()), true)
    assert.equal(writes[0].key, writes[1].key)
    assert.deepEqual(writes[1].value, { test_env: 2 })
    assert.deepEqual(s.navigations[0].query, { id: 1, execution: 8 })
  } finally {
    s.dispose()
  }
})
test('old execution success cannot navigate after environment round trip', async () => {
  const pending = deferred(),
    s = page({ executeEvaluationCase: () => pending.promise })
  try {
    await flush()
    const task = s.execute(row())
    assert.equal(await s.execute(row()), false)
    s.user.selected_environment = 3
    s.user.selected_environment = 2
    pending.resolve({ data: { id: 8 } })
    assert.equal(await task, false)
    assert.equal(s.executing.size, 0)
    assert.deepEqual(s.navigations, [])
    assert.deepEqual(s.notices, [])
  } finally {
    s.dispose()
  }
})
test('new metadata editor receives scalar defaults and edit only receives a case ID', async () => {
  const opens = [],
    s = page()
  try {
    await flush()
    s.editor.value = { open: (...args) => opens.push(args) }
    await s.sidebarChanged({ projectProduct: '2', module: '3' })
    s.openCreate()
    s.openEdit(row())
    assert.deepEqual(opens, [[undefined, 2, 3], [1]])
  } finally {
    s.dispose()
  }
})
test('delete waits for confirmation, locks repeats and retains a failed dialog for retry', async () => {
  const pending = deferred(),
    deleted = []
  let fail = true
  const s = page({
    deleteEvaluationCase: async (id) => {
      deleted.push(id)
      if (fail) return pending.promise
      return {}
    },
  })
  try {
    await flush()
    s.remove(row())
    s.remove(row(2))
    assert.equal(s.dialogs.length, 1)
    assert.deepEqual(deleted, [])
    const confirm = s.dialogs[0].config
    const first = confirm.onBeforeOk()
    assert.equal(await confirm.onBeforeOk(), false)
    pending.reject(Error('Protected'))
    assert.equal(await first, false)
    assert.equal(s.dialogs[0].closed, false)
    assert.equal(s.deleting.size, 0)
    fail = false
    assert.equal(await confirm.onBeforeOk(), true)
    assert.deepEqual(deleted, [1, 1])
  } finally {
    s.dispose()
  }
})
test('delete cancellation and identity changes cannot submit an old confirmation', async () => {
  let writes = 0
  const s = page({
    deleteEvaluationCase: async () => {
      writes++
    },
  })
  try {
    await flush()
    s.remove(row())
    const old = s.dialogs[0]
    old.close()
    assert.equal(await old.config.onBeforeOk(), false)
    s.remove(row())
    const stale = s.dialogs[1]
    s.user.roleId = 2
    assert.equal(stale.closed, true)
    assert.equal(await stale.config.onBeforeOk(), false)
    assert.equal(writes, 0)
  } finally {
    s.dispose()
  }
})
test('deleting the last row goes back one page before reloading', async () => {
  const queries = [],
    s = page({
      getEvaluationCases: async (query) => {
        queries.push(query)
        return { data: { items: [row()], count: 11 } }
      },
    })
  try {
    await flush()
    s.pagination.page = 2
    s.remove(row())
    assert.equal(await s.dialogs[0].config.onBeforeOk(), true)
    assert.equal(s.pagination.page, 1)
    assert.equal(queries.at(-1).page, 1)
  } finally {
    s.dispose()
  }
})
test('cached and identity lifecycle invalidate reads, close windows and restore safely', async () => {
  const pending = deferred()
  let first = true
  const s = page({
    getEvaluationCases: async () => {
      if (first) {
        first = false
        return pending.promise
      }
      return { data: { items: [row(2)], count: 1 } }
    },
  })
  try {
    s.filters.name = 'old'
    s.lifecycle.deactivate()
    pending.resolve({ data: { items: [row()], count: 1 } })
    await flush()
    assert.deepEqual(s.rows.value, [])
    s.lifecycle.activate()
    await flush()
    assert.equal(s.rows.value[0].id, 2)
    s.user.roleId = 2
    assert.equal(s.filters.name, '')
    await flush()
    assert.equal(s.rows.value[0].id, 2)
  } finally {
    s.dispose()
  }
})
