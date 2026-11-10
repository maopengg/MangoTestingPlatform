import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

function helpers() {
  const exports = {}
  const compiled = ts.transpileModule(readFileSync('src/views/timing/tasks/fine-tuning.ts', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  }).outputText
  new Function('exports', compiled)(exports)
  return exports
}
test('fine tuning sends changed independent fields only, never a stale whole task', () => {
  const { readFineTuning, fineTuningPatch } = helpers()
  const original = readFineTuning({ case_types: [1], case_people: { id: 7 }, api_concurrency_limit: 5,
    name: '组统一名称', test_envs: [2], task_group: 1 })
  assert.deepEqual(fineTuningPatch(original, { ...original, case_people: 8 }), { case_people: 8 })
  assert.deepEqual(fineTuningPatch(original, original), {})
  assert.deepEqual(Object.keys(original).sort(), ['api_concurrency_limit', 'case_people', 'report_retention_policy'])
  assert.deepEqual(fineTuningPatch(original, { ...original, case_types: [0, 2] }), {})
})
test('task group editing uses the public modal and preserves ordinary edit flow', () => {
  const page = readFileSync('src/views/timing/tasks/index.vue', 'utf8')
  assert.match(page, /fineTuningRef.value\?\.open\(target\)/)
  assert.match(page, /if \(record.task_group === null\) \{ onUpdate\(record\)/)
  const modal = readFileSync('src/views/timing/tasks/components/TaskFineTuningModal.vue', 'utf8')
  assert.match(modal, /<ModalDialog/)
  assert.match(modal, /fineTuningPatch\(original, form\)/)
  assert.doesNotMatch(modal, /v-permission|hasPermission/)
  assert.doesNotMatch(modal, /v-model="form.case_types"/)
})
test('task pages and fine tuning modal compile', () => {
  for (const path of ['index.vue', 'components/TaskFineTuningModal.vue', 'components/TaskGroupManager.vue']) {
    const filename = 'src/views/timing/tasks/' + path
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: path })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: path,
      compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  }
})
