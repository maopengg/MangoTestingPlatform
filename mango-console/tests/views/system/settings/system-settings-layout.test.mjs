import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'
import ts from 'typescript'

const filename = new URL('../../../../src/views/system/settings/index.vue', import.meta.url)
const source = fs.readFileSync(filename, 'utf8')
const { descriptor, errors } = parse(source)
const style = descriptor.styles[0].content
const runtimeCenterFilename = new URL(
  '../../../../src/views/system/runtime-center/index.vue',
  import.meta.url
)
const runtimeCenterSource = fs.readFileSync(runtimeCenterFilename, 'utf8')

test('datasource performance fields default to cautious management and inherit the registered level', () => {
  const editor = fs.readFileSync(new URL('../../../../src/views/system/settings/components/DatasourcePerformanceEditor.vue', import.meta.url), 'utf8')
  assert.match(editor, /managementLevel: 2/)
  assert.doesNotMatch(editor, /managementLevel: 3/)
  assert.equal((editor.match(/managementLevel === 2 \? '谨慎修改' : '普通配置'/g) || []).length, 2)
  assert.match(source, /:management-level="item.management_level"/)
})

test('every datasource performance field has an explanation without implying a business API limit', () => {
  const editor = fs.readFileSync(new URL('../../../../src/views/system/settings/components/DatasourcePerformanceEditor.vue', import.meta.url), 'utf8')
  const { descriptor: component, errors } = parse(editor)
  assert.deepEqual(errors, [])
  const script = compileScript(component, { id: 'datasource-performance' })
  assert.deepEqual(compileTemplate({ source: component.template.content, filename: 'DatasourcePerformanceEditor.vue',
    id: 'datasource-performance', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  const ast = ts.createSourceFile('editor.ts', component.scriptSetup.content, ts.ScriptTarget.Latest, true)
  const initializers = new Map(ast.statements.filter(ts.isVariableStatement)
    .flatMap(node => [...node.declarationList.declarations]).filter(node => node.initializer)
    .map(node => [node.name.getText(ast), node.initializer.getText(ast)]))
  const budget = new Function(`return ${initializers.get('budgetFields')}`)()
  for (const name of ['budgetFields', 'sharedFields']) {
    const fields = new Function('budgetFields', `return ${initializers.get(name)}`)(budget)
    for (const field of fields) assert.ok(field.hint?.trim().length >= 10, `${name}.${field.key} needs a useful explanation`)
  }
  assert.match(budget.find(field => field.key === 'concurrency').hint, /不限制Case业务API并发/)
  const shared = new Function(`return ${initializers.get('sharedFields')}`)()
  assert.match(shared.find(field => field.key === 'queue_timeout_seconds').hint, /不是Case最长排队时间/)
  assert.match(shared.find(field => field.key === 'cleanup_completion_seconds').hint, /不含资源排队等待/)
  assert.equal((component.template.content.match(/\{\{ field.hint \}\}/g) || []).length, 2)
  assert.doesNotMatch(component.template.content, /更严格的子配额|实例组合并与覆盖|新增子配额|新增实例组/)
  assert.doesNotMatch(component.scriptSetup.content, /scopeFields|instanceFields|function addScope|function addInstance/)
})

test('saving uniform datasource settings never resubmits retired overrides or subquotas', () => {
  const editor = fs.readFileSync(new URL('../../../../src/views/system/settings/components/DatasourcePerformanceEditor.vue', import.meta.url), 'utf8')
  const script = parse(editor).descriptor.scriptSetup.content
  const ast = ts.createSourceFile('editor.ts', script, ts.ScriptTarget.Latest, true)
  const declarations = ast.statements.filter(ts.isVariableStatement).flatMap(node => [...node.declarationList.declarations])
  const get = name => new Function(`return ${declarations.find(node => node.name.getText(ast) === name).initializer.getText(ast)}`)()
  const raw = { mysql: { concurrency: 4 }, instances: [{ group: 'old', connection_ids: [1] }], scopes: [{ name: 'old' }] }
  const before = structuredClone(raw)
  const events = []
  const code = ts.transpileModule(script.slice(script.indexOf('  const draft =')), {
    compilerOptions: { target: ts.ScriptTarget.ES2022 }
  }).outputText
  const run = new Function('props', 'reactive', 'ref', 'watch', 'baseBudget', 'kinds', 'emit', `${code}; return { draft, save };`)(
    { modelValue: raw, loading: false }, value => value, value => ({ value }), (_, callback) => callback(raw),
    get('baseBudget'), get('kinds'), (...args) => events.push(args)
  )
  run.save()
  const payload = events.find(([name]) => name === 'update:modelValue')[1]
  assert.equal('instances' in payload, false)
  assert.equal('scopes' in payload, false)
  assert.equal(payload.mysql.concurrency, 4)
  assert.deepEqual(raw, before)
})

test('relaxed datasource defaults match backend values and retain explicitly saved limits', () => {
  const editor = fs.readFileSync(new URL('../../../../src/views/system/settings/components/DatasourcePerformanceEditor.vue', import.meta.url), 'utf8')
  const script = parse(editor).descriptor.scriptSetup.content
  const ast = ts.createSourceFile('editor.ts', script, ts.ScriptTarget.Latest, true)
  const declarations = ast.statements.filter(ts.isVariableStatement).flatMap(node => [...node.declarationList.declarations])
  const get = name => new Function(`return ${declarations.find(node => node.name.getText(ast) === name).initializer.getText(ast)}`)()
  const code = ts.transpileModule(script.slice(script.indexOf('  const draft =')), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const initialize = raw => new Function('props', 'reactive', 'ref', 'watch', 'baseBudget', 'kinds', 'emit', `${code}; return draft;`)(
    { modelValue: raw, loading: false }, value => value, value => ({ value }), (_, callback) => callback(raw), get('baseBudget'), get('kinds'), () => {}
  )
  const defaults = initialize({})
  for (const [kind, expected] of Object.entries({ mysql: [6, 30, 12], redis: [12, 75, 16], elasticsearch: [6, 15, 12] })) {
    const value = defaults[kind]
    assert.deepEqual([value.concurrency, value.requests_per_second, value.connections], expected)
    assert.equal(value.cleanup_reserved, 2)
    assert.equal(value.cleanup_rate_percent, 25)
    assert.equal(value.cleanup_backlog_limit, 100)
  }
  assert.equal(defaults.pool_size, 3)
  assert.equal(defaults.max_waiters, 256)
  assert.equal(defaults.cleanup_consumer_threads, 2)
  const saved = initialize({ mysql: { concurrency: 4, requests_per_second: 20, connections: 8, cleanup_reserved: 1 }, pool_size: 2, max_waiters: 100 })
  assert.equal(saved.mysql.concurrency, 4)
  assert.equal(saved.mysql.cleanup_reserved, 1)
  assert.equal(saved.pool_size, 2)
  assert.equal(saved.max_waiters, 100)
  const low = initialize({ mysql: { concurrency: 2, connections: 3 } })
  assert.equal(low.mysql.cleanup_reserved, 1)
  assert.equal(low.pool_size, 2)
})

test('callback enablement uses the existing integer switch and retains numeric payloads', () => {
  const script = descriptor.scriptSetup.content
  const keys = JSON.parse(script.match(/const integerSwitchKeys: string\[\] = (\[[^\]]*\])/)[1].replaceAll("'", '"'))
  assert.ok(keys.includes('MOCK_CALLBACK_ENABLED'))
  const ast = ts.createSourceFile('settings.ts', script, ts.ScriptTarget.Latest, true)
  function evaluate(name, dependencies) {
    const declaration = ast.statements.filter(ts.isVariableStatement)
      .flatMap(node => [...node.declarationList.declarations])
      .find(node => node.name.getText(ast) === name)
    const body = ts.transpileModule(`const value = ${declaration.initializer.getText(ast)}`, {
      compilerOptions: { target: ts.ScriptTarget.ES2022 },
    }).outputText
    return new Function(...Object.keys(dependencies), `${body}; return value`)(...Object.values(dependencies))
  }
  const isEnabledValue = evaluate('isEnabledValue', {})
  const switchValue = evaluate('switchValue', { isEnabledValue })
  const isIntegerSwitchType = evaluate('isIntegerSwitchType', { integerSwitchKeys: keys })
  const normalizePayloadValue = evaluate('normalizePayloadValue', {
    API_DEFAULT_ASSERTION_CHECKS_KEY: 'API_DEFAULT_ASSERTION_CHECKS',
    API_TRANSIENT_RETRY_CONDITIONS_KEY: 'API_TRANSIENT_RETRY_CONDITIONS',
    normalizeRetryConditions: value => value,
    isIntegerSwitchType, switchValue, isEnvironmentDisplayNames: () => false,
    isDataFactoryValidationEnvironments: () => false, isAiTimeout: () => false,
  })
  for (const value of [true, 1, '1', 'true'])
    assert.equal(normalizePayloadValue({ key: 'MOCK_CALLBACK_ENABLED', value }), 1)
  for (const value of [false, 0, '0', 'false', null])
    assert.equal(normalizePayloadValue({ key: 'MOCK_CALLBACK_ENABLED', value }), 0)
  assert.equal(isIntegerSwitchType({ key: 'MOCK_CALLBACK_MAX_ACTIVE' }), false)
  assert.match(source, /if \(item.key === 'MOCK_CALLBACK_ENABLED'\) return '启用 Case 回调验证'/)
  assert.match(source, /:loading="itemSaving\(item\)"/)
  assert.match(source, /restoreSavedValue\(item, previousValue\)/)
})

test('management level buttons filter in the content panel without tab panes', () => {
  const config = fs.readFileSync(
    new URL('../../../../src/views/system/settings/config.ts', import.meta.url),
    'utf8'
  )
  const exports = {}
  new Function(
    'exports',
    ts.transpileModule(config, {
      compilerOptions: { module: ts.ModuleKind.CommonJS },
    }).outputText
  )(exports)
  assert.deepEqual(
    exports.CONFIG_LEVEL_OPTIONS.map((option) => option.key),
    ['all', '3', '2']
  )
  for (const selected of ['all', '3', '2']) {
    for (const level of [1, 2, 3, 4]) {
      assert.equal(
        exports.matchesConfigLevel(selected, level),
        [2, 3].includes(level) && (selected === 'all' || selected === String(level))
      )
    }
  }
  assert.doesNotMatch(source, /searchKeyword|matchesConfigSearch|搜索名称/)
  assert.doesNotMatch(descriptor.template.content, /<a-tabs|<a-tab-pane/)
  assert.match(source, /:aria-pressed="selectedLevel === option.key"/)
  assert.match(source, /@click="selectedLevel = option.key"/)
  assert.match(source, /配置级别：/)
  for (const block of style.matchAll(
    /\.mango-system-settings__level-(?:filter|option)[^{]*\{([^}]+)\}/g
  )) {
    assert.doesNotMatch(block[1], /border-bottom|text-decoration/)
  }
  const template = descriptor.template.content
  assert.ok(template.indexOf('mango-system-settings__level-filter') > template.indexOf('<main'))
  assert.ok(
    template.indexOf('mango-system-settings__level-filter') <
      template.indexOf('v-for="navigationGroup')
  )
  assert.doesNotMatch(source, /普通配置可按实际需要调整|mango-system-settings__level-help/)
  assert.doesNotMatch(source, /watch\(selectedLevel/)
  const filterLogic = source.slice(
    source.indexOf('  const selectedLevel ='),
    source.indexOf('  const normalizeEnvironmentList')
  )
  assert.doesNotMatch(
    filterLogic,
    /doRefresh|settingsLoading|router\.|getSystem|scrollTo|activeNavigationKey/
  )
  const navigationLogic = source.slice(
    source.indexOf('  const navigationGroups ='),
    source.indexOf('  const groupTitle =')
  )
  assert.doesNotMatch(navigationLogic, /selectedLevel|matchesItem|matchesBackend/)
  assert.match(template, /v-show="matchesItem\(group, item\)"/)
  assert.match(
    template,
    /v-if="navigationGroup.includeBackendService"\s+v-show="matchesBackend\(\)"/
  )
})

test('stored numeric configuration strings display as numbers without replacing zero', () => {
  const config = fs.readFileSync(
    new URL('../../../../src/views/system/settings/config.ts', import.meta.url),
    'utf8'
  )
  const compiled = ts.transpileModule(config, {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  }).outputText
  const exports = {}
  new Function('exports', compiled)(exports)
  for (const [value, expected] of [
    ['120', 120],
    ['0', 0],
    [0, 0],
    ['2.5', 2.5],
    [null, undefined],
    ['', undefined],
    ['bad', undefined],
  ]) {
    assert.equal(exports.normalizeConfigNumber(value), expected)
  }
  assert.match(
    source,
    /if \(isNumberType\(item\)\)\s*\{\s*return normalizeConfigNumber\(item.value\)/
  )
})

test('settings script, template and scoped styles compile', () => {
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'settings' })
  assert.deepEqual(
    compileTemplate({
      source: descriptor.template.content,
      filename: filename.pathname,
      id: 'settings',
      compilerOptions: { bindingMetadata: script.bindings },
    }).errors,
    []
  )
  assert.deepEqual(
    compileStyle({ source: style, filename: filename.pathname, id: 'settings', scoped: true })
      .errors,
    []
  )
})

test('settings remain a continuous list with standard form controls', () => {
  const section = style.match(/\.mango-system-settings__section-grid\s*\{([^}]+)\}/)[1]
  assert.match(section, /flex-direction: column/)
  const subgroup = style.match(/\.mango-system-settings__small-section\s*\{([^}]+)\}/)[1]
  assert.doesNotMatch(subgroup, /border-radius|box-shadow/)
  for (const control of descriptor.template.content.matchAll(
    /<a-(?:switch|input|input-number|input-password|select|textarea)\b[^>]*>/g
  )) {
    assert.match(control[0], /size="medium"/)
  }
  assert.equal(source.split('修改后自动保存').length - 1, 1)
  assert.match(style, /grid-template-columns: 200px 90px minmax\(240px, 420px\) minmax\(0, 1fr\)/)
  assert.match(style, /min-height: calc\(var\(--m-control-height-medium\)/)
})

test('three-column settings show optional guidance and only one test entry per group', () => {
  assert.match(source, /itemHelp\(item\)[\s\S]*isTestAnchor\(group, item\)/)
  assert.match(style, /container-type: inline-size/)
  assert.match(style, /@container \(max-width: 1000px\)/)
  assert.match(style, /@container \(max-width: 540px\)/)
  const code = source.slice(
    source.indexOf('  const isTestAnchor ='),
    source.indexOf('  const itemHelp =')
  )
  const js = ts.transpileModule(code, {
    compilerOptions: { target: ts.ScriptTarget.ES2020 },
  }).outputText
  const anchor = new Function('isAiGroup', 'AI_VISION_GROUP_KEY', `${js}; return isTestAnchor;`)(
    (group) => group.key === 'ai',
    'ai_vision'
  )
  for (const [key, keys, expected] of [
    ['email', ['SYSTEM_SEND_USER', 'SYSTEM_EMAIL_HOST', 'SYSTEM_STAMP_KET'], 'SYSTEM_SEND_USER'],
    ['ai', ['AI_API_KEY', 'AI_MODEL', 'AI_TIMEOUT'], 'AI_MODEL'],
    ['ai', ['AI_API_KEY', 'AI_TIMEOUT'], 'AI_API_KEY'],
  ]) {
    const group = { key, items: keys.map((key) => ({ key })) }
    assert.deepEqual(
      group.items.filter((item) => anchor(group, item)).map((item) => item.key),
      [expected]
    )
  }
  const item = { key: 'API_TIMEOUT' }
  assert.equal(anchor({ key: 'api', items: [item] }, item), false)
})

test('compact headings avoid duplicate sections and test inputs stay bounded', () => {
  assert.match(
    source,
    /v-if="\s*navigationGroup.includeBackendService \|\| navigationGroup.groups.length > 1\s*"/
  )
  assert.doesNotMatch(source, /groupDescription\(group\)/)
  const testControls = style.match(/\.mango-system-settings__email-test-controls\s*\{([^}]+)\}/)[1]
  assert.match(testControls, /max-width: 420px/)
  const heading = style.match(/\.mango-system-settings__heading-copy\s*\{([^}]+)\}/)[1]
  assert.match(heading, /flex-wrap: wrap/)
})

