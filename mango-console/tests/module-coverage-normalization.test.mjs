import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync, readdirSync } from 'node:fs'
import { reactive, ref } from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
import { coveragePage } from './helpers/coverage-harness.mjs'
const base = path.resolve('src/views/apitest/module-coverage')
function panel(name, bindings, api = {}, options = {}) {
  return harness(name, bindings, {
    base,
    api,
    modules: { 'html-to-image': { toBlob: async () => new Blob() }, ...options.modules },
  })
}
const pageResult = (items, count = items.length) => ({ data: { items, count } })
const record = (id, values = {}) => ({
  id,
  name: `Case ${id}`,
  module: { id: 10 },
  status: 'pending_create',
  ...values,
})
const overview = (id) => ({ modules: [{ id, parent_id: null }], summary: {} })
test('module coverage entry and nine associated components compile scripts/templates', () => {
  for (const file of [
    'index.vue',
    ...readdirSync(path.join(base, 'components')).map((name) => 'components/' + name),
  ]) {
    const filename = path.join(base, file),
      { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: file })
    assert.deepEqual(
      compileTemplate({
        filename,
        id: file,
        source: descriptor.template.content,
        compilerOptions: { bindingMetadata: script.bindings },
      }).errors,
      []
    )
  }
})
test('filter factories isolate arrays and query protocols preserve single values, collections, zero and module scope', () => {
  const state = coveragePage(),
    { createCoverageFilters, coverageQuery } = state.load('query.ts'),
    first = createCoverageFilters(),
    second = createCoverageFilters()
  first.methods.push('GET')
  assert.deepEqual(second.methods, [])
  Object.assign(first, {
    interface_status: 'removed',
    coverage_policy: 'excluded',
    analysis_statuses: ['completed'],
    scenario_layer: 0,
    repository_key: ' Example ',
    api_info_id: 2,
  })
  const scope = { projectProduct: 0, module: 10, moduleIds: [10, 11] }
  assert.deepEqual(coverageQuery('interfaces', first, scope, 3, 50), {
    project_product: 0,
    repository_key: 'Example',
    module__in: '10,11',
    page: 3,
    pageSize: 50,
    status: 'removed',
    coverage_policy: 'excluded',
    api_info_id: 2,
    include_removed: true,
    analysis_status__in: 'completed',
    method__in: 'GET',
  })
  assert.equal(coverageQuery('cases', first, scope).scenario_layer, 0)
  assert.equal('name' in coverageQuery('scans', first, scope), false)
  assert.equal('page' in coverageQuery('overview', first, scope), false)
  state.close()
})
test('same-scope overview failures retain data; changed scope and late response are isolated', async () => {
  const pending = [],
    state = coveragePage({
      getCoverageOverview: (params) =>
        new Promise((resolve, reject) => pending.push({ params, resolve, reject })),
    })
  state.projectProductId.value = 1
  const first = state.loadOverview()
  pending[0].resolve({ data: overview(1) })
  await first
  const retry = state.loadOverview()
  assert.equal(state.overview.value.modules[0].id, 1)
  pending[1].reject(Error('read'))
  await retry
  assert.equal(state.overviewError.value, true)
  assert.equal(state.overview.value.modules[0].id, 1)
  const old = state.loadOverview()
  state.projectProductId.value = 2
  const next = state.loadOverview()
  assert.equal(state.overview.value, undefined)
  pending[2].resolve({ data: overview(1) })
  await old
  assert.equal(state.overviewLoading.value, true)
  pending[3].resolve({ data: overview(2) })
  await next
  assert.equal(state.overview.value.modules[0].id, 2)
  state.close()
})
test('tab and navigation changes clear prior row scope and reject old results even after failure', async () => {
  const pending = deferred()
  const state = coveragePage({
    getCoverageInterfaces: () => pending.promise,
    getCoverageCases: async () => {
      throw Error('cases')
    },
  })
  state.activeTab.value = 'interfaces'
  const old = state.loadRows()
  state.rows.value = [record(1)]
  state.activeTab.value = 'cases'
  state.onTabChange()
  await flush()
  assert.deepEqual(state.rows.value, [])
  assert.equal(state.rowsError.value, true)
  pending.resolve(pageResult([record(9)]))
  await old
  assert.deepEqual(state.rows.value, [])
  assert.equal(state.loading.value, false)
  state.close()
})
test('same-scope list retry retains data while navigation and reset restart pagination', async () => {
  let fail = true
  const state = coveragePage({
    getCoverageInterfaces: async () => {
      if (fail) throw Error()
      return pageResult([record(2)])
    },
  })
  state.activeTab.value = 'interfaces'
  state.rows.value = [record(1)]
  await state.loadRows()
  assert.equal(state.rows.value[0].id, 1)
  state.pagination.page = 5
  state.onNavigationFilterChange({ projectProduct: 2, module: 10, moduleIds: [10, 11] })
  await flush()
  assert.equal(state.pagination.page, 1)
  assert.deepEqual(state.rows.value, [])
  fail = false
  await state.loadRows()
  assert.equal(state.rows.value[0].id, 2)
  state.filters.methods = ['GET']
  state.resetFilters()
  await flush()
  assert.deepEqual(state.filters.methods, [])
  state.close()
})
test('overview drill includes descendants, resets pages and carries only supported multi filters', async () => {
  const requests = [],
    state = coveragePage({
      getCoverageInterfaces: async (query) => {
        requests.push(query)
        return pageResult([])
      },
    })
  state.overview.value = {
    ...overview(1),
    modules: [
      { id: 1, parent_id: null },
      { id: 2, parent_id: 1 },
      { id: 3, parent_id: 2 },
      { id: 4, parent_id: null },
    ],
  }
  state.pagination.page = 4
  state.drillOverview({ id: 1, project_product_id: 2 }, 'interfaces', {
    analysis_statuses: ['gap'],
  })
  await flush()
  assert.equal(requests[0].module__in, '1,2,3')
  assert.equal(requests[0].page, 1)
  assert.equal(requests[0].analysis_status__in, 'gap')
  state.close()
})
test('deactivation invalidates reads, closes embedded assets and stale archive cannot start', async () => {
  let writes = 0
  const pending = deferred(),
    state = coveragePage({
      getCoverageCases: () => pending.promise,
      archiveCoverageCases: async () => {
        writes++
      },
    })
  state.activeTab.value = 'cases'
  const read = state.loadRows()
  state.archiveRow(record(1))
  state.openApiInfo(2)
  state.deactivate()
  assert.equal(state.assetPanel.visible, false)
  assert.equal(await state.confirmations[0].options.onBeforeOk(), false)
  assert.equal(writes, 0)
  pending.resolve(pageResult([record(9)]))
  await read
  assert.deepEqual(state.rows.value, [])
  assert.equal(state.loading.value, false)
  state.close()
})
test('archive freezes ID, prevents duplicate writes and retains confirmation after failure', async () => {
  let fail = true
  const writes = [],
    pending = deferred(),
    state = coveragePage({
      archiveCoverageCases: async (ids) => {
        writes.push(ids)
        if (fail) throw Error()
        return pending.promise
      },
    })
  const row = record(1)
  state.archiveRow(row)
  row.id = 2
  const confirm = state.confirmations[0].options
  assert.equal(await confirm.onBeforeOk(), false)
  assert.equal(state.archivingIds.size, 0)
  fail = false
  const task = confirm.onBeforeOk()
  assert.equal(await confirm.onBeforeOk(), false)
  pending.resolve({ data: {} })
  await task
  assert.deepEqual(writes, [[1], [1]])
  state.close()
})
test('Case detail resets missing fields between targets and rejects closed/older reads', async () => {
  const pending = [],
    state = panel('CoverageCaseDetailDrawer', 'open,close,load,detail,loading,failed', {
      getCoverageCaseDetail: (id) => new Promise((resolve) => pending.push({ id, resolve })),
    })
  const old = state.open(1),
    next = state.open(2)
  pending[1].resolve({ data: record(2) })
  await next
  pending[0].resolve({ data: record(1, { api_case: 4 }) })
  await old
  assert.equal(state.detail.value.id, 2)
  assert.equal(state.detail.value.api_case, undefined)
  const last = state.open(3)
  state.exposed.close()
  pending[2].resolve({ data: record(3) })
  await last
  assert.equal(state.detail.value.id, 0)
  assert.equal(state.loading.value, false)
  state.close()
})
test('Case diff releases loading on failure and retries without stale prior payload', async () => {
  let fail = true
  const state = panel('CaseDiffDrawer', 'open,loadDiff,diff,failed,loading', {
    getCoverageCaseDiff: async () => {
      if (fail) throw Error()
      return { data: { current: { id: 2, payload: { remark: 'new' } } } }
    },
  })
  await state.open(1)
  assert.equal(state.failed.value, true)
  assert.equal(state.loading.value, false)
  fail = false
  await state.loadDiff()
  assert.equal(state.diff.value.current.id, 2)
  state.close()
})
test('binding opens with loading, blocks incomplete options and ignores target-switch option races', async () => {
  const pending = [],
    writes = [],
    state = panel(
      'CoverageBindingModal',
      'open,loadOptions,save,visible,optionsLoading,options,form,failed',
      {
        getApiCaseName: (id) => new Promise((resolve) => pending.push({ id, resolve })),
        bindCoverageApiCase: async (...ids) => writes.push(ids),
      }
    )
  const first = state.open(record(1, { module: { id: 10 } }))
  assert.equal(state.visible.value, true)
  assert.equal(state.optionsLoading.value, true)
  assert.equal(await state.save(), false)
  const second = state.open(record(2, { module: { id: 20 } }))
  pending[1].resolve({ data: [{ key: 3, title: 'Case' }] })
  await second
  pending[0].resolve({ data: [{ key: 4, title: 'Old' }] })
  await first
  assert.equal(state.options.value[0].key, 3)
  state.form.apiCaseId = 3
  assert.equal(await state.save(), true)
  assert.deepEqual(writes, [[2, 3]])
  state.close()
})
test('binding read/save failures remain retryable; close suppresses late success event', async () => {
  let readFail = true
  const pending = deferred(),
    state = panel('CoverageBindingModal', 'open,loadOptions,save,visible,form,failed,saving', {
      getApiCaseName: async () => {
        if (readFail) throw Error()
        return { data: [] }
      },
      bindCoverageApiCase: () => pending.promise,
    })
  await state.open(record(1))
  assert.equal(state.failed.value, true)
  readFail = false
  await state.loadOptions()
  state.form.apiCaseId = 3
  const save = state.save()
  assert.equal(await state.save(), false)
  state.exposed.close()
  pending.resolve({ data: {} })
  await save
  assert.equal(state.events.filter((e) => e[0] === 'saved').length, 0)
  assert.equal(state.saving.value, false)
  state.close()
})
test('policy requires reason, freezes target/payload and retries failed writes', async () => {
  let fail = true
  const requests = [],
    state = panel('CoveragePolicyModal', 'open,save,form,saving,visible', {
      updateCoverageInterfacePolicy: async (...args) => {
        requests.push(args)
        if (fail) throw Error()
        return { data: {} }
      },
    })
  state.open(record(1, { coverage_policy: 'excluded' }))
  assert.equal(await state.save(), false)
  assert.equal(requests.length, 0)
  state.form.reason = ' reason '
  assert.equal(await state.save(), false)
  assert.equal(state.visible.value, true)
  assert.equal(state.saving.value, false)
  fail = false
  assert.equal(await state.save(), true)
  assert.deepEqual(requests[1], [[1], 'excluded', 'reason'])
  assert.equal(state.events.at(-1)[0], 'saved')
  state.close()
})
test('policy save is duplicate guarded and cannot emit after close', async () => {
  const pending = deferred(),
    state = panel('CoveragePolicyModal', 'open,save,form,saving', {
      updateCoverageInterfacePolicy: () => pending.promise,
    })
  state.open(record(1))
  const task = state.save()
  assert.equal(await state.save(), false)
  state.form.id = 2
  state.exposed.close()
  pending.resolve({ data: {} })
  await task
  assert.equal(state.events.length, 0)
  assert.equal(state.saving.value, false)
  state.close()
})
test('Case history pagination rejects old pages and target opens reset totals', async () => {
  const pending = [],
    state = panel('CaseHistoryDrawer', 'open,loadRows,rows,page,total,loading', {
      getCoverageCaseSnapshots: (id, page) =>
        new Promise((resolve) => pending.push({ id, page, resolve })),
    })
  const first = state.open(1)
  state.page.value = 2
  const second = state.loadRows()
  pending[1].resolve(pageResult([{ id: 20 }], 30))
  await second
  pending[0].resolve(pageResult([{ id: 10 }], 10))
  await first
  assert.equal(state.rows.value[0].id, 20)
  assert.equal(state.total.value, 30)
  const third = state.open(2)
  assert.deepEqual(state.rows.value, [])
  assert.equal(state.total.value, 0)
  state.exposed.close()
  pending[2].resolve(pageResult([{ id: 30 }]))
  await third
  assert.deepEqual(state.rows.value, [])
  state.close()
})
test('interface history closes nested diff and late diff cannot replace a new interface', async () => {
  const diff = deferred(),
    state = panel('InterfaceHistoryDrawer', 'open,openDiff,diff,diffVisible,rows,loading', {
      getCoverageInterfaceSnapshots: async (id) =>
        pageResult([{ id: id * 10 }, { id: id * 10 - 1 }], 200),
      getCoverageInterfaceDiff: () => diff.promise,
    })
  await state.open(1)
  const task = state.openDiff(10, 9)
  await state.open(2)
  diff.resolve({ data: { current: { id: 10 } } })
  await task
  assert.equal(state.diffVisible.value, false)
  assert.equal(state.rows.value[0].id, 20)
  assert.equal(state.diff.value.current, undefined)
  state.close()
})
test('scan detail loads independent regions and one failed region can retry alone', async () => {
  const pending = deferred()
  let validationCalls = 0
  const state = panel(
    'ScanDetailDrawer',
    'open,loadValidation,detail,detailLoading,validationLoading,validationFailed,validation,uploadStatus,uploadLoading',
    {
      getCoverageScanDetail: async (id) => ({ data: record(id) }),
      getCoverageScanValidation: async () => {
        validationCalls++
        if (validationCalls === 1) throw Error()
        return { data: { received_case_count: 0 } }
      },
      getCoverageScanUploadStatus: () => pending.promise,
    }
  )
  const open = state.open(1)
  await flush()
  assert.equal(state.detail.value.id, 1)
  assert.equal(state.detailLoading.value, false)
  assert.equal(state.validationFailed.value, true)
  assert.equal(state.uploadLoading.value, true)
  await state.loadValidation()
  assert.equal(state.validation.value.received_case_count, 0)
  pending.resolve({ data: { count: 0, items: [] } })
  await open
  assert.equal(state.uploadLoading.value, false)
  state.close()
})
test('scan upload pagination snapshots target/page and ignores closed results', async () => {
  const pending = [],
    state = panel('ScanDetailDrawer', 'open,loadUploadStatus,uploadStatus,uploadLoading,page', {
      getCoverageScanDetail: async () => ({ data: record(1) }),
      getCoverageScanValidation: async () => ({ data: {} }),
      getCoverageScanUploadStatus: (id, page) =>
        new Promise((resolve) => pending.push({ id, page, resolve })),
    })
  const first = state.open(1)
  state.page.value = 2
  const next = state.loadUploadStatus()
  pending[1].resolve({
    data: { count: 40, items: [{ source_key: 'new', sync_action: 'created' }] },
  })
  await next
  pending[0].resolve({ data: { items: [{ source_key: 'old' }] } })
  await first
  assert.equal(state.uploadStatus.value.items[0].source_key, 'new')
  const last = state.loadUploadStatus()
  state.exposed.close()
  pending[2].resolve({ data: { items: [{ source_key: 'closed' }] } })
  await last
  assert.equal(state.uploadStatus.value.items[0].source_key, 'new')
  assert.equal(state.uploadLoading.value, false)
  state.close()
})
test('flow closes pending interface reads and IDs form distinct panel keys', async () => {
  const pending = [],
    state = panel('CaseFlowDrawer', 'open,openMany,interfaceKey,interfaceItems,loading,visible', {
      getCoverageInterfaceDetail: (query) =>
        new Promise((resolve) => pending.push({ query, resolve })),
    })
  assert.notEqual(state.interfaceKey({ id: 1 }), state.interfaceKey({ id: 2 }))
  const task = state.open({ id: 1 })
  state.exposed.close()
  pending[0].resolve({ data: { id: 1, cases: [], mermaid: '' } })
  await task
  assert.equal(state.visible.value, false)
  assert.deepEqual(state.interfaceItems.value, [])
  assert.equal(state.loading.value, false)
  state.close()
})
test('flow popup requests ignore close and older popup sessions', async () => {
  const pending = [],
    state = panel(
      'CaseFlowDrawer',
      'visible,onCaseDetailVisible,caseDetailCache,caseDetailLoading,caseDetailErrors',
      { getCoverageCaseDetail: (id) => new Promise((resolve) => pending.push({ id, resolve })) }
    )
  state.visible.value = true
  const task = state.onCaseDetailVisible(record(1), true)
  await state.onCaseDetailVisible(record(1), false)
  pending[0].resolve({ data: record(1) })
  await task
  assert.equal(state.caseDetailCache[1], undefined)
  assert.equal(state.caseDetailLoading[1], false)
  state.close()
})

