import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import { reactive } from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/apitest/mock/details')
const lossless = {
  cloneLosslessJson: (v) => (v == null ? v : JSON.parse(JSON.stringify(v))),
  stringifyLosslessJson: (v, n) => JSON.stringify(v, null, n),
}
function page(api = {}, query = { id: '1' }) {
  const route = reactive({ path: '/apitest/mock/details', query }),
    replacements = []
  const state = harness(
    'index',
    'form,savedRecord,save,loading,saving,ready,loadFailed,loadDetail,requestPath,responseErrors,addRule,removeRule,moveRule,openDebug,debugPanelRef',
    {
      base,
      api,
      modules: {
        '@/utils/lossless-json': lossless,
        'vue-router': {
          useRoute: () => route,
          useRouter: () => ({
            replace: async (target) => {
              replacements.push(target)
              route.query = target.query
            },
            back() {},
          }),
        },
      },
    }
  )
  return { ...state, route, replacements }
}
const record = (id = 1) => ({
  id,
  project_product: { id: 2 },
  name: 'Mock',
  mock_key: 'sample',
  path: '/item',
  method: 0,
  enabled: true,
  record_call_log: false,
  description: '',
  config: {
    methods: [],
    assertions: [],
    rules: [],
    default_response: response(),
    request_decryption: { type: 'none', encrypt_key: '', verification_token: '' },
  },
})
const response = () => ({
  status_code: 200,
  content_type: 'application/json',
  headers: {},
  body_type: 'json',
  body: '{}',
  delay_ms: 0,
})
function editor(name, props, api = {}) {
  return harness(
    name,
    name === 'MockResponseEditor'
      ? 'response,headersText,headersError,onHeadersInput,updateField'
      : 'rows,updateField,updateOperator,addItem,removeItem',
    { base, props, api, modules: { '@/utils/lossless-json': lossless } }
  )
}
test('Mock page and all owned panels compile scripts and templates', () => {
  for (const name of [
    'index.vue',
    'components/MockConditionEditor.vue',
    'components/MockResponseEditor.vue',
    'components/MockDebugPanel.vue',
    '../components/MockCallLogsPanel.vue',
  ]) {
    const filename = path.join(base, name),
      { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: filename })
    assert.deepEqual(
      compileTemplate({
        id: filename,
        filename,
        source: descriptor.template.content,
        compilerOptions: { bindingMetadata: script.bindings },
      }).errors,
      []
    )
  }
})
test('draft factory and whitelist payload isolate nested data and preserve empty methods and secrets', async () => {
  const state = page()
  const { createMockDraft, mockPayload } = state.load('form.ts'),
    source = record()
  const draft = createMockDraft(source)
  draft.config.default_response.body = 'false'
  assert.equal(source.config.default_response.body, '{}')
  assert.deepEqual(draft.config.methods, [])
  draft.project_product = [1, 2]
  draft.config.request_decryption.encrypt_key = ' key '
  draft.config.request_decryption.configuration_error = 'diagnostic'
  draft.update_time = 'old'
  const payload = mockPayload(draft)
  draft.config.default_response.body = 'changed'
  assert.equal(payload.project_product, 2)
  assert.equal(payload.config.default_response.body, 'false')
  assert.equal(payload.config.request_decryption.encrypt_key, ' key ')
  assert.equal('configuration_error' in payload.config.request_decryption, false)
  assert.equal(payload.update_time, 'old')
  state.close()
})
test('latest route read wins; failure releases loading and allows retry', async () => {
  const old = deferred()
  let fail = true
  const state = page({
    getMockConfigDetail: (id) =>
      id === '1'
        ? old.promise
        : fail
        ? Promise.reject(Error('read'))
        : Promise.resolve({ data: record(2) }),
  })
  state.route.query.id = '2'
  await flush()
  assert.equal(state.loadFailed.value, true)
  assert.equal(state.loading.value, false)
  fail = false
  await state.loadDetail()
  old.resolve({ data: record(1) })
  await flush()
  assert.equal(state.form.id, 2)
  assert.equal(state.ready.value, true)
  state.close()
})
test('save freezes payload, blocks duplicates, keeps concurrent draft and ignores late completion after leaving', async () => {
  const pending = deferred(),
    requests = []
  const state = page({
    getMockConfigDetail: async (id) => ({ data: record(Number(id)) }),
    updateMockConfig: (payload) => {
      requests.push(payload)
      return pending.promise
    },
  })
  await flush()
  const saving = state.save()
  await state.save()
  assert.equal(requests.length, 1)
  state.form.config.default_response.body = 'changed while waiting'
  assert.equal(requests[0].config.default_response.body, '{}')
  state.route.query.id = '2'
  await flush()
  pending.resolve({ data: record(1) })
  await saving
  assert.equal(state.form.id, 2)
  assert.equal(state.saving.value, false)
  assert.equal(state.replacements.length, 0)
  state.close()
})
test('failed save preserves nested draft and retries; successful save does not reload over edits', async () => {
  let fail = true,
    calls = 0
  const state = page({
    getMockConfigDetail: async () => ({ data: record() }),
    updateMockConfig: async () => {
      calls++
      if (fail) throw Error('write')
      return { data: { id: 1 } }
    },
  })
  await flush()
  state.form.config.default_response.body = 'false'
  await state.save()
  assert.equal(state.form.config.default_response.body, 'false')
  assert.equal(state.saving.value, false)
  fail = false
  await state.save()
  assert.equal(calls, 2)
  assert.equal(state.savedRecord.value.config.default_response.body, 'false')
  state.close()
})
test('create adopts saved ID without resetting configuration or issuing a second create', async () => {
  let creates = 0,
    updates = 0
  const state = page(
    {
      createMockConfig: async () => {
        creates++
        return { data: { id: 42 } }
      },
      updateMockConfig: async () => {
        updates++
        return { data: { id: 42 } }
      },
    },
    {}
  )
  state.form.project_product = [1, 2]
  state.form.name = 'New'
  state.requestPath.value = '/new/{id}'
  state.form.config.default_response.body = '0'
  await state.save()
  await flush()
  assert.equal(state.form.id, 42)
  assert.equal(state.form.config.default_response.body, '0')
  await state.save()
  assert.equal(creates, 1)
  assert.equal(updates, 1)
  state.close()
})
test('saved first path segment and invalid header prevent writes; rule keys remain distinct', async () => {
  let writes = 0
  const state = page({
    getMockConfigDetail: async () => ({ data: record() }),
    updateMockConfig: async () => {
      writes++
      return { data: { id: 1 } }
    },
  })
  await flush()
  state.requestPath.value = '/other'
  await state.save()
  assert.equal(writes, 0)
  state.requestPath.value = '/sample'
  state.responseErrors.add('__default__')
  await state.save()
  assert.equal(writes, 0)
  state.addRule()
  state.addRule()
  assert.notEqual(state.form.config.rules[0].key, state.form.config.rules[1].key)
  state.removeRule(0)
  assert.equal(state.form.config.rules.length, 1)
  state.close()
})
test('response editor rejects nonobject/string header values and retains invalid text during unrelated prop updates', async () => {
  const source = response(),
    state = editor('MockResponseEditor', { modelValue: source })
  for (const text of ['null', '[]', '{"A":1}', 'invalid']) {
    state.onHeadersInput(text)
    assert.ok(state.headersError.value)
    assert.equal(
      state.events.some((e) => e[0] === 'update:modelValue'),
      false
    )
  }
  state.props.modelValue = { ...source, body: 'new' }
  await flush()
  assert.equal(state.headersText.value, 'invalid')
  state.onHeadersInput('{"X-Test":"yes"}')
  const payload = state.events.find((e) => e[0] === 'update:modelValue')[1]
  assert.deepEqual(payload.headers, { 'X-Test': 'yes' })
  assert.deepEqual(source.headers, {})
  state.updateField('delay_ms', 0)
  assert.equal(state.events.at(-1)[1].delay_ms, 0)
  state.close()
})
test('response editor respects disabled state', () => {
  const state = editor('MockResponseEditor', { modelValue: response(), disabled: true })
  state.onHeadersInput('[]')
  state.updateField('body', 'x')
  assert.equal(state.events.length, 0)
  state.close()
})
function debug(api = {}) {
  return harness(
    'MockDebugPanel',
    'open,close,runDebug,draft,visible,resultVisible,result,loading',
    { base, api, modules: { '@/utils/lossless-json': lossless } }
  )
}
test('debug validates objects, freezes request and prevents duplicate sends; closed results cannot reopen', async () => {
  const pending = deferred(),
    requests = [],
    state = debug({
      invokeMockEndpoint: (payload) => {
        requests.push(payload)
        return pending.promise
      },
    })
  state.open({ id: 1, requestPath: '/sample/{id}', methods: [] })
  state.draft.query = '[]'
  assert.equal(await state.runDebug(), false)
  assert.equal(requests.length, 0)
  state.draft.query = '{"a":1}'
  const task = state.runDebug()
  await state.runDebug()
  state.draft.query = '{}'
  assert.deepEqual(requests[0].query, { a: 1 })
  state.close()
  pending.resolve({ ok: true, status: 200, response_body: false })
  await task
  assert.equal(state.resultVisible.value, false)
  assert.equal(state.loading.value, false)
})
test('failed debug retains form for retry and successful response preserves falsy body', async () => {
  let fail = true
  const state = debug({
    invokeMockEndpoint: async () => {
      if (fail) throw Error('debug')
      return { ok: true, status: 200, response_body: 0 }
    },
  })
  state.open({ id: 1, requestPath: '/sample', methods: [0] })
  assert.equal(await state.runDebug(), false)
  assert.equal(state.visible.value, true)
  fail = false
  assert.equal(await state.runDebug(), true)
  assert.equal(state.result.value.response_body, 0)
  state.close()
})
test('condition editor isolates parent rows, expected objects, operator leaf and disabled actions', () => {
  const source = [
    {
      key: 'a',
      source: 'query',
      field: 'id',
      operator: 'equal',
      expected: { nested: true },
      enabled: true,
    },
  ]
  const state = editor('MockConditionEditor', {
    modelValue: source,
    mode: 'matcher',
    assertionMethods: [
      {
        value: 'group',
        label: 'group',
        children: [{ value: 'exists', label: 'exists', requires_expected: false }],
      },
    ],
  })
  state.updateField('a', 'name', 'changed')
  assert.equal(source[0].name, undefined)
  assert.deepEqual(state.events.at(-1)[1][0].expected, { nested: true })
  state.updateOperator('a', ['group', 'exists'])
  assert.equal(state.events.at(-1)[1][0].operator, 'exists')
  assert.equal(state.events.at(-1)[1][0].expected, '')
  state.addItem()
  state.addItem()
  assert.notEqual(state.rows.value[1].key, state.rows.value[2].key)
  state.props.disabled = true
  const length = state.events.length
  state.removeItem(0)
  state.addItem()
  assert.equal(state.events.length, length)
  state.close()
})
test('debug opens with saved methods/path instead of unsaved form', async () => {
  const state = page({ getMockConfigDetail: async () => ({ data: record() }) })
  await flush()
  const targets = []
  state.debugPanelRef.value = { open: (target) => targets.push(target), close() {} }
  state.requestPath.value = '/sample/unsaved'
  state.form.config.methods = [1]
  state.openDebug()
  assert.equal(targets[0].requestPath, '/sample/item')
  assert.deepEqual(targets[0].methods, [])
  state.close()
})

test('cached detail ignores query IDs from other routes and retains its draft', async () => {
  const reads = []
  const state = page({
    getMockConfigDetail: async (id) => {
      reads.push(id)
      return { data: record() }
    },
  })
  await flush()
  state.form.name = 'Unsaved draft'
  state.route.path = '/apitest/headers/index'
  state.route.query = { id: '9' }
  await flush()
  assert.deepEqual(reads, ['1'])
  assert.equal(state.form.name, 'Unsaved draft')
  state.close()
})

test('update retains optimistic concurrency token and adopts server version for the next save', async () => {
  const payloads = []
  const state = page({
    getMockConfigDetail: async () => ({
      data: { ...record(), update_time: '2026-11-06 10:00:00' },
    }),
    updateMockConfig: async (payload) => {
      payloads.push(payload)
      return { data: { id: 1, update_time: '2026-11-06 10:00:01' } }
    },
  })
  await flush()
  await state.save()
  await state.save()
  assert.equal(payloads[0].update_time, '2026-11-06 10:00:00')
  assert.equal(payloads[1].update_time, '2026-11-06 10:00:01')
  state.close()
})
