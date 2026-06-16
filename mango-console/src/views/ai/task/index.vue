<template>
  <TableBody>
    <template #header><TableHeader title="AI / 执行记录" @search="loadData" /></template>
    <template #default>
      <a-table
        :bordered="false"
        :columns="columns"
        :data="rows"
        :loading="loading"
        :pagination="false"
        :row-key="'id'"
        :scroll="{ x: 1040 }"
      >
        <template #columns>
          <a-table-column v-for="item of columns" :key="item.key" v-bind="item">
            <template v-if="item.key === 'status'" #cell="{ record }">
              <a-tag :color="statusColor(record.status)" size="small">
                {{ enumTitle(enumStore.ai_agent_task_status, record.status) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'task_type'" #cell="{ record }">
              <a-tag :color="enumColor(record.task_type)" size="small">
                {{ enumTitle(enumStore.ai_agent_task_type, record.task_type) }}
              </a-tag>
            </template>
            <template v-else-if="item.key === 'actions'" #cell="{ record }">
              <MangoTableActions
                :actions="[
                  { label: '详情', onClick: () => openDetail(record) },
                  {
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
            <a-tag :color="enumColor(detail.task_type)" size="small">{{ enumTitle(enumStore.ai_agent_task_type, detail.task_type) }}</a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="标题">{{ detail.title }}</a-descriptions-item>
          <a-descriptions-item label="状态">
            <a-tag :color="statusColor(detail.status)" size="small">{{ enumTitle(enumStore.ai_agent_task_status, detail.status) }}</a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="模型">{{ detail.model_name || '-' }}</a-descriptions-item>
          <a-descriptions-item label="更新时间">{{ detail.update_time || '-' }}</a-descriptions-item>
        </a-descriptions>
        <a-alert v-if="detail.error_message" type="error" class="mango-ai-task-error">
          {{ detail.error_message }}
        </a-alert>
        <a-tabs>
          <a-tab-pane key="output" title="返回结果">
            <JsonDisplay :data="detail.output_data || {}" />
          </a-tab-pane>
          <a-tab-pane key="input" title="输入参数">
            <JsonDisplay :data="detail.input_data || {}" />
          </a-tab-pane>
          <a-tab-pane key="tool_calls" title="工具调用">
            <a-table
              :bordered="false"
              :columns="toolCallColumns"
              :data="detail.tool_calls || []"
              :pagination="false"
              :row-key="'id'"
              :scroll="{ x: 980 }"
            >
              <template #columns>
                <a-table-column v-for="item of toolCallColumns" :key="item.key" v-bind="item">
                  <template v-if="item.key === 'status'" #cell="{ record }">
                    <a-tag :color="statusColor(record.status)" size="small">
                      {{ enumTitle(enumStore.ai_agent_tool_call_status, record.status) }}
                    </a-tag>
                  </template>
                  <template v-else-if="item.key === 'risk_level'" #cell="{ record }">
                    <a-tag :color="enumColor(record.risk_level)" size="small">
                      {{ enumTitle(enumStore.ai_mcp_tool_risk_level, record.risk_level) }}
                    </a-tag>
                  </template>
                  <template v-else-if="item.key === 'confirm_required'" #cell="{ record }">
                    <a-tag :color="statusColor(record.confirm_required ? 1 : 0)" size="small">
                      {{ record.confirm_required ? '需确认' : '无需确认' }}
                    </a-tag>
                  </template>
                </a-table-column>
              </template>
            </a-table>
          </a-tab-pane>
          <a-tab-pane key="raw" title="完整数据">
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

  const enumStore = useEnum()
  const TASK_STATUS_PENDING = 2
  const TASK_STATUS_RUNNING = 3
  const rows = ref<any[]>([])
  const pagination = usePagination(loadData)
  const loading = ref(false)
  const detailLoading = ref(false)
  const retryLoading = ref<number | null>(null)
  const visible = ref(false)
  const detail = ref<any>(null)
  const columns = [
    { title: 'ID', key: 'id', dataIndex: 'id', width: 80 },
    { title: '任务编号', key: 'task_no', dataIndex: 'task_no', width: 250 },
    { title: '任务类型', key: 'task_type', dataIndex: 'task_type', width: 150 },
    { title: '标题', key: 'title', dataIndex: 'title', ellipsis: true, tooltip: true },
    { title: '状态', key: 'status', dataIndex: 'status', width: 120 },
    { title: '模型', key: 'model_name', dataIndex: 'model_name', width: 250 },
    { title: '操作', key: 'actions', dataIndex: 'actions', align: 'center', fixed: 'right', width: 130 },
  ]
  const toolCallColumns = [
    { title: '序号', key: 'step_no', dataIndex: 'step_no', width: 80 },
    { title: '工具', key: 'tool_name', dataIndex: 'tool_name', width: 220, ellipsis: true, tooltip: true },
    { title: '状态', key: 'status', dataIndex: 'status', width: 100 },
    { title: '风险', key: 'risk_level', dataIndex: 'risk_level', width: 110 },
    { title: '确认', key: 'confirm_required', dataIndex: 'confirm_required', width: 100 },
    { title: '错误信息', key: 'error_message', dataIndex: 'error_message', ellipsis: true, tooltip: true },
    { title: '结束时间', key: 'end_time', dataIndex: 'end_time', width: 180 },
  ]
  function enumTitle(options: any[] = [], value: any) {
    if (value === null || value === undefined || value === '') {
      return '-'
    }
    return options.find((item) => String(item.key) === String(value))?.title || value
  }
  function enumColor(value: any) {
    return enumStore.colors?.[Number(value)]
  }
  function statusColor(value: any) {
    return enumStore.status_colors?.[Number(value)]
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
