import path from 'node:path'
import * as vue from 'vue'
import { harness } from './case-details-harness.mjs'
const base = path.resolve('src/views/functional-test/suite')
export const page = (data, totalSize = data.length) => ({ data, totalSize })
export function setupSuiteList(api = {}, overrides = {}) {
  const route = vue.reactive({
    path: '/functional-test/suite/index',
    fullPath: '/functional-test/suite/index',
  })
  const user = vue.reactive({
    userId: 1,
    roleId: 1,
    token: 'example-test-token',
    selected_environment: 1,
  })
  const hooks = { mount: [], stop: [], activate: [], unmount: [] },
    calls = [],
    dialogs = [],
    messages = []
  const wrapped = Object.fromEntries(
    Object.entries({
      getManualSuite: async () => page([{ id: 1, requirement_name: 'Original' }]),
      getManualCase: async () => page([{ id: 2, title: 'Original case' }]),
      getUserName: async () => ({ data: [] }),
      deleteManualSuite: async (id) => ({ data: { deleted_count: 1, deleted_suite_ids: [id] } }),
      deleteManualCase: async () => ({ data: { count: 1 } }),
      ...api,
    }).map(([key, fn]) => [
      key,
      async (query) => {
        calls.push([key, query])
        return fn(query)
      },
    ])
  )
  const f = harness(
    'index',
    'loadPage,loadEnums,enumsLoading,enumsError,loadUsers,userOptions,usersLoading,usersError,enumTitle,automationCaseLinks,loadSuites,loadCases,loadRequirementOptions,searchSuites,searchActiveView,resetSearch,resetCaseSearch,onNavigationFilterChange,buildQuery,buildCaseQuery,suites,cases,conditionItems,caseFilter,pagination,casePagination,suiteLoading,caseLoading,requirementLoading,suiteError,caseError,requirementError,requirementOptions,overviewVisible,caseVisible,suiteEditor,caseEditor,suiteSaving,caseSaving,suiteEditorVisible,overviewBusy,deleting,confirming,openSuite,openSuiteVersion,openCase,deleteSuite,deleteCase,goSuite,writeBlocked',
    {
      base,
      api: wrapped,
      modules: {
        '@arco-design/web-vue': {
          Message: Object.fromEntries(
            ['success', 'error', 'warning'].map((key) => [
              key,
              (value) => messages.push([key, value]),
            ])
          ),
          Modal: {
            confirm(config) {
              const handle = {
                close() {
                  config.onClose?.()
                },
              }
              dialogs.push({ config, handle })
              return handle
            },
          },
        },
        vue: {
          ...vue,
          onMounted: (fn) => hooks.mount.push(fn),
          onActivated: (fn) => hooks.activate.push(fn),
          onDeactivated: (fn) => hooks.stop.push(fn),
          onBeforeUnmount: (fn) => hooks.unmount.push(fn),
        },
        'vue-router': { useRoute: () => route, useRouter: () => ({ push() {} }) },
        '@/store/modules/user': { default: () => user },
        '@/store/modules/get-project': {
          useProject: () => ({ projectProductName: overrides.products ?? (async () => {}) }),
        },
        '@/store/modules/get-enum': {
          useEnum: () => ({ getEnum: overrides.enums ?? (async () => {}) }),
        },
        '@/hooks/table': {
          usePagination: (callback) => {
            const pagination = vue.reactive({
              page: 1,
              pageSize: 20,
              pageCount: 0,
              setTotalSize: (total) => (pagination.pageCount = total),
              onChange: () => callback(),
            })
            return pagination
          },
        },
        '@/hooks/use-latest-request': {
          useLatestRequest: () => {
            let sequence = 0
            return {
              beginRequest: () => ++sequence,
              isLatestRequest: (id) => id === sequence,
              invalidateRequests: () => ++sequence,
            }
          },
        },
        xlsx: { utils: {} },
      },
    }
  )
  return {
    ...f,
    route,
    user,
    hooks,
    calls,
    dialogs,
    messages,
    cleanup() {
      hooks.unmount.forEach((fn) => fn())
      f.close()
    },
  }
}
