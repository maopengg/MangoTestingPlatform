import test from 'node:test'
import assert from 'node:assert/strict'
import { computed, ref } from 'vue'
import { harness, method, deferred } from './helpers/case-details-harness.mjs'

function runtimeState() {
  const state = {
    caseRuntimeRunning: ref(false), caseRequestPending: ref(false),
    debugRequestPending: ref(false), scenarioHeaderSavingCount: ref(0),
    startCaseRunRefresh() { state.polling = true },
    stopCaseRunRefresh() { state.polling = false },
    polling: false,
  }
  state.hasRunningCaseStep = method('hasRunningCaseStep', {})
  state.syncCaseRunRefreshByRows = method('syncCaseRunRefreshByRows', state)
  state.active = method('caseExecutionActive', { ...state, computed })
  return state
}

test('unexecuted steps do not lock editing or debugging; running steps still do', () => {
  const state = runtimeState()
  const table = harness('ApiCaseStepTable', 'rowActions', { props: { getApiInfoId: () => 20 } })
  for (const statuses of [[], [2, 2], ['2', '1'], [0, 1, 4, 5]]) {
    state.syncCaseRunRefreshByRows(statuses.map(status => ({ status })))
    assert.equal(state.active.value, false)
    assert.equal(state.polling, false)
    table.props.executionActive = state.active.value
    assert.ok(table.rowActions({ id: 1 }).slice(0, 2).every(action => !action.disabled))
  }
  state.syncCaseRunRefreshByRows([{ status: '3' }, { status: 2 }])
  table.props.executionActive = state.active.value
  assert.equal(state.active.value, true)
  assert.equal(state.polling, true)
  assert.ok(table.rowActions({ id: 1 }).slice(0, 2).every(action => action.disabled))
  state.syncCaseRunRefreshByRows([{ status: 1 }])
  assert.equal(state.active.value, false)
  assert.equal(state.polling, false)
  table.props.editLocked = true
  table.props.executionActive = false
  assert.ok(table.rowActions({ id: 1 }).slice(0, 2).every(action => action.disabled))
  table.close()
})

test('displayed status mutations cannot acquire or release the runtime lock', () => {
  const state = runtimeState()
  const rows = [{ status: 1 }]
  state.syncCaseRunRefreshByRows(rows)
  rows[0].status = 2
  assert.equal(state.active.value, false)
  rows[0].status = 3
  assert.equal(state.active.value, false)
  state.syncCaseRunRefreshByRows(rows)
  rows[0].status = 1
  assert.equal(state.active.value, true)
})

test('pending requests and saves retain protection independently of runtime results', () => {
  const state = runtimeState()
  for (const name of ['caseRequestPending', 'debugRequestPending', 'scenarioHeaderSavingCount']) {
    state[name].value = name === 'scenarioHeaderSavingCount' ? 1 : true
    state.syncCaseRunRefreshByRows([{ status: 2 }])
    assert.equal(state.active.value, true)
    state[name].value = name === 'scenarioHeaderSavingCount' ? 0 : false
    assert.equal(state.active.value, false)
  }
})

test('initial refresh captures runtime before selected historical results mutate rows', async () => {
  const state = runtimeState()
  const rows = [{ id: 10, status: 1 }]
  const refresh = method('doRefresh', {
    apiCaseId: ref(1), pageActive: true, caseVersionPayloadActive: ref(false),
    requests: { begin: () => () => true }, stepTableLoading: ref(false),
    optionLists: {}, caseRecord: ref({ front_headers: [] }),
    getApiCaseDetailed: async () => ({ data: rows }), normalizeCaseDetailRow: row => row,
    caseSteps: ref([]), selectedStep: ref(null), scenarios: ref([]),
    select: async row => { row.status = 2 }, invalidateParameterLoad() {},
    syncCaseRunRefreshByRows: state.syncCaseRunRefreshByRows,
  })
  await refresh()
  assert.equal(rows[0].status, 2)
  assert.equal(state.active.value, false)
  assert.equal(state.polling, false)
})

test('polling uses live status even if result rendering changes it, and preserves frozen steps', async () => {
  for (const snapshot of [false, true]) {
    const state = runtimeState()
    const rows = [{ id: 10, status: 3 }]
    let merges = 0
    const refresh = method('refreshCaseRunStatusByStep', {
      ...state, apiCaseId: ref(1), requests: { capture: () => () => true },
      getApiCaseDetailed: async () => ({ data: rows }),
      caseVersionPayloadActive: ref(snapshot),
      mergeCaseStepRows: () => { merges++ },
      isRuntimeResultTab: () => true,
      refreshSelectedRuntimeResult: async () => { rows[0].status = 1 },
    })
    assert.equal(await refresh(), true)
    assert.equal(state.active.value, true)
    assert.equal(state.polling, true)
    assert.equal(merges, snapshot ? 0 : 1)
    assert.equal(await refresh(), false)
    assert.equal(state.active.value, false)
    assert.equal(state.polling, false)
  }
})

test('late polling cannot overwrite the runtime state', async () => {
  const state = runtimeState(), pending = deferred()
  state.syncCaseRunRefreshByRows([{ status: 3 }])
  let current = true
  const refresh = method('refreshCaseRunStatusByStep', {
    ...state, apiCaseId: ref(1), requests: { capture: () => () => current },
    getApiCaseDetailed: () => pending.promise,
    mergeCaseStepRows: () => assert.fail('late response merged'),
  })
  const running = refresh()
  current = false
  pending.resolve({ data: [{ status: 1 }] })
  assert.equal(await running, false)
  assert.equal(state.active.value, true)
})

test('failed polling retains the runtime lock and remains retryable', async () => {
  const state = runtimeState()
  state.syncCaseRunRefreshByRows([{ status: 3 }])
  const refresh = method('refreshCaseRunStatusByStep', {
    ...state, apiCaseId: ref(1), requests: { capture: () => () => true },
    getApiCaseDetailed: async () => { throw new Error('offline') },
    console: { log() {} },
  })
  assert.equal(await refresh(), null)
  assert.equal(state.active.value, true)
  assert.equal(state.polling, true)
})

test('switching context during result loading cannot restart the old poller', async () => {
  const state = runtimeState(), pending = deferred()
  let current = true
  const refresh = method('refreshCaseRunStatusByStep', {
    ...state, apiCaseId: ref(1), requests: { capture: () => () => current },
    getApiCaseDetailed: async () => ({ data: [{ status: 3 }] }),
    caseVersionPayloadActive: ref(false), mergeCaseStepRows() {},
    isRuntimeResultTab: () => true, refreshSelectedRuntimeResult: () => pending.promise,
  })
  const loading = refresh()
  await Promise.resolve()
  current = false
  state.caseRuntimeRunning.value = false
  state.stopCaseRunRefresh()
  pending.resolve()
  assert.equal(await loading, false)
  assert.equal(state.active.value, false)
  assert.equal(state.polling, false)
})
