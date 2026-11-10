import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'
import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/index')
const task = (id = 0) => ({
  id, name: `Task ${id}`, test_envs: [0], execution_scenes: ['regression'], execution_scope: null,
  latest_result_status: 0, next_run_at: '2026-11-07T12:00:00+08:00', next_run_time: '2026-11-07 12:00:00',
  seconds_until_run: 0, project_product: { name: 'Example product', project: { name: 'Example project' } },
  case_people: { id: 0, name: 'Example owner' }, timing_strategies: [{ id: 0, name: 'Example schedule', cron: '* * * * *' }],
})
const response = (ids, total = ids.length) => ({ code: 200, data: ids.map(task), totalSize: total })
function module(filename, dependencies = {}) {
  const exports = {}
  const source = ts.transpileModule(readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  new Function('exports', 'require', source)(exports, id => {
    if (!(id in dependencies)) { if (['@/utils/load-error', '@/utils/api-response'].includes(id)) return loadFeedbackModule(id); throw Error(`Unmocked module ${id}`) }
    return dependencies[id]
  })
  return exports
}
const pollingModule = module(path.resolve('src/utils/page-polling.ts'))
function panel(api = {}) {
  const hooks = { mount: [], activate: [], deactivate: [], unmount: [] }, timers = new Map(), listeners = new Set(), calls = []
  let timerId = 0
  const document = { visibilityState: 'visible', addEventListener: (_event, fn) => listeners.add(fn), removeEventListener: (_event, fn) => listeners.delete(fn) }
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'test-token', selected_environment: 0 })
  const route = vue.reactive({ path: '/index/home', fullPath: '/index/home' })
  const vueModule = { ...vue, onMounted: fn => hooks.mount.push(fn), onActivated: fn => hooks.activate.push(fn), onDeactivated: fn => hooks.deactivate.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) }
  const hookExports = {}
  const hookSource = ts.transpileModule(readFileSync('src/hooks/use-page-polling.ts', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
  new Function('exports', 'require', 'document', hookSource)(hookExports, id => ({
    '@/utils/load-error': loadFeedbackModule('@/utils/load-error'),
    vue: vueModule, 'vue-router': { useRoute: () => route },
    '@/utils/page-polling': { ...pollingModule, createPagePolling: (refresh, available) => pollingModule.createPagePolling(refresh, available, {
      setTimeout: (fn, delay) => { const id = ++timerId; timers.set(id, { fn, delay }); return id }, clearTimeout: id => timers.delete(id),
    }) },
  })[id], document)
  const p = harness('PendingTasks', 'dataList,loading,loadingMore,loadFailed,loadMoreFailed,page,total,fetchData,refresh,loadNextPage,handleScroll', {
    base, filename: path.join(base, 'components/PendingTasks.vue'),
    api: { getSystemIndexPendingTasks: args => { calls.push(args); return api.read ? api.read(args) : Promise.resolve(response([0])) } },
    modules: { vue: vueModule, 'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/hooks/use-page-polling': hookExports },
  })
  const dispose = p.close
  return { ...p, user, route, calls, timers, listeners,
    mount: () => hooks.mount.forEach(fn => fn()), activate: () => hooks.activate.forEach(fn => fn()),
    deactivate: () => hooks.deactivate.forEach(fn => fn()),
    visibility(value) { document.visibilityState = value; listeners.forEach(fn => fn()) },
    async tick() { const next = timers.entries().next().value; if (next) { timers.delete(next[0]); next[1].fn(); await flush() } },
    close() { hooks.unmount.forEach(fn => fn()); dispose() },
  }
}

test('初次加载与激活不重复请求；有限映射保留 0、null 并拒绝失败及畸形数据', async () => {
  const request = deferred(), p = panel({ read: () => request.promise })
  p.mount(); p.activate(); await p.tick()
  assert.equal(p.calls.length, 1); assert.equal(p.loading.value, true)
  request.resolve(response([0])); await flush()
  assert.equal(p.loading.value, false); assert.equal(p.dataList.value[0].latest_result_status, 0)
  assert.equal(p.dataList.value[0].execution_scope, null); assert.equal(p.dataList.value[0].case_people.id, 0)
  const records = p.load('records.ts'), raw = response([0]); raw.data[0].hidden = 'ignore'
  const result = records.readUpcomingTasks(raw); raw.data[0].test_envs.push(9)
  assert.deepEqual(result.rows[0].test_envs, [0]); assert.equal('hidden' in result.rows[0], false)
  assert.equal(records.readUpcomingTasks(response([], 0)).total, 0)
  for (const bad of [{ ...response([]), code: 500 }, { code: 200, data: {} }, { ...response([0]), totalSize: 'bad' }]) assert.throws(() => records.readUpcomingTasks(bad))
  p.close(); assert.equal(p.timers.size, 0); assert.equal(p.listeners.size, 0)
})

test('首次失败有局部错误，重试恢复；追加失败保留列表与页码并重试同一页', async () => {
  let fail = true
  const p = panel({ read: async ({ page }) => { if (fail) throw Error('failed'); return response(page === 1 ? [0, 1] : [1, 2, 2], 3) } })
  p.mount(); await flush(); assert.equal(p.loadFailed.value, true); assert.equal(p.loading.value, false)
  fail = false; await p.refresh(); fail = true; await p.loadNextPage()
  assert.equal(p.page.value, 1); assert.equal(p.loadMoreFailed.value, true); assert.deepEqual(p.dataList.value.map(row => row.id), [0, 1])
  fail = false; await p.loadNextPage()
  assert.equal(p.page.value, 2); assert.equal(p.loadMoreFailed.value, false); assert.deepEqual(p.dataList.value.map(row => row.id), [0, 1, 2])
  assert.deepEqual(p.calls.slice(-2), [{ page: 2, pageSize: 20 }, { page: 2, pageSize: 20 }]); p.close()
})

test('后端成功空队列省略 totalSize 时显示空态，不误报加载失败', async () => {
  const p = panel({ read: async () => ({ code: 200, msg: '获取数据成功', data: [] }) })
  try {
    p.mount(); await flush()
    assert.equal(p.loading.value, false)
    assert.equal(p.loadFailed.value, false)
    assert.equal(p.total.value, 0)
    assert.deepEqual(p.dataList.value, [])
    const records = p.load('records.ts')
    assert.throws(() => records.readUpcomingTasks({ code: 200, data: [task()] }))
    assert.throws(() => records.readUpcomingTasks({ code: 500, data: [] }))
    assert.throws(() => records.readUpcomingTasks({ code: 200, data: [], totalSize: 'bad' }))
  } finally { p.close() }
})

test('5 秒静默刷新重读全部已加载页后原子替换，失败保留整份列表且继续重试', async () => {
  const ids = Array.from({ length: 20 }, (_, i) => i)
  let phase = 'initial', second
  const p = panel({ read: ({ page }) => {
    if (phase === 'initial') return Promise.resolve(response(page === 1 ? ids : [20, 21], 22))
    if (page === 1) return Promise.resolve(response(ids.map(id => id + 100), 22))
    second = deferred(); return second.promise
  } })
  p.mount(); await flush(); await p.loadNextPage(); phase = 'refresh'
  assert.ok([...p.timers.values()].every(timer => timer.delay === 5000))
  await p.tick()
  assert.equal(p.loading.value, false); assert.equal(p.loadingMore.value, false)
  assert.equal(p.dataList.value[0].id, 0); assert.equal(p.dataList.value.length, 22)
  second.reject(Error('failed page 2')); await flush()
  assert.equal(p.dataList.value.length, 22); assert.equal(p.dataList.value[0].id, 0)
  await p.tick(); second.resolve(response([120, 121], 22)); await flush()
  assert.equal(p.page.value, 2); assert.equal(p.dataList.value[0].id, 100); assert.equal(p.dataList.value.length, 22)
  assert.ok(p.timers.size); p.close()
})

test('追加和自动刷新互斥，队列变空时保留 total 0 并清除旧列表', async () => {
  const request = deferred()
  const p = panel({ read: ({ page }) => page === 1 ? Promise.resolve(response([0], 2)) : request.promise })
  p.mount(); await flush(); const work = p.loadNextPage(); await p.loadNextPage(); await p.tick()
  assert.equal(p.calls.length, 2); assert.equal(p.loadingMore.value, true)
  request.resolve(response([], 0)); await work
  assert.deepEqual(p.dataList.value, []); assert.equal(p.total.value, 0); assert.equal(p.loadingMore.value, false); p.close()
})

for (const field of ['userId', 'roleId', 'token', 'selected_environment']) {
  test(`${field} 同步 A-B-A 使旧读取失效，旧 finally 不关闭当前 loading`, async () => {
    const requests = [], p = panel({ read: () => { const r = deferred(); requests.push(r); return r.promise } })
    p.mount(); const previous = p.user[field]; p.user[field] = field === 'token' ? 'changed' : 9; p.user[field] = previous
    assert.equal(requests.length, 3); assert.deepEqual(p.dataList.value, [])
    requests[0].resolve(response([1])); requests[1].reject(Error('old')); await flush()
    assert.deepEqual(p.dataList.value, []); assert.equal(p.loading.value, true)
    requests[2].resolve(response([2])); await flush()
    assert.equal(p.dataList.value[0].id, 2); assert.equal(p.loading.value, false); assert.equal(p.loadFailed.value, false); p.close()
  })
}

test('后台暂停、返回恢复；KeepAlive 停用、切页和卸载后不回填迟到结果', async () => {
  const requests = [], p = panel({ read: () => { const r = deferred(); requests.push(r); return r.promise } })
  p.mount(); p.visibility('hidden'); requests[0].resolve(response([1])); await flush()
  assert.deepEqual(p.dataList.value, []); assert.equal(p.loading.value, false); assert.equal(p.timers.size, 0)
  p.visibility('visible'); await p.tick(); assert.equal(requests.length, 2)
  p.deactivate(); requests[1].resolve(response([2])); await flush(); assert.deepEqual(p.dataList.value, [])
  p.route.path = '/other'; p.route.fullPath = '/other'; await flush(); assert.equal(requests.length, 2)
  p.activate(); await p.tick(); assert.equal(requests.length, 2)
  p.route.path = '/index/home'; p.route.fullPath = '/index/home'; await p.tick()
  assert.equal(requests.length, 3); p.close(); requests[2].resolve(response([3])); await flush()
  assert.deepEqual(p.dataList.value, []); assert.equal(p.timers.size, 0)
})

test('待执行任务 SFC 的脚本、模板和 LESS 编译', () => {
  const filename = path.join(base, 'components/PendingTasks.vue')
  const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename }); assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: filename })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: filename, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  for (const style of descriptor.styles) assert.deepEqual(compileStyle({ source: style.content, filename, id: filename, scoped: style.scoped, preprocessLang: style.lang }).errors, [])
})
