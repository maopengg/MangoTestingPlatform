import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/components/reports')
function setup(name, bindings, props = {}) {
  const user = vue.reactive({ userId: null, roleId: null, token: '', selected_environment: 0 })
  const route = vue.reactive({ fullPath: '/report/details?id=0' })
  const lifecycle = { mount: [], unmount: [], deactivate: [] }
  const enums = vue.reactive({ element_exp: [{ key: 0, title: 'CSS' }], element_ope: [{ key: 7, title: '点击' }] })
  const previous = globalThis.document
  const doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  globalThis.document = doc
  const h = harness(name, bindings, {
    base, filename: path.join(base, name + '.vue'), props,
    modules: {
      vue: { ...vue, onMounted: fn => lifecycle.mount.push(fn), onBeforeUnmount: fn => lifecycle.unmount.push(fn), onDeactivated: fn => lifecycle.deactivate.push(fn) },
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { useUserStoreContext: () => user },
      '@/store/modules/get-enum': { useEnum: () => enums },
      '@/hooks/use-artifact-url': { useArtifactUrl: value => vue.computed(() => value.value ? `https://example.com/${value.value}` : '') },
      '@/store/modules/get-ope-value': { useSelectValueStore: () => ({ getSelectLabel: key => key === 'click' ? '点击操作' : undefined, findItemByValue: () => undefined }) },
    },
  })
  lifecycle.mount.forEach(fn => fn())
  return { ...h, user, route, enums, doc, lifecycle, models: h.load('ui-report.ts'), close() {
    lifecycle.unmount.forEach(fn => fn()); h.close(); globalThis.document = previous
  } }
}
const runtimeBindings = 'result,hasResult,resultElementRows,elementRows,statusText,statusColor,operationLabel,pictureSrc,locatorEngineSummary,locatorCandidateRows,matchCountSummary,getCandidateStatus,formatSleep,formatDuration,formatViewport,formatBoundingBox,getElementLocatorRows,getElementTitle,getTextSnippets'
const reportBindings = 'resultData,stepList,timelineRows,operationTotal,passedCount,failedCount,pendingCount,passRate,firstFailedStep,firstFailedPictureUrl,cachePanelVisible,runtimeSections,stepName,operationLabel,timelineRowKey,timelineLabel,runtimeResultName'

test('UI 结果 ID0、失败0与等待/耗时0有效，空对象和坏结果不冒充执行完成', t => {
  const h = setup('UiStepRuntimeResult', runtimeBindings, { result: { id: 0, status: 0, sleep: 0, duration_ms: 0, picture_path: 'shot.png' } }); t.after(h.close)
  assert.equal(h.hasResult.value, true); assert.equal(h.statusText.value, '失败'); assert.equal(h.statusColor.value, 'red')
  assert.equal(h.formatSleep(h.result.value.sleep), '0 秒'); assert.equal(h.formatDuration(h.result.value.duration_ms), '0 ms')
  assert.equal(h.pictureSrc.value, 'https://example.com/shot.png')
  for (const result of [null, [], false, {}, { status: null }, { status: '0' }]) {
    h.props.result = result; assert.equal(h.hasResult.value, false); assert.equal(h.statusText.value, '未测试')
  }
  h.props.result = { page_step_details_id: 0, status: 3 }; assert.equal(h.hasResult.value, true); assert.equal(h.statusText.value, '执行中')
})

test('定位表达式三组/数组/对象兼容，0 下标、false 状态、文本与坐标保留', t => {
  const source = { id: 0, status: 1, elements: [{ id: 0, name: 'Example', exp: 0, loc: '#first', sub: 0, loc2: '#second', exp2: 0,
    visible: false, enabled: false, editable: false, ele_quantity: 0, locate_duration_ms: 0,
    bounding_box: { x: 0, y: 0, width: 0, height: 1 }, text_snippets: ['Text', {}, null, ''], element_text: 'Fallback' }] }
  const before = JSON.stringify(source), h = setup('UiStepRuntimeResult', runtimeBindings, { result: source }); t.after(h.close)
  const element = h.elementRows.value[0], locators = h.getElementLocatorRows(element)
  assert.equal(locators.length, 2); assert.equal(locators[0].expText, 'CSS'); assert.equal(locators[0].sub, 0)
  assert.equal(element.visible, false); assert.equal(element.enabled, false); assert.equal(element.editable, false)
  assert.equal(h.matchCountSummary.value, '0'); assert.deepEqual(h.getTextSnippets(element), ['Text'])
  assert.equal(h.formatBoundingBox(element.bounding_box), 'x:0 y:0 w:0 h:1'); assert.equal(JSON.stringify(source), before)
  h.props.result = { id: 1, loc: [{ type: 0, expression: '#array', sub: 0 }, '.text'], exp: [0, 0] }
  assert.equal(h.elementRows.value[0].locators[0].loc, '#array'); assert.equal(h.elementRows.value[0].locators[1].exp, 0)
})

