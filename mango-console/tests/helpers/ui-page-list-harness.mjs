import path from 'node:path'
import * as vue from 'vue'
import { loadModule, getFormItems } from './auth-config-harness.mjs'
import { liveHarness } from './ui-live-workbench-harness.mjs'
export const records = loadModule('src/views/uitest/page/page-records.ts')
export const pageRow = (extra = {}) => ({ id: 0, name: 'Example page', url: 'https://example.com/page', project_product: { id: 0, name: 'Example product', ui_client_type: 0, project: { id: 0, name: 'Example project' } }, module: { id: 0, name: 'Example module', full_path: 'Example / Module' }, update_user: { name: 'Example user' }, update_time: '2026-11-09 10:00:00', ...extra })
export const pageList = (rows = [pageRow()], totalSize = rows.length) => ({ code: 200, data: rows, totalSize })
const table = loadModule('src/hooks/table.ts')
const config = loadModule('src/views/uitest/page/config.ts', {
  '@/utils/search-condition': loadModule('src/utils/search-condition.ts'),
  '@/utils/id-search': loadModule('src/utils/id-search.ts', { '@arco-design/web-vue': { Message: { warning() {} } } }),
  '@/hooks/table': table,
  '@/utils/update-user': loadModule('src/utils/update-user.ts'),
})
export function pageHarness({ api = {}, component = false, enums = {}, bindings } = {}) {
  const confirmations = [], messages = [], pageData = { record: null, setRecord(value) { this.record = value } }
  const h = liveHarness({ filename: path.resolve(`src/views/uitest/page/${component ? 'components/UiPageEditor' : 'index'}.vue`), routePath: '/uitest/page/index',
    bindings: bindings || (component ? 'open,close,save,draft,editingId,visible,saving,error,scope' : 'conditionItems,rows,listLoading,listError,userOptions,usersLoading,usersError,clientOptions,enumsLoading,enumsError,loadUsers,loadEnums,doRefresh,initialize,pagination,selectedRowKeys,onSelectionChange,onSearch,onResetSearch,onSidebarFilterChange,sidebarResetKey,projectProduct,selectedModule,onAdd,onUpdate,onDelete,onElements,editingBusy,deleting,deletingIds,actionError,editorRef,scope'),
    api: { getUiPage: async () => pageList(), getUserName: async () => ({ code: 200, data: [{ key: 0, title: 'Example user' }] }), postUiPage: async () => ({ code: 200 }), putUiPage: async () => ({ code: 200 }), deleteUiPage: async () => ({ code: 200 }), ...api },
    modules: {
      '@/hooks/table': table,
      '@/store/page-data': { usePageData: () => pageData },
      '@/store/modules/get-enum': { useEnum: () => ({ drive_type: [{ key: 0, title: 'WEB' }], colors: {}, getEnum: async () => {}, ...enums }) },
      '@/utils/datacleaning': { getFormItems },
      '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'warning', 'error'].map(kind => [kind, value => messages.push([kind, value])])), Modal: { confirm(options) { const entry = { ...options, closed: false, close() { this.closed = true; options.onClose?.() } }; confirmations.push(entry); return entry } } },
    },
  })
  return { ...h, confirmations, messages, pageData }
}
