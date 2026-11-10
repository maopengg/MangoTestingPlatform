import { loadFeedbackModule } from '../../../../helpers/load-feedback-modules.mjs'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import vm from 'node:vm'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { computed, nextTick, reactive, ref, watch } from 'vue'

const filename = new URL('../../../../../src/views/timing/tasks/case/index.vue', import.meta.url)
const source = fs.readFileSync(filename, 'utf8')
const { descriptor } = parse(source, { filename: filename.pathname })
function actual(file, dependencies = {}) {
  const exports = {}, source = ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  new Function('exports', 'require', source)(exports, name => { if (name in dependencies) return dependencies[name]; { if (['@/utils/load-error', '@/utils/api-response'].includes(name)) return loadFeedbackModule(name); throw Error('Unexpected dependency ' + name) } })
  return exports
}
const records = actual(new URL('../../../../../src/views/timing/tasks/case/case-records.ts', import.meta.url), {
  '@/utils/business-format': actual(new URL('../../../../../src/utils/business-format.ts', import.meta.url)),
})
const script = ts.createSourceFile(
  filename.pathname,
  descriptor.scriptSetup.content,
  ts.ScriptTarget.Latest,
  true,
  ts.ScriptKind.TS
)

const bindings = new Set([
  'isApiCaseType',
  'filteredCandidateCases',
  'pagedCandidateCases',
  'selectableCandidateCases',
  'candidateAllChecked',
  'candidateAllCheckedIndeterminate',
  'candidateRequestId',
  'boundCaseKeysRequestId',
])
const functions = new Set([
  'isCaseBound',
  'isCandidateSelectable',
  'toggleAllCandidateCases',
  'clearCandidateCases',
  'changeType',
  'onExecutionVersionFilterChange',
  'selectedFilterText',
  'loadCandidateCases',
  'loadBoundCaseKeys',
])
const filterStatements = script.statements.filter((statement) => {
  if (ts.isVariableStatement(statement)) {
    return statement.declarationList.declarations.some((declaration) =>
      bindings.has(declaration.name.getText(script))
    )
  }
  if (ts.isFunctionDeclaration(statement)) return functions.has(statement.name?.text)
  return (
    ts.isExpressionStatement(statement) &&
    ts.isCallExpression(statement.expression) &&
    statement.expression.expression.getText(script) === 'watch' &&
    statement.expression.arguments[0]?.getText(script).includes('filteredCandidateCases.value.length')
  )
})
const executable = ts.transpileModule(
  filterStatements.map((statement) => statement.getText(script)).join('\n') +
    `\nglobalThis.filter = { ${[...bindings, ...functions].join(', ')} };`,
  { compilerOptions: { target: ts.ScriptTarget.ES2020 } }
).outputText

function createFilter() {
  const candidateCases = ref([
    { key: 1, published_release_id: 101 },
    { key: 2, published_release_id: null },
    { key: 3, published_release_id: 103, publication_status: 'draft_changed' },
    { key: 4, published_release_id: null, publication_status: 'prepublished' },
    { key: 5, published_release_id: 105 },
  ])
  const addForm = reactive({
    type: 1, executionVersions: [], projectProduct: 10, module: 1239,
    caseName: '', levels: [], scenarioLayers: [], scenarioTypes: [], scenarioTags: [],
  })
  const addSelectionKeys = ref([])
  const candidatePagination = reactive({
    page: 1,
    pageSize: 2,
    total: 0,
    setTotalSize(total) { this.total = total },
  })
  const requests = []
  const candidateLoading = ref(false)
  const boundRequests = []
  const boundCaseKeysLoading = ref(false)
  const boundCaseKeySet = ref(new Set(['5']))
  const currentTaskId = ref(216)
  const context = vm.createContext({
    computed, watch,
    candidateCases, addForm, addSelectionKeys, candidatePagination,
    boundCaseKeysLoading,
    boundCaseKeySet,
    candidateLoading,
    candidateError: ref(''), boundCaseKeysError: ref(''), writeBusy: ref(false),
    available: () => true, captureContext: () => () => true,
    parseCandidateCases: records.parseCandidateCases, parseBoundCaseKeys: records.parseBoundCaseKeys,
    currentTaskId,
    currentProjectProductId: ref(10),
    getLeafValue: (value) => Array.isArray(value) ? value.at(-1) : value,
    getSystemTasksTypeCaseName: (...args) => new Promise((resolve, reject) => {
      requests.push({ args, resolve, reject })
    }),
    getSystemTasksRunCase: (args) => new Promise((resolve, reject) => {
      boundRequests.push({ args, resolve, reject })
    }),
    console,
  })
  vm.runInContext(executable, context)
  return {
    ...context.filter, candidateCases, addForm, addSelectionKeys, candidatePagination,
    candidateLoading, requests, boundRequests, boundCaseKeysLoading, boundCaseKeySet, currentTaskId,
  }
}

