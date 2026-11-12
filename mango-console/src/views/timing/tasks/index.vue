<template>
  <TableBody
    ref="tableBody"
    plain
    class="mango-detail-workbench-page"
    :sticky-horizontal-scroll="false"
  >
    <template #header>
      <TableHeader title="定时任务" />
    </template>

    <template #default>
      <ProjectProductNavigationWorkbench
        ref="navigationCreateRef"
        class="mango-timing-task-workbench"
        contained-body
        show-modules
        :show-toolbar="false"
        :model-value="getConditionValue('project_product')"
        :module-value="getConditionValue('module')"
        :reset-key="sidebarResetKey"
        emit-initial-filter
        @filter-change="onSidebarFilterChange"
        @search="onWorkbenchSearch"
        @reset-search="onResetSearch"
      >
        <template #search>
          <a-form v-if="activeTab === 'tasks'" :model="{}" layout="inline" @keyup.enter="onWorkbenchSearch">
            <a-form-item v-for="item of headerConditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="onWorkbenchSearch"
                  @clear="onWorkbenchSearch"
                />
              </template>
              <template v-else-if="item.type === 'cascader'">
                <a-cascader
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="enumStore.environment_type"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onWorkbenchSearch"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'case_people'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="userOptions"
                  :loading="usersLoading"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onWorkbenchSearch"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'task_group'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="item.optionItems"
                  :placeholder="item.placeholder"
                  :loading="taskGroupOptionsLoading"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="onWorkbenchSearch"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'execution_scenes'">
                <a-select
                  v-model="item.value"
                  multiple
                  :max-tag-count="1"
                  :field-names="fieldNames"
                  :options="selectableSceneOptions"
                  :placeholder="item.placeholder"
                  allow-clear
                  @change="onWorkbenchSearch"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'test_envs'">
                <a-select
                  v-model="item.value"
                  multiple
                  :max-tag-count="1"
                  :field-names="fieldNames"
                  :options="enumStore.environment_type"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  @change="onWorkbenchSearch"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'case_types'">
                <a-select
                  v-model="item.value"
                  multiple
                  :max-tag-count="1"
                  :field-names="fieldNames"
                  :options="taskCaseTypeOptions"
                  :placeholder="item.placeholder"
                  allow-clear
                  @change="onWorkbenchSearch"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'execution_scope'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="executionScopeFilterOptions"
                  :placeholder="item.placeholder"
                  allow-clear
                  @change="onWorkbenchSearch"
                />
              </template>
              <template v-else-if="item.type === 'select'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="item.optionItems"
                  :placeholder="item.placeholder"
                  allow-clear
                  value-key="key"
                  @change="onWorkbenchSearch"
                />
              </template>
              <template v-if="item.type === 'date'">
                <a-date-picker v-model="item.value" />
              </template>
              <template v-if="item.type === 'time'">
                <a-time-picker v-model="item.value" value-format="HH:mm:ss" />
              </template>
              <template v-if="item.type === 'check-group'">
                <a-checkbox-group v-model="item.value">
                  <a-checkbox v-for="it of item.optionItems" :key="it.value" :value="it.value">
                    {{ item.label }}
                  </a-checkbox>
                </a-checkbox-group>
              </template>
            </a-form-item>
          </a-form>
          <a-form v-else :model="taskGroupFilters" layout="inline" @keyup.enter="onWorkbenchSearch">
            <a-form-item label="任务组名称">
              <a-input v-model="taskGroupFilters.name" allow-clear placeholder="请输入任务组名称" />
            </a-form-item>
            <a-form-item label="测试环境">
              <a-select
                v-model="taskGroupFilters.test_envs"
                multiple
                allow-clear
                :max-tag-count="1"
                :field-names="fieldNames"
                :options="enumStore.environment_type"
                placeholder="请选择测试环境"
              />
            </a-form-item>
            <a-form-item label="用例类型">
              <a-select
                v-model="taskGroupFilters.case_types"
                multiple
                allow-clear
                :max-tag-count="1"
                :field-names="fieldNames"
                :options="taskCaseTypeOptions"
                placeholder="请选择用例类型"
              />
            </a-form-item>
            <a-form-item label="执行场景">
              <a-select
                v-model="taskGroupFilters.execution_scenes"
                multiple
                allow-clear
                :max-tag-count="1"
                :field-names="fieldNames"
                :options="taskGroupSceneOptions"
                placeholder="请选择执行场景"
              />
            </a-form-item>
            <a-form-item label="是否开启">
              <a-select
                v-model="taskGroupFilters.status"
                allow-clear
                :options="binaryStatusOptions"
                placeholder="请选择开启状态"
              />
            </a-form-item>
            <a-form-item label="是否通知">
              <a-select
                v-model="taskGroupFilters.is_notice"
                allow-clear
                :options="noticeStatusOptions"
                placeholder="请选择通知状态"
              />
            </a-form-item>
            <a-form-item label="同步状态">
              <a-select
                v-model="taskGroupFilters.sync_status"
                allow-clear
                :options="taskGroupSyncStatusOptions"
                placeholder="请选择同步状态"
              />
            </a-form-item>
          </a-form>
        </template>
        <template #tabs>
          <a-tabs v-model:active-key="activeTab" class="mango-timing-task-tabs mango-tabs-nav-only">
            <template #extra>
              <a-space>
                <a-button
                  v-if="activeTab === 'tasks'"
                  size="small"
                  type="primary"
                  @click="onAdd"
                  data-testid="qa-views-timing-tasks-button-新增"
                >
                  新增
                </a-button>
                <a-button  v-else size="small" type="primary" @click="openTaskGroupCreate">
                  新增任务组
                </a-button>
              </a-space>
            </template>
            <a-tab-pane key="tasks" title="定时任务" />
            <a-tab-pane key="groups">
              <template #title>
                <span class="mango-timing-task-tab-title">任务组</span>
              </template>
            </a-tab-pane>
          </a-tabs>
        </template>
        <div class="mango-task-feedback">
          
          
          <MangoRequestFeedback v-if="operationError" :message="(operationError)" />
          <template v-if="activeTab === 'tasks'">
            
          </template>
        </div>
        <StickyHorizontalTable v-if="activeTab === 'tasks'" :scroll-x="3090">
          <a-table
            :scroll="{ x: 3090, y: '100%' }"
            :bordered="false"
            :columns="tableColumns"
            :data="rows"
            :loading="listLoading"
            :pagination="false"
            :rowKey="rowKey"
            @selection-change="onSelectionChange"
          >
            <template #columns>
              <a-table-column
                v-for="item of tableColumns"
                :key="item.key"
                :align="item.align"
                :data-index="item.key"
                :fixed="item.fixed"
                :title="item.title"
                :width="item.width"
                :ellipsis="item.ellipsis"
                :tooltip="item.tooltip"
              >
                <template v-if="item.key === 'index'" #cell="{ record }">
                  {{ record.id }}
                </template>
                <template v-else-if="item.key === 'module'" #cell="{ record }">
                  {{ record?.module ? formatModulePath(record.module) : '-' }}
                </template>
                <template v-else-if="item.key === 'project_product'" #cell="{ record }">
                  {{ formatProjectProductPath(record.project_product) }}
                </template>
                <template v-else-if="item.key === 'timing_strategies'" #cell="{ record }">
                  <a-tooltip :content="timingStrategiesTooltip(record.timing_strategies)">
                    <span class="mango-task-timing-strategy">
                      {{ timingStrategiesText(record.timing_strategies) }}
                    </span>
                  </a-tooltip>
                </template>
                <template v-else-if="item.key === 'recent_results'" #cell="{ record }">
                  <a-button v-if="recentError && !recentResults[String(record.id)]?.length" size="mini" type="text" :loading="recentResultsLoading" @click="list.loadRecentResults">重试</a-button>
                  <TaskRecentResults
                    v-else
                    :results="recentResults[String(record.id)] || []"
                    :loading="recentResultsLoading"
                    @open="(index) => openRecentResult(recentResults[String(record.id)]?.[index])"
                  />
                </template>
                <template v-else-if="item.key === 'case_people'" #cell="{ record }">
                  {{ record.case_people?.name }}
                </template>
                <template v-else-if="item.key === 'test_envs'" #cell="{ record }">
                  <a-space :size="4" wrap>
                    <a-tag
                      v-for="testEnv in record.test_envs || []"
                      :key="testEnv"
                      :color="enumStore.colors[testEnv]"
                      size="small"
                    >
                      {{ optionTitle(enumStore.environment_type, testEnv) }}
                    </a-tag>
                  </a-space>
                </template>
                <template v-else-if="item.key === 'case_types'" #cell="{ record }">
                  <a-tag v-if="!record.case_types?.length" color="gray" size="small"
                    >全部类型</a-tag
                  >
                  <a-space v-else :size="4">
                    <a-tag
                      v-for="caseType in record.case_types"
                      :key="caseType"
                      :color="enumStore.colors[caseType]"
                      size="small"
                    >
                      {{ optionTitle(enumStore.test_case_type, caseType) }}
                    </a-tag>
                  </a-space>
                </template>
                <template v-else-if="item.key === 'execution_scenes'" #cell="{ record }">
                  <ExecutionSceneTagGrid
                    :values="record.execution_scenes"
                    :options="enumStore.api_case_scenario_tag"
                    :colors="enumStore.colors"
                  />
                </template>
                <template v-else-if="item.key === 'execution_scope'" #cell="{ record }">
                  <a-tag
                    :color="
                      optionTagColor(enumStore.automation_execution_scope, record.execution_scope)
                    "
                    size="small"
                  >
                    {{ optionTitle(enumStore.automation_execution_scope, record.execution_scope) }}
                  </a-tag>
                </template>
                <template v-else-if="item.key === 'case_executor'" #cell="{ record }">
                  {{ record.case_executor }}
                </template>
                <template v-else-if="item.key === 'notice_group'" #cell="{ record }">
                  {{ record.notice_group?.name }}
                </template>
                <template v-else-if="item.key === 'task_group_name'" #cell="{ record }">
                  <a-tag v-if="record.task_group !== null" color="blue" size="small">
                    {{ record.task_group_name }}
                  </a-tag>
                  <span v-else>-</span>
                </template>
                <template v-else-if="item.key === 'status'" #cell="{ record }">
                  <a-switch
                    :loading="statusSavingIds.includes(String(record.id))"
                    :model-value="record.status === 1"
                    :disabled="isTaskBusy(record.id)"
                    :beforeChange="(newValue) => onModifyStatus(newValue, record, 'status')"
                  />
                </template>
                <template v-else-if="item.key === 'is_notice'" #cell="{ record }">
                  <a-switch
                    :loading="statusSavingIds.includes(String(record.id))"
                    :model-value="record.is_notice === 1"
                    :disabled="record.task_group !== null || isTaskBusy(record.id)"
                    :beforeChange="(newValue) => onModifyStatus(newValue, record, 'is_notice')"
                  />
                </template>
                <template v-else-if="item.key === 'fail_notice'" #cell="{ record }">
                  <a-switch
                    :loading="statusSavingIds.includes(String(record.id))"
                    :model-value="record.is_notice === 1 && record.fail_notice === 1"
                    :disabled="record.is_notice !== 1 || record.task_group !== null || isTaskBusy(record.id)"
                    :beforeChange="(newValue) => onModifyStatus(newValue, record, 'fail_notice')"
                  />
                </template>
                <template v-else-if="item.key === 'report_retention_policy'" #cell="{ record }">
                  <span>{{ (enumStore.report_retention_policy || []).find((option) => option.key === record.report_retention_policy)?.title || '-' }}</span>
                </template>
                <template v-else-if="item.key === 'update_user'" #cell="{ record }">
                  {{ record.update_user?.name || record.update_user?.username || '-' }}
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <MangoTableActions
                    :actions="[
    {
        label: '触发',
        loading: triggerPreparingId === record.id || (triggerSaving && triggerTarget?.id === record.id),
        disabled: isTaskBusy(record.id),
        onClick: () => onTrigger(record), },
    {
        label: record.execution_scope === 'manual'
            ? '添加用例'
            : '匹配用例',
        onClick: () => onClick(record),
    },
    { label: '排查结果', onClick: () => openTaskDiagnostic(record) },
    { label: '导出离线 HTML', onClick: () => openOfflineReport(record) },
    {
        label: '编辑',
        loading: finePreparingId === record.id,
        disabled: isTaskBusy(record.id),
        onClick: () => onEdit(record), },
    { label: '保留策略', hidden: record.task_group === null,
        disabled: isTaskBusy(record.id),
        onClick: () => openRetentionEditor(record) },
    {
        label: '删除',
        danger: true,
        disabled: record.task_group !== null || isTaskBusy(record.id),
        loading: deletingIds.includes(String(record.id)),
        onClick: () => onDelete(record), },
]"
                  />
                </template>
              </a-table-column>
            </template>
          </a-table>
        </StickyHorizontalTable>
        <TaskGroupManager
          v-else
          ref="taskGroupRef"
          :key="identityKey"
          :project-product-id="navigationProjectProductId"
          :filters="taskGroupFilters"
          @filter-tasks="filterTasksByGroup"
          @changed="loadTaskGroupOptions"
        />
        <template #footer>
          <TableFooter v-if="activeTab === 'tasks'" :pagination="pagination" />
        </template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <TaskFineTuningModal ref="fineTuningRef"
    :user-options="userOptions" :retention-options="enumStore.report_retention_policy || []"
    :platform-limit="apiPlatformLimit" @saved="doRefresh" />
  <TaskEditorDialog ref="taskEditorRef" @saved="doRefresh" />
  <TestExecutionModal
    ref="triggerModalRef"
    title="触发定时任务"
    :platform-limit="apiPlatformLimit"
    environment-selectable
    environment-multiple
    environment-placeholder="请选择本次临时执行环境"
    environment-hint="默认使用任务配置；可临时改选其他环境，每个环境分别创建一份报告，不会修改定时任务"
    concurrency-placeholder="留空则使用定时任务配置"
    concurrency-hint="留空则使用定时任务配置，本次修改不会回写定时任务"
    @confirm="onConfirmTrigger"
    @cancel="onCancelTrigger"
  >
    <template #summary><MangoRequestFeedback v-if="triggerError" :message="(triggerError)" /></template>
  </TestExecutionModal>
  <a-modal modal-class="mango-simple-form-modal" v-model:visible="retentionEditor.visible" title="报告保留策略" :width="560"
    :mask-closable="false" :closable="!retentionSaving"
    :cancel-button-props="{ disabled: !!retentionSaving }" :ok-loading="!!retentionSaving"
    @before-ok="saveRetentionPolicy" @cancel="closeRetention">
    <MangoRequestFeedback v-if="retentionError" :message="(retentionError)" />
    <a-form auto-label-width class="mango-simple-form" :model="retentionEditor" layout="horizontal">
      <a-form-item class="mango-simple-form-item" label="任务名称">{{ retentionEditor.record?.name }}</a-form-item>
      <a-form-item class="mango-simple-form-item" label="保留策略">
        <a-select v-model="retentionEditor.value" :field-names="fieldNames" :options="enumStore.report_retention_policy"
          :disabled="!!retentionSaving" />
      </a-form-item>
    </a-form>
  </a-modal>
  <OfflineReportExportDialog v-model:visible="offlineExport.visible" source-kind="suite" :source-id="offlineExport.sourceId" select-report />
  <DiagnosticMarkdownDrawer
    v-model:visible="diagnosticDrawer.visible"
    target-type="scheduled_task"
    :target-id="diagnosticDrawer.targetId"
    :document-available="diagnosticDrawer.documentAvailable"
    :title="diagnosticDrawer.title"
  />
