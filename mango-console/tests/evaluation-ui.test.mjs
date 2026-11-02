import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import { createRequire } from 'node:module'
import test from 'node:test'

const require = createRequire(import.meta.url)
const Vue = require('vue')
const ts = require('typescript')
const { parse, compileScript, compileTemplate, compileStyleAsync } = require('@vue/compiler-sfc')
const root = new URL('../src/views/evaluation/', import.meta.url)
const read = file => readFileSync(new URL(file, root), 'utf8')
const files = (directory = '') => readdirSync(new URL(directory, root), { withFileTypes: true })
  .flatMap(entry => entry.isDirectory() ? files(`${directory}${entry.name}/`) : [`${directory}${entry.name}`])

test('case step titles and nested execution titles have distinct semantic and typographic levels', () => {
  const steps = readFileSync(new URL('../src/components/forms/MangoStepCards.vue', import.meta.url), 'utf8')
  const results = read('components/ExecutionPanel.vue')
  assert.match(steps, /:is="layout === 'workspace' \? 'h2' : 'h3'"/)
  assert.match(steps, /\.mango-step-layout--workspace \.mango-step-cards__heading h2\s*\{[^}]*font-size: var\(--m-font-subtitle\)/)
  assert.match(results, /\.mango-execution-item-heading\s*\{[^}]*font-size: var\(--m-font-body\)/)
  assert.match(results, /<h4 class="mango-execution-summary-heading">本次结果 AI 总结<\/h4>/)
})

test('case details aligns header and three-column content with one standard outer gap', () => {
  const page = read('case/details/index.vue')
  assert.match(page, /> \.mango-table-body__header\)\s*\{[^}]*padding-inline: var\(--m-page-gap\)/)
  assert.match(page, /> \.mango-table-body__header > \.mango-detail-toolbar\)\s*\{[^}]*padding: var\(--m-card-padding\) 0/)
  assert.match(page, /> \.mango-table-body__content\)\s*\{[^}]*padding: 0 var\(--m-page-gap\) var\(--m-page-gap\)/)
  assert.doesNotMatch(page, /\.mango-evaluation-workspace\s*\{[^}]*padding-top:/)
  assert.match(page, /\.mango-evaluation-workspace\s*\{[^}]*gap: var\(--m-page-gap\)/)
})