const ids = (items) => Array.from(items, (item) => item.key)

test('older bound-case responses cannot overwrite the latest case type', async () => {
  const filter = createFilter()
  filter.addForm.type = 0
  const older = filter.loadBoundCaseKeys()
  filter.addForm.type = 1
  const latest = filter.loadBoundCaseKeys()
  assert.deepEqual(JSON.parse(JSON.stringify(filter.boundRequests[1].args)), {
    task_id: 216, type: 1, case_ids_only: 1,
  })
  filter.boundRequests[1].resolve({ code: 200, data: [{ case_id: 1 }] })
  await latest
  filter.boundRequests[0].resolve({ code: 200, data: [{ case_id: 3 }] })
  await older
  assert.deepEqual(Array.from(filter.boundCaseKeySet.value), ['1'])
  assert.equal(filter.isCandidateSelectable({ key: 1, published_release_id: 101 }), false)
  assert.equal(filter.isCandidateSelectable({ key: 3, published_release_id: 103 }), true)
})

test('older bound requests do not end loading or enable selection while latest is pending', async () => {
  const filter = createFilter()
  const older = filter.loadBoundCaseKeys()
  const latest = filter.loadBoundCaseKeys()
  filter.boundRequests[0].resolve({ code: 200, data: [] })
  await older
  assert.equal(filter.boundCaseKeysLoading.value, true)
  assert.equal(filter.isCandidateSelectable({ key: 1, published_release_id: 101 }), false)
  filter.boundRequests[1].resolve({ code: 200, data: [] })
  await latest
  assert.equal(filter.boundCaseKeysLoading.value, false)
  assert.equal(filter.isCandidateSelectable({ key: 1, published_release_id: 101 }), true)
})

test('clearing the task invalidates in-flight bound requests and clears loading', async () => {
  const filter = createFilter()
  const older = filter.loadBoundCaseKeys()
  filter.currentTaskId.value = ''
  await filter.loadBoundCaseKeys()
  filter.boundRequests[0].resolve({ code: 200, data: [{ case_id: 1 }] })
  await older
  assert.deepEqual(Array.from(filter.boundCaseKeySet.value), [])
  assert.equal(filter.boundCaseKeysLoading.value, false)
})

test('candidate requests submit every selected filter, including zero and string scene values', async () => {
  const filter = createFilter()
  Object.assign(filter.addForm, {
    caseName: '筛选用例', levels: [0, 1], scenarioLayers: [0, 2],
    scenarioTypes: [0, 3], scenarioTags: ['temporary_validation', 'routine_regression'],
  })
  const pending = filter.loadCandidateCases()
  const request = filter.requests[0]
  assert.deepEqual(Array.from(request.args.slice(0, 4)), [1, 1239, 10, undefined])
  assert.equal(request.args[5], 216)
  assert.deepEqual(JSON.parse(JSON.stringify(request.args[4])), {
    case_name: '筛选用例', levels: '0,1', scenario_layers: '0,2',
    scenario_types: '0,3', scenario_tags: 'temporary_validation,routine_regression',
  })
  request.resolve({ code: 200, data: [] })
  await pending
  assert.equal(filter.candidateLoading.value, false)
})

