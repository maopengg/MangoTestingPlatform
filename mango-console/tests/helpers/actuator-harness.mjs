import path from 'node:path'
import * as vue from 'vue'
import { harness, flush } from './case-details-harness.mjs'
export function setupActuator(name, bindings, api = {}) {
  const lifecycle = {},
    route = vue.reactive({ path: '/equipment/actuator/index', query: {} }),
    user = vue.reactive({
      userId: 1,
      roleId: 1,
      token: 'fixture-session',
      selected_environment: 0,
    }),
    notices = []
  const state = harness(name, bindings, {
    base: path.resolve('src/views/equipment/actuator'),
    api,
    modules: {
      vue: {
        ...vue,
        onMounted: (fn) => (lifecycle.mount = fn),
        onActivated: (fn) => (lifecycle.activate = fn),
        onDeactivated: (fn) => (lifecycle.deactivate = fn),
        onBeforeUnmount: (fn) => (lifecycle.unmount = fn),
      },
      'vue-router': { useRoute: () => route },
      '@/store/modules/user': { default: () => user },
      '@arco-design/web-vue': {
        Message: { success: (m) => notices.push(m), error: (m) => notices.push(m) },
      },
      '@arco-design/web-vue/es/icon': { IconUser: {} },
    },
  })
  return {
    ...state,
    route,
    user,
    lifecycle,
    notices,
    dispose() {
      lifecycle.unmount?.()
      state.close()
    },
  }
}
export function fakeTimers() {
  const originalSet = globalThis.setTimeout,
    originalClear = globalThis.clearTimeout,
    jobs = new Map()
  let id = 0
  globalThis.setTimeout = (fn, ms) => {
    jobs.set(++id, { fn, ms })
    return id
  }
  globalThis.clearTimeout = (id) => jobs.delete(id)
  return {
    jobs,
    async tick() {
      await flush()
      const job = jobs.entries().next().value
      if (job) {
        jobs.delete(job[0])
        job[1].fn()
      }
      await flush()
    },
    restore() {
      globalThis.setTimeout = originalSet
      globalThis.clearTimeout = originalClear
    },
  }
}
export const actuator = (username = 'worker-a', extra = {}) => ({
  id: 1,
  name: 'Example',
  username,
  ip: '192.0.2.1',
  type: 'pytest_web',
  is_open: false,
  debug: false,
  ...extra,
})
export const readApi = (config = {}) => ({
  postSystemSocketActuatorConfigRequest: async () => ({ data: { request_id: 'read-fixture' } }),
  getSystemSocketActuatorConfigResult: async () => ({ data: { status: 'success', config } }),
})