</template>

<script lang="ts" setup>
  import { requestFailureMessage, reportLoadError } from '@/utils/load-error'
import { usePagination, useRowKey, useRowSelection } from '@/hooks/table'
import { Message, Modal } from '@arco-design/web-vue'
import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getFormItems } from '@/utils/datacleaning'
import { fieldNames } from '@/setting'
import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { createConditionItems, tableColumns, taskGroupFilterOption, binaryStatusOptions, noticeStatusOptions, taskGroupSyncStatusOptions } from './config'
import { deleteSystemTasks, getSystemTaskExecutionOptions, getScheduledTaskGroupOptions, postSystemTriggerManual, putSystemTasks, updateScheduledTaskGroupMemberStatus } from '@/api/system/tasks'
import { getUserName } from '@/api/user/user'
import { useEnum } from '@/store/modules/get-enum'
import ExecutionSceneTagGrid from '@/components/display/ExecutionSceneTagGrid.vue'
import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
import StickyHorizontalTable from '@/components/table/StickyHorizontalTable.vue'
import TestExecutionModal from '@/components/overlays/TestExecutionModal.vue'
import DiagnosticMarkdownDrawer from '@/components/reports/DiagnosticMarkdownDrawer.vue'
import TaskGroupManager from './components/TaskGroupManager.vue'
import TaskFineTuningModal from './components/TaskFineTuningModal.vue'
import TaskEditorDialog from './components/TaskEditorDialog.vue'
import OfflineReportExportDialog from '@/components/reports/OfflineReportExportDialog.vue'
import TaskRecentResults from './components/TaskRecentResults.vue'
import { formatProjectProductPath, formatModulePath, getEnumTagColor } from '@/utils/business-format'
import type { NavigationCreateSource } from '@/utils/navigation-create-defaults'
import { readTaskEditorCapacity, readTaskEditorOptions, taskEditorId, taskEditorResponse, type TaskEditorId, type TaskEditorOption } from './task-editor-records'
import { readTaskListRecord, taskListId, taskListObject, taskListQuery, type TaskListRecord, type TaskListRecentResult } from './task-list-records'
import { useTaskList } from './composables/useTaskList'