test('older responses cannot override the latest filter result or end its loading state', async () => {
  const filter = createFilter()
  const older = filter.loadCandidateCases()
  filter.addForm.scenarioTags = ['temporary_validation']
  const latest = filter.loadCandidateCases()
  filter.requests[0].resolve({ code: 200, data: [{ key: 11, title: 'Example 11' }] })
  await older
  assert.deepEqual(ids(filter.candidateCases.value), [])
  assert.equal(filter.candidateLoading.value, true)
  filter.requests[1].resolve({ code: 200, data: [{ key: 12, title: 'Example 12' }] })
  await latest
  assert.deepEqual(ids(filter.candidateCases.value), [12])
  assert.equal(filter.candidateLoading.value, false)
})

test('an older request arriving after the latest result cannot overwrite it', async () => {
  const filter = createFilter()
  const older = filter.loadCandidateCases()
  const latest = filter.loadCandidateCases()
  filter.requests[1].resolve({ code: 200, data: [{ key: 12, title: 'Example 12' }] })
  await latest
  filter.requests[0].resolve({ code: 200, data: [{ key: 11, title: 'Example 11' }] })
  await older
  assert.deepEqual(ids(filter.candidateCases.value), [12])
})

test('hover text includes all selected labels for enums and execution versions', () => {
  const { selectedFilterText } = createFilter()
  assert.equal(selectedFilterText([1, 2, 3], [
    { key: 1, title: '正常场景' },
    { key: 2, title: '异常场景' },
    { key: 3, title: '边界场景' },
  ]), '正常场景、异常场景、边界场景')
  assert.equal(selectedFilterText(['unpublished'], [
    { value: 'unpublished', label: '暂无已发布版本' },
  ]), '暂无已发布版本')
  assert.equal(selectedFilterText([], []), '')
  assert.equal(selectedFilterText(['unknown'], []), 'unknown')
})

test('all candidate multi-selects fold tags and expose full hover text without wrapping', () => {
  const template = descriptor.template.content
  for (const field of ['levels', 'scenarioLayers', 'scenarioTypes', 'scenarioTags', 'executionVersions']) {
    const select = template.match(new RegExp(`<a-select\\s+v-model="addForm\\.${field}"[\\s\\S]*?/>`))?.[0]
    assert.ok(select, field)
    assert.match(select, /tag-nowrap/)
    assert.match(select, /:max-tag-count="1"/)
    assert.match(select, /:trigger-props="candidateFilterTriggerProps"/)
    assert.ok(template.includes(`selectedFilterText(addForm.${field},`))
  }
  assert.match(descriptor.styles[0].content, /arco-select-view-nowrap\)\s*\{[^}]*flex-wrap: nowrap/)
  assert.match(descriptor.styles[0].content, /arco-tag-text\)\s*\{[^}]*text-overflow: ellipsis/)
})

test('default includes all candidates and only published, unbound cases are selectable', () => {
  const filter = createFilter()
  assert.deepEqual(ids(filter.filteredCandidateCases.value), [1, 2, 3, 4, 5])
  assert.deepEqual(ids(filter.selectableCandidateCases.value), [1, 3])
  assert.equal(filter.candidatePagination.total, 5)
})

test('published filter uses the executable release, including cases with newer drafts', async () => {
  const filter = createFilter()
  filter.addForm.executionVersions = ['published']
  await nextTick()
  assert.deepEqual(ids(filter.filteredCandidateCases.value), [1, 3, 5])
  assert.equal(filter.candidatePagination.total, 3)
  assert.deepEqual(ids(filter.pagedCandidateCases.value), [1, 3])
  filter.candidatePagination.page = 2
  assert.deepEqual(ids(filter.pagedCandidateCases.value), [5])
})

