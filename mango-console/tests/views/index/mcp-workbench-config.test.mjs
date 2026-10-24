import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { computed, reactive, ref } from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import ts from 'typescript'

const filename = 'src/views/index/components/McpWorkbench.vue'
const source = readFileSync(new URL('../../../src/views/index/components/McpWorkbench.vue', import.meta.url), 'utf8')
const code = source.slice(source.indexOf('  const mcpServerName ='), source.indexOf('  function fallbackCopy('))
const { outputText } = ts.transpileModule(code.replace('import.meta.env.MODE', "'dev'"), {
  compilerOptions: { target: ts.ScriptTarget.ES2020 },
})

test('MCP prompts and install instructions follow reactive platform English name', () => {
  const branding = reactive({ englishName: 'mango-test-platform' })
  const state = new Function('computed', 'ref', 'branding', 'baseURL', 'apiKey', `${outputText}; return { prompts, activePrompt, installPrompt, nextPrompt }`)(
    computed, ref, branding, 'https://example.com/api', ref('example-api-key'),
  )
  assert.ok(state.prompts.value.every(prompt => prompt.includes('mango-test-platform')))
  assert.match(state.installPrompt.value, /MCP 服务名称：mango-test-platform/)
  branding.englishName = 'ExampleTestingPlatform'
  assert.ok(state.prompts.value.every(prompt => prompt.includes('ExampleTestingPlatform')))
  assert.match(state.activePrompt.value, /ExampleTestingPlatform/)
  assert.match(state.installPrompt.value, /安装 ExampleTestingPlatform MCP 服务/)
  assert.match(state.installPrompt.value, /MCP 服务名称：ExampleTestingPlatform/)
  assert.doesNotMatch(state.installPrompt.value, /\[object Object\]/)
  for (let index = 0; index < state.prompts.value.length + 1; index++) {
    state.nextPrompt()
    assert.match(state.activePrompt.value, /ExampleTestingPlatform/)
  }
})

test('MCP workbench script and template compile', () => {
  const { descriptor } = parse(source, { filename })
  const script = compileScript(descriptor, { id: 'mcp-branding' })
  const template = compileTemplate({
    source: descriptor.template.content, filename, id: 'mcp-branding',
    compilerOptions: { bindingMetadata: script.bindings },
  })
  assert.deepEqual(template.errors, [])
})
