import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { deferred, flush as microtasks } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/report/details')
const response = data => ({ code: 200, data })
const task = (status = 'pending', id = 'task-1') => response({ task_id: id, status, file_name: 'example.xlsx' })
async function flush() { await microtasks(); await new Promise(resolve => setImmediate(resolve)) }
function setup(overrides = {}, settings = {}) {
  const state = vue.reactive({ reportId: '1', status: 0, enabled: true })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-a', selected_environment: 0 })
  const route = vue.reactive({ fullPath: '/report/details?id=1' })
  const life = { mount: [], unmount: [], activate: [], deactivate: [] }, timers = new Map(), calls = [], messages = [], confirmations = []
  const original = { document: globalThis.document, setTimeout, clearTimeout, create: URL.createObjectURL, revoke: URL.revokeObjectURL }
  const downloads = [], removed = [], revoked = [], listeners = new Set()
  const doc = Object.assign(new EventTarget(), { visibilityState: 'visible',
    body: { appendChild() {} }, createElement() { return {
      click() { if (settings.clickFails) throw new Error('click failed'); downloads.push({ name: this.download, href: this.href }) },
      remove() { removed.push(true) },
    } },
  })
  const add = doc.addEventListener.bind(doc), remove = doc.removeEventListener.bind(doc)
  doc.addEventListener = (name, fn) => { listeners.add(fn); add(name, fn) }
  doc.removeEventListener = (name, fn) => { listeners.delete(fn); remove(name, fn) }
  globalThis.document = doc
  let timerId = 0
  globalThis.setTimeout = (fn, delay) => { const id = ++timerId; timers.set(id, { fn, delay }); return id }
  globalThis.clearTimeout = id => timers.delete(id)
  URL.createObjectURL = () => 'blob:example'
  URL.revokeObjectURL = url => revoked.push(url)
  const api = {
    postSystemTestSuiteDetailsApiExport: () => task(),
    getSystemTestSuiteDetailsApiExportStatus: () => task('running'),
    downloadSystemTestSuiteDetailsApiExport: () => ({ status: 200, data: new Blob(['example'], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }) }),
    getSystemTestSuiteDetailsRetry: () => response(null),
    ...overrides,
  }
  const requestApi = Object.fromEntries(Object.entries(api).map(([name, fn]) => [name, (...args) => { calls.push([name, ...args]); return fn(...args) }]))
  const modules = {
    vue: { ...vue, onMounted: fn => life.mount.push(fn), onBeforeUnmount: fn => life.unmount.push(fn), onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn) },
    'vue-router': { useRoute: () => route },
    '@/store/modules/user': { useUserStoreContext: () => user },
    '@/api/system/test_sute_details': requestApi,
    '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'error', 'warning'].map(name => [name, value => messages.push([name, value])])), Modal: {
      confirm(config) { const handle = { closed: false, close() { this.closed = true; if (settings.cancelOnClose) config.onCancel() } }; confirmations.push({ config, handle }); return handle },
    } },
  }
  const cache = new Map()
  function load(filename) {
    if (cache.has(filename)) return cache.get(filename)
    const exports = {}; cache.set(filename, exports)
    const code = ts.transpileModule(readFileSync(filename, 'utf8'), { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText
    new Function('exports', 'require', code)(exports, id => modules[id] || load(id.startsWith('@/') ? path.resolve('src', id.slice(2)) + '.ts' : path.resolve(path.dirname(filename), id) + '.ts'))
    return exports
  }
  const scope = vue.effectScope(), available = () => state.enabled && doc.visibilityState === 'visible'
  let refreshed = 0
  const { exporter, retry } = scope.run(() => ({
    exporter: load(path.join(base, 'composables/useReportApiExport.ts')).useReportApiExport({ reportId: () => state.reportId, status: () => state.status, available }),
    retry: load(path.join(base, 'composables/useReportCaseRetry.ts')).useReportCaseRetry({ reportId: () => state.reportId, available, onSuccess: async () => { refreshed++; await settings.refresh?.() } }),
  }))
  life.mount.forEach(fn => fn()); life.activate.forEach(fn => fn())
  const changeVisibility = value => { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) }
  return { state, user, route, exporter, retry, calls, messages, confirmations, timers, downloads, removed, revoked, doc, listeners,
    data: load(path.join(base, 'report-export.ts')),
    refreshed: () => refreshed,
    hidden() { changeVisibility('hidden') }, visible() { changeVisibility('visible') },
    deactivate() { state.enabled = false; life.deactivate.forEach(fn => fn()) },
    activate() { state.enabled = true; life.activate.forEach(fn => fn()) },
    async tick() { const [id, timer] = timers.entries().next().value; timers.delete(id); timer.fn(); await flush() },
    close() { life.unmount.forEach(fn => fn()); scope.stop(); globalThis.document = original.document; globalThis.setTimeout = original.setTimeout; globalThis.clearTimeout = original.clearTimeout; URL.createObjectURL = original.create; URL.revokeObjectURL = original.revoke },
  }
}

