import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const read = path => readFileSync(new URL(path, import.meta.url), 'utf8')
const source = read('../src/views/apitest/case/details/components/ApiCasePosteriorPanel.vue')
const { descriptor } = parse(source)
const ast = ts.createSourceFile('panel.ts', descriptor.scriptSetup.content, ts.ScriptTarget.Latest, true)
const functions = ast.statements.filter(node => ts.isFunctionDeclaration(node) &&
  ['saveField', 'testExtract'].includes(node.name?.text)).map(node => node.getText(ast)).join('\n')
const js = ts.transpileModule(functions, { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
const guardSource = ts.transpileModule(read('../src/utils/change-aware-save.ts').replace(/export /g, ''),
  { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
const createChangeAwareSave = new Function(`${guardSource}; return createChangeAwareSave`)()

function panel(initial, { rejectSave = false, rejectTest = false } = {}) {
  const writes = [], errors = [], successes = []
  const item = { id: 1, posterior_response: [], posterior_response_text: [], ...initial }
  const draft = { value: structuredClone(item) }
  const guard = createChangeAwareSave(async payload => {
    writes.push(payload)
    if (rejectSave) { errors.push('具体后端错误'); throw Error('具体后端错误') }
    return { msg: 'saved' }
  })
  guard.seed(item)
  const props = { editLocked: false, item: draft.value }
  const actions = new Function('props', 'draft', 'putApiCaseDetailedParameter', 'Message',
    'postCaseDetailedParameterTestExtractResponseAfter', `${js}; return {saveField,testExtract}`)(
    props, draft, guard.save, { error: value => errors.push(value), success: value => successes.push(value) },
    async () => {
      if (rejectTest) { errors.push('提取接口具体错误'); throw Error('提取接口具体错误') }
      return { data: { key: 'key', value: 'value' } }
    })
  return { ...actions, draft, props, writes, errors, successes }
}

test('posterior panel script and template compile', () => {
  const script = compileScript(descriptor, { id: 'posterior-panel' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename: 'panel.vue',
    id: 'posterior-panel', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
})

for (const field of ['posterior_response', 'posterior_response_text']) {
  test(`${field}: unchanged and incomplete rows do not save; complete rows save once`, async () => {
    const p = panel({})
    await p.saveField(field)
    p.draft.value[field].push({ key: '', value: '' })
    await p.saveField(field)
    p.draft.value[field][0].key = 'result'
    await p.saveField(field)
    assert.equal(p.writes.length, 0)
    assert.deepEqual(p.errors, [])
    p.draft.value[field][0].value = field === 'posterior_response' ? '$.data' : '(.*)'
    await p.saveField(field)
    await p.saveField(field)
    assert.equal(p.writes.length, 1)
  })
}

test('incomplete edit never filters out an existing rule; deletion still persists an empty list', async () => {
  const p = panel({ posterior_response: [{ key: 'result', value: '$.data' }] })
  p.draft.value.posterior_response[0].key = ''
  await p.saveField('posterior_response')
  assert.equal(p.writes.length, 0)
  assert.equal(p.draft.value.posterior_response.length, 1)
  p.draft.value.posterior_response = []
  await p.saveField('posterior_response')
  assert.deepEqual(p.writes, [{ id: 1, posterior_response: [] }])
})

test('save failure displays only the request-layer error and keeps draft retryable', async () => {
  const p = panel({}, { rejectSave: true })
  p.draft.value.posterior_response.push({ key: 'result', value: '$.data' })
  await p.saveField('posterior_response')
  assert.deepEqual(p.errors, ['具体后端错误'])
  assert.equal(p.draft.value.posterior_response[0].key, 'result')
  await p.saveField('posterior_response')
  assert.equal(p.writes.length, 2)
  assert.equal(p.successes.length, 0)
})

test('locked scenarios do not save; extraction test errors are not duplicated', async () => {
  const p = panel({ posterior_response: [{ key: 'result', value: '$.data' }],
    result_data: { response: { json: { data: 1 } } } }, { rejectTest: true })
  p.props.editLocked = true
  p.draft.value.posterior_response[0].key = 'changed'
  await p.saveField('posterior_response')
  assert.equal(p.writes.length, 0)
  await p.testExtract('jsonpath', 0)
  assert.deepEqual(p.errors, ['提取接口具体错误'])
})
