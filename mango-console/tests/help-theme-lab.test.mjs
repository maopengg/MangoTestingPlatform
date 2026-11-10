import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

function lab(router = {}) {
  const deactivate = [], activate = [], unmount = []
  const page = harness('index', 'formModel,resetFilters,drawerForm,drawerSaved,drawerVisible,openDrawer,cancelDrawer,saveDrawer,modalVisible,tableFilter,rows,displayedRows,onCustomColumnsUpdate,visibleCustomColumns,tableConfigState,goBack,navigationLoading', {
    base: path.resolve('src/views/help'), filename: path.resolve('src/views/help/test.vue'),
    modules: { 'vue-router': { useRouter: () => router }, vue: { ...vue, onDeactivated: fn => deactivate.push(fn), onActivated: fn => activate.push(fn) } },
  })
  return { ...page, deactivate: () => deactivate.forEach(fn => fn()) }
}

test('筛选重置创建独立数组，两个页面实例不互相污染', () => {
  const a = lab(), b = lab()
  a.formModel.tags.push('changed'); a.formModel.retry = 0; a.formModel.notice = false
  assert.deepEqual([...b.formModel.tags], ['冒烟', 'P0'])
  a.resetFilters()
  assert.deepEqual([...a.formModel.tags], ['冒烟', 'P0'])
  assert.equal(a.formModel.retry, 2)
  assert.equal(a.formModel.notice, true)
  a.close(); b.close()
})

test('抽屉取消与重开恢复快照，保存只更新本地示例，停用关闭浮层', () => {
  const p = lab()
  p.openDrawer(); p.drawerForm.name = 'discard'; p.cancelDrawer(); p.openDrawer()
  assert.equal(p.drawerForm.name, '每日冒烟测试')
  p.drawerForm.name = 'saved'; p.drawerForm.mode = 'serial'; p.drawerForm.failNotice = false; p.saveDrawer()
  p.openDrawer(); assert.deepEqual({ ...p.drawerForm }, { name: 'saved', mode: 'serial', failNotice: false })
  p.drawerForm.name = 'discard'; p.modalVisible.value = true; p.deactivate()
  assert.equal(p.drawerVisible.value, false); assert.equal(p.modalVisible.value, false)
  assert.equal(p.drawerForm.name, 'saved'); p.close()
})

test('样例行筛选与开关保持实例隔离，列更新不保留子组件可变对象', () => {
  const a = lab(), b = lab()
  a.tableFilter.value = 'fail'
  assert.deepEqual(a.displayedRows.value.map(row => row.id), ['10422'])
  a.tableFilter.value = 'success'
  assert.deepEqual(a.displayedRows.value.map(row => row.id), ['10421'])
  a.rows.value[0].enabled = false
  assert.equal(b.rows.value[0].enabled, true)
  const input = [{ title: 'Column', key: 'name', sortIndex: 0, checked: true }]
  a.onCustomColumnsUpdate(input); input[0].title = 'changed'
  assert.equal(a.visibleCustomColumns.value[0].title, 'Column')
  assert.equal(a.tableConfigState.value, '已显示 1 列'); a.close(); b.close()
})

test('返回首页等待导航、阻止重复，失败后恢复，停用不发起导航', async () => {
  const original = globalThis.window, pending = deferred(), calls = []
  globalThis.window = { history: { state: {} } }
  const p = lab({ push: target => { calls.push(target); return pending.promise } })
  try {
    const navigation = p.goBack(); await p.goBack()
    assert.equal(p.navigationLoading.value, true); assert.deepEqual(calls, ['/index/home'])
    pending.reject(Error('navigation failed')); await navigation
    assert.equal(p.navigationLoading.value, false)
    p.deactivate(); await p.goBack(); assert.equal(calls.length, 1)
  } finally { p.close(); globalThis.window = original }
})

