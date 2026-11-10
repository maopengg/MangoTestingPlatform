import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as Vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/case/details')
const record = (id = 1) => ({ id, title: 'Fixture case', case_no: 'FIX-1', priority: 0,
  precondition: null, test_point: 'Fixture scenario', test_data: null, remark: null, source_text: null,
  change_status: 0, automation_impact_status: 0, bindings: [] })

function fixture(options = {}) {
  const route = Vue.reactive({ path: '/functional-test/case/details', query: { id: '1', ...options.query } })
  const user = Vue.reactive({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 2 })
  const lifecycle = {}, calls = [], enumCalls = [], back = []
  const state = harness('index', 'detail,caseId,loading,loadError,enumLoading,enumError,loadDetail,loadEnums,start', {
    filename: path.join(base, 'index.vue'), base,
    api: { getManualCaseDetail: async id => { calls.push(id); return options.read ? options.read(id) : { data: record(id) } } },
    modules: {
      vue: { ...Vue, onMounted: fn => { lifecycle.mount = fn }, onBeforeUnmount: fn => { lifecycle.unmount = fn },
        onDeactivated: fn => { lifecycle.deactivate = fn }, onActivated: fn => { lifecycle.activate = fn } },
      'vue-router': { useRoute: () => route, useRouter: () => ({ back: () => back.push(true) }) },
      '@/store/modules/user': { default: () => user },
      '@/store/modules/get-enum': { useEnum: () => ({ colors: ['gray'], getEnum: async () => {
        enumCalls.push(true); if (options.enums) await options.enums()
      } }) },
    },
  })
  const { enumTitle, bindingCaseId } = state.load('presentation.ts')
  return { ...state, enumTitle, bindingCaseId, route, user, lifecycle, calls, enumCalls,
    dispose() { lifecycle.unmount(); state.close() } }
}

test('detail ID accepts positive integer query strings and rejects missing, repeated or lossy IDs', () => {
  const f = fixture()
  try {
    const { caseDetailId } = f.load('presentation.ts')
    assert.equal(caseDetailId('0042'), 42)
    for (const value of [undefined, null, '', '0', '-1', '1.2', ['1'], ['1', '2'], 'NaN', '9007199254740992'])
      assert.equal(caseDetailId(value), null)
  } finally { f.dispose() }
})

test('enum presentation preserves zero and matches numeric/string keys', () => {
  const f = fixture()
  try {
    assert.equal(f.enumTitle([], 0), '0')
    assert.equal(f.enumTitle([{ key: '0', title: 'Fixture zero' }], 0), 'Fixture zero')
    assert.equal(f.enumTitle([], null), '-')
    assert.equal(f.enumTitle([], 99), '99')
  } finally { f.dispose() }
})

test('bindings use serializer foreign-key fields and retain the stored automation ID fallback', () => {
  const f = fixture()
  try {
    assert.equal(f.bindingCaseId({ api_case: 10, ui_case: null, automation_case_id: 20 }), 10)
    assert.equal(f.bindingCaseId({ api_case: null, ui_case: 30, automation_case_id: 20 }), 30)
    assert.equal(f.bindingCaseId({ api_case: null, ui_case: null, automation_case_id: 20 }), 20)
  } finally { f.dispose() }
})

test('detail becomes readable before pending enums finish and initial activation does not duplicate requests', async () => {
  const wait = deferred(), f = fixture({ enums: () => wait.promise })
  try {
    f.lifecycle.mount(); f.lifecycle.activate(); await flush()
    assert.equal(f.detail.value.id, 1)
    assert.equal(f.loading.value, false)
    assert.equal(f.enumLoading.value, true)
    assert.deepEqual(f.calls, [1])
    wait.resolve(); await flush()
    assert.equal(f.enumLoading.value, false)
  } finally { f.dispose() }
})

test('enum failure is independent, recoverable and never refetches detail during enum-only retry', async () => {
  let fail = true
  const f = fixture({ enums: async () => { if (fail) throw Error('fixture failure') } })
  try {
    f.lifecycle.mount(); await flush()
    assert.equal(f.detail.value.id, 1)
    assert.equal(f.enumError.value, true)
    assert.equal(f.enumLoading.value, false)
    fail = false; assert.equal(await f.loadEnums(), true)
    assert.equal(f.enumError.value, false)
    assert.deepEqual(f.calls, [1])
  } finally { f.dispose() }
})

test('failed detail requests release loading, preserve readable data on retry and can recover', async () => {
  let fail = false
  const f = fixture({ read: async id => { if (fail) throw Error('fixture rejection'); return { data: record(id) } } })
  try {
    f.lifecycle.mount(); await flush(); fail = true
    assert.equal(await f.loadDetail(), false)
    assert.equal(f.loadError.value, true)
    assert.equal(f.loading.value, false)
    assert.equal(f.detail.value.id, 1)
    fail = false; assert.equal(await f.loadDetail(), true)
    assert.equal(f.loadError.value, false)
  } finally { f.dispose() }
})

