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
          <a-form v-if="activeTab === 'tasks'" :model="{}" layout="inline" @keyup.enter="doRefresh">
            <a-form-item v-for="item of headerConditionItems" :key="item.key" :label="item.label">
              <template v-if="item.type === 'input'">
                <a-input
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  allow-clear
                  @blur="doRefresh"
                  @clear="doRefresh"
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
                  @change="doRefresh"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'case_people'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="data.userList"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="doRefresh"
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
                  :loading="data.taskGroupOptionsLoading"
                  allow-clear
                  allow-search
                  value-key="key"
                  @change="doRefresh"
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
                  @change="doRefresh"
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
                  @change="doRefresh"
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
                  @change="doRefresh"
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
                  @change="doRefresh"
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
                  @change="doRefresh"
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
                  :loading="data.executionOptionsLoading"
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
        <StickyHorizontalTable v-if="activeTab === 'tasks'" :scroll-x="3090">
          <a-table
            :scroll="{ x: 3090, y: '100%' }"
            :bordered="false"
            :columns="tableColumns"
            :data="table.dataList"
            :loading="table.tableLoading.value"
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
                  <TaskRecentResults
                    :results="data.recentResults[String(record.id)] || []"
                    :loading="data.recentResultsLoading"
                    @open="(index) => openRecentResult(data.recentResults[String(record.id)][index])"
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
                  <a-tag v-if="record.task_group" color="blue" size="small">
                    {{ record.task_group_name }}
                  </a-tag>
                  <span v-else>-</span>
                </template>
                <template v-else-if="item.key === 'status'" #cell="{ record }">
                  <a-switch
                    :model-value="record.status === 1"
                    :beforeChange="(newValue) => onModifyStatus(newValue, record, 'status')"
                  />
                </template>
                <template v-else-if="item.key === 'is_notice'" #cell="{ record }">
                  <a-switch
                    :model-value="record.is_notice === 1"
                    :disabled="Boolean(record.task_group)"
                    :beforeChange="(newValue) => onModifyStatus(newValue, record, 'is_notice')"
                  />
                </template>
                <template v-else-if="item.key === 'fail_notice'" #cell="{ record }">
                  <a-switch
                    :model-value="record.is_notice === 1 && record.fail_notice === 1"
                    :disabled="record.is_notice !== 1 || Boolean(record.task_group)"
                    :beforeChange="(newValue) => onModifyStatus(newValue, record, 'fail_notice')"
                  />
                </template>
                <template v-else-if="item.key === 'report_retention_policy'" #cell="{ record }">
                  <span>{{ enumStore.report_retention_policy.find((option) => option.key === record.report_retention_policy)?.title || '-' }}</span>
                </template>
                <template v-else-if="item.key === 'update_user'" #cell="{ record }">
                  {{ record.update_user?.name || record.update_user?.username || '-' }}
                </template>
                <template v-else-if="item.key === 'actions'" #cell="{ record }">
                  <MangoTableActions
                    :actions="[
    {
        label: '触发',
        loading: data.triggerLoading || data.executionOptionsLoading,
        onClick: () => onTrigger(record), },
    {
        label: record.execution_scope === 'manual'
            ? '添加用例'
            : '匹配用例',
        onClick: () => onClick(record),
    },
    { label: '排查结果', onClick: () => openTaskDiagnostic(record) },
    { label: '导出离线 HTML', onClick: () => { offlineExport.sourceId = record.id; offlineExport.visible = true; } },
    {
        label: '编辑',
        loading: data.executionOptionsLoading,
        onClick: () => onEdit(record), },
    { label: '保留策略', hidden: !record.task_group,
        onClick: () => openRetentionEditor(record) },
    {
        label: '删除',
        danger: true,
        disabled: Boolean(record.task_group),
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
          :project-product-id="navigationProjectProductId"
          :filters="taskGroupFilters"
          @filter-tasks="filterTasksByGroup"
        />
        <template #footer>
          <TableFooter v-if="activeTab === 'tasks'" :pagination="pagination" />
        </template>
      </ProjectProductNavigationWorkbench>
    </template>
  </TableBody>
  <TaskFineTuningModal ref="fineTuningRef"
    :user-options="data.userList" :retention-options="enumStore.report_retention_policy || []"
    :platform-limit="data.apiPlatformLimit" @saved="doRefresh" />
  <ModalDialog
    ref="modalDialogRef"
    :title="data.actionTitle"
    width="min(760px, calc(100vw - 32px))"
    @confirm="onDataForm"
  >
    <template #content>
      <a-form :model="formModel" layout="horizontal" class="mango-task-form">
        <section v-for="group of taskFormGroups" :key="group.key" class="mango-task-form-group">
          <header class="mango-task-form-group__header">
            <strong>{{ group.title }}</strong>
            <span>{{ group.description }}</span>
          </header>
          <div class="mango-task-form-group__fields">
            <a-form-item
              v-for="item of group.items"
              :key="item.key"
              :class="[
                item.required ? 'mango-form-item__require' : 'mango-form-item__no_require',
                { 'mango-task-form-item--wide': ['name', 'module'].includes(item.key) },
              ]"
              :label="item.label"
            >
              <template v-if="item.type === 'input' && item.key === 'trigger_type'">
                <a-input v-model="item.value" :placeholder="item.placeholder" disabled />
              </template>
              <template v-else-if="item.type === 'input' && item.key === 'name'">
                <a-input v-model="item.value" :placeholder="item.placeholder" />
              </template>
              <template v-else-if="item.type === 'number'">
                <a-input-number
                  v-model="item.value"
                  :min="1"
                  :max="data.apiPlatformLimit"
                  :precision="0"
                  :step="1"
                  allow-clear
                  class="full-width"
                  :placeholder="item.placeholder"
                />
              </template>
              <template v-else-if="item.type === 'cascader'">
                <ProjectProductSelect
                  v-model="item.value"
                  :placeholder="item.placeholder"
                  @change="onFormProjectChange(item.value)"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'module'">
                <ProductModuleLevelSelect
                  v-if="getFormValue('project_product')"
                  v-model="item.value"
                  :auto-clear="false"
                  :project-product-id="getFormValue('project_product')"
                  :disabled="getFormValue('execution_scope') === 'full_product'"
                />
                <a-input v-else disabled placeholder="请先选择项目 / 产品" />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'timing_strategies'">
                <a-select
                  v-model="item.value"
                  multiple
                  :max-tag-count="1"
                  :field-names="fieldNames"
                  :options="data.timingList"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'notice_group'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :options="data.noticeList"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
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
                  value-key="key"
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
                />
              </template>
              <template v-else-if="item.key === 'report_retention_policy'">
                <a-select v-model="item.value" :field-names="fieldNames" :options="enumStore.report_retention_policy" />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'execution_scope'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="selectableScopeOptions"
                  :placeholder="item.placeholder"
                />
              </template>
              <template v-else-if="item.type === 'select' && item.key === 'case_people'">
                <a-select
                  v-model="item.value"
                  :multiple="item.multiple"
                  :max-tag-count="item.multiple ? 1 : undefined"
                  :field-names="fieldNames"
                  :options="data.userList"
                  :placeholder="item.placeholder"
                  allow-clear
                  allow-search
                  value-key="key"
                />
              </template>

              <template v-else-if="item.type === 'select' && item.key === 'case_executor'">
                <a-select v-model="item.value" :placeholder="item.placeholder" multiple>
                  <a-option v-for="user of data.userList" :key="user.key">{{
                    user.title
                  }}</a-option>
                </a-select>
              </template>
              <template v-else-if="item.type === 'switch' && item.key === 'status'">
                <a-switch v-model="item.value" :checked-value="1" :unchecked-value="0" />
              </template>
            </a-form-item>
          </div>
          <div v-if="group.key === 'execution'" class="mango-task-classification-summary">
            <span>当前规则</span>
            <strong>{{ taskClassificationSummary }}</strong>
          </div>
        </section>
      </a-form>
    </template>
  </ModalDialog>
  <TestExecutionModal
    ref="triggerModalRef"
    title="触发定时任务"
    :platform-limit="data.apiPlatformLimit"
    environment-selectable
    environment-multiple
    environment-placeholder="请选择本次临时执行环境"
    environment-hint="默认使用任务配置；可临时改选其他环境，每个环境分别创建一份报告，不会修改定时任务"
    concurrency-placeholder="留空则使用定时任务配置"
    concurrency-hint="留空则使用定时任务配置，本次修改不会回写定时任务"
    @confirm="onConfirmTrigger"
    @cancel="onCancelTrigger"
  />
  <a-modal v-model:visible="retentionEditor.visible" title="报告保留策略" :width="520"
    :mask-closable="false" :closable="!retentionSavingIds.length"
    :cancel-button-props="{ disabled: !!retentionSavingIds.length }" :ok-loading="!!retentionSavingIds.length"
    @before-ok="saveRetentionPolicy(retentionEditor.record, retentionEditor.value)">
    <a-form :model="retentionEditor" layout="horizontal">
      <a-form-item label="任务名称">{{ retentionEditor.record?.name }}</a-form-item>
      <a-form-item label="保留策略">
        <a-select v-model="retentionEditor.value" :field-names="fieldNames" :options="enumStore.report_retention_policy"
          :disabled="!!retentionSavingIds.length" />
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
  import { usePagination, useRowKey, useRowSelection, useTable } from '@/hooks/table'
  import { useLatestRequest } from '@/hooks/use-latest-request'
  import { ModalDialogType } from '@/types/components'
  import { Message, Modal } from '@arco-design/web-vue'
  import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
  import { getFormItems } from '@/utils/datacleaning'
  import { fieldNames } from '@/setting'

  import { useRouter } from 'vue-router'
  import { conditionItems, formItems, tableColumns } from './config'
  import {
    deleteSystemTasks,
    getSystemTasks,
    getSystemTaskExecutionOptions,
    getSystemTaskRecentResults,
    getScheduledTaskGroupOptions,
    postSystemTriggerManual,
    postSystemTasks,
    putSystemTasks,
    updateScheduledTaskGroupMemberStatus,
  } from '@/api/system/tasks'
  import { getSystemTimingList } from '@/api/system/time'
  import { getUserName } from '@/api/user/user'
  import { useEnum } from '@/store/modules/get-enum'
  import { getSystemNoticeName } from '@/api/system/notice_group'
  import ProjectProductSelect from '@/components/business/ProjectProductSelect.vue'
  import ExecutionSceneTagGrid from '@/components/display/ExecutionSceneTagGrid.vue'
  import ProductModuleLevelSelect from '@/components/business/ProductModuleLevelSelect.vue'
  import ProjectProductNavigationWorkbench from '@/components/business/ProjectProductNavigationWorkbench.vue'
  import StickyHorizontalTable from '@/components/table/StickyHorizontalTable.vue'
  import TestExecutionModal from '@/components/overlays/TestExecutionModal.vue'
  import DiagnosticMarkdownDrawer from '@/components/reports/DiagnosticMarkdownDrawer.vue'
  import TaskGroupManager from './components/TaskGroupManager.vue'
  import TaskFineTuningModal from './components/TaskFineTuningModal.vue'
  import OfflineReportExportDialog from '@/components/reports/OfflineReportExportDialog.vue'
  import TaskRecentResults from './components/TaskRecentResults.vue'
  import type { TaskRecentResult } from '@/api/system/tasks'
  import {
    formatProjectProductPath,
    formatModulePath,
    getEnumTagColor,
    getOptionId,
  } from '@/utils/business-format'
  import { prefillNavigationFormItems, NavigationCreateSource } from '@/utils/navigation-create-defaults'

  const navigationCreateRef = ref<NavigationCreateSource | null>(null)

  const enumStore = useEnum()

  const activeTab = ref<'tasks' | 'groups'>('tasks')
  const taskGroupRef = ref<InstanceType<typeof TaskGroupManager> | null>(null)
  const fineTuningRef = ref<InstanceType<typeof TaskFineTuningModal> | null>(null)
  const offlineExport = reactive({ visible: false, sourceId: 0 })
  const navigationProjectProductId = ref<number | null>(null)
  const taskGroupFilters = reactive({
    navigation_module_ids: [] as number[],
    navigation_module_id: null as number | null,
    name: '',
    test_envs: [] as number[],
    case_types: [] as number[],
    execution_scenes: [] as string[],
    status: null as number | null,
    is_notice: null as number | null,
    sync_status: null as string | null,
  })
  const binaryStatusOptions = [
    { label: '已开启', value: 1 },
    { label: '已关闭', value: 0 },
  ]
  const noticeStatusOptions = [
    { label: '通知', value: 1 },
    { label: '不通知', value: 0 },
  ]
  const taskGroupSyncStatusOptions = [
    { label: '已同步', value: 'synced' },
    { label: '待同步', value: 'pending' },
    { label: '同步失败', value: 'failed' },
  ]

  function openTaskGroupCreate() {
    taskGroupRef.value?.openCreate(navigationCreateRef.value?.getCreateDefaults().module)
  }

  function filterTasksByGroup(record: any) {
    const taskGroupCondition = conditionItems.find((item) => item.key === 'task_group')
    if (
      taskGroupCondition &&
      !taskGroupCondition.optionItems?.some((item: any) => Number(item.key) === Number(record.id))
    ) {
      taskGroupCondition.optionItems = [
        ...(taskGroupCondition.optionItems || []),
        { key: record.id, title: record.name },
      ]
    }
    setConditionValue('task_group', record.id)
    pagination.page = 1
    activeTab.value = 'tasks'
  }

  function openRecordModuleConfig(record: any) {
    const projectProductId = getOptionId(record.project_product) || record.project_product_id
    if (!projectProductId) {
      Message.error('当前任务缺少项目产品，无法打开任务组')
      return
    }
    navigationProjectProductId.value = Number(projectProductId)
    activeTab.value = 'groups'
  }

  async function onEdit(record: any) {
    if (!record.task_group) {
      void onUpdate(record)
      return
    }
    if (!(await loadExecutionOptions())) return
    fineTuningRef.value?.open(record)
  }
  const productionScenes = [
    'stability_monitoring',
    'production_inspection',
    'production_regression',
  ]
  const selectableSceneOptions = computed(() => {
    const testEnvs = getFormArrayValue('test_envs').map(Number)
    const options = (enumStore.automation_execution_scene || []).filter(
      (item) => !['unclassified', 'effectiveness_test'].includes(String(item.key))
    )
    if (getFormValue('execution_scope') === 'manual') {
      const isProductionOnly = testEnvs.length > 0 && testEnvs.every((value) => value === 2)
      return options.filter((item) => item.key !== 'stability_monitoring' || isProductionOnly)
    }
    if (!testEnvs.length) return options
    const hasProduction = testEnvs.includes(2)
    const hasNonProduction = testEnvs.some((value) => value !== 2)
    if (hasProduction && hasNonProduction) return options
    return options.filter((item) => {
      const scene = String(item.key)
      if (hasProduction) return productionScenes.includes(scene)
      return scene !== 'stability_monitoring'
    })
  })
  const selectableScopeOptions = computed(() =>
    (enumStore.automation_execution_scope || [])
      .filter((item) => ['manual', 'full_product', 'module'].includes(String(item.key)))
      .map((item) => {
        const isModuleScope = item.key === 'module'
        const scenes = getExecutionScenes()
        const testEnvs = getFormArrayValue('test_envs').map(Number)
        const isProductionOnly = testEnvs.length > 0 && testEnvs.every((value) => value === 2)
        const productionDynamicAllowed =
          scenes.length > 0 && scenes.every((scene) => productionScenes.includes(scene))
        return {
          ...item,
          title: isModuleScope ? `${item.title}（请前往任务组创建）` : item.title,
          disabled:
            isModuleScope ||
            (isProductionOnly && item.key !== 'manual' && !productionDynamicAllowed),
        }
      })
  )
  const executionScopeFilterOptions = computed(() =>
    (enumStore.automation_execution_scope || []).filter((item) =>
      ['manual', 'full_product', 'module'].includes(String(item.key))
    )
  )
  const taskCaseTypeOptions = computed(() =>
    (enumStore.test_case_type || []).map((item) => ({
      ...item,
      disabled: [3, 4].includes(Number(item.key)),
    }))
  )
  const taskGroupSceneOptions = computed(() =>
    (enumStore.automation_execution_scene || []).filter(
      (item) =>
        ![
          'unclassified',
          'effectiveness_test',
          'temporary_validation',
          'performance_test',
        ].includes(String(item.key))
    )
  )
  const showApiConcurrency = computed(() => {
    const caseTypes = formItems.find((item) => item.key === 'case_types')?.value
    if (!Array.isArray(caseTypes) || caseTypes.length === 0) return true
    return caseTypes.some((value) => Number(value) === 1)
  })
  const taskFormGroups = computed(() => {
    const itemMap = new Map(formItems.map((item) => [item.key, item]))
    return [
      {
        key: 'basic',
        title: '基础信息',
        description: '设置任务名称及所属产品、模块',
        itemKeys: ['name', 'project_product', 'module'],
      },
      {
        key: 'execution',
        title: '执行规则',
        description: '设置触发策略、运行环境、执行场景与用例匹配范围',
        itemKeys: [
          'timing_strategies',
          'test_envs',
          'execution_scenes',
          'execution_scope',
          'case_types',
          'api_concurrency_limit',
          'report_retention_policy',
        ],
      },
      {
        key: 'management',
        title: '责任与通知',
        description: '设置任务负责人和结果通知对象',
        itemKeys: ['case_people', 'notice_group'],
      },
    ].map((group) => ({
      ...group,
      items: group.itemKeys.flatMap((key) => {
        if (key === 'api_concurrency_limit' && !showApiConcurrency.value) return []
        const item = itemMap.get(key)
        return item ? [item] : []
      }),
    }))
  })
  const taskClassificationSummary = computed(() => {
    const scenes = getExecutionScenes()
    const scope = getFormValue('execution_scope')
    const module = getFormValue('module')
    const caseTypes = (formItems.find((item) => item.key === 'case_types')?.value || []) as number[]
    const sceneName = scenes.length
      ? scenes.map((scene) => optionTitle(enumStore.api_case_scenario_tag, scene)).join('、')
      : '待选择执行场景'
    const scopeName = scope
      ? optionTitle(enumStore.automation_execution_scope, scope)
      : '待选择执行范围'
    const moduleHint = scope === 'module' ? (module ? ' · 已选择模块' : ' · 待选择模块') : ''
    const caseTypeName =
      Array.isArray(caseTypes) && caseTypes.length
        ? caseTypes.map((value: number) => optionTitle(enumStore.test_case_type, value)).join('、')
        : '全部类型'
    return `${caseTypeName} · ${sceneName} · ${scopeName}${moduleHint}`
  })
  const diagnosticDrawer = reactive({
    visible: false,
    targetId: '' as number | string,
    documentAvailable: false,
    title: '定时任务排查结果',
  })

  function openTaskDiagnostic(record: any) {
    diagnosticDrawer.targetId = record.id
    diagnosticDrawer.documentAvailable = Boolean(record.diagnostic_file_path)
    diagnosticDrawer.title = `${record.name || '定时任务'} · 排查结果`
    diagnosticDrawer.visible = true
  }

  function optionTitle(options: any[] | null, key: string | number) {
    return options?.find((item) => item.key === key)?.title || '未分类'
  }

  function timingStrategiesText(strategies: any[]) {
    if (!Array.isArray(strategies) || !strategies.length) return '-'
    return (
      strategies
        .map((item) => item.name)
        .filter(Boolean)
        .join('、') || '-'
    )
  }

  function timingStrategiesTooltip(strategies: any[]) {
    if (!Array.isArray(strategies) || !strategies.length) return '未配置定时器'
    return strategies
      .map((item) => (item.cron ? `${item.name}（Cron：${item.cron}）` : item.name))
      .join('\n')
  }

  function optionTagColor(
    options: Array<{ key: string | number; title: string }> | null,
    value: string | number
  ) {
    return getEnumTagColor(options, value, enumStore.colors)
  }

  const modalDialogRef = ref<ModalDialogType | null>(null)
  const triggerModalRef = ref<InstanceType<typeof TestExecutionModal> | null>(null)
  const pagination = usePagination(doRefresh, () => table.tableLoading)
  const { onSelectionChange } = useRowSelection()
  const table = useTable()
  const { beginRequest, isLatestRequest } = useLatestRequest()
  const { beginRequest: beginRecentRequest, isLatestRequest: isLatestRecentRequest } =
    useLatestRequest()
  const sidebarResetKey = ref(0)
  const sidebarModuleIds = ref<Array<string | number>>([])
  const sidebarSelectedModuleId = ref<string | number | null>(null)
  const headerConditionItems = computed(() =>
    conditionItems.filter((item) => !['project_product', 'module'].includes(item.key))
  )
  const rowKey = useRowKey('id')
  const router = useRouter()

  const data = reactive({
    isAdd: false,
    updateId: 0,
    actionTitle: '新增',
    triggerLoading: false,
    triggerRecord: null as any,
    apiPlatformLimit: 1,
    executionOptionsLoading: false,
    taskGroupOptionsLoading: false,
    isHydratingForm: false,
    userList: [],
    timingList: [],
    noticeList: [],
    recentResults: {} as Record<string, TaskRecentResult[]>,
    recentResultsLoading: false,
  })

  const formModel = ref({})
  watch(
    () => getFormValue('execution_scope'),
    (scope) => {
      if (scope === 'full_product' && getFormValue('module')) {
        setFormValue('module', '')
      }
      if (!data.isHydratingForm) syncExecutionScenesWithOptions()
    }
  )
  watch(
    () => getFormArrayValue('test_envs'),
    () => {
      if (data.isHydratingForm) return
      syncExecutionScenesWithOptions()
    }
  )
  watch(showApiConcurrency, (visible) => {
    if (!visible) setFormValue('api_concurrency_limit', null)
  })

  function syncExecutionScenesWithOptions() {
    const allowedScenes = new Set(selectableSceneOptions.value.map((item) => String(item.key)))
    const scenes = getExecutionScenes()
    const nextScenes = scenes.filter((scene) => allowedScenes.has(scene))
    if (nextScenes.length !== scenes.length) {
      setFormValue('execution_scenes', nextScenes)
    }
  }

  function doRefresh() {
    const requestId = beginRequest()
    beginRecentRequest()
    data.recentResults = {}
    data.recentResultsLoading = false
    table.tableLoading.value = true
    let value = getFormItems(conditionItems)
    value['project_product'] = getOptionId(value['project_product'])
    if (value['project_product'] === null || value['project_product'] === '') {
      delete value['project_product']
    }
    value['module'] = getOptionId(value['module'])
    if (value['module'] === null || value['module'] === '') {
      delete value['module']
    }
    if (sidebarSelectedModuleId.value !== null) {
      value['module'] = sidebarSelectedModuleId.value
      delete value['module__in']
    } else if (sidebarModuleIds.value.length) {
      delete value['module']
      value['module__in'] = sidebarModuleIds.value.join(',')
    }
    if (value['case_people'] === null || value['case_people'] === '') {
      delete value['case_people']
    }
    value['task_group'] = getOptionId(value['task_group'])
    if (value['task_group'] === null || value['task_group'] === '') {
      delete value['task_group']
    }
    value['page'] = pagination.page
    value['pageSize'] = pagination.pageSize
    getSystemTasks(value)
      .then((res) => {
        if (!isLatestRequest(requestId)) return
        table.handleSuccess(res)
        pagination.setTotalSize((res as any).totalSize)
        loadRecentResults(Array.isArray(res.data) ? res.data : [])
      })
      .catch((error) => {
        if (isLatestRequest(requestId)) console.log(error)
      })
      .finally(() => {
        if (isLatestRequest(requestId)) table.tableLoading.value = false
      })
  }

  function loadRecentResults(records: any[]) {
    const requestId = beginRecentRequest()
    const taskIds = records.map((item) => item.id).filter(Boolean)
    data.recentResults = {}
    if (!taskIds.length) {
      data.recentResultsLoading = false
      return
    }
    data.recentResultsLoading = true
    getSystemTaskRecentResults(taskIds)
      .then((res) => {
        if (!isLatestRecentRequest(requestId)) return
        data.recentResults = res.data || {}
      })
      .catch((error) => {
        if (isLatestRecentRequest(requestId)) console.log(error)
      })
      .finally(() => {
        if (isLatestRecentRequest(requestId)) data.recentResultsLoading = false
      })
  }

  function openRecentResult(result: TaskRecentResult) {
    if (result.report_retained === false) {
      Message.info('本次执行成功，已按保留策略清理完整报告，仅保留质量统计')
      return
    }
    router.push({
      path: '/report/system/details',
      query: { id: result.test_suite_id },
    })
  }

  function onSidebarFilterChange(filter: {
    projectProduct: any
    module?: any
    moduleIds?: Array<string | number>
    selectedModuleId?: string | number | null
  }) {
    const previousProjectProductId = navigationProjectProductId.value
    const projectProductId = Number(getOptionId(filter.projectProduct))
    navigationProjectProductId.value =
      Number.isInteger(projectProductId) && projectProductId > 0 ? projectProductId : null
    if (previousProjectProductId !== navigationProjectProductId.value) {
      setConditionValue('task_group', '')
      void loadTaskGroupOptions(navigationProjectProductId.value)
    }
    setConditionValue('project_product', filter.projectProduct)
    setConditionValue('module', filter.module ?? '')
    sidebarModuleIds.value = filter.moduleIds || []
    sidebarSelectedModuleId.value = filter.selectedModuleId ?? null
    taskGroupFilters.navigation_module_ids = (filter.moduleIds || []).map(Number)
    taskGroupFilters.navigation_module_id = filter.selectedModuleId
      ? Number(filter.selectedModuleId)
      : null
    pagination.page = 1
    if (activeTab.value === 'tasks') doRefresh()
  }

  function onWorkbenchSearch() {
    if (activeTab.value === 'tasks') {
      doRefresh()
      return
    }
    taskGroupRef.value?.applyFilters()
  }

  function onResetSearch() {
    if (activeTab.value === 'groups') {
      taskGroupFilters.test_envs = []
      taskGroupFilters.name = ''
      taskGroupFilters.case_types = []
      taskGroupFilters.execution_scenes = []
      taskGroupFilters.status = null
      taskGroupFilters.is_notice = null
      taskGroupFilters.sync_status = null
      taskGroupRef.value?.applyFilters()
      return
    }
    conditionItems.forEach((it) => {
      it.value = it.multiple ? [] : ''
    })
    sidebarModuleIds.value = []
    sidebarSelectedModuleId.value = null
    navigationProjectProductId.value = null
    sidebarResetKey.value += 1
    doRefresh()
  }

  watch(activeTab, (tab) => {
    if (tab === 'tasks') doRefresh()
    else taskGroupRef.value?.load()
  })

