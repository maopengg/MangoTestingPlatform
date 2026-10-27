import assert from 'node:assert/strict'
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import test from 'node:test'
import { compileScript, compileTemplate, parse } from '@vue/compiler-sfc'

function sourceFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const path = join(directory, entry.name)
    return entry.isDirectory() ? sourceFiles(path) : /\.(vue|ts)$/.test(path) ? [path] : []
  })
}

test('environment field labels no longer use the ambiguous two-character label', () => {
  for (const filename of sourceFiles('src')) {
    const source = readFileSync(filename, 'utf8')
    assert.doesNotMatch(source, /(?:label|title)\s*[:=]\s*['"]环境['"]/, filename)
    assert.doesNotMatch(source, />\s*环境\s*</, filename)
    assert.doesNotMatch(source, /placeholder\s*[:=]\s*['"]请选择(?:绑定)?环境['"]/, filename)
  }
})

test('renamed environment labels preserve Vue template compilation', () => {
  for (const filename of [
    'src/components/business/UiElementAiHealPanel.vue',
    'src/components/forms/ParametrizeDrawer.vue',
    'src/views/apitest/case/details/index.vue',
    'src/views/gray/repository/index.vue',
    'src/views/system/sql-execution/index.vue',
    'src/views/timing/tasks/components/TaskGroupManager.vue',
    'src/views/uitest/auth-config/index.vue',
    'src/views/uitest/case/details/index.vue',
    'src/views/uitest/page/elements/index.vue',
  ]) {
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(errors, [], filename)
    const script = compileScript(descriptor, { id: 'environment-labels' })
    const template = compileTemplate({
      source: descriptor.template.content, filename, id: 'environment-labels',
      compilerOptions: { bindingMetadata: script.bindings },
    })
    assert.deepEqual(template.errors, [], filename)
  }
})
