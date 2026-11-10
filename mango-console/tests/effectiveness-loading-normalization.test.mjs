import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, deferred, flush as microtasks } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/report/effectiveness')
const overviewResponse = (name = 'current') => ({ code: 200, data: { cards: { suite_count: 1, detail_count: 1 }, testName: name } })
const unavailable = () => ({ code: 200, data: { available: false, reason: 'not configured' } })
const summaryResponse = (name = 'Example') => ({ code: 200, data: { available: true, model: 'Example', generated_at: '', summary: {
  headline: name, executive_summary: 'Summary', quality_trend: { status: 'stable', label: 'Stable', analysis: 'Evidence' },
  benefits: [{ title: 'Benefit', detail: 'Detail', evidence: 'Evidence' }], risks: [], recommendations: [], chart_insights: {}, component_insights: {},
} } })
async function flush() { await microtasks(); await new Promise(resolve => setImmediate(resolve)); await microtasks() }
function setup(settings = {}) {
  const route = vue.reactive({ path: '/report/effectiveness/index', fullPath: '/report/effectiveness/index' })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 0 })
  const project = vue.reactive({ projectProduct: [{ label: 'Project', value: 1, children: [{ label: 'Product', value: 0 }] }],
    projectProductNavigationSelection: { projectProduct: 0 }, optionErrors: { products: false },
    projectProductName: () => settings.options ? settings.options() : Promise.resolve(),
    setProjectProductNavigationSelection(value) { this.projectProductNavigationSelection.projectProduct = value },
  })
  const enums = { getEnum: async () => {}, environment_type: [], automation_execution_scene: [], automation_execution_scope: [] }
  const life = { mount: [], unmount: [], activate: [], deactivate: [] }, calls = [], messages = [], navigations = []
  const oldDocument = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  globalThis.document = doc
  const h = harness('index', 'ai,aiState,aiLoading,aiError,aiInsightError,overview,overviewEvidence,overviewReady,loading,loadError,loadData,loadAiSummary,filters,draftFilters,applyFilters,filterVisible,failureReportDrawer,diagnosticDrawer,cacheClearing,clearEffectivenessCache,pageContextVersion,resetFilters,syncDraftFilters,onFilterPopoverVisibleChange,verdictText,verdictReasonText,moduleQualityData,moduleQualitySummary,taskHealthClass,sceneMatrixData,trendOption,environmentOption,sceneOption,scopeOption,moduleRiskOption,issueParetoOption,moduleChangeOption,sceneMatrixOption,automationTypeOption,onTrendChartClick,onEnvironmentChartClick,onSceneChartClick,onScopeChartClick,onModuleRiskClick,onIssueParetoClick,onModuleChangeClick,onSceneMatrixClick,openFailedCaseReport,openTaskDiagnostic,currentReportQuery,onPeriodQualityClick,imageExportDisabled,pdfExportDisabled,downloadReportImage,printReport', {
    base, filename: path.join(base, 'index.vue'),
    api: {
      getAutomationEffectivenessOverview: (...args) => { calls.push(['overview', ...args]); return settings.overview ? settings.overview(...args) : overviewResponse() },
      postAutomationEffectivenessAiSummary: payload => { calls.push(['ai', payload]); return settings.ai ? settings.ai(payload) : unavailable() },
      postAutomationEffectivenessCacheClear: () => { calls.push(['clear']); return settings.clear ? settings.clear() : { code: 200, msg: 'ok' } },
    },
    modules: {
      vue: { ...vue, onMounted: fn => life.mount.push(fn), onBeforeUnmount: fn => life.unmount.push(fn), onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn) },
      'vue-router': { useRoute: () => route, useRouter: () => ({ push(value) { navigations.push(value) } }) },
      '@/store/modules/user': { useUserStoreContext: () => user }, '@/store/modules/get-project': { useProject: () => project },
      '@/store/modules/get-enum': { useEnum: () => enums },
      '@arco-design/web-vue/es/icon': {}, 'print-js': { default() {} }, 'html-to-image': { toPng: async () => 'data:image/png;base64,' },
      '@arco-design/web-vue': { Message: { error: value => messages.push(['error', value]), success: value => messages.push(['success', value]), warning: value => messages.push(['warning', value]) } },
    },
  })
  return { ...h, route, user, project, doc, life, calls, messages, navigations,
    mount() { life.mount.forEach(fn => fn()); life.activate.forEach(fn => fn()) },
    close() { life.unmount.forEach(fn => fn()); h.close(); globalThis.document = oldDocument },
  }
}

