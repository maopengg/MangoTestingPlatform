import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

const source = readFileSync(new URL('../../../../src/views/timing/tasks/index.vue', import.meta.url), 'utf8')
const group = readFileSync(new URL('../../../../src/views/timing/tasks/components/TaskGroupManager.vue', import.meta.url), 'utf8')

test('任务表单标签预留六字及必填标记宽度，保持单行对齐', () => {
  const style = source.match(/\.mango-task-form-group__fields :deep\(\.arco-form-item-label-col\) \{([^}]+)\}/)?.[1]
  assert.ok(style)
  assert.match(style, /flex: 0 0 120px/)
  assert.match(style, /white-space: nowrap/)
})

test('任务组只提供创建时的子任务初始策略，不保存也不覆盖', () => {
  assert.match(source, /:options="enumStore.report_retention_policy"/)
  assert.match(source, /permission: 'timing.tasks:change', label: '保留策略'/)
  assert.match(group, /v-model="form.new_task_report_retention_policy"/)
  assert.match(group, /v-if="!editingId" label="报告保留策略"/)
  assert.match(group, /!editingId.value \? \{ new_task_report_retention_policy \} : \{\}/)
  assert.doesNotMatch(group, /form\.report_retention_policy|overwrite_report_retention/)
  assert.match(source, /result.report_retained === false/)
})

test('表格保留策略只读，任务组子任务通过独立弹窗修改', () => {
  const cell = source.split('item.key === \'report_retention_policy\'')[1].split('</template>')[0]
  assert.match(cell, /<span>/)
  assert.doesNotMatch(cell, /a-select|@change/)
  assert.match(source, /label: '保留策略', hidden: !record.task_group/)
  assert.match(source, /v-model:visible="retentionEditor.visible"/)
})

test('独立保存子任务策略：授权、局部 loading、失败不改变当前值', async () => {
  const start = source.indexOf('  async function saveRetentionPolicy(')
  const code = ts.transpileModule('const retentionSavingIds = ref([]);' + source.slice(start, source.indexOf('  const onModifyStatus', start)), {}).outputText
  let allowed = true, calls = 0, fail = false
  const state = new Function('ref', 'permissionStore', 'putSystemTasks', 'Message',
    `${code}; return { saveRetentionPolicy, retentionSavingIds }`)((value) => ({ value }),
    { hasPermission: () => allowed }, async (payload) => {
      calls++
      assert.equal(payload.id, 1)
      if (fail) throw new Error('network')
    }, { success() {} })
  const record = { id: 1, report_retention_policy: 'all' }
  await state.saveRetentionPolicy(record, 'abnormal_only')
  assert.equal(record.report_retention_policy, 'abnormal_only')
  fail = true
  await state.saveRetentionPolicy(record, 'all')
  assert.equal(record.report_retention_policy, 'abnormal_only')
  allowed = false
  await state.saveRetentionPolicy(record, 'all')
  assert.equal(calls, 2)
  assert.deepEqual(state.retentionSavingIds.value, [])
})
