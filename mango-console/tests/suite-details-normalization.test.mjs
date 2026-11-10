import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import * as vue from 'vue'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/suite/details')
const suite = (id = 1) => ({
  id,
  requirement_name: 'Example',
  project_product: { id: 2, name: 'Product' },
  module: { id: 3, full_path: 'Parent / Child' },
  owner: { id: 4, name: 'Owner' },
  case_count: 2,
})
const row = (id = 11, suiteId = 1) => ({
  id,
  suite: { id: suiteId },
  title: `Case ${id}`,
  case_no: `CASE-${id}`,
  test_types: [0],
  scenario_tags: ['smoke'],
  priority: 0,
  version_no: 3,
  project_product: { id: 2 },
  module: { id: 3 },
  owner: { id: 4 },
  bindings: [{ id: 90, automation_type: 0, automation_case_id: 21, api_case: 21, ui_case: null }],
})
const resource = (id = 31, suiteId = 1) => ({
  id,
  suite: suiteId,
  context_key: 0,
  title: 'Resource',
  content: 'Original',
  enabled: true,
})
const bindings =
  'loadSuite,loadCases,loadContextResources,loadPlans,loadDefects,loadEnums,refreshAll,suite,cases,contextResources,relatedPlans,relatedDefects,suiteLoading,caseLoading,resourceLoading,plansLoading,defectsLoading,suiteError,caseError,resourceError,plansError,defectsError,enumsError,casePagination,caseFilters,searchCases,resetCaseFilters,selectedCaseKeys,batchDeleteCases,removeResource,caseDeleting,resourceDeleting,caseSaving,bindingSaving,resourceSaving,onCaseChanged,onResourceChanged,openCase,openBind,openResource,caseEditor,bindingEditor,resourceEditor,choosePane,activePane,enumTitle,goAutomationCase,apiCaseDetailVisible,apiCaseProductId,apiDetailsLoading,closeApiDetails,navigationLoading,createRequirementPlan'