test('初次加载选项与统计后自动总结，ID0/多值查询保留；同请求合并至实际完成', async t => {
  const read = deferred(), h = setup({ overview: () => read.promise }); t.after(h.close)
  h.mount(); await flush()
  assert.equal(h.loading.value, true); assert.equal(h.calls.filter(c => c[0] === 'overview').length, 1)
  const first = h.loadData(), second = h.loadData(); assert.equal(first, second)
  assert.equal(h.calls[0][1].project_product_id, 0); assert.equal(h.calls[0][2], true)
  read.resolve(overviewResponse()); await first; await flush()
  assert.equal(h.loading.value, false); assert.equal(h.overviewReady.value, true); assert.equal(h.calls.filter(c => c[0] === 'ai').length, 1)
  h.draftFilters.test_env = [0, 1]; h.draftFilters.execution_scene = ['smoke', 'regression']
  await h.applyFilters(); await flush()
  const query = h.calls.filter(c => c[0] === 'overview').at(-1)[1]
  assert.equal(query.test_env, '0,1'); assert.equal(query.execution_scene, 'smoke,regression')
})

test('新范围失败不展示旧统计，业务/网络失败有局部错误，重试成功后才启动AI', async t => {
  const responses = [overviewResponse('old'), { code: 403, data: {} }, new Error('network'), overviewResponse('new')]
  const h = setup({ overview: () => { const next = responses.shift(); if (next instanceof Error) throw next; return next } }); t.after(h.close)
  h.mount(); await flush(); assert.equal(h.overviewEvidence.value?.testName, 'old')
  assert.equal(h.imageExportDisabled.value, false); assert.equal(h.pdfExportDisabled.value, false)
  h.filters.test_env = [1]; await h.loadData(); await flush()
  assert.equal(h.overviewEvidence.value?.testName, undefined); assert.equal(h.overviewReady.value, false); assert.ok(h.loadError.value); assert.equal(h.loading.value, false)
  assert.equal(h.imageExportDisabled.value, true); assert.equal(h.pdfExportDisabled.value, true)
  await h.downloadReportImage(); await h.printReport()
  assert.equal(h.calls.filter(c => c[0] === 'ai').length, 1)
  await h.loadData(); assert.ok(h.loadError.value)
  await h.loadData(); await flush(); assert.equal(h.overviewEvidence.value?.testName, 'new'); assert.equal(h.loadError.value, '')
})

test('筛选A-B-A，旧统计与finally不覆盖最后一次请求', async t => {
  const reads = [deferred(), deferred(), deferred()]; let index = 0
  const h = setup({ overview: () => reads[index++].promise }); t.after(h.close)
  h.mount(); await flush(); const first = h.loadData()
  h.filters.test_env = [2]; const second = h.loadData(); await flush()
  h.filters.test_env = []; const last = h.loadData(); await flush()
  reads[0].resolve(overviewResponse('old')); reads[1].reject(new Error('stale')); await Promise.all([first, second])
  assert.equal(h.loading.value, true); assert.equal(h.overviewEvidence.value?.testName, undefined); assert.equal(h.loadError.value, '')
  reads[2].resolve(overviewResponse('latest')); await last; assert.equal(h.overviewEvidence.value?.testName, 'latest')
})

for (const field of ['userId', 'roleId', 'token', 'selected_environment']) {
  test(`${field} A-B-A 失效旧统计/AI并关闭窗口，重新加载当前可见产品`, async t => {
    const old = deferred(); let count = 0
    const h = setup({ overview: () => ++count === 1 ? old.promise : overviewResponse('current') }); t.after(h.close)
    h.mount(); await flush()
    h.failureReportDrawer.visible = true; h.diagnosticDrawer.visible = true
    const before = h.user[field]; h.user[field] = field === 'token' ? 'fixture-new' : 2; h.user[field] = before
    await flush(); assert.equal(h.failureReportDrawer.visible, false); assert.equal(h.diagnosticDrawer.visible, false)
    old.resolve(overviewResponse('old')); await flush()
    assert.equal(h.overviewEvidence.value?.testName, 'current'); assert.equal(h.loading.value, false)
  })
}