test('chart update queued before disposal cannot initialize charts after unmount', async () => {
  const originalWindow = globalThis.window
  globalThis.window = { addEventListener() {}, removeEventListener() {} }
  let initialized = 0,
    disposed = 0
  const state = panel(
    'CoverageOverview',
    'update,scanChart',
    {},
    {
      modules: {
        'echarts/components': { TitleComponent: {} },
        'echarts/core': {
          use() {},
          dispose() {
            disposed++
          },
        },
        '@/hooks/useEcharts': {
          default: () => {
            initialized++
            return { getOption: () => ({}), setOption() {}, resize() {} }
          },
        },
        '@/hooks/table': {
          usePagination: () => reactive({ page: 1, pageSize: 20, setTotalSize() {} }),
        },
      },
    }
  )
  try {
    state.scanChart.value = {}
    const task = state.update()
    state.close()
    await task
    assert.equal(initialized, 0)
  } finally {
    globalThis.window = originalWindow
  }
})

test('flow close prevents the second stage of a delayed Case-to-interface lookup', async () => {
  const pending = deferred()
  let interfaceRequests = 0
  const state = panel('CaseFlowDrawer', 'open,loading', {
    getCoverageCaseFlow: () => pending.promise,
    getCoverageInterfaceDetail: async () => {
      interfaceRequests++
      return { data: { id: 2, cases: [], mermaid: '' } }
    },
  })
  const task = state.open(record(1), 1)
  state.exposed.close()
  pending.resolve({ data: { coverage_interface_id: 2 } })
  await task
  assert.equal(interfaceRequests, 0)
  assert.equal(state.loading.value, false)
  state.close()
})

test('scroll widths equal every visible column and action columns use global width', () => {
  const state = coveragePage(),
    config = state.load('config.ts')
  for (const [tab, key] of [
    ['interfaces', 'interfaceColumns'],
    ['cases', 'caseColumns'],
    ['scans', 'scanColumns'],
  ]) {
    const columns = config[key]
    assert.equal(
      config.tableScrollXByTab[tab],
      columns.reduce((sum, item) => sum + item.width, 0)
    )
    assert.equal(columns.at(-1).width, 160)
  }
  assert.equal(config.overviewModuleColumns.at(-1).width, 160)
  assert.equal(
    config.overviewModuleScrollX,
    config.overviewModuleColumns.reduce((sum, item) => sum + item.width, 0)
  )
  state.close()
})
