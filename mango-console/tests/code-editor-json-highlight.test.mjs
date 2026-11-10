import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { jsonLanguage } from '@codemirror/lang-json'
import { highlightTree, classHighlighter } from '@lezer/highlight'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

test('JSON property names use the existing shared key color', () => {
  const json = '{"categoryId":0,"name":"${{example_name}}","enabled":true}'
  const spans = []
  highlightTree(jsonLanguage.parser.parse(json), classHighlighter, (from, to, classes) => spans.push({text: json.slice(from, to), classes}))
  assert.equal(spans.find(item => item.text === '"categoryId"').classes, 'tok-propertyName')
  assert.equal(spans.find(item => item.text === '0').classes, 'tok-number')
  assert.equal(spans.find(item => item.text === '"${{example_name}}"').classes, 'tok-string')
  const filename = 'src/components/editors/CodeEditor.vue'
  const source = fs.readFileSync(filename, 'utf8')
  assert.match(source, /:deep\(\.tok-propertyName\)[^{]*\{\s*color: var\(--m-code-key\)/)
  const {descriptor} = parse(source, {filename})
  const script = compileScript(descriptor, {id: 'json-highlight'})
  assert.deepEqual(compileTemplate({source: descriptor.template.content, filename, id: 'json-highlight', compilerOptions: {bindingMetadata: script.bindings}}).errors, [])
})
