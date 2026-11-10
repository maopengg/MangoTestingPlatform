import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/perf/scenario/details')
globalThis.document = Object.assign(new EventTarget(), { visibilityState: 'visible' })
const envelope = data => ({ code: 200, data })
const candidate = fingerprint => ({ fingerprint, executor_name: fingerprint, available: 10, calibrated: false, ignored: true })
const capacity = (ids = [], patch = {}) => envelope({
  can_run: ids.length === 1, capacity_type: 'vu', required_per_node: 5, requested_node_count: 1,
  candidates: [candidate('node-a'), candidate('node-b')], selected: ids.map(candidate), ...patch,
})
function setup(overrides = {}) {
  let externalVersion = 0
  const cleanup = overrides.cleanup || []
  const warnings = [], errors = [], requests = [], executes = [], saves = []
  const h = harness('ScenarioExecuteDialog', 'draft,visible,submitting,executorLoading,preflightError,formRef,preflight,executorCandidates,executorSelectionReady,confirm,refreshPreflight', {
    base,
    props: {
      scenarioId: '1', contextVersion: 0, executorCount: 1,
      isContextCurrent: version => version === externalVersion && document.visibilityState !== 'hidden',
      saveConfiguration: async isCurrent => { saves.push(isCurrent); return true },
      ...overrides.props,
    },
    modules: {
      vue: { ...vue, onMounted: fn => fn(), onDeactivated: fn => cleanup.push(fn), onBeforeUnmount: fn => cleanup.push(fn) },
      '@arco-design/web-vue': { Message: { warning: value => warnings.push(value), error: value => errors.push(value) } },
      '@/api/perf': {
        preflightPerfScenario: async (id, payload) => { requests.push({ id, payload }); return overrides.preflight ? overrides.preflight(id, payload) : capacity(payload.selected_executor_fingerprints) },
        executePerfScenario: async (id, payload) => { executes.push({ id, payload }); return overrides.execute ? overrides.execute(id, payload) : envelope({ run_id: 12 }) },
      },
    },
  })
  h.formRef.value = { validate: async () => undefined, clearValidate() {} }
  return {
    ...h, warnings, errors, requests, executes, saves, boundary: h.load('execution.ts'),
    open: h.exposed.open, cancel: h.exposed.close,
    expire: () => externalVersion++,
    close: () => { cleanup.forEach(fn => fn()); h.close() },
  }
}
async function ready(h, env = 0) {
  await h.open()
  h.draft.test_env = env
  await flush()
  h.draft.selected_executor_fingerprints = ['node-a']
  await flush()
  assert.equal(h.executorSelectionReady.value, true)
}
const executed = h => h.events.filter(item => item[0] === 'executed')

test('new execution draft resets on every open and environment zero is a real selection', async () => {
  const h = setup()
  await ready(h)
  assert.equal(h.requests[0].payload.test_env, 0)
  Object.assign(h.draft, { remark: 'unsaved', capture_request: true, capture_response: true, production_load_confirmed: true })
  h.cancel(); await h.open()
  assert.equal(h.draft.test_env, undefined)
  assert.deepEqual(h.draft.selected_executor_fingerprints, [])
  assert.equal(h.draft.remark, '')
  assert.equal(h.draft.production_load_confirmed, false)
  assert.equal(h.draft.capture_request, false)
  assert.equal(h.preflight.value, null)
  h.close()
})

test('environment A-B-A ignores old successes, failures and finalizers', async () => {
  const requests = []
  const h = setup({ preflight: () => { const pending = deferred(); requests.push(pending); return pending.promise } })
  await h.open()
  h.draft.test_env = 0; h.draft.test_env = 1; h.draft.test_env = 0
  assert.equal(requests.length, 3)
  requests[0].resolve(capacity([], { required_per_node: 99 }))
  requests[1].reject(new Error('stale failure'))
  await flush()
  assert.equal(h.executorLoading.value, true)
  assert.equal(h.preflight.value, null)
  assert.equal(h.preflightError.value, false)
  requests[2].resolve(capacity([], { required_per_node: 3 }))
  await flush()
  assert.equal(h.executorLoading.value, false)
  assert.equal(h.preflight.value.required_per_node, 3)
  h.close()
})

