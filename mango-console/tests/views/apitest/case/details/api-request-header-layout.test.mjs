import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import postcss from 'postcss'

const filename = new URL('../../../../../src/views/apitest/case/details/components/ApiCaseRequestPanel.vue', import.meta.url).pathname
const source = readFileSync(filename, 'utf8')
const defaults = readFileSync(new URL('../../../../../src/views/apitest/case/details/index.vue', import.meta.url), 'utf8')
const css = postcss.parse(readFileSync(new URL('../../../../../src/styles/index.css', import.meta.url), 'utf8'))
function declaration(selector, property) {
  let result
  css.walkRules(selector, rule => rule.walkDecls(property, decl => { result = decl.value }))
  return result
}

test('scenario and default headers share the global headers layout', () => {
  for (const content of [source, defaults]) {
    assert.match(content, /class="mango-case-global-table mango-case-global-table--headers"/)
  }
  const { descriptor } = parse(source, { filename })
  assert.doesNotMatch(descriptor.styles[0].content, /grid-template-columns|font-size|text-overflow/)
  assert.match(source, /:title="header.key"/)
  assert.match(source, /:title="header.value"/)
})

test('global header has checkbox track but data row has only key and value tracks', () => {
  assert.equal(declaration('.mango-case-global-table--headers .mango-case-global-table__head', 'grid-template-columns'),
    '30px minmax(160px, 0.8fr) minmax(240px, 1.6fr)')
  assert.equal(declaration('.mango-case-global-table--headers .mango-case-global-table__row', 'grid-template-columns'),
    'minmax(160px, 0.8fr) minmax(240px, 1.6fr)')
  assert.equal(declaration('.mango-case-global-table--headers .mango-case-global-table__body .arco-checkbox', 'grid-template-columns'),
    '30px minmax(0, 1fr)')
  assert.equal(declaration('.mango-case-global-table--headers .mango-case-global-table__body .arco-checkbox-label', 'margin-left'), '0')
})

test('request panel keeps selection, rollback and local loading and compiles', () => {
  assert.match(source, /v-model="item.headers"/)
  assert.match(source, /@change="saveHeaders"/)
  assert.match(source, /props.item.headers = persistedHeaders/)
  assert.match(source, /:loading="headersSaving"/)
  const { descriptor, errors } = parse(source, { filename })
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'request-headers' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename,
    id: 'request-headers', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
})
