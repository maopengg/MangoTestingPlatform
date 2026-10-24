import assert from 'node:assert/strict'
import test from 'node:test'

class MemoryStorage {
  values = new Map()
  getItem(key) { return this.values.get(key) ?? null }
  setItem(key, value) { this.values.set(key, String(value)) }
  removeItem(key) { this.values.delete(key) }
}

global.window = { sessionStorage: new MemoryStorage() }

const observer = await import('../../src/utils/executor-task-observer.mjs')

test('stores and restores a task observation after page refresh', () => {
  assert.equal(observer.saveExecutorTaskObservation('element-check', 12, {
    taskId: 81,
    businessType: 'u_element_check',
    meta: { mode: 'deep' },
  }), true)
  assert.deepEqual(observer.loadExecutorTaskObservation('element-check', 12).meta, {
    mode: 'deep',
  })
})

test('an old terminal task cannot clear a newer observation', () => {
  observer.saveExecutorTaskObservation('case-run', 3, { taskId: 91 })
  observer.clearExecutorTaskObservation('case-run', 3, 90)
  assert.equal(observer.loadExecutorTaskObservation('case-run', 3).taskId, '91')
  observer.clearExecutorTaskObservation('case-run', 3, 91)
  assert.equal(observer.loadExecutorTaskObservation('case-run', 3), null)
})

test('expired observations are removed instead of polling a deleted task forever', () => {
  observer.saveExecutorTaskObservation('element-check', 12, { taskId: 101 })
  const key = 'mango:executor-task:element-check:12'
  const stored = JSON.parse(window.sessionStorage.getItem(key))
  stored.savedAt = Date.now() - 25 * 60 * 60 * 1000
  window.sessionStorage.setItem(key, JSON.stringify(stored))
  assert.equal(observer.loadExecutorTaskObservation('element-check', 12), null)
  assert.equal(window.sessionStorage.getItem(key), null)
})