test('导出固定报告/状态快照保留 0，创建合并并维持 1500ms 局部轮询', async t => {
  const read = deferred(), h = setup({ postSystemTestSuiteDetailsApiExport: () => read.promise }); t.after(h.close)
  const first = h.exporter.start(), second = h.exporter.start()
  assert.equal(first, second); assert.equal(h.exporter.loading.value, true)
  await flush(); h.state.status = 1
  assert.deepEqual(h.calls[0], ['postSystemTestSuiteDetailsApiExport', { test_suite_id: '1', status: 0 }])
  read.resolve(task()); await first
  assert.equal(h.timers.size, 1); assert.equal([...h.timers.values()][0].delay, 1500)
  await h.tick(); assert.equal(h.calls.filter(call => call[0] === 'postSystemTestSuiteDetailsApiExport').length, 1)
})

test('完成后仅下载当前任务，成功清理临时链接与 URL', async t => {
  const h = setup({ getSystemTestSuiteDetailsApiExportStatus: () => task('success') }); t.after(h.close)
  await h.exporter.start()
  assert.deepEqual(h.calls.at(-1), ['downloadSystemTestSuiteDetailsApiExport', 'task-1'])
  assert.deepEqual(h.downloads, [{ name: 'example.xlsx', href: 'blob:example' }])
  assert.equal(h.removed.length, 1); assert.deepEqual(h.revoked, ['blob:example'])
  assert.equal(h.timers.size, 0); assert.equal(h.exporter.loading.value, false)
})

test('公开访问不按 token 阻止导出；过期任务可显式重新创建，普通重试复用原任务', async t => {
  const h = setup({ getSystemTestSuiteDetailsApiExportStatus: () => ({ code: 404, data: null }) }); t.after(h.close)
  h.user.token = ''
  await h.exporter.start(); assert.ok(h.exporter.error.value); assert.equal(h.exporter.canRestart.value, true)
  await h.exporter.start()
  assert.equal(h.calls.filter(call => call[0] === 'postSystemTestSuiteDetailsApiExport').length, 1)
  await h.exporter.restart()
  assert.equal(h.calls.filter(call => call[0] === 'postSystemTestSuiteDetailsApiExport').length, 2)
})

test('创建中进入后台不丢任务，恢复只查询既有任务', async t => {
  const read = deferred(), h = setup({ postSystemTestSuiteDetailsApiExport: () => read.promise }); t.after(h.close)
  const pending = h.exporter.start(); await flush(); h.hidden()
  read.resolve(task()); await pending
  assert.equal(h.calls.length, 1); assert.equal(h.timers.size, 0)
  h.visible(); await flush()
  assert.equal(h.calls.filter(call => call[0] === 'postSystemTestSuiteDetailsApiExport').length, 1)
  assert.equal(h.calls.at(-1)[0], 'getSystemTestSuiteDetailsApiExportStatus')
})

test('后台/KeepAlive 取消计时，返回原任务且不叠加查询', async t => {
  const h = setup(); t.after(h.close)
  await h.exporter.start(); h.hidden(); assert.equal(h.timers.size, 0)
  h.visible(); await flush(); assert.equal(h.timers.size, 1)
  h.deactivate(); assert.equal(h.timers.size, 0)
  h.activate(); await flush(); assert.equal(h.timers.size, 1)
  assert.equal(h.calls.filter(call => call[0] === 'postSystemTestSuiteDetailsApiExport').length, 1)
})

