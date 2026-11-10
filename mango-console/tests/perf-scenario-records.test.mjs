import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/perf/scenario/details')
const envelope = data => ({ code: 200, data })
const release = (patch = {}) => ({
  release_id: 2, case_id: 7, name: 'Example case', title: 'Example case · Group / Module (V1)',
  disabled: false, compatible: true, incompatible_reasons: [], version_label: 'V1', revision_no: 1,
  module_full_path: 'Group / Module', ignored: 'extra',
  steps: [{ key: 'step-1', name: 'Example request', api_info_id: 9, extractor_count: 0, check_count: 0, ignored: 'extra' }],
  ...patch,
})
const scenario = (patch = {}) => ({
  id: 1, name: 'Example scenario', project_product: 10, version: 3, engine: 'k6',
  source_case_release_id: 2, source_case: release(), default_executor_count: 1,
  node_failure_policy: 'strict', min_ready_nodes: null, load_type: 'concurrency',
  load_config: { name: 'Example load', profile: 'constant_concurrency', duration_seconds: 60, target_users: 10, target_rate: null },
  performance_goal: { template_key: 'recommended', p95_ms: 500, max_error_rate: 0.01, min_load_achievement_rate: 0.95 },
  ignored: 'extra', ...patch,
})
function setup(api = {}) {
  const messages = []
  const h = harness('index', 'form,scenarioRecord,loadConfig,sourceCase,caseItems,performanceGoal,performanceGoalTemplate,caseLoading,caseError,detailError,loading,refresh:load,loadCases,save,validating,validateConfig', {
    base, modules: {
      'vue-router': { useRoute: () => ({ path: '/perf/scenario/details', query: { id: '1' } }), useRouter: () => ({}) },
      '@/store/modules/user': { default: () => ({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 0 }) },
      '@arco-design/web-vue': { Message: { warning: text => messages.push(['warning', text]), success: text => messages.push(['success', text]), error: text => messages.push(['error', text]) } },
      '@/api/perf': {
        getPerfScenario: async () => envelope(scenario()), getPerfScenarioSourceCases: async () => envelope([]),
        savePerfScenarioConfiguration: async () => envelope({ id: 1, version: 4 }),
        validatePerfScenario: async () => envelope({ valid: true, step_count: 0, duration_seconds: 60 }), ...api,
      },
    },
  })
  return { ...h, records: h.load('records.ts'), messages }
}

test('finite defaults keep unselected IDs nullable and editable empty numerics undefined', () => {
  const h = setup()
  assert.equal(h.form.project_product, null)
  assert.equal(h.form.version, null)
  assert.equal(h.form.source_case_release_id, undefined)
  assert.equal(h.form.min_ready_nodes, undefined)
  assert.equal(h.sourceCase.value, null)
  assert.equal(h.scenarioRecord.value, null)
  assert.equal('ignored' in h.form, false)
  h.close()
})

test('metadata unlocks while source options load; source failure and retry remain local', async () => {
  const pending = deferred()
  let attempt = 0
  const h = setup({ getPerfScenarioSourceCases: () => ++attempt === 1 ? pending.promise : Promise.resolve(envelope([release()])) })
  const loading = h.refresh()
  await flush()
  assert.equal(h.loading.value, false)
  assert.equal(h.form.name, 'Example scenario')
  assert.equal(h.caseLoading.value, true)
  assert.equal(h.detailError.value, false)
  pending.reject(new Error('source unavailable'))
  await assert.rejects(loading)
  assert.equal(h.caseError.value, true)
  assert.equal(h.detailError.value, false)
  assert.equal(h.caseLoading.value, false)
  h.form.name = 'Unsaved draft'
  await h.loadCases()
  assert.equal(h.caseError.value, false)
  assert.equal(h.caseItems.value.length, 1)
  assert.equal(h.form.name, 'Unsaved draft')
  h.close()
})

test('overlapping detail reads publish only the newest response and preserve its loading ownership', async () => {
  const first = deferred(), second = deferred()
  let reads = 0, options = 0
  const h = setup({
    getPerfScenario: () => ++reads === 1 ? first.promise : second.promise,
    getPerfScenarioSourceCases: async () => { options++; return envelope([]) },
  })
  const oldRead = h.refresh(), currentRead = h.refresh()
  first.resolve(envelope(scenario({ name: 'Stale' })))
  await oldRead
  assert.equal(h.form.name, '')
  assert.equal(h.loading.value, true)
  assert.equal(options, 0)
  second.resolve(envelope(scenario({ name: 'Current' })))
  await currentRead
  assert.equal(h.form.name, 'Current')
  assert.equal(h.loading.value, false)
  assert.equal(options, 1)
  h.close()
})

test('new metadata read invalidates pending source options including stale failure feedback', async () => {
  const oldOptions = deferred(), newOptions = deferred()
  let reads = 0
  const h = setup({ getPerfScenarioSourceCases: () => ++reads === 1 ? oldOptions.promise : newOptions.promise })
  const first = h.refresh()
  await flush()
  const second = h.refresh()
  await flush()
  oldOptions.reject(new Error('stale source failure'))
  await first
  assert.equal(h.caseError.value, false)
  assert.equal(h.caseLoading.value, true)
  newOptions.resolve(envelope([release({ name: 'Current option' })]))
  await second
  assert.equal(h.caseLoading.value, false)
  assert.equal(h.caseItems.value[0].name, 'Current option')
  h.close()
})

