import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/perf/scenario/details')
function setup() {
  const warnings = [], errors = []
  const h = harness('LoadConfigurationDialog', 'draft,visible,confirming,formRef,confirm,selectLoadProfile,editedDuration', {
    base, props: { contextKey: 'scenario-1', executorCount: 1 },
    modules: { '@arco-design/web-vue': { Message: {
      warning: value => warnings.push(value), error: value => errors.push(value),
    } } },
  })
  h.formRef.value = { validate: async () => undefined, clearValidate() {} }
  return { ...h, warnings, errors, config: h.load('config.ts'), load: h.load('load-configuration.ts'), dispose: h.close }
}

function dialog() {
  const h = setup()
  return { ...h, cancel: h.exposed.close, openDialog: h.exposed.open }
}

test('open owns a detached whitelist draft; cancel and reopen restore the supplied configuration', async () => {
  const h = dialog()
  const original = { ...h.config.createDefaultLoadConfiguration(), name: 'Example load', audit: 'ignored', hold_seconds: 0 }
  await h.openDialog(original, 'concurrency')
  h.draft.name = 'Unsaved'
  h.draft.target_users = 30
  assert.equal(original.name, 'Example load')
  assert.equal('audit' in h.draft, false)
  h.cancel()
  assert.equal(h.visible.value, false)
  assert.deepEqual(h.events, [])
  await h.openDialog(original, 'concurrency')
  assert.equal(h.draft.name, 'Example load')
  assert.equal(h.draft.target_users, 10)
  assert.equal(h.draft.hold_seconds, 0)
  h.dispose()
})

test('all eight profiles retain their load-type and duration rules when committed by actual dialog', async () => {
  const h = dialog()
  for (const [profile, type, seconds] of [
    ['constant_concurrency', 'concurrency', 60], ['fixed_iterations', 'concurrency', 60],
    ['staircase', 'concurrency', 60], ['linear_ramp', 'concurrency', 60],
    ['spike', 'concurrency', 120], ['soak', 'concurrency', 60],
    ['constant_arrival_rate', 'arrival_rate', 60], ['constant_iteration_rate', 'iteration_rate', 60],
  ]) {
    await h.openDialog(undefined, 'concurrency')
    h.selectLoadProfile(profile)
    assert.equal(await h.confirm(), true, profile)
    assert.equal(h.visible.value, false)
    const [, change] = h.events.at(-1)
    assert.equal(change.loadType, type)
    assert.equal(change.configuration.duration_seconds, seconds)
    assert.equal(change.configuration.profile, profile)
    assert.equal(change.configuration.target_users, type === 'concurrency' ? 10 : null)
    if (type === 'concurrency') {
      assert.equal(change.configuration.target_rate, null)
      assert.equal(change.configuration.rate_time_unit, null)
      assert.equal(change.configuration.preallocated_vus, null)
      assert.equal(change.configuration.max_vus, null)
    }
  }
  h.dispose()
})

test('changing profiles preserves name and wait range but resets profile-specific defaults', async () => {
  const h = dialog()
  await h.openDialog(undefined, 'arrival_rate')
  Object.assign(h.draft, { name: 'Example', user_wait_min_ms: 0, user_wait_max_ms: 300, target_rate: 15 })
  h.selectLoadProfile('linear_ramp')
  assert.equal(h.draft.name, 'Example')
  assert.equal(h.draft.target_rate, undefined)
  assert.equal(h.draft.user_wait_max_ms, 300)
  assert.equal(h.draft.user_wait_min_ms, 0)
  h.selectLoadProfile('invalid')
  assert.equal(h.draft.profile, 'linear_ramp')
  h.dispose()
})

test('null optional stage fields receive editor defaults while valid zero start and hold are preserved', async () => {
  const h = dialog()
  await h.openDialog({ ...h.config.createDefaultLoadConfiguration(), profile: 'linear_ramp', start_users: 0, hold_seconds: 0, ramp_seconds: null }, 'concurrency')
  assert.equal(h.draft.start_users, 0)
  assert.equal(h.draft.hold_seconds, 0)
  assert.equal(h.draft.ramp_seconds, 30)
  assert.equal(await h.confirm(), true)
  assert.equal(h.events[0][1].configuration.duration_seconds, 30)
  h.dispose()
})

test('API reader keeps null and decimal values but rejects booleans, blank numbers and invalid enums', () => {
  const h = dialog()
  const read = h.load.readLoadConfiguration
  const value = read({ name: 'Example', target_users: null, target_rate: '0.5', spawn_rate: 0, user_wait_min_ms: 0 })
  assert.equal(value.target_users, null); assert.equal(value.target_rate, 0.5); assert.equal(value.spawn_rate, 0)
  assert.equal(read(null).duration_seconds, 0)
  for (const value of [[], false, '', { target_users: false }, { target_users: '' }, { duration_seconds: NaN }, { profile: 'invalid' }, { rate_time_unit: 'day' }, { ramp_type: 'invalid' }])
    assert.throws(() => read(value))
  h.dispose()
})