test('存在历史入口时使用 router.back，不额外跳首页', async () => {
  const original = globalThis.window, calls = []
  globalThis.window = { history: { state: { back: '/previous' } } }
  const p = lab({ back: () => calls.push('back'), push: () => calls.push('push') })
  try { await p.goBack(); assert.deepEqual(calls, ['back']); assert.equal(p.navigationLoading.value, false) }
  finally { p.close(); globalThis.window = original }
})

function ai(request) {
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'test-token', selected_environment: 0 })
  const route = vue.reactive({ fullPath: '/help/test' })
  const deactivate = [], activate = [], unmount = []
  const p = harness('index', 'open,analyze,invalidateAnalysis,visible,loading,analysis,deterministicSummary', {
    filename: path.resolve('src/components/feedback/AssertionAiAnalysis.vue'),
    props: { data: [{ method: '等于', actual: 0, expect: false, status: 0, ass_msg: 'failed' }] },
    api: { postAssertionAiAnalysis: request },
    modules: {
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user },
      vue: { ...vue, onDeactivated: fn => deactivate.push(fn), onBeforeUnmount: fn => unmount.push(fn), onActivated: fn => activate.push(fn) },
    },
  })
  return { ...p, user, route, deactivate: () => deactivate.forEach(fn => fn()), activate: () => activate.forEach(fn => fn()), unmount: () => unmount.forEach(fn => fn()) }
}
const result = { available: true, reason: '', summary: 'done', failed_count: 1, analyzed_count: 1, omitted_count: 0, items: [] }

test('AI 分析发送固定断言快照并阻止重复请求；失败后可重试', async () => {
  let count = 0, snapshot
  const request = deferred()
  const p = ai(data => { count++; snapshot = data; return request.promise })
  p.open(); await p.analyze()
  assert.equal(count, 1); assert.equal(p.loading.value, true)
  assert.equal(snapshot[0].actual, 0); assert.equal(snapshot[0].expect, false)
  p.props.data[0].actual = 5
  assert.equal(snapshot[0].actual, 0)
  request.reject(Error('failure')); await flush()
  assert.equal(p.loading.value, false); assert.equal(p.analysis.value, null)
  p.close()
  let calls = 0
  const retry = ai(async () => { if (++calls === 1) throw Error('failed'); return { code: 200, data: result } })
  retry.open(); await flush(); assert.equal(retry.analysis.value.available, false)
  await retry.analyze(); assert.equal(calls, 2); assert.equal(retry.analysis.value.summary, 'done'); retry.close()
})

for (const key of ['userId', 'roleId', 'token', 'selected_environment']) {
  test(`AI ${key} 同步 A-B-A 切换抑制旧响应且请求结束前不解锁`, async () => {
    const request = deferred(); let count = 0
    const p = ai(() => { count++; return request.promise })
    p.open(); const before = p.user[key]; p.user[key] = key === 'token' ? 'other' : 9; p.user[key] = before
    p.open(); assert.equal(count, 1); assert.equal(p.loading.value, true)
    request.resolve({ code: 200, data: result }); await flush()
    assert.equal(p.analysis.value, null); assert.equal(p.loading.value, false); p.close()
  })
}

test('AI 关闭、切页、KeepAlive 停用及返回均不接收迟到结果', async () => {
  for (const invalidate of [p => p.invalidateAnalysis(), p => p.unmount(), p => { p.route.fullPath = '/elsewhere'; p.route.fullPath = '/help/test' }, p => { p.deactivate(); p.activate() }]) {
    const request = deferred(); const p = ai(() => request.promise)
    p.open(); invalidate(p); request.resolve({ code: 200, data: result }); await flush()
    assert.equal(p.visible.value, false); assert.equal(p.analysis.value, null); assert.equal(p.loading.value, false); p.close()
  }
})

