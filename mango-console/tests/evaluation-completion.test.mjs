import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import test from 'node:test'
import { setImmediate as immediate } from 'node:timers/promises'

const require = createRequire(import.meta.url)
const Vue = require('vue'), ts = require('typescript')
const { parse, compileScript } = require('@vue/compiler-sfc')
const base = new URL('../src/views/evaluation/', import.meta.url)
const flush = async () => { await Vue.nextTick(); await immediate(); await Vue.nextTick() }
const renderer = Vue.createRenderer({
  createElement: type => ({ type, children: [] }), createText: text => ({ text }), createComment: text => ({ text }),
  insert(node, parent) { parent.children.push(node); node.parent = parent },
  remove(node) { if (node.parent) node.parent.children = node.parent.children.filter(item => item !== node) },
  parentNode: node => node.parent, nextSibling: () => null, setText(node, text) { node.text = text },
  setElementText(node, text) { node.text = text }, patchProp(node, key, _old, value) { node[key] = value },
})
function scriptModule(file, resolve) {
  const text = readFileSync(new URL(file, base), 'utf8')
  const source = file.endsWith('.vue') ? compileScript(parse(text, { filename: file }).descriptor, { id: file }).content : text
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true } }).outputText
  const module = { exports: {} }
  new Function('require', 'module', 'exports', code)(resolve, module, module.exports)
  return module.exports
}
async function mount(file, { api = {}, permissions = { hasPermission: () => true }, user = Vue.reactive({ selected_environment: 1 }), router, route = { query: {} }, props = {}, guards = [], modal = { warning() {} } } = {}) {
  const resolve = name => {
    if (name === 'vue') return Vue
    if (name === '@arco-design/web-vue') return { Message: { success() {}, warning() {}, error() {} }, Modal: modal }
    if (name === 'vue-router') return { useRoute: () => route, useRouter: () => router || { push() {}, replace() {} }, onBeforeRouteLeave: guard => guards.push(guard), onBeforeRouteUpdate() {} }
    if (name === '@/api/evaluation' || name === '@/api/data-factory') return new Proxy(api, { get: (object, key) => object[key] || (async () => ({ data: [], totalSize: 0 })) })
    if (name === '@/store/modules/permission') return { default: () => permissions, __esModule: true }
    if (name === '@/store/modules/user') return { default: () => user, __esModule: true }
    if (name === '@/store/modules/get-enum') return { useEnum: () => ({ evaluation_verdict: [{ key: 'passed', title: '通过' }, { key: 'failed', title: '不通过' }], evaluation_execution_status: [], evaluation_item_execution_status: [], evaluation_grade_status: [] }) }
    if (name.endsWith('/useEvaluationEnums')) return scriptModule('components/useEvaluationEnums.ts', resolve)
    if (name.includes('details/config')) return scriptModule('case/details/config.ts', resolve)
    if (name.endsWith('/presentation') || name === './presentation') return scriptModule('components/presentation.ts', resolve)
    if (name === './guide') return scriptModule('grader/guide.ts', resolve)
    if (name === '../dataset/workflow') return scriptModule('dataset/workflow.ts', resolve)
    if (name === '../workflow' && file.startsWith('dataset/')) return scriptModule('dataset/workflow.ts', resolve)
    if (name === '../config' && file.startsWith('case/details/')) return scriptModule('case/config.ts', resolve)
    if (name.endsWith('/case/config') || name === './config' && file.startsWith('case/') || name === '../case/config') return scriptModule('case/config.ts', resolve)
    if (name === './config' && file.startsWith('dataset/')) return scriptModule('dataset/config.ts', resolve)
    if (name === '../config' && file.startsWith('dataset/details/')) return scriptModule('dataset/config.ts', resolve)
    if (name === '@/utils/business-format') {
      const source = readFileSync(new URL('../src/utils/business-format.ts', import.meta.url), 'utf8')
      const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
      const module = { exports: {} }
      new Function('module', 'exports', code)(module, module.exports)
      return module.exports
    }
    if (name.endsWith('.vue')) return {}
    throw new Error(`Unexpected unit dependency: ${name}`)
  }
  const component = scriptModule(file, resolve).default
  component.render = () => null
  const app = renderer.createApp(component, props)
  app.mount({ children: [] })
  await flush()
  return { state: app._instance.setupState, user, unmount: () => app.unmount() }
}

test('QA result evidence comes from source materials without duplicate expected fields', async () => {
  const view = await mount('components/ItemResultContent.vue', { props: { item: {
    resolved_expected_output: { answer: '北京' }, actual_output: { answer: '北京' },
    item_snapshot: { context: { source_evidence: [null, { excerpt: '已搬到北京', occurred_at: '2025-02-01' }, '之前住上海', { excerpt: '已搬到北京' }] } },
  } } })
  try {
    assert.deepEqual(view.state.expectedSources, [
      { text: '已搬到北京', time: '2025-02-01', ranks: [] },
      { text: '之前住上海', time: undefined, ranks: [] },
    ])
  } finally { view.unmount() }
})

test('QA result shows the resolved grading materials instead of the source template', async () => {
  const view = await mount('components/ItemResultContent.vue', { props: { item: {
    resolved_expected_output: { answer: '张三' }, actual_output: { answer: '张三' },
    item_snapshot: { context: { source_evidence: [{ excerpt: '${{contract_owner}}' }] } },
    details: { turns: [
      { scored: true, context: { source_evidence: [{ excerpt: '负责人是张三' }] } },
      { scored: false, context: { source_evidence: [{ excerpt: '无需评分' }] } },
    ] },
  } } })
  try { assert.deepEqual(view.state.expectedSources, [{ text: '负责人是张三', time: undefined, ranks: [] }]) } finally { view.unmount() }
})

test('retrieval result keeps explicitly configured target sources and matches their ranks', async () => {
  const view = await mount('components/ItemResultContent.vue', { props: { item: {
    resolved_expected_output: { source_excerpt: '目标原文', source_excerpts: ['目标原文'] },
    actual_output: { top_items: [{ evidence: [{ excerpt: '其他原文' }] }, { evidence: [{ excerpt: '目标原文' }] }] },
    item_snapshot: { context: { source_evidence: [{ excerpt: '目标原文', occurred_at: '2025-01-01' }, { excerpt: '其他原文' }] } },
  } } })
  try {
    assert.deepEqual(view.state.expectedSources, [{ text: '目标原文', time: '2025-01-01', ranks: [2] }])
  } finally { view.unmount() }
})

test('results without source materials do not invent evidence', async () => {
  const view = await mount('components/ItemResultContent.vue', { props: { item: { resolved_expected_output: { answer: '北京' }, actual_output: '北京' } } })
  try { assert.deepEqual(view.state.expectedSources, []) } finally { view.unmount() }
})

test('dataset workflow saves variables on the version and published versions remain read only', async () => {
  const writes = []
  const view = await mount('components/DatasetConfigDrawer.vue', { api: { updateDatasetVersion: async (id, data) => { writes.push({ id, data }); return { data } } } })
  try {
    view.state.open({ id: 8, status: 'draft', schema_snapshot: {} }, { query: '北京' })
    view.state.config.input_variables = [{ name: 'question', path: '$.query' }, { name: 'complete', path: '$' }]
    await view.state.save()
    assert.equal(writes.length, 1)
    assert.equal(writes[0].id, 8)
    assert.equal('version_label' in writes[0].data, false)
    assert.equal(writes[0].data.schema_snapshot.input_variables.length, 2)
    assert.equal(view.state.visible, false)
    view.state.open({ id: 9, status: 'published', schema_snapshot: {} })
    assert.equal(view.state.readonly, true)
    await view.state.save()
    assert.equal(writes.length, 1)
  } finally { view.unmount() }
})

test('dataset inputs hide whole-input selection and offer named fields for multiple variables', async () => {
  const view = await mount('components/DatasetConfigDrawer.vue')
  try {
    view.state.open({ id: 8, status: 'draft', schema_snapshot: { input_schema: { properties: { query: { title: '问题' } } } } }, { query: '哪里', attachments: ['example.txt'] })
    assert.equal(view.state.variableColumns.some(column => column.slotName === 'path'), false)
    assert.deepEqual(view.state.inputFieldOptions.find(option => option.value === '$.query'), { value: '$.query', label: '问题' })
    assert.ok(view.state.inputFieldOptions.some(option => option.value === '$.attachments'))
    view.state.config.input_variables.push({ name: 'question', path: '$.query' })
    assert.equal(view.state.variableColumns.find(column => column.slotName === 'path').title, '输入字段')
    view.state.open({ id: 9, status: 'published', schema_snapshot: { input_variables: [{ name: 'question', path: '$.query' }] } })
    assert.ok(view.state.variableColumns.some(column => column.slotName === 'path'))
    assert.equal(view.state.variableColumns.some(column => column.slotName === 'actions'), false)
    assert.equal(view.state.config.input_variables[0].path, '$.query')
  } finally { view.unmount() }
})

test('item data-source settings are local and source-type changes clear old SQL resources', async () => {
  const source = Vue.reactive({ kind: 'sql', query: 'SELECT id FROM contracts', parameters: { id: 1 }, binding: { project_product_id: 1, ref_id: 10, name: '订单库' } })
  const values = []
  const view = await mount('components/ItemDataSourceEditor.vue', { props: { modelValue: source, versionId: 1, 'onUpdate:modelValue': value => values.push(value) } })
  try {
    view.state.update({ query: 'SELECT name FROM contracts' })
    assert.equal(values[0].query, 'SELECT name FROM contracts')
    assert.equal(source.query, 'SELECT id FROM contracts')
    view.state.changeKind('manual')
    assert.deepEqual(values[1], { kind: 'manual', query: '', binding: null })
    assert.equal(source.binding.ref_id, 10)
  } finally { view.unmount() }
})

