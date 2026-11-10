import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
const response = data => ({ data: { code: 200, data } })
const links = { filename: 'example.html', preview_url: 'https://reports.example.com/view', download_url: 'https://reports.example.com/download', expires_at: '2026-11-09T10:00:00Z' }
const option = id => ({ id, name: 'Example', test_env: 0, status: 1, started_at: '2026-11-09 10:00:00' })
const transpile = source => ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
function loadApi(request) {
  const errors = {}, api = {}
  new Function('exports', transpile(readFileSync('src/api/errors.ts', 'utf8')))(errors)
  new Function('exports', 'require', transpile(readFileSync('src/api/system/offline_report.ts', 'utf8')))(api, name => {
    if (name === '@/api/axios.config') return { default: request }
    if (name === '@/api/errors') return errors
    if (name === '@/api/http') return { get: () => Promise.resolve({}) }
    throw Error(name)
  })
  return { api, errors }
}
function setup(settings = {}) {
  const calls = [], downloads = [], urls = [], revoked = [], timers = [], listeners = new Set(), life = { mount: [], unmount: [], activate: [], deactivate: [] }
  const route = vue.reactive({ path: '/report/index', fullPath: '/report/index' }), user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['report:read'] })
  const previous = { document: globalThis.document, setTimeout: globalThis.setTimeout, create: URL.createObjectURL, revoke: URL.revokeObjectURL }
  const doc = Object.assign(new EventTarget(), { visibilityState: 'visible', createElement: () => ({ click() { downloads.push({ href: this.href, filename: this.download }); if (settings.clickThrows) throw Error('click failed') } }) })
  const add = doc.addEventListener.bind(doc), remove = doc.removeEventListener.bind(doc)
  doc.addEventListener = (event, callback) => { listeners.add(callback); add(event, callback) }; doc.removeEventListener = (event, callback) => { listeners.delete(callback); remove(event, callback) }
  globalThis.document = doc; globalThis.setTimeout = (fn, delay) => { timers.push({ fn, delay }); return timers.length }
  URL.createObjectURL = blob => { urls.push(blob); return `blob:example-${urls.length}` }; URL.revokeObjectURL = url => revoked.push(url)
  const request = {
    get: (...args) => { calls.push(['get', ...args]); return settings.get ? settings.get(...args) : Promise.resolve(response({ items: [option(0)], count: 1 })) },
    post: (...args) => { calls.push(['post', ...args]); return settings.post ? settings.post(...args) : Promise.resolve(args[0].endsWith('/links') ? response(links) : { status: 200, data: new Blob(['Example'], { type: 'text/html' }) }) },
  }
  const { api, errors } = loadApi(request)
  const h = harness('OfflineReportExportDialog', 'generate,loadOptions,loadMoreOptions,retryOptions,cancelRequest,closeDialog:close,links,options,selectedId,page,total,optionsLoading,optionsError,downloading,busy,downloaded,error,statusText,canGenerate,optionLabel', {
    filename: path.resolve('src/components/reports/OfflineReportExportDialog.vue'), props: { visible: true, sourceKind: 'suite', sourceId: 1, ...settings.props }, modules: {
      vue: { ...vue, onMounted: fn => life.mount.push(fn), onBeforeUnmount: fn => life.unmount.push(fn), onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn) },
      'vue-router': { useRoute: () => route }, '@/api/system/offline_report': api, '@/api/errors': errors,
      '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
      '@/store/modules/get-enum': { useEnum: () => ({ environment_type: [{ key: 0, title: 'Zero' }], task_status: [{ key: 1, title: 'Passed' }] }) },
    },
  })
  let closed = false
  return { ...h, calls, downloads, urls, revoked, timers, listeners, route, user, permission, doc, life, api, errors,
    mount() { life.mount.forEach(fn => fn()); life.activate.forEach(fn => fn()) },
    async visibility(state) { doc.visibilityState = state; doc.dispatchEvent(new Event('visibilitychange')); await flush() },
    dispose() { if (closed) return; closed = true; life.unmount.forEach(fn => fn()); h.close(); timers.forEach(timer => timer.fn()); globalThis.document = previous.document; globalThis.setTimeout = previous.setTimeout; URL.createObjectURL = previous.create; URL.revokeObjectURL = previous.revoke },
  }
}
test('完整setup先选择执行报告，0有效；每次生成使用当前执行ID与原API协议', async t => {
  const h = setup({ props: { selectReport: true, sourceKind: 'group', sourceId: 11 } }); t.after(h.dispose); h.mount(); await flush()
  assert.equal(await h.generate(), false); h.selectedId.value = 0; assert.equal(h.canGenerate.value, true)
  assert.equal(await h.generate(), true); assert.equal(await h.generate(), true)
  assert.ok(h.calls.filter(item => item[0] === 'post').every(item => item[1] === '/system/test/suite/offline/links'))
  assert.deepEqual(h.calls.filter(item => item[0] === 'post').map(item => item[2]), [{ source_kind: 'group', source_id: 0 }, { source_kind: 'group', source_id: 0 }]); assert.deepEqual(h.links.value, links)
  assert.match(h.optionLabel(h.options.value[0]), /Zero.*2026-11-09 10:00:00.*Passed.*ID 0/)
})
test('换目标拒绝迟到选项，20条分页；追加失败保留选中并重试原页、去重', async t => {
  const old = deferred(); let failed = true
  const h = setup({ props: { selectReport: true }, get: (url, config) => {
    if (config.params.source_id === 1) return old.promise
    if (config.params.page === 1) return Promise.resolve(response({ items: [option(2)], count: 21 }))
    if (failed) throw Error('next page failed')
    return Promise.resolve(response({ items: [option(2), option(1)], count: 21 }))
  } }); t.after(h.dispose); h.mount(); await flush(); h.props.sourceId = 2; await flush(); assert.equal(h.calls[0][2].signal.aborted, true)
  old.resolve(response({ items: [option(99)], count: 21 })); await flush(); assert.equal(h.options.value[0].id, 2)
  h.selectedId.value = 2; await h.loadMoreOptions(); assert.ok(h.optionsError.value); assert.equal(h.page.value, 1); assert.equal(h.selectedId.value, 2)
  failed = false; await h.retryOptions(); assert.deepEqual(h.options.value.map(item => item.id), [2, 1])
  assert.deepEqual(h.calls.filter(item => item[2]?.params?.source_id === 2).map(item => item[2].params.page), [1, 2, 2]); assert.ok(h.calls.filter(item => item[0] === 'get').every(item => item[2].params.page_size === 20))
  assert.ok(h.calls.every(item => item[1] === '/system/test/suite/offline/options'))
})
test('取消后保持在途物理锁，重开与换来源后旧结果/旧finally不改新状态', async t => {
  const pending = deferred(); let writes = 0
  const h = setup({ post: () => ++writes === 1 ? pending.promise : Promise.resolve(response(links)) }); t.after(h.dispose); h.mount()
  const first = h.generate(); assert.equal(await h.generate(), false); h.closeDialog(); assert.equal(h.busy.value, true); assert.equal(h.calls[0][3].signal.aborted, true)
  h.props.visible = false; h.props.sourceId = 2; h.props.visible = true; assert.equal(await h.generate(), false)
  pending.resolve(response(links)); assert.equal(await first, false); assert.equal(h.links.value, null); assert.equal(h.busy.value, false)
  assert.equal(await h.generate(), true); assert.equal(h.calls.at(-1)[2].source_id, 2)
})
test('仅40047回退HTML下载；其他错误不回退，Blob下载及清理使用固定来源', async t => {
  let code = 40047
  const h = setup({ props: { sourceKind: 'group', sourceId: '90071992547409931234' }, post: url => Promise.resolve(url.endsWith('/links') ? { data: { code, msg: 'Example business error' } } : { status: 200, data: new Blob(['Example'], { type: 'text/html' }) }) }); t.after(h.dispose); h.mount()
  assert.equal(await h.generate(), true); assert.equal(h.downloaded.value, true); assert.equal(h.downloads.length, 1)
  assert.deepEqual(h.calls.map(item => item[1]), ['/system/test/suite/offline/links', '/system/test/suite/offline'])
  assert.deepEqual(h.calls.map(item => item[2]), [{ source_kind: 'group', source_id: '90071992547409931234' }, { source_kind: 'group', source_id: '90071992547409931234' }])
  code = 40042; assert.equal(await h.generate(), false); assert.equal(h.downloads.length, 1); assert.ok(h.error.value); assert.equal(h.downloaded.value, false)
  assert.equal(h.timers[0].delay, 1000); h.timers[0].fn(); assert.equal(h.revoked[0], 'blob:example-1')
})
test('取消后上传错误不回退；下载HTTP迟到不创建Blob链接或点击', async t => {
  const late = deferred(), h = setup({ post: () => late.promise }); t.after(h.dispose); h.mount()
  const write = h.generate(); h.closeDialog(); late.resolve({ data: { code: 40047 } }); assert.equal(await write, false); assert.equal(h.calls.length, 1)
  const download = deferred(); let index = 0
  const other = setup({ post: () => ++index === 1 ? Promise.resolve({ data: { code: 40047 } }) : download.promise })
  try { other.mount(); const current = other.generate(); await flush(); other.closeDialog(); download.resolve({ status: 200, data: new Blob(['Example'], { type: 'text/html' }) }); assert.equal(await current, false); assert.equal(other.urls.length, 0); assert.equal(other.downloads.length, 0) } finally { other.dispose() }
})
for (const field of ['userId', 'roleId', 'token', 'selected_environment', 'permissionKeys', 'route']) {
  test(`${field}切换关闭窗口且拒绝迟到结果，不按权限值预拦截请求`, async t => {
    const pending = deferred(), h = setup({ post: () => pending.promise }); t.after(h.dispose); h.mount(); const write = h.generate()
    if (field === 'permissionKeys') h.permission.permissionKeys = []
    else if (field === 'route') h.route.fullPath = '/other'
    else { const old = h.user[field]; h.user[field] = field === 'token' ? '' : 2; h.user[field] = old }
    assert.deepEqual(h.events.at(-1), ['update:visible', false]); pending.resolve(response(links)); assert.equal(await write, false); assert.equal(h.links.value, null); assert.equal(h.busy.value, false); assert.equal(await h.generate(), false)
  })
}
test('后台和KeepAlive暂停选项，返回自动恢复读取；生成不自动重启，卸载清理', async t => {
  const first = deferred(); let reads = 0
  const h = setup({ props: { selectReport: true }, get: () => ++reads === 1 ? first.promise : Promise.resolve(response({ items: [option(0)], count: 1 })) }); t.after(h.dispose); h.mount(); await flush()
  await h.visibility('hidden'); first.resolve(response({ items: [option(99)], count: 1 })); await flush(); assert.equal(h.options.value.length, 0)
  await h.visibility('visible'); assert.equal(h.options.value[0].id, 0); h.life.deactivate.forEach(fn => fn()); assert.equal(await h.generate(), false)
  h.life.activate.forEach(fn => fn()); await flush(); assert.equal(h.calls.filter(item => item[0] === 'post').length, 0); h.life.unmount.forEach(fn => fn()); assert.equal(h.listeners.size, 0)
})
test('API拒绝坏结构/URL/日期，保留0/长字符串ID及40047机器错误码', async t => {
  const h = setup(); t.after(h.dispose)
  for (const value of [null, [], {}, { items: [], count: false }]) assert.throws(() => h.api.parseOfflineReportOptions(value))
  assert.deepEqual(h.api.parseOfflineReportOptions({ items: [option(0), option('90071992547409931234'), option(false), option(0)], count: 2 }).items.map(item => item.id), [0, '90071992547409931234'])
  for (const preview_url of ['javascript:alert(1)', 'https://user:password@reports.example.com', '', 'not a url']) assert.throws(() => h.api.parseOfflineReportLinks({ ...links, preview_url }))
  assert.throws(() => h.api.parseOfflineReportLinks({ ...links, expires_at: 'invalid' }))
  const failed = loadApi({ post: async () => ({ data: { code: 40047, msg: 'Local storage' } }) }); await assert.rejects(failed.api.generateOfflineReport('suite', 1), error => error instanceof failed.errors.ApiBusinessError && error.code === 40047)
})
test('权限集合为空或token清空后明确重开，仍将请求交给后端判断', async t => {
  const h = setup({ post: () => Promise.resolve({ data: { code: 403, msg: 'Denied' } }) }); t.after(h.dispose); h.mount()
  h.permission.permissionKeys = []; h.user.token = ''
  h.props.visible = false; h.props.visible = true
  assert.equal(h.canGenerate.value, true); assert.equal(await h.generate(), false)
  assert.equal(h.calls.filter(item => item[0] === 'post').length, 1); assert.match(h.error.value, /Denied/)
})
test('下载点击失败仍释放Blob地址，JSON错误响应不伪装成HTML', async t => {
  const h = setup({ clickThrows: true }); t.after(h.dispose); await assert.rejects(h.api.downloadOfflineReport('suite', 1), /click failed/)
  assert.equal(h.timers.length, 1); h.timers[0].fn(); assert.equal(h.revoked.length, 1)
  const api = loadApi({ post: async () => ({ status: 200, data: new Blob([JSON.stringify({ msg: 'Denied' })], { type: 'application/json' }) }) }).api
  await assert.rejects(api.downloadOfflineReport('suite', 1), /Denied/)
})
test('共享HTML下载仍支持设置页样例报告的原URL与文件名', async t => {
  const h = setup(); t.after(h.dispose)
  await h.api.downloadSampleReport()
  assert.equal(h.calls[0][1], '/system/cache/data/report-delivery/sample')
  assert.equal(h.downloads[0].filename, 'sample-report.html')
  assert.equal(h.timers[0].delay, 1000)
})
test('设置页取消样例下载后迟到Blob不会创建下载链接', async t => {
  const pending = deferred(), h = setup({ post: () => pending.promise }); t.after(h.dispose)
  const controller = new AbortController(), download = h.api.downloadSampleReport(controller.signal)
  assert.equal(h.calls[0][3].signal, controller.signal); controller.abort()
  pending.resolve({ status: 200, data: new Blob(['Example'], { type: 'text/html' }) }); await download
  assert.equal(h.downloads.length, 0); assert.equal(h.urls.length, 0)
})
test('共享导出及三个真实调用窗口脚本、模板、样式编译，保留选择与直接导出入口', async () => {
  for (const filename of ['src/components/reports/OfflineReportExportDialog.vue', 'src/views/report/index.vue', 'src/views/timing/tasks/index.vue', 'src/views/timing/tasks/components/TaskGroupManager.vue']) {
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename }); assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: filename }); assert.deepEqual(compileTemplate({ id: filename, source: descriptor.template.content, filename, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ id: filename, source: style.content, filename, scoped: style.scoped, preprocessLang: style.lang })).errors, [])
  }
})