test('状态读取未结束时暂停再恢复，真实请求结束后才补一次查询', async t => {
  const read = deferred(); let count = 0
  const h = setup({ getSystemTestSuiteDetailsApiExportStatus: () => count++ ? task('running') : read.promise }); t.after(h.close)
  const pending = h.exporter.start(); await flush(); h.hidden(); h.visible(); await flush()
  assert.equal(count, 1)
  read.resolve(task('running')); await pending
  assert.equal([...h.timers.values()][0].delay, 0)
  await h.tick(); assert.equal(count, 2)
})

for (const key of ['reportId', 'route', 'userId', 'roleId', 'token', 'selected_environment']) {
  test(`导出创建期间 ${key} A-B-A 丢弃旧任务，锁等到真实请求完成`, async t => {
    const read = deferred(), h = setup({ postSystemTestSuiteDetailsApiExport: () => read.promise }); t.after(h.close)
    const pending = h.exporter.start(); await flush()
    const target = key === 'reportId' ? h.state : key === 'route' ? h.route : h.user
    const property = key === 'route' ? 'fullPath' : key, old = target[property]
    target[property] = typeof old === 'string' ? old + '-b' : 2
    target[property] = old
    assert.equal(h.exporter.loading.value, true)
    assert.equal(h.exporter.start(), pending)
    read.resolve(task()); await pending
    assert.equal(h.calls.length, 1); assert.equal(h.timers.size, 0); assert.deepEqual(h.messages, [])
    assert.equal(h.exporter.loading.value, false)
  })
}

test('下载期间切页或后台，迟到 blob 不触发下载或成功提示', async t => {
  const read = deferred(), h = setup({ getSystemTestSuiteDetailsApiExportStatus: () => task('success'), downloadSystemTestSuiteDetailsApiExport: () => read.promise }); t.after(h.close)
  const pending = h.exporter.start(); await flush(); h.hidden()
  read.resolve({ data: new Blob(['example']) }); await pending
  assert.equal(h.downloads.length, 0)
  assert.equal(h.messages.filter(message => message[1] === 'API报告导出完成').length, 0)
})

test('查询失败显式重试原任务，不创建新任务；业务 fail 后允许重新创建', async t => {
  let mode = 'error'
  const h = setup({ getSystemTestSuiteDetailsApiExportStatus: () => { if (mode === 'error') throw new Error('failed'); return task(mode) } }); t.after(h.close)
  await h.exporter.start(); assert.ok(h.exporter.error.value); assert.equal(h.exporter.loading.value, false)
  mode = 'fail'; await h.exporter.start(); assert.ok(h.exporter.error.value)
  assert.equal(h.calls.filter(call => call[0] === 'postSystemTestSuiteDetailsApiExport').length, 1)
  mode = 'running'; await h.exporter.start()
  assert.equal(h.calls.filter(call => call[0] === 'postSystemTestSuiteDetailsApiExport').length, 2)
  assert.equal(h.exporter.error.value, '')
})

test('拒绝错任务、错误状态、错误码、JSON/空下载，click 异常也释放资源', async t => {
  const h = setup({}, { clickFails: true }); t.after(h.close)
  assert.throws(() => h.data.parseReportExportTask(task('success', 'other'), 'task-1'))
  assert.throws(() => h.data.parseReportExportTask(task('unknown')))
  assert.throws(() => h.data.parseReportExportTask(task(['success'])))
  assert.throws(() => h.data.parseReportExportTask({ ...task(), code: 403 }))
  assert.throws(() => h.data.reportExportBlob({ data: new Blob(['{}'], { type: 'application/json' }) }))
  assert.throws(() => h.data.reportExportBlob({ data: new Blob([]) }))
  assert.throws(() => h.data.saveReportExport(new Blob(['example']), 'example.xlsx'))
  assert.equal(h.removed.length, 1); assert.equal(h.revoked.length, 1)
})

test('卸载清理定时器与监听，旧状态成功不会下载', async t => {
  const read = deferred(), h = setup({ getSystemTestSuiteDetailsApiExportStatus: () => read.promise })
  const pending = h.exporter.start(); await flush(); h.close()
  read.resolve(task('success')); await pending
  assert.equal(h.listeners.size, 0); assert.equal(h.timers.size, 0); assert.equal(h.downloads.length, 0)
})