test('actual detail load stores detached finite response and separates form draft from original record', async () => {
  const fixture = scenario({ min_ready_nodes: 0 })
  const h = setup({ getPerfScenario: async () => envelope(fixture) })
  await h.refresh()
  assert.equal(h.form.project_product, 10)
  assert.equal(h.form.min_ready_nodes, 0)
  assert.equal(h.sourceCase.value.steps[0].extractor_count, 0)
  assert.equal(h.sourceCase.value.steps[0].check_count, 0)
  assert.equal('ignored' in h.form, false)
  assert.equal('ignored' in h.sourceCase.value, false)
  assert.equal('ignored' in h.sourceCase.value.steps[0], false)
  h.form.name = 'Edited draft'
  h.loadConfig.target_users = 20
  h.performanceGoal.p95_ms = 900
  assert.equal(h.scenarioRecord.value.form.name, 'Example scenario')
  assert.equal(h.scenarioRecord.value.load.target_users, 10)
  assert.equal(h.scenarioRecord.value.goal.p95_ms, 500)
  fixture.source_case.steps[0].name = 'Mutated response'
  assert.equal(h.sourceCase.value.steps[0].name, 'Example request')
  h.close()
})

test('bad late field or wrong scenario cannot partially replace previously loaded form, load and source', async () => {
  let fixture = scenario()
  const h = setup({ getPerfScenario: async () => envelope(fixture) })
  await h.refresh()
  const saved = h.scenarioRecord.value
  for (const patch of [
    { name: 'Corrupt', performance_goal: { p95_ms: null } }, { id: 2 }, { version: false },
    { source_case_release_id: 99 }, { project_product: { id: 10 } }, { engine: 'invalid' },
    { source_case: release({ steps: [{ key: 'bad', extractor_count: false }] }) },
  ]) {
    fixture = scenario(patch)
    await assert.rejects(h.refresh())
    assert.equal(h.scenarioRecord.value, saved)
    assert.equal(h.form.name, 'Example scenario')
    assert.equal(h.loadConfig.target_users, 10)
    assert.equal(h.sourceCase.value.release_id, 2)
    assert.equal(h.loading.value, false)
  }
  h.close()
})

test('empty and malformed source-case results are distinct; pinned release remains available', async () => {
  let fixture = envelope([])
  const h = setup({ getPerfScenarioSourceCases: async () => fixture })
  await h.refresh()
  assert.equal(h.caseItems.value.length, 1)
  assert.equal(h.caseItems.value[0].release_id, 2)
  fixture = envelope([release({ release_id: 3, case_id: 8 })])
  await h.loadCases()
  assert.deepEqual(h.caseItems.value.map(item => item.release_id), [2, 3])
  const before = h.caseItems.value
  for (const value of [{ code: 400, data: [] }, envelope({}), envelope([release(), release()]), envelope([release({ disabled: 'false' })])]) {
    fixture = value
    await assert.rejects(h.loadCases())
    assert.equal(h.caseItems.value, before)
    assert.equal(h.caseLoading.value, false)
  }
  h.close()
})

test('nullable source, nullable step API ID and custom zero goal remain valid without invented records', () => {
  const h = setup()
  const result = h.records.readScenarioConfiguration(envelope(scenario({
    source_case: null, source_case_release_id: null,
    performance_goal: { template_key: 'custom', p95_ms: 5, max_error_rate: 0, min_load_achievement_rate: 0 },
  })), '1')
  assert.equal(result.source, null)
  assert.equal(result.form.source_case_release_id, undefined)
  assert.equal(result.goal.error_rate_percent, 0)
  assert.equal(result.goal.load_achievement_rate_percent, 0)
  assert.equal(result.goalTemplate, 'custom')
  assert.equal(h.records.readSourceCase(release({ steps: [{ key: 'step-1', name: 'Example', api_info_id: null, extractor_count: 0, check_count: 0 }] })).steps[0].api_info_id, null)
  h.close()
})

test('business/format failure and wrong saved version cannot update optimistic version or show success', async () => {
  let fixture = envelope({ id: 1, version: 4 })
  const h = setup({ savePerfScenarioConfiguration: async () => fixture })
  await h.refresh()
  for (const value of [{ code: 400, data: { id: 1, version: 4 } }, envelope({ id: 2, version: 4 }), envelope({ id: 1, version: 3 }), envelope({ id: 1, version: null })]) {
    fixture = value
    await assert.rejects(h.save())
    assert.equal(h.form.version, 3)
  }
  assert.equal(h.messages.filter(item => item[0] === 'success').length, 0)
  fixture = envelope({ id: 1, version: 4 })
  assert.equal(await h.save(), true)
  assert.equal(h.form.version, 4)
  h.close()
})

test('cleared min-ready field is explicitly sent as null; zero is preserved and audit fields are excluded', async () => {
  let payload, next = 3
  const h = setup({ savePerfScenarioConfiguration: async (_id, value) => { payload = value; return envelope({ id: 1, version: ++next }) } })
  await h.refresh()
  await h.save()
  assert.equal(payload.base.min_ready_nodes, null)
  assert.equal('ignored' in payload.base, false)
  assert.equal('project_product' in payload.base, false)
  h.form.min_ready_nodes = 0
  await h.save()
  assert.equal(payload.base.min_ready_nodes, 0)
  h.close()
})

test('configuration validation has an independent physical lock and validates business response before success', async () => {
  const pending = deferred()
  let calls = 0
  const h = setup({ validatePerfScenario: () => { calls++; return pending.promise } })
  await h.refresh()
  const first = h.validateConfig(); await flush()
  await h.validateConfig()
  assert.equal(calls, 1)
  assert.equal(h.validating.value, true)
  pending.resolve(envelope({ valid: false, step_count: 0, duration_seconds: 60 }))
  await assert.rejects(first)
  assert.equal(h.validating.value, false)
  assert.equal(h.messages.some(item => item[1].startsWith('校验通过')), false)
  h.close()
})
