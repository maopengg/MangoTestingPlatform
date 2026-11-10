import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { deferred, flush as microtasks, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/components/reports')
const response = (id = 0, type = 'test_report', patch = {}) => ({ code: 200, data: {
  target_id: id, target_type: type, content: '# Example', file_name: 'example.md',
  download_url: 'https://example.com/example.md', file_path: 'example.md', update_time: '', ...patch,
} })
async function flush() { await microtasks(); await new Promise(resolve => setImmediate(resolve)) }
function setup(read = () => response(), settings = {}) {
  const user = vue.reactive({ userId: null, roleId: null, token: '', selected_environment: 0 })
  const route = vue.reactive({ fullPath: '/report/details?id=0' }), app = vue.reactive({ theme: 'light' })
  const life = { mount: [], unmount: [], activate: [], deactivate: [] }, calls = [], messages = [], listeners = new Set()
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  const add = doc.addEventListener.bind(doc), remove = doc.removeEventListener.bind(doc), links = []
  doc.addEventListener = (event, fn) => { listeners.add(fn); add(event, fn) }
  doc.removeEventListener = (event, fn) => { listeners.delete(fn); remove(event, fn) }
  doc.body = { appendChild(link) { link.appended = true } }
  doc.createElement = () => {
    const link = { click() { this.clicked = true; if (settings.clickFails) throw new Error('download failed') }, remove() { this.removed = true } }
    links.push(link); return link
  }
  globalThis.document = doc
  const api = Object.fromEntries(['getSystemTaskDiagnosticMarkdown', 'getSystemTestSuiteDiagnosticMarkdown'].map(name => [name, (...args) => {
    calls.push([name, ...args]); return read(args[0], name === 'getSystemTaskDiagnosticMarkdown' ? 'scheduled_task' : 'test_report')
  }]))
  const h = harness('DiagnosticMarkdownDrawer', 'loading,document,errorText,dismissed,loadDocument,closeDrawer,downloadDocument,markdownContent,hasOutline,markdownTheme', {
    base, filename: path.join(base, 'DiagnosticMarkdownDrawer.vue'),
    props: { visible: false, targetType: 'test_report', targetId: 0, documentAvailable: false }, api,
    modules: {
      vue: { ...vue, onMounted: fn => life.mount.push(fn), onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn), onBeforeUnmount: fn => life.unmount.push(fn) },
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { useUserStoreContext: () => user },
      '@/store/modules/app-config': { default: () => app },
      '@arco-design/web-vue/es/icon': { IconClose: {} }, 'md-editor-v3': {}, 'md-editor-v3/lib/preview.css': {},
      '@arco-design/web-vue': { Message: { warning: text => messages.push(text), error: text => messages.push(text) } },
    },
  })
  life.mount.forEach(fn => fn()); life.activate.forEach(fn => fn())
  return { ...h, user, route, app, life, calls, messages, doc, links, listeners, data: h.load('diagnostic-markdown.ts'),
    open() { h.props.visible = true; return h.loadDocument() },
    close() { life.unmount.forEach(fn => fn()); h.close(); globalThis.document = previous } }
}

test('公开报告 ID0 和缓存标记 false 仍实时读取；相同请求合并，加载到真实完成', async t => {
  const read = deferred(), h = setup(() => read.promise); t.after(h.close)
  const first = h.open(), second = h.loadDocument(); assert.equal(first, second)
  await flush(); assert.equal(h.loading.value, true)
  assert.deepEqual(h.calls, [['getSystemTestSuiteDiagnosticMarkdown', '0', true]])
  assert.equal(h.user.token, '')
  read.resolve(response()); await first
  assert.equal(h.document.value.target_id, '0'); assert.equal(h.loading.value, false)
})

test('关闭按钮立即失效，无需等父级回传；重开同目标不接收旧响应或 finally', async t => {
  const old = deferred(); let count = 0
  const h = setup(() => ++count === 1 ? old.promise : response(0, 'test_report', { content: 'new' })); t.after(h.close)
  const first = h.open(); await flush()
  h.closeDrawer(); assert.equal(h.loading.value, false); assert.equal(h.document.value, null)
  await h.loadDocument(); assert.equal(h.calls.length, 1)
  h.props.visible = false; const current = h.open(); await current
  old.resolve(response(0, 'test_report', { content: 'old' })); await first
  assert.equal(h.document.value.content, 'new'); assert.equal(h.events[0][0], 'update:visible')
})

test('目标 A-B-A、目标类型与旧错误不能覆盖最后一次选择', async t => {
  const reads = [deferred(), deferred(), deferred()]; let count = 0
  const h = setup(() => reads[count++].promise); t.after(h.close)
  const first = h.open(); await flush()
  h.props.targetId = 1; const second = h.loadDocument(); await flush()
  h.props.targetId = 0; const last = h.loadDocument(); await flush()
  reads[0].resolve(response()); await first
  reads[1].reject(new Error('old')); await second
  assert.equal(h.loading.value, true); assert.equal(h.document.value, null); assert.equal(h.errorText.value, '')
  reads[2].resolve(response(0, 'test_report', { content: 'current' })); await last
  assert.equal(h.document.value.content, 'current')
})

test('定时任务和报告分别调用既有 API，文档必须与类型和 ID 一致', async t => {
  const h = setup((id, type) => response(id, type)); t.after(h.close)
  await h.open()
  h.props.targetType = 'scheduled_task'; await h.loadDocument()
  assert.equal(h.calls.at(-1)[0], 'getSystemTaskDiagnosticMarkdown')
  assert.equal(h.document.value.target_type, 'scheduled_task')
  assert.throws(() => h.data.parseDiagnosticDocument(response(1), 'test_report', '0'))
  assert.throws(() => h.data.parseDiagnosticDocument(response(0, 'scheduled_task'), 'test_report', '0'))
})

