import path from 'node:path'
import * as vue from 'vue'
import { harness } from './case-details-harness.mjs'
const base = path.resolve('src/views/config/test-object')
export const targetRecord = (id = 1, extra = {}) => ({
  id,
  name: `Target ${id}`,
  project_product: { id: 10, name: 'Product' },
  environment: 0,
  auto_type: 0,
  value: '',
  target_config: {
    default: 'https://example.com',
    selector: 'tenant',
    mapping: { first: 'https://example.org' },
  },
  network_test_addresses: [
    { label: '默认地址', value: 'https://example.com' },
    { label: '条件值：first', value: 'https://example.org' },
  ],
  ...extra,
})
export function setupTarget(name, bindings, api = {}, props = {}) {
  const lifecycle = {},
    route = vue.reactive({
      path: '/config/test-object/index',
      query: { id: '10', name: 'Project' },
    }),
    user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-session' }),
    dialogs = [],
    notices = []
  const state = harness(name, bindings, {
    base,
    api,
    props,
    modules: {
      vue: {
        ...vue,
        onMounted: (f) => (lifecycle.mount = f),
        onActivated: (f) => (lifecycle.activate = f),
        onDeactivated: (f) => (lifecycle.deactivate = f),
        onBeforeUnmount: (f) => (lifecycle.unmount = f),
      },
      'vue-router': { useRoute: () => route },
      '@/store/modules/user': { default: () => user },
      '@/store/modules/get-enum': {
        useEnum: () => ({
          environment_type: [{ key: 0, title: '测试' }],
          auto_type: [{ key: 0, title: 'API' }],
          colors: { 0: 'blue' },
        }),
      },
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
          success: (m) => notices.push(['success', m]),
          error: (m) => notices.push(['error', m]),
        },
        Modal: {
          confirm: (config) => {
            const d = {
              config,
              closed: false,
              close() {
                d.closed = true
                config.onClose?.()
              },
            }
            dialogs.push(d)
            return d
          },
        },
      },
    },
  })
  return {
    ...state,
    lifecycle,
    route,
    user,
    dialogs,
    notices,
    dispose() {
      lifecycle.unmount?.()
      state.close()
    },
  }
}