test('reference API selection filters by product and module and disables unpublished interfaces', async () => {
  const calls = [], changes = []
  const source = Vue.reactive({ kind: 'api_info', module_id: 5, binding: { project_product_id: 1, ref_id: 10, revision_id: 7, content_hash: 'old' }, variables: [] })
  const view = await mount('components/ItemDataSourceEditor.vue', { props: { modelValue: source, versionId: 1, 'onUpdate:modelValue': value => changes.push(value) }, api: {
    getDatasetWorkflowResources: async (_id, values) => { calls.push(values); return { data: { items: [{ id: 11, name: '参考订单查询', available: true }, { id: 12, name: '草稿接口', available: false }], count: 2 } } },
  } })
  try {
    await view.state.loadResources()
    assert.deepEqual(calls[0], { action: 'api_info', project_product_id: 1, module_id: 5, search: '', page: 1 })
    assert.equal(view.state.resources[1].disabled, true)
    assert.equal(view.state.resources[1].label, '草稿接口（未发布）')
    view.state.setApi(11)
    assert.deepEqual(changes[0].binding, { resource: 'item_source', project_product_id: 1, ref_id: 11, name: '参考订单查询' })
    view.state.setModule(6)
    assert.equal(changes[1].module_id, 6)
    assert.equal(changes[1].binding.ref_id, undefined)
    assert.equal(source.binding.ref_id, 10)
    source.module_id = null
    await flush(); await view.state.loadResources()
    assert.equal(calls.length, 1)
  } finally { view.unmount() }
})

test('reference response variables are edited locally and source changes clear API-only settings', async () => {
  const changes = [], source = { kind: 'api_info', module_id: 5, binding: { project_product_id: 1, ref_id: 10 }, parameters: { id: 101 }, variables: [{ name: 'contract_id', path: '$.json.data.id' }] }
  const view = await mount('components/ItemDataSourceEditor.vue', { props: { modelValue: source, versionId: 1, 'onUpdate:modelValue': value => changes.push(value) } })
  try {
    view.state.setVariable(0, { name: 'expected_owner', path: '$.json.data.owner' })
    assert.deepEqual(changes[0].variables, [{ name: 'expected_owner', path: '$.json.data.owner' }])
    assert.equal(source.variables[0].name, 'contract_id')
    view.state.changeKind('sql')
    assert.deepEqual(changes[1], { kind: 'sql', query: '', binding: null })
  } finally { view.unmount() }
})

test('clearing a SQL draft reaches the item editor and retains the selected product', async () => {
  const values = [], source = { kind: 'sql', query: 'SELECT id FROM contracts', binding: { resource: 'item_source', project_product_id: 1, ref_id: 10 } }
  const view = await mount('components/ItemDataSourceEditor.vue', { props: { modelValue: source, versionId: 1, 'onUpdate:modelValue': value => values.push(value) } })
  try {
    view.state.sqlRows[0].value = ''
    view.state.saveSql()
    assert.equal(values[0].query, '')
    view.state.sqlRows[0].datasource_alias = null
    view.state.saveSql()
    assert.deepEqual(values[1].binding, { resource: 'item_source', project_product_id: 1 })
  } finally { view.unmount() }
})

test('SQL variable keys are loaded, saved and cleared with the item source', async () => {
  const values = [], source = { kind: 'sql', query: 'SELECT id,name FROM contracts', key: 'contract_id,contract_name', binding: { resource: 'item_source', project_product_id: 1, ref_id: 10 } }
  const view = await mount('components/ItemDataSourceEditor.vue', { props: { modelValue: source, versionId: 1, 'onUpdate:modelValue': value => values.push(value) } })
  try {
    assert.equal(view.state.sqlRows[0].key, source.key)
    view.state.sqlRows[0].key = 'contract_id'
    view.state.saveSql()
    assert.equal(values[0].key, 'contract_id')
    view.state.sqlRows[0].key = ''
    view.state.saveSql()
    assert.equal(values[1].key, '')
    view.state.changeKind('manual')
    assert.equal(values[2].key, undefined)
  } finally { view.unmount() }
})

test('shared factory panel saves local selections without writing API case bindings', async () => {
  const writes = [], selected = []
  const template = { id: 7, name: '订单模板', project_product: { id: 1 } }
  const view = await mount('../../components/DataFactory/CaseConfigPanel.vue', { props: { local: true, localPermission: 'evaluation.dataset:change', projectProductId: 1, configs: [], 'onUpdate:configs': value => selected.push(value) }, api: {
    getDataFactoryCaseConfig: async () => { writes.push('read-api-binding'); return { data: [] } },
    postDataFactoryCaseConfig: async () => { writes.push('create-api-binding'); return { data: {} } },
    putDataFactoryCaseConfig: async () => { writes.push('update-api-binding'); return { data: {} } },
  } })
  try {
    await view.state.open(); await flush()
    view.state.templateList = [template]
    view.state.form.template = 7
    assert.equal(await view.state.save(), true)
    assert.equal(selected[0][0].template.id, 7)
    assert.deepEqual(writes, [])
  } finally { view.unmount() }
})

test('item source ignores resources loaded for a previously selected product', async () => {
  let finish
  const source = Vue.reactive({ kind: 'sql', binding: { project_product_id: 1 } })
  const view = await mount('components/ItemDataSourceEditor.vue', { props: { modelValue: source, versionId: 1 }, api: { getDatasetWorkflowResources: () => new Promise(resolve => { finish = resolve }) } })
  try {
    const pending = view.state.loadResources()
    source.binding = { project_product_id: 2 }
    await flush()
    finish({ data: { items: [{ id: 10, name: '旧库', available: true }], count: 1 } })
    await pending
    assert.deepEqual(view.state.resources, [])
    assert.equal(view.state.loading, false)
  } finally { view.unmount() }
})

test('dataset workflow ignores preview responses after switching versions and resets loading', async () => {
  let resolvePreview
  const view = await mount('components/DatasetConfigDrawer.vue', { api: { previewDatasetInputs: () => new Promise(resolve => { resolvePreview = resolve }) } })
  try {
    view.state.open({ id: 8, status: 'draft', schema_snapshot: {} }, 'old input')
    const pending = view.state.preview()
    assert.equal(view.state.previewing, true)
    view.state.open({ id: 9, status: 'draft', schema_snapshot: {} }, 'new input')
    assert.equal(view.state.previewing, false)
    resolvePreview({ data: { case_input: 'old input' } })
    await pending
    assert.equal(view.state.previewResult, undefined)
    assert.equal(view.state.version.id, 9)
  } finally { view.unmount() }
})

test('case information inspector formats existing metadata and reacts to record changes without requests', async () => {
  const record = Vue.reactive({ id: 1, name: '评测用例', project_product_data: { name: '产品' }, module_data: { full_path: '一级 / 二级', name: '二级' }, owner_name: '负责人', dataset_name: '数据集', dataset_version_no: 2, create_time: '2026-10-22T10:20:30.123456', update_time: null })
  const view = await mount('components/CaseInfoPanel.vue', { props: { record } })
  try {
    const field = label => view.state.fields.find(item => item.label === label).value
    assert.equal(field('用例 ID'), 1)
    assert.equal(field('所属模块'), '一级 / 二级')
    assert.equal(field('项目/产品'), '产品')
    assert.equal(field('发布版本'), 'V2')
    assert.equal(field('创建时间'), '2026-10-22 10:20:30')
    assert.equal(field('更新时间'), '—')
    record.name = '更新后的名称'
    record.module_data = null
    record.dataset_version_no = null
    await flush()
    assert.equal(field('用例名称'), '更新后的名称')
    assert.equal(field('所属模块'), '-')
    assert.equal(field('发布版本'), '—')
  } finally { view.unmount() }
})

test('grader guide switches frontend examples and resets the example when the grader changes', async () => {
  const detail = Vue.reactive({ grader_key: 'memory_qa', grader_version: 2, category: 'model', parameters_schema: {} })
  const view = await mount('grader/GraderDetail.vue', { props: { detail } })
  try {
    assert.equal(view.state.activeTab, 'configuration')
    assert.equal(view.state.example.score, 100)
    view.state.exampleIndex = 1
    await flush()
    assert.equal(view.state.example.outcome, '幻觉')
    view.state.exampleIndex = 3
    await flush()
    assert.equal(view.state.example.score, null)
    assert.match(view.state.fields.find(field => field.label === '原文证据').value, /广州/)
    assert.doesNotMatch(view.state.guide.fields.find(field => field.label === '原文证据').value, /广州/)
    view.state.activeTab = 'example'
    Object.assign(detail, { grader_key: 'memory_extraction', grader_version: 1 })
    await flush()
    assert.equal(view.state.activeTab, 'configuration')
    assert.equal(view.state.exampleIndex, 0)
    view.state.exampleIndex = 1
    await flush()
    assert.equal(view.state.example.score, 66.67)
    assert.match(view.state.example.reason, /准确率 100%/)
  } finally { view.unmount() }
})

test('grader guide does not present current examples as explanations for an unsupported version', async () => {
  const view = await mount('grader/GraderDetail.vue', { props: { detail: { grader_key: 'memory_qa', grader_version: 1, category: 'model' } } })
  try { assert.equal(view.state.guide, undefined); assert.equal(view.state.example, undefined) }
  finally { view.unmount() }
})

