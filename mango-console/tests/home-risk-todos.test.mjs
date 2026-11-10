import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/index')
const todo = (id = 0) => ({ id, source_type: 4, source_id: 0, event_type: 6, event_type_name: 'Cleanup failure', severity: 2,
  title: `Risk ${id}`, summary: 'Example risk', due_at: null, occurred_at: '2026-11-07 12:00:00',
  project_product: { name: 'Example product', project: { name: 'Example project' } }, module: null,
  details: { execution_no: 'example-execution', failed_count: 0, errors: [{ item_id: 0, alias: 'Example data', error: 'Example failure' }] },
  owners: [{ id: 0, name: 'Example owner', username: 'example' }], can_mark_handled: true,
})
const response = (ids, count = ids.length) => ({ code: 200, data: { items: ids.map(todo), count, summary: { pending: count } } })
const ack = id => ({ code: 200, data: { id, can_mark_handled: false }, msg: 'Handled' })
function panel(api = {}) {
  const hooks = { mount: [], activate: [], deactivate: [], unmount: [] }, timers = new Map(), listeners = new Set(), reads = [], writes = [], dialogs = [], messages = [], pushes = [], badges = []
  let timerId = 0
  const document = { visibilityState: 'visible', addEventListener: (_event, fn) => listeners.add(fn), removeEventListener: (_event, fn) => listeners.delete(fn) }
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'test-token', selected_environment: 0 })
  const route = vue.reactive({ path: '/index/home', fullPath: '/index/home' })
  const vueModule = { ...vue, onMounted: fn => hooks.mount.push(fn), onActivated: fn => hooks.activate.push(fn), onDeactivated: fn => hooks.deactivate.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) }
  function load(filename, dependencies = {}) {
    const exports = {}, code = ts.transpileModule(readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
    new Function('exports', 'require', 'document', code)(exports, id => dependencies[id], document)
    return exports
  }
  const polling = load('src/utils/page-polling.ts')
  const hook = load('src/hooks/use-page-polling.ts', {
    '@/utils/load-error': loadFeedbackModule('@/utils/load-error'),
    vue: vueModule, 'vue-router': { useRoute: () => route }, '@/utils/page-polling': { ...polling,
      createPagePolling: (refresh, available) => polling.createPagePolling(refresh, available, {
        setTimeout: (fn, delay) => { const id = ++timerId; timers.set(id, { fn, delay }); return id }, clearTimeout: id => timers.delete(id),
      }),
    },
  })
  const Modal = { confirm(config) { const dialog = { config, closed: false, close() { dialog.closed = true }, update() {} }; dialogs.push(dialog); return dialog } }
  const p = harness('RiskTodos', 'items,loading,loadingMore,loadFailed,loadMoreFailed,page,total,handlingTodoId,navigatingTodoId,fetchData,refresh,loadNextPage,confirmHandled,goToSource,detailRows,cleanupErrors,cleanupPendingItems', {
    base, filename: path.join(base, 'components/RiskTodos.vue'),
    api: {
      getSystemWorkbenchTodos: args => { reads.push(args); return api.read ? api.read(args) : Promise.resolve(response([0, 1])) },
      postSystemWorkbenchTodoHandled: args => { writes.push(args); return api.write ? api.write(args) : Promise.resolve(ack(args.id)) },
    },
    modules: { vue: vueModule, 'vue-router': { useRoute: () => route, useRouter: () => ({ push: args => { pushes.push(args); return api.navigate?.(args) } }) },
      '@/store/modules/user': { default: () => user }, '@/hooks/use-page-polling': hook,
      '@/store/modules/notification-message': { useNotificationMessage: () => ({ setTodoPendingCount: count => badges.push(count) }) },
      '@arco-design/web-vue': { Modal, Message: { success: msg => messages.push(['success', msg]), error: msg => messages.push(['error', msg]) } },
      '@arco-design/web-vue/es/icon': {},
    },
  })
  const dispose = p.close
  return { ...p, user, route, reads, writes, dialogs, messages, pushes, badges, timers,
    mount: () => hooks.mount.forEach(fn => fn()), activate: () => hooks.activate.forEach(fn => fn()), deactivate: () => hooks.deactivate.forEach(fn => fn()),
    visibility(value) { document.visibilityState = value; listeners.forEach(fn => fn()) },
    async tick() { const next = timers.entries().next().value; if (next) { timers.delete(next[0]); next[1].fn(); await flush() } },
    close() { hooks.unmount.forEach(fn => fn()); dispose() },
  }
}

