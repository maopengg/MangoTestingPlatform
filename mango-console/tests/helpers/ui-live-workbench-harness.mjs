import path from 'node:path'
import * as vue from 'vue'
import * as jsonc from 'jsonc-parser'
import { harness } from './case-details-harness.mjs'
import { loadModule } from './auth-config-harness.mjs'
import { createUiElementCheckSession } from '../../src/utils/ui-element-check-session.mjs'

export const lossless = loadModule('src/utils/lossless-json.ts', { 'jsonc-parser': jsonc })
export const models = loadModule('src/components/business/ui-live-workbench.ts', { '@/utils/lossless-json': lossless })
export function liveHarness({ component = 'UiLiveWorkbenchPanel', bindings, api = {}, props = {}, filename, modules: extraModules = {}, routePath = '/uitest/live-workbench', query = {} } = {}) {
  const previous = { document: globalThis.document, window: globalThis.window, sessionStorage: globalThis.sessionStorage }
  const doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }), browser = new EventTarget(), storage = new Map(), timers = new Map(), callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }
  let timerId = 0
  const sessionStorage = { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key) }
  Object.assign(browser, { sessionStorage, setTimeout(fn, delay) { const id = ++timerId; timers.set(id, { fn, delay }); return id }, clearTimeout: id => timers.delete(id), setInterval(fn, delay) { const id = ++timerId; timers.set(id, { fn, delay, interval: true }); return id }, clearInterval: id => timers.delete(id) })
  Object.assign(globalThis, { document: doc, window: browser, sessionStorage })
  const lifecycle = { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) }
  const user = vue.reactive({ userId: 1, roleId: 2, userName: 'example-user', token: 'example-token', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['ui.page:read'] }), route = vue.reactive({ path: routePath, fullPath: `${routePath}?example=0`, query })
  const routes = []
  const modules = { vue: lifecycle, 'vue-router': { useRoute: () => route, useRouter: () => ({ push: value => { routes.push(value); return Promise.resolve() } }) }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission }, '@/utils/lossless-json': lossless }
  const scope = loadModule('src/hooks/use-live-workbench-scope.ts', modules)
  const workbenchHook = loadModule('src/hooks/use-ui-live-workbench.ts', { vue: lifecycle, '@/utils/minimum-loading': { waitForMinimumLoading: async () => {} } })
  const reads = [], writes = [], messages = [], observations = new Map()
  const functions = { createUiLiveWorkspace: async () => ({ data: { status: 'select_actuator', actuators: [] } }), closeUiLiveWorkspace: async () => ({ code: 200 }), getUiLiveWorkspaceStatus: async () => ({ data: { status: 'ready' } }), getUiUiElementName: async () => ({ data: [] }), getExecutorTask: async () => ({ data: { terminal: false } }), getDataFactoryDatasourceAlias: async () => ({ data: [] }), postUiElementScan: async () => ({ data: { task_id: 'example-task' } }), postUiElementCheck: async () => ({ data: { check_id: 'example-check', task_id: 'example-check-task' } }), postUiElementAiLocatorRecommend: async () => ({ data: { candidates: [] } }), postUiPageStepRecordingCommit: async () => ({ data: { id: 0 } }), putUiElementDeepCheckApply: async () => ({ data: { applied_slots: [1] } }), postUiElementAiSnapshot: async () => ({ code: 200 }), getUiStepsTest: async () => ({ code: 200 }), ...api }
  const wrappers = Object.fromEntries(Object.entries(functions).map(([key, fn]) => [key, (...args) => { (key.startsWith('get') ? reads : writes).push([key, ...args]); return fn(...args) }]))
  const h = harness('index', bindings || 'scope,workspace,workspaceOpening,openWorkspace,resetWorkspace,reopenWorkspace,waitForWorkspaceReady,loadElements,elementOptions,elementsLoading,elementsError,scanPageElements,scanLoading,scanTaskId,pollScanTask,scannedElements,recordedActions,appendRecordedAction,recordingPaused,persistRecordedActions,restoreRecordedActions,recordingStorageKey,openAiLocatorRecommendation,aiLocator,loadAiLocatorBatch,livePanelRef,elementCheckDetail,applyDeepCheckUpdates,deepCheckApplied,deepCheckApplyLoading,checkSelectedElement,selectedElementId,latestElementResult,pollElementCheckTask,elementChecking,handleRecordingSaved,handleLiveCommandResult,debugStep,stepDebugging,contextVersion', {
    filename: filename || path.resolve(`src/components/business/${component}.vue`), props: { mode: 'element', pageId: 0, testEnv: 0, actions: [], ...props }, api: wrappers,
    modules: { ...modules, '@/hooks/use-ui-live-workbench': workbenchHook, '@/components/business/ui-live-workbench': models, '@/hooks/use-live-workbench-scope': scope, '@/utils/ui-element-check-session.mjs': { createUiElementCheckSession }, '@/utils/executor-task-observer.mjs': { saveExecutorTaskObservation: (scope, id, item) => observations.set(`${scope}:${id}`, item), loadExecutorTaskObservation: (scope, id) => observations.get(`${scope}:${id}`), clearExecutorTaskObservation: (scope, id) => observations.delete(`${scope}:${id}`) },
      '@/store/modules/get-ope-value': { useSelectValueStore: () => ({ getSelectValue: async () => {}, findItemByValue: () => ({ parameter: [] }), getOperationOptions: () => [], getAssertionOptions: () => [] }) },
      '@/store/modules/get-enum': { useEnum: () => ({ colors: {}, element_exp: [], environment_type: [], getEnum: async () => {} }) },
      '@arco-design/web-vue/es/icon': {},
      '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'warning', 'error', 'info'].map(kind => [kind, value => messages.push([kind, value])])) },
      ...extraModules,
    },
  })
  return { ...h, user, permission, route, routes, callbacks, timers, writes, reads, messages, observations, storage, workbenchHook,
    mount() { callbacks.mount.forEach(fn => fn()) },
    visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    async tick(delay) { for (const [id, entry] of [...timers]) if (entry.delay === delay) { if (!entry.interval) timers.delete(id); await entry.fn() } },
    ready(id = 'example-workspace') { h.workspace.workspaceId = id; h.workspace.ready = true; h.workspace.resourceId = String(h.props.pageId) },
    cleanup() { callbacks.unmount.forEach(fn => fn()); h.close(); Object.assign(globalThis, previous) },
  }
}