test('memory graders use model restrictions and label obsolete bindings without exposing internal codes', async () => {
  const updates = []
  const view = await mount('components/GraderEditor.vue', { props: {
    modelValue: [{ grader_key: 'memory_qa', grader_version: 1, metric_key: 'qa', parameters: {}, hard_gate: true }],
    catalog: [{ grader_key: 'memory_qa', grader_version: 2, name: '记忆问答正确性', category: 'model' },
      { grader_key: 'memory_extraction', grader_version: 1, name: '记忆提取', category: 'model' },
      { grader_key: 'memory_update', grader_version: 1, name: '记忆更新', category: 'model' }],
    'onUpdate:modelValue': value => updates.push(value),
  } })
  try {
    assert.equal(view.state.options.find(item => item.value === 'memory_qa@1').disabled, true)
    assert.match(view.state.options.find(item => item.value === 'memory_qa@1').label, /旧口径/)
    assert.doesNotMatch(view.state.options.find(item => item.value === 'memory_qa@1').label, /memory_qa/)
    for (const key of ['memory_qa@2', 'memory_extraction@1', 'memory_update@1']) {
      view.state.choose(0, key)
      assert.equal(updates.at(-1)[0].hard_gate, false)
    }
  } finally { view.unmount() }
})

test('published item details retain full context and grading without editing the source', async () => {
  const view = await mount('dataset/details/index.vue')
  try {
    view.state.activeVersion = { id: 2, version_no: 3, status: 'published' }
    const item = { item_id: 101, context: { nested: { evidence: 'source' } }, metadata: { split: 'test' }, grading_config: { mode: 'replace', graders: [{ grader_key: 'contains' }] } }
    view.state.viewItem(item)
    item.context.nested.evidence = 'changed'
    assert.equal(view.state.documentVisible, true)
    assert.equal(view.state.documentData.context.nested.evidence, 'source')
    assert.equal(view.state.documentData.grading_config.mode, 'replace')
    assert.equal(view.state.documentData.version, 3)
  } finally { view.unmount() }
})

test('structured field display uses configured labels and preserves false, zero and empty values', async () => {
  for (const [data, text] of [[false, '否'], [0, '0'], [null, '空值'], ['', '空文本'], [[], '无'], [{}, '无']]) {
    const view = await mount('components/DataFieldsView.vue', { props: { data } })
    try { assert.equal(view.state.text, text) } finally { view.unmount() }
  }
  const view = await mount('components/DataFieldsView.vue', { props: { data: { query: '完整输入', answer_terms: ['北京'] }, schema: { properties: { query: { title: '提问内容' } } } } })
  try {
    assert.equal(view.state.label('query'), '提问内容')
    assert.equal(view.state.label('answer_terms'), '答案关键词')
    assert.deepEqual(view.state.entries, [['query', '完整输入'], ['answer_terms', ['北京']]])
  } finally { view.unmount() }
})

test('structured field editing preserves nested values, false, zero and null in a saved item', async () => {
  const writes = []
  const view = await mount('dataset/details/index.vue', { api: { updateEvaluationDatasetItem: async data => { writes.push(data) } } })
  try {
    view.state.activeVersion = { id: 2, status: 'draft', schema_snapshot: {} }
    const original = { id: 9, item_id: 101, input_data: { enabled: false, count: 0, optional: null, list: [1, '1'], nested: { answer: '原文' } }, expected_output: { answer: '原文' }, context: {}, metadata: {}, tags: [], weight: 1, enabled: true }
    view.state.openItem(original)
    const edited = view.state.parseFields(view.state.itemForm.input_text)
    edited.nested.answer = '修改后的原文'
    view.state.itemForm.input_text = JSON.stringify(edited)
    await view.state.saveItem()
    assert.deepEqual(writes[0].input_data, { ...original.input_data, nested: { answer: '修改后的原文' } })
    assert.equal(original.input_data.nested.answer, '原文')
  } finally { view.unmount() }
})

test('item drawer keeps its version and source keys while saving and prevents duplicate submissions', async () => {
  let finish
  const writes = []
  const view = await mount('dataset/details/index.vue', { api: { createEvaluationDatasetItem: async (id, data) => { writes.push({ id, data }); await new Promise(resolve => { finish = resolve }) } } })
  try {
    view.state.activeVersion = { id: 2, status: 'draft', schema_snapshot: { input_schema: { type: 'string' } } }
    view.state.openItem()
    assert.equal(view.state.itemEditorVisible, true)
    assert.equal(view.state.itemVersion.id, 2)
    view.state.itemForm.data_source = { kind: 'sql', key: 'contract_id', query: 'SELECT id FROM contracts', binding: { project_product_id: 1, ref_id: 10 } }
    view.state.activeVersion = { id: 3, status: 'draft', schema_snapshot: {} }
    const pending = view.state.saveItem()
    assert.equal(view.state.itemSaving, true)
    await view.state.saveItem()
    view.state.openItem()
    assert.equal(writes.length, 1)
    assert.equal(writes[0].id, 2)
    assert.equal(writes[0].data.data_source.key, 'contract_id')
    assert.equal(view.state.itemVersion.id, 2)
    finish(); await pending
    assert.equal(view.state.itemSaving, false)
    assert.equal(view.state.itemEditorVisible, false)
  } finally { view.unmount() }
})

test('published versions cannot open the item editor', async () => {
  const view = await mount('dataset/details/index.vue')
  try {
    view.state.activeVersion = { id: 2, status: 'published' }
    view.state.openItem()
    assert.equal(view.state.itemEditorVisible, false)
  } finally { view.unmount() }
})

test('schema inspection includes nested and array fields with independent required constraints', () => {
  const { schemaRows, dataSummary } = scriptModule('components/presentation.ts', () => {})
  const rows = schemaRows({ type: 'object', required: ['results'], properties: { results: { type: 'array', items: { type: 'object', required: ['score'], properties: { score: { type: 'number', minimum: 0 }, evidence: { type: 'string' } } } } } })
  assert.equal(rows.find(row => row.path === 'results').required, true)
  assert.equal(rows.find(row => row.path === 'results[].score').required, true)
  assert.equal(rows.find(row => row.path === 'results[].evidence').required, false)
  assert.equal(dataSummary({ enabled: false, score: 0 }), '启用：否；得分：0')
})

test('history navigation opens the drawer without changing the initial scroll anchor', async () => {
  const view = await mount('case/details/index.vue', { route: Vue.reactive({ query: { id: '1', tab: 'history' } }), api: { getEvaluationCase: async () => ({ data: { id: 1, name: '当前配置' } }) } })
  try {
    assert.equal(view.state.historyVisible, true)
    assert.equal(view.state.initialStep, 'data')
    view.state.historyVisible = false
    assert.equal(view.state.initialStep, 'data')
    assert.equal(view.state.record.name, '当前配置')
  }
  finally { view.unmount() }
})

test('history selection discards records returned from a previous environment', async () => {
  let oldResponse
  const view = await mount('components/ExecutionPanel.vue', { props: { caseId: 1, history: true }, api: { getCaseExecutions: async (_case, query) => query.test_env === 1 ? await new Promise(resolve => { oldResponse = resolve }) : { data: { items: [{ id: 22, verdict: 'passed', execution_no: 'NEW' }], count: 1 } } } })
  try {
    view.user.selected_environment = 2; await flush()
    assert.equal(view.state.selectedHistoryId, 22)
    oldResponse({ data: { items: [{ id: 11, execution_no: 'OLD' }], count: 1 } }); await flush()
    assert.equal(view.state.selectedHistoryId, 22)
    assert.equal(view.state.historyRows[0].execution_no, 'NEW')
  } finally { view.unmount() }
})

test('item browser selects the requested item outside the first page and deduplicates later pages', async () => {
  const queries = []
  const view = await mount('components/EvaluationItemBrowser.vue', { props: { caseId: 1, executionId: 11, initialItemId: 99 }, api: {
    getCaseExecution: async () => ({ data: { id: 11 } }),
    getCaseExecutionItems: async (_case, _execution, query) => { queries.push(query); return { data: { items: query.page === 1 ? [{ id: 1 }] : [{ id: 99 }], count: 21 } } },
    getCaseExecutionItem: async (_case, _execution, id) => ({ data: { id, dataset_item_id: id + 100 } }),
  } })
  try {
    assert.equal(view.state.selectedId, 99)
    assert.equal(view.state.itemDetail.id, 99)
    assert.deepEqual(view.state.items.map(item => item.id), [99, 1])
    await view.state.loadItems(false)
    assert.deepEqual(view.state.items.map(item => item.id), [99, 1])
    assert.equal(queries[1].page, 2)
    assert.equal(queries[0].pageSize, 20)
  } finally { view.unmount() }
})

test('item browser ignores a slow detail response after selecting another item', async () => {
  let oldResponse
  const view = await mount('components/EvaluationItemBrowser.vue', { props: { caseId: 1, executionId: 11 }, api: {
    getCaseExecution: async () => ({ data: { id: 11 } }),
    getCaseExecutionItems: async () => ({ data: { items: [], count: 0 } }),
    getCaseExecutionItem: async (_case, _execution, id) => id === 1 ? new Promise(resolve => { oldResponse = resolve }) : { data: { id } },
  } })
  try {
    const old = view.state.selectItem(1)
    await view.state.selectItem(2)
    oldResponse({ data: { id: 1 } }); await old
    assert.equal(view.state.selectedId, 2)
    assert.equal(view.state.itemDetail.id, 2)
    assert.equal(view.state.detailLoading, false)
  } finally { view.unmount() }
})