test('executor selection A-B-A uses only latest capacity and captures request arrays', async () => {
  const pending = []
  const h = setup({ preflight: (_id, payload) => {
    if (!payload.selected_executor_fingerprints.length) return capacity()
    const item = deferred(); pending.push(item); return item.promise
  } })
  await h.open(); h.draft.test_env = 0; await flush()
  h.draft.selected_executor_fingerprints = ['node-a']
  h.draft.selected_executor_fingerprints = ['node-b']
  h.draft.selected_executor_fingerprints = ['node-a']
  pending[0].resolve(capacity(['node-a']))
  pending[1].resolve(capacity(['node-b']))
  await flush()
  assert.equal(h.executorSelectionReady.value, false)
  assert.equal(h.executorLoading.value, true)
  assert.deepEqual(h.requests[1].payload.selected_executor_fingerprints, ['node-a'])
  pending[2].resolve(capacity(['node-a']))
  await flush()
  assert.equal(h.executorSelectionReady.value, true)
  h.close()
})

test('production confirmation is required to be true and is cleared on environment changes', async () => {
  const h = setup()
  await ready(h, 2)
  assert.equal(await h.confirm(), false)
  assert.equal(h.executes.length, 0)
  assert.match(h.warnings.at(-1), /生产环境/)
  h.draft.production_load_confirmed = true
  h.draft.test_env = 0
  assert.equal(h.draft.production_load_confirmed, false)
  h.draft.test_env = 2
  await flush()
  assert.deepEqual(h.draft.selected_executor_fingerprints, [])
  assert.equal(h.draft.production_load_confirmed, false)
  h.close()
})

test('confirmation preserves save→fresh preflight→execute order and exact payload flags', async () => {
  const order = []
  const h = setup({ props: { saveConfiguration: async () => { order.push('save'); return true } },
    preflight: (_id, payload) => { order.push('preflight'); return capacity(payload.selected_executor_fingerprints) },
    execute: () => { order.push('execute'); return envelope({ run_id: '12' }) },
  })
  await ready(h, 2)
  Object.assign(h.draft, { production_load_confirmed: true, capture_request: true, capture_response: false, remark: 'Example run' })
  order.length = 0
  assert.equal(await h.confirm(), true)
  assert.deepEqual(order, ['save', 'preflight', 'execute'])
  assert.deepEqual(h.executes[0], { id: '1', payload: {
    test_env: 2, selected_executor_fingerprints: ['node-a'], remark: 'Example run',
    production_load_confirmed: true, capture_request: true, capture_response: false,
  } })
  assert.deepEqual(executed(h), [['executed', 12, 0]])
  assert.equal(h.visible.value, false)
  h.close()
})

test('physical submit lock starts before asynchronous validation and survives cancel/reopen', async () => {
  const h = setup(), validation = deferred()
  await ready(h)
  h.formRef.value.validate = () => validation.promise
  const first = h.confirm()
  assert.equal(h.submitting.value, true)
  assert.equal(await h.confirm(), false)
  h.cancel(); await h.open()
  assert.equal(h.submitting.value, true)
  assert.equal(await h.confirm(), false)
  validation.resolve(undefined)
  assert.equal(await first, false)
  assert.equal(h.submitting.value, false)
  assert.equal(h.visible.value, true)
  assert.equal(h.saves.length, 0)
  assert.deepEqual(executed(h), [])
  h.close()
})

