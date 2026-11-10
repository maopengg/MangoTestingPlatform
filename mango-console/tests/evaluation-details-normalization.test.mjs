import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import * as vue from 'vue'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

function page(api = {}) {
  const route = vue.reactive({ path: '/evaluation/case/details', query: { id: '1' } })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 2 })
  const lifecycle = {},
    notices = []
  const state = harness(
    'index',
    'record,editor,loading,loadError,graderCatalog,catalogLoading,catalogError,loadCatalog,gradingPreview,previewLoading,executing,executionId,historyVisible,reload,preview,execute,configurationSaved,saveConfiguration',
    {
      base: path.resolve('src/views/evaluation/case/details'),
      api,
      modules: {
        vue: {
          ...vue,
          onBeforeUnmount: (fn) => (lifecycle.unmount = fn),
          onDeactivated: (fn) => (lifecycle.deactivate = fn),
          onActivated: (fn) => (lifecycle.activate = fn),
        },
        'vue-router': { useRoute: () => route, useRouter: () => ({ replace() {}, push() {} }) },
        '@/store/modules/user': { default: () => user },
        '@arco-design/web-vue': {
          Message: {
            success: (value) => notices.push(value),
            warning: (value) => notices.push(value),
          },
        },
        '../../components/useEvaluationEnums': {
          useEvaluationEnums: () => ({ title() {}, color() {} }),
        },
      },
    }
  )
  state.editor.value = {
    ready: true,
    saving: false,
    loading: false,
    flush: async () => true,
    scrollToStep() {},
  }
  return {
    ...state,
    route,
    user,
    lifecycle,
    notices,
    dispose() {
      lifecycle.unmount?.()
      state.close()
    },
  }
}
const record = (id) => ({ id, name: `Case ${id}`, status: 'enabled' })
const api = (extra) => ({
  getEvaluationCase: async (id) => ({ data: record(id) }),
  getCaseGraderCatalog: async () => ({ data: [] }),
  ...extra,
})

