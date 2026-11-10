import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/help/variable'), lossless = {}
new Function('exports', 'require', ts.transpileModule(readFileSync('src/utils/lossless-json.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText)(lossless, createRequire(import.meta.url))
const method = (value = 'example', parameter = null) => ({ value, label: value, parameter })
const tree = () => [
  { value: 'data', label: 'Data', children: [
    { value: 'other', label: 'Other', children: [method()] },
    { value: '人物信息测试数据', label: 'People', children: [method('person')] },
  ] },
  { value: 'performance', label: 'Performance', children: [{ value: 'perf', label: 'Perf', children: [method('perf_uuid')] }] },
  { value: 'cache', label: 'Cache', children: [{ value: 'cache', label: 'Cache', children: [method('cache_get')] }] },
]
function page(api = {}, mount = true) {
  const notifications = [], warnings = [], hooks = { mounted: [], activated: [], deactivated: [], unmount: [] }
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'test-token', selected_environment: 0 })
  const route = vue.reactive({ fullPath: '/help/variable/index' })
  const p = harness('index', 'randomList,input,activeGroupValue,classGroups,menuSections,currentClassGroup,catalogLoading,catalogError,loadCatalog,testing,testError,lastExpression,obtain,retryTest,selectGroup', {
    base,
    api: { getSystemRandomList: async () => ({ code: 200, data: tree() }), getSystemRandomData: async () => ({ code: 200, data: 'generated' }), ...api },
    modules: {
      vue: { ...vue, onMounted: fn => hooks.mounted.push(fn), onActivated: fn => hooks.activated.push(fn), onDeactivated: fn => hooks.deactivated.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) },
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user },
      '@arco-design/web-vue': { Message: { warning: value => warnings.push(value) }, Notification: { success: value => notifications.push(value) } },
      '@/utils/lossless-json': lossless,
    },
  })
  if (mount) hooks.mounted.forEach(fn => fn())
  return { ...p, user, route, notifications, warnings, deactivate: () => hooks.deactivated.forEach(fn => fn()), activate: () => hooks.activated.forEach(fn => fn()), unmount: () => hooks.unmount.forEach(fn => fn()) }
}

test('目录默认人物分类，保留类型分组与空组过滤，实例不共享状态', async () => {
  const p = page(), other = page(); await flush()
  assert.equal(p.currentClassGroup.value.value, '人物信息测试数据')
  assert.deepEqual(p.menuSections.value.map(item => item.value), ['data', 'performance', 'tools'])
  p.selectGroup('cache:cache'); assert.equal(p.currentClassGroup.value.typeValue, 'cache')
  assert.equal(other.currentClassGroup.value.typeValue, 'data')
  p.close(); other.close()
})

test('目录仅最新请求更新数据/loading，旧失败不覆盖新结果', async () => {
  const first = deferred(), second = deferred(); let calls = 0
  const p = page({ getSystemRandomList: () => (++calls === 1 ? first.promise : second.promise) })
  const latest = p.loadCatalog(); second.resolve({ code: 200, data: tree() }); await latest
  assert.equal(p.catalogLoading.value, false); assert.equal(p.randomList.value.length, 3)
  first.reject(Error('old failure')); await flush()
  assert.equal(p.catalogError.value, ''); assert.equal(p.randomList.value.length, 3); p.close()
})

test('目录失败可重试，已加载目录保留；错误响应与合法空目录区分', async () => {
  let fail = false
  const p = page({ getSystemRandomList: async () => fail ? { code: 500, data: [] } : { code: 200, data: tree() } })
  await flush(); fail = true; await p.loadCatalog()
  assert.ok(p.catalogError.value); assert.equal(p.randomList.value.length, 3); assert.equal(p.catalogLoading.value, false)
  fail = false; await p.loadCatalog(); assert.equal(p.catalogError.value, '')
  p.close()
  const empty = page({ getSystemRandomList: async () => ({ code: 200, data: [] }) }); await flush()
  assert.equal(empty.catalogError.value, ''); assert.equal(empty.currentClassGroup.value, undefined); empty.close()
})

