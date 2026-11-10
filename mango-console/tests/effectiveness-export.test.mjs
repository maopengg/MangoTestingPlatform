import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { harness, deferred, flush as microtasks } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/report/effectiveness')
async function flush() { await microtasks(); await new Promise(resolve => setImmediate(resolve)); await microtasks() }
function setup(settings = {}) {
  const previous = Object.fromEntries(['window', 'document', 'requestAnimationFrame', 'cancelAnimationFrame', 'getComputedStyle'].map(key => [key, globalThis[key]]))
  const win = new EventTarget(), fonts = deferred(), frames = new Map(), elements = new Map(), links = [], pngCalls = [], printCalls = [], messages = []
  const life = { mount: [], unmount: [], deactivate: [] }, listeners = new Set()
  let frameSequence = 0
  const report = { scrollWidth: settings.width ?? 1200, scrollHeight: settings.height ?? 800 }
  if (!settings.missingReport) elements.set('mango-effectiveness-report-image', report)
  const doc = Object.assign(new EventTarget(), {
    visibilityState: 'visible', fonts: { ready: fonts.promise }, documentElement: {},
    getElementById: id => elements.get(id) ?? null,
    createElement: () => { const link = { download: '', href: '', clicks: 0, removed: false, click() { this.clicks++ }, remove() { this.removed = true } }; links.push(link); return link },
  })
  const add = doc.addEventListener.bind(doc), remove = doc.removeEventListener.bind(doc)
  doc.addEventListener = (event, callback) => { listeners.add(callback); add(event, callback) }
  doc.removeEventListener = (event, callback) => { listeners.delete(callback); remove(event, callback) }
  Object.assign(globalThis, { window: win, document: doc, requestAnimationFrame: fn => { const id = ++frameSequence; frames.set(id, fn); return id }, cancelAnimationFrame: id => frames.delete(id), getComputedStyle: () => ({ backgroundColor: 'theme-background', getPropertyValue: () => 'theme-surface' }) })
  const options = {
    scope: vue.ref('scope-a'), available: vue.ref(true), loading: vue.ref(false), title: vue.ref('Example / report'),
    printing: vue.ref(false), imageExporting: vue.ref(false), reportMode: vue.ref(false), filterVisible: vue.ref(true),
  }
  const h = harness('EffectivenessAiNote', '', {
    base, filename: path.join(base, 'components/EffectivenessAiNote.vue'), props: { text: '' },
    modules: {
      vue: { ...vue, onMounted: fn => life.mount.push(fn), onBeforeUnmount: fn => life.unmount.push(fn), onDeactivated: fn => life.deactivate.push(fn) },
      '@arco-design/web-vue': { Message: Object.fromEntries(['warning', 'error', 'success'].map(key => [key, text => messages.push([key, text])])) },
      'html-to-image': { toPng: (...args) => { pngCalls.push(args); return settings.png ? settings.png(...args) : Promise.resolve('data:image/png;base64,example') } },
      'print-js': { default: value => { printCalls.push(value); elements.set(value.frameId, { onload: () => {}, remove() { elements.delete(value.frameId) } }); if (settings.print) settings.print(value) } },
    },
  })
  const effect = vue.effectScope()
  const api = effect.run(() => h.load('composables/useEffectivenessExport.ts').useEffectivenessExport({
    contextKey: () => options.scope.value, available: () => options.available.value,
    loading: () => options.loading.value, title: () => options.title.value,
    printing: options.printing, imageExporting: options.imageExporting, reportMode: options.reportMode, filterVisible: options.filterVisible,
  }))
  life.mount.forEach(fn => fn()); if (!settings.pendingFonts) fonts.resolve()
  return { ...api, ...options, doc, win, fonts, frames, links, pngCalls, printCalls, messages, elements, report, life, listeners,
    model: h.load('export-layout.ts'),
    async paint() { await flush(); for (let i = 0; i < 3; i++) { for (const [id, fn] of [...frames]) { frames.delete(id); fn() }; await flush() } },
    close() { life.unmount.forEach(fn => fn()); effect.stop(); h.close(); Object.assign(globalThis, previous) },
  }
}

test('PNG固定标题与主题/实测尺寸，成功下载后释放按钮状态，重复点击不重复转换', async t => {
  const image = deferred(), h = setup({ png: () => image.promise }); t.after(h.close)
  const first = h.downloadReportImage(); assert.equal(h.imageExporting.value, true); assert.equal(h.filterVisible.value, false)
  await h.downloadReportImage(); await h.paint(); assert.equal(h.pngCalls.length, 1)
  h.title.value = 'changed'; image.resolve('data:image/png;base64,example'); await first
  assert.equal(h.pngCalls[0][1].width, 1200); assert.equal(h.pngCalls[0][1].height, 800); assert.equal(h.pngCalls[0][1].backgroundColor, 'theme-background')
  assert.equal(h.pngCalls[0][1].pixelRatio, 3); assert.equal(h.links[0].download, 'Example - report.png'); assert.equal(h.links[0].clicks, 1); assert.equal(h.links[0].removed, true)
  assert.equal(h.imageExporting.value, false); assert.equal(h.messages.filter(item => item[0] === 'success').length, 1)
})

test('字体等待期间上下文变化可结束，不触发绘制；旧finally不清除新任务loading', async t => {
  const h = setup({ pendingFonts: true }); t.after(h.close)
  const first = h.downloadReportImage(); await flush(); h.scope.value = 'scope-b'
  assert.equal(h.imageExporting.value, false)
  const second = h.downloadReportImage(); await first; assert.equal(h.imageExporting.value, true)
  h.fonts.resolve(); await h.paint(); await second; assert.equal(h.pngCalls.length, 1); assert.equal(h.links.length, 1)
})