test('后台、缓存停用和离开路由暂停请求，返回重读，卸载后不再读取', async t => {
  const old = deferred(); let count = 0
  const h = setup({ overview: () => ++count === 1 ? old.promise : overviewResponse(`read-${count}`) }); t.after(h.close)
  h.mount(); await flush()
  h.doc.visibilityState = 'hidden'; h.doc.dispatchEvent(new Event('visibilitychange'))
  old.resolve(overviewResponse('old')); await flush(); assert.equal(h.overviewReady.value, false)
  await h.loadData(); assert.equal(count, 1)
  h.doc.visibilityState = 'visible'; h.doc.dispatchEvent(new Event('visibilitychange')); await flush(); assert.equal(h.overviewEvidence.value?.testName, 'read-2')
  h.life.deactivate.forEach(fn => fn()); await h.loadData(); assert.equal(count, 2)
  h.life.activate.forEach(fn => fn()); await flush(); assert.equal(h.overviewEvidence.value?.testName, 'read-3')
  h.route.path = '/report/index'; h.route.fullPath = '/report/index'; await h.loadData(); assert.equal(count, 3)
  h.route.path = '/report/effectiveness/index'; h.route.fullPath = h.route.path; await flush(); assert.equal(h.overviewEvidence.value?.testName, 'read-4')
  h.life.unmount.forEach(fn => fn()); await h.loadData(); assert.equal(count, 4)
})

test('初始化失败可重试，成功后才读取统计', async t => {
  let count = 0
  const h = setup({ options: () => { if (++count === 1) throw new Error('options failed'); return Promise.resolve() } }); t.after(h.close)
  h.mount(); await flush(); assert.ok(h.loadError.value); assert.equal(h.loading.value, false); assert.equal(h.calls.length, 0)
  await h.loadData(); await flush(); assert.equal(h.overviewReady.value, true)
})

test('选项初始化期间进入后台，迟到选项不触发统计，返回重新初始化', async t => {
  const options = deferred(); let count = 0
  const h = setup({ options: () => ++count === 1 ? options.promise : Promise.resolve() }); t.after(h.close)
  h.mount(); await flush(); assert.equal(h.loading.value, true)
  h.doc.visibilityState = 'hidden'; h.doc.dispatchEvent(new Event('visibilitychange'))
  options.resolve(); await flush(); assert.equal(h.calls.length, 0); assert.equal(h.loading.value, false)
  h.doc.visibilityState = 'visible'; h.doc.dispatchEvent(new Event('visibilitychange')); await flush()
  assert.equal(count, 2); assert.equal(h.overviewReady.value, true)
})

test('AI总结等待期间身份切换，旧正文和finally不回填当前上下文', async t => {
  const old = deferred(); let count = 0
  const h = setup({ ai: () => ++count === 1 ? old.promise : unavailable() }); t.after(h.close)
  h.mount(); await flush(); assert.equal(h.aiLoading.value, true)
  h.user.roleId = 2; await flush(); assert.equal(h.aiState.available, false)
  old.resolve(summaryResponse('old')); await flush()
  assert.equal(h.aiState.available, false); assert.equal(h.aiState.summary, null); assert.equal(h.aiLoading.value, false)
})

test('AI生成合并重复点击，输入为固定快照；补解读失败保留总结并恢复重试', async t => {
  const summary = deferred(), insights = deferred(); let count = 0
  const h = setup({ ai: () => ++count === 1 ? summary.promise : count === 2 ? insights.promise : unavailable() }); t.after(h.close)
  h.mount(); await flush()
  const first = h.loadAiSummary(true), second = h.loadAiSummary(true); assert.equal(first, second); assert.equal(count, 1)
  h.overviewEvidence.value.testName = 'mutated'
  assert.equal(h.calls.find(c => c[0] === 'ai')[1].overview.testName, 'current')
  summary.resolve(summaryResponse()); await flush(); assert.equal(h.aiState.summary.headline, 'Example'); assert.equal(h.aiLoading.value, true)
  insights.reject(new Error('insight unavailable')); await first
  assert.equal(h.aiLoading.value, false); assert.ok(h.aiInsightError.value); assert.equal(h.aiState.summary.headline, 'Example')
  await h.loadAiSummary(true); assert.equal(h.aiError.value, ''); assert.equal(h.aiState.available, false)
})

