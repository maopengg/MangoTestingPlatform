import { loadFeedbackModule } from './load-feedback-modules.mjs'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import * as vue from 'vue'
import { parse } from '@vue/compiler-sfc'

const base = path.resolve('src/views/timing/system-jobs')
const compile = source => ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
export const fire = (values = {}) => ({ id: 0, status: 0, status_name: '待分发', planned_at: '2026-11-09 10:00:00', fired_at: null, error_message: null, extra_data: { sample: 'omit' }, ...values })
export const row = (values = {}) => ({ key: 'example_job', name: 'Example job', description: 'Example description', cron: '*/5 * * * *', next_fire_at: null,
  source_type: 0, source_type_name: 'Example source', latest_fire: fire(), ...values })
export const ok = (data, totalSize = 1) => ({ code: 200, data, totalSize, msg: '触发完成' })
export function setup(overrides = {}) {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, reads = [], writes = [], messages = [], confirms = []
  const route = vue.reactive({ path: '/system/system-jobs/index', fullPath: '/system/system-jobs/index' })
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['timing.system_jobs:read'] })
  const modules = { vue: { ...vue, onMounted: f => callbacks.mount.push(f), onActivated: f => callbacks.activate.push(f), onDeactivated: f => callbacks.deactivate.push(f), onBeforeUnmount: f => callbacks.unmount.push(f) },
    'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
    '@/api/system/tasks': { getSystemTaskSystemJobs: query => { reads.push(structuredClone(query)); return overrides.read?.(query) ?? Promise.resolve(ok([row()])) },
      postSystemTaskSystemJobTrigger: key => { writes.push(key); return overrides.trigger?.(key) ?? Promise.resolve(ok({ fire_id: 0, status: 3 })) } },
    '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'error', 'warning'].map(name => [name, value => messages.push([name, value])])),
      Modal: { confirm(options) { const handle = { options, closed: false, close() { this.closed = true } }; confirms.push(handle); return handle } } } }
  const cache = new Map()
  function load(file) {
    if (cache.has(file)) return cache.get(file)
    const exports = {}; cache.set(file, exports)
    new Function('exports', 'require', compile(readFileSync(file, 'utf8')))(exports, name => {
      if (name in modules) return modules[name]
      if (name.startsWith('.')) return load(path.resolve(path.dirname(file), name) + '.ts')
      if (name.startsWith('@/')) return load(path.resolve('src', name.slice(2)) + '.ts')
      { if (['@/utils/load-error', '@/utils/api-response'].includes(name)) return loadFeedbackModule(name); throw Error('Unexpected dependency ' + name) }
    })
    return exports
  }
  const filename = path.join(base, 'index.vue'), { descriptor } = parse(readFileSync(filename, 'utf8')), exports = {}
  new Function('exports', 'require', compile(descriptor.script.content))(exports, name => {
    if (name in modules) return modules[name]
    return load(name.startsWith('.') ? path.resolve(base, name) + '.ts' : path.resolve('src', name.slice(2)) + '.ts')
  })
  const scope = vue.effectScope(), page = scope.run(() => exports.default.setup())
  return { ...page, component: exports.default, route, user, permission, callbacks, reads, writes, confirms, messages,
    module: name => load(path.join(base, name)),
    mount() { callbacks.mount.forEach(f => f()); callbacks.activate.forEach(f => f()) },
    visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { callbacks.unmount.forEach(f => f()); scope.stop(); globalThis.document = previous } }
}