test('latest detail wins and an older finally cannot end the active loading state', async () => {
  const waits = [deferred(), deferred()]; let index = 0
  const f = fixture({ read: () => waits[index++].promise })
  try {
    const first = f.loadDetail(), second = f.loadDetail()
    waits[0].resolve({ data: record(10) }); await first
    assert.equal(f.detail.value, null)
    assert.equal(f.loading.value, true)
    waits[1].resolve({ data: record(20) }); await second
    assert.equal(f.detail.value.id, 20)
    assert.equal(f.loading.value, false)
  } finally { f.dispose() }
})

for (const context of ['id', 'environment', 'identity', 'token', 'route', 'deactivate', 'unmount']) {
  test(`${context} changes clear the old record and ignore late detail and enum failures`, async () => {
    const detailWait = deferred(), enumWait = deferred(), freshDetail = deferred(), freshEnums = deferred()
    let reads = 0, enums = 0
    const f = fixture({ read: () => ++reads === 1 ? detailWait.promise : freshDetail.promise,
      enums: () => ++enums === 1 ? enumWait.promise : freshEnums.promise })
    try {
      f.detail.value = record(9)
      const detailRequest = f.loadDetail(), enumRequest = f.loadEnums()
      if (context === 'id') f.route.query.id = '2'
      if (context === 'environment') f.user.selected_environment++
      if (context === 'identity') f.user.roleId++
      if (context === 'token') f.user.token = 'new-fixture-token'
      if (context === 'route') f.route.path = '/functional-test/case/index'
      if (context === 'deactivate') f.lifecycle.deactivate()
      if (context === 'unmount') f.lifecycle.unmount()
      assert.equal(f.detail.value, null)
      detailWait.resolve({ data: record(99) }); enumWait.reject(Error('late fixture failure'))
      await Promise.all([detailRequest, enumRequest]); await flush()
      assert.equal(f.detail.value, null)
      assert.equal(f.loadError.value, false)
      assert.equal(f.enumError.value, false)
      if (['id', 'environment', 'identity', 'token'].includes(context)) {
        assert.equal(f.calls.length, 2)
        assert.equal(f.loading.value, true)
        assert.equal(f.enumLoading.value, true)
        freshDetail.resolve({ data: record(context === 'id' ? 2 : 1) }); freshEnums.resolve()
        await flush()
        assert.equal(f.detail.value.id, context === 'id' ? 2 : 1)
        assert.equal(f.loading.value, false)
        assert.equal(f.enumError.value, false)
      } else {
        assert.equal(f.detail.value, null)
        assert.equal(f.loadError.value, false)
        assert.equal(f.enumError.value, false)
        assert.equal(f.loading.value, false)
      }
    } finally { f.dispose() }
  })
}

test('KeepAlive activation reloads the current ID while stopped pages do not issue requests', async () => {
  const f = fixture()
  try {
    f.lifecycle.mount(); await flush()
    f.lifecycle.deactivate()
    f.route.query.id = '2'
    assert.equal(await f.loadDetail(), false)
    assert.deepEqual(f.calls, [1])
    f.lifecycle.activate(); await flush()
    assert.deepEqual(f.calls, [1, 2])
    assert.equal(f.detail.value.id, 2)
  } finally { f.dispose() }
})

test('invalid route IDs issue neither detail nor enum requests', async () => {
  const f = fixture({ query: { id: ['1', '2'] } })
  try {
    f.lifecycle.mount(); await flush()
    assert.equal(f.caseId.value, null)
    assert.deepEqual(f.calls, [])
    assert.deepEqual(f.enumCalls, [])
  } finally { f.dispose() }
})

test('functional case detail compiles its script, slots and token styles with real table configuration', async () => {
  const file = path.join(base, 'index.vue'), source = readFileSync(file, 'utf8')
  const { descriptor, errors } = parse(source, { filename: file })
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: file })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename: file, id: file,
    compilerOptions: { bindingMetadata: script.bindings, expressionPlugins: ['typescript'] } }).errors, [])
  for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({
    source: style.content, filename: file, id: file, scoped: style.scoped,
  })).errors, [])
  const f = fixture()
  try {
    const config = f.load('config.ts')
    assert.equal(config.BINDING_SCROLL_X, 620)
    assert.equal(config.bindingColumns.find(column => column.dataIndex === 'automation_case_name').tooltip, true)
    assert.equal(config.bindingColumns.find(column => column.dataIndex === 'automation_case_id').align, 'center')
  } finally { f.dispose() }
})
