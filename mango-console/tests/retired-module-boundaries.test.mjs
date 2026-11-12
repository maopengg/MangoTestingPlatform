import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { compileScript, compileTemplate, parse } from '@vue/compiler-sfc'

test('gray page, router, API client and editor are removed', () => {
  for (const path of ['src/views/gray/repository/index.vue', 'src/views/gray/config-file/index.vue',
    'src/views/gray/feature/index.vue', 'src/views/gray/execution-log/index.vue',
    'src/api/gray/index.ts', 'src/hooks/useGray.ts', 'src/components/business/CaseGrayConfigPanel.vue']) {
    assert.equal(existsSync(path), false, path)
  }
  assert.doesNotMatch(readFileSync('src/router/index.ts', 'utf8'), /path:\s*['"]\/gray['"]|@\/views\/gray\//)
})

test('remaining version snapshot component compiles without a gray editing tab', () => {
  const filename = 'src/views/apitest/case/details/components/ApiCaseVersionSnapshot.vue'
  const source = readFileSync(filename, 'utf8')
  assert.doesNotMatch(source, /key="gray"|caseGraySections|灰度配置/)
  const { descriptor, errors } = parse(source, { filename })
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'retired-version-snapshot' })
  const compiled = compileTemplate({ source: descriptor.template.content, filename, id: 'retired-version-snapshot',
    compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(compiled.errors, [])
})

test('version parser no longer synthesizes retired runtime fields or mutates history', () => {
  const source = readFileSync('src/types/api-test/case-revision-payload.ts', 'utf8')
  const output = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
  const module = { exports: {} }
  new Function('exports', 'module', output)(module.exports, module)
  const payload = { runtime: { gray_configs: [] }, api_case_detailed: [] }
  const original = structuredClone(payload)
  const result = module.exports.parseApiCaseRevisionPayload(payload)
  assert.equal(Object.hasOwn(result.runtime, 'gray_configs'), false)
  assert.deepEqual(payload, original)
})
