import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse } from '@vue/compiler-sfc'
import * as Vue from 'vue'
import Arco from '@arco-design/web-vue'
import { renderToString } from '@vue/server-renderer'

const root = new URL('../', import.meta.url)
const read = (path) => fs.readFileSync(new URL(path, root), 'utf8')
const source = read('src/components/business/CasePublicationReviewModal.vue')
const { descriptor } = parse(source)
const configurationTags = parse(read('src/components/display/CaseExecutionConfigurationTags.vue')).descriptor
const CaseExecutionConfigurationTags = Vue.defineComponent({
  props: ['sqlCount', 'factoryCount'],
  render: Vue.compile(configurationTags.template.content),
})

test('shared execution configuration renders named tags and consistent empty states', async () => {
  for (const [sqlCount, factoryCount, expected, absent] of [
    [90, 0, ['SQL 90'], ['数据工厂', '无']],
    [1, 7, ['SQL 1', '数据工厂 7'], ['无']],
    [0, 1, ['数据工厂 1'], ['SQL']],
    [0, 0, ['无'], ['SQL', '数据工厂']],
    [undefined, undefined, ['—'], ['无', 'SQL', '数据工厂']],
  ]) {
    const app = Vue.createSSRApp({ render: () => Vue.h(CaseExecutionConfigurationTags, { sqlCount, factoryCount }) })
    for (const name of ['Space', 'Tag']) app.component('A' + name, Arco[name])
    const html = await renderToString(app)
    for (const text of expected) assert.ok(html.includes(text), `Missing ${text}`)
    for (const text of absent) assert.ok(!html.includes(text), `Unexpected ${text}`)
  }
})
const file = ts.createSourceFile('review.ts', descriptor.scriptSetup.content, ts.ScriptTarget.Latest, true)
const functions = file.statements.filter(ts.isFunctionDeclaration)
  .map((node) => ts.transpileModule(node.getText(file), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText).join('\n')
const rulesScript = ts.transpileModule(read('src/utils/case-publication-review.ts').replaceAll('export function', 'function'), {
  compilerOptions: { target: ts.ScriptTarget.ES2022 },
}).outputText
const reviewRequirements = new Function(rulesScript + '; return reviewRequirements')()
const requiresCaseReview = new Function(rulesScript + '; return requiresCaseReview')()
const reviewRequirementParts = new Function(rulesScript + '; return reviewRequirementParts')()

function setup() {
  const calls = [], emitted = []
  const state = {
    loading: { value: false }, publishing: { value: false }, acknowledged: { value: false },
    canPublish: { value: true }, domain: { value: 'api' }, ids: { value: [1, 2, 3] },
    visible: { value: true }, rows: { value: [{ id: 1, reviewConfirmed: true }, { id: 2, reviewConfirmed: true }, { id: 3, reviewConfirmed: true }] },
    configurationDrawerRef: { value: { openSnapshot: (...args) => calls.push(args) } },
    displayRows: { value: [{ id: 1 }, { id: 2, disabled: true }, { id: 3 }] },
    selectedIds: { value: [] }, permissions: { hasPermission: () => true },
    detailVisible: { value: false }, detailCaseId: { value: null },
    requiresCaseReview,
    approveApiCasePrepublication: async (id) => calls.push(id),
    putUiCasePublication: async (id) => calls.push(id), putPytestCasePublication: async (id) => calls.push(id),
    Message: { success: () => {} }, emit: (...args) => emitted.push(args),
    get: async ({ data }) => ({ data: { id: data().case_id, publication_status: 'prepublished', eligibility_reasons: [] } }),
  }
  const names = Object.keys(state)
  const create = () => new Function(...names, `let requestVersion = 0; ${functions}; return { open, selectRows, publishSelected, reload, close, onReviewVisibilityChange, openCaseDetail, openConfiguration, setRowReview }`)(...names.map((key) => state[key]))
  return { state, calls, emitted, create }
}

test('review selection excludes blocked rows and clears acknowledgment', () => {
  const { state, create } = setup()
  state.acknowledged.value = true
  create().selectRows([1, 2])
  assert.deepEqual(state.selectedIds.value, [1])
  assert.equal(state.acknowledged.value, false)
})

test('single and batch publication only publish checked eligible rows', async () => {
  for (const domain of ['api', 'ui', 'pytest']) {
    const { state, calls, emitted, create } = setup()
    state.domain.value = domain
    state.selectedIds.value = [1, 2]
    state.acknowledged.value = true
    await create().publishSelected()
    assert.deepEqual(calls, [1])
    assert.deepEqual(emitted, [['published', [1]]])
    assert.equal(state.rows.value[2].published, undefined)
  }
})

test('no acknowledgment, loading and duplicate submission never publish', async () => {
  for (const [field, value] of [['acknowledged', false], ['loading', true], ['publishing', true]]) {
    const { state, calls, create } = setup()
    state.selectedIds.value = [1]
    state.acknowledged.value = true
    state[field].value = value
    await create().publishSelected()
    assert.deepEqual(calls, [])
  }
})

test('partial failure preserves unselected rows and reports only successful IDs', async () => {
  const { state, calls, emitted, create } = setup()
  state.displayRows.value[1].disabled = false
  state.selectedIds.value = [1, 2]
  state.acknowledged.value = true
  state.approveApiCasePrepublication = async (id) => { if (id === 2) throw new Error('changed'); calls.push(id) }
  await create().publishSelected()
  assert.deepEqual(calls, [1])
  assert.deepEqual(emitted, [['published', [1]]])
  assert.match(state.rows.value[1].error, /发布失败/)
  assert.equal(state.rows.value[2].error, undefined)
  assert.equal(state.visible.value, true)
})

test('loading summaries never preselects rows, and failures fail closed', async () => {
  const { state, create } = setup()
  state.selectedIds.value = [1]
  state.acknowledged.value = true
  state.get = async ({ data }) => { if (data().case_id === 2) throw new Error('failed'); return { data: { id: data().case_id, eligibility_reasons: [] } } }
  await create().reload()
  assert.deepEqual(state.selectedIds.value, [])
  assert.equal(state.acknowledged.value, false)
  assert.match(state.rows.value[1].error, /不能发布/)
  assert.equal(state.loading.value, false)
})

test('large review scrolls all cases without pagination and preserves selection', () => {
  assert.match(source, /<BaseSidePanel/)
  assert.match(source, /:width="1440"/)
  assert.match(source, /:data="displayRows"/)
  assert.match(source, /:pagination="false"/)
  assert.match(source, /y: '100%'/)
  assert.match(source, /__table \{ flex: 1; min-height: 0;/)
  assert.doesNotMatch(source, /62vh/)
  assert.match(source, /<TableHeader/)
  assert.doesNotMatch(source, /TableFooter|pagedRows|currentPage|changePage/)
  assert.doesNotMatch(source, /刷新内容|@click="reload"/)
  assert.match(source, /<MangoTableActions/)
  assert.match(source, /<ExecutionSceneTagGrid :values="record.scenario_tags"/)
  assert.match(source, /<a-tag :color="enumStore.status_colors\?\.\[record.status\]" size="small"/)
  assert.match(source, /onlyCurrent: false/)
  const { state, create } = setup()
  const rows = Array.from({ length: 125 }, (_, index) => ({ id: index + 1 }))
  state.rows.value = rows
  state.displayRows.value = rows
  const actions = create()
  actions.selectRows([1, 20])
  assert.deepEqual(state.selectedIds.value, [1, 20])
  actions.selectRows([1, 20, 101, 120])
  assert.deepEqual(state.selectedIds.value, [1, 20, 101, 120])
})

test('publication review fits all fields inside the drawer without a forced wide canvas', () => {
  assert.match(source, /:scroll="\{ x: '100%', y: '100%' \}"/)
  assert.doesNotMatch(source, /x: 1280/)
  const columnsNode = file.statements.filter(ts.isVariableStatement)
    .flatMap(node => [...node.declarationList.declarations])
    .find(node => node.name.getText(file) === 'reviewColumns')
  const code = ts.transpileModule(`const reviewColumns = ${columnsNode.initializer.getText(file)}`, {
    compilerOptions: { target: ts.ScriptTarget.ES2022 },
  }).outputText
  const columns = new Function(code + ';return reviewColumns')()
  assert.deepEqual(columns.filter(column => !column.width).map(column => column.title), ['用例'])
  assert.ok(columns.every(column => column.width == null || typeof column.width === 'number'))
  assert.deepEqual(columns.slice(1).map(column => column.width), [72, 88, 156, 156, 260, 88, 160])
  assert.equal(columns.find(column => column.title === '负责人').align, 'center')
  assert.equal(columns.at(-1).width, 160)
  assert.match(source, /\.mango-publication-review__muted\s*\{[^}]*white-space: normal/)
})

test('Arco table shows human review requirements without expanding configuration content', () => {
  assert.match(source, /:columns="reviewColumns"/)
  assert.match(source, /\{ title: '审核要求', slotName: 'requirements', width: 260 \}/)
  assert.doesNotMatch(source, /<a-table-column/)
  assert.match(source, /reviewRequirements\(record.scenario_tags\)/)
  assert.doesNotMatch(source, /expand-row|record.configuration_items|record.step_details/)
  assert.doesNotMatch(source, /blocking_reasons|未发现静态规则|需人工核查，展开查看说明/)
})

test('actual Arco renderer shows case, owner and review requirements for 125 cases', async () => {
  const columnsNode = file.statements.filter(ts.isVariableStatement)
    .flatMap((node) => [...node.declarationList.declarations])
    .find((node) => node.name.getText(file) === 'reviewColumns')
  const columnsScript = ts.transpileModule(`const reviewColumns = ${columnsNode.initializer.getText(file)}`, {
    compilerOptions: { target: ts.ScriptTarget.ES2022 },
  }).outputText
  const reviewColumns = new Function(columnsScript + ';return reviewColumns')()
  const row = { id: 29, name: 'Example Case', owner: 'Case owner', product: 'Example Product', module: 'Module',
    status: 1, scenario_tags: ['production_regression'], description: 'Create and query item', eligibility_reasons: [],
    sql_count: 1, factory_count: 7,
    configuration_items: [{ label: '前置 SQL', content: 'select id from example_table' }],
    step_details: [{ title: 'POST /products', lines: ['Scenario: create succeeds'] }] }
  const reviewRows = [row, ...Array.from({ length: 124 }, (_, index) => ({ ...row, id: index + 100, name: `Pagination Case ${index + 100}` }))]
  const context = { visible: true, domain: 'api', rows: reviewRows, displayRows: reviewRows,
    reviewColumns, reviewRequirements, reviewRequirementParts,
    detailVisible: false, detailCaseId: null, canViewDetails: true, detailComponents: {}, allSelectedReviewed: false,
    loading: false, publishing: false, selectedIds: [], permissionKey: 'api.case:change',
    canPublish: true, acknowledged: false, enumStore: { task_status: [], api_case_scenario_tag: [], environment_type: [] },
    enumTitle: (_, value) => String(value), close() {}, onReviewVisibilityChange() {}, selectRows() {}, reload() {}, openCaseDetail() {}, publishSelected() {} }
  const app = Vue.createSSRApp({ setup: () => context, render: Vue.compile(descriptor.template.content) })
  for (const name of ['Table', 'Button', 'Switch', 'Checkbox', 'Space', 'Tag']) app.component('A' + name, Arco[name])
  app.component('ExecutionSceneTagGrid', { render: () => Vue.h('span') })
  app.component('CaseExecutionConfigurationTags', CaseExecutionConfigurationTags)
  app.component('CaseExecutionConfigurationTitle', { render: () => Vue.h('span', '执行配置') })
  app.component('ApiCaseConfigurationDrawer', { render: () => null })
  app.component('MangoTableActions', { render: () => Vue.h('button', '查看详情') })
  app.component('TableHeader', { setup(_, { slots }) { return () => Vue.h('header', slots['header-extra']?.()) } })
  app.component('BaseSidePanel', { setup(_, { slots }) { return () => Vue.h('section', [slots.default?.(), slots['footer-buttons']?.()]) } })
  app.directive('permission', { getSSRProps: () => ({}) })
  const html = await renderToString(app)
  for (const text of ['Example Case', 'Case owner', '执行配置', 'SQL 1', '数据工厂 7', '无 SQL、数据工厂', '失败也清理', '查看详情']) {
    assert.ok(html.includes(text), `Missing rendered review content: ${text}`)
  }
  assert.ok(html.includes('Pagination Case 118'))
  assert.ok(html.includes('Pagination Case 223'), 'The last of 125 cases should be available without pagination')
})

test('review configuration opens the drawer without local role filtering', () => {
  const { state, calls, create } = setup()
  const row = { id: 29, name: 'Example', sql_count: 1, factory_count: 7,
    configuration_details: [{ kind: 'sql', location: '用例 / 前置 SQL', enabled: null, configuration: { sql: 'select 1' } }] }
  create().openConfiguration(row)
  assert.equal(calls.length, 1)
  assert.equal(calls[0][1], undefined)
  assert.deepEqual(calls[0][0].items, row.configuration_details)
  state.permissions.hasPermission = () => false
  create().openConfiguration(row)
  assert.equal(calls.length, 2)
  state.permissions.hasPermission = () => true
  create().openConfiguration({ ...row, configuration_details: undefined })
  assert.equal(calls.length, 2)
})

test('scene-based requirements are deduplicated and remain reminders, not automatic verdicts', () => {
  assert.equal(reviewRequirements(undefined).length, 1)
  assert.equal(reviewRequirements(['production_inspection', 'production_inspection']).length, 2)
  assert.ok(reviewRequirements(['production_inspection']).some((text) => text.includes('只读')))
  assert.ok(reviewRequirements(['production_regression']).some((text) => text.includes('失败也清理')))
  const both = reviewRequirements(['production_inspection', 'production_regression'])
  assert.equal(both.length, 4)
  assert.ok(both.some((text) => text.includes('标签是否准确')))
  assert.equal(both.filter((text) => text.includes('SQL')).length, 1)
})

test('requirement emphasis highlights only key phrases and preserves the complete text', () => {
  for (const text of [...reviewRequirements(['production_regression']), ...reviewRequirements(['production_inspection']), ...reviewRequirements([])]) {
    const parts = reviewRequirementParts(text)
    assert.equal(parts.map((part) => part.text).join(''), text)
    assert.ok(parts.some((part) => part.emphasis))
  }
  assert.deepEqual(reviewRequirementParts('确认无 SQL、数据工厂配置。').filter((part) => part.emphasis).map((part) => part.text), ['无 SQL、数据工厂'])
  assert.doesNotMatch(source, /v-html/)
  assert.match(source, /__emphasis \{ color: var\(--m-danger\)/)
})

test('details reuse embedded case pages without local role filtering', () => {
  for (const domain of ['api', 'ui', 'pytest']) {
    const { state, calls, create } = setup()
    state.domain.value = domain
    create().openCaseDetail(29)
    assert.equal(state.detailVisible.value, true)
    assert.equal(state.detailCaseId.value, 29)
    assert.deepEqual(calls, [])
    state.selectedIds.value = [29]
    assert.equal(state.acknowledged.value, false)
    state.permissions.hasPermission = () => false
    create().openCaseDetail(30)
    assert.equal(state.detailCaseId.value, 30)
    assert.deepEqual(state.selectedIds.value, [29])
  }
  assert.doesNotMatch(source, /hasPermission|v-permission|permission:/)
  assert.doesNotMatch(source, /window.open|router.resolve/)
  assert.match(source, /mode="page"/)
  assert.match(source, /:visible="detailVisible" title="用例详情" width="calc\(92vw - 150px\)"/)
  assert.match(source, /embedded :case-id="detailCaseId"/)
  assert.match(read('src/views/pytest/case/index.vue'), /props.caseId \|\| route.query.id/)
  assert.match(read('src/views/pytest/case/index.vue'), /existingCaseId \|\| linkedCaseId.value/)
  assert.match(read('src/views/apitest/case/details/components/ApiCaseVersionPanel.vue'), /if \(prepublishedRevision.value\) await selectRevision\(prepublishedRevision.value\)/)
})

test('every single approval entry and API batch approval opens the same review component', () => {
  for (const domain of ['apitest', 'uitest', 'pytest']) {
    const page = read(`src/views/${domain}/case/index.vue`)
    assert.match(page, /<CasePublicationReviewModal/)
    assert.match(page, /publicationReviewRef.value\?\.open/)
  }
  assert.match(read('src/views/apitest/case/index.vue'), /open\('api', selectedRows.map/)
  assert.match(read('src/views/apitest/case/index.vue'), /@click="batchUpdatePrepublication\('publish'\)"/)
  assert.match(read('src/views/apitest/case/details/components/ApiCaseVersionPanel.vue'), /publicationReviewRef.value\?\.open/)
  assert.doesNotMatch(source, /v-permission/)
  assert.match(source, /v-model="acknowledged"/)
  assert.match(source, /<a-switch :model-value="record.reviewConfirmed === true"/)
  assert.doesNotMatch(source, /<a-switch[^>]*size=/)
  assert.match(source, /<a-checkbox v-model="acknowledged"/)
})

test('production cases start unreviewed, other cases start confirmed, and each selected case must be confirmed', async () => {
  const { state, calls, create } = setup()
  state.get = async ({ data }) => ({ data: { id: data().case_id, publication_status: 'prepublished', eligibility_reasons: [],
    scenario_tags: data().case_id === 1 ? ['production_inspection'] : data().case_id === 2 ? ['production_regression'] : ['routine_regression'] } })
  const actions = create()
  await actions.reload()
  assert.deepEqual(state.rows.value.map((row) => row.reviewConfirmed), [false, false, true])
  state.displayRows.value = state.rows.value
  state.selectedIds.value = [1, 3]
  state.acknowledged.value = true
  await actions.publishSelected()
  assert.deepEqual(calls, [])
  actions.setRowReview(1, true)
  assert.equal(state.acknowledged.value, false)
  assert.equal(state.rows.value[1].reviewConfirmed, false)
  assert.equal(state.rows.value[0].reviewConfirmed, true)
  state.acknowledged.value = true
  await actions.publishSelected()
  assert.deepEqual(calls, [1, 3])
  await actions.reload()
  assert.equal(state.rows.value[0].reviewConfirmed, false)
})

test('review and embedded case tables use the global action column width', () => {
  assert.match(source, /title: '操作', slotName: 'actions', width: 160/)
  assert.match(read('src/views/apitest/case/details/config.ts'), /title: '操作',[\s\S]*?width: 160/)
  assert.match(read('src/views/apitest/case/details/components/ApiCaseAssertionPanel.vue'), /title="操作" :width="160"/)
  assert.match(read('src/views/pytest/case/config.ts'), /title: '操作',[\s\S]*?width: 160/)
})

test('drawer close state is synchronized and review can reopen repeatedly for every domain', async () => {
  assert.match(source, /@update:visible="onReviewVisibilityChange"/)
  for (const domain of ['api', 'ui', 'pytest']) {
    const { state, create } = setup()
    const actions = create()
    for (let attempt = 0; attempt < 3; attempt++) {
      await actions.open(domain, [1, 3])
      assert.equal(state.visible.value, true)
      state.selectedIds.value = [1]
      state.acknowledged.value = true
      state.detailVisible.value = true
      actions.onReviewVisibilityChange(false)
      assert.equal(state.visible.value, false)
      assert.equal(state.detailVisible.value, false)
      assert.deepEqual(state.selectedIds.value, [])
      assert.equal(state.acknowledged.value, false)
    }
  }
})

test('API batch review rejects mixed states before passing IDs into the drawer', () => {
  const page = parse(read('src/views/apitest/case/index.vue')).descriptor.scriptSetup.content
  const ast = ts.createSourceFile('case.ts', page, ts.ScriptTarget.Latest, true)
  const code = ast.statements.filter((node) => ts.isFunctionDeclaration(node) &&
    ['batchUpdatePrepublication', 'canApproveCasePrepublication'].includes(node.name.text))
    .map((node) => ts.transpileModule(node.getText(ast), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText).join('\n')
  for (const status of ['published', 'unpublished', 'draft_changed', null]) {
    const opened = [], warnings = []
    const dataList = [{ id: 29, name: 'Valid', publication_status: 'prepublished', prepublished_revision_id: 7, is_product_owner: true },
      { id: 30, name: 'Invalid', publication_status: status, prepublished_revision_id: 8, is_product_owner: true }]
    const invoke = new Function('publicationActionCaseId', 'batchPublicationAction', 'selectedRowKeys', 'table', 'Message', 'publicationReviewRef',
      code + ';return batchUpdatePrepublication')({ value: null }, { value: null }, { value: [29, 30] }, { dataList },
      { warning: (message) => warnings.push(message) }, { value: { open: (...args) => opened.push(args) } })
    invoke('publish')
    assert.deepEqual(opened, [])
    assert.match(warnings[0], /#30 Invalid/)
    dataList[1].publication_status = 'prepublished'
    invoke('publish')
    assert.deepEqual(opened, [['api', [29, 30]]])
  }
})

test('fresh review responses reject cases whose publication status changed', async () => {
  const { state, create } = setup()
  state.get = async ({ data }) => ({ data: { id: data().case_id, publication_status: 'published', eligibility_reasons: [] } })
  await create().reload()
  assert.ok(state.rows.value.every((row) => row.eligibility_reasons.includes('当前不是预发布状态，不能发布')))
})

test('API case publication labels never combine published and prepublished states', () => {
  const code = ts.transpileModule(read('src/utils/api-case-version.ts'), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
  }).outputText
  const exports = {}
  new Function('exports', code)(exports)
  assert.equal(exports.getApiCasePublicationMeta('prepublished', 'V3', true, 4).label, '预发布 r4')
  assert.equal(exports.getApiCasePublicationMeta('published', 'V3', true).label, '已发布 V3')
  assert.equal(exports.getApiCasePublicationMeta('unpublished', null, false).label, '未发布')
  assert.doesNotMatch(read('src/types/api-test/case-version.ts'), /draft_changed/)
})