for (const key of ['elements', 'element_result', 'element_list', 'element']) {
  test(`${key} 旧元素格式转有限类型，未知数量不再计算为0`, t => {
    const h = setup('UiStepRuntimeResult', runtimeBindings, { result: { id: 0, [key]: [null, { name: key, loc: '#example', ele_quantity: null }] } }); t.after(h.close)
    assert.equal(h.elementRows.value.length, 1); assert.equal(h.elementRows.value[0].name, key)
    assert.equal(h.matchCountSummary.value, '-')
    assert.equal(h.elementRows.value[0].locators[0].loc, '#example')
  })
}

test('运行态优先于配置定位；无结果时保留原有空态，配置不冒充执行结果', t => {
  const h = setup('UiStepRuntimeResult', runtimeBindings, { result: { id: 1 }, fallbackElement: { name: 'Configured', loc3: '#configured', exp3: 0, sub3: 0 }, fallbackOpeKey: 'click' }); t.after(h.close)
  assert.equal(h.elementRows.value[0].__configuredFallback, true); assert.equal(h.getElementLocatorRows(h.elementRows.value[0])[0].sub, 0)
  assert.equal(h.resultElementRows.value.length, 0); assert.equal(h.operationLabel.value, '点击操作')
  h.props.result = { id: 1, ele_name: { name: 'Actual', loc: '#actual' } }
  assert.equal(h.elementRows.value[0].name, 'Actual'); assert.equal(h.elementRows.value[0].__configuredFallback, false)
  h.props.result = null; assert.equal(h.hasResult.value, false)
})

test('定位候选和 viewport 采用有限字段，评分0/数量0保留，非法嵌套不进入模板', t => {
  const h = setup('UiStepRuntimeResult', runtimeBindings, { result: { id: 1, viewport: { w: 0, h: 100 }, locator_engine: {
    used_source: 'rules', candidate_count: 0, temporary_heal_used: false, candidates: [null, { loc: '#example', count: 0, final_score: 0, verified: true, decision_status: 'auto_apply', decision_reasons: ['reason', {}] }, { verified: false, final_score: {} }],
  } } }); t.after(h.close)
  assert.equal(h.formatViewport(h.result.value.viewport), '0 × 100'); assert.match(h.locatorEngineSummary.value, /候选 0/)
  assert.equal(h.locatorCandidateRows.value.length, 2); assert.equal(h.locatorCandidateRows.value[0].final_score, 0)
  assert.deepEqual(h.locatorCandidateRows.value[0].decision_reasons, ['reason'])
  assert.equal(h.getCandidateStatus(h.locatorCandidateRows.value[0]).text, '已采用')
  assert.equal(h.getCandidateStatus(h.locatorCandidateRows.value[1]).text, '验证失败')
  assert.equal(h.locatorCandidateRows.value[1].final_score, null)
})

test('父子重复归一化不丢定位和元素名；动态字段不透传，冻结原始证据不修改', t => {
  const h = setup('UiStepRuntimeResult', runtimeBindings); t.after(h.close)
  const source = Object.freeze({ id: 0, ele_name: Object.freeze({ name: 'Element', loc: '#example', exp: 0 }), other: { private: true } })
  const first = h.models.normalizeUiRuntime(source), second = h.models.normalizeUiRuntime(first)
  assert.deepEqual(second, first); assert.equal(second.elementName, 'Element'); assert.equal(second.elements[0].locators[0].loc, '#example')
  assert.equal('other' in first, false)
})

