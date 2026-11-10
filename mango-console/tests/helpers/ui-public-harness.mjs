import path from 'node:path'
import { loadModule, getFormItems } from './auth-config-harness.mjs'
import { liveHarness } from './ui-live-workbench-harness.mjs'
export const publicRecords = loadModule('src/views/uitest/public/public-records.ts')
export const publicRow = (extra = {}) => ({
  id: 0,
  name: 'Example variable',
  key: 'example_key',
  value: 'example value',
  type: 0,
  status: 1,
  test_envs: [],
  project_product: { id: 0, name: 'Example product', project: { id: 0, name: 'Example project' } },
  datasource_alias: null,
  update_user: { name: 'Example user', username: 'example-user' },
  update_time: '2026-11-09 10:00:00',
  ...extra,
})
export const publicList = (rows = [publicRow()], totalSize = rows.length) => ({
  code: 200,
  data: rows,
  totalSize,
})
const table = loadModule('src/hooks/table.ts')
export const publicConfig = loadModule('src/views/uitest/public/config.ts', {
  '@/utils/search-condition': loadModule('src/utils/search-condition.ts'),
  '@/utils/id-search': loadModule('src/utils/id-search.ts', {
    '@arco-design/web-vue': { Message: { warning() {} } },
  }),
  '@/hooks/table': table,
  '@/utils/update-user': loadModule('src/utils/update-user.ts'),
})
export function publicHarness({ component = false, api = {}, enums = {}, props = {} } = {}) {
  const confirmations = [],
    messages = []
  const enumStore = {
    ui_public: [
      { key: 0, title: '普通' },
      { key: 1, title: 'SQL' },
      { key: 2, title: '代码' },
    ],
    environment_type: [{ key: 0, title: 'Example environment' }],
    colors: [],
    getEnum: async () => {},
    ...enums,
  }
  const h = liveHarness({
    filename: path.resolve(
      `src/views/uitest/public/${component ? 'components/PublicVariableEditor' : 'index'}.vue`
    ),
    routePath: '/uitest/public/index',
    bindings: component
      ? 'open,close,save,draft,visible,saving,error,editingId,aliasOptions,aliasesLoading,aliasesFailed,loadAliases,onProductChange,onTypeChange,onEnvironmentChange,scope'
      : 'conditionItems,rows,listLoading,listError,userOptions,usersLoading,usersError,typeOptions,environments,enumsLoading,enumsError,loadUsers,loadEnums,doRefresh,initialize,pagination,onSearchRefresh,onResetSearch,onNavigationFilterChange,onAdd,onUpdate,onDelete,onModifyStatus,busy,editorRef,editingBusy,statusIds,deletingIds,actionError,scope,sidebarResetKey,projectProduct',
    props: {
      typeOptions: enumStore.ui_public,
      environments: enumStore.environment_type,
      optionsLoading: false,
      optionsError: '',
      ...props,
    },
    api: {
      getUiPublic: async () => publicList(),
      getUserName: async () => ({ code: 200, data: [{ key: 0, title: 'Example user' }] }),
      getDataFactoryDatasourceAlias: async () => ({ code: 200, data: [] }),
      postUiPublic: async () => ({ code: 200 }),
      putUiPublic: async () => ({ code: 200 }),
      deleteUiPublic: async () => ({ code: 200 }),
      putUiPublicPutStatus: async () => ({ code: 200 }),
      ...api,
    },
    modules: {
      '@/hooks/table': table,
      '@/store/modules/get-enum': { useEnum: () => enumStore },
      '@/utils/datacleaning': { getFormItems },
      '@arco-design/web-vue': {
        Message: Object.fromEntries(
          ['success', 'warning', 'error'].map((kind) => [
            kind,
            (value) => messages.push([kind, value]),
          ])
        ),
        Modal: {
          confirm(options) {
            const entry = {
              ...options,
              closed: false,
              close() {
                this.closed = true
                options.onClose?.()
              },
            }
            confirmations.push(entry)
            return entry
          },
        },
      },
    },
  })
  return { ...h, confirmations, messages, enumStore }
}
