import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { setupTaskList, taskResponse, taskRow } from '../../../helpers/timing-task-list-harness.mjs'

const source = readFileSync(new URL('../../../../src/views/timing/tasks/index.vue', import.meta.url), 'utf8')
const editor = readFileSync(new URL('../../../../src/views/timing/tasks/components/TaskEditorDialog.vue', import.meta.url), 'utf8')
const group = readFileSync(new URL('../../../../src/views/timing/tasks/components/TaskGroupEditorDialog.vue', import.meta.url), 'utf8')

test('任务表单标签预留六字及必填标记宽度，保持单行对齐', () => {
  const style = editor.match(/\.mango-task-form-group__fields :deep\(\.arco-form-item-label-col\) \{([^}]+)\}/)?.[1]
  assert.ok(style)
  assert.match(style, /flex: 0 0 120px/)
  assert.match(style, /white-space: nowrap/)
})

test('任务组只提供创建时的子任务初始策略，不保存也不覆盖', () => {
  assert.match(source, /:options="enumStore.report_retention_policy"/)
  assert.match(source, /label: '保留策略'/)
  assert.doesNotMatch(source, /permission: 'timing.tasks:change'|hasPermission\(/)
  assert.match(group, /v-model="form.new_task_report_retention_policy"/)
  assert.match(group, /v-if="editingId === null" label="报告保留策略"/)
  assert.match(group, /taskGroupPayload\(draft, editingId.value\)/)
  assert.doesNotMatch(group, /form\.report_retention_policy|overwrite_report_retention/)
  assert.match(source, /result.report_retained === false/)
})

test('表格保留策略只读，任务组子任务通过独立弹窗修改', () => {
  const cell = source.split('item.key === \'report_retention_policy\'')[1].split('</template>')[0]
  assert.match(cell, /<span>/)
  assert.doesNotMatch(cell, /a-select|@change/)
  assert.match(source, /label: '保留策略', hidden: record.task_group === null/)
  assert.match(source, /v-model:visible="retentionEditor.visible"/)
})

test('独立保存子任务策略：局部 loading、网络失败和后端拒绝不改变当前值', async t => {
  let server = taskRow({ id: 1, task_group: 1 }), mode = 'success'
  const h = setupTaskList({ getSystemTasks: async () => taskResponse([server]), putSystemTasks: async payload => {
    assert.equal(payload.id, 1)
    if (mode === 'network') throw Error('network')
    if (mode === 'denied') return { code: 403 }
    server = { ...server, ...payload }; return { code: 200 }
  } }); t.after(h.close); await h.mount()
  const original = h.rows.value[0]; h.openRetentionEditor(original); h.retentionEditor.value = 'abnormal_only'
  assert.equal(await h.saveRetentionPolicy(), true)
  assert.equal(original.report_retention_policy, 'all')
  assert.equal(h.rows.value[0].report_retention_policy, 'abnormal_only')
  for (const failure of ['network','denied']) {
    mode = failure; h.openRetentionEditor(h.rows.value[0]); h.retentionEditor.value = 'all'
    assert.equal(await h.saveRetentionPolicy(), false)
    assert.equal(h.rows.value[0].report_retention_policy, 'abnormal_only')
    assert.equal(h.retentionEditor.visible, true); assert.equal(h.retentionSaving.value, false)
  }
  assert.equal(h.writes.length, 3); assert.deepEqual(h.writeIds.value, [])
})