test('initial entry keeps filters visible and only explicit valid groups scroll into view', async () => {
  const code = source.slice(
    source.indexOf('  async function doRefresh()'),
    source.indexOf('  const debugLogSaving =')
  )
  const js = ts.transpileModule(code, {
    compilerOptions: { target: ts.ScriptTarget.ES2020 },
  }).outputText
  for (const requested of [undefined, '', 'unknown', 'email', 'system-services']) {
    const calls = []
    const configElement = { name: 'email' }
    const sectionElement = { name: 'system-services' }
    const loading = { value: false }
    const refresh = new Function(
      'settingsLoading',
      'route',
      'getSystemCacheDataGrouped',
      'settingsGroups',
      'normalizeEditValue',
      'rememberSavedValues',
      'findNavigationGroup',
      'activeNavigationKey',
      'navigationGroups',
      'SYSTEM_SERVICES_GROUP_KEY',
      'nextTick',
      'configSectionElements',
      'sectionElements',
      'scrollElementIntoPanel',
      'panelRef',
      `${js}; return doRefresh;`
    )(
      loading,
      { query: { group: requested } },
      async () => ({ data: [] }),
      { value: [] },
      () => {},
      () => {},
      () => undefined,
      { value: '' },
      { value: [{ key: 'system-services' }] },
      'system-services',
      async () => {},
      new Map([['email', configElement]]),
      new Map([['system-services', sectionElement]]),
      (...args) => calls.push(args),
      { value: { scrollTo: (options) => calls.push(options) } }
    )
    await refresh()
    assert.equal(loading.value, false)
    assert.deepEqual(
      calls,
      requested === 'email'
        ? [[configElement, 'auto']]
        : requested === 'system-services'
        ? [[sectionElement, 'auto']]
        : [{ top: 0, behavior: 'auto' }]
    )
  }
})