for (const key of ['userId', 'roleId', 'token', 'selected_environment']) {
  test(`目录 ${key} 同步 A-B-A 仅接受当前代响应`, async () => {
    const requests = []
    const p = page({ getSystemRandomList: () => { const request = deferred(); requests.push(request); return request.promise } })
    const before = p.user[key]; p.user[key] = key === 'token' ? 'other' : 9; p.user[key] = before
    assert.equal(requests.length, 3)
    requests[0].resolve({ code: 200, data: tree() }); await flush(); assert.equal(p.randomList.value.length, 0)
    assert.equal(p.catalogLoading.value, true)
    requests[2].resolve({ code: 200, data: tree() }); await flush(); assert.equal(p.randomList.value.length, 3)
    requests[1].reject(Error('old')); await flush(); assert.equal(p.catalogError.value, ''); p.close()
  })
}

test('目录 KeepAlive 停用失效，返回重新读取，重复激活不重复初始加载', async () => {
  const pending = deferred(); let calls = 0
  const p = page({ getSystemRandomList: () => ++calls === 1 ? pending.promise : Promise.resolve({ code: 200, data: tree() }) })
  p.activate(); assert.equal(calls, 1)
  p.deactivate(); pending.resolve({ code: 200, data: tree() }); await flush()
  assert.equal(p.randomList.value.length, 0); assert.equal(p.catalogLoading.value, false)
  p.activate(); await flush(); assert.equal(calls, 2); assert.equal(p.randomList.value.length, 3); p.close()
})

test('试验固定表达式且防重复，目录加载与试验可独立结束', async () => {
  const catalog = deferred(), generate = deferred(), expressions = []
  const p = page({ getSystemRandomList: () => catalog.promise, getSystemRandomData: expression => { expressions.push(expression); return generate.promise } })
  const request = p.obtain('${{ example(0, false)|cache_key }}'); await p.obtain('other()')
  assert.deepEqual(expressions, ['${{example(0, false)|cache_key}}']); assert.equal(p.testing.value, true)
  catalog.resolve({ code: 200, data: tree() }); await flush()
  assert.equal(p.catalogLoading.value, false); assert.equal(p.testing.value, true)
  generate.resolve({ code: 200, data: '' }); await request
  assert.equal(p.notifications.length, 1); assert.equal(p.notifications[0].content, ''); assert.equal(p.testing.value, false); p.close()
})

test('空表达式不请求；业务错误与畸形生成响应不报告成功；重试使用原试验表达式', async () => {
  const expressions = []; let valid = false
  const p = page({ getSystemRandomData: async expression => { expressions.push(expression); return valid ? { code: 200, data: '0' } : { code: 500, data: 'failed' } } })
  p.input.value = ''; await p.obtain(); assert.equal(expressions.length, 0); assert.equal(p.warnings.length, 1)
  await p.obtain('row_method()'); assert.ok(p.testError.value); assert.equal(p.testing.value, false)
  valid = true; p.retryTest(); await flush()
  assert.deepEqual(expressions, ['${{row_method()}}', '${{row_method()}}'])
  assert.equal(p.notifications[0].content, '0'); p.close()
  const malformed = page({ getSystemRandomData: async () => ({ code: 200, data: { value: 1 } }) })
  await malformed.obtain('example()'); assert.ok(malformed.testError.value); assert.equal(malformed.notifications.length, 0); malformed.close()
})