test('unexecuted grading preview shows configuration rows without fabricated test results', async () => {
  let requested = 0
  const view = await mount('components/ExecutionPanel.vue', { props: { caseId: 1, gradingPreview: { items: [{ item_id: 101, graders: [{ grader_key: 'exact_match', threshold: 100 }] }] }, onPreview: () => requested++ }, api: { getLatestCaseExecution: async () => ({ data: null }) } })
  try {
    assert.deepEqual(view.state.displayRows, [])
    view.state.toggleGrading(); await flush()
    assert.equal(requested, 1)
    assert.equal(view.state.displayRows[0].dataset_item_id, 101)
    assert.equal(view.state.displayRows[0].score, undefined)
    assert.ok(view.state.displayColumns.some(column => column.slotName === 'unexecuted'))
    view.state.toggleGrading()
    assert.deepEqual(view.state.displayRows, [])
  } finally { view.unmount() }
})

test('executed rows show frozen graders instead of current configuration and cache immutable bindings', async () => {
  let details = 0
  const frozen = { grader_key: 'exact_match', grader_version: 1, threshold: 80, weight: 1 }
  const view = await mount('components/ExecutionPanel.vue', { props: { caseId: 1, gradingPreview: { items: [{ item_id: 101, graders: [{ ...frozen, threshold: 100 }] }] } }, api: {
    getLatestCaseExecution: async () => ({ data: { id: 11, status: 'completed', snapshot: { grader_bindings: { hash: frozen } } } }),
    getCaseExecutionItems: async () => ({ data: { items: [{ id: 51, dataset_item_id: 101, score: 90 }], count: 1 } }),
    getCaseExecutionItem: async () => { details++; return { data: { item_snapshot: { effective_graders: [{ binding_hash: 'hash' }] } } } },
  } })
  try {
    view.state.toggleGrading(); await flush()
    assert.equal(view.state.rowGraders(view.state.displayRows[0])[0].threshold, 80)
    assert.equal(view.state.displayRows[0].score, 90)
    view.state.toggleGrading(); view.state.toggleGrading(); await flush()
    assert.equal(details, 1)
  } finally { view.unmount() }
})

test('grader editor generates unique internal metric keys and preserves existing identities when changing graders', async () => {
  const updates = []
  const view = await mount('components/GraderEditor.vue', { props: { modelValue: [{ grader_key: 'exact_match', grader_version: 1, metric_key: 'answer_correctness', parameters: {} }], catalog: [], 'onUpdate:modelValue': value => updates.push(value) } })
  try {
    view.state.add(); view.state.add()
    assert.notEqual(updates[0][1].metric_key, updates[1][1].metric_key)
    assert.match(updates[0][1].metric_key, /^metric_[a-f0-9]{32}$/)
    assert.ok(`${updates[0][1].metric_key}_recall_at_k`.length <= 64)
    view.state.choose(0, 'contains@1')
    assert.equal(updates[2][0].metric_key, 'answer_correctness')
    assert.equal(updates[2][0].grader_key, 'contains')
  } finally { view.unmount() }
})

test('evaluation labels and dropdowns follow the loaded global enum values', () => {
  const store = Vue.reactive({ evaluation_verdict: [{ key: 'passed', title: '全局通过文案' }] })
  const { useEvaluationEnums } = scriptModule('components/useEvaluationEnums.ts', () => ({ useEnum: () => store }))
  const enums = useEvaluationEnums()
  assert.equal(enums.title('evaluation_verdict', 'passed'), '全局通过文案')
  store.evaluation_verdict.push({ key: 'invalid', title: '结果无效' })
  assert.deepEqual(enums.options('evaluation_verdict'), [{ value: 'passed', label: '全局通过文案' }, { value: 'invalid', label: '结果无效' }])
  assert.equal(enums.color('passed'), 'green'); assert.equal(enums.color('failed'), 'red')
})

test('editing a schema description preserves nested constraints and required fields', async () => {
  const values = []
  const schema = { type: 'object', additionalProperties: false, required: ['score'], properties: { score: { type: 'number', minimum: 0, maximum: 100, default: 0 }, evidence: { type: 'object', properties: { text: { type: 'string', minLength: 1 } } } } }
  const view = await mount('components/SchemaEditor.vue', { props: { modelValue: schema, 'onUpdate:modelValue': value => values.push(value) } })
  try {
    view.state.update('score', { description: '确定性评分' })
    assert.deepEqual(values[0].properties.score, { ...schema.properties.score, description: '确定性评分' })
    assert.deepEqual(values[0].properties.evidence, schema.properties.evidence)
    assert.equal(values[0].additionalProperties, false)
    view.state.remove('score')
    assert.deepEqual(values[1].required, [])
    assert.equal('score' in values[1].properties, false)
    assert.equal(schema.properties.score.maximum, 100)
  } finally { view.unmount() }
})

test('field configuration saves structured fields and preserves workflow and variables', async () => {
  const writes = []
  const source = { input_schema: { type: 'object', additionalProperties: false, properties: { query: { type: 'string', minLength: 1 } } }, input_variables: [{ name: 'question', path: '$.query' }], workflow: { preparation: 'none', steps: [] } }
  const view = await mount('components/DatasetConfigDrawer.vue', { api: { updateDatasetVersion: async (id, data) => { writes.push({ id, data }); return { data: { id, ...data } } } } })
  try {
    view.state.open({ id: 8, version_no: 3, status: 'draft', schema_snapshot: source })
    view.state.config.input_schema.properties.query.title = '问题'
    view.state.config.input_schema.required = ['query']
    await view.state.save()
    assert.equal(writes[0].id, 8)
    assert.equal(writes[0].data.schema_snapshot.input_schema.properties.query.title, '问题')
    assert.equal(writes[0].data.schema_snapshot.input_schema.properties.query.minLength, 1)
    assert.equal(writes[0].data.schema_snapshot.input_schema.additionalProperties, false)
    assert.deepEqual(writes[0].data.schema_snapshot.input_variables, source.input_variables)
    assert.deepEqual(writes[0].data.schema_snapshot.workflow, { ...source.workflow, bindings: [] })
    assert.equal(source.input_schema.properties.query.title, undefined)
    assert.equal(view.state.visible, false)
    view.state.open({ id: 9, status: 'published', schema_snapshot: source })
    await view.state.save()
    assert.equal(writes.length, 1)
  } finally { view.unmount() }
})

test('published field rows cannot emit editing mutations', async () => {
  const writes = []
  const view = await mount('components/SchemaEditor.vue', { props: { disabled: true, modelValue: { properties: { query: { type: 'string' } } }, 'onUpdate:modelValue': value => writes.push(value) } })
  try {
    view.state.update('query', { title: '问题' })
    view.state.requireField('query', true)
    view.state.remove('query')
    assert.deepEqual(writes, [])
  } finally { view.unmount() }
})

test('dataset editing does not submit deleted project and module fields', async () => {
  const writes = []
  const view = await mount('dataset/index.vue', { api: { updateEvaluationDataset: async data => { writes.push(data); return {} } } })
  try {
    view.state.openEdit({ id: 9, name: 'before', project_product_id: 7, module_id: 4, task_type: ['generation'], version_count: 2, status: 'enabled' })
    view.state.form.name = 'after'
    await view.state.saveDataset()
    assert.deepEqual(writes, [{ id: 9, name: 'after', description: '', task_type: ['generation'], status: 'enabled' }])
  } finally { view.unmount() }
})

test('task types accept free labels, persist JSON arrays, and use JSON membership search', async () => {
  const writes = [], queries = []
  const view = await mount('dataset/index.vue', { api: {
    updateEvaluationDataset: async data => { writes.push(data); return {} },
    getEvaluationDatasets: async query => { queries.push(query); return { data: [] } },
  } })
  try {
    const record = { id: 9, name: '题库', project_product_id: 7, module_id: 4, task_type: ['记忆'], version_count: 2, status: 'enabled' }
    view.state.openEdit(record)
    view.state.form.task_type.push('记忆，问答', ' 用户自定义类型 ')
    await view.state.saveDataset()
    assert.deepEqual(writes[0].task_type, ['记忆', '问答', '用户自定义类型'])
    assert.deepEqual(record.task_type, ['记忆'])
    view.state.filters.task_type = ['记忆，问答']
    await view.state.load()
    assert.deepEqual(JSON.parse(queries.at(-1).task_types), ['记忆', '问答'])
    assert.equal('task_type__in' in queries.at(-1), false)
    view.state.openCreate()
    assert.deepEqual([...view.state.form.task_type], [])
  } finally { view.unmount() }
})

test('legacy scalar task types remain whole labels and can be removed without character ghosts', async () => {
  const writes = []
  const view = await mount('dataset/index.vue', { api: {
    getEvaluationDatasets: async () => ({ data: [{ id: 9, name: '题库', task_type: 'retrieval', status: 'enabled' }] }),
    updateEvaluationDataset: async data => { writes.push(data); return {} },
  } })
  try {
    assert.deepEqual(view.state.rows[0].task_type, ['retrieval'])
    const source = { id: 9, name: '题库', task_type: 'retrieval', status: 'enabled' }
    view.state.openEdit(source)
    assert.deepEqual(view.state.form.task_type, ['retrieval'])
    view.state.updateTaskTypes(['retrieval', '记忆'])
    view.state.updateTaskTypes(['记忆'])
    await view.state.saveDataset()
    assert.deepEqual(writes[0].task_type, ['记忆'])
    assert.equal(source.task_type, 'retrieval')
  } finally { view.unmount() }
})

test('duplicate task labels are normalized before rendering and removing the first never reintroduces it', async () => {
  const view = await mount('dataset/index.vue')
  try {
    view.state.openEdit({ id: 9, name: '题库', task_type: ['r', 'r', '记忆', ' 记忆 '], status: 'enabled' })
    assert.deepEqual(view.state.form.task_type, ['r', '记忆'])
    view.state.updateTaskTypes(['记忆'])
    assert.deepEqual(view.state.form.task_type, ['记忆'])
    view.state.updateTaskTypes([])
    assert.deepEqual(view.state.form.task_type, [])
  } finally { view.unmount() }
})