test('directory scrolls locally without routing, remounting or refetching', () => {
  const code = source.slice(
    source.indexOf('  const scrollToGroup ='),
    source.indexOf('  const handlePanelScroll =')
  )
  const js = ts.transpileModule(code, {
    compilerOptions: { target: ts.ScriptTarget.ES2020 },
  }).outputText
  for (const reduced of [false, true]) {
    const active = { value: 'system-services' }
    const element = {}
    const calls = []
    const navigate = new Function(
      'activeNavigationKey',
      'sectionElements',
      'scrollElementIntoPanel',
      'window',
      `${js}; return scrollToGroup;`
    )(active, new Map([['ai-capabilities', element]]), (...args) => calls.push(args), {
      matchMedia: () => ({ matches: reduced }),
    })
    navigate('ai-capabilities')
    assert.equal(active.value, 'ai-capabilities')
    assert.deepEqual(calls, [[element, reduced ? 'auto' : 'smooth']])
  }
  assert.equal((source.match(/await doRefresh\(\)/g) || []).length, 1)
})

test('primary and secondary groups have distinct visual and semantic levels', () => {
  assert.match(descriptor.template.content, /<h2 class="mango-system-settings__large-title"/)
  assert.match(descriptor.template.content, /<h3 class="mango-system-settings__card-title"/)
  const header = style.match(/\.mango-system-settings__large-header\s*\{([^}]+)\}/)[1]
  assert.match(header, /background-color: var\(--m-surface-soft\)/)
  assert.match(header, /border-inline-start: 3px solid var\(--m-primary\)/)
  const children = style.match(/\.mango-system-settings__section-grid\s*\{([^}]+)\}/)[1]
  assert.match(children, /padding-inline-start: var\(--m-space-lg\)/)
})