test('failed detail read clears loading and supports retry', async () => {
  let fail = true
  const s = page(
    api({
      getEvaluationCase: async (id) => {
        if (fail) throw Error('offline')
        return { data: record(id) }
      },
    })
  )
  try {
    await flush()
    assert.equal(s.loadError.value, true)
    assert.equal(s.loading.value, false)
    fail = false
    s.reload()
    await flush()
    assert.equal(s.record.value.id, 1)
    assert.equal(s.loadError.value, false)
  } finally {
    s.dispose()
  }
})
test('late detail cannot overwrite a different case', async () => {
  const pending = deferred()
  const s = page(
    api({
      getEvaluationCase: (id) =>
        id === 1 ? pending.promise : Promise.resolve({ data: record(id) }),
    })
  )
  try {
    s.route.query.id = '2'
    await flush()
    pending.resolve({ data: record(1) })
    await flush()
    assert.equal(s.record.value.id, 2)
  } finally {
    s.dispose()
  }
})
test('role change and cached reactivation reload detail, stale response stays discarded', async () => {
  const s = page(api())
  try {
    await flush()
    s.user.roleId = 2
    assert.equal(s.record.value, null)
    await flush()
    assert.equal(s.record.value.id, 1)
    s.lifecycle.deactivate()
    assert.equal(s.record.value, null)
    s.lifecycle.activate()
    await flush()
    assert.equal(s.record.value.id, 1)
  } finally {
    s.dispose()
  }
})
test('preview owns one physical request and a save invalidates stale preview', async () => {
  const pending = deferred()
  let calls = 0
  const s = page(
    api({
      getCaseGradingPreview: () => {
        calls++
        return pending.promise
      },
    })
  )
  try {
    await flush()
    const first = s.preview()
    await flush()
    assert.equal(await s.preview(), false)
    s.configurationSaved({ id: 1, config: {} })
    assert.equal(s.previewLoading.value, true)
    pending.resolve({ data: { items: [] } })
    assert.equal(await first, false)
    assert.equal(s.gradingPreview.value, undefined)
    assert.equal(calls, 1)
    assert.equal(s.previewLoading.value, false)
  } finally {
    s.dispose()
  }
})
test('switching environment away and back discards an in-flight preview', async () => {
  const pending = deferred(),
    s = page(api({ getCaseGradingPreview: () => pending.promise }))
  try {
    await flush()
    const first = s.preview()
    await flush()
    s.user.selected_environment = 3
    s.user.selected_environment = 2
    pending.resolve({ data: { items: [] } })
    assert.equal(await first, false)
    assert.equal(s.gradingPreview.value, undefined)
  } finally {
    s.dispose()
  }
})
test('execution retains idempotency key on failure, prevents duplicates, then selects result', async () => {
  const keys = [],
    pending = deferred()
  let fail = true
  const s = page(
    api({
      executeEvaluationCase: async (_id, _value, key) => {
        keys.push(key)
        if (fail) throw Error('offline')
        return pending.promise
      },
    })
  )
  try {
    await flush()
    assert.equal(await s.execute(), false)
    fail = false
    const task = s.execute()
    await flush()
    assert.equal(await s.execute(), false)
    pending.resolve({ data: { id: 8 } })
    assert.equal(await task, true)
    assert.equal(keys[0], keys[1])
    assert.equal(s.executionId.value, 8)
    assert.equal(s.executing.value, false)
  } finally {
    s.dispose()
  }
})
test('environment round trip suppresses execution success and releases physical lock', async () => {
  const pending = deferred(),
    s = page(api({ executeEvaluationCase: () => pending.promise }))
  try {
    await flush()
    const task = s.execute()
    await flush()
    s.user.selected_environment = 3
    s.user.selected_environment = 2
    pending.resolve({ data: { id: 8 } })
    assert.equal(await task, false)
    assert.equal(s.executionId.value, undefined)
    assert.equal(s.notices.length, 0)
    assert.equal(s.executing.value, false)
  } finally {
    s.dispose()
  }
})
test('missing editor prevents execution without silently treating configuration as saved', async () => {
  let calls = 0
  const s = page(
    api({
      executeEvaluationCase: async () => {
        calls++
        return { data: { id: 8 } }
      },
    })
  )
  try {
    await flush()
    s.editor.value = null
    assert.equal(await s.execute(), false)
    assert.equal(calls, 0)
    s.configurationSaved({})
    assert.equal(s.record.value.id, 1)
  } finally {
    s.dispose()
  }
})

test('slow catalogue does not block case details; failed catalogue retries without replacing the editor', async () => {
  const pending = deferred()
  let first = true
  const s = page(
    api({
      getCaseGraderCatalog: () =>
        first
          ? pending.promise
          : Promise.resolve({
              data: [{ grader_key: 'fixture', grader_version: 1, name: 'Example' }],
            }),
    })
  )
  try {
    await flush()
    assert.equal(s.record.value.id, 1)
    assert.equal(s.loading.value, false)
    assert.equal(s.catalogLoading.value, true)
    pending.reject(Error('offline'))
    await flush()
    assert.equal(s.catalogError.value, true)
    const editor = s.editor.value
    first = false
    assert.equal(await s.loadCatalog(), true)
    assert.equal(s.editor.value, editor)
    assert.equal(s.catalogError.value, false)
    assert.equal(s.graderCatalog.value.length, 1)
  } finally {
    s.dispose()
  }
})
test('an ambiguous execution failure keeps its idempotency key across cached navigation', async () => {
  const pending = deferred(),
    keys = []
  let fail = true
  const s = page(
    api({
      executeEvaluationCase: async (_id, _payload, key) => {
        keys.push(key)
        if (fail) return pending.promise
        return { data: { id: 10 } }
      },
    })
  )
  try {
    await flush()
    const task = s.execute()
    await flush()
    s.lifecycle.deactivate()
    pending.reject(Error('offline'))
    assert.equal(await task, false)
    s.lifecycle.activate()
    await flush()
    fail = false
    assert.equal(await s.execute(), true)
    assert.equal(keys[0], keys[1])
  } finally {
    s.dispose()
  }
})