test('cleared required numeric fields and non-finite/fractional duration do not commit', async () => {
  const h = dialog()
  for (const [key, value] of [
    ['duration_seconds', null], ['duration_seconds', undefined], ['duration_seconds', NaN], ['duration_seconds', 1.5],
    ['target_users', null], ['target_users', undefined], ['target_users', 0], ['user_wait_min_ms', null], ['user_wait_min_ms', undefined],
    ['user_wait_max_ms', 3600001], ['user_wait_max_ms', -1], ['name', '  '], ['name', 'x'.repeat(65)],
  ]) {
    await h.openDialog(undefined, 'concurrency')
    h.draft[key] = value
    assert.equal(await h.confirm(), false, `${key}: ${value}`)
    assert.equal(h.visible.value, true)
    assert.equal(h.confirming.value, false)
  }
  assert.deepEqual(h.events, [])
  h.dispose()
})

test('existing load constraints cover executor count, iterations, staircase, ramp, spike and wait order', () => {
  const h = dialog(), commit = h.load.commitLoadDraft, defaults = () => h.config.createDefaultLoadConfiguration()
  for (const [patch, count] of [
    [{ target_users: 1 }, 2], [{ profile: 'fixed_iterations', total_iterations: 9 }, 1],
    [{ profile: 'staircase', step_users: 1, target_users: 100 }, 1],
    [{ profile: 'staircase', step_users: 1 }, 2],
    [{ profile: 'linear_ramp', start_users: 10 }, 1],
    [{ profile: 'spike', start_users: 1 }, 2], [{ profile: 'spike', hold_seconds: 0 }, 1],
    [{ user_wait_min_ms: 50, user_wait_max_ms: 40 }, 1], [{ duration_seconds: 86401 }, 1],
  ]) assert.throws(() => commit({ ...defaults(), ...patch }, count))
  assert.equal(commit({ ...defaults(), duration_seconds: 86400 }, 1).configuration.duration_seconds, 86400)
  h.dispose()
})

test('rate profiles preserve sub-unit rates and require per-minute integral load plus sufficient VU capacity', () => {
  const h = dialog(), defaults = h.config.createDefaultLoadConfiguration('arrival_rate'), commit = h.load.commitLoadDraft
  assert.equal(commit({ ...defaults, target_rate: 0.5 }, 1).configuration.target_rate, 0.5)
  assert.equal(commit({ ...defaults, target_rate: 4.15 }, 1).configuration.target_rate, 4.15)
  assert.equal(commit({ ...defaults, target_rate: 1, rate_time_unit: 'minute' }, 1).configuration.target_rate, 1)
  for (const patch of [{ target_rate: 0 }, { target_rate: 10000001 }, { target_rate: 0.001 }, { preallocated_vus: null }, { preallocated_vus: 5, max_vus: 4 }])
    assert.throws(() => commit({ ...defaults, ...patch }, 1))
  assert.throws(() => commit({ ...defaults, preallocated_vus: 1 }, 2))
  assert.throws(() => commit({ ...defaults, target_rate: 1, rate_time_unit: 'minute' }, 2))
  assert.throws(() => commit({ ...defaults, target_rate: 1.00000000001, rate_time_unit: 'minute' }, 1))
  h.dispose()
})

test('form validation failure or rejection retains draft and allows retry', async () => {
  const h = dialog()
  await h.openDialog(undefined, 'concurrency')
  h.formRef.value.validate = async () => ({ name: 'invalid' })
  assert.equal(await h.confirm(), false)
  h.formRef.value.validate = async () => { throw new Error('fixture') }
  assert.equal(await h.confirm(), false)
  assert.equal(h.errors.length, 1)
  assert.equal(h.visible.value, true)
  assert.equal(h.confirming.value, false)
  h.formRef.value.validate = async () => undefined
  assert.equal(await h.confirm(), true)
  assert.equal(h.events.length, 1)
  h.dispose()
})

test('cancel and reopen during validation ignore late completion and retain physical validation lock', async () => {
  const h = dialog(), pending = deferred()
  await h.openDialog(undefined, 'concurrency')
  h.formRef.value.validate = () => pending.promise
  const first = h.confirm()
  h.cancel()
  await h.openDialog({ ...h.config.createDefaultLoadConfiguration(), name: 'New draft' }, 'concurrency')
  assert.equal(h.confirming.value, true)
  assert.equal(await h.confirm(), false)
  pending.resolve(undefined)
  assert.equal(await first, false)
  assert.deepEqual(h.events, [])
  assert.equal(h.visible.value, true)
  assert.equal(h.draft.name, 'New draft')
  h.dispose()
})

