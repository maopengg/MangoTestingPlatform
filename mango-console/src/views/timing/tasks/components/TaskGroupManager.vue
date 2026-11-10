<template>
  <div class="mango-task-group-manager">
    <template v-if="enumsError"></template>
    <a-spin v-else-if="enumsLoading" :size="scaleDensityPixels(16)"><span class="mango-task-group-manager__metadata">正在加载选项…</span></a-spin>
    <a-alert v-if="operationError" type="error">{{ operationError }}</a-alert>
    <a-table
      :data="rows"
      :loading="loading"
      :pagination="false"
      :bordered="false"
      :scroll="{ x: 2510 }"
      row-key="id"
    >
      <template #columns>
        <a-table-column title="ID" data-index="id" :width="80" align="center" />
        <a-table-column title="任务组名称" data-index="name" :width="180" ellipsis tooltip>
          <template #cell="{ record }">
            <a-link @click="filterTasks(record)">{{ record.name }}</a-link>
          </template>
        </a-table-column>
        <a-table-column title="子任务" :width="120" align="center">
          <template #cell="{ record }">
            {{ record.enabled_task_count }}/{{ record.module_count }} 启用
          </template>
        </a-table-column>
        <a-table-column title="最近执行质量" :width="290">
          <template #cell="{ record }">
            <TaskRecentResults
              :results="record.recent_results || []"
              @open="(index) => openGroupReport(record.recent_results[index])"
            />
          </template>
        </a-table-column>
        <a-table-column title="模块范围" :width="120" align="center">
          <template #cell="{ record }">{{ record.module_count }} 个模块</template>
        </a-table-column>
        <a-table-column title="定时器" :width="120" ellipsis tooltip>
          <template #cell="{ record }">
            <a-tooltip :content="record.timing_strategies.map((item) => item.name).join('、')">
              <span class="mango-task-group-manager__ellipsis">
                {{ record.timing_strategies.map((item) => item.name).join('、') || '-' }}
              </span>
            </a-tooltip>
          </template>
        </a-table-column>
        <a-table-column title="测试环境" :width="100">
          <template #cell="{ record }">
            <a-space :size="4" wrap>
              <a-tag
                v-for="value in record.test_envs"
                :key="value"
                :color="enumStore.colors[value]"
                size="small"
              >
                {{ optionTitle(enumStore.environment_type, value) }}
              </a-tag>
            </a-space>
          </template>
        </a-table-column>
        <a-table-column title="用例类型" :width="100">
          <template #cell="{ record }">
            <a-tag v-if="!record.case_types?.length" color="gray" size="small">全部类型</a-tag>
            <a-space v-else :size="4" wrap>
              <a-tag
                v-for="value in record.case_types"
                :key="value"
                :color="enumStore.colors[value]"
                size="small"
              >
                {{ optionTitle(enumStore.test_case_type, value) }}
              </a-tag>
            </a-space>
          </template>
        </a-table-column>
        <a-table-column title="执行场景" :width="180">
          <template #cell="{ record }">
            <ExecutionSceneTagGrid
              :values="record.execution_scenes"
              :options="enumStore.api_case_scenario_tag"
              :colors="enumStore.colors"
            />
          </template>
        </a-table-column>
        <a-table-column title="负责人" :width="90" align="center">
          <template #cell="{ record }">
            {{ record.case_people?.name || '-' }}
          </template>
        </a-table-column>
        <a-table-column title="是否开启" :width="90" align="center">
          <template #cell="{ record }">
            <a-switch
              :loading="switchIds.has(record.id)"
              :disabled="busy(record.id)"
              :model-value="record.status === 1"
              :before-change="(value) => changeGroupSwitch(record, 'status', value)"
            />
          </template>
        </a-table-column>
        <a-table-column title="是否通知" :width="90" align="center">
          <template #cell="{ record }">
            <a-switch
              :loading="switchIds.has(record.id)"
              :disabled="busy(record.id)"
              :model-value="record.is_notice === 1"
              :before-change="(value) => changeGroupSwitch(record, 'is_notice', value)"
            />
          </template>
        </a-table-column>
        <a-table-column title="失败通知" :width="90" align="center">
          <template #cell="{ record }">
            <a-switch
              :loading="switchIds.has(record.id)"
              :model-value="record.is_notice === 1 && record.fail_notice === 1"
              :disabled="record.is_notice !== 1 || busy(record.id)"
              :before-change="(value) => changeGroupSwitch(record, 'fail_notice', value)"
            />
          </template>
        </a-table-column>
        <a-table-column title="通知组" :width="180" ellipsis tooltip>
          <template #cell="{ record }">{{ record.notice_group?.name || '-' }}</template>
        </a-table-column>
        <a-table-column title="更新人" data-index="update_user_name" :width="110" align="center" />
        <a-table-column title="更新时间" data-index="update_time" :width="180" align="center" />
        <a-table-column title="同步状态" :width="110" align="center">
          <template #cell="{ record }">
            <a-tag :color="syncColor(record.sync_status)" size="small">
              {{ syncText(record.sync_status) }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column title="项目/产品" :width="140" ellipsis tooltip>
          <template #cell="{ record }">
            {{ formatProjectProductPath(record.project_product) }}
          </template>
        </a-table-column>
        <a-table-column title="操作" :width="160" fixed="right" align="center">
          <template #cell="{ record }">
            <MangoTableActions
              :actions="[
    {
        label: '触发',
        loading: triggeringIds.has(record.id),
        disabled: busy(record.id),
        onClick: () => triggerGroup(record),
    },
    {
        label: '重发报告',
        loading: noticeLoadingIds.has(record.id) || (noticeSending && sendingGroupId === record.id),
        disabled: busy(record.id),
        onClick: () => openResendNotice(record),
    },
    { label: '查看', onClick: () => openDetail(record) },
    { label: '导出离线 HTML', onClick: () => openOfflineReport(record) },
    { label: '编辑', disabled: busy(record.id), onClick: () => openEdit(record) },
    { label: '删除', danger: true, disabled: busy(record.id), loading: deletingIds.has(record.id), onClick: () => deleteGroup(record) },
]"
            />
          </template>
        </a-table-column>
      </template>
    </a-table>
    <TableFooter :pagination="pagination" :show-refresh="false" />
  </div>

  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="noticeVisible"
    title="重新发送任务组汇总通知"
    :width="560"
    :mask-closable="false"
    :ok-loading="noticeSending"
    :cancel-button-props="{ disabled: noticeSending }"
    :closable="!noticeSending"
    ok-text="发送"
    @before-ok="confirmResendNotice"
    @cancel="closeNotice"
  >
    <a-alert v-if="noticeError" type="error">{{ noticeError }}</a-alert>
    <a-form auto-label-width class="mango-simple-form" :model="{}" layout="horizontal">
      <a-form-item class="mango-simple-form-item" label="任务组">{{ noticeGroup?.name }}</a-form-item>
      <a-form-item class="mango-simple-form-item" label="最近执行" required>
        <a-select
          v-model="noticeExecutionId"
          :loading="noticeLoading"
          :disabled="noticeLoading || noticeSending"
          :options="noticeExecutions.map((item) => ({
            value: item.id,
            label: `${optionTitle(enumStore.environment_type, item.test_env)} · ${String(item.planned_at).replace('T', ' ').slice(0, 19)}`,
          }))"
          placeholder="请选择被测环境对应的最近一次执行"
        />
      </a-form-item>
      <a-form-item class="mango-simple-form-item" label="原通知组">
        {{ noticeExecutions.find((item) => item.id === noticeExecutionId)?.notice_group__name || '未配置' }}
      </a-form-item>
    </a-form>
    <a-alert>按所选批次全部子报告的当前结果发送到原通知组，不重新执行任务；全部通过也可发送。</a-alert>
  </a-modal>

  <TaskGroupEditorDialog ref="groupEditorRef" @saved="refreshGroups" />

  <TaskGroupDetailDrawer ref="groupDetailRef" @changed="refreshGroups" />
  <OfflineReportExportDialog v-model:visible="offlineExport.visible" source-kind="group" :source-id="offlineExport.sourceId" select-report />
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