const route = useRoute(), router = useRouter(), user = useUserStore(), permission = usePermissionStore(), enumStore = useEnum(), pagePath = route.path
let mounted = false, active = true, disposed = false, paused = false, contextVersion = 0
const identity = () => JSON.stringify([route.path, route.fullPath, user.userId, user.roleId, user.token, user.selected_environment, permission.permissionKeys])
const identityKey = computed(identity)
const available = () => mounted && active && !disposed && route.path === pagePath && document.visibilityState === 'visible'
function captureContext() {
  const version = contextVersion, key = identity()
  return () => available() && version === contextVersion && key === identity()
}
const navigationCreateRef = ref<NavigationCreateSource | null>(null)
const taskGroupRef = ref<InstanceType<typeof TaskGroupManager> | null>(null), fineTuningRef = ref<InstanceType<typeof TaskFineTuningModal> | null>(null)
const taskEditorRef = ref<InstanceType<typeof TaskEditorDialog> | null>(null), triggerModalRef = ref<InstanceType<typeof TestExecutionModal> | null>(null)
const conditionItems = createConditionItems(), activeTab = ref<'tasks' | 'groups'>('tasks')
const navigationProjectProductId = ref<TaskEditorId | null>(null), sidebarResetKey = ref(0), sidebarModuleIds = ref<TaskEditorId[]>([]), sidebarSelectedModuleId = ref<TaskEditorId | null>(null)
const headerConditionItems = computed(() => conditionItems.filter(item => !['project_product', 'module'].includes(item.key)))
const taskGroupFilters = reactive({ navigation_module_ids: [] as TaskEditorId[], navigation_module_id: null as TaskEditorId | null, name: '', test_envs: [] as number[], case_types: [] as number[], execution_scenes: [] as string[], status: null as number | null, is_notice: null as number | null, sync_status: null as string | null })
const pagination = usePagination(doRefresh, () => list.loading)
const list = useTaskList({ available: () => available() && activeTab.value === 'tasks', capture: captureContext,
  query: () => taskListQuery(getFormItems(conditionItems), pagination.page, pagination.pageSize, sidebarSelectedModuleId.value, sidebarModuleIds.value), pagination })
