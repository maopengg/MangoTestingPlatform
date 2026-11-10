import path from 'node:path'
import * as vue from 'vue'
import { harness, flush } from './case-details-harness.mjs'

export const groupEditorBase = path.resolve('src/views/timing/tasks')
export const groupDetail = (values = {}) => ({ id: 0, name: 'Example group', project_product: { id: 0, name: 'Product' }, members: [{ id: 5, module: { id: 0, full_path: 'Root' } }], timing_strategies: [{ id: 0, name: 'Hourly' }], case_people: { id: 0, name: 'Group owner' }, notice_group: { id: 0, name: 'Group notice' }, test_envs: [0], case_types: [1], execution_scenes: ['regression_test'], status: 1, is_notice: 1, fail_notice: 0, revision: 3, extra: 'omit', ...values })
export const groupTree = () => [{ key: 0, title: 'Root', children: [{ key: 1, title: 'Child', children: [{ key: 2, title: 'Leaf', children: [] }] }] }]
export const groupPreview = (values = {}) => ({ create_count: 1, update_count: 0, remove_count: 0, rows: [{ action: 'create', module_id: 0, module_full_path: 'Root', task_name: 'Example child task' }], ...values })
export function setupGroupEditor(overrides = {}) {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, reads = [], writes = [], previews = [], messages = []
  const route = vue.reactive({ path: '/timing/tasks/index', fullPath: '/timing/tasks/index' })
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['timing.tasks:change'] })
  const enumStore = vue.reactive({ environment_type: [{ key: 0, title: 'Test' },{ key: 2, title: 'Production' }], test_case_type: [{ key: 1, title: 'API' },{ key: 3, title: 'Unsupported' }],
    automation_execution_scene: ['unclassified','effectiveness_test','temporary_validation','performance_test','regression_test','stability_monitoring','production_inspection','production_regression'].map(key => ({ key, title: key })), report_retention_policy: [{ key: 'all', title: 'All' },{ key: 'abnormal_only', title: 'Abnormal' }], getEnum: overrides.getEnum || (async () => {}) })
  const api = Object.fromEntries(Object.entries({
    getScheduledTaskGroupDetail: overrides.getScheduledTaskGroupDetail || (async id => ({ code: 200, data: groupDetail({ id }) })),
    getUserModuleTree: overrides.getUserModuleTree || (async () => ({ code: 200, data: groupTree() })),
    getSystemNoticeName: overrides.getSystemNoticeName || (async () => ({ code: 200, data: [{ value: 0, label: 'Notice option' }] })),
    getSystemTimingList: overrides.getSystemTimingList || (async () => ({ code: 200, data: [] })),
    getUserName: overrides.getUserName || (async () => ({ code: 200, data: [{ key: 1, title: 'Another owner' }] })),
    previewScheduledTaskGroup: overrides.previewScheduledTaskGroup || (async () => ({ code: 200, data: groupPreview() })),
    createScheduledTaskGroup: overrides.createScheduledTaskGroup || (async () => ({ code: 200 })),
    updateScheduledTaskGroup: overrides.updateScheduledTaskGroup || (async () => ({ code: 200 })),
  }).map(([name, fn]) => [name, (...args) => { (name.startsWith('get') ? reads : name === 'previewScheduledTaskGroup' ? previews : writes).push([name,...args]); return fn(...args) }]))
  const h = harness('TaskGroupEditorDialog', 'form,editingId,editorVisible,editorLoading,detailReady,detailError,editorLocked,preview,previewVisible,previewLoading,previewSnapshot,previewError,saveError,saveLoading,metadataLoading,metadataErrors,moduleTree,moduleLoading,moduleError,expandedModuleKeys,availableUsers,availableTimings,availableNotices,usersLoading,timingsLoading,noticesLoading,enumsLoading,enumsError,productSelection,selectableModuleTree,mutuallyExclusiveSceneOptions,openCreate,openEdit,loadDetail,loadUsers,loadTimings,loadModules,loadNotices,loadEnums,retryMetadata,onEditorProductChange,onModuleCheck,onEnvironmentChange,openPreview,closePreview,saveGroup,closeEditor:close', { base: groupEditorBase, api,
    modules: { vue: { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) },
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission }, '@/store/modules/get-enum': { useEnum: () => enumStore },
      '@arco-design/web-vue': { Message: Object.fromEntries(['success','error'].map(key => [key, value => messages.push([key,value])])) },
    },
  })
  return { ...h, reads, writes, previews, messages, callbacks, route, user, permission, enumStore,
    async mount() { callbacks.mount.forEach(fn => fn()); await flush() }, visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { callbacks.unmount.forEach(fn => fn()); h.close(); globalThis.document = previous },
  }
}
