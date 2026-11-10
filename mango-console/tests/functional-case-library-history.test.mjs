import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/case-library')
const subject = (id = 11) => ({ id, title: 'Example case', case_no: `CASE-${id}` })
const version = (id, values = {}) => ({ id, case: 11, version_no: id, snapshot: { priority: 0 }, ...values })
function setup(overrides = {}) {
  return harness('CaseHistoryDrawer', 'open, closeHistory, loadHistory, visible, subject, historyVersions, activeHistory, historySnapshot, historyLoading, loadError, enumLabel, enumLabels', {
    base, props: { contextKey: 'context-1' }, ...overrides,
  })
}

test('history owns a subject snapshot, selects first version and preserves zero enums', async () => {
  const f = setup({ api: { getManualCaseVersions: async () => ({ data: [version(2), version(1)] }) } })
  try {
    const source = subject(); await f.open(source); source.title = 'Outside change'
    assert.equal(f.subject.value.title, 'Example case')
    assert.equal(f.activeHistory.value.id, 2); assert.equal(f.historySnapshot.value.priority, 0)
    assert.equal(f.enumLabel([{ key: '0', title: 'Highest' }], 0), 'Highest')
    assert.equal(f.enumLabel([], 0), '0')
    assert.equal(f.enumLabels([{ key: 0, title: 'Type zero' }], [0]), 'Type zero')
    f.activeHistory.value = f.historyVersions.value[1]
    await f.loadHistory(); assert.equal(f.activeHistory.value.id, 1)
  } finally { f.close() }
})

test('load failure remains distinct from empty success and permits retry', async () => {
  let fail = true
  const f = setup({ api: { getManualCaseVersions: async () => { if (fail) throw Error('Offline'); return { data: [] } } } })
  try {
    await f.open(subject())
    assert.equal(f.visible.value, true); assert.equal(f.loadError.value, true)
    assert.equal(f.historyLoading.value, false); assert.equal(f.activeHistory.value, null)
    fail = false; await f.loadHistory()
    assert.equal(f.loadError.value, false); assert.deepEqual([...f.historyVersions.value], [])
    assert.equal(f.historyLoading.value, false)
  } finally { f.close() }
})

test('switching records ignores old success and old finally while current request is pending', async () => {
  const first = deferred(), second = deferred(); const calls = []
  const f = setup({ api: { getManualCaseVersions: id => { calls.push(id); return id === 11 ? first.promise : second.promise } } })
  try {
    const old = f.open(subject(11)), fresh = f.open(subject(22))
    first.resolve({ data: [version(1)] }); await old; await flush()
    assert.equal(f.subject.value.id, 22); assert.equal(f.historyLoading.value, true)
    assert.deepEqual([...f.historyVersions.value], [])
    second.resolve({ data: [version(2, { case: 22 })] }); await fresh
    assert.equal(f.historyLoading.value, false); assert.equal(f.activeHistory.value.case, 22)
    assert.deepEqual(calls, [11, 22])
  } finally { f.close() }
})

test('old rejected request cannot mark a new history window failed', async () => {
  const first = deferred(), second = deferred(); let count = 0
  const f = setup({ api: { getManualCaseVersions: () => ++count === 1 ? first.promise : second.promise } })
  try {
    const old = f.open(subject()), fresh = f.open(subject(22))
    first.reject(Error('Late failure')); await old
    assert.equal(f.loadError.value, false); assert.equal(f.historyLoading.value, true)
    second.resolve({ data: [] }); await fresh
    assert.equal(f.historyLoading.value, false); assert.equal(f.loadError.value, false)
  } finally { f.close() }
})

for (const transition of ['close', 'context', 'deactivate', 'unmount']) {
  test(`${transition} clears history and suppresses a pending response`, async () => {
    const hooks = {}, pending = deferred()
    const f = setup({
      modules: { vue: { ...vue, onActivated: fn => { hooks.activate = fn }, onDeactivated: fn => { hooks.deactivate = fn }, onBeforeUnmount: fn => { hooks.unmount = fn } } },
      api: { getManualCaseVersions: () => pending.promise },
    })
    try {
      const reading = f.open(subject())
      if (transition === 'close') f.closeHistory()
      else if (transition === 'context') f.props.contextKey = 'new-environment'
      else hooks[transition]()
      pending.resolve({ data: [version(1)] }); await reading
      assert.equal(f.visible.value, false); assert.equal(f.subject.value, null)
      assert.equal(f.historyLoading.value, false); assert.equal(f.loadError.value, false)
      assert.deepEqual([...f.historyVersions.value], [])
      if (transition === 'deactivate') {
        await f.open(subject()); assert.equal(f.visible.value, false)
        hooks.activate(); await f.open(subject(22)); assert.equal(f.subject.value.id, 22)
      }
    } finally { f.close() }
  })
}