test('unpublished filter includes prepublication but never enables adding those cases', async () => {
  const filter = createFilter()
  filter.addForm.executionVersions = ['unpublished']
  await nextTick()
  assert.deepEqual(ids(filter.filteredCandidateCases.value), [2, 4])
  assert.equal(filter.candidatePagination.total, 2)
  assert.equal(filter.selectableCandidateCases.value.length, 0)
  filter.toggleAllCandidateCases(true)
  assert.equal(filter.addSelectionKeys.value.length, 0)
  assert.equal(filter.candidateAllChecked.value, false)
})

test('501 candidates split into 494 published and 7 without a published version', async () => {
  const filter = createFilter()
  filter.candidateCases.value = Array.from({ length: 501 }, (_, index) => ({
    key: index + 1,
    published_release_id: index < 494 ? index + 1000 : null,
  }))
  filter.addForm.executionVersions = ['published']
  await nextTick()
  assert.equal(filter.filteredCandidateCases.value.length, 494)
  assert.equal(filter.candidatePagination.total, 494)
  filter.addForm.executionVersions = ['unpublished']
  filter.onExecutionVersionFilterChange()
  await nextTick()
  assert.equal(filter.filteredCandidateCases.value.length, 7)
  assert.equal(filter.candidatePagination.total, 7)
  assert.equal(filter.selectableCandidateCases.value.length, 0)
})

test('multi-select and clearing return all candidates and reset pagination and selection', async () => {
  const filter = createFilter()
  filter.addForm.executionVersions = ['published', 'unpublished']
  await nextTick()
  assert.equal(filter.filteredCandidateCases.value.length, 5)
  filter.addForm.executionVersions = ['published']
  filter.candidatePagination.page = 2
  filter.toggleAllCandidateCases(true)
  assert.deepEqual(Array.from(filter.addSelectionKeys.value), [1, 3])
  filter.addForm.executionVersions = []
  filter.onExecutionVersionFilterChange()
  await nextTick()
  assert.equal(filter.candidatePagination.page, 1)
  assert.equal(filter.candidatePagination.total, 5)
  assert.equal(filter.addSelectionKeys.value.length, 0)
})

test('select all only selects eligible filtered cases and maintains checkbox states', () => {
  const filter = createFilter()
  filter.addForm.executionVersions = ['published']
  filter.addSelectionKeys.value = [1]
  assert.equal(filter.candidateAllCheckedIndeterminate.value, true)
  filter.toggleAllCandidateCases(true)
  assert.equal(filter.candidateAllChecked.value, true)
  assert.equal(filter.candidateAllCheckedIndeterminate.value, false)
  assert.deepEqual(Array.from(filter.addSelectionKeys.value), [1, 3])
  filter.toggleAllCandidateCases(false)
  assert.equal(filter.addSelectionKeys.value.length, 0)
})

test('UI and Pytest candidates are not filtered by API execution versions', () => {
  const filter = createFilter()
  filter.addForm.executionVersions = ['unpublished']
  filter.addForm.type = 0
  assert.equal(filter.filteredCandidateCases.value.length, 5)
  filter.changeType(2)
  assert.equal(filter.addForm.executionVersions.length, 0)
  assert.equal(filter.candidateCases.value.length, 0)
  assert.equal(filter.candidatePagination.page, 1)
})

test('Vue script and template compile with the execution version filter', () => {
  const compiled = compileScript(descriptor, { id: 'timing-case-filter-test' })
  const template = compileTemplate({
    source: descriptor.template.content,
    filename: filename.pathname,
    id: 'timing-case-filter-test',
    compilerOptions: { bindingMetadata: compiled.bindings },
  })
  assert.deepEqual(template.errors, [])
  assert.ok(compiled.bindings.candidateExecutionVersionOptions)
  assert.match(descriptor.template.content, /已加载 \{\{ filteredCandidateCases.length \}\}/)
})