test('AI补充解读旧失败不能清空新范围解读，AI失败不伪装成未配置', async t => {
  const oldInsights = deferred(); let count = 0
  const h = setup({ ai: payload => {
    if (++count === 1) return summaryResponse('old')
    if (count === 2) return oldInsights.promise
    if (count === 3) return summaryResponse('current')
    if (count === 4) return { code: 200, data: { available: true, insights: { overview: 'current insight' } } }
    throw new Error('network')
  } }); t.after(h.close)
  h.mount(); await flush(); assert.equal(count, 2)
  await h.loadData(); await flush(); assert.equal(h.ai.insightState.insights.overview, 'current insight')
  oldInsights.reject(new Error('stale')); await flush()
  assert.equal(h.aiState.summary.headline, 'current'); assert.equal(h.ai.insightState.insights.overview, 'current insight'); assert.equal(h.aiInsightError.value, '')
  await h.loadAiSummary(true); assert.ok(h.aiError.value); assert.equal(h.aiState.available, null); assert.equal(h.aiLoading.value, false)
})

test('AI有限字段校验保留正文和合法解读，不信任错误码或非法嵌套', t => {
  const h = setup(); t.after(h.close); const data = h.load('ai-summary.ts')
  const response = summaryResponse(); response.data.summary.benefits = [null, { title: 'Title', detail: {}, evidence: 'Evidence', unexpected: true }]
  response.data.summary.chart_insights = { trend: 'Trend', unknown: 'unexpected', environment: {} }
  const parsed = data.parseEffectivenessAiState(response)
  assert.deepEqual(parsed.summary.benefits, [{ title: 'Title', detail: '', evidence: 'Evidence' }])
  assert.deepEqual(parsed.summary.chart_insights, { trend: 'Trend' })
  assert.throws(() => data.parseEffectivenessAiState({ code: 403, data: response.data }))
  assert.throws(() => data.parseEffectivenessAiState({ code: 200, data: { available: true, summary: {} } }))
  assert.equal(data.parseEffectivenessAiState(unavailable()).available, false)
})

test('清除缓存防重复；身份切换后迟到成功不提示或刷新新范围', async t => {
  const read = deferred(), h = setup({ clear: () => read.promise }); t.after(h.close)
  h.mount(); await flush(); const first = h.clearEffectivenessCache(); await h.clearEffectivenessCache()
  assert.equal(h.calls.filter(c => c[0] === 'clear').length, 1); assert.equal(h.cacheClearing.value, true)
  h.user.roleId = 2; await flush(); const before = h.calls.filter(c => c[0] === 'overview').length
  read.resolve({ code: 200, msg: 'ok' }); await first
  assert.equal(h.cacheClearing.value, false); assert.equal(h.calls.filter(c => c[0] === 'overview').length, before)
  assert.deepEqual(h.messages, [])
})