async function onAdd() {
    if (!(await loadExecutionOptions())) return
    data.actionTitle = '新增'
    data.isAdd = true
    modalDialogRef.value?.toggle()
    formItems.forEach((it) => {
      if (it.reset) {
        it.reset()
      } else {
        it.value = it.multiple ? [] : ''
      }
    })
    setFormValue('execution_scope', 'manual')
    void prefillNavigationFormItems(navigationCreateRef.value, formItems, () => data.isAdd)
      .then(() => { if (data.isAdd) onProjectChange(getFormValue('project_product')) })
  }

  function onDelete(record: any) {
    Modal.confirm({
      title: '提示',
      content: '是否要删除此定时任务？',
      cancelText: '取消',
      okText: '删除',
      onBeforeOk: () => {
        return deleteSystemTasks(record.id)
          .then((res) => {
            Message.success(res.msg)
          })
          .catch(console.log)
          .finally(() => {
            doRefresh()
          })
      },
    })
  }

  async function onTrigger(record: any) {
    data.triggerLoading = true
    const loaded = await loadExecutionOptions()
    data.triggerLoading = false
    if (!loaded) return
    data.triggerRecord = record
    triggerModalRef.value?.show({
      executionName: record.name || `定时任务 #${record.id}`,
      testEnv: null,
      testEnvs: Array.isArray(record.test_envs) ? record.test_envs.map(Number) : [],
      apiConcurrencyLimit: null,
    })
  }

  function onCancelTrigger() {
    data.triggerRecord = null
  }

  async function onConfirmTrigger(config: {
    executionName: string
    testEnv: number | null
    testEnvs?: number[]
    apiConcurrencyLimit: number | null
  }) {
    if (!data.triggerRecord) return false
    data.triggerLoading = true
    try {
      const res = await postSystemTriggerManual(
        data.triggerRecord.id,
        config.apiConcurrencyLimit,
        config.testEnvs
      )
      Message.success(res.msg)
      triggerModalRef.value?.close()
      data.triggerRecord = null
      doRefresh()
      return true
    } catch {
      return false
    } finally {
      data.triggerLoading = false
      triggerModalRef.value?.setConfirmLoading(false)
    }
  }

  async function onUpdate(item: any) {
    if (!(await loadExecutionOptions())) return
    data.actionTitle = '编辑'
    data.isAdd = false
    data.updateId = item.id
    data.isHydratingForm = true
    onProjectChange(item.project_product?.id)
    modalDialogRef.value?.toggle()
    nextTick(() => {
      formItems.forEach((it) => {
        const propName = item[it.key]
        if (Array.isArray(propName)) {
          it.value = propName.map((value: any) => getOptionId(value))
        } else if (typeof propName === 'object' && propName !== null) {
          if (propName.name) {
            it.value = propName.id
          } else if (propName.id) {
            it.value = propName.id
          } else {
            it.value = propName
          }
        } else {
          it.value = propName
        }
      })
      nextTick(() => {
        data.isHydratingForm = false
      })
    })
  }

  function onDataForm() {
    if (formItems.every((it) => (it.validator ? it.validator() : true))) {
      let value = getFormItems(formItems)
      if (value['execution_scope'] === 'module' && !getOptionId(value['module'])) {
        Message.error('执行范围选择“模块全量”时必须选择模块')
        modalDialogRef.value?.setConfirmLoading(false)
        return
      }
      if (value['execution_scope'] === 'full_product' && getOptionId(value['module'])) {
        Message.error('执行范围选择“产品全量”时不能同时选择模块')
        modalDialogRef.value?.setConfirmLoading(false)
        return
      }
      const apiConcurrencyLimit = value['api_concurrency_limit']
      const hasApiConcurrencyLimit =
        apiConcurrencyLimit !== undefined &&
        apiConcurrencyLimit !== null &&
        String(apiConcurrencyLimit).trim() !== ''
      if (
        hasApiConcurrencyLimit &&
        (!Number.isInteger(Number(apiConcurrencyLimit)) ||
          Number(apiConcurrencyLimit) < 1 ||
          Number(apiConcurrencyLimit) > data.apiPlatformLimit)
      ) {
        Message.error(`API 执行并发必须在 1 到 ${data.apiPlatformLimit} 之间`)
        modalDialogRef.value?.setConfirmLoading(false)
        return
      }
      if (!hasApiConcurrencyLimit) {
        value['api_concurrency_limit'] = null
      } else {
        value['api_concurrency_limit'] = Number(apiConcurrencyLimit)
      }
      value['case_types'] = Array.isArray(value['case_types']) ? value['case_types'] : []
      value['execution_scenes'] = Array.isArray(value['execution_scenes'])
        ? value['execution_scenes']
        : []
      value['timing_strategies'] = Array.isArray(value['timing_strategies'])
        ? value['timing_strategies'].map((item: any) => getOptionId(item))
        : []
      value['test_envs'] = Array.isArray(value['test_envs'])
        ? value['test_envs'].map((item: any) => Number(getOptionId(item)))
        : []
      value['project_product'] = getOptionId(value['project_product'])
      value['module'] = getOptionId(value['module'])
      if (value['module'] === null || value['module'] === '') {
        value['module'] = null
      }
      if (data.isAdd) {
        value['status'] = 0
        value['is_notice'] = 0
        const createRequest = postSystemTasks(value)
        createRequest
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      } else {
        value['id'] = data.updateId
        putSystemTasks(value)
          .then((res) => {
            modalDialogRef.value?.toggle()
            Message.success(res.msg)
            doRefresh()
          })
          .catch((error) => {
            console.log(error)
          })
          .finally(() => {
            modalDialogRef.value?.setConfirmLoading(false)
          })
      }
    } else {
      modalDialogRef.value?.setConfirmLoading(false)
    }
  }

  function getNickName() {
    getUserName()
      .then((res) => {
        data.userList = res.data
      })
      .catch(console.log)
  }

  async function loadTaskGroupOptions(projectProductId: number | null) {
    const item = conditionItems.find((condition) => condition.key === 'task_group')
    if (!item) return
    data.taskGroupOptionsLoading = true
    try {
      const res = await getScheduledTaskGroupOptions(projectProductId)
      item.optionItems = Array.isArray(res.data) ? res.data : []
    } catch (error) {
      item.optionItems = []
      console.log(error)
    } finally {
      data.taskGroupOptionsLoading = false
    }
  }

  function getTiming() {
    getSystemTimingList()
      .then((res) => {
        data.timingList = res.data
      })
      .catch(console.log)
  }

  async function loadExecutionOptions() {
    data.executionOptionsLoading = true
    try {
      const res = await getSystemTaskExecutionOptions()
      data.apiPlatformLimit = Number(res.data?.api_platform_limit || 1)
      return true
    } catch {
      return false
    } finally {
      data.executionOptionsLoading = false
    }
  }

  function replaceTaskRow(record: any, changes: Record<string, any>) {
    const index = table.dataList.findIndex((item) => String(item.id) === String(record.id))
    if (index < 0) return
    table.dataList.splice(index, 1, { ...record, ...changes })
  }

  const retentionSavingIds = ref<number[]>([])
  const retentionEditor = reactive({ visible: false, record: null as any, value: 'all' })
  function openRetentionEditor(record: any) {
    if (retentionSavingIds.value.length)
    return;
    Object.assign(retentionEditor, { visible: true, record, value: record.report_retention_policy || 'all' })
  }
  async function saveRetentionPolicy(record: any, value: string) {
    if (!record || retentionSavingIds.value.includes(record.id))
    return false;
    retentionSavingIds.value.push(record.id)
    try {
      await putSystemTasks({ id: record.id, report_retention_policy: value })
      record.report_retention_policy = value
      Message.success('报告保留策略已保存，下次执行生效')
      return true
    } catch {
      // 请求层负责错误提示，保留原选项。
      return false
    } finally {
      retentionSavingIds.value = retentionSavingIds.value.filter((id) => id !== record.id)
    }
  }
  const onModifyStatus = async (newValue: any, record: any, field: string) => {
    const nextValue = newValue ? 1 : 0
    if (record.task_group && field !== 'status') {
      Message.warning('任务组生成任务的通知配置请在任务组中修改')
      return false
    }
    try {
      const response = record.task_group
        ? await updateScheduledTaskGroupMemberStatus(
            Number(record.task_group),
            Number(record.task_group_member_id),
            newValue
          )
        : await putSystemTasks({
            id: record.id,
            [field]: nextValue,
            ...(field === 'is_notice' && nextValue === 0 ? { fail_notice: 0 } : {}),
          })
      if (response.code !== 200) return false
      const changes: Record<string, any> = {
        [field]:
          record.task_group && field === 'status'
            ? Number(Boolean(response.data?.effective_enabled))
            : nextValue,
      }
      if (field === 'is_notice' && nextValue === 0) changes.fail_notice = 0
      replaceTaskRow(record, changes)
      Message.success(response.msg)
      return true
    } catch (error) {
      console.log(error)
      return false
    }
  }

  function onClick(record: any) {
    router.push({
      path: '/timing/case',
      query: {
        id: record.id,
        name: record.name,
        types: (record.case_types || []).join(','),
        execution_scope: record.execution_scope,
        project_product_id: record.project_product.id,
        module_id: record.module?.id || '',
      },
    })
  }

  function getConditionValue(key: string) {
    const item = conditionItems.find((it) => it.key === key)
    return getOptionId(item?.value)
  }

  function getFormValue(key: string) {
    const item = formItems.find((it) => it.key === key)
    return getOptionId(item?.value)
  }

  function getFormArrayValue(key: string) {
    const value = formItems.find((item) => item.key === key)?.value
    return Array.isArray(value) ? value : []
  }

  function getExecutionScenes() {
    const value = formItems.find((item) => item.key === 'execution_scenes')?.value
    return Array.isArray(value) ? value.map((item) => String(item)) : []
  }

  function setConditionValue(key: string, value: any) {
    const item = conditionItems.find((it) => it.key === key)
    if (item) item.value = value
  }

  function setFormValue(key: string, value: any) {
    const item = formItems.find((it) => it.key === key)
    if (item) item.value = value
  }

  function onFormProjectChange(value: any) {
    if (!data.isHydratingForm) {
      setFormValue('module', '')
    }
    onProjectChange(value)
  }

  function onProjectChange(value: any) {
    const id = getOptionId(value)
    getSystemNoticeName(id)
      .then((res) => {
        data.noticeList = res.data
      })
      .catch(console.log)
  }

  onMounted(() => {
    nextTick(async () => {
      await enumStore.getEnum()
      await loadTaskGroupOptions(navigationProjectProductId.value)
      getTiming()
      getNickName()
    })
  })