test('输入 A-B-A、上下文切换、关闭嵌入窗口和 KeepAlive 返回不弹出旧通知，物理锁保留至请求结束', async () => {
  const invalidations = [
    p => { const before = p.input.value; p.input.value = 'other()'; p.input.value = before },
    p => { p.route.fullPath = '/other'; p.route.fullPath = '/help/variable/index' },
    p => { p.user.roleId = 9; p.user.roleId = 2 },
    p => { p.user.selected_environment = 3; p.user.selected_environment = 0 },
    p => { p.deactivate(); p.activate() }, p => p.unmount(),
  ]
  for (const invalidate of invalidations) {
    const request = deferred(); let calls = 0
    const p = page({ getSystemRandomData: () => { calls++; return request.promise } }); await flush()
    const work = p.obtain('example()'); invalidate(p); await p.obtain('other()')
    assert.equal(calls, 1); assert.equal(p.testing.value, true)
    request.resolve({ code: 200, data: 'old result' }); await work
    assert.equal(p.notifications.length, 0); assert.equal(p.testError.value, ''); assert.equal(p.testing.value, false); p.close()
  }
})

test('真实目录解析和示例转换保留零/false、无损数字及旧对象参数顺序', () => {
  const p = page({}, false), records = p.load('records.ts')
  const response = { code: 200, data: [{ value: 'data', label: 'Data', children: [{ value: 'group', label: 'Group', children: [method('sample', [{ f: 'left', v: 0 }, { f: 'flag', v: false }, { f: 'length', v: null }])] }] }] }
  const item = records.readCatalog(response)[0].children[0].children[0]
  assert.equal(records.buildExample(item), 'sample(0, false, 8)')
  response.data[0].children[0].children[0].parameter[0].v = 9
  assert.equal(item.parameter[0].v, 0)
  const exact = new lossless.LosslessJsonNumber('9007199254740993')
  response.data[0].children[0].children[0].parameter = [{ f: 'id', v: exact }]
  assert.equal(records.buildExample(records.readCatalog(response)[0].children[0].children[0]), 'sample(9007199254740993)')
  response.data[0].children[0].children[0].parameter = { length: null, extension: 'json' }
  assert.equal(records.buildExample(records.readCatalog(response)[0].children[0].children[0]), 'sample(8, json)')
  assert.throws(() => records.readCatalog({ code: 200, data: [{ children: 'bad' }] }))
  p.close()
})

test('方法表格 cache/json 保持只读，加载/试验禁用时不发送事件，类型变化更新列宽', () => {
  const group = { menuKey: 'data:g', typeValue: 'data', typeLabel: 'Data', value: 'g', label: 'G', children: [{ value: 'example', label: 'Example', parameter: [] }] }
  const p = harness('MethodClassCard', 'select,columns,scrollX', { base, props: { group, disabled: true, loading: false }, modules: { '@/utils/lossless-json': lossless } })
  p.select(p.props.group.children[0]); assert.equal(p.events.length, 0)
  p.props.disabled = false; p.props.loading = true; p.select(p.props.group.children[0]); assert.equal(p.events.length, 0)
  p.props.loading = false; p.select(p.props.group.children[0]); assert.deepEqual(p.events[0], ['test', 'example()'])
  assert.equal(p.columns.value.at(-1).width, 120); assert.equal(p.scrollX.value, 1120)
  p.props.group.typeValue = 'cache'; p.select(p.props.group.children[0]); assert.equal(p.events.length, 1)
  assert.equal(p.columns.value.length, 3); assert.equal(p.scrollX.value, 740); p.close()
})

test('主页面、方法表格及嵌入外壳 SFC 脚本/模板/LESS 编译通过', () => {
  for (const filename of [path.join(base, 'index.vue'), path.join(base, 'components/MethodClassCard.vue'), path.resolve('src/components/business/VariableReferencePanel.vue')]) {
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(errors, [], filename)
    const script = compileScript(descriptor, { id: filename })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: filename, compilerOptions: { bindingMetadata: script.bindings } }).errors, [], filename)
    for (const style of descriptor.styles) assert.deepEqual(compileStyle({ source: style.content, filename, id: filename, scoped: style.scoped, preprocessLang: style.lang }).errors, [], filename)
  }
})
