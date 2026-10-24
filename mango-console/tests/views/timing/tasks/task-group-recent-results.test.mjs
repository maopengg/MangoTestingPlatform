import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

test('任务组直接展示最近五次质量，点击打开对应批次报告，不按环境分组', () => {
  const source = readFileSync(new URL('../../../../src/views/timing/tasks/components/TaskGroupManager.vue', import.meta.url), 'utf8')
  assert.match(source, /title="最近执行质量"/)
  assert.match(source, /:results="record.recent_results \|\| \[\]"/)
  assert.match(source, /openGroupReport\(record.recent_results\[index\]\)/)
  assert.doesNotMatch(source, /result.test_env_text|mango-task-group-quality/)
  assert.match(source, /group_execution_id: result.group_execution_id/)
})

test('任务组、定时任务和共享质量组件均编译正常', () => {
  for (const path of ['components/TaskGroupManager.vue', 'components/TaskRecentResults.vue', 'index.vue']) {
    const filename = new URL(`../../../../src/views/timing/tasks/${path}`, import.meta.url).pathname
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: path })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: path,
      compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  }
})
