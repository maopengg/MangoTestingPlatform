import { loadFeedbackModule } from './load-feedback-modules.mjs'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import * as vue from 'vue'
import { harness, flush } from './case-details-harness.mjs'

export const groupListBase = path.resolve('src/views/timing/tasks')
const table = {}
new Function('exports','require',ts.transpileModule(readFileSync('src/hooks/table.ts','utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText)(table, name => {
  if (name === 'vue') return vue
  { if (['@/utils/load-error', '@/utils/api-response'].includes(name)) return loadFeedbackModule(name); throw Error('Unexpected table dependency '+name) }
})
export const groupRecent = (values = {}) => ({ group_execution_id: 0, status: 1, status_key: 'success', status_text: 'Passed', test_env: 0, test_env_text: 'Test', create_time: '2026-11-09 10:00:00', update_time: null, duration_ms: 12, total: 1, success: 1, fail: 0, warning: 0, proceed: 0, stay_begin: 0, stopped: 0, excluded_count: 0, pass_rate: 100, ...values })
export const groupRow = (values = {}) => ({ id: 0, name: 'Example group', project_product: { id: 0, name: 'Product', project: { id: 0, name: 'Project' } },
  timing_strategies: [{ id: 0, name: 'Timing', cron: '0 * * * *' }], test_envs: [0], case_types: [1], execution_scenes: ['regression_test'], case_people: { id: 0, name: 'Owner' }, notice_group: { id: 0, name: 'Notice' }, status: 1, is_notice: 1, fail_notice: 1, sync_status: 'synced', module_count: 1, enabled_task_count: 1, update_user_name: 'Owner', update_time: '2026-11-09 10:00:00', recent_results: [groupRecent()], ...values })
export const groupListResponse = (rows = [groupRow()], count = rows.length) => ({ code: 200, data: { items: rows, count } })
export const groupListDetail = (values = {}) => ({ ...groupRow(), members: [{ id: 0, module: { id: 0, full_path: 'Root / Child' } }], ...values })
export const groupFilters = () => ({ navigation_module_ids: [], navigation_module_id: null, name: '', test_envs: [], case_types: [], execution_scenes: [], status: null, is_notice: null, sync_status: null })
export function setupGroupList(overrides = {}) {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, reads = [], writes = [], messages = [], confirmations = [], navigation = []
  const route = vue.reactive({ path: '/timing/tasks/index', fullPath: '/timing/tasks/index' })
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['timing.tasks:read'] })
  const enumStore = vue.reactive({ environment_type: [{ key: 0, title: 'Test' }], test_case_type: [{ key: 1, title: 'API' }], colors: {}, api_case_scenario_tag: [], getEnum: overrides.getEnum || (async () => {}) })
  const api = Object.fromEntries(Object.entries({
    getScheduledTaskGroups: overrides.getScheduledTaskGroups || (async () => groupListResponse()),
    getScheduledTaskGroupDetail: overrides.getScheduledTaskGroupDetail || (async id => ({ code:200,data:groupListDetail({ id }) })),
    updateScheduledTaskGroup: overrides.updateScheduledTaskGroup || (async payload => ({ code:200,data:{ item:groupRow({ id:payload.id,status:payload.status,is_notice:payload.is_notice,fail_notice:payload.fail_notice }) } })),
    triggerScheduledTaskGroup: overrides.triggerScheduledTaskGroup || (async () => ({ code:200,data:{ generated_count:2,failed_count:0 } })),
    deleteScheduledTaskGroup: overrides.deleteScheduledTaskGroup || (async () => ({ code:200 })),
    getLatestTaskGroupExecutions: overrides.getLatestTaskGroupExecutions || (async () => ({ code:200,data:[{ id:0,test_env:0,planned_at:'2026-11-09T10:00:00',notice_group__name:'Notice' }] })),
    resendTaskGroupNotice: overrides.resendTaskGroupNotice || (async () => ({ code:200 })),
  }).map(([name,fn]) => [name,(...args) => { (name.startsWith('get') ? reads : writes).push([name,...args]);return fn(...args) }]))
  const h = harness('TaskGroupManager', 'list,rows,loading,listError,pagination,enumsLoading,enumsError,operationError,groupEditorRef,groupDetailRef,offlineExport,pendingGroups,triggeringIds,deletingIds,switchIds,confirmations,noticeLoadingIds,noticeVisible,noticeSending,noticeLoading,noticeError,noticeGroup,noticeExecutions,noticeExecutionId,sendingGroupId,optionTitle,load,refreshGroups,loadEnums,applyFilters,openCreate,openEdit,openDetail,openOfflineReport,filterTasks,openGroupReport,changeGroupSwitch,triggerGroup,deleteGroup,openResendNotice,loadNoticeExecutions,confirmResendNotice,closeNotice,resume', { base:groupListBase, props:{ projectProductId:0,filters:groupFilters(),...overrides.props }, api,
    modules:{ vue:{ ...vue,onMounted:fn=>callbacks.mount.push(fn),onActivated:fn=>callbacks.activate.push(fn),onDeactivated:fn=>callbacks.deactivate.push(fn),onBeforeUnmount:fn=>callbacks.unmount.push(fn) },
      '@/hooks/table':table,'vue-router':{useRoute:()=>route,useRouter:()=>({push:value=>{navigation.push(value);return Promise.resolve()}})},
      '@/store/modules/user':{default:()=>user},'@/store/modules/permission':{default:()=>permission},'@/store/modules/get-enum':{useEnum:()=>enumStore},
      '@arco-design/web-vue':{Message:Object.fromEntries(['success','warning','error'].map(key=>[key,value=>messages.push([key,value])])),Modal:{confirm(config){const shell={config,closed:false,close(){this.closed=true}};confirmations.push(shell);return shell}}},
    },
  })
  const windows = { editor:[],detail:[],closed:[] }
  h.groupEditorRef.value = { openCreate: value=>windows.editor.push(['create',value]),openEdit:id=>windows.editor.push(['edit',id]),close:()=>windows.closed.push('editor') }
  h.groupDetailRef.value = { open:id=>windows.detail.push(id),close:()=>windows.closed.push('detail') }
  return { ...h, callbacks, reads, writes, messages, confirmations, navigation, windows, route, user, permission, enumStore,
    async mount() { callbacks.mount.forEach(fn=>fn());await flush() }, visibility(value){doc.visibilityState=value;doc.dispatchEvent(new Event('visibilitychange'))},
    close(){callbacks.unmount.forEach(fn=>fn());h.close();globalThis.document=previous},
  }
}
