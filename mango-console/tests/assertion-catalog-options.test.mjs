import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import { parse } from '@vue/compiler-sfc'
import { loadModule } from './helpers/auth-config-harness.mjs'

const catalog = loadModule('src/utils/assertion-catalog.ts')
const group = (value) => ({ value, label: value, children: [{ value: value + '-methods', children: [] }] })
const visual = group('文件视觉识别')
const future = group('Future checks')

function loadFunction(filename, name, bindings) {
  const source = parse(readFileSync(filename, 'utf8')).descriptor.scriptSetup.content
  const ast = ts.createSourceFile(filename + '.ts', source, ts.ScriptTarget.Latest, true)
  const declaration = ast.statements.find(node => ts.isFunctionDeclaration(node) && node.name?.text === name)
  assert.ok(declaration, name)
  const code = ts.transpileModule(declaration.getText(ast), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
  }).outputText
  return new Function(...Object.keys(bindings), code + `;return ${name}`)(...Object.values(bindings))
}

test('UI catalog uses dedicated assertions and does not depend on labels', () => {
  const merged = catalog.mergeUiMethodCatalog(
    [group('web'), group('android'), group('ios'), group('ass_web'), group('文件断言'), group('unrelated-operation')],
    [visual, future]
  )
  assert.deepEqual(merged.map(item => item.value), ['web', 'android', 'ios', 'ass_web', '文件视觉识别', 'Future checks'])
})

test('UI store exposes visual and future assertions on Web, Android and iOS', async () => {
  const calls = []
  const useStore = loadModule('src/store/modules/get-ope-value.ts', {
    pinia: { defineStore: (_name, options) => () => {
      const state = options.state()
      for (const [key, value] of Object.entries(options.actions)) state[key] = value.bind(state)
      return state
    } },
    '@/utils/assertion-catalog': catalog,
    '@/api/system/cache_data': { getSystemCacheDataKeyValue: async key => {
      calls.push(key)
      return { data: key === 'select_value'
        ? [group('web'), group('ass_web'), group('ass_android'), group('ass_ios'), group('outdated')]
        : [visual, future] }
    } },
  }).useSelectValueStore
  const store = useStore()
  await Promise.all([store.getSelectValue(), store.getSelectValue()])
  assert.deepEqual(calls, ['select_value', 'ass_select_value'])
  for (const platform of [0, 1, 3]) {
    const options = store.getAssertionOptions(platform)
    assert.ok(options.some(item => item.value === visual.value))
    assert.ok(options.some(item => item.value === future.value))
    assert.ok(!options.some(item => item.value === 'web' || item.value === 'outdated'))
  }
  await store.getSelectValue()
  assert.equal(store.ass.filter(item => item.value === visual.value).length, 1)
})

test('API general assertions keep categories without the word assertion', async () => {
  const options = { ass: [], textAss: [] }
  const fn = loadFunction('src/views/apitest/case/details/index.vue', 'getCacheDataKeyValue', {
    getSystemCacheDataKeyValue: async () => ({ data: [visual, future] }),
    filterDeprecatedAssertionMethods: items => items,
    optionLists: options,
  })
  fn()
  await Promise.resolve()
  await Promise.resolve()
  assert.deepEqual(options.ass.map(item => item.value), ['文件视觉识别', 'Future checks'])
})

test('UI visual actual is an object input, not an element selector', () => {
  const fields = { value: [{ key: 'ope_key', value: '' }] }
  const fn = loadFunction('src/views/uitest/page-steps/details/index.vue', 'upDataOpeValue', {
    nodeFields: fields, nodeType: { value: 1 }, liveObject: value => value,
    useSelectValue: {
      findItemByValue: () => ({ parameter: [
        { f: 'actual', n: '待测文件', d: true, v: { 文件路径: '' }, value_type: 'object', input_type: 'object' },
        { f: 'expect', n: '基准文件及比较标准', d: true, v: {}, value_type: 'object', input_type: 'object' },
      ] }),
      getTopLevelLabelByValue: () => visual,
    },
    isUiUploadFileParam: () => false,
    presetOpeValueValue: (_values, _key, fallback) => fallback,
  })
  fn('assert_pdf_comparison_pass')
  assert.equal(fields.value.some(item => item.type === 'element-cascader'), false)
  assert.ok(fields.value.some(item => item.key === 'actual-ope_value'))
  assert.ok(fields.value.some(item => item.key === 'expect-ope_value'))
})
