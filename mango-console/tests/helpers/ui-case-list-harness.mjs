import path from 'node:path'
import * as vue from 'vue'
import * as jsonc from 'jsonc-parser'
import { harness } from './case-details-harness.mjs'
import { loadModule } from './auth-config-harness.mjs'
export const assets = loadModule('src/components/business/ui-case-step-create.ts')
export const lossless = loadModule('src/utils/lossless-json.ts', { 'jsonc-parser': jsonc })
export const caseRecords = loadModule('src/views/uitest/case/case-list-records.ts', { '@/utils/lossless-json': lossless, '@/components/business/ui-case-step-create': assets })
export const caseRow = (changes = {}) => ({ id: 0, name: 'Example case', project_product: { id: 0, name: 'Example product', project: { id: 0, name: 'Example project' } }, module: { id: 0, name: 'Example module', full_path: 'Example / Module' }, case_people: { id: 0, name: 'Example user' }, status: 1, level: 0, scenario_layer: 0, scenario_type: 0, scenario_tags: ['regression'], publication_status: 'unpublished', parametrize: [], ...changes })
export const caseResponse = (rows = [caseRow()], totalSize = rows.length) => ({ code: 200, data: rows, totalSize })
export function uiCaseHarness({ component = null, bindings = '', api = {}, props = {} } = {}) {
  const previous = { document: globalThis.document, window: globalThis.window }
  const doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const timers = new Map(); let timerId = 0
  const clock = { setTimeout(fn, delay) { const id = ++timerId; timers.set(id, { fn, delay }); return id }, clearTimeout(id) { timers.delete(id) } }
  globalThis.window = { ...clock }
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, reads = [], writes = [], messages = [], confirmations = [], navigation = [], records = []
  const route = vue.reactive({ path: '/uitest/case/index', fullPath: '/uitest/case/index', query: {} }), user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['ui.case:read'] })
  const enums = vue.reactive({ task_status: [{ key: 0, title: 'Failed' }, { key: 1, title: 'Passed' }], case_level: [{ key: 0, title: 'High' }], api_case_scenario_layer: [{ key: 0, title: 'API' }], api_case_scenario_type: [{ key: 0, title: 'Normal' }], api_case_scenario_tag: [], colors: [], status_colors: [], getEnum: async () => {} })
  const lifecycle = { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) }
  const routerModule = { useRoute: () => route, useRouter: () => ({ push(value) { navigation.push(value); return Promise.resolve() } }) }
  const polling = loadModule('src/utils/page-polling.ts')
  const hooks = loadModule('src/hooks/use-page-polling.ts', { vue: lifecycle, 'vue-router': routerModule, '@/utils/page-polling': { ...polling, createPagePolling: (refresh, available) => polling.createPagePolling(refresh, available, clock) } })
  const functions = { getUiCase: async () => caseResponse(), getUserName: async () => ({ code: 200, data: [{ key: 0, title: 'Example user' }] }), getSystemTasksName: async () => ({ code: 200, data: [{ key: 0, title: 'Example task' }] }),
    ...Object.fromEntries(['postUiCase', 'putUiCase', 'postUiCaseCopy', 'deleteUiCase', 'putUiCasePublication', 'getUiCaseRun', 'postUiRunCaseBatch', 'postSystemTasksBatchSetCases'].map(name => [name, async () => ({ code: 200 })])), ...api }
  const wrappers = Object.fromEntries(Object.entries(functions).map(([name, fn]) => [name, (...args) => { (name.startsWith('get') && name !== 'getUiCaseRun' ? reads : writes).push([name, ...args]); return fn(...args) }]))
  const h = harness('index', bindings || 'list,actions,scope,query,conditionItems,pagination,activePublicationStatus,selectedRowKeys,batchSelectableDataList,enumsLoading,enumsError,doRefresh,onSearchRefresh,onResetSearch,onNavigationFilterChange,switchPublicationTab,onUiCaseSelectionChange,onAdd,onClick,review,caseActions,metadataEditorRef,suiteEditorRef,taskBindingRef,publicationReviewRef,navigationCreateRef,saved', {
    filename: path.resolve(component ? `src/views/uitest/case/components/${component}.vue` : 'src/views/uitest/case/index.vue'), props: { userOptions: [], usersLoading: false, usersError: '', ...props }, api: wrappers,
    modules: { vue: lifecycle, 'vue-router': routerModule, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission }, '@/store/modules/get-enum': { useEnum: () => enums },
      '@/hooks/table': loadModule('src/hooks/table.ts'), '@/hooks/use-page-polling': hooks, '@/utils/lossless-json': lossless, '@/components/business/ui-case-step-create': assets,
      '@/utils/search-condition': loadModule('src/utils/search-condition.ts'), '@/utils/id-search': loadModule('src/utils/id-search.ts', { '@arco-design/web-vue': { Message: { warning: value => messages.push(value) } } }),
      '@/utils/business-format': loadModule('src/utils/business-format.ts'), '@/utils/update-user': { createUpdateUserCondition: () => ({ key: 'update_user', type: 'select', multiple: true, searchOperator: 'in', value: [] }), updateUserColumn: () => ({ key: 'update_user', width: 110 }), updateTimeColumn: () => ({ key: 'update_time', width: 180 }) },
      '@/store/page-data': { usePageData: () => ({ setRecord: value => records.push(value) }) },
      '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'warning', 'error'].map(kind => [kind, value => messages.push([kind, value])])), Modal: { confirm(options) { const shell = { ...options, closed: false, close() { shell.closed = true } }; confirmations.push(shell); return shell } } },
    },
  })
  return { ...h, user, permission, route, enums, callbacks, reads, writes, messages, confirmations, timers, navigation, records,
    async mount() { for (const fn of [...callbacks.mount]) await fn() },
    async tick() { const entry = timers.entries().next().value; if (!entry) return; timers.delete(entry[0]); await entry[1].fn() },
    visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    cleanup() { callbacks.unmount.forEach(fn => fn()); h.close(); Object.assign(globalThis, previous) },
  }
}