</script>

<style scoped>
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

  .mango-task-form {
    display: grid;
    gap: 0;
  }

  .mango-task-form-group {
    padding: 14px 0;
    border-bottom: 1px solid var(--m-border);
  }

  .mango-task-form-group:first-child {
    padding-top: 0;
  }

  .mango-task-form-group:last-child {
    padding-bottom: 0;
    border-bottom: 0;
  }

  .mango-task-form-group__header {
    display: flex;
    align-items: baseline;
    gap: 10px;
    margin-bottom: 12px;
  }

  .mango-task-form-group__header strong {
    color: var(--m-text);
    font-size: 14px;
    font-weight: 600;
  }

  .mango-task-form-group__header span {
    color: var(--m-muted);
    font-size: 12px;
  }

  .mango-task-form-group__fields {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px 16px;
  }

  .mango-task-form-group__fields :deep(.arco-form-item) {
    flex-wrap: nowrap;
    min-width: 0;
    margin-bottom: 0;
  }

  .mango-task-form-group__fields :deep(.arco-form-item-label-col) {
    flex: 0 0 120px;
    width: 120px;
    max-width: 120px;
    white-space: nowrap;
  }

  .mango-task-form-group__fields :deep(.arco-form-item-wrapper-col) {
    flex: 1 1 0;
    width: 0;
    max-width: none;
    min-width: 0;
  }

  .mango-task-form-item--wide {
    grid-column: 1 / -1;
  }

  .mango-task-classification-summary {
    display: flex;
    align-items: center;
    padding: 10px 12px;
    gap: 10px;
    margin-top: 12px;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface-soft);
  }

  .mango-task-classification-summary > span {
    color: var(--m-muted);
    font-size: 12px;
    white-space: nowrap;
  }

  .mango-task-classification-summary > strong {
    color: var(--m-text);
    font-size: 13px;
    font-weight: 600;
  }

  @media (max-width: 720px) {
    .mango-task-form-group__fields {
      grid-template-columns: minmax(0, 1fr);
    }

    .mango-task-form-item--wide {
      grid-column: auto;
    }

    .mango-task-classification-summary {
      align-items: flex-start;
      flex-wrap: wrap;
    }
  }
</style>