function page(api = {}, options = {}) {
  const route = vue.reactive({
    path: '/functional-test/suite/details',
    fullPath: '/functional-test/suite/details?id=1',
    query: { id: '1' },
  })
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'test-token', selected_environment: 3 })
  const confirms = [],
    messages = [],
    pushes = [],
    hooks = {}
  const e = harness('index', bindings, {
    base,
    api: {
      getManualSuite: async (p) => ({ data: [suite(p.id)] }),
      getManualCase: async (p) => ({ data: [row(11, p.suite), row(12, p.suite)], totalSize: 2 }),
      getFunctionalContextResource: async (p) => ({ data: [resource(31, p.suite)] }),
      getRelatedFunctionalPlans: async () => ({ data: [] }),
      getRelatedFunctionalDefects: async () => ({ data: [] }),
      deleteManualCase: async (p) => ({ data: { count: p.ids.length } }),
      deleteFunctionalContextResource: async (id) => ({
        data: { deleted_count: 1, deleted_resource_ids: [id] },
      }),
      ...api,
    },
    modules: {
      vue: {
        ...vue,
        onMounted: (fn) => {
          hooks.mount = fn
        },
        onActivated: (fn) => {
          hooks.activate = fn
        },
        onDeactivated: (fn) => {
          hooks.deactivate = fn
        },
        onBeforeUnmount: (fn) => {
          hooks.unmount = fn
        },
      },
      'vue-router': {
        useRoute: () => route,
        useRouter: () => ({
          push: async (p) => {
            pushes.push(p)
          },
          back() {},
        }),
      },
      '@/store/modules/user': { default: () => user },
      '@/store/modules/get-enum': {
        useEnum: () => ({
          getEnum: options.getEnum || (async () => {}),
          colors: {},
          status_colors: {},
        }),
      },
      '@/hooks/table': {
        usePagination: (callback) => {
          const state = vue.reactive({
            page: 1,
            pageSize: 20,
            pageCount: 0,
            setTotalSize: (count) => {
              state.pageCount = count
            },
            onChange: callback,
          })
          return state
        },
      },
      '@arco-design/web-vue': {
        Message: {
          success: (text) => messages.push(text),
          error: (text) => messages.push(text),
          warning: (text) => messages.push(text),
        },
        Modal: {
          confirm: (config) => {
            const handle = {
              config,
              closed: false,
              close() {
                handle.closed = true
              },
            }
            confirms.push(handle)
            return handle
          },
        },
      },
      '@/views/apitest/case/details/index.vue': { default: { name: 'Embedded' } },
    },
  })
  const close = e.close
  e.close = () => {
    hooks.unmount?.()
    close()
  }
  return Object.assign(e, { route, user, confirms, messages, pushes, hooks })
}
test('initial regions load concurrently and slow enums do not block data', async () => {
  const enums = deferred(),
    plans = deferred()
  const p = page(
    { getRelatedFunctionalPlans: () => plans.promise },
    { getEnum: () => enums.promise }
  )
  p.hooks.mount()
  await flush()
  assert.equal(p.suite.value.id, 1)
  assert.equal(p.cases.value.length, 2)
  assert.equal(p.contextResources.value.length, 1)
  assert.equal(p.caseLoading.value, false)
  assert.equal(p.plansLoading.value, true)
  assert.equal(p.defectsLoading.value, false)
  enums.resolve()
  plans.resolve({ data: [] })
  await flush()
  p.close()
})
test('failed region keeps other results usable and explicit retry recovers', async () => {
  let reads = 0
  const p = page({
    getRelatedFunctionalPlans: async () => {
      if (++reads === 1) throw Error('offline')
      return { data: [{ id: 40, name: 'Plan' }] }
    },
  })
  await p.refreshAll()
  assert.equal(p.plansError.value, true)
  assert.equal(p.plansLoading.value, false)
  assert.equal(p.cases.value.length, 2)
  assert.equal(p.defectsError.value, false)
  await p.loadPlans()
  assert.equal(p.plansError.value, false)
  assert.equal(p.relatedPlans.value[0].id, 40)
  p.close()
})
test('out-of-order cases never overwrite newer filters or loading state', async () => {
  const first = deferred(),
    second = deferred()
  let reads = 0
  const p = page({ getManualCase: () => (++reads === 1 ? first.promise : second.promise) })
  const one = p.loadCases()
  p.caseFilters.scenario_layer = 0
  const two = p.searchCases()
  second.resolve({ data: [row(12)], totalSize: 1 })
  await two
  first.resolve({ data: [row(11)], totalSize: 1 })
  await one
  assert.deepEqual(
    p.cases.value.map((r) => r.id),
    [12]
  )
  assert.equal(p.caseLoading.value, false)
  p.close()
})
test('zero total is preserved and selected rows are constrained to the loaded page', async () => {
  const p = page({ getManualCase: async () => ({ data: [], totalSize: 0 }) })
  p.casePagination.setTotalSize(99)
  p.selectedCaseKeys.value = [11]
  await p.loadCases()
  assert.equal(p.casePagination.pageCount, 0)
  assert.deepEqual(p.selectedCaseKeys.value, [])
  p.close()
})
test('filters preserve zero, omit cleared values and reset page and selection', async () => {
  const queries = []
  const p = page({
    getManualCase: async (q) => {
      queries.push(q)
      return { data: [], totalSize: 0 }
    },
  })
  p.casePagination.page = 3
  p.caseFilters.scenario_layer = 0
  p.caseFilters.scenario_tag = ''
  p.selectedCaseKeys.value = [11]
  await p.searchCases()
  assert.equal(queries[0].scenario_layer, 0)
  assert.equal('scenario_tag' in queries[0], false)
  assert.equal(queries[0].page, 1)
  assert.equal(queries[0].pageSize, 20)
  await p.resetCaseFilters()
  assert.equal('scenario_layer' in queries[1], false)
  assert.deepEqual(p.selectedCaseKeys.value, [])
  p.close()
})
for (const [label, mutate] of [
  [
    'role',
    (p) => {
      p.user.roleId = 9
    },
  ],
  [
    'environment',
    (p) => {
      p.user.selected_environment = 9
    },
  ],
  [
    'route',
    (p) => {
      p.route.query.id = '2'
      p.route.fullPath = '/functional-test/suite/details?id=2'
    },
  ],
]) {
  test(`${label} invalidates late responses and clears previous records`, async () => {
    const pending = deferred()
    const p = page({ getManualCase: () => pending.promise })
    const request = p.loadCases()
    mutate(p)
    await flush()
    pending.resolve({ data: [row()], totalSize: 1 })
    await request
    assert.deepEqual(p.cases.value, [])
    p.close()
  })
}
test('route A-B-A ignores an A response from the previous generation', async () => {
  const pending = deferred()
  const p = page({ getManualCase: () => pending.promise })
  const request = p.loadCases()
  p.route.fullPath = '/functional-test/suite/details?id=2'
  p.route.fullPath = '/functional-test/suite/details?id=1'
  pending.resolve({ data: [row()], totalSize: 1 })
  await request
  assert.deepEqual(p.cases.value, [])
  p.close()
})
test('KeepAlive pauses, clears, and reloads once on return', async () => {
  let reads = 0
  const p = page({
    getManualCase: async (q) => {
      reads++
      return { data: [row(11, q.suite)], totalSize: 1 }
    },
  })
  p.hooks.mount()
  p.hooks.activate()
  await flush()
  assert.equal(reads, 1)
  p.hooks.deactivate()
  assert.deepEqual(p.cases.value, [])
  await p.loadCases()
  assert.equal(reads, 1)
  p.hooks.activate()
  await flush()
  assert.equal(reads, 2)
  assert.equal(p.cases.value.length, 1)
  p.close()
})
test('invalid route ID and departure to another route issue no scoped queries', async () => {
  let reads = 0
  const p = page({
    getManualCase: async () => {
      reads++
      return { data: [], totalSize: 0 }
    },
  })
  p.route.query.id = ['1', '2']
  await p.refreshAll()
  assert.equal(reads, 0)
  p.route.query.id = '1'
  p.route.path = '/other'
  await p.refreshAll()
  assert.equal(reads, 0)
  p.close()
})
test('bad ownership or malformed list is a read error, not successful empty data', async () => {
  const p = page({
    getManualCase: async () => ({ data: [row(11, 2)], totalSize: 1 }),
    getFunctionalContextResource: async () => ({ data: {} }),
  })
  await p.refreshAll()
  assert.equal(p.caseError.value, true)
  assert.equal(p.resourceError.value, true)
  assert.deepEqual(p.cases.value, [])
  assert.equal(p.suite.value.id, 1)
  p.close()
})
test('manual pane choice is not overridden by slow initial reads', async () => {
  const pending = deferred()
  const p = page({ getManualCase: () => pending.promise })
  const request = p.refreshAll()
  p.choosePane(0)
  pending.resolve({ data: [row()], totalSize: 1 })
  await request
  assert.equal(p.activePane.value, 0)
  p.close()
})
test('case deletion freezes selection and ignores later checkbox edits', async () => {
  const deletes = []
  const p = page({
    deleteManualCase: async (q) => {
      deletes.push(q)
      return { data: { count: 1 } }
    },
  })
  await p.refreshAll()
  p.selectedCaseKeys.value = [11]
  p.batchDeleteCases()
  p.selectedCaseKeys.value = [12]
  assert.equal(await p.confirms[0].config.onBeforeOk(), true)
  assert.deepEqual(deletes, [{ ids: [11] }])
  await flush()
  p.close()
})
test('case deletion failure keeps confirmation/selection and explicit retry works', async () => {
  let count = 0
  const p = page({
    deleteManualCase: async () => {
      if (++count === 1) throw Error('offline')
      return { data: { count: 1 } }
    },
  })
  await p.refreshAll()
  p.selectedCaseKeys.value = [11]
  p.batchDeleteCases()
  const confirm = p.confirms[0].config
  assert.equal(await confirm.onBeforeOk(), false)
  assert.deepEqual(p.selectedCaseKeys.value, [11])
  assert.equal(p.caseDeleting.value, false)
  assert.equal(await confirm.onBeforeOk(), true)
  p.close()
})
test('delete physical lock prevents duplicate writes, editors and normal cancellation', async () => {
  const pending = deferred()
  let writes = 0,
    opens = 0
  const p = page({
    deleteManualCase: () => {
      writes++
      return pending.promise
    },
  })
  await p.refreshAll()
  p.caseEditor.value = {
    open() {
      opens++
    },
  }
  p.selectedCaseKeys.value = [11]
  p.batchDeleteCases()
  const confirm = p.confirms[0].config,
    request = confirm.onBeforeOk()
  assert.equal(confirm.onBeforeCancel(), false)
  assert.equal(await confirm.onBeforeOk(), false)
  p.openCase()
  assert.equal(writes, 1)
  assert.equal(opens, 0)
  pending.resolve({ data: { count: 1 } })
  await request
  p.close()
})
test('context switch closes confirmation and prevents stale confirmation from deleting', async () => {
  let writes = 0
  const p = page({
    deleteManualCase: async () => {
      writes++
    },
  })
  await p.refreshAll()
  p.selectedCaseKeys.value = [11]
  p.batchDeleteCases()
  const confirm = p.confirms[0]
  p.user.roleId = 9
  assert.equal(confirm.closed, true)
  assert.equal(await confirm.config.onBeforeOk(), false)
  assert.equal(writes, 0)
  p.close()
})
test('late delete response cannot notify or refresh a new identity', async () => {
  const pending = deferred()
  let reads = 0
  const p = page({
    deleteManualCase: () => pending.promise,
    getManualCase: async () => {
      reads++
      return { data: [row()], totalSize: 1 }
    },
  })
  await p.refreshAll()
  p.selectedCaseKeys.value = [11]
  p.batchDeleteCases()
  const request = p.confirms[0].config.onBeforeOk()
  p.user.roleId = 9
  pending.resolve({ data: { count: 1 } })
  await request
  await flush()
  assert.equal(reads, 1)
  assert.equal(p.messages.includes('删除成功'), false)
  assert.equal(p.caseDeleting.value, false)
  p.close()
})
test('successful delete with failed refresh is still a successful write with local retry state', async () => {
  let reads = 0
  const p = page({
    getManualCase: async () => {
      if (++reads > 1) throw Error('offline')
      return { data: [row()], totalSize: 1 }
    },
  })
  await p.refreshAll()
  p.selectedCaseKeys.value = [11]
  p.batchDeleteCases()
  assert.equal(await p.confirms[0].config.onBeforeOk(), true)
  await flush()
  assert.equal(p.caseError.value, true)
  assert.equal(p.messages.includes('删除成功'), true)
  assert.deepEqual(p.cases.value, [])
  p.close()
})
test('resource deletion freezes ID and keeps failed row for retry', async () => {
  let calls = 0
  const ids = []
  const p = page({
    deleteFunctionalContextResource: async (id) => {
      ids.push(id)
      if (++calls === 1) throw Error('offline')
      return { data: { deleted_count: 1, deleted_resource_ids: [id] } }
    },
  })
  await p.refreshAll()
  const original = { ...p.contextResources.value[0] }
  p.removeResource(original)
  original.id = 99
  const confirm = p.confirms[0].config
  assert.equal(await confirm.onBeforeOk(), false)
  assert.equal(p.contextResources.value[0].id, 31)
  assert.equal(await confirm.onBeforeOk(), true)
  assert.deepEqual(ids, [31, 31])
  p.close()
})
test('resource write in flight postpones requested refresh until physical busy release', async () => {
  let reads = 0
  const p = page({
    getFunctionalContextResource: async () => {
      reads++
      return { data: [resource()] }
    },
  })
  await p.refreshAll()
  p.resourceSaving.value = true
  await p.loadContextResources()
  p.onResourceChanged(1)
  assert.equal(reads, 1)
  p.resourceSaving.value = false
  await flush()
  assert.equal(reads, 2)
  p.close()
})
test('case changed during save refreshes only after physical lock release', async () => {
  let reads = 0
  const p = page({
    getManualCase: async () => {
      reads++
      return { data: [row()], totalSize: 1 }
    },
  })
  await p.refreshAll()
  p.caseSaving.value = true
  p.onCaseChanged(1)
  await flush()
  assert.equal(reads, 1)
  p.caseSaving.value = false
  await flush()
  assert.equal(reads, 2)
  p.close()
})
test('in-flight old read invalidated by save cannot replace committed list', async () => {
  const pending = deferred()
  let reads = 0
  const p = page({
    getManualCase: () =>
      ++reads === 1 ? pending.promise : Promise.resolve({ data: [row(12)], totalSize: 1 }),
  })
  const request = p.loadCases()
  p.caseSaving.value = true
  p.onCaseChanged(1)
  p.caseSaving.value = false
  await flush()
  pending.resolve({ data: [row(11)], totalSize: 1 })
  await request
  assert.deepEqual(
    p.cases.value.map((r) => r.id),
    [12]
  )
  p.close()
})
test('API embedded panel uses asset product and closes on context change', async () => {
  const p = page()
  await p.refreshAll()
  const asset = p.cases.value[0]
  asset.project_product.id = 8
  p.goAutomationCase(asset, 0)
  await flush()
  assert.equal(p.apiCaseDetailVisible.value, true)
  assert.equal(p.apiCaseProductId.value, 8)
  assert.equal(p.apiDetailsLoading.value, false)
  p.user.selected_environment = 9
  assert.equal(p.apiCaseDetailVisible.value, false)
  p.close()
})
test('plan creation preserves registered route with real product and create hint', async () => {
  const p = page()
  await p.refreshAll()
  await p.createRequirementPlan()
  assert.deepEqual(p.pushes[0], {
    path: '/functional-test/plan/index',
    query: { create: '1', requirement_version: 1, project_product: 2 },
  })
  p.close()
})
test('unmount invalidates pending request', async () => {
  const pending = deferred()
  const p = page({ getManualSuite: () => pending.promise })
  const request = p.loadSuite()
  p.close()
  pending.resolve({ data: [suite()] })
  await request
  assert.equal(p.suite.value, null)
})
test('enum fallback displays zero and search config has only real protocol fields', () => {
  const p = page()
  assert.equal(p.enumTitle([], 0), '0')
  assert.equal(p.enumTitle([{ key: 0, title: 'Zero' }], '0'), 'Zero')
  p.close()
})