test('dataset search retains header padding and compact controls inside the table shell', () => {
  const shell = readFileSync(new URL('../src/components/table/TableBody.vue', import.meta.url), 'utf8')
  assert.match(shell, /:deep\(> \.arco-card-body\)\s*\{/)
  assert.doesNotMatch(shell, /:deep\(\.arco-card-body\)\s*\{/)
  assert.match(read('dataset/index.vue'), /<a-form :model="filters" layout="inline" size="small"/)
  assert.match(read('dataset/index.vue'), /v-model="filters.status"[\s\S]*?multiple/)
})

test('grader explanations distinguish headings, body, rules and constraints without nesting cards', () => {
  const detail = read('grader/GraderDetail.vue')
  assert.match(detail, /\.mango-grader-guide-content\s*\{[^}]*max-width: 960px/)
  assert.match(detail, /h3\s*\{[^}]*font-size: var\(--m-font-subtitle\);[^}]*font-weight: 600/)
  assert.match(detail, /\.mango-grader-guide-note\s*\{[^}]*color: var\(--m-text-2\)/)
  assert.match(detail, /\.mango-grader-guide-scoring\s*\{[^}]*background: var\(--m-surface-soft\)/)
  assert.match(detail, /<strong>判定边界<\/strong>/)
  assert.match(detail, /<strong>通过设置<\/strong>/)
  assert.match(detail, /container-type: inline-size/)
  assert.doesNotMatch(detail, /<a-card|font-family:/)
})

test('case workspace includes an independent read-only metadata inspector with responsive columns', () => {
  const page = read('case/details/index.vue')
  const inspector = read('components/CaseInfoPanel.vue')
  assert.match(page, /<CaseInfoPanel :record="record"/)
  assert.match(page, /grid-template-columns: minmax\(0, 1fr\) 360px/)
  assert.match(page, /@container \(max-width: 800px\)/)
  assert.match(inspector, /aria-label="用例信息"/)
  assert.match(inspector, /mango-case-info__body mango-native-scrollbar/)
  assert.match(inspector, /min-height: 0;\s*overflow: auto/)
  assert.match(inspector, /formatModulePath\(props.record.module_data\)/)
  assert.doesNotMatch(inspector, /@\/api|<a-input|<a-select|<a-switch/)
})

test('dataset pages use standard list chrome, bounded workbench and elastic content columns', () => {
  const list = read('dataset/index.vue')
  const detail = read('dataset/details/index.vue')
  assert.match(list, /<TableBody content-flush>/)
  assert.match(list, /<TableTabs>[\s\S]*#extra[\s\S]*新建数据集/)
  assert.doesNotMatch(list, /#table-config/)
  assert.match(detail, /<BaseSidePanel/)
  assert.match(detail, /mango-native-scroll-table/)
  assert.doesNotMatch(detail, /mango-section-card/)
  assert.match(detail, /\.mango-dataset-workbench\s*\{[^}]*flex: 1;[^}]*min-height: 0;/)
  const code = ts.transpileModule(read('dataset/config.ts'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  }).outputText
  const module = { exports: {} }
  new Function('module', 'exports', code)(module, module.exports)
  assert.equal(module.exports.datasetColumns.find(column => column.key === 'name').width, undefined)
  assert.equal(module.exports.itemColumns.find(column => column.key === 'input_data').width, undefined)
  assert.match(list, /formatEvaluationDate\(record.update_time\)/)
  assert.match(detail, /:title="record.published_at"/)
})

test('dataset date presentation removes ISO microseconds without timezone reinterpretation', () => {
  const code = ts.transpileModule(read('components/presentation.ts'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  }).outputText
  const module = { exports: {} }
  new Function('module', 'exports', code)(module, module.exports)
  const format = module.exports.formatEvaluationDate
  assert.equal(format('2026-10-22T09:10:11.123456+08:00'), '2026-10-22 09:10:11')
  assert.equal(format('2026-10-22 09:10:11'), '2026-10-22 09:10:11')
  assert.equal(format(null), '—')
  assert.equal(format(''), '—')
  assert.equal(format('尚未发布'), '尚未发布')
})

test('all Evaluation Center templates, scripts and token styles compile together', async () => {
  for (const file of files().filter(file => file.endsWith('.vue'))) {
    const { descriptor, errors } = parse(read(file), { filename: file })
    assert.deepEqual(errors, [], file)
    const script = compileScript(descriptor, { id: file })
    const result = compileTemplate({ source: descriptor.template.content, filename: file, id: file,
      compilerOptions: { bindingMetadata: script.bindings, expressionPlugins: ['typescript'] } })
    assert.deepEqual(result.errors, [], file)
    for (const style of descriptor.styles) {
      const compiled = await compileStyleAsync({ source: style.content, filename: file, id: 'data-v-evaluation',
        scoped: style.scoped, preprocessLang: style.lang })
      assert.deepEqual(compiled.errors, [], `${file}: styles`)
    }
  }
})

test('evaluation drawer forwards visibility, close guards and footer without changing behavior', async () => {
  const descriptor = parse(read('components/EvaluationDrawer.vue')).descriptor
  const compiled = compileScript(descriptor, { id: 'evaluation-drawer', inlineTemplate: true })
  const code = ts.transpileModule(compiled.content, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText
  const module = { exports: {} }
  new Function('require', 'module', 'exports', code)(name => {
    assert.equal(name, 'vue')
    return Vue
  }, module, module.exports)
  const renderer = Vue.createRenderer({
    createElement: type => ({ type, children: [] }), createText: text => ({ text }), createComment: text => ({ text }),
    insert(node, parent) { parent.children.push(node) }, remove() {}, parentNode: () => null, nextSibling: () => null,
    setText() {}, setElementText() {}, patchProp(node, key, _old, value) { node[key] = value },
  })
  let attrs, slots
  const Drawer = Vue.defineComponent({ inheritAttrs: false, setup(_, context) {
    attrs = context.attrs; slots = context.slots
    return () => Vue.h('drawer', context.attrs)
  } })
  let visible = true
  const guard = () => false
  const app = renderer.createApp({ render: () => Vue.h(module.exports.default, {
    visible, width: 1000, footer: true, contained: true, closable: false, maskClosable: false,
    escToClose: false, onBeforeCancel: guard, 'onUpdate:visible': value => { visible = value },
  }, { default: () => Vue.h('p', 'content'), footer: () => Vue.h('button', 'save') }) })
  app.component('a-drawer', Drawer)
  app.mount({ children: [] })
  try {
    assert.equal(attrs.width, 1000)
    assert.equal(attrs.footer, true)
    assert.equal(attrs.visible, true)
    assert.equal(attrs.closable, false)
    assert.equal(attrs.maskClosable, false)
    assert.equal(attrs.escToClose, false)
    assert.equal(attrs.onBeforeCancel, guard)
    assert.ok(attrs['body-class'].some(value => value?.['mango-evaluation-side-panel__body--contained']))
    assert.ok(slots.default && slots.footer)
    attrs['onUpdate:visible'](false)
    assert.equal(visible, false)
  } finally { app.unmount() }
})

test('evaluation overlays and editor grids follow global sizing and scroll boundaries', () => {
  for (const file of files().filter(file => file.endsWith('.vue') && !file.endsWith('/EvaluationDrawer.vue'))) {
    assert.doesNotMatch(read(file), /<a-drawer\b/, file)
  }
  assert.match(read('components/ItemSelectionDrawer.vue'), /:width="1000" contained/)
  assert.match(read('components/CaseEditor.vue'), /@container \(max-width: 920px\)/)
  assert.doesNotMatch(read('components/CaseEditor.vue'), /<a-grid\b/)
  assert.match(read('components/EvaluationDrawer.vue'), /padding: var\(--m-page-gap\)/)
  assert.match(read('components/EvaluationDrawer.vue'), /__body--contained[\s\S]*overflow: hidden/)
  assert.doesNotMatch(read('dataset/details/index.vue'), /DatasetImportDialog|jsonImportDialog|导入 JSON/)
  assert.match(read('components/EvaluationItemBrowser.vue'), /:aria-pressed="selectedId === item.id"/)
})

test('every evaluation table action column uses the global width and alignment', () => {
  let count = 0
  for (const file of files().filter(file => /\.(vue|ts)$/.test(file))) {
    for (const [column] of read(file).matchAll(/\{\s*title: '操作'[^}]+\}/g)) {
      count++
      assert.match(column, /width: 160\b/, file)
      assert.match(column, /align: 'center'/, file)
      assert.match(column, /fixed: 'right'/, file)
    }
  }
  assert.ok(count >= 8)
})

test('grader rows stay single-line and the description absorbs spare table width', () => {
  const code = ts.transpileModule(read('grader/config.ts'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  }).outputText
  const module = { exports: {} }
  new Function('module', 'exports', code)(module, module.exports)
  const columns = module.exports.graderColumns
  assert.equal(columns.find(column => column.dataIndex === 'description').width, undefined)
  assert.equal(columns.find(column => column.slotName === 'actions').width, 160)
  assert.ok(columns.some(column => column.dataIndex === 'name'))
  assert.match(read('grader/index.vue'), /:scroll="\{ x: GRADER_SCROLL_X \}"\s+size="small"/)
  assert.doesNotMatch(read('grader/index.vue'), /mango-grader-identity|white-space: normal/)
})

test('grader catalogue preserves multi-select search, pagination and detail permission boundaries', async () => {
  const requests = [], detailCalls = []
  let permitted = true
  const descriptor = parse(read('grader/index.vue')).descriptor
  const script = compileScript(descriptor, { id: 'grader-page' }).content
  const code = ts.transpileModule(script, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true },
  }).outputText
  const module = { exports: {} }
  new Function('require', 'module', 'exports', code)(name => {
    if (name === 'vue') return Vue
    if (name.endsWith('.vue')) return {}
    if (name === './config') return { graderColumns: [], categoryOptions: [] }
    if (name === '@/store/modules/get-enum') return { useEnum: () => ({ colors: ['arcoblue', 'orange', 'purple'] }) }
    if (name === '@/utils/business-format') return { getEnumTagColor: () => 'arcoblue' }
    if (name.endsWith('/presentation')) return { formatVersion: value => `V${value}` }
    if (name === '@/store/modules/permission') return { __esModule: true, default: () => ({ hasPermission: () => permitted }) }
    if (name === '@/api/evaluation') return {
      getGraderCatalog: async query => { requests.push(query); return { data: { items: Array.from({ length: 25 }, (_, index) => ({ grader_key: `rule_${index}`, grader_version: 1 })) } } },
      getGrader: async (key, version) => { detailCalls.push([key, version]); return { data: { name: '规则', grader_key: key } } },
    }
    throw new Error(`Unexpected dependency: ${name}`)
  }, module, module.exports)
  const renderer = Vue.createRenderer({
    createComment: () => ({}), insert() {}, remove() {}, parentNode: () => null, nextSibling: () => null,
  })
  module.exports.default.render = () => null
  const app = renderer.createApp(module.exports.default)
  app.mount({})
  const state = app._instance.setupState
  try {
    await new Promise(resolve => setImmediate(resolve))
    state.filters.search = 'rule'
    state.filters.categories = ['deterministic', 'model']
    await state.load()
    assert.equal(requests.at(-1).category__in, 'deterministic,model')
    assert.equal(requests.at(-1).search, 'rule')
    assert.equal(state.displayedRows.length, 20)
    state.pagination.page = 2
    assert.equal(state.displayedRows.length, 5)
    state.detailError = true
    await state.show({ grader_key: 'rule_1', grader_version: 2 })
    assert.equal(state.detailError, false)
    assert.deepEqual(detailCalls, [['rule_1', 2]])
    permitted = false
    await state.show({ grader_key: 'rule_2', grader_version: 1 })
    assert.equal(detailCalls.length, 1)
  } finally { app.unmount() }
})