test('global dataset save requires task types and never submits project, module or tags', async () => {
  const writes = []
  const view = await mount('dataset/index.vue', { api: {
    createEvaluationDataset: async data => { writes.push(data); return {} },
  } })
  try {
    view.state.openCreate()
    Object.assign(view.state.form, { name: '题库', task_type: [' ', '，'] })
    await view.state.saveDataset()
    assert.equal(writes.length, 0)
    view.state.form.task_type = ['记忆，问答']
    await view.state.saveDataset()
    assert.equal(writes.length, 1)
    assert.deepEqual(writes[0].task_type, ['记忆', '问答'])
    assert.equal('module' in writes[0], false)
    assert.equal('project_product' in writes[0], false)
    assert.equal('tags' in writes[0], false)
    assert.equal('tags' in view.state.form, false)
  } finally { view.unmount() }
})

test('dataset status action is permission checked and changes only status', async () => {
  const writes = []
  let granted = false
  const view = await mount('dataset/index.vue', { permissions: { hasPermission: () => granted }, api: { updateEvaluationDataset: async data => { writes.push(data) } } })
  try {
    await view.state.changeDatasetStatus({ id: 1, status: 'enabled' })
    assert.equal(writes.length, 0)
    granted = true
    await view.state.changeDatasetStatus({ id: 1, status: 'enabled' })
    await view.state.changeDatasetStatus({ id: 1, status: 'archived', current_version: 2 })
    assert.deepEqual(writes, [{ id: 1, status: 'archived' }, { id: 1, status: 'enabled' }])
  } finally { view.unmount() }
})

test('published schema has a read-only inspection path', async () => {
  const view = await mount('components/DatasetConfigDrawer.vue')
  try {
    view.state.open({ version_no: 2, status: 'published', content_hash: 'digest', schema_snapshot: { input_schema: { type: 'object' } } })
    assert.equal(view.state.visible, true)
    assert.equal(view.state.readonly, true)
    assert.deepEqual(view.state.config.input_schema, { type: 'object' })
  } finally { view.unmount() }
})

test('dataset list navigates to the version subpage without loading drawer assets', async () => {
  const navigations = [], reads = []
  const view = await mount('dataset/index.vue', { router: { push: target => navigations.push(target) }, api: {
    getDatasetVersions: async () => { reads.push('versions'); return { data: { items: [] } } },
  } })
  try {
    view.state.openVersions({ id: 12, name: '记忆题库' })
    assert.deepEqual(navigations, [{ path: '/evaluation/dataset/details', query: { id: 12, name: '记忆题库' } }])
    assert.deepEqual(reads, [])
    assert.equal(view.state.versionVisible, undefined)
  } finally { view.unmount() }
})

test('dataset version subpage reloads from the URL and selects the latest version', async () => {
  const reads = []
  const view = await mount('dataset/details/index.vue', { route: { query: { id: '12', name: '记忆题库' } }, api: {
    getDatasetVersions: async id => { reads.push(id); return { data: { items: [{ id: 25, version_no: 2, status: 'published' }], count: 1 } } },
    getEvaluationDatasetItems: async id => { reads.push(id); return { data: { items: [{ id: 30, item_id: 101 }], count: 1 } } },
  } })
  try {
    assert.deepEqual(reads, [12, 25])
    assert.equal(view.state.activeDataset.name, '记忆题库')
    assert.equal(view.state.activeVersion.id, 25)
    assert.equal(view.state.items[0].id, 30)
  } finally { view.unmount() }
})

test('publishing automatically checks the dataset and publishes without a separate check step', async () => {
  const calls = []
  const view = await mount('dataset/details/index.vue', { api: {
    getDatasetQuality: async id => { calls.push(['check', id]); return { data: { errors: [], warnings: [] } } },
    publishDatasetVersion: async id => { calls.push(['publish', id]) },
  } })
  try {
    await view.state.publishVersion({ id: 4, status: 'draft' })
    assert.deepEqual(calls, [['check', 4], ['publish', 4]])
    assert.equal(view.state.publishingVersionId, undefined)
  } finally { view.unmount() }
})

test('publication errors retain the item ID and never publish', async () => {
  let published = false, opened = false
  const view = await mount('dataset/details/index.vue', { api: {
    getDatasetQuality: async () => ({ data: { errors: [{ item_id: 25, message: '问题不能为空' }], warnings: [] } }),
    publishDatasetVersion: async () => { published = true },
  } })
  try {
    view.state.qualityDialogRef = { show: () => { opened = true } }
    await view.state.publishVersion({ id: 4, status: 'draft' })
    assert.equal(opened, true)
    assert.equal(view.state.qualityReport.errors[0].item_id, 25)
    assert.equal(published, false)
    assert.equal(view.state.publishingVersionId, undefined)
  } finally { view.unmount() }
})

test('publication warnings show affected items and require confirmation before writing', async () => {
  let confirmation
  const writes = []
  const view = await mount('dataset/details/index.vue', { modal: { warning: value => { confirmation = value } }, api: {
    getDatasetQuality: async () => ({ data: { errors: [], warnings: [{ message: '存在重复条目', groups: [[25, 26]] }] } }),
    acknowledgeDatasetQuality: async id => { writes.push(['acknowledge', id]) },
    publishDatasetVersion: async id => { writes.push(['publish', id]) },
  } })
  try {
    await view.state.publishVersion({ id: 4, status: 'draft' })
    assert.match(confirmation.content, /25、26/)
    assert.deepEqual(writes, [])
    assert.equal(view.state.publishConfirmationOpen, true)
    assert.equal(await confirmation.onBeforeOk(), true)
    assert.deepEqual(writes, [['acknowledge', 4], ['publish', 4]])
    confirmation.onClose()
    assert.equal(view.state.publishConfirmationOpen, false)
  } finally { view.unmount() }
})

test('copying a dataset version requires confirmation and cancelling never creates a draft', async () => {
  let confirmation, release
  const writes = []
  const source = { id: 25, version_no: 2, status: 'published' }
  const view = await mount('dataset/details/index.vue', { route: { query: { id: '12' } }, modal: { confirm: value => { confirmation = value } }, api: {
    getDatasetVersions: async () => ({ data: { items: [source], count: 1 } }),
    getEvaluationDatasetItems: async () => ({ data: { items: [], count: 0 } }),
    createDatasetVersion: async (id, data) => { writes.push({ id, data }); await new Promise(resolve => { release = resolve }) },
  } })
  try {
    view.state.cloneVersion(source)
    assert.match(confirmation.content, /V2/)
    assert.deepEqual(writes, [])
    confirmation.onClose()
    assert.equal(view.state.cloneConfirmationOpen, false)
    assert.deepEqual(writes, [])
    view.state.cloneVersion(source)
    const pending = confirmation.onBeforeOk()
    assert.equal(view.state.versionCreating, true)
    assert.equal(await confirmation.onBeforeOk(), false)
    assert.deepEqual(writes, [{ id: 12, data: { source_version_id: 25 } }])
    release(); assert.equal(await pending, true)
    assert.equal(view.state.versionCreating, false)
    confirmation.onClose()
  } finally { view.unmount() }
})

test('draft deletion confirms, prevents published deletion and selects a remaining version', async () => {
  const remaining = { id: 24, version_no: 1, status: 'published' }
  const draft = { id: 25, version_no: 2, status: 'draft' }
  let records = [draft, remaining], confirmation
  const deleted = []
  const view = await mount('dataset/details/index.vue', { route: { query: { id: '12' } }, modal: { warning: value => { confirmation = value } }, api: {
    getDatasetVersions: async () => ({ data: { items: records, count: records.length } }),
    deleteDatasetVersion: async id => { deleted.push(id); records = records.filter(record => record.id !== id) },
    getEvaluationDatasetItems: async () => ({ data: { items: [], count: 0 } }),
  } })
  try {
    view.state.removeVersion(remaining)
    assert.equal(confirmation, undefined)
    view.state.removeVersion(draft)
    assert.equal(deleted.length, 0)
    await confirmation.onOk()
    assert.deepEqual(deleted, [25])
    assert.equal(view.state.activeVersion.id, 24)
    assert.equal(view.state.deletingVersionId, undefined)
  } finally { view.unmount() }
})

test('invalid or unauthorized dataset links never request versions', async () => {
  for (const [id, permitted] of [['invalid', true], ['12', false]]) {
    const reads = []
    const view = await mount('dataset/details/index.vue', { route: { query: { id } }, permissions: { hasPermission: () => permitted }, api: {
      getDatasetVersions: async () => { reads.push(true); return {} },
    } })
    try {
      assert.deepEqual(reads, [])
      assert.equal(view.state.activeDataset, undefined)
    } finally { view.unmount() }
  }
})

test('versions load twenty at a time on bottom scroll, append once and stop at total', async () => {
  const requests = []
  let finish
  const view = await mount('dataset/details/index.vue', { route: { query: { id: '12' } }, api: {
    getDatasetVersions: async (_id, query) => {
      requests.push({ ...query })
      if (query.page === 2) return new Promise(resolve => { finish = resolve })
      return { data: { items: Array.from({ length: 20 }, (_, i) => ({ id: i + 1 })), count: 22 } }
    },
  } })
  try {
    assert.deepEqual(requests, [{ page: 1, pageSize: 20 }])
    view.state.onVersionScroll({ currentTarget: { scrollTop: 0, clientHeight: 400, scrollHeight: 800 } })
    assert.equal(requests.length, 1)
    const selected = view.state.activeVersion.id
    view.state.onVersionScroll({ currentTarget: { scrollTop: 400, clientHeight: 400, scrollHeight: 800 } })
    view.state.loadMoreVersions()
    assert.equal(requests.length, 2)
    assert.equal(view.state.versionLoadingMore, true)
    assert.equal(view.state.versionLoading, false)
    finish({ data: { items: [{ id: 20 }, { id: 21 }, { id: 22 }], count: 22 } })
    await flush()
    assert.equal(view.state.versions.length, 22)
    assert.equal(view.state.activeVersion.id, selected)
    assert.equal(view.state.hasMoreVersions, false)
    await view.state.loadMoreVersions()
    assert.equal(requests.length, 2)
    await view.state.loadVersions()
    assert.deepEqual(requests.at(-1), { page: 1, pageSize: 20 })
    assert.equal(view.state.versions.length, 20)
  } finally { view.unmount() }
})

