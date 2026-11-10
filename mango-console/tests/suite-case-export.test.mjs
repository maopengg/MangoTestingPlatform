import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import ts from 'typescript'
import * as vue from 'vue'
import { deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/suite')
const row = (id, extra = {}) => ({ id, title: `Case ${id}`, ...extra })
const page = (data, totalSize = data.length) => ({ data, totalSize })
function fixture(fetch = async () => page([row(1)])) {
  const calls = [],
    downloads = [],
    messages = [],
    hooks = {},
    cache = new Map()
  const state = vue.reactive({
    context: 'one',
    query: { title: 'original', priority: 0, page: 8, pageSize: 20, empty: '', nil: null },
  })
  const enums = {
    testTypes: [{ key: 0, title: 'API' }],
    priorities: [{ key: 0, title: 'High' }],
    layers: [],
    types: [],
    tags: [],
    changes: [],
    impacts: [],
  }
  const modules = {
    vue: {
      ...vue,
      onActivated: (fn) => (hooks.activate = fn),
      onDeactivated: (fn) => (hooks.deactivate = fn),
      onBeforeUnmount: (fn) => (hooks.unmount = fn),
    },
    '@arco-design/web-vue': {
      Message: Object.fromEntries(
        ['warning', 'error', 'success'].map((key) => [key, (text) => messages.push([key, text])])
      ),
    },
    '@/api/functional-test': {
      getManualCaseExport: async (query) => {
        calls.push({ ...query })
        return fetch(query)
      },
    },
    xlsx: {
      utils: {
        json_to_sheet: (rows) => rows,
        book_new: () => ({}),
        book_append_sheet: (book, sheet, title) => Object.assign(book, { sheet, title }),
      },
      writeFile: (book, name) => downloads.push({ book, name }),
    },
  }
  function load(filename) {
    if (cache.has(filename)) return cache.get(filename)
    const exports = {}
    cache.set(filename, exports)
    const compiled = ts.transpileModule(readFileSync(filename, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText
    new Function('exports', 'require', compiled)(exports, (id) => {
      if (id in modules) return modules[id]
      if (id.startsWith('@/')) return load(path.resolve('src', id.slice(2)) + '.ts')
      if (id.startsWith('.')) return load(path.resolve(path.dirname(filename), id) + '.ts')
      { if (['@/utils/load-error', '@/utils/api-response'].includes(id)) return loadFeedbackModule(id); throw Error(`Unmocked dependency ${id}`) }
    })
    return exports
  }
  const scope = vue.effectScope()
  const result = scope.run(() =>
    load(path.join(base, 'composables/useCaseExport.ts')).useCaseExport({
      contextKey: () => state.context,
      query: () => state.query,
      enums: () => enums,
    })
  )
  return {
    ...result,
    state,
    enums,
    calls,
    downloads,
    messages,
    hooks,
    mapping: load(path.join(base, 'export-rows.ts')),
    close: () => {
      hooks.unmount()
      scope.stop()
    },
  }
}

test('all pages retain the initial filters and enum labels; zero and empty conditions have distinct semantics', async () => {
  const pending = deferred()
  const f = fixture((query) =>
    query.page === 1 ? pending.promise : page([row(1001, { priority: 0 })], 1001)
  )
  const exporting = f.exportCases()
  assert.equal(f.exportLoading.value, true)
  f.state.query.title = 'new'
  f.enums.priorities[0].title = 'Changed'
  pending.resolve(
    page(
      Array.from({ length: 1000 }, (_, i) => row(i + 1)),
      1001
    )
  )
  await exporting
  assert.deepEqual(
    f.calls,
    [1, 2].map((page) => ({ title: 'original', priority: 0, page, pageSize: 1000 }))
  )
  assert.equal(f.downloads[0].book.sheet.length, 1001)
  assert.equal(f.downloads[0].book.sheet[1000].优先级, 'High')
  assert.equal(f.downloads[0].book.title, '测试用例')
  assert.match(f.downloads[0].name, /^功能测试用例_.*\.xlsx$/)
  assert.equal(f.exportLoading.value, false)
  f.close()
})
test('duplicate click is blocked while the actual request remains pending', async () => {
  const pending = deferred(),
    f = fixture(() => pending.promise)
  const exporting = f.exportCases()
  await f.exportCases()
  assert.equal(f.calls.length, 1)
  pending.resolve(page([row(1)]))
  await exporting
  assert.equal(f.downloads.length, 1)
  f.close()
})
for (const transition of [
  'context',
  'context-roundtrip',
  'deactivate',
  'deactivate-reactivate',
  'unmount',
]) {
  test(`${transition} prevents late download, notices and continuation pages`, async () => {
    const pending = deferred(),
      f = fixture(() => pending.promise)
    const exporting = f.exportCases()
    if (transition.startsWith('context')) {
      f.state.context = 'two'
      if (transition.endsWith('roundtrip')) f.state.context = 'one'
    } else if (transition === 'unmount') f.hooks.unmount()
    else {
      f.hooks.deactivate()
      if (transition.endsWith('reactivate')) f.hooks.activate()
    }
    await f.exportCases()
    assert.equal(f.calls.length, 1)
    pending.resolve(
      page(
        Array.from({ length: 1000 }, (_, i) => row(i + 1)),
        1001
      )
    )
    await exporting
    assert.equal(f.calls.length, 1)
    assert.equal(f.downloads.length, 0)
    assert.equal(f.messages.length, 0)
    assert.equal(f.exportLoading.value, false)
    f.close()
  })
}
test('reactivated page can explicitly retry after the old request settles', async () => {
  const pending = deferred()
  let first = true
  const f = fixture(() => {
    if (first) {
      first = false
      return pending.promise
    }
    return page([row(2)])
  })
  const exporting = f.exportCases()
  f.hooks.deactivate()
  f.hooks.activate()
  pending.resolve(page([row(1)]))
  await exporting
  await f.exportCases()
  assert.equal(f.downloads.length, 1)
  assert.equal(f.downloads[0].book.sheet[0].ID, 2)
  f.close()
})
test('failure releases loading, records local error and permits explicit retry', async () => {
  let failing = true
  const f = fixture(() => {
    if (failing) throw Error('Network')
    return page([row(2)])
  })
  await f.exportCases()
  assert.equal(f.exportError.value, true)
  assert.equal(f.exportLoading.value, false)
  assert.equal(f.downloads.length, 0)
  failing = false
  await f.exportCases()
  assert.equal(f.exportError.value, false)
  assert.equal(f.downloads.length, 1)
  f.close()
})
test('stale rejection stays silent and clears loading', async () => {
  const pending = deferred(),
    f = fixture(() => pending.promise)
  const exporting = f.exportCases()
  f.state.context = 'two'
  pending.reject(Error('late'))
  await exporting
  assert.equal(f.messages.length, 0)
  assert.equal(f.exportError.value, false)
  assert.equal(f.exportLoading.value, false)
  f.close()
})
test('valid zero count does not produce a workbook', async () => {
  const f = fixture(() => page([]))
  await f.exportCases()
  assert.equal(f.downloads.length, 0)
  assert.equal(f.exportError.value, false)
  assert.equal(f.messages[0][0], 'warning')
  f.close()
})
for (const invalid of [
  null,
  {},
  { data: {}, totalSize: 0 },
  { data: [], totalSize: -1 },
  { data: [], totalSize: '1' },
  { data: [row(0)], totalSize: 1 },
  { data: [row(1)], totalSize: 0 },
  { data: [], totalSize: 1 },
]) {
  test(`invalid response ${JSON.stringify(
    invalid
  )} cannot silently export partial data`, async () => {
    const f = fixture(() => invalid)
    await f.exportCases()
    assert.equal(f.exportError.value, true)
    assert.equal(f.downloads.length, 0)
    assert.equal(f.exportLoading.value, false)
    f.close()
  })
}
for (const failure of ['duplicate', 'count-change', 'empty-next', 'network-next']) {
  test(`${failure} on a later page prevents partial download`, async () => {
    const f = fixture((query) => {
      if (query.page === 1)
        return page(
          Array.from({ length: 1000 }, (_, i) => row(i + 1)),
          1001
        )
      if (failure === 'network-next') throw Error('Network')
      if (failure === 'count-change') return page([row(1001)], 1002)
      if (failure === 'empty-next') return page([], 1001)
      return page([row(1)], 1001)
    })
    await f.exportCases()
    assert.equal(f.exportError.value, true)
    assert.equal(f.downloads.length, 0)
    assert.equal(f.calls.length, 2)
    f.close()
  })
}
test('mapping preserves the twenty existing export columns and actual binding serializer fields', () => {
  const f = fixture()
  const [value] = f.mapping.caseExportRows(
    [
      row(1, {
        priority: 0,
        scenario_layer: 0,
        test_types: [0],
        scenario_tags: ['smoke'],
        project_product: { name: 'Product', project: { name: 'Project' } },
        module: { full_path: 'Parent/Child' },
        suite: { requirement_name: 'Requirement', iteration_ref: { name: 'Sprint' } },
        bindings: [
          { automation_type: 0, api_case: 77, ui_case: null, automation_case_id: 99 },
          { automation_type: 1, ui_case: 88, api_case: null },
        ],
        test_point: 'Point',
        test_data: 'Data',
        precondition: 'Before',
        remark: 'Note',
      }),
    ],
    f.enums
  )
  assert.equal(Object.keys(value).length, 20)
  assert.equal(value['API 用例 ID'], 77)
  assert.equal(value['UI 用例 ID'], 88)
  assert.equal(value.优先级, 'High')
  assert.equal(value.测试层级, 0)
  assert.equal(value['项目/产品'], 'Project/Product')
  assert.equal(value.模块, 'Parent/Child')
  assert.equal(value.所属Sprint, 'Sprint')
  assert.equal(value.备注, 'Note')
  assert.equal(value.前置条件, 'Before')
  f.close()
})
test('export mapping handles orphan suites, nullable fields and shared binding ID fallback', () => {
  const f = fixture()
  const [value] = f.mapping.caseExportRows(
    [row(1, { suite: null, bindings: [{ automation_type: 0, automation_case_id: 7 }] })],
    f.enums
  )
  assert.equal(value.需求名称, '')
  assert.equal(value.所属Sprint, '')
  assert.equal(value['API 用例 ID'], 7)
  assert.equal(value['UI 用例 ID'], '')
  assert.equal(value.优先级, '-')
  f.close()
})
test('invalid dynamic filter fails before HTTP and remains retryable', async () => {
  const f = fixture()
  f.state.query.title = ['unconverted-selection']
  await f.exportCases()
  assert.equal(f.calls.length, 0)
  assert.equal(f.exportError.value, true)
  f.state.query.title = 'valid'
  await f.exportCases()
  assert.equal(f.downloads.length, 1)
  f.close()
})