const { rows, loading: listLoading, error: listError, recentResults, recentLoading: recentResultsLoading, recentError } = list
const { onSelectionChange } = useRowSelection(), rowKey = useRowKey('id')
const userOptions = ref<TaskEditorOption[]>([]), usersLoading = ref(false), usersError = ref('')
const taskGroupOptionsLoading = ref(false), taskGroupOptionsError = ref(''), executionOptionsLoading = ref(false), executionOptionsError = ref(''), apiPlatformLimit = ref(1)
const enumsLoading = ref(false), enumsError = ref(''), operationError = ref('')
let userVersion = 0, groupVersion = 0, capacityVersion = 0, enumVersion = 0, preparationVersion = 0
const triggerPreparingId = ref<TaskEditorId | null>(null), finePreparingId = ref<TaskEditorId | null>(null)
const triggerTarget = ref<TaskListRecord | null>(null), triggerSaving = ref(false), triggerError = ref('')
let triggerVersion = 0, retentionVersion = 0
const writeIds = ref<string[]>([]), statusSavingIds = ref<string[]>([]), deletingIds = ref<string[]>([])
const retentionSaving = ref(false), retentionError = ref('')
const retentionEditor = reactive({ visible: false, record: null as { id: TaskEditorId; name: string } | null, value: 'all' })
const offlineExport = reactive({ visible: false, sourceId: '' as TaskEditorId })
const diagnosticDrawer = reactive({ visible: false, targetId: '' as TaskEditorId, documentAvailable: false, title: '定时任务排查结果' })
let confirmation: ReturnType<typeof Modal.confirm> | null = null, confirmationVersion = 0
const selectableSceneOptions = computed(() => (enumStore.automation_execution_scene || []).filter(item => !['unclassified', 'effectiveness_test'].includes(String(item.key))))
const executionScopeFilterOptions = computed(() => (enumStore.automation_execution_scope || []).filter(item => ['manual', 'full_product', 'module'].includes(String(item.key))))
const taskCaseTypeOptions = computed(() => (enumStore.test_case_type || []).map(item => ({ ...item, disabled: [3, 4].includes(Number(item.key)) })))
const taskGroupSceneOptions = computed(() => (enumStore.automation_execution_scene || []).filter(item => !['unclassified', 'effectiveness_test', 'temporary_validation', 'performance_test'].includes(String(item.key))))