import { scaleDensityPixels } from '@/hooks/useDisplayDensity'
import { onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Message, Modal } from '@arco-design/web-vue'
import TaskRecentResults from './TaskRecentResults.vue'
import TaskGroupEditorDialog from './TaskGroupEditorDialog.vue'
import TaskGroupDetailDrawer from './TaskGroupDetailDrawer.vue'
import OfflineReportExportDialog from '@/components/reports/OfflineReportExportDialog.vue'
import ExecutionSceneTagGrid from '@/components/display/ExecutionSceneTagGrid.vue'
import { useEnum } from '@/store/modules/get-enum'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { usePagination } from '@/hooks/table'
import { deleteScheduledTaskGroup, getScheduledTaskGroupDetail, updateScheduledTaskGroup, triggerScheduledTaskGroup, getLatestTaskGroupExecutions, resendTaskGroupNotice } from '@/api/system/tasks'
import { formatProjectProductPath } from '@/utils/business-format'
import { readTaskEditorOptions, taskEditorResponse, type TaskEditorId } from '../task-editor-records'
import { taskListId } from '../task-list-records'
import { readTaskGroupEditorDetail, taskGroupPayload } from '../task-group-editor-records'
import { taskGroupSyncText as syncText, taskGroupSyncColor as syncColor } from '../task-group-detail-records'
import { taskGroupSummary, taskGroupQuery, readTaskGroupUpdate, readGroupTriggerResult, readGroupNoticeExecutions, type TaskGroupFilters, type TaskGroupSummary, type TaskGroupListRecord, type GroupRecentResult, type GroupNoticeExecution } from '../task-group-list-records'
import { useTaskGroupList } from '../composables/useTaskGroupList'

