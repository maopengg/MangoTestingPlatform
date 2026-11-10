import { loadFeedbackModule } from './load-feedback-modules.mjs'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import ts from 'typescript'
import * as vue from 'vue'
import * as fflate from 'fflate'
import { parse } from '@vue/compiler-sfc'

export function resourcePanel(name, options = {}) {
  const base = path.resolve('src/views/index'), hooks = { mount: [], activate: [], deactivate: [], unmount: [] }
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'test-token', selected_environment: 0 })
  const route = vue.reactive({ path: '/index/home', fullPath: '/index/home' })
  const props = vue.reactive({ visible: false, compact: false, ...options.props }), events = [], messages = [], dialogs = []
  const reads = [], writes = [], copied = [], fetched = [], clicks = [], revoked = [], archives = []
  const frames = new Map(), timers = new Map(), listeners = new Map(), observers = [], elements = new Set()
  let frameId = 0, timerId = 0, urlId = 0, now = ['2026-11-07', '12:00:00']
  const scope = vue.effectScope()
  const vueModule = { ...vue, onMounted: fn => hooks.mount.push(fn), onActivated: fn => hooks.activate.push(fn), onDeactivated: fn => hooks.deactivate.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) }
  const window = {
    location: { origin: 'https://example.com' }, isSecureContext: true,
    requestAnimationFrame(fn) { const id = ++frameId; frames.set(id, fn); return id }, cancelAnimationFrame: id => frames.delete(id),
    addEventListener(event, fn) { if (!listeners.has(event)) listeners.set(event, new Set()); listeners.get(event).add(fn) },
    removeEventListener(event, fn) { listeners.get(event)?.delete(fn) },
  }
  const document = {
    visibilityState: 'visible',
    addEventListener(event, fn) { if (!listeners.has(event)) listeners.set(event, new Set()); listeners.get(event).add(fn) },
    removeEventListener(event, fn) { listeners.get(event)?.delete(fn) },
    body: { appendChild: element => elements.add(element), removeChild: element => elements.delete(element) },
    createElement: type => ({ type, style: {}, select() {}, click() { clicks.push({ href: this.href, download: this.download }) } }),
    execCommand() { return options.fallback ? options.fallback() : true },
  }
  const navigator = { clipboard: { writeText(text) { copied.push(text); return options.copy?.(text) } } }
  const URL = { createObjectURL(blob) { archives.push(blob); return `blob:example-${++urlId}` }, revokeObjectURL: url => revoked.push(url) }
  class ResizeObserver {
    constructor(fn) { this.callback = fn; this.disconnected = false; observers.push(this) }
    observe(target) { this.target = target }
    disconnect() { this.disconnected = true }
  }
  const globals = {
    window, document, navigator, URL, ResizeObserver, AbortController, Blob,
    h: vue.h,
    getComputedStyle: () => ({ rowGap: '8' }),
    setTimeout(fn, delay) { const id = ++timerId; timers.set(id, { fn, delay }); return id }, clearTimeout: id => timers.delete(id),
    setInterval(fn, delay) { const id = ++timerId; timers.set(id, { fn, delay, repeat: true }); return id }, clearInterval: id => timers.delete(id),
    fetch(url, config) { fetched.push({ url, config }); return options.fetch ? options.fetch(url, config) : Promise.resolve({ ok: true, arrayBuffer: async () => new TextEncoder().encode('Example asset').buffer }) },
  }
  const api = {
    getCurrentUserApiKey() { reads.push({}); return options.read ? options.read() : Promise.resolve({ code: 200, data: { api_key: 'example-old-key' } }) },
    putUserApiKey(args) { writes.push(args); return options.write ? options.write(args) : Promise.resolve({ code: 200, data: { api_key: 'example-new-key' } }) },
    getSystemSocketAllUserSum() { reads.push({}); return options.read ? options.read() : Promise.resolve({ code: 200, data: { sum: 0 } }) },
  }
  const modules = {
    vue: vueModule, 'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user },
    '@/utils': { getNowDate: () => now },
    '@/store/modules/platform-branding': { default: () => vue.reactive({ englishName: 'ExamplePlatform' }) },
    '@/views/index/composables/use-home-menu-icon': { useHomeMenuIcon: () => ({ resolveMenuIcon: (_path, fallback) => fallback }) },
    '@/hooks/useDisplayDensity': { displayDensityScale: vue.ref(1), scaleDensityPixels: value => value },
    '@/api/axios.config': { baseURL: 'https://example.com/api' },
    '@arco-design/web-vue/es/icon': new Proxy({}, { get: (_target, key) => ({ name: key }) }),
    '@arco-design/web-vue': {
      Message: Object.fromEntries(['success', 'error', 'warning'].map(kind => [kind, text => messages.push({ kind, text })])),
      Modal: { confirm(config) { const dialog = { config, closed: false, close() { this.closed = true }, update() {} }; dialogs.push(dialog); return dialog } },
    },
    fflate,
  }
  const assets = options.assets ?? {
    documents: { '../../../../../skill/example/SKILL.md': '---\nname: Example\ndescription: Example document\n---\n## Usage\nExample content' },
    introductions: {}, urls: { '../../../../../skill/example/SKILL.md': '/assets/example.md', '../../../../../skill/example/references/example.txt': '/assets/example.txt' },
  }
  const transformer = context => {
    const visit = node => {
      if (ts.isCallExpression(node) && node.expression.getText().startsWith('import.meta.glob')) {
        const first = node.arguments[0]
        const key = ts.isStringLiteral(first) && first.text.includes('SKILL.md') ? 'documents' : ts.isStringLiteral(first) ? 'introductions' : 'urls'
        return ts.factory.createElementAccessExpression(ts.factory.createIdentifier('__assets'), ts.factory.createStringLiteral(key))
      }
      if (ts.isPropertyAccessExpression(node) && node.getText() === 'import.meta.env.MODE') return ts.factory.createStringLiteral('dev')
      return ts.visitEachChild(node, visit, context)
    }
    return node => ts.visitNode(node, visit)
  }
  const cache = new Map()
  function resolve(id, directory) {
    if (id in modules) return modules[id]
    if (id.startsWith('@/api/')) return api
    if (id.startsWith('.')) return load(path.resolve(directory, id) + '.ts')
    { if (['@/utils/load-error', '@/utils/api-response'].includes(id)) return loadFeedbackModule(id); throw Error(`Unknown dependency ${id}`) }
  }
  function compile(source, lang = 'ts') { return ts.transpileModule(source, { fileName: lang === 'tsx' ? 'component.tsx' : 'component.ts', compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React, jsxFactory: 'h' }, transformers: { before: [transformer] } }).outputText }
  function load(filename) {
    if (cache.has(filename)) return cache.get(filename)
    const exports = {}; cache.set(filename, exports)
    new Function('exports', 'require', compile(readFileSync(filename, 'utf8')))(exports, id => resolve(id, path.dirname(filename)))
    return exports
  }
  const filename = path.join(base, `components/${name}.vue`), descriptor = parse(readFileSync(filename, 'utf8')).descriptor
  const bindings = name === 'ContactAuthor' ? 'visible,handleCancel,handleOk'
    : name === 'HoverTaskDetail' ? 'popupVisible,setPopupVisible,active'
    : name === 'ResourceCenter' ? 'handleDownloadExecutor,handleViewSkill,handleViewHelp,handleContactAuthor'
    : name === 'McpWorkbench'
    ? 'apiKey,apiKeyLoading,apiKeyFailed,configVisible,resetting,copyingLabel,maskedApiKey,capabilityGridRef,loadCurrentUserApiKey,resetApiKey,copyText,copyAuthHeader,copyInstallPrompt,openConfig'
    : 'skills,selectedKey,detail,detailHtml,keyword,filteredSkills,loading,detailLoading,loadFailed,downloadingKey,loadSkills,selectSkill,downloadSkill,close'
  const macroGlobals = {
    defineProps: () => props, withDefaults(p, defaults) { for (const [key, value] of Object.entries(defaults)) if (!(key in p)) p[key] = value; return p },
    defineEmits: () => (...event) => { events.push(event); if (name === 'ContactAuthor' && event[0] === 'update:visible') props.visible = event[1] },
    defineModel: () => vue.computed({ get: () => props.visible, set(value) { props.visible = value; events.push(['update:visible', value]) } }),
  }
  const script = descriptor.scriptSetup ?? descriptor.script
  const result = descriptor.scriptSetup ? `{${bindings}}` : 'exports.default.setup()'
  const state = scope.run(() => new Function('exports', 'require', '__assets', ...Object.keys(globals), ...Object.keys(macroGlobals), `${compile(script.content, script.lang)};return ${result}`)(
    {}, id => resolve(id, path.dirname(filename)), assets, ...Object.values(globals), ...Object.values(macroGlobals),
  ))
  return { ...(typeof state === 'function' ? { render: state } : state), user, route, props, events, messages, dialogs, reads, writes, copied, fetched, clicks, revoked, archives, frames, timers, elements, observers, listeners,
    mount: () => hooks.mount.forEach(fn => fn()), activate: () => hooks.activate.forEach(fn => fn()), deactivate: () => hooks.deactivate.forEach(fn => fn()),
    dispose() { hooks.unmount.forEach(fn => fn()); scope.stop() },
    helpers: () => load(path.join(base, 'skill-documents.ts')),
    setNow(value) { now = value },
    tickClock() { for (const timer of timers.values()) if (timer.repeat) timer.fn() },
    visibility(value) { document.visibilityState = value; listeners.get('visibilitychange')?.forEach(fn => fn()) },
    releaseUrls() { const pending = [...timers.values()]; timers.clear(); pending.forEach(timer => timer.fn()) },
  }
}