function sortable() {
  const filename = 'src/components/table/SortableTable.vue', hooks = [], ticks = [], instances = [], events = []
  const descriptor = parse(readFileSync(filename, 'utf8')).descriptor
  class Sortable { constructor(element, options) { this.element = element; this.options = options; this.destroyed = false; instances.push(this) } destroy() { this.destroyed = true } }
  const exports = {}
  new Function('exports', 'require', ts.transpileModule(descriptor.script.content, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText)(exports, id => {
    if (id === 'vue') return { ...vue, defineComponent: value => value, nextTick: fn => ticks.push(fn), onDeactivated: fn => hooks.push(fn), onBeforeUnmount: fn => hooks.push(fn) }
    if (id === 'sortablejs') return { default: Sortable }
    if (id === 'lodash-es') return { cloneDeep: value => JSON.parse(JSON.stringify(value)), isUndefined: value => value === undefined }
    throw Error(id)
  })
  const columns = [{ title: 'A', key: 'a', checked: true, sortIndex: 0 }, { title: 'B', key: 'b', checked: true, sortIndex: 1 }]
  const p = exports.default.setup({ columns }, { emit: (...args) => events.push(args) })
  p.sortColumnWrapper.value = { id: 'local' }
  return { ...p, instances, events, tick: () => { while (ticks.length) ticks.shift()() }, stop: () => hooks.forEach(fn => fn()) }
}

test('列排序组件仅创建本实例拖拽，关闭前 nextTick、重开和停用销毁正确', () => {
  const a = sortable(), b = sortable()
  a.onPopVisibleChange(true); a.onPopVisibleChange(false); a.tick(); assert.equal(a.instances.length, 0)
  a.onPopVisibleChange(true); a.tick(); b.onPopVisibleChange(true); b.tick()
  assert.notEqual(a.instances[0].element, b.instances[0].element)
  a.instances[0].options.onEnd({ oldIndex: 0, newIndex: 1 })
  assert.deepEqual(a.events[0][1].map(column => column.key), ['b', 'a'])
  assert.equal(b.events.length, 0)
  a.onPopVisibleChange(true); a.tick(); assert.equal(a.instances[0].destroyed, true)
  a.instances[0].options.onEnd({ oldIndex: 0, newIndex: 1 }); assert.equal(a.events.length, 1)
  a.stop(); b.stop(); assert.equal(a.instances[1].destroyed, true); assert.equal(b.instances[0].destroyed, true)
  assert.equal(a.popupVisible.value, false); assert.equal(b.popupVisible.value, false)
})

test('密码强度首次回显即更新，清空后不残留旧等级', async () => {
  const p = harness('index', 'tipValue,stronger', {
    filename: path.resolve('src/components/forms/PasswordStrong.vue'),
    props: { inputValue: 'Mango2026', lowReg: /^[0-9]{6,16}$|^[a-zA-Z]{6,16}$/, middleReg: /^[A-Za-z0-9]{6,16}$/, strongReg: /^\w{6,16}$/ },
  })
  assert.equal(p.tipValue.value, '中')
  p.props.inputValue = ''; await flush()
  assert.equal(p.tipValue.value, '未输入')
  assert.deepEqual(p.stronger.map(item => item.status), ['normal', 'normal', 'normal'])
  p.close()
})

test('主题页及直接引用公共组件的 SFC 脚本/模板/样式编译通过', () => {
  for (const filename of ['src/views/help/test.vue', 'src/components/table/SortableTable.vue', 'src/components/table/TableConfig.vue', 'src/components/feedback/AssertionAiAnalysis.vue', 'src/components/feedback/AssertionResult.vue', 'src/components/forms/PasswordStrong.vue', 'src/components/feedback/TipMessage.vue', 'src/components/table/MangoTableActions.vue']) {
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(errors, [], filename)
    const script = compileScript(descriptor, { id: filename })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: filename, compilerOptions: { bindingMetadata: script.bindings } }).errors, [], filename)
    for (const style of descriptor.styles) assert.deepEqual(compileStyle({ source: style.content, filename, id: filename, scoped: style.scoped, preprocessLang: style.lang }).errors, [], filename)
  }
})