test('待办有限映射和动态明细展示保留 0/null/false；通知快照只从成功响应更新', async () => {
  const p = panel(); p.mount(); p.activate(); await p.tick(); await flush()
  assert.equal(p.reads.length, 1); assert.equal(p.loading.value, false); assert.deepEqual(p.badges, [2])
  assert.equal(p.items.value[0].source_id, 0); assert.equal(p.items.value[0].due_at, null)
  assert.equal(p.cleanupErrors(p.items.value[0])[0].item_id, 0)
  assert.ok(p.detailRows(p.items.value[0]).some(row => row.label === '清理失败' && row.value === '0'))
  const records = p.load('records.ts'), raw = response([0]); raw.data.items[0].unknown_field = 'ignore'
  assert.equal('unknown_field' in records.readRiskTodos(raw).rows[0], false)
  assert.throws(() => records.readRiskTodos({ code: 500, data: raw.data }))
  assert.throws(() => records.readRiskTodos({ code: 200, data: { ...raw.data, summary: {} } }))
  assert.equal(records.riskCleanupDetails([null, 'bad', { item_id: 0, error: { message: 'Example error' } }])[0].error, '{"message":"Example error"}')
  p.close()
})

test('分页失败重试同页、去重；静默刷新重读已加载页并保留原数据直至全部成功', async () => {
  const ids = Array.from({ length: 20 }, (_, i) => i); let mode = 'initial', second
  const p = panel({ read: ({ page }) => {
    if (mode === 'initial') return Promise.resolve(response(page === 1 ? ids : [19, 20, 20], 21))
    if (mode === 'append-fail') return Promise.reject(Error('failed'))
    if (page === 1) return Promise.resolve(response(ids.map(id => id + 100), 21))
    second = deferred(); return second.promise
  } })
  p.mount(); await flush(); mode = 'append-fail'; await p.loadNextPage()
  assert.equal(p.page.value, 1); assert.equal(p.loadMoreFailed.value, true)
  mode = 'initial'; await p.loadNextPage(); assert.equal(p.items.value.length, 21)
  mode = 'quiet'; await p.tick(); assert.equal(p.items.value[0].id, 0); assert.equal(p.loading.value, false)
  second.reject(Error('page 2')); await flush(); assert.equal(p.items.value[0].id, 0); assert.deepEqual(p.badges, [21, 21])
  await p.tick(); second.resolve(response([120], 21)); await flush()
  assert.equal(p.items.value[0].id, 100); assert.equal(p.page.value, 2); assert.ok([...p.timers.values()].every(timer => timer.delay === 5000)); p.close()
})

test('确认固定 ID；取消和重开互不影响，操作仅在成功回执后更新并阻止重复提交', async () => {
  const request = deferred(), p = panel({ write: () => request.promise })
  p.mount(); await flush(); p.confirmHandled(p.items.value[0]); const first = p.dialogs[0]
  first.config.onClose(); p.confirmHandled(p.items.value[1]); const second = p.dialogs[1]
  first.config.onClose(); assert.equal(await first.config.onBeforeOk(), false)
  const work = second.config.onBeforeOk(); await second.config.onBeforeOk(); p.confirmHandled(p.items.value[0])
  assert.deepEqual(p.writes, [{ id: 1 }]); assert.equal(p.handlingTodoId.value, 1); assert.equal(p.dialogs.length, 2)
  assert.equal(second.config.onBeforeCancel(), false)
  request.resolve(ack(1)); assert.equal(await work, true); assert.equal(p.handlingTodoId.value, null); assert.equal(p.messages[0][0], 'success'); p.close()
})

test('失败和错误回执不关闭确认窗口、不假报成功，可在同一窗口重试', async () => {
  let mode = 0
  const p = panel({ write: async () => mode++ === 0 ? { code: 500, msg: 'failed' } : mode === 2 ? ack(9) : ack(0) })
  p.mount(); await flush(); p.confirmHandled(p.items.value[0]); const dialog = p.dialogs[0]
  assert.equal(await dialog.config.onBeforeOk(), false); assert.equal(p.handlingTodoId.value, null)
  assert.equal(await dialog.config.onBeforeOk(), false); assert.ok(p.messages.every(row => row[0] === 'error'))
  assert.equal(await dialog.config.onBeforeOk(), true); assert.equal(p.writes.length, 3); p.close()
})

test('列表首次失败可恢复，处理成功后的重读失败不将写入当失败，也不允许重复处理已确认记录', async () => {
  let fail = true
  const p = panel({ read: async () => { if (fail) throw Error('read failed'); return response([0, 1]) } })
  p.mount(); await flush(); assert.equal(p.loadFailed.value, true); assert.equal(p.loading.value, false); assert.deepEqual(p.badges, [])
  fail = false; await p.refresh(); p.confirmHandled(p.items.value[0]); fail = true
  assert.equal(await p.dialogs[0].config.onBeforeOk(), true)
  assert.equal(p.items.value.some(row => row.id === 0), false); assert.equal(p.messages.filter(([kind]) => kind === 'success').length, 1)
  assert.equal(p.messages.filter(([kind]) => kind === 'error').length, 1)
  p.dialogs[0].config.onClose(); p.confirmHandled(todo(0))
  assert.equal(await p.dialogs[1].config.onBeforeOk(), true); assert.equal(p.writes.length, 1)
  fail = false; await p.tick(); assert.equal(p.loadFailed.value, false); p.close()
})