test('grader category cells render real Arco tags using the global classification palette', async () => {
  const { renderToString } = require('@vue/server-renderer')
  const Arco = require('@arco-design/web-vue')
  function loadModule(source, resolve) {
    const code = ts.transpileModule(source, { compilerOptions: {
      module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, esModuleInterop: true,
    } }).outputText
    const module = { exports: {} }
    new Function('require', 'module', 'exports', code)(resolve, module, module.exports)
    return module.exports
  }
  const config = loadModule(read('grader/config.ts'), () => { throw new Error('Unexpected config dependency') })
  const formatting = loadModule(readFileSync(new URL('../src/utils/business-format.ts', import.meta.url), 'utf8'), () => { throw new Error('Unexpected formatter dependency') })
  const source = compileScript(parse(read('grader/index.vue')).descriptor, { id: 'grader-tags', inlineTemplate: true }).content
  const categories = ['deterministic', 'algorithm', 'model']
  const component = loadModule(source, name => {
    if (name === 'vue') return { ...Vue, onMounted: Vue.onServerPrefetch }
    if (name.endsWith('.vue')) return { __esModule: true, default: { render: () => null } }
    if (name === './config') return config
    if (name === '@/utils/business-format') return formatting
    if (name === '@/store/modules/get-enum') return { useEnum: () => ({ colors: ['cyan', 'gold', 'pinkpurple'] }) }
    if (name === '@/store/modules/permission') return { __esModule: true, default: () => ({ hasPermission: () => false }) }
    if (name.endsWith('/presentation')) return { formatVersion: value => `V${value}` }
    if (name === '@/api/evaluation') return {
      getGraderCatalog: async () => ({ data: { items: categories.map((category, index) => ({
        name: `评分器 ${index}`, grader_key: `rule_${index}`, category, grader_version: 1, description: '规则说明',
      })) } }),
    }
    throw new Error(`Unexpected rendering dependency: ${name}`)
  }).default
  const app = Vue.createSSRApp(component)
  app.use(Arco.default)
  app.component('TableBody', { setup: (_, { slots }) => () => Vue.h('main', [slots.header?.(), slots.default?.(), slots.footer?.()]) })
  for (const name of ['TableHeader', 'TableFooter', 'MangoTableActions']) app.component(name, { render: () => null })
  const html = await renderToString(app)
  for (const color of ['cyan', 'gold', 'pinkpurple']) assert.match(html, new RegExp(`arco-tag-${color}`))
  for (const title of ['确定性规则', '专业算法', 'LLM 裁判']) assert.ok(html.includes(title))
  assert.match(html, /arco-table-size-small/)
})