test('有限展示模型隔离原始AI证据，未知字段不进入页面状态，0/false/非法值不混淆', t => {
  const h = setup(); t.after(h.close); const model = h.load('overview.ts')
  const source = { cards: { suite_count: 1, final_pass_rate: 0, completion_rate: false, flaky_rate: '', detail_count: 0 },
    benefits: { automation_types: [null, { type: 0, name: 'UI', count: 0 }] },
    module_quality: [null, { module_id: '9223372036854775807', quality_level: 'other', final_pass_rate: null, pass_rate_delta: -2 }], unknown: { retained: true } }
  const before = JSON.stringify(source), result = model.normalizeEffectivenessOverview(source)
  assert.equal(result.cards.final_pass_rate, 0); assert.equal(result.cards.completion_rate, null); assert.equal(result.cards.flaky_rate, null)
  assert.equal(result.benefits.automation_types[0].type, 0); assert.equal(result.module_quality[0].module_id, '9223372036854775807')
  assert.equal(result.module_quality[0].quality_level, 'unknown'); assert.equal(result.module_quality[0].pass_rate_delta, -2)
  assert.equal('unknown' in result, false); assert.equal(JSON.stringify(source), before)
  result.benefits.automation_types[0].name = 'changed'; assert.equal(source.benefits.automation_types[1].name, 'UI')
  for (const value of [null, undefined, false, '', '  ', {}, [], NaN, Infinity, '0x10', 'invalid']) assert.equal(model.effectivenessNumber(value), null)
  assert.equal(model.effectivenessNumber('0.00'), 0); assert.equal(model.effectivenessNumber('-2.5'), -2.5)
})

test('坏统计结构不会造成数组和属性异常，全部图表计算仍可读取', async t => {
  const h = setup({ overview: () => ({ code: 200, data: { cards: null, benefits: [], comparison: false, convergence: '',
    module_quality: [null, false], insights: {}, trend: null, period_quality: [null], scene_distribution: false,
    scope_distribution: {}, environment_quality: 'bad', scene_matrix: { environments: [null], scenes: null, values: [] }, task_health: {}, failed_case_ranking: null } }) }); t.after(h.close)
  h.mount(); await flush()
  assert.equal(h.loadError.value, ''); assert.equal(h.overview.cards.suite_count, 0); assert.equal(h.overview.module_quality.length, 0)
  for (const name of ['trendOption', 'environmentOption', 'sceneOption', 'scopeOption', 'moduleRiskOption', 'issueParetoOption', 'moduleChangeOption', 'sceneMatrixOption', 'automationTypeOption']) assert.ok(h[name].value, name)
})

test('未完成或缺失通过率不被当成0%高风险，真实0%仍按既有风险阈值判断', async t => {
  const h = setup({ overview: () => ({ code: 200, data: { cards: { suite_count: 1, detail_count: 1, final_pass_rate: null, unfinished_count: 1 } } }) }); t.after(h.close)
  h.mount(); await flush(); assert.equal(h.verdictText.value, '执行尚未完成'); assert.match(h.verdictReasonText.value, /尚未结束/)
  h.overview.cards.unfinished_count = 0; assert.equal(h.verdictText.value, '暂无完成结果')
  h.overview.cards.final_pass_rate = 0; assert.equal(h.verdictText.value, '质量风险较高')
  assert.equal(h.taskHealthClass(h.load('overview.ts').normalizeEffectivenessOverview({ task_health: [{ final_pass_rate: null }] }).task_health[0]), 'is-neutral')
  assert.equal(h.taskHealthClass(h.load('overview.ts').normalizeEffectivenessOverview({ task_health: [{ final_pass_rate: null, consecutive_abnormal: 1 }] }).task_health[0]), 'is-warning')
})

test('筛选打开/取消/重开及应用后草稿均独立，级联路径不会连带修改生效产品', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush()
  h.filters.project_product = [1, 0]; h.filters.test_env = [0]
  h.onFilterPopoverVisibleChange(true); h.draftFilters.project_product[1] = 2; h.draftFilters.test_env.push(1)
  assert.deepEqual(h.filters.project_product, [1, 0]); assert.deepEqual(h.filters.test_env, [0])
  h.onFilterPopoverVisibleChange(false); h.onFilterPopoverVisibleChange(true)
  assert.deepEqual(h.draftFilters.project_product, [1, 0]); assert.deepEqual(h.draftFilters.test_env, [0])
  await h.applyFilters(); h.draftFilters.project_product[1] = 5; h.draftFilters.test_env.push(3)
  assert.deepEqual(h.filters.project_product, [1, 0]); assert.deepEqual(h.filters.test_env, [0])
  h.resetFilters(); assert.equal(h.draftFilters.project_product, undefined); assert.deepEqual(h.draftFilters.test_env, [])
  assert.equal(h.filters.project_product[1], 0)
})