test('cancel or an expired parent scope during save cannot start an execution', async () => {
  for (const action of ['cancel', 'expire']) {
    const save = deferred()
    const h = setup({ props: { saveConfiguration: () => save.promise } })
    await ready(h)
    const first = h.confirm(); await flush()
    h[action]()
    save.resolve(true)
    assert.equal(await first, false)
    assert.equal(h.executes.length, 0)
    assert.deepEqual(executed(h), [])
    h.close()
  }
})

test('draft A-B-A during save invalidates the operation even if values return to the original', async () => {
  const save = deferred(), h = setup({ props: { saveConfiguration: () => save.promise } })
  await ready(h)
  const first = h.confirm(); await flush()
  h.draft.remark = 'changed'; h.draft.remark = ''
  save.resolve(true)
  assert.equal(await first, false)
  assert.equal(h.executes.length, 0)
  h.close()
})

test('a capacity change after saving prevents execution and keeps the dialog open for another choice', async () => {
  let requests = 0
  const h = setup({ preflight: (_id, payload) => {
    requests++
    return capacity(payload.selected_executor_fingerprints, requests === 3 ? { can_run: false } : {})
  } })
  await ready(h)
  assert.equal(await h.confirm(), false)
  assert.equal(h.executes.length, 0)
  assert.equal(h.visible.value, true)
  assert.equal(h.submitting.value, false)
  assert.match(h.warnings.at(-1), /容量已变化/)
  h.close()
})

test('preflight failure and malformed success remain retryable without readiness', async () => {
  let fixture = { code: 400, data: capacity().data }
  const h = setup({ preflight: () => fixture })
  await h.open(); h.draft.test_env = 0; await flush()
  assert.equal(h.preflightError.value, true)
  assert.equal(h.executorLoading.value, false)
  assert.equal(h.executorSelectionReady.value, false)
  fixture = capacity()
  assert.equal(await h.refreshPreflight(), true)
  assert.equal(h.preflightError.value, false)
  h.close()
})

test('execution rejection or malformed run ID unlocks the dialog and permits an explicit retry', async () => {
  let attempt = 0
  const h = setup({ execute: () => {
    attempt++
    if (attempt === 1) throw new Error('fixture')
    return envelope({ run_id: attempt === 2 ? null : 20 })
  } })
  await ready(h)
  assert.equal(await h.confirm(), false)
  assert.equal(h.visible.value, true)
  assert.equal(h.submitting.value, false)
  assert.equal(await h.confirm(), false)
  assert.deepEqual(executed(h), [])
  assert.equal(h.visible.value, true)
  assert.equal(h.submitting.value, false)
  assert.equal(await h.confirm(), true)
  assert.deepEqual(executed(h), [['executed', 20, 0]])
  h.close()
})

test('failed configuration save and failed fresh capacity read stop before execution and allow retry', async () => {
  let saved = false, calls = 0
  const h = setup({
    props: { saveConfiguration: async () => saved },
    preflight: (_id, payload) => {
      calls++
      return calls === 3 ? { code: 400, data: capacity().data } : capacity(payload.selected_executor_fingerprints)
    },
  })
  await ready(h)
  assert.equal(await h.confirm(), false)
  assert.equal(calls, 2)
  assert.equal(h.executes.length, 0)
  saved = true
  assert.equal(await h.confirm(), false)
  assert.equal(h.executes.length, 0)
  assert.equal(h.submitting.value, false)
  assert.equal(h.preflightError.value, true)
  assert.equal(await h.refreshPreflight(), true)
  assert.equal(await h.confirm(), true)
  h.close()
})

test('late execution response after cancel cannot close a new dialog or emit navigation', async () => {
  const pending = deferred(), h = setup({ execute: () => pending.promise })
  await ready(h)
  const first = h.confirm(); await flush()
  assert.equal(h.executes.length, 1)
  h.cancel(); await h.open()
  assert.equal(h.submitting.value, true)
  pending.resolve(envelope({ run_id: 30 }))
  assert.equal(await first, false)
  assert.equal(h.visible.value, true)
  assert.equal(h.submitting.value, false)
  assert.deepEqual(executed(h), [])
  h.close()
})