test('evaluation classification tags share the global formatter and dense list defaults', () => {
  for (const file of ['grader/index.vue', 'case/index.vue', 'dataset/details/index.vue']) {
    assert.match(read(file), /getEnumTagColor\([^\n]*enumStore.colors\)/, file)
    assert.match(read(file), /size="small"/, file)
  }
  assert.match(read('dataset/index.vue'), /record.task_type.slice\(0, 2\)/)
  assert.match(read('dataset/index.vue'), /record.task_type.join\('、'\)/)
  assert.doesNotMatch(read('dataset/index.vue'), /<a-space v-else-if="column.key === 'task_type'" wrap/)
})

test('case configuration and results share a continuous anchored workbench', async () => {
  const page = read('case/details/index.vue')
  assert.doesNotMatch(read('components/CaseEditor.vue'), /mango-case-editor-toolbar|配置修改后自动保存/)
  assert.ok(page.indexOf('@click="saveConfiguration"') < page.indexOf('@click="historyVisible = true"'))
  assert.match(page, /v-permission="'evaluation.case:change'"/)
  assert.doesNotMatch(page, /<TableTabs|<a-tabs|activeWorkspace/)
  assert.match(page, /<template #results>/)
  assert.doesNotMatch(page, /grid-template-columns:\s*minmax\(560px/)
  assert.match(read('components/CaseEditor.vue'), /label="用例配置步骤" layout="workspace"/)
  const filename = new URL('../src/components/forms/MangoStepCards.vue', import.meta.url)
  const { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'step-layout' })
  const template = compileTemplate({ source: descriptor.template.content, filename: String(filename), id: 'step-layout', compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, [])
  for (const style of descriptor.styles) {
    const result = await compileStyleAsync({ source: style.content, filename: String(filename), id: 'step-layout', scoped: true })
    assert.deepEqual(result.errors, [])
  }
  assert.match(descriptor.styles[0].content, /@container \(max-width: 800px\)/)
  assert.doesNotMatch(descriptor.template.content, /v-show/)
  assert.match(descriptor.template.content, /@scroll.passive="handlePanelScroll"/)
})

test('step anchors scroll inside the panel and follow manual scrolling including the final result section', async () => {
  const filename = new URL('../src/components/forms/MangoStepCards.vue', import.meta.url)
  const descriptor = parse(readFileSync(filename, 'utf8')).descriptor
  const script = compileScript(descriptor, { id: 'step-anchors' }).content
  const code = ts.transpileModule(script, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText
  const module = { exports: {} }
  new Function('require', 'module', 'exports', code)(name => {
    assert.equal(name, 'vue')
    return Vue
  }, module, module.exports)
  const renderer = Vue.createRenderer({ createComment: () => ({}), insert() {}, remove() {}, parentNode: () => null, nextSibling: () => null })
  module.exports.default.render = () => null
  const steps = Vue.reactive(['data', 'target', 'grading', 'results'].map(key => ({ key, title: key })))
  const app = renderer.createApp(module.exports.default, { steps, layout: 'workspace', initialStep: 'results' })
  app.mount({})
  await Vue.nextTick()
  const state = app._instance.setupState, calls = []
  const panel = { scrollTop: 0, clientHeight: 400, scrollHeight: 1700,
    getBoundingClientRect: () => ({ top: 80 }), scrollTo(value) { calls.push(value); this.scrollTop = value.top } }
  state.panelRef = panel
  for (const [key, offset] of [['data', 0], ['target', 300], ['grading', 800], ['results', 1300]])
    state.sectionElements.set(key, { getBoundingClientRect: () => ({ top: 80 + offset - panel.scrollTop }) })
  try {
    assert.equal(state.activeStep, 'results')
    state.scrollToStep('target')
    assert.deepEqual(calls.at(-1), { top: 300, behavior: 'smooth' })
    panel.scrollTop = 850
    state.handlePanelScroll()
    assert.equal(state.activeStep, 'grading')
    panel.scrollTop = 1300
    state.handlePanelScroll()
    assert.equal(state.activeStep, 'results')
    state.scrollToStep('data', 'auto')
    assert.deepEqual(calls.at(-1), { top: 0, behavior: 'auto' })
    state.scrollToStep('missing')
    assert.equal(calls.length, 2)
    state.activeStep = 'target'
    steps.splice(1, 1)
    await Vue.nextTick()
    assert.equal(state.activeStep, 'data')
  } finally { app.unmount() }
})

test('case workbench uses theme surface tiers and flattens only embedded execution cards', () => {
  const steps = readFileSync(new URL('../src/components/forms/MangoStepCards.vue', import.meta.url), 'utf8')
  assert.match(steps, /\.mango-step-layout--workspace\s*\{[^}]*background: var\(--m-bg\)/)
  assert.match(steps, /\.mango-step-navigation\s*\{[^}]*background: var\(--m-surface-soft\)/)
  assert.match(steps, /\.mango-step-layout--workspace \.mango-step-cards__card\s*\{[^}]*border: 0;[^}]*background: var\(--m-surface\)/)
  const execution = read('components/ExecutionPanel.vue')
  assert.match(execution, /\.mango-case-execution-panel--flat > \.mango-execution-card\s*\{[^}]*border: 0;[^}]*background: transparent/)
  const page = read('case/details/index.vue')
  assert.match(page, /<ExecutionPanel\s+flat/)
  assert.doesNotMatch(page, /<ExecutionPanel[^>]*history[^>]*\bflat\b/)
})

test('case form controls have bounded field, expression and grader widths', () => {
  const editor = read('components/CaseEditor.vue')
  assert.equal((editor.match(/class="mango-case-config-form"/g) || []).length, 5)
  assert.match(editor, /repeat\(2, minmax\(0, 440px\)\)/)
  assert.match(editor, /arco-form-item-label-col\)[^}]*120px/)
  assert.match(editor, /arco-input-number\)[^}]*max-width: 160px/)
  assert.match(editor, /mango-case-code-field\)[^}]*max-width: none/)
  assert.match(read('components/ExtractionEditor.vue'), /mango-extraction-editor[^}]*max-width: 880px/)
  assert.match(read('components/GraderEditor.vue'), /<div class="mango-grader-editor__select"><a-select/)
  assert.match(read('components/GraderEditor.vue'), /mango-grader-editor__select[^}]*max-width: 360px/)
})
