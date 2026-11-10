<template>
  <BaseSidePanel
    :visible="boundTaskVisible"
    :title="boundTaskTitle"
    width="min(1180px, calc(100vw - 32px))"
    cancel-button-text="关闭"
    @update:visible="handleBoundTaskVisibleChange"
    @cancel="handleBoundTaskCancel"
  >
    <a-space class="mango-bound-task-summary">
      <span>共 {{ boundTaskTotal }} 条关联任务</span>
      <a-tag color="blue" size="small">手动绑定 {{ manualRelatedTaskCount }}</a-tag>
      <a-tag color="purple" size="small">自动匹配 {{ automaticRelatedTaskCount }}</a-tag>
    </a-space>
    <a-table
      :bordered="false"
      :data="boundTaskList"
      :loading="boundTaskLoading"
      :pagination="false"
      row-key="relation_key"
      :scroll="{ x: 1420 }"
      size="small"
    >
      <template #empty>
        <div class="mango-empty-state mango-bound-task-empty">暂无关联定时任务</div>
      </template>
      <template #columns>
        <a-table-column title="ID" data-index="task_id" :width="70" align="center" />
        <a-table-column title="关联方式" :width="100" align="center">
          <template #cell="{ record }">
            <a-tag :color="record.relation_type === 'manual' ? 'blue' : 'purple'" size="small">
              {{ record.relation_type === 'manual' ? '手动绑定' : '自动匹配' }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column title="任务名称" data-index="task_name" :width="180" ellipsis tooltip />
        <a-table-column
          title="定时策略"
          data-index="timing_strategies"
          :width="180"
          ellipsis
          tooltip
        >
          <template #cell="{ record }">
            <span>{{
              (record.timing_strategies || []).map((item: any) => item.name).join('、') || '-'
            }}</span>
          </template>
        </a-table-column>
        <a-table-column
          title="负责人"
          data-index="case_people_name"
          :width="100"
          ellipsis
          tooltip
        />
        <a-table-column title="匹配范围" :width="180" ellipsis tooltip>
          <template #cell="{ record }">
            {{ record.relation_type === 'manual' ? '手动指定' : record.module_name || '产品全量' }}
          </template>
        </a-table-column>
        <a-table-column title="命中环境" data-index="matching_test_envs" :width="160">
          <template #cell="{ record }">
            <a-space :size="4" wrap>
              <a-tag
                v-for="testEnv in record.matching_test_envs || []"
                :key="testEnv"
                :color="enumStore.colors[testEnv]"
                size="small"
              >
                {{
                  enumStore.environment_type.find((item) => String(item.key) === String(testEnv))
                    ?.title || '-'
                }}
              </a-tag>
            </a-space>
          </template>
        </a-table-column>
        <a-table-column title="执行场景" :width="200">
          <template #cell="{ record }">
            <ExecutionSceneTagGrid
              :values="record.execution_scenes"
              :options="enumStore.api_case_scenario_tag"
              :colors="enumStore.colors"
            />
          </template>
        </a-table-column>
        <a-table-column title="是否开启" data-index="status" :width="90" align="center">
          <template #cell="{ record }">
            <a-tag :color="record.status === 1 ? 'green' : 'gray'" size="small">
              {{ record.status === 1 ? '开启' : '关闭' }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column title="操作" data-index="actions" fixed="right" :width="160" align="center">
          <template #cell="{ record }">
            <MangoTableActions
              :actions="[
                {
                  label: record.relation_type === 'manual' ? '添加用例' : '查看匹配',
                  onClick: () => openBoundTask(record),
                },
                {
                  label: '解绑',
                  danger: true,
                  hidden: record.relation_type !== 'manual',
                  loading: unbindingIds.has(record.task_detail_id),
                  onClick: () => unbindBoundTask(record),
                },
              ]"
            />
          </template>
        </a-table-column>
      </template>
    </a-table>
  </BaseSidePanel>
  <BaseSidePanel
    :visible="taskCasePanel.visible"
    :title="taskCasePanelTitle"
    width="calc(92vw - 150px)"
    mode="page"
    @update:visible="(value) => (taskCasePanel.visible = value)"
    @cancel="taskCasePanel.visible = false"
  >
    <TimingTaskCase
      v-if="taskCasePanel.visible && taskCasePanel.taskId"
      :key="taskCasePanel.taskId"
      embedded
      :task-id="taskCasePanel.taskId"
      :task-name="taskCasePanel.taskName"
      :task-type="taskCasePanel.taskType"
      :project-product-id="taskCasePanel.projectProductId"
      :module-id="taskCasePanel.moduleId"
      @close="taskCasePanel.visible = false"
    />
  </BaseSidePanel>
</template>
<script setup lang="ts">
  import { computed, reactive, ref, onBeforeUnmount, onDeactivated } from 'vue'
  import { Message, Modal } from '@arco-design/web-vue'
  import { getApiCaseRelatedTasks } from '@/api/apitest/case'
  import { deleteSystemTasksRunCase } from '@/api/system/tasks_details'
  import { useEnum } from '@/store/modules/get-enum'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import ExecutionSceneTagGrid from '@/components/display/ExecutionSceneTagGrid.vue'
  import TimingTaskCase from '@/views/timing/tasks/case/index.vue'
  import type { CaseListRow, RelatedTask } from '../types'
  const enumStore = useEnum()
  const boundTaskVisible = ref(false),
    boundTaskLoading = ref(false),
    boundTaskTitle = ref('关联任务'),
    boundTaskTotal = ref(0)
  const boundTaskList = ref<RelatedTask[]>([])
  const unbindingIds = reactive(new Set<number>())
  let requestVersion = 0,
    currentCaseId: number | null = null
  const manualRelatedTaskCount = computed(
    () => boundTaskList.value.filter((item) => item.relation_type === 'manual').length
  )
  const automaticRelatedTaskCount = computed(
    () => boundTaskList.value.filter((item) => item.relation_type === 'automatic').length
  )
  const taskCasePanel = reactive({
    visible: false,
    taskId: 0,
    taskName: '',
    taskType: 1,
    projectProductId: '' as number | string,
    moduleId: '' as number | string,
    relationType: 'manual' as 'manual' | 'automatic',
  })
  const taskCasePanelTitle = computed(
    () =>
      `${taskCasePanel.relationType === 'automatic' ? '匹配用例' : '添加用例'} - ${
        taskCasePanel.taskName
      }`
  )
  function resetBoundTaskPanel() {
    boundTaskList.value = []
    boundTaskTotal.value = 0
  }

  function handleBoundTaskVisibleChange(value: boolean) {
    boundTaskVisible.value = value
    if (!value) {
      requestVersion++
      boundTaskLoading.value = false
      resetBoundTaskPanel()
    }
  }

  function handleBoundTaskCancel() {
    requestVersion++
    boundTaskLoading.value = false
    boundTaskVisible.value = false
    resetBoundTaskPanel()
  }

  async function open(record: CaseListRow) {
    const request = ++requestVersion
    currentCaseId = record.id
    boundTaskTitle.value = `关联任务 - ${record.name || record.id}`
    boundTaskVisible.value = true
    boundTaskLoading.value = true
    resetBoundTaskPanel()
    try {
      const response = await getApiCaseRelatedTasks(record.id)
      if (request !== requestVersion || !boundTaskVisible.value) return
      boundTaskList.value = Array.isArray(response.data) ? response.data : []
      boundTaskTotal.value = response.totalSize || boundTaskList.value.length
    } catch {
      /* 公共请求层反馈错误，保留当前窗口。 */
    } finally {
      if (request === requestVersion) boundTaskLoading.value = false
    }
  }
  function openBoundTask(record: RelatedTask) {
    taskCasePanel.taskId = record.task_id
    taskCasePanel.taskName = record.task_name || ''
    taskCasePanel.taskType = 1
    taskCasePanel.projectProductId = record.project_product_id || ''
    taskCasePanel.moduleId = record.module_id || ''
    taskCasePanel.relationType = record.relation_type || 'manual'
    taskCasePanel.visible = true
  }

  function unbindBoundTask(record: RelatedTask) {
    if (
      record.relation_type !== 'manual' ||
      !record.task_detail_id ||
      unbindingIds.has(record.task_detail_id)
    )
      return
    const caseId = currentCaseId,
      detailId = record.task_detail_id
    const version = requestVersion
    Modal.confirm({
      title: '确认解绑',
      content: `确认解除当前用例与定时任务「${record.task_name || record.task_id}」的绑定吗？`,
      cancelText: '取消',
      okText: '解绑',
      onBeforeOk: async () => {
        if (caseId !== currentCaseId || version !== requestVersion || !boundTaskVisible.value)
          return false
        if (unbindingIds.has(detailId)) return false
        unbindingIds.add(detailId)
        try {
          const response = await deleteSystemTasksRunCase(detailId)
          if (caseId === currentCaseId && version === requestVersion) {
            Message.success(response.msg)
            boundTaskList.value = boundTaskList.value.filter(
              (item) => item.task_detail_id !== detailId
            )
            boundTaskTotal.value = boundTaskList.value.length
          }
          return true
        } catch {
          return false
        } finally {
          unbindingIds.delete(detailId)
        }
      },
    })
  }

  function close() {
    handleBoundTaskCancel()
    taskCasePanel.visible = false
  }
  onBeforeUnmount(close)
  onDeactivated(close)
  defineExpose({ open, close })
</script>
<style scoped>
  .mango-bound-task-summary {
    display: flex;
    align-items: center;
    gap: var(--m-page-gap);
    margin-bottom: var(--m-page-gap);
  }
  .mango-bound-task-empty {
    padding: var(--m-card-padding);
  }
</style>