test('failed version append retries the same page and ignores a stale response after refresh', async () => {
  let calls = 0, finish
  const view = await mount('dataset/details/index.vue', { route: { query: { id: '12' } }, api: {
    getDatasetVersions: async (_id, query) => {
      if (query.page === 1) return { data: { items: [{ id: 1 }], count: 21 } }
      calls++
      if (calls === 1) throw new Error('offline')
      return new Promise(resolve => { finish = resolve })
    },
  } })
  try {
    await view.state.loadMoreVersions()
    assert.equal(view.state.versionLoadError, true)
    assert.equal(view.state.versionPagination.page, 1)
    assert.equal(view.state.versions.length, 1)
    const retry = view.state.retryVersions()
    assert.equal(calls, 2)
    await view.state.loadVersions()
    finish({ data: { items: [{ id: 99 }], count: 21 } })
    await retry
    assert.deepEqual(view.state.versions.map(row => row.id), [1])
    assert.equal(view.state.versionLoadingMore, false)
    assert.equal(view.state.versionLoadError, false)
  } finally { view.unmount() }
})

test('switching versions keeps the new selection when the older item request finishes late', async () => {
  const pending = new Map()
  const view = await mount('dataset/details/index.vue', { route: { query: { id: '12' } }, api: {
    getDatasetVersions: async () => ({ data: { items: [{ id: 2, version_no: 2 }], count: 1 } }),
    getEvaluationDatasetItems: id => new Promise(resolve => pending.set(id, resolve)),
  } })
  try {
    const next = view.state.selectVersion({ id: 1, version_no: 1 })
    pending.get(1)({ data: { items: [{ id: 301 }], count: 1 } })
    await next
    pending.get(2)({ data: { items: [{ id: 302 }], count: 1 } })
    await flush()
    assert.equal(view.state.activeVersion.id, 1)
    assert.equal(view.state.items[0].id, 301)
    assert.equal(view.state.itemLoading, false)
  } finally { view.unmount() }
})

test('environment switching clears a previously selected execution in Case details', async () => {
  const replacements = []
  const view = await mount('case/details/index.vue', { router: { replace: value => replacements.push(value) }, route: Vue.reactive({ query: { id: '1', execution: '101' } }) })
  try {
    assert.equal(view.state.executionId, 101)
    view.user.selected_environment = 2
    await flush()
    assert.equal(view.state.executionId, undefined)
    assert.equal(replacements[0].query.execution, undefined)
  } finally { view.unmount() }
})

test('Case details loads when permissions finish initializing and clears data after revocation', async () => {
  const access = Vue.reactive({ granted: false })
  let reads = 0
  const view = await mount('case/details/index.vue', { route: Vue.reactive({ query: { id: '1' } }),
    permissions: { hasPermission: () => access.granted }, api: { getEvaluationCase: async () => { reads += 1; return { data: { id: 1 } } } } })
  try {
    assert.equal(reads, 0)
    access.granted = true
    await flush()
    assert.equal(reads, 1)
    assert.equal(view.state.record.id, 1)
    access.granted = false
    await flush()
    assert.equal(view.state.record, undefined)
  } finally { view.unmount() }
})

test('initial environment hydration preserves the execution deep link', async () => {
  const user = Vue.reactive({ selected_environment: undefined })
  const replacements = []
  const view = await mount('case/details/index.vue', { user, router: { replace: value => replacements.push(value) },
    route: Vue.reactive({ query: { id: '1', execution: '101' } }) })
  try {
    user.selected_environment = 3
    await flush()
    assert.equal(view.state.executionId, 101)
    assert.equal(replacements.length, 0)
  } finally { view.unmount() }
})

test('a retry response from the previous environment cannot select its execution', async () => {
  let complete
  const selected = []
  const api = { getLatestCaseExecution: async () => ({ data: { id: 101, status: 'completed' } }), getCaseExecutionItems: async () => ({ data: { items: [], count: 0 } }), retryCaseExecution: () => new Promise(resolve => { complete = resolve }) }
  const view = await mount('components/ExecutionPanel.vue', { api, props: { caseId: 1, onSelected: id => selected.push(id) } })
  try {
    const retry = view.state.retry()
    view.user.selected_environment = 2
    await flush()
    complete({ data: { id: 202 } })
    await retry
    assert.deepEqual(selected, [])
  } finally { view.unmount() }
})

function editorFixture() {
  const { defaultCaseConfig } = scriptModule('case/config.ts', () => {})
  const config = defaultCaseConfig()
  config.target = { type: 'script', ref_id: null, version_ref: null, parameters: { code: 'def main(input, context):\n    return input\n' } }
  return { id: 7, name: 'Original', description: '', project_product: 22, module: null, dataset_id: 1, dataset_version: 2, status: 'enabled', config }
}
function editorOptions(record, update, extra = {}) {
  return { props: { embedded: true, caseId: record.id, initialRecord: record, initialCatalog: [] }, api: {
    getEvaluationDatasets: async () => ({ data: [{ id: 1, name: 'Dataset' }] }),
    getDatasetVersions: async () => ({ data: [{ id: 2, version_no: 2, status: 'published' }] }),
    updateEvaluationCase: update,
  }, ...extra }
}

test('incomplete quality gates never reach autosave and valid gates save intact', async () => {
  const writes = []
  const view = await mount('components/CaseEditor.vue', editorOptions(editorFixture(), async value => writes.push(value)))
  try {
    view.state.config.grading.quality_gates = [{}]
    await flush()
    assert.equal(await view.state.flush(), false)
    assert.match(view.state.saveStatus, /质量门禁第 1 条：请选择统计指标/)
    assert.equal(writes.length, 0)
    view.state.config.grading.quality_gates = [{ key: 'valid_rate', operator: 'gte', threshold: 0.95, severity: 'critical' }]
    assert.equal(await view.state.flush(), true)
    assert.deepEqual(writes[0].config.grading.quality_gates, [{ key: 'valid_rate', operator: 'gte', threshold: 0.95, severity: 'critical' }])
  } finally { view.unmount() }
})

test('run requirements reject missing and out-of-range rates before saving', async () => {
  let writes = 0
  const view = await mount('components/CaseEditor.vue', editorOptions(editorFixture(), async () => { writes++ }))
  try {
    view.state.config.grading.aggregation.min_valid_rate = null
    await flush()
    assert.equal(await view.state.flush(), false)
    view.state.config.grading.aggregation.min_valid_rate = 1
    view.state.config.grading.aggregation.min_effect_pass_rate = 80
    await flush()
    assert.equal(await view.state.flush(), false)
    assert.equal(writes, 0)
    view.state.config.grading.aggregation.min_effect_pass_rate = 0.8
    assert.equal(await view.state.flush(), true)
    assert.equal(writes, 1)
  } finally { view.unmount() }
})

test('scenario description edits belong to external case metadata and preserve execution configuration', async () => {
  const writes = [], record = editorFixture()
  const view = await mount('components/CaseEditor.vue', { props: { embedded: false }, api: {
    getEvaluationCase: async () => ({ data: record }),
    updateEvaluationCase: async value => writes.push(value),
  } })
  try {
    await view.state.open(record.id)
    view.state.form.description = 'Given 已有记忆\nWhen 查询当前住址\nThen 返回北京'
    await view.state.save()
    assert.equal(writes.length, 1)
    assert.equal(writes[0].description, view.state.form.description)
    assert.equal('config' in writes[0], false)
  } finally { view.unmount() }
})

test('quality gate editor uses structured defaults and protects readonly values', async () => {
  for (const disabled of [false, true]) {
    const values = []
    const view = await mount('components/QualityGateEditor.vue', { props: { modelValue: [], disabled,
      'onUpdate:modelValue': value => values.push(value) } })
    try {
      view.state.add()
      assert.deepEqual(values, disabled ? [] : [[{ key: '', operator: 'gte', threshold: 0, severity: 'critical' }]])
      const gate = { key: 'valid_rate', threshold: 1 }
      view.state.choose(gate, 'metric:accuracy')
      assert.equal(gate.key, disabled ? 'valid_rate' : 'accuracy')
      assert.equal(gate.metric_key, disabled ? undefined : 'accuracy')
    } finally { view.unmount() }
  }
})

test('item selection drawer keeps cross-page checkboxes local until save and supports exclusion', async () => {
  const saved = [], original = { exclude: false, item_ids: [101] }
  const view = await mount('components/ItemSelectionDrawer.vue', { props: { versionId: 2, modelValue: original,
    saveSelection: async value => { saved.push(value); return true } }, api: {
      getEvaluationDatasetItems: async () => ({ data: { items: [{ id: 101, enabled: true }, { id: 102, enabled: true }], count: 3 } }),
    } })
  try {
    view.state.open(); await flush()
    view.state.select([101, 102])
    view.state.records = [{ id: 103, enabled: true }]
    view.state.select([103])
    assert.deepEqual(view.state.selected, [101, 102, 103])
    view.state.exclude = true
    assert.deepEqual(original, { exclude: false, item_ids: [101] })
    view.state.visible = false
    assert.deepEqual(saved, [])
    view.state.open(); await flush()
    assert.deepEqual(view.state.selected, [101])
    view.state.exclude = true
    await view.state.save()
    assert.deepEqual(saved, [{ exclude: true, item_ids: [101] }])
    assert.equal(view.state.visible, false)
  } finally { view.unmount() }
})

