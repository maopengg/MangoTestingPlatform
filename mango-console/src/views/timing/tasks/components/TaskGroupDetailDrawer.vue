<template>
  <a-drawer v-model:visible="visible" title="任务组详情" width="min(1100px, calc(100vw - 24px))" :footer="false" @cancel="close">
    <mango-panel-spin :loading="loading" class="mango-task-group-detail__spin">
      <a-alert v-if="operationError" type="error">{{ operationError }}</a-alert>
      <div v-if="detail" class="mango-task-group-detail">
        <div class="mango-soft-panel mango-task-group-detail__summary">
          <strong>{{ detail.name }}</strong>
          <span>{{ detail.enabled_task_count }}/{{ detail.module_count }} 个子任务启用</span>
          <a-tag :color="taskGroupSyncColor(detail.sync_status)" size="small">{{ taskGroupSyncText(detail.sync_status) }}</a-tag>
        </div>
        <a-table :data="detail.members" :pagination="false" :scroll="{ x: 940, y: 'calc(100vh - 220px)' }" class="mango-native-scroll-table" row-key="id">
          <template #columns>
            <a-table-column title="模块" :width="320" ellipsis tooltip>
              <template #cell="{ record }">{{ formatModulePath(record.module) }}</template>
            </a-table-column>
            <a-table-column title="任务ID" data-index="task_id" :width="90" align="center" />
            <a-table-column title="任务名称" data-index="task_name" :width="320" ellipsis tooltip />
            <a-table-column title="单独启用" :width="100" align="center">
              <template #cell="{ record }">
                <a-switch :model-value="record.child_enabled" :disabled="loading || pendingMembers.has(memberKey(record.id))"
                  :loading="pendingMembers.has(memberKey(record.id))" :before-change="value => changeMemberStatus(record, value)" />
              </template>
            </a-table-column>
            <a-table-column title="同步状态" :width="110" align="center">
              <template #cell="{ record }"><a-tag :color="taskGroupSyncColor(record.sync_status)" size="small">{{ taskGroupSyncText(record.sync_status) }}</a-tag></template>
            </a-table-column>
          </template>
        </a-table>
      </div>
    </mango-panel-spin>
  </a-drawer>
</template>

<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

import { onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { getScheduledTaskGroupDetail, updateScheduledTaskGroupMemberStatus } from '@/api/system/tasks'
import { formatModulePath } from '@/utils/business-format'
import { taskEditorResponse, type TaskEditorId } from '../task-editor-records'
import { taskListId } from '../task-list-records'
import { readTaskGroupDetail, readTaskGroupMemberUpdate, taskGroupSyncColor, taskGroupSyncText, type TaskGroupDetail, type TaskGroupMember } from '../task-group-detail-records'

const emit = defineEmits<{ (event: 'changed'): void }>()
const route = useRoute(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
const visible = ref(false), recordId = ref<TaskEditorId | null>(null), detail = ref<TaskGroupDetail | null>(null)
const loading = ref(false), error = ref(''), operationError = ref(''), pendingMembers = reactive(new Set<string>())
let active = true, disposed = false, windowVersion = 0, readVersion = 0
const identity = () => JSON.stringify([route.path, route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
const available = () => active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
function capture() {
  const version = windowVersion, key = identity(), id = recordId.value
  return () => available() && visible.value && version === windowVersion && key === identity() && id === recordId.value
}
const memberKey = (id: TaskEditorId) => JSON.stringify([String(recordId.value), String(id)])
function close() {
  windowVersion++; readVersion++; visible.value = false; recordId.value = null; detail.value = null
  loading.value = false; error.value = ''; operationError.value = ''
}
async function loadDetail() {
  if (!available() || !visible.value || recordId.value === null) return
  const id = recordId.value, version = ++readVersion, current = capture()
  loading.value = true; error.value = ''
  try {
    const result = readTaskGroupDetail(await getScheduledTaskGroupDetail(id), id)
    if (version === readVersion && current()) detail.value = result
  } catch (loadFailure0) { if (version === readVersion && current()) (reportLoadError(loadFailure0, "任务组详情加载失败，请重试", false), error.value = '任务组详情加载失败，请重试') }
  finally { if (version === readVersion && current()) loading.value = false }
}
async function open(id: TaskEditorId) {
  if (!available()) return
  close()
  try { recordId.value = taskListId(id) }
  catch { Message.error('任务组ID格式异常，请刷新后重试'); return }
  visible.value = true; await loadDetail()
}
async function changeMemberStatus(member: TaskGroupMember, enabled: boolean): Promise<boolean> {
  if (!available() || !visible.value || loading.value || !detail.value || recordId.value === null) return false
  const currentMember = detail.value.members.find(item => String(item.id) === String(member.id))
  if (!currentMember) return false
  const groupId = recordId.value, memberId = currentMember.id, key = memberKey(memberId), current = capture(), context = identity()
  const reopenedSameGroup = () => !current() && context === identity() && available() && visible.value && String(recordId.value) === String(groupId)
  if (pendingMembers.has(key)) return false
  pendingMembers.add(key); operationError.value = ''
  let committed = false
  try {
    const response = await updateScheduledTaskGroupMemberStatus(groupId, memberId, enabled)
    // 接口成功后的异常回包不应伪装成未提交，保留权威重读路径。
    taskEditorResponse(response)
    committed = true
    const updated = readTaskGroupMemberUpdate(response, currentMember)
    if (current() && detail.value) {
      readVersion++; loading.value = false
      const members = detail.value.members.map(item => String(item.id) === String(memberId) ? updated : item)
      detail.value = { ...detail.value, members, enabled_task_count: members.filter(item => item.effective_enabled).length }
      Message.success('子任务状态已更新')
    }
    if (reopenedSameGroup()) await loadDetail()
    if (context === identity() && available()) emit('changed')
    return true
  } catch {
    if (current()) {
      operationError.value = committed ? '状态已提交，但返回数据异常，请重新加载详情核对' : '子任务状态更新失败，请重试'
      if (committed) await loadDetail()
    }
    if (committed && reopenedSameGroup()) await loadDetail()
    if (committed && context === identity() && available()) emit('changed')
    return false
  } finally { pendingMembers.delete(key) }
}
function visibilityChanged() { if (document.visibilityState !== 'visible') close() }
watch(identity, close, { flush: 'sync' })
onMounted(() => document.addEventListener('visibilitychange', visibilityChanged))
onActivated(() => { active = true })
onDeactivated(() => { active = false; close() })
onBeforeUnmount(() => { disposed = true; close(); document.removeEventListener('visibilitychange', visibilityChanged) })
defineExpose({ open, close })
</script>

<style scoped>
.mango-task-group-detail__spin { display: block; width: 100%; }
.mango-task-group-detail {
  display: flex;
  height: calc(100vh - 100px);
  min-height: 0;
  flex-direction: column;
  gap: var(--m-page-gap);
}
.mango-task-group-detail__summary { display: flex; align-items: center; gap: var(--m-page-gap); }
</style>
