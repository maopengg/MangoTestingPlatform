import { loadFeedbackModule } from './load-feedback-modules.mjs'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import * as vue from 'vue'
import { harness, flush } from './case-details-harness.mjs'

export const taskListBase = path.resolve('src/views/timing/tasks')
const table = {}
new Function('exports','require',ts.transpileModule(readFileSync('src/hooks/table.ts','utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText)(table, name => {
  if (name === 'vue') return vue
  { if (['@/utils/load-error', '@/utils/api-response'].includes(name)) return loadFeedbackModule(name); throw Error('Unexpected table dependency '+name) }
})
export const taskRow = (values = {}) => ({ id: 0, name: 'Example task', project_product: { id: 0, name: 'Product', project: { id: 1, name: 'Project' } }, module: { id: 0, name: 'Module', full_path: 'Root/Module' },
  case_people: { id: 0, name: 'Owner' }, notice_group: null, timing_strategies: [{ id: 0, name: 'Timing', cron: '0 * * * *' }], test_envs: [0], case_types: [1], execution_scenes: ['regression_test'], execution_scope: 'manual', api_concurrency_limit: null,
  report_retention_policy: 'all', task_group: null, task_group_member_id: null, task_group_name: '', status: 0, is_notice: 1, fail_notice: 1, diagnostic_file_path: '', update_time: '2026-11-09 10:00:00', update_user: { id: 0, name: 'Owner', username: 'example' }, ...values })
export const taskRecent = (values = {}) => ({ test_suite_id: 0, report_retained: true, status: 1, status_key: 'success', status_text: 'Passed', test_env: 0, test_env_text: 'Test', create_time: '2026-11-09 10:00:00', update_time: null, duration_ms: 12, total: 1, success: 1, fail: 0, warning: 0, proceed: 0, stay_begin: 0, stopped: 0, pass_rate: 100, ...values })
export const taskResponse = (rows = [taskRow()], totalSize = rows.length) => ({ code: 200, data: rows, totalSize })
export function setupTaskList(overrides = {}) {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, writes = [], reads = [], messages = [], navigation = [], confirmations = []
  const route = vue.reactive({ path: '/timing/tasks/index', fullPath: '/timing/tasks/index' })
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['timing.tasks:change'] })
  const enumStore = vue.reactive({ environment_type: [{ key: 0, title: 'Test' }], test_case_type: [{ key: 1, title: 'API' }], automation_execution_scene: [], automation_execution_scope: [], api_case_scenario_tag: [], report_retention_policy: [{ key: 'all', title: 'All' },{ key: 'abnormal_only', title: 'Abnormal' }], colors: [], getEnum: overrides.getEnum || (async () => {}) })
  const api = Object.fromEntries(Object.entries({
    getSystemTasks: overrides.getSystemTasks || (async () => taskResponse()),
    getSystemTaskRecentResults: overrides.getSystemTaskRecentResults || (async ids => ({ code: 200, data: Object.fromEntries(ids.map(id => [String(id), [taskRecent()]])) })),
    getUserName: overrides.getUserName || (async () => ({ code: 200, data: [{ key: 0, title: 'Owner' }] })),
    getScheduledTaskGroupOptions: overrides.getScheduledTaskGroupOptions || (async () => ({ code: 200, data: [] })),
    getSystemTaskExecutionOptions: overrides.getSystemTaskExecutionOptions || (async () => ({ code: 200, data: { api_platform_limit: 8 } })),
    deleteSystemTasks: overrides.deleteSystemTasks || (async () => ({ code: 200 })),
    postSystemTriggerManual: overrides.postSystemTriggerManual || (async () => ({ code: 200 })),
    putSystemTasks: overrides.putSystemTasks || (async () => ({ code: 200 })),
    updateScheduledTaskGroupMemberStatus: overrides.updateScheduledTaskGroupMemberStatus || (async () => ({ code: 200, data: { effective_enabled: true } })),
  }).map(([name, fn]) => [name, (...args) => { (name.startsWith('get') ? reads : writes).push([name, ...args]); return fn(...args) }]))
  const h = harness('index', 'conditionItems,activeTab,pagination,list,rows,listLoading,listError,recentResults,recentResultsLoading,recentError,userOptions,usersLoading,usersError,taskGroupOptionsLoading,taskGroupOptionsError,enumsLoading,enumsError,executionOptionsLoading,executionOptionsError,operationError,apiPlatformLimit,navigationCreateRef,navigationProjectProductId,sidebarModuleIds,sidebarSelectedModuleId,sidebarResetKey,taskGroupFilters,taskGroupRef,fineTuningRef,taskEditorRef,triggerModalRef,triggerTarget,triggerSaving,triggerError,triggerPreparingId,finePreparingId,retentionEditor,retentionSaving,retentionError,writeIds,deletingIds,statusSavingIds,offlineExport,diagnosticDrawer,doRefresh,onWorkbenchSearch,onResetSearch,onSidebarFilterChange,filterTasksByGroup,openRecordModuleConfig,getNickName,loadTaskGroupOptions,loadExecutionOptions,openTaskGroupCreate,onAdd,onEdit,onTrigger,onCancelTrigger,onConfirmTrigger,onDelete,openRetentionEditor,closeRetention,saveRetentionPolicy,onModifyStatus,onClick,openRecentResult,openTaskDiagnostic,openOfflineReport,resume', { base: taskListBase, api,
    modules: { vue: { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) },
      '@/hooks/table': table, 'vue-router': { useRoute: () => route, useRouter: () => ({ push: value => { navigation.push(value); return Promise.resolve() } }) },
      '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission }, '@/store/modules/get-enum': { useEnum: () => enumStore },
      '@arco-design/web-vue': { Message: Object.fromEntries(['success','warning','info','error'].map(key => [key,value => messages.push([key,value])])), Modal: { confirm(config) { const shell = { config, closed: false, close() { this.closed = true } }; confirmations.push(shell); return shell } } },
    },
  })
  const shell = () => ({ visible: false, loading: false, opened: [], show(value) { this.visible = true; this.opened.push(value); return Promise.resolve() }, open(value) { this.visible = true; this.opened.push(value) }, openEdit(value) { this.open(value) }, openCreate(value) { this.open(value) }, close() { this.visible = false; this.loading = false }, setConfirmLoading(value) { this.loading = value } })
  const triggerShell = shell(), editorShell = shell(), fineShell = shell()
  h.triggerModalRef.value = triggerShell; h.taskEditorRef.value = editorShell; h.fineTuningRef.value = fineShell
  const groupCalls = []; h.taskGroupRef.value = { applyFilters: () => groupCalls.push('filters'), load: () => groupCalls.push('load'), openCreate: value => groupCalls.push(['create',value]) }
  return { ...h, callbacks, writes, reads, messages, navigation, confirmations, triggerShell, editorShell, fineShell, groupCalls, user, permission, route, enumStore,
    async mount() { callbacks.mount.forEach(fn => fn()); await flush() }, visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { callbacks.unmount.forEach(fn => fn()); h.close(); globalThis.document = previous },
  }
}