test('automation types have separate top-level directory entries', () => {
  const definition = source.slice(
    source.indexOf('  const navigationDefinitions ='),
    source.indexOf('  const settingsGroups =')
  )
  const definitions = new Function(
    'SYSTEM_SERVICES_GROUP_KEY',
    'DATA_CAPABILITIES_GROUP_KEY',
    'AI_CAPABILITIES_GROUP_KEY',
    'AI_VISION_GROUP_KEY',
    `${definition}; return navigationDefinitions;`
  )('system-services', 'data-capabilities', 'ai-capabilities', 'ai_vision')
  for (const key of ['api', 'ui', 'pytest', 'execution', 'runtime-capacity']) {
    const entry = definitions.find((item) => item.key === key)
    assert.ok(entry, `${key} must have a top-level entry`)
    assert.deepEqual(entry.groupKeys, key === 'api' ? ['api', 'mock'] : [key === 'runtime-capacity' ? 'runtime' : key])
  }
  assert.equal(definitions.some((item) => item.key === 'mock'), false)
  assert.equal(
    definitions.some((item) => item.title === '自动化配置'),
    false
  )
  assert.deepEqual(definitions.find((item) => item.key === 'system-services').groupKeys, ['system', 'email'])
  assert.deepEqual(definitions.find((item) => item.key === 'report-delivery').groupKeys, ['report_delivery'])
})