test('failed and readonly item selection saves do not close or mutate configured keys', async () => {
  let calls = 0
  const view = await mount('components/ItemSelectionDrawer.vue', { props: { versionId: 2, modelValue: { item_ids: [] },
    saveSelection: async () => { calls++; return false } } })
  try {
    view.state.open(); await flush()
    await view.state.save()
    assert.equal(view.state.visible, true)
    assert.equal(view.state.saving, false)
    assert.equal(calls, 1)
  } finally { view.unmount() }
  const readonly = await mount('components/ItemSelectionDrawer.vue', { props: { versionId: 2, disabled: true,
    modelValue: { item_ids: [101] }, saveSelection: async () => { calls++; return true } } })
  try {
    readonly.state.open(); await flush()
    readonly.state.select([102]); await readonly.state.save()
    assert.deepEqual(readonly.state.selected, [101])
    assert.equal(calls, 1)
  } finally { readonly.unmount() }
})

test('all AI roles can explicitly save the system default alongside independent profiles', async () => {
  const writes = [], record = editorFixture()
  const options = editorOptions(record, async data => { writes.push(data) })
  options.api.getEvaluationAiProfiles = async () => ({ data: { items: [
    { id: '__system_default__', name: '系统默认 AI', model: 'default-model', enabled: true },
    { id: 'judge', name: '独立裁判', model: 'judge-model', enabled: true },
  ] } })
  const view = await mount('components/CaseEditor.vue', options)
  try {
    assert.equal(view.state.aiOptions[0].label, '系统默认 AI · default-model')
    assert.equal(view.state.aiOptions[0].disabled, false)
    assert.equal(view.state.aiOptions.length, 2)
    view.state.config.ai = { judge_profile_id: '__system_default__', answer_profile_id: '__system_default__', summary_profile_id: '__system_default__' }
    await flush()
    assert.equal(await view.state.flush(), true)
    assert.deepEqual(writes[0].config.ai, { judge_profile_id: '__system_default__', answer_profile_id: '__system_default__', summary_profile_id: '__system_default__' })
  } finally { view.unmount() }
})

test('simple extraction retains incomplete drafts and emits only valid unique expressions', async () => {
  const values = [], errors = []
  const view = await mount('components/ExtractionEditor.vue', { props: {
    modelValue: { paths: [] },
    'onUpdate:modelValue': value => values.push(value), onValidityChange: message => errors.push(message),
  } })
  try {
    assert.equal(values.length, 0)
    view.state.add()
    assert.match(errors.at(-1), /填写/)
    assert.equal(values.length, 0)
    view.state.rows[0].path = '$.messages[0].content'; view.state.changed()
    assert.deepEqual(values.at(-1), { paths: ['$.messages[0].content'] })
    view.state.add()
    view.state.rows[1].path = '$.messages[0].content'; view.state.changed()
    assert.match(errors.at(-1), /重复/)
    assert.equal(values.length, 1)
    view.state.remove(1); view.state.remove(0)
    assert.deepEqual(values.at(-1), { paths: [] })
  } finally { view.unmount() }
})

test('readonly extraction retains values without mutations', async () => {
  const values = [], original = { paths: ['$.json.items'] }
  const view = await mount('components/ExtractionEditor.vue', { props: { disabled: true, modelValue: original,
    'onUpdate:modelValue': value => values.push(value) } })
  try {
    assert.equal(view.state.rows[0].path, '$.json.items')
    view.state.add(); view.state.remove(0)
    assert.deepEqual(values, [])
    assert.deepEqual(original, { paths: ['$.json.items'] })
  } finally { view.unmount() }
})

test('answering stays a fixed step and a blank AI selection skips generation', async () => {
  let writes = 0
  const record = editorFixture()
  const view = await mount('components/CaseEditor.vue', editorOptions(record, async () => { writes++ }))
  try {
    assert.deepEqual(view.state.visibleConfigSteps.map(step => step.key), ['data', 'target', 'answering', 'grading', 'policy'])
    assert.equal(view.state.dirty, false)
    view.state.answerProfile = 'answer-ai'
    assert.deepEqual(view.state.visibleConfigSteps.map(step => step.key), ['data', 'target', 'answering', 'grading', 'policy'])
    assert.equal(view.state.config.answering.max_tokens, 800)
    assert.equal(view.state.config.ai.answer_profile_id, 'answer-ai')
    view.state.answerProfile = undefined
    assert.equal(view.state.config.answering, null)
    assert.equal(view.state.config.ai.answer_profile_id, null)
    assert.deepEqual(view.state.visibleConfigSteps.map(step => step.key), ['data', 'target', 'answering', 'grading', 'policy'])
    assert.equal(view.state.config.data_selection.input_variable, undefined)
    assert.equal('input' in view.state.config.mapping, false)
    assert.equal('runtime_context' in view.state.config, false)
    assert.equal(writes, 0)
  } finally { view.unmount() }
})

test('fixed answering step preserves existing generation settings and platform default AI', async () => {
  const record = editorFixture()
  record.config.answering = { question_path: 'question.text', max_tokens: 1600 }
  record.config.ai = { answer_profile_id: null, judge_profile_id: null, summary_profile_id: null }
  const view = await mount('components/CaseEditor.vue', editorOptions(record, async () => {}))
  try {
    assert.equal(view.state.answerProfile, '__platform_default__')
    assert.equal(view.state.dirty, false)
    view.state.answerProfile = 'answer-ai'
    assert.equal(view.state.config.answering.question_path, 'question.text')
    assert.equal(view.state.config.answering.max_tokens, 1600)
    assert.equal(view.state.visibleConfigSteps.find(step => step.key === 'answering').title, '召回后生成回答')
  } finally { view.unmount() }
})

test('dataset owns input variables and Case saves only item selection', async () => {
  const record = editorFixture(), writes = []
  record.config.runtime_context = [{ key: 'old-source' }]
  record.config.mapping.input = { mode: 'select', selectors: { old: 'runtime.value' } }
  const view = await mount('components/CaseEditor.vue', editorOptions(record, async value => writes.push(value)))
  try {
    assert.equal('runtime_context' in view.state.config, false)
    assert.equal('input' in view.state.config.mapping, false)
    assert.equal(await view.state.saveItemSelection({ exclude: true, item_ids: [101] }), true)
    assert.deepEqual(writes[0].config.data_selection, { exclude: true, item_ids: [101] })
    assert.equal(view.state.inputVariableReference, '${{case_input}}')
    assert.equal(await view.state.flush(), true)
    assert.equal(writes.length, 1)
    assert.equal(record.config.runtime_context[0].key, 'old-source')
  } finally { view.unmount() }
})

test('incomplete extraction blocks execution flush even when saved configuration has not changed', async () => {
  let writes = 0
  const guards = [], view = await mount('components/CaseEditor.vue', editorOptions(editorFixture(), async () => { writes++ }, { guards }))
  try {
    view.state.extractionErrors.output = 'JSONPath 必须以 $ 开头'; await flush()
    assert.equal(view.state.dirty, true)
    assert.equal(await view.state.flush(), false)
    assert.equal(await guards[0](), false)
    assert.equal(writes, 0)
    view.state.extractionErrors.output = ''; await flush()
    assert.equal(await view.state.flush(), true)
    assert.equal(writes, 0)
  } finally { view.unmount() }
})

test('inline configuration loads without writes and saves the latest draft after debounce', async context => {
  context.mock.timers.enable({ apis: ['setTimeout'] })
  const updates = [], record = editorFixture()
  const view = await mount('components/CaseEditor.vue', editorOptions(record, async value => { updates.push(structuredClone(value)) }))
  try {
    assert.equal(view.state.ready, true)
    context.mock.timers.tick(1000); await flush()
    assert.equal(updates.length, 0)
    view.state.config.execution.item_timeout_seconds = 100; await flush()
    context.mock.timers.tick(300)
    view.state.config.execution.item_timeout_seconds = 200; await flush()
    context.mock.timers.tick(599); await flush()
    assert.equal(updates.length, 0)
    context.mock.timers.tick(1); await flush()
    assert.equal(updates.length, 1)
    assert.equal(updates[0].config.execution.item_timeout_seconds, 200)
    assert.equal('name' in updates[0], false)
    assert.equal('status' in updates[0], false)
    assert.equal('description' in updates[0], false)
    assert.equal(view.state.dirty, false)
    assert.equal(record.name, 'Original')
  } finally { view.unmount() }
})

test('inline autosave serializes writes and drains edits made while a save is in flight', async () => {
  let finish
  const updates = [], record = editorFixture()
  const view = await mount('components/CaseEditor.vue', editorOptions(record, async value => {
    updates.push(structuredClone(value))
    if (updates.length === 1) await new Promise(resolve => { finish = resolve })
  }))
  try {
    view.state.config.execution.item_timeout_seconds = 100; await flush()
    const first = view.state.flush()
    assert.equal(updates.length, 1)
    view.state.config.execution.repeat_count = 2; await flush()
    const second = view.state.flush()
    assert.equal(updates.length, 1)
    finish(); assert.equal(await first, true); assert.equal(await second, true)
    assert.equal(updates.length, 2)
    assert.equal(updates[1].config.execution.repeat_count, 2)
    assert.equal(view.state.dirty, false)
  } finally { view.unmount() }
})