function isTaskBusy(id: TaskEditorId) { return writeIds.value.includes(String(id)) }
function acquire(id: TaskEditorId) { if (isTaskBusy(id)) return false; writeIds.value.push(String(id)); return true }
function release(id: TaskEditorId) { writeIds.value = writeIds.value.filter(value => value !== String(id)) }
function getConditionValue(key: string) { return taskEditorId(conditionItems.find(item => item.key === key)?.value) }
function setConditionValue(key: string, value: unknown) { const item = conditionItems.find(item => item.key === key); if (item) item.value = value }
function optionTitle(options: TaskEditorOption[] | null | undefined, key: TaskEditorId) { return options?.find(item => String(item.key) === String(key))?.title || '未分类' }
function timingStrategiesText(strategies: TaskListRecord['timing_strategies']) { return strategies.map(item => item.name).filter(Boolean).join('、') || '-' }
function timingStrategiesTooltip(strategies: TaskListRecord['timing_strategies']) { return strategies.length ? strategies.map(item => item.cron ? `${item.name}（Cron：${item.cron}）` : item.name).join('\n') : '未配置定时器' }
function optionTagColor(options: TaskEditorOption[] | null, value: TaskEditorId) { return getEnumTagColor(options, value, enumStore.colors) }
function doRefresh() { return list.load() }
function onWorkbenchSearch() {
  if (activeTab.value === 'tasks') { pagination.page = 1; return doRefresh() }
  return taskGroupRef.value?.applyFilters()
}
function resetGroupFilters() {
  Object.assign(taskGroupFilters, { navigation_module_ids: [], navigation_module_id: null, name: '', test_envs: [], case_types: [], execution_scenes: [], status: null, is_notice: null, sync_status: null })
}
function onResetSearch() {
  if (activeTab.value === 'groups') {
    const modules = taskGroupFilters.navigation_module_ids.slice(), module = taskGroupFilters.navigation_module_id
    resetGroupFilters(); taskGroupFilters.navigation_module_ids = modules; taskGroupFilters.navigation_module_id = module
    return taskGroupRef.value?.applyFilters()
  }
  conditionItems.forEach(item => item.reset?.())
  sidebarModuleIds.value = []; sidebarSelectedModuleId.value = null; navigationProjectProductId.value = null
  resetGroupFilters(); sidebarResetKey.value++; pagination.page = 1
  void loadTaskGroupOptions(); return doRefresh()
}
function onSidebarFilterChange(filter: { projectProduct: unknown; module?: unknown; moduleIds?: TaskEditorId[]; selectedModuleId?: TaskEditorId | null }) {
  const product = taskEditorId(filter.projectProduct), previous = navigationProjectProductId.value
  closeWindows()
  navigationProjectProductId.value = product
  if (previous !== product) { setConditionValue('task_group', []); void loadTaskGroupOptions() }
  setConditionValue('project_product', product); setConditionValue('module', taskEditorId(filter.module))
  sidebarModuleIds.value = (filter.moduleIds || []).map(taskListId); sidebarSelectedModuleId.value = taskEditorId(filter.selectedModuleId)
  taskGroupFilters.navigation_module_ids = sidebarModuleIds.value.slice(); taskGroupFilters.navigation_module_id = sidebarSelectedModuleId.value
  pagination.page = 1
  if (activeTab.value === 'tasks') return doRefresh()
}
function filterTasksByGroup(value: unknown) {
  const record = taskListObject(value), id = taskListId(record.id), name = typeof record.name === 'string' ? record.name : `ID ${id}`
  const item = conditionItems.find(item => item.key === 'task_group')
  if (item && !item.optionItems?.some(option => String(option.value) === String(id))) item.optionItems = [...(item.optionItems || []), taskGroupFilterOption(id, name)]
  setConditionValue('task_group', [id]); pagination.page = 1
  if (activeTab.value === 'tasks') return doRefresh()
  activeTab.value = 'tasks'
}
function openRecordModuleConfig(record: TaskListRecord) {
  if (record.project_product === null) { Message.error('当前任务缺少项目产品，无法打开任务组'); return }
  navigationProjectProductId.value = record.project_product.id; activeTab.value = 'groups'
}
async function getNickName() {
  if (!available()) return false
  const version = ++userVersion, valid = captureContext(); usersLoading.value = true; usersError.value = ''
  try { const values = readTaskEditorOptions(taskEditorResponse(await getUserName())); if (version !== userVersion || !valid()) return false; userOptions.value = values; return true }
  catch (loadFailure0) { if (version === userVersion && valid()) (reportLoadError(loadFailure0, "负责人加载失败", false), usersError.value = '负责人加载失败'); return false }
  finally { if (version === userVersion) usersLoading.value = false }
}
async function loadTaskGroupOptions() {
  if (!available()) return false
  const product = navigationProjectProductId.value, version = ++groupVersion, valid = captureContext()
  const current = () => version === groupVersion && valid() && product === navigationProjectProductId.value
  taskGroupOptionsLoading.value = true; taskGroupOptionsError.value = ''
  try {
    const options = readTaskEditorOptions(taskEditorResponse(await getScheduledTaskGroupOptions(product)))
    if (!current()) return false
    const item = conditionItems.find(item => item.key === 'task_group')
    if (item) {
      const selected = Array.isArray(item.value) ? item.value : []
      const previous = item.optionItems || [], values = options.map(option => taskGroupFilterOption(option.key, option.title))
      for (const value of selected) if (!values.some(option => String(option.key) === String(value))) {
        const id = taskListId(value), old = previous.find(option => String(option.value) === String(id))
        values.push(taskGroupFilterOption(id, old?.label || `ID ${id}`))
      }
      item.optionItems = values
    }
    return true
  } catch (loadFailure1) { if (current()) (reportLoadError(loadFailure1, "任务组选项加载失败", false), taskGroupOptionsError.value = '任务组选项加载失败'); return false }
  finally { if (version === groupVersion) taskGroupOptionsLoading.value = false }
}
async function loadEnums() {
  if (!available()) return
  const version = ++enumVersion, valid = captureContext(); enumsLoading.value = true; enumsError.value = ''
  try { await enumStore.getEnum() }
  catch (loadFailure2) { if (version === enumVersion && valid()) (reportLoadError(loadFailure2, "枚举加载失败", false), enumsError.value = '枚举加载失败') }
  finally { if (version === enumVersion) enumsLoading.value = false }
}
async function loadExecutionOptions() {
  if (!available()) return false
  const version = ++capacityVersion, valid = captureContext(); executionOptionsLoading.value = true; executionOptionsError.value = ''
  try {
    const limit = readTaskEditorCapacity(taskEditorResponse(await getSystemTaskExecutionOptions()))
    if (version !== capacityVersion || !valid()) return false
    apiPlatformLimit.value = limit; return true
  } catch (loadFailure3) { if (version === capacityVersion && valid()) (reportLoadError(loadFailure3, "执行容量加载失败，请重新打开操作重试", false), executionOptionsError.value = '执行容量加载失败，请重新打开操作重试'); return false }
  finally { if (version === capacityVersion) executionOptionsLoading.value = false }
}
function cancelPreparation() {
  preparationVersion++; capacityVersion++; executionOptionsLoading.value = false
  triggerPreparingId.value = null; finePreparingId.value = null
}
function openTaskGroupCreate() {
  if (available()) taskGroupRef.value?.openCreate(navigationCreateRef.value?.getCreateDefaults().module)
}
function onAdd() { if (!available()) return; cancelPreparation(); void taskEditorRef.value?.openCreate(navigationCreateRef.value?.getCreateDefaults()) }
function onUpdate(record: TaskListRecord) { void taskEditorRef.value?.openEdit(record) }
async function onEdit(record: TaskListRecord) {
  if (!available() || isTaskBusy(record.id)) return
  cancelPreparation()
  if (record.task_group === null) { onUpdate(record); return }
  const target = readTaskListRecord(record), version = preparationVersion, valid = captureContext()
  finePreparingId.value = target.id
  try { if (await loadExecutionOptions() && version === preparationVersion && valid()) fineTuningRef.value?.open(target) }
  finally { if (version === preparationVersion) finePreparingId.value = null }
}
async function onTrigger(record: TaskListRecord) {
  if (!available() || triggerSaving.value || isTaskBusy(record.id)) return
  cancelPreparation(); onCancelTrigger()
  const target = readTaskListRecord(record), version = preparationVersion, valid = captureContext()
  triggerPreparingId.value = target.id
  try {
    if (!await loadExecutionOptions() || version !== preparationVersion || !valid()) return
    triggerVersion++; triggerTarget.value = target; triggerError.value = ''
    await triggerModalRef.value?.show({ executionName: target.name || `定时任务 ID ${target.id}`, testEnv: null, testEnvs: target.test_envs.slice(), apiConcurrencyLimit: null })
  } finally { if (version === preparationVersion) triggerPreparingId.value = null }
}
function onCancelTrigger() { triggerVersion++; triggerTarget.value = null; triggerError.value = ''; void triggerModalRef.value?.close() }
async function onConfirmTrigger(config: { executionName: string; testEnv: number | null; testEnvs?: number[]; apiConcurrencyLimit: number | null }) {
  if (!available() || triggerSaving.value || !triggerTarget.value) return false
  const target = triggerTarget.value, id = target.id, version = triggerVersion, key = identity(), valid = captureContext()
  const current = () => version === triggerVersion && valid() && triggerTarget.value?.id === id
  if (!acquire(id)) { triggerModalRef.value?.setConfirmLoading(false); return false }
  const envs = config.testEnvs?.slice(), concurrency = config.apiConcurrencyLimit
  triggerSaving.value = true; triggerError.value = ''; let committed = false
  try {
    taskEditorResponse(await postSystemTriggerManual(id, concurrency, envs)); committed = true
    if (current()) { onCancelTrigger(); Message.success('任务已触发') }
    return true
  } catch (requestFailure) { if (current()) triggerError.value = requestFailureMessage(requestFailure, '任务触发失败，请重试'); return false }
  finally { triggerSaving.value = false; release(id); if (version === triggerVersion) triggerModalRef.value?.setConfirmLoading(false); if (committed) refreshAfterWrite(key) }
}
function closeConfirmation() { confirmationVersion++; confirmation?.close(); confirmation = null }
function onDelete(record: TaskListRecord) {
  if (!available() || isTaskBusy(record.id) || record.task_group !== null) return
  closeConfirmation()
  const id = record.id, version = confirmationVersion, key = identity(), valid = captureContext()
  const current = () => version === confirmationVersion && valid()
  confirmation = Modal.confirm({ title: '提示', content: '是否要删除此定时任务？', cancelText: '取消', okText: '删除',
    onCancel: () => { if (version === confirmationVersion) closeConfirmation() },
    onBeforeOk: async () => {
      if (!current() || !acquire(id)) return false
      deletingIds.value.push(String(id)); operationError.value = ''; let committed = false
      try {
        taskEditorResponse(await deleteSystemTasks(id)); committed = true
        if (!current()) return false
        closeConfirmation(); Message.success('任务已删除'); return true
      } catch (requestFailure) { if (current()) operationError.value = requestFailureMessage(requestFailure, '任务删除失败，请重试'); return false }
      finally { release(id); deletingIds.value = deletingIds.value.filter(value => value !== String(id)); if (committed) refreshAfterWrite(key) }
    },
  })
}
function closeRetention() { retentionVersion++; Object.assign(retentionEditor, { visible: false, record: null, value: 'all' }); retentionError.value = '' }
function openRetentionEditor(record: TaskListRecord) {
  if (!available() || retentionSaving.value || isTaskBusy(record.id)) return
  closeRetention(); Object.assign(retentionEditor, { visible: true, record: { id: record.id, name: record.name }, value: record.report_retention_policy })
}
async function saveRetentionPolicy() {
  if (!available() || retentionSaving.value || !retentionEditor.visible || !retentionEditor.record) return false
  const id = retentionEditor.record.id, value = retentionEditor.value, version = retentionVersion, key = identity(), valid = captureContext()
  const current = () => version === retentionVersion && valid() && retentionEditor.visible
  if (!value) { retentionError.value = '请选择报告保留策略'; return false }
  if (!acquire(id)) return false
  retentionSaving.value = true; retentionError.value = ''; let committed = false
  try {
    taskEditorResponse(await putSystemTasks({ id, report_retention_policy: value })); committed = true
    if (!current()) return false
    replaceTaskRow(id, { report_retention_policy: value }); closeRetention(); Message.success('报告保留策略已保存，下次执行生效'); return true
  } catch (requestFailure) { if (current()) retentionError.value = requestFailureMessage(requestFailure, '保留策略保存失败，请重试'); return false }
  finally { release(id); retentionSaving.value = false; if (committed) refreshAfterWrite(key) }
}
function replaceTaskRow(id: TaskEditorId, changes: Partial<TaskListRecord>) { rows.value = rows.value.map(row => String(row.id) === String(id) ? { ...row, ...changes } : row) }
async function onModifyStatus(newValue: unknown, record: TaskListRecord, field: 'status' | 'is_notice' | 'fail_notice') {
  if (!available() || (record.task_group !== null && field !== 'status') || (field === 'fail_notice' && record.is_notice !== 1) || !acquire(record.id)) return false
  const id = record.id, group = record.task_group, member = record.task_group_member_id, nextValue = newValue ? 1 : 0, key = identity(), valid = captureContext()
  statusSavingIds.value.push(String(id)); operationError.value = ''; let committed = false
  try {
    if (group !== null && member === null) throw Error('Missing group member')
    const data = taskEditorResponse(group !== null && member !== null
      ? await updateScheduledTaskGroupMemberStatus(group, member, Boolean(newValue))
      : await putSystemTasks({ id, [field]: nextValue, ...(field === 'is_notice' && nextValue === 0 ? { fail_notice: 0 } : {}) }))
    committed = true
    let effective = nextValue
    if (group !== null) {
      const enabled = taskListObject(data).effective_enabled
      if (typeof enabled !== 'boolean' && enabled !== 0 && enabled !== 1) throw Error('Invalid group status')
      effective = Number(enabled)
    }
    if (!valid()) return false
    const changes: Partial<TaskListRecord> = { [field]: effective }
    if (field === 'is_notice' && nextValue === 0) changes.fail_notice = 0
    replaceTaskRow(id, changes); Message.success('任务状态已更新'); return true
  } catch (requestFailure) { if (valid()) operationError.value = requestFailureMessage(requestFailure, committed ? '任务状态已提交，但返回结果异常，请刷新核对' : '任务状态修改失败，请重试'); return false }
  finally { release(id); statusSavingIds.value = statusSavingIds.value.filter(value => value !== String(id)); if (committed) refreshAfterWrite(key) }
}
function refreshAfterWrite(key: string) { if (key === identity() && available() && activeTab.value === 'tasks') void doRefresh() }
function openRecentResult(result?: TaskListRecentResult) {
  if (!available() || !result) return
  if (result.report_retained === false) { Message.info('本次执行成功，已按保留策略清理完整报告，仅保留质量统计'); return }
  if (result.test_suite_id === null) { Message.info('当前执行暂无可查看的报告'); return }
  void router.push({ path: '/report/system/details', query: { id: result.test_suite_id } })
}
function onClick(record: TaskListRecord) {
  if (!available() || record.project_product === null) return
  void router.push({ path: '/timing/case', query: { id: record.id, name: record.name, types: record.case_types.join(','), execution_scope: record.execution_scope, project_product_id: record.project_product.id, module_id: record.module?.id ?? '' } })
}
function openTaskDiagnostic(record: TaskListRecord) { if (available()) Object.assign(diagnosticDrawer, { targetId: record.id, documentAvailable: Boolean(record.diagnostic_file_path), title: `${record.name || '定时任务'} · 排查结果`, visible: true }) }
function openOfflineReport(record: TaskListRecord) { if (available()) Object.assign(offlineExport, { sourceId: record.id, visible: true }) }
function closeWindows() {
  cancelPreparation(); onCancelTrigger(); closeRetention(); closeConfirmation()
  taskEditorRef.value?.close(); fineTuningRef.value?.close(); offlineExport.visible = false; diagnosticDrawer.visible = false
}
function invalidate(clear = false) {
  contextVersion++; userVersion++; groupVersion++; enumVersion++; closeWindows(); list.invalidate(clear)
  usersLoading.value = false; taskGroupOptionsLoading.value = false; enumsLoading.value = false
  if (clear) {
    userOptions.value = []; usersError.value = ''; taskGroupOptionsError.value = ''; enumsError.value = ''; executionOptionsError.value = ''; operationError.value = ''
    conditionItems.forEach(item => { item.reset?.(); if (item.key === 'task_group') item.optionItems = [] })
    navigationProjectProductId.value = null; sidebarModuleIds.value = []; sidebarSelectedModuleId.value = null
    resetGroupFilters(); sidebarResetKey.value++; pagination.page = 1
  }
}
function resume() {
  if (!available()) return Promise.resolve([])
  paused = false
  return Promise.allSettled([getNickName(), loadTaskGroupOptions(), loadEnums(), activeTab.value === 'tasks' ? doRefresh() : taskGroupRef.value?.load()])
}
function visibilityChanged() { if (available()) { if (paused) void resume() } else { paused = true; invalidate() } }
watch(identity, () => { invalidate(true); if (available()) void resume() }, { flush: 'sync' })
watch(activeTab, async () => {
  closeWindows(); list.invalidate()
  if (!available()) return
  if (activeTab.value === 'tasks') await doRefresh()
  else { await nextTick(); void taskGroupRef.value?.load() }
})
onMounted(() => { mounted = true; document.addEventListener('visibilitychange', visibilityChanged); void resume() })
onActivated(() => { active = true; if (paused) void resume() })
onDeactivated(() => { active = false; paused = true; invalidate() })
onBeforeUnmount(() => { disposed = true; invalidate(true); document.removeEventListener('visibilitychange', visibilityChanged) })
</script>

<style scoped>
  .mango-task-feedback { display: grid; gap: var(--m-page-gap); }
  .mango-task-feedback:empty { display: none; }
  .mango-timing-task-workbench {
    flex: 1 1 0;
    min-height: 0;
  }

  .mango-timing-task-tabs {
    overflow: hidden;
    flex: none;
  }

  .mango-timing-task-tabs :deep(.arco-tabs-nav-extra) {
    margin-right: var(--m-page-gap);
  }

  .mango-timing-task-tab-title {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .mango-task-timing-strategy {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

</style>