for (const field of ['userId', 'roleId', 'token', 'selected_environment']) {
  test(`${field} 同步往返清除旧待办与通知数量，旧响应及 finally 不覆盖当前读取`, async () => {
    const requests = [], p = panel({ read: () => { const r = deferred(); requests.push(r); return r.promise } })
    p.mount(); const previous = p.user[field]; p.user[field] = field === 'token' ? 'changed' : 9; p.user[field] = previous
    assert.equal(requests.length, 3); requests[0].resolve(response([1], 99)); requests[1].reject(Error('old')); await flush()
    assert.deepEqual(p.items.value, []); assert.equal(p.loading.value, true); assert.deepEqual(p.badges, [0, 0])
    requests[2].resolve(response([], 0)); await flush(); assert.equal(p.total.value, 0); assert.deepEqual(p.badges, [0, 0, 0]); p.close()
  })
}

test('身份变化关闭旧确认但物理写锁保持至网络完成，旧成功不弹消息或刷新当前通知', async () => {
  const request = deferred(), p = panel({ write: () => request.promise })
  p.mount(); await flush(); p.confirmHandled(p.items.value[0]); const work = p.dialogs[0].config.onBeforeOk()
  p.user.roleId = 9; assert.equal(p.dialogs[0].closed, true); assert.equal(p.handlingTodoId.value, 0)
  p.confirmHandled(todo(1)); assert.equal(p.dialogs.length, 1); assert.equal(p.writes.length, 1)
  request.resolve(ack(0)); assert.equal(await work, false); assert.equal(p.handlingTodoId.value, null)
  assert.deepEqual(p.messages, []); assert.deepEqual(p.badges, [2, 0]); await p.tick(); assert.equal(p.items.value.length, 2); p.close()
})

test('后台、缓存停用及卸载均失效读取和确认窗口，返回后恢复静默读取', async () => {
  const requests = [], p = panel({ read: () => { const r = deferred(); requests.push(r); return r.promise } })
  p.mount(); p.visibility('hidden'); requests[0].resolve(response([1])); await flush()
  assert.deepEqual(p.items.value, []); assert.deepEqual(p.badges, []); assert.equal(p.timers.size, 0)
  p.visibility('visible'); await p.tick(); requests[1].resolve(response([2])); await flush()
  p.confirmHandled(p.items.value[0]); p.deactivate(); assert.equal(p.dialogs[0].closed, true)
  p.route.path = '/other'; p.route.fullPath = '/other'; p.activate(); await p.tick(); assert.equal(requests.length, 2)
  p.route.path = '/index/home'; p.route.fullPath = '/index/home'; await p.tick(); p.close()
  requests[2].resolve(response([3])); await flush(); assert.deepEqual(p.items.value, []); assert.equal(p.timers.size, 0)
})

test('跳转保留来源路由和查询参数，导航防重复并恢复失败按钮', async () => {
  const request = deferred(), p = panel({ navigate: () => request.promise }); p.mount(); await flush()
  const row = p.items.value[0], work = p.goToSource(row); await p.goToSource(row)
  assert.deepEqual(p.pushes, [{ path: '/data-factory/execution/index', query: { execution_no: 'example-execution' } }])
  assert.equal(p.navigatingTodoId.value, 0); p.user.roleId = 9; request.reject(Error('old')); await work
  assert.equal(p.navigatingTodoId.value, null); assert.deepEqual(p.messages, []); p.close()
  const q = panel({ navigate: async () => { throw Error('failed') } }); q.mount(); await flush()
  await q.goToSource({ ...todo(), source_type: 6 }); assert.equal(q.pushes[0].path, '/apitest/case/index'); assert.equal(q.pushes[0].query.project_product, '0')
  assert.equal(q.messages.length, 1); assert.equal(q.navigatingTodoId.value, null); q.close()
})

test('风险待办 SFC 的脚本、模板和 LESS 编译', () => {
  const filename = path.join(base, 'components/RiskTodos.vue'), { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename }); assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: filename })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: filename, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  for (const style of descriptor.styles) assert.deepEqual(compileStyle({ source: style.content, filename, id: filename, scoped: style.scoped, preprocessLang: style.lang }).errors, [])
})
