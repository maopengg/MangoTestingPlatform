<template>
  <TableBody content-flush>
    <template #header><TableHeader title="AI / 执行记录" @search="loadData" /></template>
    <template #default>
      <a-table
        :bordered="false"
        :columns="columns"
        :data="rows"
        :loading="loading"
        :pagination="false"
        :row-key="'id'"
        :scroll="{ x: taskTableScrollX }"
      >
        <template #columns>
          <a-table-column v-for="item of columns" :key="item.key" v-bind="item">
            <template v-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="statusColor(record.status)" size="small">
                {{ enumTitle(enumStore.ai_agent_task_status, record.status) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'task_type'" #cell="{ record }">
              <a-tag
                :color="enumColor(enumStore.ai_agent_task_type, record.task_type)"
                size="small"
              >
                {{ enumTitle(enumStore.ai_agent_task_type, record.task_type) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { permission: 'ai.task:detail', label: '详情', onClick: () => openDetail(record) },
                  { permission: 'ai.task:retry',
                    label: '重试',
                    loading: retryLoading === record.id,
                    disabled: [TASK_STATUS_PENDING, TASK_STATUS_RUNNING].includes(record.status),
                    onClick: () => retryTask(record),
                  },
                ]"
              />
            </template>
          </a-table-column>
        </template>
      </a-table>
    </template>
    <template #footer>
      <TableFooter :pagination="pagination" />
    </template>
  </TableBody>
  <a-drawer v-model:visible="visible" title="AI 任务详情" width="60%" :footer="false">
    <a-spin :loading="detailLoading">
      <div v-if="detail" class="mango-ai-task-detail">
        <a-descriptions :column="2" bordered size="small">
          <a-descriptions-item label="任务编号">{{ detail.task_no }}</a-descriptions-item>
          <a-descriptions-item label="任务类型">
            <a-tag
              :color="enumColor(enumStore.ai_agent_task_type, detail.task_type)"
              size="small"
              >{{ enumTitle(enumStore.ai_agent_task_type, detail.task_type) }}</a-tag
            >
          </a-descriptions-item>
          <a-descriptions-item label="标题">{{ detail.title }}</a-descriptions-item>
          <a-descriptions-item label="状态">
            <a-tag :color="statusColor(detail.status)" size="small">{{
              enumTitle(enumStore.ai_agent_task_status, detail.status)
            }}</a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="模型">{{ detail.model_name || '-' }}</a-descriptions-item>
          <a-descriptions-item label="更新时间">{{
            detail.update_time || '-'
          }}</a-descriptions-item>
        </a-descriptions>
        <a-alert v-if="detail.error_message" type="error" class="mango-ai-task-error">
          {{ detail.error_message }}
        </a-alert>
        <a-tabs>
          <a-tab-pane
            key="output"
            title="返回结果"
            data-testid="qa-views-ai-task-tab-pane-返回结果"
          >
            <JsonDisplay :data="detail.output_data || {}" />
          </a-tab-pane>
          <a-tab-pane key="input" title="输入参数" data-testid="qa-views-ai-task-tab-pane-输入参数">
            <JsonDisplay :data="detail.input_data || {}" />
          </a-tab-pane>
          <a-tab-pane
            key="tool_calls"
            title="工具调用"
            data-testid="qa-views-ai-task-tab-pane-工具调用"
          >
            <a-table
              :bordered="false"
              :columns="toolCallColumns"
              :data="detail.tool_calls || []"
              :pagination="false"
              :row-key="'id'"
              :scroll="{ x: toolCallTableScrollX }"
            >
              <template #columns>
                <a-table-column v-for="item of toolCallColumns" :key="item.key" v-bind="item">
                  <template v-if="item.key === 'status'" #cell="{ record }">
                    <a-tag :color="statusColor(record.status)" size="small">
                      {{ enumTitle(enumStore.ai_agent_tool_call_status, record.status) }}
                    </a-tag>
                  </template>
                  <template v-else-if="item.key === 'risk_level'" #cell="{ record }">
                    <a-tag
                      :color="enumColor(enumStore.ai_mcp_tool_risk_level, record.risk_level)"
                      size="small"
                    >
                      {{ enumTitle(enumStore.ai_mcp_tool_risk_level, record.risk_level) }}
                    </a-tag>
                  </template>
                  <template v-else-if="item.key === 'confirm_required'" #cell="{ record }">
                    <a-tag :color="record.confirm_required ? 'orange' : 'gray'" size="small">
                      {{ record.confirm_required ? '需确认' : '无需确认' }}
                    </a-tag>
                  </template>
                </a-table-column>
              </template>
            </a-table>
          </a-tab-pane>
          <a-tab-pane key="raw" title="完整数据" data-testid="qa-views-ai-task-tab-pane-完整数据">
            <JsonDisplay :data="detail" />
          </a-tab-pane>
        </a-tabs>
      </div>
    </a-spin>
  </a-drawer>
</template>

<script setup lang="ts">
  import { Message } from '@arco-design/web-vue'
  import { onMounted, ref } from 'vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import { useEnum } from '@/store/modules/get-enum'
  import { getAiTask, getAiTaskDetail, postAiTaskRetry } from '@/api/ai'
  import { usePagination } from '@/hooks/table'
  import { AI_AGENT_TASK_STATUS_COLORS, getStatusTagColor } from '@/utils/status-color'
  import { getEnumTagColor } from '@/utils/business-format'
  import { columns, taskTableScrollX, toolCallColumns, toolCallTableScrollX } from './config'

  const enumStore = useEnum()
  const TASK_STATUS_PENDING = 2
  const TASK_STATUS_RUNNING = 3
  const rows = ref<any[]>([])
  const pagination = usePagination(loadData, () => loading)
  const loading = ref(false)
  const detailLoading = ref(false)
  const retryLoading = ref<number | null>(null)
  const visible = ref(false)
  const detail = ref<any>(null)
  function enumTitle(options: any[] = [], value: any) {
    if (value === null || value === undefined || value === '') {
      return '-'
    }
    return options.find((item) => String(item.key) === String(value))?.title || value
  }
  function enumColor(options: any[], value: any) {
    return getEnumTagColor(options, value, enumStore.colors)
  }
  function statusColor(value: any) {
    return getStatusTagColor(AI_AGENT_TASK_STATUS_COLORS, value)
  }
  async function loadData() {
    loading.value = true
    try {
      const res = await getAiTask({ page: pagination.page, pageSize: pagination.pageSize })
      rows.value = res.data || []
      pagination.setTotalSize((res as any).totalSize || rows.value.length)
    } finally {
      loading.value = false
    }
  }
  async function openDetail(record: any) {
    visible.value = true
    detailLoading.value = true
    try {
      detail.value = (await getAiTaskDetail(record.id)).data
    } finally {
      detailLoading.value = false
    }
  }
  async function retryTask(record: any) {
    retryLoading.value = record.id
    try {
      await postAiTaskRetry(record.id)
      Message.success('重试任务已启动')
      await loadData()
      if (visible.value && detail.value?.id === record.id) {
        await openDetail(record)
      }
    } finally {
      retryLoading.value = null
    }
  }
  onMounted(async () => {
    await enumStore.getEnum()
    loadData()
  })
</script>

<style scoped>
  .mango-ai-task-detail {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .mango-ai-task-error {
    margin-top: 4px;
  }
</style>
