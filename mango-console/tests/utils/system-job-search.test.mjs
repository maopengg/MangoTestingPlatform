import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { reactive, ref } from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

function loadModule(path, dependencies = {}) {
  const source = readFileSync(path, 'utf8')
  const exports = {}
  new Function('exports', 'require', ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText)(exports, key => dependencies[key])
  return exports
}

const searchUtils = loadModule('src/utils/search-condition.ts')
const cleaning = loadModule('src/utils/datacleaning.ts')
const fireConfig = loadModule('src/views/system/fire-record/config.ts', {
  vue: { reactive, ref }, '@/hooks/table': { useTable: () => ({}), useTableColumn: value => value },
  '@/utils/search-condition': searchUtils,
})
function createConditions() {
  return loadModule('src/views/timing/system-jobs/config.ts', {
    vue: { reactive }, '@/utils/search-condition': searchUtils,
    '@/views/system/fire-record/config': fireConfig,
  }).conditionItems
}

test('system jobs exposes text filters and multi-select trigger/status filters', () => {
  const items = createConditions()
  assert.deepEqual(items.map(item => item.key), ['key', 'name', 'description', 'cron', 'source_type', 'latest_status', 'latest_error_message'])
  for (const item of items.filter(item => item.type === 'select')) {
    assert.equal(item.multiple, true)
    assert.equal(item.searchOperator, 'in')
    assert.deepEqual(item.value, [])
  }
  assert.ok(items.find(item => item.key === 'latest_status').optionItems.some(item => item.value === 'untriggered'))
})

test('system jobs search compiles with global search and reset actions', () => {
  const filename = 'src/views/timing/system-jobs/index.vue'
  const source = readFileSync(filename, 'utf8')
  const { descriptor, errors } = parse(source, { filename })
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'system-job-search' })
  const template = compileTemplate({ source: descriptor.template.content, filename,
    id: 'system-job-search', compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, [])
  assert.match(source, /@search="onSearch" @reset-search="onResetSearch"/)
  assert.match(source, /pagination.page = 1/)
  assert.match(source, /version !== requestVersion/)
  assert.match(source, /if \(!params\[key\]\) delete params\[key\]/)
  assert.match(source, /:multiple="item.multiple"/)
  assert.match(source, /:max-tag-count="1"/)
})

test('search resets pagination, trims conditions, ignores stale responses and resets all fields', async () => {
  const source = readFileSync('src/views/timing/system-jobs/index.vue', 'utf8')
  const { descriptor } = parse(source)
  const items = createConditions()
  const table = { dataList: [], tableLoading: ref(false), handleSuccess(res) {
    this.dataList.splice(0, this.dataList.length, ...res.data)
  } }
  const pagination = { page: 3, pageSize: 20, total: 0, setTotalSize(total) { this.total = total } }
  const requests = []
  const dependencies = {
    vue: { reactive, defineComponent: component => component, onMounted: () => {} },
    '@/hooks/table': { useTable: () => table, useRowKey: key => key,
      useTableColumn: columns => columns, usePagination: () => pagination },
    '@/api/system/tasks': { getSystemTaskSystemJobs(params) {
      return new Promise((resolve, reject) => requests.push({ params, resolve, reject }))
    } },
    '@arco-design/web-vue': {},
    '@/utils/datacleaning': cleaning,
    './config': { conditionItems: items },
  }
  const exports = {}
  new Function('exports', 'require', ts.transpileModule(descriptor.script.content, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText)(exports, key => dependencies[key])
  const page = exports.default.setup()
  items[1].value = ' 清理 '
  const first = page.onSearch()
  assert.equal(pagination.page, 1)
  assert.deepEqual(requests[0].params, { name: '清理', page: 1, pageSize: 20 })
  items[0].value = 'clean_sql'
  items.find(item => item.key === 'source_type').value = [2, 4]
  items.find(item => item.key === 'latest_status').value = [0, 4, 'untriggered']
  const second = page.onSearch()
  assert.equal(requests[1].params.source_type__in, '2,4')
  assert.equal(requests[1].params.latest_status__in, '0,4,untriggered')
  requests[0].resolve({ data: [{ key: 'stale' }], totalSize: 1 })
  await first
  assert.deepEqual(table.dataList, [])
  assert.equal(table.tableLoading.value, true)
  requests[1].resolve({ data: [{ key: 'clean_sql' }], totalSize: 1 })
  await second
  assert.equal(table.dataList[0].key, 'clean_sql')
  assert.equal(table.tableLoading.value, false)
  pagination.page = 4
  const reset = page.onResetSearch()
  assert.ok(items.every(item => item.multiple ? Array.isArray(item.value) && item.value.length === 0 : item.value === ''))
  assert.deepEqual(requests[2].params, { page: 1, pageSize: 20 })
  requests[2].reject(new Error('example request failure'))
  await reset
  assert.deepEqual(table.dataList, [])
  assert.equal(pagination.total, 0)
  assert.equal(table.tableLoading.value, false)
})
