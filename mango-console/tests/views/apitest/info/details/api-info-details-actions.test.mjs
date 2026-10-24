import assert from 'node:assert/strict'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'

import { compileScript, compileTemplate, parse } from '@vue/compiler-sfc'

const componentPath = fileURLToPath(
  new URL('../../../../../src/views/apitest/info/details/index.vue', import.meta.url)
)
const source = fs.readFileSync(componentPath, 'utf8')
const { descriptor, errors } = parse(source, { filename: componentPath })

assert.equal(errors.length, 0, `SFC parse errors: ${errors.join('\n')}`)
assert.ok(descriptor.template, 'API info details must include a template block')
assert.ok(descriptor.scriptSetup, 'API info details must include a script setup block')

const componentId = 'api-info-details-actions'
const compiledScript = compileScript(descriptor, { id: componentId })
const compiledTemplate = compileTemplate({
  id: componentId,
  filename: componentPath,
  source: descriptor.template.content,
  compilerOptions: {
    bindingMetadata: compiledScript.bindings,
  },
})

assert.equal(
  compiledTemplate.errors.length,
  0,
  `template compile errors: ${compiledTemplate.errors.join('\n')}`
)

const runActionCount = source.match(/@click="onRunCase"/g)?.length ?? 0
assert.equal(runActionCount, 1, 'API info details must expose exactly one run action')

const toolbarStart = source.indexOf('<a-space class="mango-detail-actions"')
const toolbarEnd = source.indexOf('</a-space>', toolbarStart)
const toolbarSource = source.slice(toolbarStart, toolbarEnd)
assert.ok(
  toolbarSource.includes('@click="onRunCase"'),
  'the single run action must stay in toolbar'
)

const responsePanelStart = source.indexOf('<aside class="api-response-panel">')
const responsePanelEnd = source.indexOf('</aside>', responsePanelStart)
const responsePanelSource = source.slice(responsePanelStart, responsePanelEnd)
assert.ok(
  !responsePanelSource.includes('@click="onRunCase"'),
  'response panel must only display results and must not duplicate the run action'
)

console.log('api info details action contract passed')
