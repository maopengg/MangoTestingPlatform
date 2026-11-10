import assert from 'node:assert/strict'
import test from 'node:test'
import { evaluationComponent } from './helpers/evaluation-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'

const execution = (extra = {}) => ({
  id: 8,
  execution_no: 'fixture-run',
  status: 'running',
  test_env: 2,
  verdict: 'pending',
  ...extra,
})
const item = (id) => ({
  id,
  dataset_item_id: id,
  repeat_index: 1,
  execution_status: 'success',
  grade_status: 'graded',
  verdict: 'passed',
})
const executionApi = (extra) => ({
  getLatestCaseExecution: async () => ({ data: execution() }),
  getCaseExecution: async () => ({ data: execution() }),
  getCaseExecutionItems: async () => ({ data: { items: [item(1)], count: 1 } }),
  ...extra,
})
const panel = (api = {}, props = {}) =>
  evaluationComponent(
    'ExecutionPanel',
    'record,itemRows,recordLoading,itemsLoading,historyLoading,recordError,itemsError,historyError,historyRows,selectedHistoryId,loadHistory,refresh,loadItems,loadRecord,loadFrozenGraders,showGrading,gradingError,gradingLoading,frozenGraders,stop,retry,retrying,stopping,select,itemPagination,verdictFilter,filterItems',
    { api: executionApi(api), props }
  )
const browser = (api = {}, props = {}) =>
  evaluationComponent(
    'EvaluationItemBrowser',
    'items,itemDetail,execution,selectedId,itemsLoading,detailLoading,detailError,listError,executionLoading,executionError,loadItems,loadExecution,selectItem,page,hasMore',
    {
      api: executionApi({
        getCaseExecutionItem: async (_case, _execution, id) => ({ data: item(id) }),
        ...api,
      }),
      props: { executionId: 8, ...props },
    }
  )