test('save failures retain the draft and block navigation until an explicit retry succeeds', async () => {
  const guards = [], record = editorFixture()
  let fail = true
  const view = await mount('components/CaseEditor.vue', editorOptions(record, async () => { if (fail) throw new Error('offline') }, { guards }))
  try {
    view.state.config.execution.retry_count = 1; await flush()
    assert.equal(await guards[0](), false)
    assert.equal(view.state.config.execution.retry_count, 1)
    assert.equal(view.state.dirty, true)
    assert.match(view.state.saveStatus, /保存失败/)
    fail = false
    assert.equal(await view.state.flush(), true)
    assert.equal(view.state.saveStatus, '已保存')
    assert.equal(await guards[0](), true)
  } finally { view.unmount() }
})

test('readonly configuration cannot autosave and incomplete target changes are not submitted', async () => {
  let writes = 0
  const readonly = await mount('components/CaseEditor.vue', editorOptions(editorFixture(), async () => { writes++ }, { permissions: { hasPermission: () => false } }))
  try { readonly.state.config.execution.retry_count = 1; await flush(); assert.equal(await readonly.state.flush(), false); assert.equal(writes, 0); assert.equal(readonly.state.saveStatus, '只读') }
  finally { readonly.unmount() }
  const editable = await mount('components/CaseEditor.vue', editorOptions(editorFixture(), async () => { writes++ }))
  try {
    editable.state.config.target.type = 'api_info'; editable.state.targetChanged(); await flush()
    assert.equal(await editable.state.flush(), false)
    assert.equal(writes, 0)
    assert.match(editable.state.saveStatus, /已发布接口/)
  } finally { editable.unmount() }
})

test('interface selection is scoped by module and marks unpublished rows disabled', async () => {
  const requests = []
  const options = editorOptions(editorFixture(), async () => {})
  options.api.getEvaluationInterfaces = async (id, query) => {
    requests.push([id, query])
    return { data: { count: 2, items: [{ id: 11, name: '问答', protocol_type: 'http', published: true }, { id: 12, name: '流式问答', protocol_type: 'sse', published: false }] } }
  }
  const view = await mount('components/CaseEditor.vue', options)
  try {
    view.state.config.target.type = 'api_info'; view.state.targetChanged()
    view.state.targetModule = 4
    await view.state.targetModuleChanged(); await flush()
    assert.equal(requests[0][0], 7)
    assert.equal(requests[0][1].module_id, 4)
    assert.equal(view.state.interfaceOptions[0].disabled, false)
    assert.equal(view.state.interfaceOptions[1].disabled, true)
    assert.match(view.state.interfaceOptions[1].label, /SSE（未发布）/)
    assert.equal(view.state.config.target.version_ref, null)
  } finally { view.unmount() }
})

test('old module requests cannot replace the latest interface choices', async () => {
  const pending = new Map(), options = editorOptions(editorFixture(), async () => {})
  options.api.getEvaluationInterfaces = (id, query) => new Promise(resolve => pending.set(query.module_id, resolve))
  const view = await mount('components/CaseEditor.vue', options)
  try {
    view.state.config.target.type = 'api_info'; view.state.targetChanged()
    view.state.targetModule = 4; const older = view.state.loadInterfaces()
    view.state.targetModule = 5; const newer = view.state.loadInterfaces()
    pending.get(5)({ data: { items: [{ id: 15, published: true }], count: 1 } }); await newer
    pending.get(4)({ data: { items: [{ id: 14, published: true }], count: 1 } }); await older
    assert.equal(view.state.interfaces[0].id, 15)
    assert.equal(view.state.interfacesLoading, false)
    view.state.config.target.type = 'script'; view.state.targetChanged()
    assert.deepEqual(view.state.interfaces, [])
    assert.match(view.state.config.target.parameters.code, /def main\(input, context\)/)
    assert.equal(view.state.config.target.ref_id, null)
  } finally { view.unmount() }
})

test('execution waits for configuration persistence and refuses to run on save failure', async () => {
  let executions = 0, finish
  const anchors = []
  const view = await mount('case/details/index.vue', { route: Vue.reactive({ query: { id: '7' } }), api: {
    getEvaluationCase: async () => ({ data: { id: 7, status: 'enabled' } }),
    executeEvaluationCase: async () => { executions++; return { data: { id: 31 } } },
  } })
  try {
    view.state.editor = { flush: () => new Promise(resolve => { finish = resolve }) }
    const pending = view.state.execute(); await flush()
    assert.equal(executions, 0)
    finish(false); await pending
    assert.equal(executions, 0)
    assert.deepEqual(anchors, [])
    view.state.editor = { flush: async () => true, scrollToStep: key => anchors.push(key) }
    await view.state.execute()
    assert.equal(executions, 1)
    assert.equal(view.state.executionId, 31)
    assert.deepEqual(anchors, ['results'])
  } finally { view.unmount() }
})

test('header save button follows editor autosave state, retries failures and guards concurrent saves', async () => {
  let finish, writes = 0
  const permissions = { hasPermission: () => true }
  const view = await mount('case/details/index.vue', { permissions, route: { query: { id: '1' } }, api: {
    getEvaluationCase: async () => ({ data: { id: 1, status: 'enabled' } }),
  } })
  const editor = Vue.reactive({ ready: true, dirty: false, saving: false, loading: false, saveError: '',
    async flush() {
      writes++; editor.saving = true
      const saved = await new Promise(resolve => { finish = resolve })
      editor.saving = false
      editor.saveError = saved ? '' : '保存失败'
      editor.dirty = !saved
      return saved
    },
  })
  try {
    view.state.editor = editor
    assert.equal(view.state.saveButtonLabel, '已保存')
    editor.dirty = true
    assert.equal(view.state.saveButtonLabel, '保存')
    const first = view.state.saveConfiguration()
    assert.equal(view.state.saveButtonLabel, '保存中')
    await view.state.saveConfiguration()
    assert.equal(writes, 1)
    finish(false); await first
    assert.equal(view.state.saveButtonLabel, '重试保存')
    const retry = view.state.saveConfiguration()
    finish(true); await retry
    assert.equal(view.state.saveButtonLabel, '已保存')
    permissions.hasPermission = () => false
    editor.dirty = true
    await view.state.saveConfiguration()
    assert.equal(writes, 2)
  } finally { view.unmount() }
})

test('header save can retry failed editor initialization without submitting incomplete configuration', async () => {
  const opened = []
  const view = await mount('case/details/index.vue', { route: { query: { id: '1' } }, api: {
    getEvaluationCase: async () => ({ data: { id: 1 } }),
  } })
  try {
    view.state.editor = { ready: false, loading: false, saving: false, saveError: '配置加载失败',
      open: async id => opened.push(id), flush: () => assert.fail('must reload before saving') }
    assert.equal(view.state.saveButtonLabel, '重试加载')
    await view.state.saveConfiguration()
    assert.deepEqual(opened, [1])
  } finally { view.unmount() }
})

test('case result deep links target the results anchor and reset on a different case', async () => {
  const route = Vue.reactive({ query: { id: '1', execution: '25' } })
  const view = await mount('case/details/index.vue', { route, api: {
    getEvaluationCase: async id => ({ data: { id, name: '配置' } }),
  } })
  try {
    assert.equal(view.state.initialStep, 'results')
    assert.equal(view.state.executionId, 25)
    const editor = { flush: async () => true }
    view.state.editor = editor
    assert.equal(Vue.toRaw(view.state.editor), editor)
    route.query = { id: '2' }
    await flush()
    assert.equal(view.state.initialStep, 'data')
    assert.equal(view.state.executionId, undefined)
  } finally { view.unmount() }
})

test('outer create form sends metadata only and does not load configuration assets', async () => {
  const created = []
  let assetReads = 0
  const view = await mount('components/CaseEditor.vue', { api: {
    createEvaluationCase: async value => { created.push(value); return { data: { id: 99 } } },
    getEvaluationDatasets: async () => { assetReads++; return { data: [] } },
    getCaseGraderCatalog: async () => { assetReads++; return { data: [] } },
  } })
  try {
    await view.state.open(undefined, 22, 4)
    view.state.form.name = 'New case'
    await view.state.save()
    assert.equal(created.length, 1)
    assert.deepEqual(Object.keys(created[0]).sort(), ['description', 'id', 'module', 'name', 'project_product'])
    assert.equal(created[0].project_product, 22)
    assert.equal(assetReads, 0)
  } finally { view.unmount() }
})

test('outer metadata edits preserve configuration and inner editing never submits metadata', async context => {
  context.mock.timers.enable({ apis: ['setTimeout'] })
  const record = editorFixture(), updates = []
  const outer = await mount('components/CaseEditor.vue', { api: {
    getEvaluationCase: async () => ({ data: record }),
    updateEvaluationCase: async value => { updates.push(value) },
  } })
  try {
    await outer.state.open(record.id)
    outer.state.form.name = 'Renamed'; await flush()
    await outer.state.save()
    assert.equal(updates[0].name, 'Renamed')
    assert.equal('config' in updates[0], false)
    assert.equal('dataset_version' in updates[0], false)
  } finally { outer.unmount() }
  const inner = await mount('components/CaseEditor.vue', editorOptions(record, async value => { updates.push(value) }))
  try {
    inner.state.form.name = 'Must stay outside'; await flush()
    context.mock.timers.tick(1000); await flush()
    assert.equal(inner.state.dirty, false)
    assert.equal(updates.length, 1)
    inner.state.config.execution.retry_count = 1; await flush(); await inner.state.flush()
    assert.deepEqual(Object.keys(updates[1]).sort(), ['config', 'dataset_version', 'id'])
  } finally { inner.unmount() }
})