for (const field of ['userId', 'roleId', 'token', 'selected_environment', 'route']) {
  test(`${field} A-B-A 清除证据并关闭；缓存标记变化不能自动重开`, async t => {
    const read = deferred(), h = setup(() => read.promise); t.after(h.close)
    const pending = h.open(); await flush()
    if (field === 'route') { h.route.fullPath = '/report/index'; h.route.fullPath = '/report/details?id=0' }
    else { const before = h.user[field]; h.user[field] = field === 'token' ? 'fixture-b' : 2; h.user[field] = before }
    assert.equal(h.document.value, null); assert.equal(h.dismissed.value, true)
    h.props.documentAvailable = true; await flush(); assert.equal(h.calls.length, 1)
    read.resolve(response()); await pending
    assert.equal(h.document.value, null); assert.equal(h.loading.value, false)
  })
}

test('后台/KeepAlive 暂停旧读取，返回重读；卸载清理监听且旧结果不回填', async t => {
  const read = deferred(); let count = 0
  const h = setup(() => ++count === 1 ? read.promise : response(0, 'test_report', { content: `read-${count}` })); t.after(h.close)
  const pending = h.open(); await flush()
  h.doc.visibilityState = 'hidden'; h.doc.dispatchEvent(new Event('visibilitychange'))
  read.resolve(response()); await pending; assert.equal(h.document.value, null)
  h.doc.visibilityState = 'visible'; h.doc.dispatchEvent(new Event('visibilitychange')); await flush()
  assert.equal(h.document.value.content, 'read-2')
  h.life.deactivate.forEach(fn => fn()); assert.equal(h.document.value, null)
  await h.loadDocument(); assert.equal(h.calls.length, 2)
  h.life.activate.forEach(fn => fn()); await flush(); assert.equal(h.document.value.content, 'read-3')
  h.life.unmount.forEach(fn => fn()); assert.equal(h.listeners.size, 0)
  await h.loadDocument(); assert.equal(h.calls.length, 3)
})

test('只有明确未绑定代码38005为空态，文件缺失/网络/业务错误保留显式重试', async t => {
  const responses = [{ code: 38005 }, Object.assign(new Error('missing'), { code: 38005 }), { code: 38006 }, new Error('network'), { code: 403 }, response()]
  const h = setup(() => { const value = responses.shift(); if (value instanceof Error) throw value; return value }); t.after(h.close)
  await h.open(); assert.equal(h.errorText.value, ''); assert.equal(h.document.value, null)
  await h.loadDocument(); assert.equal(h.errorText.value, '')
  for (let index = 0; index < 3; index++) {
    await h.loadDocument(); assert.ok(h.errorText.value); assert.equal(h.loading.value, false); assert.equal(h.document.value, null)
  }
  await h.loadDocument(); assert.equal(h.errorText.value, ''); assert.ok(h.document.value)
})

test('无效/超精度 ID 不请求，大字符串 ID 保留；坏正文和错误码不作可展示文档', async t => {
  const h = setup((id, type) => response(id, type)); t.after(h.close)
  h.props.targetId = Number.MAX_SAFE_INTEGER + 1
  await h.open(); assert.equal(h.calls.length, 0); assert.ok(h.errorText.value)
  h.props.targetId = '9223372036854775807'; await h.loadDocument()
  assert.equal(h.calls[0][1], '9223372036854775807')
  assert.throws(() => h.data.parseDiagnosticDocument(response(0, 'test_report', { content: {} }), 'test_report', '0'))
  assert.equal(h.data.parseDiagnosticDocument({ code: 200, data: null }, 'test_report', '0'), null)
})

test('正文去掉 frontmatter，空正文不造内容，主题变化即时生效', async t => {
  const h = setup(() => response(0, 'test_report', { content: '---\r\nkey: example\r\n---\r\n# Heading\nText' })); t.after(h.close)
  await h.open(); assert.equal(h.markdownContent.value, '# Heading\nText'); assert.equal(h.hasOutline.value, true)
  h.app.theme = 'dark'; assert.equal(h.markdownTheme.value, 'dark')
  h.document.value.content = ''; assert.equal(h.markdownContent.value, ''); assert.equal(h.hasOutline.value, false)
})

test('下载只使用当前文档，异常也释放临时链接，关闭后不触发下载', async t => {
  const h = setup(() => response(), { clickFails: true }); t.after(h.close)
  await h.open(); h.downloadDocument()
  assert.equal(h.links[0].download, 'example.md'); assert.equal(h.links[0].href, 'https://example.com/example.md')
  assert.equal(h.links[0].removed, true); assert.equal(h.messages.length, 1)
  h.closeDrawer(); h.downloadDocument(); assert.equal(h.links.length, 1)
})

test('公共抽屉及四个调用页面的脚本/模板可编译，抽屉 scoped LESS 可编译', async () => {
  for (const relative of ['src/components/reports/DiagnosticMarkdownDrawer.vue', 'src/views/report/details/index.vue', 'src/views/report/index.vue', 'src/views/report/effectiveness/index.vue', 'src/views/timing/tasks/index.vue']) {
    const filename = path.resolve(relative), { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: relative })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: relative, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    if (relative.includes('DiagnosticMarkdownDrawer')) for (const style of descriptor.styles) {
      assert.deepEqual((await compileStyleAsync({ source: style.content, filename, id: 'diagnostic', scoped: style.scoped, preprocessLang: style.lang })).errors, [])
    }
  }
})