test('overview renders before a slow item request and each region owns loading', async () => {
  const pending = deferred(),
    s = panel({ getCaseExecutionItems: () => pending.promise })
  try {
    await flush()
    assert.equal(s.record.value.id, 8)
    assert.equal(s.recordLoading.value, false)
    assert.equal(s.itemsLoading.value, true)
    pending.resolve({ data: { items: [item(1)], count: 1 } })
    await flush()
    assert.equal(s.itemsLoading.value, false)
  } finally {
    s.dispose()
  }
})
test('polling is silent, retries failures without clearing data, and stops at terminal success', async () => {
  let fail = false,
    status = 'pending'
  const pending = deferred()
  let slow = false
  const read = async () => {
    if (slow) return pending.promise
    if (fail) throw Error('offline')
    return { data: execution({ status }) }
  }
  const s = panel({ getLatestCaseExecution: read, getCaseExecution: read })
  try {
    await flush()
    const starts = s.polling.starts
    fail = true
    assert.equal(await s.poll(), false)
    assert.equal(s.record.value.id, 8)
    assert.ok(s.polling.starts > starts)
    fail = false
    slow = true
    const task = s.poll()
    await flush()
    assert.equal(s.recordLoading.value, false)
    assert.equal(s.itemsLoading.value, false)
    pending.resolve({ data: execution({ status: 'completed' }) })
    assert.equal(await task, true)
    assert.equal(s.record.value.status, 'completed')
    assert.ok(s.polling.stops > 0)
  } finally {
    s.dispose()
  }
})
test('a slow overview is not duplicated by a poll or manual refresh', async () => {
  const pending = deferred()
  let calls = 0
  const s = panel({
    getLatestCaseExecution: () => {
      calls++
      return pending.promise
    },
  })
  try {
    await s.poll()
    await s.refresh()
    assert.equal(calls, 1)
    pending.resolve({ data: execution() })
    await flush()
    assert.equal(s.record.value.id, 8)
  } finally {
    s.dispose()
  }
})
test('overview and item failures recover independently', async () => {
  let overviewFail = true,
    itemsFail = true
  const read = async () => {
    if (overviewFail) throw Error('offline')
    return { data: execution() }
  }
  const s = panel({
    getLatestCaseExecution: read,
    getCaseExecution: read,
    getCaseExecutionItems: async () => {
      if (itemsFail) throw Error('offline')
      return { data: { items: [item(1)], count: 1 } }
    },
  })
  try {
    await flush()
    assert.equal(s.recordError.value, true)
    assert.equal(s.recordLoading.value, false)
    overviewFail = false
    await s.refresh()
    assert.equal(s.recordError.value, false)
    assert.equal(s.itemsError.value, true)
    itemsFail = false
    await s.loadItems()
    assert.equal(s.itemsError.value, false)
    assert.equal(s.itemRows.value.length, 1)
  } finally {
    s.dispose()
  }
})
test('environment round trip, role switch and cached activation reject old result reads', async () => {
  const pending = deferred()
  let first = true
  const s = panel({
    getLatestCaseExecution: async () => {
      if (first) {
        first = false
        return pending.promise
      }
      return { data: execution({ id: 9 }) }
    },
  })
  try {
    s.user.selected_environment = 3
    s.user.selected_environment = 2
    await flush()
    pending.resolve({ data: execution() })
    await flush()
    assert.equal(s.record.value.id, 9)
    s.lifecycle.deactivate()
    assert.equal(s.record.value, null)
    s.lifecycle.activate()
    await flush()
    assert.equal(s.record.value.id, 9)
    s.user.roleId = 2
    assert.equal(s.record.value, null)
    await flush()
    assert.equal(s.record.value.id, 9)
  } finally {
    s.dispose()
  }
})
test('history error can retry and a late environment response cannot become selected', async () => {
  const pending = deferred()
  let calls = 0
  const s = panel(
    {
      getCaseExecutions: async () => {
        calls++
        if (calls === 1) throw Error('offline')
        if (calls === 2) return pending.promise
        return { data: { items: [execution({ id: 9, test_env: 3 })], count: 1 } }
      },
    },
    { history: true }
  )
  try {
    await flush()
    assert.equal(s.historyError.value, true)
    const task = s.loadHistory()
    s.user.selected_environment = 3
    await flush()
    pending.resolve({ data: { items: [execution()], count: 1 } })
    await task
    assert.equal(s.selectedHistoryId.value, 9)
    assert.equal(s.historyRows.value[0].test_env, 3)
    assert.equal(s.historyLoading.value, false)
  } finally {
    s.dispose()
  }
})
test('stop and retry share physical locks; stale retry success produces no UI update', async () => {
  const pending = deferred()
  let stops = 0,
    retries = 0
  const s = panel({
    retryCaseExecution: () => {
      retries++
      return pending.promise
    },
    stopCaseExecution: async () => {
      stops++
    },
  })
  try {
    await flush()
    const task = s.retry()
    assert.equal(await s.retry(), false)
    assert.equal(await s.stop(), false)
    s.user.selected_environment = 3
    s.user.selected_environment = 2
    await flush()
    pending.resolve({ data: { id: 10 } })
    assert.equal(await task, false)
    assert.equal(s.retrying.value, false)
    assert.equal(s.notices.length, 0)
    assert.equal(stops, 0)
    assert.equal(retries, 1)
  } finally {
    s.dispose()
  }
})
test('failed retry preserves its idempotency key and unlocks for explicit retry', async () => {
  const keys = []
  let fail = true
  const s = panel({
    retryCaseExecution: async (_case, _execution, key) => {
      keys.push(key)
      if (fail) throw Error('offline')
      return { data: { id: 10 } }
    },
  })
  try {
    await flush()
    assert.equal(await s.retry(), false)
    assert.equal(s.retrying.value, false)
    fail = false
    assert.equal(await s.retry(), true)
    assert.equal(keys[0], keys[1])
    assert.deepEqual(s.events[0], ['selected', 10])
  } finally {
    s.dispose()
  }
})
test('frozen grader partial failures retain successes and retry only missing items', async () => {
  const binding = { grader_key: 'fixture', grader_version: 1 }
  const reads = []
  let fail = true
  const s = panel({
    getLatestCaseExecution: async () => ({
      data: execution({ snapshot: { grader_bindings: { hash: binding } } }),
    }),
    getCaseExecutionItems: async () => ({ data: { items: [item(1), item(2)], count: 2 } }),
    getCaseExecutionItem: async (_case, _execution, id) => {
      reads.push(id)
      if (id === 2 && fail) throw Error('offline')
      return {
        data: { ...item(id), item_snapshot: { effective_graders: [{ binding_hash: 'hash' }] } },
      }
    },
  })
  try {
    await flush()
    assert.equal(await s.loadFrozenGraders(), false)
    assert.equal(s.frozenGraders.value[1][0].grader_key, 'fixture')
    fail = false
    assert.equal(await s.loadFrozenGraders(), true)
    assert.deepEqual(reads, [1, 2, 2])
    assert.equal(s.gradingLoading.value, false)
  } finally {
    s.dispose()
  }
})
test('detail browser releases left-list loading before slow selected content', async () => {
  const pending = deferred(),
    s = browser({ getCaseExecutionItem: () => pending.promise })
  try {
    await flush()
    assert.equal(s.items.value.length, 1)
    assert.equal(s.itemsLoading.value, false)
    assert.equal(s.detailLoading.value, true)
    pending.resolve({ data: item(1) })
    await flush()
    assert.equal(s.itemDetail.value.id, 1)
  } finally {
    s.dispose()
  }
})
test('detail browser newest selection wins and list append deduplicates rows', async () => {
  const pending = deferred()
  let delayed = false
  const s = browser({
    getCaseExecutionItems: async (_case, _execution, query) => ({
      data: { items: query.page === 1 ? [item(1)] : [item(1), item(2)], count: 25 },
    }),
    getCaseExecutionItem: async (_case, _execution, id) =>
      delayed && id === 1 ? pending.promise : { data: item(id) },
  })
  try {
    await flush()
    delayed = true
    const task = s.selectItem(1)
    await s.selectItem(2)
    pending.resolve({ data: item(1) })
    await task
    assert.equal(s.itemDetail.value.id, 2)
    await s.loadItems(false)
    assert.equal(s.page.value, 2)
    assert.deepEqual(s.items.value.map((row) => row.id).sort(), [1, 2])
  } finally {
    s.dispose()
  }
})
test('detail browser errors recover and identity changes suppress all late snapshots', async () => {
  const pending = deferred()
  let fail = true,
    delayed = false
  const s = browser({
    getCaseExecution: async () => {
      if (fail) throw Error('offline')
      return delayed ? pending.promise : { data: execution() }
    },
  })
  try {
    await flush()
    assert.equal(s.executionError.value, true)
    fail = false
    await s.loadExecution()
    assert.equal(s.executionError.value, false)
    delayed = true
    const task = s.loadExecution()
    s.lifecycle.deactivate()
    pending.resolve({ data: execution() })
    await task
    assert.equal(s.execution.value, null)
    assert.equal(s.executionLoading.value, false)
  } finally {
    s.dispose()
  }
})
test('malformed dynamic evidence is safely ignored while real excerpts and ranks remain', () => {
  const s = evaluationComponent('ItemResultContent', 'expectedSources,memories,memoryContent', {
    props: {
      item: {
        ...item(1),
        resolved_expected_output: { source_excerpt: 'Example fact' },
        actual_output: { retrieval: [null, { evidence: [null, { excerpt: 'Example fact' }] }] },
        item_snapshot: {
          input_data: { query: 'Question' },
          context: { source_evidence: [null, 'Example fact'] },
        },
      },
    },
  })
  try {
    assert.equal(s.expectedSources.value[0].text, 'Example fact')
    assert.deepEqual(s.expectedSources.value[0].ranks, [2])
    assert.equal(s.memoryContent(null), undefined)
    assert.equal(s.memories.value.length, 2)
  } finally {
    s.dispose()
  }
})