test('日期预设保持原自然周期与月末规则，默认值工厂及复制不共享数组', t => {
  const h = setup(); t.after(h.close); const f = h.load('filters.ts'), current = new Date(2024, 2, 31)
  assert.deepEqual(f.resolvePeriodDateRange('recent_month', current), ['2024-03-01', '2024-03-31'])
  assert.deepEqual(f.resolvePeriodDateRange('natural_month', current), ['2024-03-01', '2024-03-31'])
  assert.deepEqual(f.resolvePeriodDateRange('natural_quarter', current), ['2024-01-01', '2024-03-31'])
  assert.deepEqual(f.resolvePeriodDateRange('natural_week', current), ['2024-03-25', '2024-03-31'])
  assert.deepEqual(f.resolvePeriodDateRange('natural_two_weeks', current), ['2024-03-18', '2024-03-31'])
  const first = f.createDefaultFilters(current), second = f.createDefaultFilters(current); first.test_env.push(0); first.dateRange[0] = 'changed'
  assert.deepEqual(second.test_env, []); assert.notEqual(second.dateRange[0], 'changed')
  assert.equal(f.selectedEffectivenessProduct([1, 0]), 0); assert.equal(f.selectedEffectivenessProduct('9223372036854775807'), '9223372036854775807')
  assert.equal(f.selectedEffectivenessProduct(Number.MAX_SAFE_INTEGER + 1), null)
})

test('查询只提交白名单日期/真实产品/多值字段，不把空值、草稿元数据提交', t => {
  const h = setup(); t.after(h.close); const f = h.load('filters.ts')
  const source = { ...f.createDefaultFilters(), dateRange: ['2026-01-01', '2026-01-07'], project_product: [1, 0], test_env: [0, 1], execution_scope: ['module'], extra: 'omit' }
  assert.deepEqual(f.effectivenessQuery(source), { start_date: '2026-01-01', end_date: '2026-01-07', project_product_id: 0, test_env: '0,1', execution_scope: 'module' })
  source.project_product = null; source.test_env = []; source.execution_scope = []
  assert.deepEqual(f.effectivenessQuery(source), { start_date: '2026-01-01', end_date: '2026-01-07' })
})

test('下钻只接受有效图表索引，模块/环境/失败明细ID0和长ID保持可操作', async t => {
  const h = setup({ overview: () => ({ code: 200, data: { module_quality: [{ module_id: 0, quality_level: 'danger', final_pass_rate: 0, failed_count: 1, pass_rate_delta: -1 }], environment_quality: [{ environment: 0 }], trend: [{ date_value: '2026-01-01' }], failed_case_ranking: [{ case_type: 0, case_id: 0, latest_failed_detail_id: 0 }] } }) }); t.after(h.close)
  h.mount(); await flush()
  for (const params of [null, {}, { dataIndex: false }, { dataIndex: '' }, { dataIndex: '0' }, { dataIndex: -1 }, { dataIndex: 0.5 }, { dataIndex: 99 }]) { h.onModuleRiskClick(params); h.onTrendChartClick(params) }
  assert.deepEqual(h.navigations, [])
  h.onModuleRiskClick({ dataIndex: 0 }); assert.equal(h.navigations.at(-1).query.module, 0)
  h.onEnvironmentChartClick({ dataIndex: 0 }); assert.equal(h.navigations.at(-1).query.test_env, 0)
  h.openFailedCaseReport(h.overview.failed_case_ranking[0]); assert.equal(h.failureReportDrawer.testSuiteDetailId, 0); assert.equal(h.failureReportDrawer.caseId, 0)
})