test('context A-B-A and executor-count changes invalidate pending confirmation synchronously', async () => {
  const h = dialog(), pending = deferred()
  await h.openDialog(undefined, 'concurrency')
  h.formRef.value.validate = () => pending.promise
  const first = h.confirm()
  h.props.contextKey = 'scenario-2'
  assert.equal(h.visible.value, false)
  h.props.contextKey = 'scenario-1'
  await h.openDialog(undefined, 'concurrency')
  pending.resolve(undefined)
  assert.equal(await first, false)
  assert.deepEqual(h.events, [])
  h.props.executorCount = 2
  assert.equal(h.visible.value, false)
  h.dispose()
})

test('invalid input cannot open a dialog and unmount/deactivation discards a pending confirmation', async () => {
  const h = dialog(), pending = deferred()
  assert.equal(await h.openDialog({ duration_seconds: false }, 'concurrency'), false)
  assert.equal(h.visible.value, false)
  await h.openDialog(undefined, 'concurrency')
  h.formRef.value.validate = () => pending.promise
  const first = h.confirm()
  h.dispose()
  pending.resolve(undefined)
  assert.equal(await first, false)
  assert.deepEqual(h.events, [])
  await flush()
})

test('parent synchronous identity callback invalidates confirmation before child props rerender', async () => {
  const h = dialog(), pending = deferred()
  let version = 0
  h.props.contextVersion = 0
  h.props.isContextCurrent = captured => captured === version
  await h.openDialog(undefined, 'concurrency')
  h.formRef.value.validate = () => pending.promise
  const confirm = h.confirm()
  version++
  assert.equal(h.props.contextVersion, 0)
  pending.resolve(undefined)
  assert.equal(await confirm, false)
  assert.deepEqual(h.events, [])
  assert.equal(await h.openDialog(undefined, 'concurrency'), false)
  h.dispose()
})

test('actual parent coordinates only load configuration and preserves unrelated scenario state', async () => {
  const h = harness('index', 'form,loadConfig,loadDialogRef,openLoadConfig,commitLoadConfig', {
    base,
    modules: {
      'vue-router': { useRoute: () => ({ path: '/perf/scenario/details', query: { id: '1' } }), useRouter: () => ({}) },
      '@/store/modules/user': { default: () => ({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 0 }) },
    },
  })
  Object.assign(h.form, { load_type: 'concurrency', name: 'Example scenario', source_case_release_id: 7 })
  const opened = []
  h.loadDialogRef.value = { open: async (...args) => opened.push(args), close() {} }
  await h.openLoadConfig()
  assert.deepEqual(opened[0], [undefined, 'concurrency'])
  const config = h.load('config.ts'), load = h.load('load-configuration.ts')
  const change = load.commitLoadDraft(config.createDefaultLoadConfiguration('arrival_rate'), 1)
  h.commitLoadConfig(change)
  assert.equal(h.form.load_type, 'arrival_rate')
  assert.equal(h.loadConfig.target_users, null)
  assert.equal(h.loadConfig.target_rate, 10)
  assert.equal(h.form.name, 'Example scenario')
  assert.equal(h.form.source_case_release_id, 7)
  await h.openLoadConfig()
  assert.equal(opened[1][0], h.loadConfig)
  assert.equal(opened[1][1], 'arrival_rate')
  h.close()
})

test('load configuration and main SFCs compile; pure load boundary passes strict TypeScript', () => {
  for (const relative of ['index.vue', 'components/LoadConfigurationDialog.vue']) {
    const filename = path.join(base, relative)
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: relative })
    const template = compileTemplate({ source: descriptor.template.content, filename, id: relative, compilerOptions: { bindingMetadata: script.bindings } })
    assert.deepEqual(template.errors, [])
  }
  const program = ts.createProgram(['types.ts', 'config.ts', 'load-configuration.ts', 'performance-goal.ts'].map(name => path.join(base, name)), {
    noEmit: true, strict: true, target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext,
    moduleResolution: ts.ModuleResolutionKind.NodeJs, types: [], skipLibCheck: true,
  })
  const diagnostics = ts.getPreEmitDiagnostics(program)
  assert.equal(diagnostics.length, 0, ts.formatDiagnosticsWithColorAndContext(diagnostics, {
    getCanonicalFileName: value => value, getCurrentDirectory: () => process.cwd(), getNewLine: () => '\n',
  }))
})