test('后台取消动画帧，返回不自动下载，KeepAlive和卸载清理自己的等待与监听', async t => {
  const h = setup(); t.after(h.close)
  const first = h.downloadReportImage(); await flush(); assert.equal(h.frames.size, 1)
  h.doc.visibilityState = 'hidden'; h.doc.dispatchEvent(new Event('visibilitychange')); await first
  assert.equal(h.frames.size, 0); assert.equal(h.pngCalls.length, 0); assert.equal(h.imageExporting.value, false)
  h.doc.visibilityState = 'visible'; h.doc.dispatchEvent(new Event('visibilitychange')); await h.paint(); assert.equal(h.pngCalls.length, 0)
  const second = h.downloadReportImage(); await flush(); h.life.deactivate.forEach(fn => fn()); await second; assert.equal(h.frames.size, 0)
  const third = h.downloadReportImage(); await flush(); h.life.unmount.forEach(fn => fn()); await third
  assert.equal(h.listeners.size, 0); assert.equal(h.frames.size, 0); assert.equal(h.pngCalls.length, 0)
})

test('已开始的PNG保持物理锁直到实际结束，过期成功/失败均不下载或提示', async t => {
  for (const failure of [false, true]) {
    const image = deferred(), h = setup({ png: () => image.promise })
    try {
      const first = h.downloadReportImage(); await h.paint(); h.scope.value = 'scope-b'
      assert.equal(h.imageExporting.value, true); await h.downloadReportImage(); assert.equal(h.pngCalls.length, 1)
      if (failure) image.reject(new Error('internal failure')); else image.resolve('data:image/png;base64,example')
      await first; assert.equal(h.imageExporting.value, false); assert.equal(h.links.length, 0)
      assert.equal(h.messages.filter(item => item[0] !== 'warning').length, 0)
    } finally { h.close() }
  }
})

test('缺失内容、非法尺寸、字体/转换失败有安全错误且恢复重试', async t => {
  for (const settings of [{ missingReport: true }, { width: 0 }, { height: NaN }, { png: () => Promise.reject(new Error('internal details')) }]) {
    const h = setup(settings)
    try { const pending = h.downloadReportImage(); await h.paint(); await pending; assert.equal(h.imageExporting.value, false); assert.match(h.messages.at(-1)[1], /生成失败/); assert.equal(h.links.length, 0) }
    finally { h.close() }
  }
  const h = setup({ pendingFonts: true }); t.after(h.close)
  const pending = h.downloadReportImage(); await flush(); h.fonts.reject(new Error('fonts')); await pending
  assert.equal(h.imageExporting.value, false); assert.match(h.messages.at(-1)[1], /生成失败/)
})

test('打印保持A4配置与独有frame，防重复，关闭后恢复原模式，迟到回调不影响新任务', async t => {
  const h = setup(); t.after(h.close)
  const first = h.printReport(); await h.paint(); await first
  const old = h.printCalls[0]; assert.equal(h.printing.value, true); assert.equal(h.reportMode.value, true)
  assert.equal(old.type, 'html'); assert.match(old.style, /A4 landscape/); assert.equal(old.maxWidth, 10000)
  await h.printReport(); assert.equal(h.printCalls.length, 1)
  old.onPrintDialogClose(); assert.equal(h.printing.value, false); assert.equal(h.reportMode.value, false); assert.equal(h.elements.has(old.frameId), false)
  h.reportMode.value = true; const second = h.printReport(); await h.paint(); await second
  assert.notEqual(h.printCalls[1].frameId, old.frameId); old.onPrintDialogClose(); assert.equal(h.printing.value, true)
  h.printCalls[1].onPrintDialogClose(); assert.equal(h.reportMode.value, true); assert.equal(h.printing.value, false)
})

test('打印同步异常、异步错误与上下文失效均可恢复，旧错误不泄露内部信息', async t => {
  const h = setup({ print: () => { throw new Error('internal detail') } }); t.after(h.close)
  const first = h.printReport(); await h.paint(); await first; assert.equal(h.printing.value, false); assert.equal(h.reportMode.value, false); assert.equal(h.messages.at(-1)[1], '打印报告失败，请重试')
  const other = setup()
  try {
    const pending = other.printReport(); await other.paint(); await pending
    const old = other.printCalls[0]; old.onError(new Error('details')); assert.equal(other.printing.value, false)
    const next = other.printReport(); await other.paint(); await next; other.scope.value = 'scope-b'
    assert.equal(other.printing.value, false); assert.equal(other.elements.has(other.printCalls[1].frameId), false)
    const count = other.messages.length; old.onError(new Error('stale')); assert.equal(other.messages.length, count)
  } finally { other.close() }
})

test('loading/不可用时不导出；文件名只使用固定标题的合法字符', async t => {
  const h = setup(); t.after(h.close); h.loading.value = true
  await h.printReport(); await h.downloadReportImage(); assert.equal(h.printCalls.length, 0); assert.equal(h.pngCalls.length, 0)
  h.loading.value = false; h.available.value = false; await h.downloadReportImage(); assert.equal(h.imageExporting.value, false)
  assert.equal(h.model.reportFileName('  /<>:"*?\\|  ', 'png'), '---------.png')
  assert.equal(h.model.reportFileName('  ', 'png'), '自动化质量效能报告.png')
})