test('重试确认固定 ID 0、防重复，提交成功后只刷新一次', async t => {
  const read = deferred(), h = setup({ getSystemTestSuiteDetailsRetry: () => read.promise }); t.after(h.close)
  h.retry.confirm(0)
  const config = h.confirmations[0].config, pending = config.onBeforeOk()
  assert.deepEqual(h.retry.busyIds.value, ['0'])
  assert.equal(await config.onBeforeOk(), false)
  h.retry.confirm(0); assert.equal(h.confirmations.length, 1)
  read.resolve(response(null)); assert.equal(await pending, true)
  assert.equal(h.refreshed(), 1); assert.deepEqual(h.retry.busyIds.value, [])
  assert.deepEqual(h.calls[0], ['getSystemTestSuiteDetailsRetry', '0', true])
})

test('重试失败保持确认可再提交，错误码不产生成功或刷新', async t => {
  let failed = true
  const h = setup({ getSystemTestSuiteDetailsRetry: () => failed ? { code: 403 } : response(null) }); t.after(h.close)
  h.retry.confirm(1); const config = h.confirmations[0].config
  assert.equal(await config.onBeforeOk(), false); assert.equal(h.refreshed(), 0)
  failed = false; assert.equal(await config.onBeforeOk(), true); assert.equal(h.refreshed(), 1)
})

test('被替换/取消的旧确认不能提交，关闭回调可重入而不递归', async t => {
  const h = setup({}, { cancelOnClose: true }); t.after(h.close)
  h.retry.confirm(1); const old = h.confirmations[0]
  h.retry.confirm(2); assert.equal(old.handle.closed, true)
  assert.equal(await old.config.onBeforeOk(), false)
  old.config.onCancel(); assert.equal(h.confirmations[1].handle.closed, false)
  h.confirmations[1].config.onCancel()
  assert.equal(await h.confirmations[1].config.onBeforeOk(), false); assert.equal(h.calls.length, 0)
})

test('重试进行中身份变更关闭确认，物理锁保留，迟到成功不刷新', async t => {
  const read = deferred(), h = setup({ getSystemTestSuiteDetailsRetry: () => read.promise }); t.after(h.close)
  h.retry.confirm(1); const pending = h.confirmations[0].config.onBeforeOk()
  h.user.roleId = 2; h.user.roleId = 1
  assert.equal(h.confirmations[0].handle.closed, true); assert.deepEqual(h.retry.busyIds.value, ['1'])
  h.retry.confirm(1); assert.equal(h.confirmations.length, 1)
  read.resolve(response(null)); assert.equal(await pending, false); assert.equal(h.refreshed(), 0)
  assert.deepEqual(h.retry.busyIds.value, [])
})

for (const key of ['reportId', 'route', 'userId', 'token', 'selected_environment']) {
  test(`重试 ${key} 切换使旧确认失效，锁保留到请求结束`, async t => {
    const read = deferred(), h = setup({ getSystemTestSuiteDetailsRetry: () => read.promise }); t.after(h.close)
    h.retry.confirm(1); const pending = h.confirmations[0].config.onBeforeOk()
    if (key === 'reportId') h.state.reportId = '2'
    else if (key === 'route') h.route.fullPath = '/report/details?id=2'
    else h.user[key] = key === 'token' ? 'fixture-b' : 2
    assert.deepEqual(h.retry.busyIds.value, ['1']); assert.equal(h.confirmations[0].handle.closed, true)
    read.reject(new Error('old')); assert.equal(await pending, false)
    assert.equal(h.refreshed(), 0); assert.deepEqual(h.retry.busyIds.value, [])
    assert.equal(h.messages.length, 0)
  })
}

test('后台或停用后旧确认不能提交，重新激活不自动执行写操作', async t => {
  const h = setup(); t.after(h.close)
  h.retry.confirm(1); h.hidden()
  assert.equal(await h.confirmations[0].config.onBeforeOk(), false)
  h.visible(); h.retry.confirm(1); h.deactivate()
  assert.equal(await h.confirmations[1].config.onBeforeOk(), false)
  h.activate(); await flush(); assert.equal(h.calls.length, 0)
})

test('服务端已接受后刷新失败仍关闭确认，不误报任务未提交', async t => {
  const h = setup({}, { refresh: async () => { throw new Error('refresh failed') } }); t.after(h.close)
  h.retry.confirm(1); assert.equal(await h.confirmations[0].config.onBeforeOk(), true)
  assert.equal(h.calls.length, 1)
  assert.equal(h.messages.some(message => message[0] === 'error'), false)
  assert.equal(h.messages.some(message => message[0] === 'warning'), true)
})
