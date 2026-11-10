import path from 'node:path'
import { loadModule, getFormItems } from './auth-config-harness.mjs'
import { liveHarness } from './ui-live-workbench-harness.mjs'
export const stepRecords = loadModule('src/views/uitest/page-steps/step-list-records.ts')
export const stepRow = (extra = {}) => ({ id: 0, name: 'Example step', page: { id: 0, name: 'Example page' }, project_product: { id: 0, name: 'Example product', project: { id: 0, name: 'Example project' } }, module: { id: 0, name: 'Example module', full_path: 'Example / Module' }, status: 3, run_flow: 'Start → End', update_time: '2026-11-09 12:00:00', update_user: { name: 'Example user' }, ...extra })
export const stepList = (rows = [stepRow()], totalSize = rows.length) => ({ code: 200, data: rows, totalSize })
const table = loadModule('src/hooks/table.ts')
const config = loadModule('src/views/uitest/page-steps/config.ts', {
  '@/hooks/table': table,
  '@/utils/search-condition': loadModule('src/utils/search-condition.ts'),
  '@/utils/id-search': loadModule('src/utils/id-search.ts', { '@arco-design/web-vue': { Message: { warning() {} } } }),
  '@/utils/update-user': loadModule('src/utils/update-user.ts'),
})
export function stepHarness({ component = '', api = {}, enums = {}, bindings } = {}) {
  const confirmations = [], messages = [], pageData = { record: null, setRecord(value) { this.record = value } }
  let enabled = false, refresh
  const polling = { start() { enabled = true }, stop() { enabled = false }, enabled: () => enabled, refresh: () => refresh() }
  const h = liveHarness({ filename: path.resolve(`src/views/uitest/page-steps/${component ? `components/${component}` : 'index'}.vue`), routePath: '/uitest/page-steps/index',
    bindings: bindings || (component === 'StepEditor' ? 'open,closeWindow:close,save,draft,editingId,visible,saving,error,pageOptions,pagesLoading,pagesError,loadPages,changeModule,changeProduct,scope' : component === 'StepReferencesPanel' ? 'open,closeWindow:close,loadReferences,visible,loading,error,rows,selectedStep,selectedCase,caseVisible,openCase,closeCase,scope' : 'conditionItems,rows,listLoading,listError,pagination,selectedRowKeys,onSelectionChange,onSearch,onResetSearch,onSidebarFilterChange,sidebarResetKey,projectProduct,selectedModule,editorRef,referencesRef,onAdd,onUpdate,onDelete,onRunCase,onReferences,onSteps,onSaved,editingBusy,deleting,deletingIds,runningId,actionError,userOptions,usersLoading,usersError,statusOptions,enumsLoading,enumsError,pageOptions,pagesLoading,pagesError,loadUsers,loadEnums,loadPages,doRefresh,initialize,scope'),
    api: { getUiSteps: async () => stepList(), getUiPageName: async () => ({ code: 200, data: [{ key: 0, title: 'Example page' }] }), getUserName: async () => ({ code: 200, data: [{ key: 0, title: 'Example user' }] }), postUiSteps: async () => ({ code: 200 }), putUiSteps: async () => ({ code: 200 }), deleteUiSteps: async () => ({ code: 200 }), getUiPageStepReferencedCases: async () => ({ code: 200, data: [stepRow({ case_people: { name: 'Example owner' } })] }), ...api },
    modules: {
      '@/hooks/table': table,
      '@/hooks/use-page-polling': { usePagePolling(fn) { refresh = fn; return polling }, isPendingExecution: row => [2, 3].includes(Number(row.status)) },
      '@/store/page-data': { usePageData: () => pageData },
      '@/store/modules/get-enum': { useEnum: () => ({ task_status: [{ key: 3, title: '进行中' }], status_colors: {}, getEnum: async () => {}, ...enums }) },
      '@/utils/datacleaning': { getFormItems },
      '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'warning', 'error'].map(kind => [kind, value => messages.push([kind, value])])), Modal: { confirm(options) { const entry = { ...options, closed: false, close() { this.closed = true; options.onClose?.() } }; confirmations.push(entry); return entry } } },
    },
  })
  return { ...h, ...(component ? { close: h.closeWindow } : {}), confirmations, messages, pageData, polling, config }
}