test('runtime configuration is managed by settings instead of runtime center', () => {
  assert.match(source, /title: '运行与容量'[\s\S]*groupKeys: \['runtime'\]/)
  assert.doesNotMatch(source, /hiddenGroupKeys = \[[^\]]*'runtime'/)
  assert.doesNotMatch(runtimeCenterSource, /<h2>运行配置<\/h2>/)
  assert.doesNotMatch(runtimeCenterSource, /saveRuntimeConfig|getSystemCacheDataGrouped/)

  const runtimeCenter = parse(runtimeCenterSource)
  assert.deepEqual(runtimeCenter.errors, [])
  const runtimeScript = compileScript(runtimeCenter.descriptor, { id: 'runtime-center' })
  assert.deepEqual(
    compileTemplate({
      source: runtimeCenter.descriptor.template.content,
      filename: runtimeCenterFilename.pathname,
      id: 'runtime-center',
      compilerOptions: { bindingMetadata: runtimeScript.bindings },
    }).errors,
    []
  )
})

test('configuration management levels are visible and cautious changes require confirmation', () => {
  assert.match(source, /const MANAGEMENT_LEVEL_STANDARD = 3/)
  assert.match(
    source,
    /<a-tag\s+v-else-if="item.management_level === MANAGEMENT_LEVEL_STANDARD"\s+size="small"\s*>\s*普通配置\s*<\/a-tag>/
  )
  assert.match(source, /management_level: number/)
  assert.match(source, /item\.management_level === MANAGEMENT_LEVEL_CAUTION/)
  assert.match(descriptor.template.content, /谨慎修改/)
  assert.match(source, /Modal\.warning\(\{/)
  assert.match(source, /确认修改谨慎配置/)
  assert.match(style, /\.mango-system-settings__help--caution\s*\{[^}]*var\(--m-warning\)/s)
})
