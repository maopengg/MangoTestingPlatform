import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/index')
const project = (id = 0) => ({ project_id: id, project_name: 'Example project', report_count: 4, success_count: 0, fail_count: 1, warning_count: 1, other_count: 2, pass_rate: 0 })
const counts = () => ({ success: 0, fail: 1, warning: 1, proceed: 2, stay_begin: 3, stopped: 4 })
const reports = () => ({ code: 200, data: { status_counts: counts(), final_pass_rate: 0 } })
function page(api = {}) {
  const hooks = { mount: [], activate: [], deactivate: [], unmount: [] }, errors = [], pushes = []
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'test-token', selected_environment: 0 })
  const route = vue.reactive({ path: '/index/home', fullPath: '/index/home' })
  const p = harness('index', 'projectQualityRows,projectQualityLoading,projectQualityError,reportCounts,reportPassRate,reportSumLoading,reportSumError,reportOtherCount,loadProjectQuality,loadReportSummary,contactVisible,skillVisible,viewSkill,contactAuthor,navigateTo,navigatingTo', {
    filename: path.join(base, 'main.vue'), base,
    api: { getSystemProjectQuality: async () => ({ code: 200, data: [project()] }), getSystemCaseRunSum: async () => reports(), ...api },
    modules: {
      vue: { ...vue, onMounted: fn => hooks.mount.push(fn), onActivated: fn => hooks.activate.push(fn), onDeactivated: fn => hooks.deactivate.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) },
      'vue-router': { useRouter: () => ({ push: target => { pushes.push(target); return api.navigate?.(target) } }), useRoute: () => route },
      '@/store/modules/user': { default: () => user },
      '@arco-design/web-vue': { Message: { error: message => errors.push(message) } },
    },
  })
  return { ...p, user, route, errors, pushes, mount: () => hooks.mount.forEach(fn => fn()), activate: () => hooks.activate.forEach(fn => fn()), deactivate: () => hooks.deactivate.forEach(fn => fn()), unmount: () => hooks.unmount.forEach(fn => fn()) }
}

test('两块聚合数据分别结束 loading，保留 ID 0 与通过率 0，不共享页面状态', async () => {
  const quality = deferred(), sum = deferred()
  const p = page({ getSystemProjectQuality: () => quality.promise, getSystemCaseRunSum: () => sum.promise }), other = page()
  p.mount(); other.mount(); await flush()
  assert.equal(p.projectQualityLoading.value, true); assert.equal(p.reportSumLoading.value, true)
  quality.resolve({ code: 200, data: [project()] }); await flush()
  assert.equal(p.projectQualityRows.value[0].project_id, 0); assert.equal(p.projectQualityLoading.value, false); assert.equal(p.reportSumLoading.value, true)
  sum.resolve(reports()); await flush()
  assert.equal(p.reportPassRate.value, 0); assert.equal(p.reportOtherCount.value, 9)
  p.reportCounts.value.success = 99; assert.equal(other.reportCounts.value.success, 0)
  p.close(); other.close()
})

test('失败保留本分区旧数据并提供重试，重试成功清除错误', async () => {
  let fail = false
  const p = page({ getSystemProjectQuality: async () => fail ? { code: 500 } : { code: 200, data: [project()] } })
  p.mount(); await flush(); fail = true; await p.loadProjectQuality()
  assert.ok(p.projectQualityError.value); assert.equal(p.projectQualityLoading.value, false)
  assert.equal(p.projectQualityRows.value.length, 1); assert.equal(p.reportSumError.value, '')
  fail = false; await p.loadProjectQuality(); assert.equal(p.projectQualityError.value, ''); p.close()
})

test('仅最新聚合读取可写入数据/loading，旧失败不覆盖新结果', async () => {
  const first = deferred(), second = deferred(); let calls = 0
  const p = page({ getSystemProjectQuality: () => ++calls === 1 ? first.promise : second.promise })
  p.mount(); const work = p.loadProjectQuality()
  first.reject(Error('old failure')); await flush(); assert.equal(p.projectQualityLoading.value, true); assert.equal(p.projectQualityError.value, '')
  second.resolve({ code: 200, data: [project(2)] }); await work
  assert.equal(p.projectQualityRows.value[0].project_id, 2); assert.equal(p.projectQualityLoading.value, false); p.close()
})