test('矩阵有限单元格保留0%和环境0，非法/越界点击不扩大查询范围', async t => {
  const h = setup({ overview: () => ({ code: 200, data: { scene_matrix: { environments: [{ key: 0, title: 'Env' }], scenes: [{ key: 'smoke', title: 'Scene' }], values: { 0: { smoke: { final_pass_rate: 0, detail_count: 0, failed_count: 0 }, unknown: { final_pass_rate: 100 } } } } } }) }); t.after(h.close)
  h.mount(); await flush(); assert.equal(h.sceneMatrixData.value.length, 1); assert.equal(h.sceneMatrixData.value[0].finalPassRate, 0)
  assert.equal(h.overview.scene_matrix.values['0'].unknown, undefined)
  for (const data of [undefined, {}, { sceneIndex: '0', environmentIndex: 0 }, { sceneIndex: -1, environmentIndex: 0 }, { sceneIndex: 2, environmentIndex: 0 }]) h.onSceneMatrixClick({ data })
  assert.deepEqual(h.navigations, [])
  h.onSceneMatrixClick({ data: { sceneIndex: 0, environmentIndex: 0 } }); assert.equal(h.navigations.at(-1).query.test_env, 0); assert.equal(h.navigations.at(-1).query.execution_scene, 'smoke')
})

test('日期下钻拒绝不存在的日期；原始快照未知字段继续传AI，展示白名单不影响请求', async t => {
  const payload = { ...overviewResponse().data, additional_evidence: { value: 0 }, previous_period: { start: '2025-12-01', end: '2025-12-07' } }
  const h = setup({ overview: () => ({ code: 200, data: payload }) }); t.after(h.close); h.mount(); await flush()
  assert.deepEqual(h.calls.find(call => call[0] === 'ai')[1].overview, payload); assert.equal('additional_evidence' in h.overview, false)
  h.onPeriodQualityClick({ start: '2026-02-30', end: '2026-03-01' }); assert.deepEqual(h.navigations, [])
  h.onPeriodQualityClick({ start: '2026-01-01 00:00:00', end: '2026-01-07 23:59:59' }); assert.equal(h.navigations.at(-1).query.start_date, '2026-01-01')
})

test('图表tooltip和数据标签接受未知边界，业务文案转义，缺失索引不回退第一环境', async t => {
  const h = setup({ overview: () => ({ code: 200, data: { environment_quality: [{ environment: 0, final_pass_rate: 99 }] } }) }); t.after(h.close)
  h.mount(); await flush()
  for (const name of ['trendOption', 'environmentOption', 'sceneOption', 'scopeOption', 'moduleRiskOption', 'issueParetoOption', 'moduleChangeOption', 'sceneMatrixOption', 'automationTypeOption']) {
    const formatter = h[name].value.tooltip.formatter
    for (const value of [null, false, {}, [], [null], { value: false }, { value: [null, NaN] }]) {
      const result = formatter(value)
      assert.equal(typeof result, 'string', name); assert.doesNotMatch(result, /NaN|undefined|\[object Object\]/, name)
    }
  }
  const hostile = '<img src="example" onerror="example">'
  const axis = h.trendOption.value.tooltip.formatter([{ axisValueLabel: hostile, seriesName: hostile, value: 0, marker: hostile }])
  assert.match(axis, /&lt;img/); assert.doesNotMatch(axis, /<img/)
  const scatter = h.moduleRiskOption.value.tooltip.formatter({ value: [1, 0, 0, hostile, 1] })
  const matrix = h.sceneMatrixOption.value.tooltip.formatter({ data: { environment: hostile, scene: hostile, value: 0, detailCount: 1 } })
  const change = h.moduleChangeOption.value.tooltip.formatter({ name: hostile, value: 0 })
  for (const result of [scatter, matrix, change]) { assert.match(result, /&lt;img/); assert.doesNotMatch(result, /<img/) }
  const label = h.environmentOption.value.series[1].label.formatter
  assert.equal(label({ dataIndex: 0 }), '99.00%')
  for (const params of [null, {}, { dataIndex: false }, { dataIndex: '' }, { dataIndex: -1 }, { dataIndex: 99 }]) assert.equal(label(params), '暂无结果')
})

test('页面与四个关联组件脚本、模板及CSS编译', async () => {
  for (const name of ['index.vue', 'components/EffectivenessAiNote.vue', 'components/EffectivenessChart.vue', 'components/EffectivenessEmptyState.vue', 'components/PeriodQualityTrend.vue']) {
    const file = path.join(base, name), { descriptor, errors } = parse(readFileSync(file, 'utf8'), { filename: file })
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: name })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename: file, id: name, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ id: name, filename: file, source: style.content, scoped: style.scoped, preprocessLang: style.lang })).errors, [])
  }
})
