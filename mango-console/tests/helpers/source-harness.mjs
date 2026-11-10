import path from 'node:path'
import * as vue from 'vue'
import { harness } from './case-details-harness.mjs'
const base = path.resolve('src/views/config/data-source')
export const source = (id = 1, extra = {}) => ({
  id,
  source_category: 0,
  db_type: 0,
  display_name: `Source ${id}`,
  host: 'db.example.com',
  port: 3306,
  user: 'test-user',
  file_path: '',
  ...extra,
})
export function setupSource(name, bindings, api = {}, props = {}) {
  const lifecycle = {},
    route = vue.reactive({ path: '/config/data-source/index', query: {} }),
    user = vue.reactive({ token: 'fixture-session', roleId: 1 }),
    confirmations = [],
    notices = []
  const enums = {
    colors: {},
    data_source_type: [
      { key: 0, title: 'MySQL' },
      { key: 1, title: 'PostgreSQL' },
      { key: 2, title: 'SQLite' },
      { key: 3, title: 'Oracle' },
      { key: 10, title: 'Redis' },
      { key: 20, title: 'Elasticsearch' },
    ],
    data_source_category: [],
    data_source_type_category: { 0: 0, 1: 0, 2: 0, 3: 0, 10: 1, 20: 2 },
    getEnum: async () => {},
  }
  function pagination(callback, loading) {
    return vue.reactive({
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
    })
  }
  const state = harness(name, bindings, {
    base,
    props,
    api,
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
        useRouter: () => ({
          replace: async ({ query }) => {
            route.query = query
          },
        }),
      },
      '@/store/modules/user': { default: () => user },
      '@/store/modules/get-enum': { useEnum: () => enums },
      '@/hooks/table': { usePagination: pagination },
      '@arco-design/web-vue': {
        Message: {
          error: (message) => notices.push(message),
          success: (message) => notices.push(message),
        },
        Notification: {
          success: (item) => notices.push(item),
          error: (item) => notices.push(item),
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
  const close = () => {
    lifecycle.unmount?.()
    state.close()
  }
  return { ...state, lifecycle, route, user, confirmations, notices, enums, dispose: close }
}
