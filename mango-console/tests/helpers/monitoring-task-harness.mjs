import { loadFeedbackModule } from './load-feedback-modules.mjs'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import ts from 'typescript'
import * as vue from 'vue'
import { parse } from '@vue/compiler-sfc'
import { flush } from './case-details-harness.mjs'

const base = path.resolve('src/views/monitoring/task')
const compile = source => ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText
export const taskRecord = (id = 1, patch = {}) => ({
  id, name: `Example ${id}`, description: null, project_product: { id: 0, name: 'Product', project: { id: 0, name: 'Project' } },
  notice_group: null, is_notice: 0, test_env: 0, test_env_display: 'Example environment', script_content: `print(${id})`,
  status: 0, status_display: '待执行', pid: null, started_at: null, stopped_at: null,
  create_time: '2026-11-07 10:00:00', update_time: '2026-11-07 10:00:00', update_user: null, ...patch,
})
export function monitoringHarness(overrides = {}) {
  const calls = [], messages = [], dialogs = [], downloads = [], revoked = [], appended = [], clipboard = []
  const hooks = { mounted: [], activated: [], deactivated: [], unmounted: [] }, timers = new Map()
  let timerId = 0, urlId = 0, exposed
  const document = Object.assign(new EventTarget(), {
    visibilityState: 'visible', body: { appendChild: link => appended.push(link) },
    createElement: () => ({ href: '', download: '', click() { if (overrides.click) overrides.click(); downloads.push({ href: this.href, name: this.download }) }, remove() { const index = appended.indexOf(this); if (index >= 0) appended.splice(index, 1) } }),
  })
  const route = vue.reactive({ path: '/monitoring/task/index', fullPath: '/monitoring/task/index' })
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-token', selected_environment: 0 })
  const defaults = {
    getMonitoringTask: () => ({ code: 200, data: [taskRecord()], totalSize: 1 }),
    getMonitoringTaskDetail: id => ({ code: 200, data: taskRecord(id) }),
    putMonitoringTask: data => ({ code: 200, data: { id: data.id }, msg: 'saved' }),
    postMonitoringTaskStart: id => ({ code: 200, data: taskRecord(id, { status: 5 }), msg: 'started' }),
    postMonitoringTaskStop: id => ({ code: 200, data: taskRecord(id, { status: 2 }), msg: 'stopped' }),
    getMonitoringTaskLogs: () => ({ code: 200, data: ['Example\n'] }),
    deleteMonitoringTask: () => ({ code: 200, msg: 'deleted' }),
    downloadMonitoringTaskLog: () => ({ data: new Blob(['Example\n'], { type: 'text/plain' }) }),
  }
  const api = Object.fromEntries(Object.entries(defaults).map(([name, fn]) => [name, async (...args) => { calls.push([name, ...args]); return (overrides.api?.[name] || fn)(...args) }]))
  const modules = {
    vue: { ...vue, onMounted: fn => hooks.mounted.push(fn), onActivated: fn => hooks.activated.push(fn), onDeactivated: fn => hooks.deactivated.push(fn), onBeforeUnmount: fn => hooks.unmounted.push(fn) },
    'vue-router': { useRoute: () => route },
    '@/store/modules/user': { default: () => user },
    '@/store/modules/get-enum': { useEnum: () => ({ monitoring_task_status: [{ key: 5, title: '启动中' }, { key: 0, title: '待执行' }, { key: 1, title: '运行中' }, { key: 2, title: '已停止' }], environment_type: [] }) },
    '@/api/monitoring/task': api,
    '@/hooks/useDisplayDensity': { scaleDensityPixels: value => value * (overrides.density || 1) },
    '@arco-design/web-vue': {
      Message: Object.fromEntries(['success', 'error', 'warning', 'info'].map(key => [key, value => messages.push([key, value])])),
      Modal: { confirm(options) { const dialog = { options, closed: false, close() { this.closed = true; options.onClose?.() } }; dialogs.push(dialog); return dialog } },
    },
  }
  const cache = new Map()
  const clock = (fn, delay, interval) => { const id = ++timerId; timers.set(id, { fn, delay, interval }); return id }
  const globals = { document, window: {}, navigator: { clipboard: { writeText: async value => { clipboard.push(value); return overrides.copy?.(value) } } },
    URL: { createObjectURL: () => `blob:fixture-${++urlId}`, revokeObjectURL: url => revoked.push(url) }, Blob,
    setTimeout: (fn, delay) => clock(fn, delay, false), clearTimeout: id => timers.delete(id),
    setInterval: (fn, delay) => clock(fn, delay, true), clearInterval: id => timers.delete(id),
  }
  function requireModule(id, dir) {
    if (id in modules) return modules[id]
    if (id.endsWith('.vue')) return {}
    if (id.startsWith('@/')) return load(path.resolve('src', id.slice(2)) + '.ts')
    if (id.startsWith('.')) return load(path.resolve(dir, id) + '.ts')
    { if (['@/utils/load-error', '@/utils/api-response'].includes(id)) return loadFeedbackModule(id); throw Error('Unexpected dependency: ' + id) }
  }
  function execute(source, filename, bindings = '') {
    return new Function('exports', 'require', 'defineExpose', ...Object.keys(globals), compile(source) + bindings)(
      {}, id => requireModule(id, path.dirname(filename)), value => { exposed = value }, ...Object.values(globals),
    )
  }
  function load(filename) {
    if (!cache.has(filename)) {
      const source = readFileSync(filename, 'utf8')
      cache.set(filename, execute(source, filename, '; return exports'))
    }
    return cache.get(filename)
  }
  const filename = path.join(base, overrides.component ? `components/${overrides.component}.vue` : 'index.vue')
  const source = parse(readFileSync(filename, 'utf8')).descriptor.scriptSetup.content
  const scope = vue.effectScope()
  const names = overrides.component === 'MonitoringTaskDemo' ? 'visible,copying,activeDemoType,copyMonitoringDemo,open,close' :
    'tasks,workspace,logs,taskRows,taskPaging,workspaceTask,workspaceTaskId,workspaceCodeText,workspaceDirty,workspaceLoading,workspaceReady,fileSaving,workspaceActionLoading,taskListLoading,taskListLoadingMore,taskListFailed,conditionItems,taskName,currentProjectProductLabel,logPanelVisible,logRefreshLoading,logFailed,logDownloadLoading,logText,autoScroll,logEditorRef,configSaving,deletingIds,taskEditorRef,demoRef,onAdd,onUpdate,onDelete,onTaskSearch,onSidebarFilterChange,doRefresh,selectWorkspaceTask,saveWorkspaceCode,runWorkspaceTask,stopWorkspaceTask,onEditorSaved,monitoringTaskStatusText'
  const state = scope.run(() => execute(source, filename, `; return {${names}}`))
  hooks.mounted.forEach(fn => fn())
  return { ...state, route, user, calls, messages, hooks, timers, dialogs, downloads, revoked, appended, clipboard, document, get exposed() { return exposed },
    load: relative => load(path.join(base, relative)),
    async tick(delay) { for (const [id, timer] of [...timers]) if (timer.delay === delay && timers.has(id)) { if (!timer.interval) timers.delete(id); timer.fn() } await flush() },
    async visibility(value) { document.visibilityState = value; document.dispatchEvent(new Event('visibilitychange')); await flush() },
    dispose() { hooks.unmounted.forEach(fn => fn()); scope.stop(); timers.clear() },
  }
}
