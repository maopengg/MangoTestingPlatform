import path from 'node:path'
import * as vue from 'vue'
import { loadModule } from './auth-config-harness.mjs'
import { flush } from './case-details-harness.mjs'
import * as storageObserver from '../../src/utils/executor-task-observer.mjs'

export const taskResponse = (taskId = 91, id = 0, action = 'start', status = 'running', patch = {}) => ({ code: 200, data: { task_id: taskId, business_id: id, business_type: action === 'start' ? 'u_auth_auto' : 'u_auth_auto_capture', task_type: action === 'start' ? 'auth_start' : 'auth_capture', status, terminal: ['success', 'failed', 'interrupted', 'cancelled', 'timeout'].includes(status), ...patch } })
export function setupUiAuthTasks(overrides = {}) {
  const previous = globalThis.window, originalNow = Date.now
  let now = 1_000_000, timerId = 0, epoch = 0, available = true, owner = '[1,2,0]', manualBusy = false
  const timers = new Map(), storage = new Map(), reads = [], writes = [], messages = [], captured = []
  const sessionStorage = { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) }
  globalThis.window = { sessionStorage, setTimeout: (fn, delay) => { const id = ++timerId; timers.set(id, { fn, at: now + delay }); return id }, clearTimeout: id => timers.delete(id) }
  Date.now = () => now
  const recordsBase = path.resolve('src/views/uitest/auth-config'), cache = new Map()
  const api = { getExecutorTask: (...args) => { reads.push(args); return (overrides.getExecutorTask || (async taskId => taskResponse(taskId)))(...args) },
    postUiAuthConfigAutoStart: (...args) => { writes.push(['start', ...args]); return (overrides.start || (async () => ({ code: 200, data: { task_id: 91 } })))(...args) },
    postUiAuthConfigAutoCapture: (...args) => { writes.push(['capture', ...args]); return (overrides.capture || (async () => ({ code: 200, data: { task_id: 92 } })))(...args) },
  }
  const modules = { vue, '@arco-design/web-vue': { Message: { success: message => messages.push(message) } },
    '@/api/system/executor-task': api, '@/api/uitest/auth-config': api, '@/utils/executor-task-observer.mjs': storageObserver,
    '@/utils/lossless-json': { cloneLosslessJson: value => JSON.parse(JSON.stringify(value)) },
  }
  function load(file) {
    if (cache.has(file)) return cache.get(file)
    const value = loadModule(file, new Proxy(modules, { has: (target, id) => id in target || id.startsWith('.'), get: (target, id) => id in target ? target[id] : load(path.resolve(path.dirname(file), id) + '.ts') }))
    cache.set(file, value); return value
  }
  const { useAuthTaskObserver } = load(path.join(recordsBase, 'composables/useAuthTaskObserver.ts'))
  const context = { available: () => available, owner: () => owner, busy: () => manualBusy,
    capture: () => { const version = epoch; return () => available && epoch === version },
    onCaptured: () => { captured.push(true); return overrides.onCaptured?.() },
  }
  const h = useAuthTaskObserver(context), records = load(path.join(recordsBase, 'auth-task-records.ts'))
  return { ...h, records, reads, writes, messages, captured, timers, storage, sessionStorage,
    createObserver: () => useAuthTaskObserver(context),
    getOwner: () => owner, setOwner(value) { epoch++; owner = value; h.pause() },
    setBusy(value) { manualBusy = value }, invalidate() { epoch++; h.pause() },
    pausePage() { available = false; epoch++; h.pause() }, resumePage(rows = []) { available = true; h.resume(rows) },
    store(id = 0, action = 'start', taskId = 91, legacy = false) { storageObserver.saveExecutorTaskObservation(legacy ? `ui-auth-${action}` : records.authTaskScope(action, owner), id, { taskId, businessType: records.authTaskBusiness(action), owner }) },
    observation(id = 0, action = 'start', legacy = false) { return storageObserver.loadExecutorTaskObservation(legacy ? `ui-auth-${action}` : records.authTaskScope(action, owner), id) },
    async tick(ms) { now += ms; const ready = [...timers].filter(([, timer]) => timer.at <= now); for (const [id, timer] of ready) { timers.delete(id); timer.fn() } await flush() },
    close() { available = false; epoch++; h.pause(); Date.now = originalNow; globalThis.window = previous },
  }
}
