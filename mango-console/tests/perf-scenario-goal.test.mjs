import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { deferred, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/perf/scenario/details')
function setup(api = {}) {
  const warnings = []
  const h = harness('index', 'form,sourceCase,loadConfig,performanceGoal,validateLocal,save,saving', {
    base,
    modules: {
      'vue-router': { useRoute: () => ({ path: '/perf/scenario/details', query: { id: '1' } }), useRouter: () => ({}) },
      '@/store/modules/user': { default: () => ({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 0 }) },
      '@arco-design/web-vue': { Message: { warning: value => warnings.push(value), success() {} }, Modal: {} },
      '@/api/perf': api,
    },
  })
  Object.assign(h.form, { name: 'Example scenario', source_case_release_id: 2, version: 3 })
  h.sourceCase.value = { release_id: 2, compatible: true }
  Object.assign(h.loadConfig, { duration_seconds: 60 })
  return { ...h, warnings, goal: h.load('performance-goal.ts'), config: h.load('config.ts') }
}

test('missing goals use detached default objects; explicit zero percentages survive', () => {
  const h = setup()
  const a = h.goal.performanceGoalFromApi(), b = h.goal.performanceGoalFromApi(null)
  assert.deepEqual(a, { p95_ms: 500, error_rate_percent: 1, load_achievement_rate_percent: 95 })
  a.p95_ms = 1
  assert.equal(b.p95_ms, 500)
  assert.deepEqual(h.goal.performanceGoalFromApi({ p95_ms: '20', max_error_rate: '0', min_load_achievement_rate: 0 }), {
    p95_ms: 20, error_rate_percent: 0, load_achievement_rate_percent: 0,
  })
  h.close()
})

test('backend decimal rates convert to percentages and response extras are not retained', () => {
  const h = setup()
  const fixture = { p95_ms: 800, max_error_rate: '0.025', min_load_achievement_rate: '0.9', audit: 'ignored' }
  const result = h.goal.performanceGoalFromApi(fixture)
  assert.deepEqual(result, { p95_ms: 800, error_rate_percent: 2.5, load_achievement_rate_percent: 90 })
  fixture.p95_ms = 900
  assert.equal(result.p95_ms, 800)
  assert.equal('audit' in result, false)
  h.close()
})

test('malformed API goals cannot turn null, blank, booleans or non-finite values into valid thresholds', () => {
  const h = setup()
  for (const value of [false, '', [], 0, { p95_ms: 0 }, { p95_ms: 1.5 }, { p95_ms: Number.MAX_SAFE_INTEGER + 1 }]) {
    assert.throws(() => h.goal.performanceGoalFromApi(value))
  }
  for (const key of ['p95_ms', 'max_error_rate', 'min_load_achievement_rate']) {
    for (const value of [null, false, true, '', ' ', Infinity, NaN, -1, {}, []]) {
      assert.throws(() => h.goal.performanceGoalFromApi({ [key]: value }), `${key}: ${String(value)}`)
    }
  }
  assert.throws(() => h.goal.performanceGoalFromApi({ max_error_rate: 1.01 }))
  assert.throws(() => h.goal.performanceGoalFromApi({ min_load_achievement_rate: 1.01 }))
  h.close()
})

test('payload contains only defined backend fields and round-trips custom boundary values', () => {
  const h = setup()
  for (const percentage of [0, 0.5, 100]) {
    const goal = { p95_ms: 1, error_rate_percent: percentage, load_achievement_rate_percent: percentage, ignored: true }
    const payload = h.goal.performanceGoalToPayload(goal, 'custom')
    assert.deepEqual(Object.keys(payload).sort(), ['template_key', 'p95_ms', 'max_error_rate', 'min_load_achievement_rate'].sort())
    assert.deepEqual(h.goal.performanceGoalFromApi(payload), { p95_ms: 1, error_rate_percent: percentage, load_achievement_rate_percent: percentage })
    assert.equal(payload.template_key, 'custom')
  }
  assert.throws(() => h.goal.performanceGoalToPayload(h.config.createDefaultPerformanceGoal(), 'invalid'))
  h.close()
})

test('recommended classification uses the same finite numeric validation as serialization', () => {
  const h = setup()
  assert.equal(h.goal.isRecommendedPerformanceGoal(h.config.createDefaultPerformanceGoal()), true)
  assert.equal(h.goal.isRecommendedPerformanceGoal({ p95_ms: 500, error_rate_percent: 0, load_achievement_rate_percent: 95 }), false)
  assert.equal(h.goal.isRecommendedPerformanceGoal({ p95_ms: NaN, error_rate_percent: 1, load_achievement_rate_percent: 95 }), false)
  h.close()
})

test('actual page validation and save block invalid cleared/out-of-range goal fields without HTTP', async () => {
  let calls = 0
  const h = setup({ savePerfScenarioConfiguration: async () => { calls++; return { code: 200, data: { id: 1, version: 4 } } } })
  for (const [field, value] of [
    ['p95_ms', undefined], ['p95_ms', 1.5], ['p95_ms', NaN],
    ['error_rate_percent', undefined], ['error_rate_percent', 101],
    ['load_achievement_rate_percent', null], ['load_achievement_rate_percent', -1],
  ]) {
    Object.assign(h.performanceGoal, h.config.createDefaultPerformanceGoal(), { [field]: value })
    assert.equal(await h.save(), false)
    assert.equal(h.saving.value, false)
    assert.ok(h.warnings.at(-1))
  }
  assert.equal(calls, 0)
  h.close()
})

test('actual page saves legitimate zero percentages with version and existing configuration protocol', async () => {
  let saved
  const h = setup({ savePerfScenarioConfiguration: async (id, payload) => { saved = { id, payload }; return { code: 200, data: { id: 1, version: 4 } } } })
  Object.assign(h.performanceGoal, { p95_ms: 25, error_rate_percent: 0, load_achievement_rate_percent: 0 })
  assert.equal(await h.save(), true)
  assert.equal(saved.id, '1')
  assert.equal(saved.payload.version, 3)
  assert.equal(saved.payload.source_case_release_id, 2)
  assert.deepEqual(saved.payload.performance_goal, { template_key: 'recommended', p95_ms: 25, max_error_rate: 0, min_load_achievement_rate: 0 })
  assert.equal(h.form.version, 4)
  assert.equal(h.saving.value, false)
  h.close()
})

test('actual scenario SFC compiles and goal/config/types pass a dependency-isolated TypeScript check', () => {
  const filename = path.join(base, 'index.vue')
  const parsed = parse(readFileSync(filename, 'utf8'), { filename })
  assert.deepEqual(parsed.errors, [])
  const script = compileScript(parsed.descriptor, { id: 'perf-scenario-details' })
  const template = compileTemplate({ source: parsed.descriptor.template.content, filename, id: 'perf-scenario-details', compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, [])
  const program = ts.createProgram(['config.ts', 'types.ts', 'performance-goal.ts'].map(file => path.join(base, file)), {
    noEmit: true, strict: true, target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext,
    moduleResolution: ts.ModuleResolutionKind.NodeJs, types: [], skipLibCheck: true,
  })
  const diagnostics = ts.getPreEmitDiagnostics(program)
  assert.equal(diagnostics.length, 0, ts.formatDiagnosticsWithColorAndContext(diagnostics, {
    getCanonicalFileName: value => value, getCurrentDirectory: () => process.cwd(), getNewLine: () => '\n',
  }))
})

test('actual save retains a physical request lock and captures a detached payload until completion', async () => {
  const pending = deferred()
  let calls = 0, payload
  const h = setup({ savePerfScenarioConfiguration: async (_id, value) => {
    calls++; payload = value; return pending.promise
  } })
  const first = h.save()
  assert.equal(h.saving.value, true)
  h.form.name = 'Changed while saving'
  h.loadConfig.duration_seconds = 120
  h.performanceGoal.p95_ms = 1000
  assert.equal(await h.save(), false)
  assert.equal(calls, 1)
  assert.equal(payload.base.name, 'Example scenario')
  assert.equal(payload.load_config.duration_seconds, 60)
  assert.equal(payload.performance_goal.p95_ms, 500)
  pending.resolve({ code: 200, data: { id: 1, version: 4 } })
  assert.equal(await first, true)
  assert.equal(h.saving.value, false)
  h.close()
})

test('failed save releases the lock, preserves version and draft, and permits explicit retry', async () => {
  let fail = true, calls = 0
  const h = setup({ savePerfScenarioConfiguration: async () => {
    calls++
    if (fail) throw new Error('fixture failure')
    return { code: 200, data: { id: 1, version: 4 } }
  } })
  await assert.rejects(h.save(), /fixture failure/)
  assert.equal(h.saving.value, false)
  assert.equal(h.form.version, 3)
  assert.equal(h.form.name, 'Example scenario')
  fail = false
  assert.equal(await h.save(), true)
  assert.equal(calls, 2)
  assert.equal(h.form.version, 4)
  h.close()
})