test('scope A-B-A, background pause and lifecycle cleanup invalidate read/submit responses', async () => {
  const cleanup = [], pending = deferred(), h = setup({ cleanup, preflight: () => pending.promise })
  await h.open(); h.draft.test_env = 0
  h.props.contextVersion = 1; h.props.contextVersion = 0
  assert.equal(h.visible.value, false)
  await h.open()
  document.visibilityState = 'hidden'; document.dispatchEvent(new Event('visibilitychange'))
  assert.equal(h.visible.value, false)
  document.visibilityState = 'visible'
  await h.open()
  cleanup.forEach(fn => fn())
  pending.resolve(capacity())
  await flush()
  assert.equal(h.preflight.value, null)
  assert.equal(h.visible.value, false)
  h.close()
})

test('finite preflight/run parsers whitelist rows and reject forged readiness, duplicates and bad values', () => {
  const h = setup(), source = capacity(['node-a'])
  const parsed = h.boundary.readExecutorPreflight(source)
  source.data.candidates[0].available = 999
  assert.equal(parsed.candidates[0].available, 10)
  assert.equal('ignored' in parsed.candidates[0], false)
  for (const fixture of [capacity([], { can_run: 'true' }), capacity([], { candidates: [candidate('node-a'), candidate('node-a')] }), capacity([], { required_per_node: null }), capacity([], { capacity_type: 'invalid' }), capacity([], { requested_node_count: 0 })])
    assert.throws(() => h.boundary.readExecutorPreflight(fixture))
  for (const value of [null, false, 0, '', 1.5, Number.MAX_SAFE_INTEGER + 1])
    assert.throws(() => h.boundary.readExecutionRunId(envelope({ run_id: value })))
  const draft = { test_env: 0, selected_executor_fingerprints: ['node-b'] }
  assert.equal(h.boundary.executionSelectionReady(draft, parsed, 1), false)
  h.close()
})

test('parent context version invalidates user/role/token/environment/route A-B-A before child props render', () => {
  const route = vue.reactive({ path: '/perf/scenario/details', query: { id: '1' } })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-a', selected_environment: 0 })
  const h = harness('index', 'executionContextVersion,isExecutionContextCurrent', {
    base, modules: {
      'vue-router': { useRoute: () => route, useRouter: () => ({}) },
      '@/store/modules/user': { default: () => user },
    },
  })
  assert.equal(h.isExecutionContextCurrent(0), true)
  for (const key of ['userId', 'roleId', 'token', 'selected_environment']) {
    const version = h.executionContextVersion.value, before = user[key]
    user[key] = typeof before === 'string' ? 'fixture-b' : before + 1
    user[key] = before
    assert.equal(h.isExecutionContextCurrent(version), false)
  }
  const version = h.executionContextVersion.value
  route.query.id = '2'; route.query.id = '1'
  assert.equal(h.isExecutionContextCurrent(version), false)
  h.close()
})

test('new execute and main SFCs compile; execution boundary passes strict TypeScript', () => {
  for (const relative of ['index.vue', 'components/ScenarioExecuteDialog.vue']) {
    const filename = path.join(base, relative), { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: relative })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: relative, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  }
  const program = ts.createProgram(['types.ts', 'config.ts', 'execution.ts'].map(file => path.join(base, file)), {
    noEmit: true, strict: true, target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext,
    moduleResolution: ts.ModuleResolutionKind.NodeJs, types: [], skipLibCheck: true,
  })
  const diagnostics = ts.getPreEmitDiagnostics(program)
  assert.equal(diagnostics.length, 0, ts.formatDiagnosticsWithColorAndContext(diagnostics, {
    getCanonicalFileName: value => value, getCurrentDirectory: () => process.cwd(), getNewLine: () => '\n',
  }))
})
