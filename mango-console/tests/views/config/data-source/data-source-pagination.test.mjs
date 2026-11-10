import { setupSource } from '../../../helpers/source-harness.mjs'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { computed, effectScope, nextTick, ref, watch } from 'vue'

const source = fs.readFileSync(
  new URL(
    '../../../../src/views/config/data-source/components/DataSourceWorkbench.vue',
    import.meta.url
  ),
  'utf8'
)
const hook = fs.readFileSync(new URL('../../../../src/hooks/table.ts', import.meta.url), 'utf8')
const paginationCode = hook.slice(hook.indexOf('export const usePagination ='))
const hookJs = ts.transpileModule(paginationCode, {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText
const exports = {}
const { reactive } = await import('vue')
new Function('exports', 'reactive', hookJs)(exports, reactive)

test('client pagination counts filtered rows, slices pages, and resets after searching', async () => {
  const state = setupSource(
    'DataSourceWorkbench',
    'bindings,databases,databaseKeyword,bindingPagination,databasePagination,pagedBindings,pagedDatabases',
    {},
    { sources: [], loading: false, testingIds: [] }
  )
  const { bindings, databases, databaseKeyword } = state
  try {
    bindings.value = Array.from({ length: 45 }, (_, id) => ({ id }))
    databases.value = Array.from({ length: 65 }, (_, id) => ({ name: `database-${id}` }))
    await nextTick()
    assert.equal(state.bindingPagination.pageCount, 45)
    assert.equal(state.databasePagination.pageCount, 65)
    state.bindingPagination.page = 2
    assert.deepEqual(
      state.pagedBindings.value.map((row) => row.id),
      Array.from({ length: 20 }, (_, i) => i + 20)
    )
    state.databasePagination.page = 4
    assert.equal(state.pagedDatabases.value.length, 5)
    databaseKeyword.value = 'database-6'
    await nextTick()
    assert.equal(state.databasePagination.page, 1)
    assert.equal(state.databasePagination.pageCount, 6)
    databaseKeyword.value = 'missing'
    await nextTick()
    assert.equal(state.databasePagination.pageCount, 0)
    assert.deepEqual(state.pagedDatabases.value, [])
    state.bindingPagination.pageSize = 10
    assert.equal(state.pagedBindings.value.length, 10)
    bindings.value = []
    await nextTick()
    assert.equal(state.bindingPagination.page, 1)
    assert.equal(state.bindingPagination.pageCount, 0)
  } finally {
    state.dispose()
  }
})

test('product table pagination resets filters and clamps pages when data shrinks', async () => {
  const product = fs.readFileSync(
    new URL(
      '../../../../src/views/config/product/datasource/components/ProductDataSourceTables.vue',
      import.meta.url
    ),
    'utf8'
  )
  const start = product.indexOf('  const pagination =')
  const end = product.indexOf('  const rowSelection =', start)
  assert.ok(start > 0 && end > start)
  const js = ts.transpileModule(product.slice(start, end), {}).outputText
  const rows = ref(Array.from({ length: 45 }, (_, id) => ({ name: `table-${id}` })))
  const keyword = ref('')
  const filteredTables = computed(() =>
    rows.value.filter((row) => row.name.includes(keyword.value))
  )
  const scope = effectScope()
  const state = scope.run(() =>
    new Function(
      'usePagination',
      'ref',
      'computed',
      'watch',
      'filteredTables',
      'keyword',
      `${js}; return { pagination, pagedTables };`
    )(exports.usePagination, ref, computed, watch, filteredTables, keyword)
  )
  try {
    assert.equal(state.pagination.pageCount, 45)
    state.pagination.page = 3
    assert.equal(state.pagedTables.value.length, 5)
    keyword.value = 'table-4'
    await nextTick()
    assert.equal(state.pagination.page, 1)
    assert.equal(state.pagination.pageCount, 6)
    state.pagination.pageSize = 10
    keyword.value = ''
    await nextTick()
    state.pagination.page = 4
    rows.value = rows.value.slice(0, 12)
    await nextTick()
    assert.equal(state.pagination.page, 2)
    assert.equal(state.pagedTables.value.length, 2)
    rows.value = []
    await nextTick()
    assert.equal(state.pagination.page, 1)
    assert.equal(state.pagination.pageCount, 0)
  } finally {
    scope.stop()
  }
})