const props = defineProps<{ projectProductId: TaskEditorId | null; filters: TaskGroupFilters }>()
const emit = defineEmits<{ (event: 'filter-tasks', record: TaskGroupSummary): void; (event: 'changed'): void }>()
const route = useRoute(), router = useRouter(), enumStore = useEnum(), user = useUserStore(), permission = usePermissionStore(), pagePath = route.path
let mounted = false, active = true, disposed = false, paused = false, contextVersion = 0, enumVersion = 0, noticeVersion = 0
const identity = () => JSON.stringify([route.path, route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
const contextKey = () => JSON.stringify([identity(), props.projectProductId])
const available = () => mounted && active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
function capture() { const version = contextVersion, key = contextKey(); return () => available() && version === contextVersion && key === contextKey() }
const pagination = usePagination(load, () => list.loading)
const list = useTaskGroupList({ available, capture, query: () => taskGroupQuery(props.projectProductId, props.filters, pagination.page, pagination.pageSize), pagination })
const { rows, loading, error: listError } = list
const enumsLoading = ref(false), enumsError = ref(''), operationError = ref('')
const groupEditorRef = ref<InstanceType<typeof TaskGroupEditorDialog> | null>(null), groupDetailRef = ref<InstanceType<typeof TaskGroupDetailDrawer> | null>(null)
const offlineExport = reactive<{ visible: boolean; sourceId: TaskEditorId }>({ visible: false, sourceId: 0 })
const pendingGroups = reactive(new Set<string>()), triggeringIds = reactive(new Set<TaskEditorId>()), deletingIds = reactive(new Set<TaskEditorId>()), switchIds = reactive(new Set<TaskEditorId>())
const confirmations = new Map<string, { close: () => void; valid: () => boolean }>()
const noticeLoadingIds = reactive(new Set<TaskEditorId>()), noticeVisible = ref(false), noticeSending = ref(false), noticeLoading = ref(false), noticeError = ref('')
const noticeGroup = ref<TaskGroupSummary | null>(null), noticeExecutions = ref<GroupNoticeExecution[]>([]), noticeExecutionId = ref<TaskEditorId | null>(null), sendingGroupId = ref<TaskEditorId | null>(null)
const busy = (id: TaskEditorId) => pendingGroups.has(String(id))
function acquire(id: TaskEditorId) { if (busy(id)) return false; pendingGroups.add(String(id)); return true }
function release(id: TaskEditorId) { pendingGroups.delete(String(id)) }
function optionTitle(options: unknown, value: TaskEditorId) {
  try { return readTaskEditorOptions(options ?? []).find(item => String(item.key) === String(value))?.title ?? String(value) }
  catch { return String(value) }
}
function load() { return list.load() }
function refreshGroups() { if (available()) emit('changed'); list.invalidate(); return load() }
async function loadEnums() {
  if (!available()) return
  const version = ++enumVersion, current = capture(); enumsLoading.value = true; enumsError.value = ''
  try { await enumStore.getEnum() }
  catch (loadFailure0) { if (version === enumVersion && current()) (reportLoadError(loadFailure0, "任务组选项加载失败，请重试", false), enumsError.value = '任务组选项加载失败，请重试') }
  finally { if (version === enumVersion) enumsLoading.value = false }
}
function refreshAfterWrite(key: string) { if (key === identity() && available()) { list.invalidate(); void load() } }
function openCreate(moduleId?: TaskEditorId | null) { if (available()) return groupEditorRef.value?.openCreate({ projectProduct: props.projectProductId, module: moduleId ?? null }) }
function openEdit(record: TaskGroupSummary) { if (available() && !busy(record.id)) return groupEditorRef.value?.openEdit(record.id) }
function openDetail(record: TaskGroupSummary) { if (available()) return groupDetailRef.value?.open(record.id) }
function openOfflineReport(record: TaskGroupSummary) { if (available()) Object.assign(offlineExport, { sourceId: taskListId(record.id), visible: true }) }
function filterTasks(record: TaskGroupSummary) { if (available()) emit('filter-tasks', taskGroupSummary(record)) }
function openGroupReport(result: GroupRecentResult | undefined) {
  if (available() && result) return router.push({ path: '/report/index', query: { group_execution_id: result.group_execution_id } })
}
async function changeGroupSwitch(record: TaskGroupListRecord, field: 'status' | 'is_notice' | 'fail_notice', enabled: boolean): Promise<boolean> {
  if (!available() || (field === 'fail_notice' && record.is_notice !== 1) || !acquire(record.id)) return false
  const id = taskListId(record.id), key = identity(), current = capture()
  switchIds.add(id); operationError.value = ''; let committed = false
  try {
    const { draft } = readTaskGroupEditorDetail(await getScheduledTaskGroupDetail(id), id)
    if (!current()) return false
    draft[field] = enabled ? 1 : 0
    if (field === 'is_notice' && !enabled) draft.fail_notice = 0
    const response = await updateScheduledTaskGroup(taskGroupPayload(draft, id))
    taskEditorResponse(response); committed = true
    const updated = readTaskGroupUpdate(response, id)
    if (current()) { list.replace(updated); Message.success('任务组配置已更新') }
    return true
  } catch { if (current()) operationError.value = committed ? '任务组配置已提交，但返回数据异常，请重新加载核对' : '任务组配置更新失败，请重试'; return false }
  finally { switchIds.delete(id); release(id); if (committed) refreshAfterWrite(key) }
}
function closeConfirmation(id: TaskEditorId) {
  const key = String(id), entry = confirmations.get(key)
  confirmations.delete(key); entry?.close()
}
function confirmOperation(record: TaskGroupSummary, kind: 'trigger' | 'delete') {
  const target = taskGroupSummary(record), id = target.id, key = String(id)
  if (!available() || busy(id) || confirmations.has(key)) return
  const context = capture(); let open = true
  const current = () => open && context() && confirmations.get(key)?.valid === current
  const shell = Modal.confirm({
    title: kind === 'trigger' ? '触发任务组' : '删除任务组',
    content: kind === 'trigger' ? `确认立即触发任务组“${target.name}”中的全部定时任务吗？本次将生成执行报告并开始执行。` : `删除后将同时删除“${target.name}”及其生成的定时任务，历史执行报告和触发记录仍会保留。确认继续吗？`,
    okText: kind === 'trigger' ? '确认触发' : '删除', cancelText: '取消', ...(kind === 'delete' ? { okButtonProps: { status: 'danger' as const } } : {}),
    onCancel: () => { if (current()) closeConfirmation(id) },
    onBeforeOk: () => kind === 'trigger' ? executeGroupTrigger(id, current) : executeGroupDelete(id, current),
  })
  confirmations.set(key, { valid: current, close: () => { open = false; shell.close() } })
}
function triggerGroup(record: TaskGroupSummary) { confirmOperation(record, 'trigger') }
async function executeGroupTrigger(groupId: TaskEditorId, current: () => boolean): Promise<boolean> {
  if (!current() || !acquire(groupId)) return false
  const key = identity(); triggeringIds.add(groupId); operationError.value = ''; let committed = false
  try {
    const response = await triggerScheduledTaskGroup(groupId)
    taskEditorResponse(response); committed = true
    const result = readGroupTriggerResult(response)
    if (current()) {
      if (result.failed_count) Message.warning(`已触发任务组：生成 ${result.generated_count} 个执行报告，${result.failed_count} 个子任务生成失败，请查看定时触发记录`)
      else Message.success(`已触发任务组：生成 ${result.generated_count} 个执行报告`)
      closeConfirmation(groupId)
    }
    return true
  } catch { if (current()) operationError.value = committed ? '触发已提交，但返回结果异常，请查看触发记录核对' : '任务组触发失败，请重试'; return false }
  finally { triggeringIds.delete(groupId); release(groupId); if (committed) refreshAfterWrite(key) }
}
async function executeGroupDelete(id: TaskEditorId, current: () => boolean): Promise<boolean> {
  if (!current() || !acquire(id)) return false
  const key = identity(); deletingIds.add(id); operationError.value = ''; let committed = false
  try {
    taskEditorResponse(await deleteScheduledTaskGroup(id)); committed = true
    if (current()) { closeConfirmation(id); Message.success('任务组已删除') }
    return true
  } catch { if (current()) operationError.value = '任务组删除失败，请重试'; return false }
  finally {
    deletingIds.delete(id); release(id)
    if (committed) { if (key === identity() && available()) emit('changed'); refreshAfterWrite(key) }
  }
}
function deleteGroup(record: TaskGroupSummary) { confirmOperation(record, 'delete') }
function closeNotice() {
  noticeVersion++; noticeVisible.value = false; noticeGroup.value = null; noticeExecutions.value = []; noticeExecutionId.value = null
  noticeLoadingIds.clear(); noticeLoading.value = false; noticeError.value = ''
}
async function loadNoticeExecutions() {
  if (!available() || !noticeVisible.value || !noticeGroup.value || noticeSending.value) return
  const id = noticeGroup.value.id, version = ++noticeVersion, valid = capture()
  const current = () => valid() && version === noticeVersion && noticeVisible.value && noticeGroup.value?.id === id
  noticeLoadingIds.clear(); noticeLoadingIds.add(id); noticeLoading.value = true; noticeError.value = ''; noticeExecutions.value = []; noticeExecutionId.value = null
  try {
    const executions = readGroupNoticeExecutions(await getLatestTaskGroupExecutions(id))
    if (!current()) return
    if (!executions.length) { closeNotice(); Message.warning('该任务组暂无执行批次'); return }
    noticeExecutions.value = executions; noticeExecutionId.value = executions[0].id
  } catch (loadFailure1) { if (current()) (reportLoadError(loadFailure1, '执行批次加载失败，请重试'), noticeError.value = '') }
  finally { if (version === noticeVersion) { noticeLoadingIds.delete(id); noticeLoading.value = false } }
}
async function openResendNotice(record: TaskGroupSummary) {
  if (!available() || noticeLoading.value || noticeSending.value || noticeVisible.value || busy(record.id)) return
  closeNotice(); noticeGroup.value = taskGroupSummary(record); noticeVisible.value = true; await loadNoticeExecutions()
}
async function confirmResendNotice(): Promise<boolean> {
  if (!available() || !noticeVisible.value || noticeLoading.value || noticeSending.value || !noticeGroup.value || noticeExecutionId.value === null) return false
  const execution = noticeExecutions.value.find(item => String(item.id) === String(noticeExecutionId.value))
  if (!execution || !acquire(noticeGroup.value.id)) return false
  const groupId = noticeGroup.value.id, executionId = execution.id, version = noticeVersion, valid = capture()
  const current = () => valid() && version === noticeVersion && noticeVisible.value && noticeGroup.value?.id === groupId
  noticeSending.value = true; sendingGroupId.value = groupId; noticeError.value = ''
  try {
    taskEditorResponse(await resendTaskGroupNotice(groupId, executionId))
    if (current()) { closeNotice(); Message.success('报告通知已发送') }
    return true
  } catch (loadFailure0) { if (current()) (reportLoadError(loadFailure0, "加载失败，请重试", false), noticeError.value = '报告通知发送失败，请重试'); return false }
  finally { noticeSending.value = false; sendingGroupId.value = null; release(groupId) }
}
function closeWindows() {
  closeNotice(); groupEditorRef.value?.close(); groupDetailRef.value?.close(); offlineExport.visible = false
  for (const id of [...confirmations.keys()]) closeConfirmation(id)
}
function invalidate(clear = false) {
  contextVersion++; enumVersion++; closeWindows(); list.invalidate(clear); enumsLoading.value = false
  if (clear) { operationError.value = ''; enumsError.value = ''; pagination.page = 1 }
}
function applyFilters() { pagination.page = 1; list.invalidate(); return load() }
function resume() { if (!available()) return Promise.resolve([]); paused = false; return Promise.allSettled([loadEnums(), load()]) }
function visibilityChanged() { if (available()) { if (paused) void resume() } else { paused = true; invalidate() } }
watch(contextKey, () => { invalidate(true); if (available()) void resume() }, { flush: 'sync' })
watch(() => props.filters, () => { pagination.page = 1; list.invalidate(); if (available()) void load() }, { deep: true })
onMounted(() => { mounted = true; document.addEventListener('visibilitychange', visibilityChanged); void resume() })
onActivated(() => { active = true; if (paused) void resume() })
onDeactivated(() => { active = false; paused = true; invalidate() })
onBeforeUnmount(() => { disposed = true; invalidate(true); document.removeEventListener('visibilitychange', visibilityChanged) })
defineExpose({ applyFilters, load, openCreate })
</script>

<style scoped>
  .mango-task-group-manager {
    display: flex;
    min-height: 0;
    flex: 1;
    flex-direction: column;
  }

  .mango-task-group-manager__ellipsis {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mango-task-group-manager__metadata { color: var(--m-muted); font-size: 12px; }

</style>
