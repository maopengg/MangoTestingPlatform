import path from 'node:path'
import * as vue from 'vue'
import { loadModule } from './auth-config-harness.mjs'
import { liveHarness, models, lossless } from './ui-live-workbench-harness.mjs'
export const editor = loadModule('src/components/business/ui-element-editor.ts', { '@/utils/lossless-json': lossless, './ui-live-workbench': models })
export const records = loadModule('src/views/uitest/page/elements/element-records.ts', { '@/components/business/ui-element-editor': editor, '@/components/business/ui-live-workbench': models })
export const elementRow = (extra = {}) => ({ id: 0, page: 0, name: 'Example element', category: 'Example', exp: 0, loc: '//button', sub: 0, latest_runtime_snapshot: {}, ...extra })
export const pageRow = (extra = {}) => ({ id: 0, name: 'Example page', url: 'https://example.com/page', project_product: { id: 0, ui_client_type: 0 }, ...extra })
export const listResponse = (rows = [elementRow()], totalSize = rows.length) => ({ code: 200, data: rows, totalSize })
export function elementsHarness({ bindings, api = {}, props = {}, query = { id: 0 }, cached = null } = {}) {
  const confirmations = [], notices = [], pageData = vue.reactive({ record: cached })
  const h = liveHarness({ filename: path.resolve('src/views/uitest/page/elements/index.vue'), routePath: '/uitest/page/elements', query,
    bindings: bindings || 'resources,checks,scope,currentPageId,pageRecord,listLoading,pageLoading,categoryLoading,listError,categoryError,pageError,elementRows,pagination,selectedRowKeys,selectedCategoryKeys,activeCategory,onCategorySelect,onSelectionChange,onDelete,onAiInfo,onCheck,doRefresh,loadCategories,initialize,refreshAll,browserOpening,openElementPageBrowser,actionError,deleting,batchAddVisible,elementEditPanelRef,deepCheckVariablesDialogRef,liveWorkbenchRef,liveWorkbenchVisible,toggleElementLiveWorkbench,metadataLoading',
    props: { pageId: '', embedded: false, ...props },
    api: { getUiPage: async ({ id }) => ({ code: 200, data: [pageRow({ id })] }), getUiElement: async () => listResponse(), getUiElementCategory: async () => ({ code: 200, data: [{ key: '__all__', title: '全部', count: 1 }, { key: 'Example', title: 'Example', count: 1 }] }), getActiveExecutorTasks: async () => ({ code: 200, data: [] }), deleteUiElement: async () => ({ code: 200 }), postUiElementOpenBrowser: async () => ({ code: 200 }), ...api },
    modules: {
      '@/components/business/ui-element-editor': editor,
      '@/hooks/table': loadModule('src/hooks/table.ts'), '@/store/page-data': { usePageData: () => pageData },
      '@/utils/update-user': { updateUserColumn: () => ({ key: 'update_user', dataIndex: 'update_user' }), updateTimeColumn: () => ({ key: 'update_time', dataIndex: 'update_time' }) },
      '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'error', 'warning', 'info'].map(kind => [kind, value => notices.push([kind, value])])), Modal: { confirm(options) { const entry = { ...options, closed: false, close() { entry.closed = true; options.onClose?.() } }; confirmations.push(entry); return entry } } },
    },
  })
  return { ...h, confirmations, notices, pageData }
}
