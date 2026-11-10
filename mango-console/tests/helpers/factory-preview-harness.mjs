import path from 'node:path'
import * as vue from 'vue'
import { harness } from './case-details-harness.mjs'
export const base = path.resolve('src/views/data-factory/template/preview')
export function setupPreview(name, bindings, api = {}, props = {}, filename) {
  const lifecycle = {},
    route = vue.reactive({
      path: '/data-factory/template/preview',
      query: { template_id: '1', test_env: 0 },
    }),
    user = vue.reactive({ token: 'fixture-session', roleId: 1, selected_environment: 0 }),
    notices = [],
    confirmations = [],
    navigations = [],
    records = [],
    pageData = vue.reactive({ record: null })
  const enums = {
    colors: {},
    data_source_category: [
      { key: 0, title: 'DB' },
      { key: 1, title: 'Cache' },
      { key: 2, title: 'Search' },
    ],
    data_source_type: [
      { key: 0, title: 'MySQL' },
      { key: 1, title: 'PostgreSQL' },
      { key: 2, title: 'SQLite' },
      { key: 10, title: 'Redis' },
      { key: 20, title: 'Elasticsearch' },
    ],
    data_source_type_category: { 0: 0, 1: 0, 2: 0, 10: 1, 20: 2 },
    environment_type: [
      { key: 0, title: 'Test' },
      { key: 1, title: 'Stage' },
      { key: 2, title: 'Production' },
    ],
    getEnum: async () => {},
  }
  const state = harness(name, bindings, {
    base,
    api,
    props,
    filename,
    modules: {
      vue: {
        ...vue,
        onMounted: (fn) => (lifecycle.mount = fn),
        onActivated: (fn) => (lifecycle.activate = fn),
        onDeactivated: (fn) => (lifecycle.deactivate = fn),
        onBeforeUnmount: (fn) => (lifecycle.unmount = fn),
      },
      'vue-router': {
        useRoute: () => route,
        onBeforeRouteLeave: (fn) => (lifecycle.leave = fn),
        onBeforeRouteUpdate: (fn) => (lifecycle.update = fn),
        useRouter: () => ({ push: async (to) => navigations.push(to) }),
      },
      '@/store/page-data': {
        usePageData: () => ({
          get record() {
            return pageData.record
          },
          setRecord: (record) => {
            records.push(record)
            pageData.record = record
          },
        }),
      },
      '@/store/modules/user': { default: () => user },
      '@/store/modules/get-enum': { useEnum: () => enums },
      '@/hooks/table': {
        useTableIndexColumn: () => ({ key: 'index' }),
        useTableColumn: (columns) => columns,
        usePagination: (callback, loading) =>
          vue.reactive({
            page: 1,
            pageSize: 20,
            pageCount: 0,
            setTotalSize(total) {
              this.pageCount = total
            },
            onChange() {
              loading.value = true
              return callback()
            },
          }),
      },
      '@arco-design/web-vue': {
        Message: {
          success: (m) => notices.push(m),
          error: (m) => notices.push(m),
          warning: (m) => notices.push(m),
        },
        Modal: {
          confirm: (config) => {
            const dialog = {
              config,
              closed: false,
              close() {
                this.closed = true
                config.onClose?.()
              },
            }
            confirmations.push(dialog)
            return dialog
          },
        },
      },
    },
  })
  return {
    ...state,
    close: state.exposed?.close ?? state.close,
    lifecycle,
    route,
    user,
    notices,
    confirmations,
    navigations,
    records,
    pageData,
    enums,
    dispose() {
      lifecycle.unmount?.()
      state.close()
    },
  }
}