for (const field of ['userId', 'roleId', 'token', 'selected_environment']) {
  test(`${field} 同步 A-B-A 清除两区及窗口，旧响应不复活`, async () => {
    const requests = []
    const p = page({ getSystemProjectQuality: () => { const r = deferred(); requests.push(r); return r.promise } })
    p.mount(); await flush(); p.contactAuthor(); p.viewSkill()
    const initial = p.user[field]; p.user[field] = field === 'token' ? 'another' : 9; p.user[field] = initial
    assert.equal(requests.length, 3); assert.equal(p.projectQualityRows.value.length, 0)
    assert.equal(p.contactVisible.value, false); assert.equal(p.skillVisible.value, false)
    requests[0].resolve({ code: 200, data: [project(1)] }); requests[1].reject(Error('old')); await flush()
    assert.equal(p.projectQualityRows.value.length, 0); assert.equal(p.projectQualityLoading.value, true)
    requests[2].resolve({ code: 200, data: [project(3)] }); await flush()
    assert.equal(p.projectQualityRows.value[0].project_id, 3); assert.equal(p.projectQualityError.value, ''); p.close()
  })
}

test('切到其他路由不发起首页读取，返回及 KeepAlive 激活重读且不重复初始请求', async () => {
  let calls = 0
  const p = page({ getSystemProjectQuality: async () => { calls++; return { code: 200, data: [] } } })
  p.mount(); p.activate(); await flush(); assert.equal(calls, 1)
  p.route.path = '/other'; p.route.fullPath = '/other'; await flush(); assert.equal(calls, 1)
  p.deactivate(); p.route.path = '/index/home'; p.route.fullPath = '/index/home'; await flush(); assert.equal(calls, 1)
  p.activate(); await flush(); assert.equal(calls, 2); p.close()
})

test('停用或卸载后迟到聚合不落地，关闭窗口且结束区域 loading', async () => {
  for (const stop of [p => p.deactivate(), p => p.unmount()]) {
    const request = deferred(), p = page({ getSystemProjectQuality: () => request.promise })
    p.mount(); p.viewSkill(); stop(p); request.resolve({ code: 200, data: [project()] }); await flush()
    assert.equal(p.projectQualityRows.value.length, 0); assert.equal(p.projectQualityLoading.value, false); assert.equal(p.skillVisible.value, false); p.close()
  }
})

test('导航防重复、失败恢复，身份变化后不弹出迟到导航错误', async () => {
  const request = deferred(), p = page({ navigate: () => request.promise })
  const work = p.navigateTo('/report/index'); await p.navigateTo('/report/index')
  assert.deepEqual(p.pushes, ['/report/index']); assert.equal(p.navigatingTo.value, '/report/index')
  p.user.roleId = 9; request.reject(Error('old')); await work
  assert.equal(p.navigatingTo.value, null); assert.equal(p.errors.length, 0); p.close()
  const failure = page({ navigate: async () => { throw Error('failed') } })
  await failure.navigateTo('/report/index'); assert.equal(failure.errors.length, 1); assert.equal(failure.navigatingTo.value, null); failure.close()
})

test('聚合映射保留原指标口径和已有旧列表协议，畸形响应不作为空数据', () => {
  const p = page(), records = p.load('records.ts')
  assert.deepEqual(records.readReportSummary(reports()), { counts: counts(), passRate: 0 })
  const legacy = records.readReportSummary({ code: 200, data: [{ name: '通过', value: 1 }, { name: '失败', value: 1 }, { name: '进行中', value: 3 }] })
  assert.equal(legacy.passRate, 50); assert.equal(legacy.counts.proceed, 3); assert.equal(legacy.counts.stopped, 0)
  assert.equal(records.readReportSummary({ code: 200, data: [] }).passRate, null)
  assert.equal(records.formatPercent(0), '0.00%'); assert.equal(records.formatPercent(null), '-')
  for (const response of [{ code: 500, data: [] }, { code: 200, data: {} }, { code: 200, data: { status_counts: { ...counts(), fail: 'bad' } } }]) assert.throws(() => records.readReportSummary(response))
  const row = { ...project(), hidden: 'not a chart field' }
  const parsed = records.readProjectQuality({ code: 200, data: [row] }); row.report_count = 9
  assert.equal(parsed[0].report_count, 4); assert.equal('hidden' in parsed[0], false)
  assert.throws(() => records.readProjectQuality({ code: 200, data: null })); p.close()
})

test('本阶段主页面及项目图表 SFC 编译通过', () => {
  for (const filename of [path.join(base, 'main.vue'), path.join(base, 'components/chart/ProjectQualityChart.vue')]) {
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename }); assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: filename })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: filename, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    for (const style of descriptor.styles) assert.deepEqual(compileStyle({ source: style.content, filename, id: filename, scoped: style.scoped, preprocessLang: style.lang }).errors, [])
  }
})