for (const key of ['steps', 'element_result_list', 'children']) {
  test(`${key} 报告格式正确计算时间线、通过率和非连续枚举，重复ID key不冲突`, t => {
    const h = setup('ElementTestReport', reportBindings, { resultData: { name: 'Example', status: 0, [key]: [
      { id: 0, type: 7, status: 0, picture_path: 'failed.png', element_result_list: [{ id: 0, status: 1, stop_time: '2026-01-01 10:11:12' }, { id: 0, status: 0 }] },
      { id: 0, children: [{ id: 0, status: 3 }] },
    ] } }); t.after(h.close)
    assert.equal(h.operationTotal.value, 3); assert.equal(h.passedCount.value, 1); assert.equal(h.failedCount.value, 1); assert.equal(h.pendingCount.value, 1); assert.equal(h.passRate.value, 33)
    assert.equal(h.operationLabel(h.stepList.value[0]), '点击'); assert.equal(h.firstFailedPictureUrl.value, 'https://example.com/failed.png')
    assert.equal(new Set(h.timelineRows.value.map(h.timelineRowKey)).size, 3)
    assert.equal(h.timelineLabel(h.timelineRows.value[0].runtime), '10:11:12')
    h.props.resultData = { steps: [false, null], children: [{ id: 999 }] }; assert.equal(h.operationTotal.value, 0)
  })
}

test('缓存0/false保留；切换证据、身份/环境/路由及后台或缓存停用关闭缓存窗口', async t => {
  const h = setup('ElementTestReport', reportBindings, { resultData: { cache_data: false, data_factory_cache_data: 0 } }); t.after(h.close)
  assert.equal(h.runtimeSections.value.length, 2)
  for (const field of ['userId', 'roleId', 'token', 'selected_environment']) {
    h.cachePanelVisible.value = true; h.user[field] = field === 'token' ? 'example' : 2
    assert.equal(h.cachePanelVisible.value, false)
  }
  h.cachePanelVisible.value = true; h.route.fullPath = '/report/index'; assert.equal(h.cachePanelVisible.value, false)
  h.cachePanelVisible.value = true; h.props.resultData = { cache_data: 'new' }; assert.equal(h.cachePanelVisible.value, false)
  h.cachePanelVisible.value = true; h.doc.visibilityState = 'hidden'; h.doc.dispatchEvent(new Event('visibilitychange')); assert.equal(h.cachePanelVisible.value, false)
  h.cachePanelVisible.value = true; h.lifecycle.deactivate.forEach(fn => fn()); assert.equal(h.cachePanelVisible.value, false)
  await flush()
})

test('UI 用例结果边界区分无记录/无结果，错误正文只接收字符串', t => {
  const h = setup('UiCaseExecutionResult', 'detail,resultData,executionError', { detail: null }); t.after(h.close)
  assert.equal(h.detail.value, null); assert.equal(h.resultData.value, null)
  h.props.detail = { error_message: 'execution error', result_data: { error_message: 'nested' } }
  assert.equal(h.executionError.value, 'execution error')
  h.props.detail = { error_message: {}, result_data: { error_message: 'nested' } }; assert.equal(h.executionError.value, 'nested')
  h.props.detail = { result_data: [] }; assert.equal(h.resultData.value, null); assert.equal(h.executionError.value, '')
})

test('三层结果组件及真实调用方 SFC/模板/样式可编译', async () => {
  const files = ['src/components/reports/ElementTestReport.vue', 'src/components/reports/UiStepRuntimeResult.vue', 'src/components/reports/UiCaseExecutionResult.vue',
    'src/components/reports/TestReportResultDrawer.vue', 'src/views/uitest/case/details/index.vue', 'src/views/uitest/page-steps/details/index.vue', 'src/views/report/details/components/ReportExecutionResultDrawer.vue']
  for (const file of files) {
    const { descriptor, errors } = parse(readFileSync(file, 'utf8'), { filename: file }); assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: file })
    const template = compileTemplate({ id: file, filename: file, source: descriptor.template.content, compilerOptions: { bindingMetadata: script.bindings } })
    assert.deepEqual(template.errors, [], file)
    for (const style of descriptor.styles) {
      const result = await compileStyleAsync({ id: file, filename: file, source: style.content, scoped: style.scoped, preprocessLang: style.lang })
      assert.deepEqual(result.errors, [], file)
    }
  }
})
