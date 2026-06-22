<template>
  <a-table
    :bordered="false"
    :data="flatRows"
    :loading="loading"
    :pagination="false"
    :scroll="{ x: 1280 }"
    :span-method="spanMethod"
    class="case-summary-table"
    row-key="__rowKey"
  >
    <template #columns>
      <a-table-column
        v-for="itemRow of pytestColumns"
        :key="itemRow.key || itemRow.dataIndex"
        :align="itemRow.align ? itemRow.align : 'center'"
        :data-index="itemRow.dataIndex"
        :fixed="itemRow.fixed"
        :title="itemRow.title"
        :width="itemRow.width"
        :ellipsis="itemRow.ellipsis"
        :tooltip="itemRow.tooltip"
      >
        <template v-if="itemRow.key === '__caseCount'" #cell="{ record }">
          <span class="case-count">共 {{ record.__caseCount }} 条</span>
        </template>
        <template v-else-if="itemRow.key === 'status'" #cell="{ record }">
          <a-tag :color="statusColor(record.status)" size="small">{{
            statusText(record.status)
          }}</a-tag>
        </template>
        <template v-else-if="itemRow.key === 'start'" #cell="{ record }">
          <span>{{ formatDateTime(record.start) }}</span>
        </template>
        <template v-else-if="itemRow.key === 'stop'" #cell="{ record }">
          <span>{{ formatDateTime(record.stop) }}</span>
        </template>
        <template v-else-if="itemRow.key === 'actions'" #cell="{ record }">
          <div class="action-cell">
            <a-button
              v-if="!record.children"
              type="text"
              size="mini"
              @click="$emit('show-details', record.__detailRecord || record)"
            >
              详细报告
            </a-button>
            <span v-else></span>
            <a-button
              v-if="canRetry && record.__isFirstCaseRow"
              type="text"
              size="mini"
              @click="$emit('retry', record.__caseSourceId)"
            >
              重试
            </a-button>
            <span v-else class="action-placeholder">重试</span>
          </div>
        </template>
      </a-table-column>
    </template>
  </a-table>
</template>

<script lang="ts" setup>
  import { computed } from 'vue'
  import { pytestColumns } from './config'

  const props = defineProps<{
    cases: any[]
    enumStore: any
    canRetry?: boolean
    loading?: boolean
  }>()

  defineEmits<{
    (event: 'show-details', record: any): void
    (event: 'retry', id: any): void
  }>()

  const flatRows = computed(() =>
    (props.cases || []).flatMap((item) => {
      const rows =
        Array.isArray(item?.children) && item.children.length > 0 ? item.children : [item]
      const warningRows = buildWarningRows(item)
      const displayRows = [...rows, ...warningRows]
      const rowSpan = displayRows.length
      const caseId = item?.case_id || item?.id || '-'
      const caseName = item?.case_name || item?.name || '未命名用例'
      return displayRows.map((row: any, index: number) => ({
        ...row,
        error_message: row?.statusDetails?.message || row?.error_message,
        case_type: row?.case_type ?? 2,
        name: row?.name || item?.case_name || item?.name,
        __rowKey: `${item?.id || caseId}-${row?.id || index}-${index}`,
        __caseId: caseId,
        __caseName: caseName,
        __caseCount: Number(item?.case_sum || displayRows.length || 0),
        __caseRowSpan: index === 0 ? rowSpan : 0,
        __caseSourceId: item?.id,
        __isFirstCaseRow: index === 0,
        __isWarningRow: row?.__isWarningRow,
        __detailRecord: {
          ...row,
          error_message: row?.statusDetails?.message || row?.error_message,
          case_type: row?.case_type ?? 2,
          name: row?.name || item?.case_name || item?.name,
        },
      }))
    })
  )

  function spanMethod({ record, columnIndex }: any) {
    if (columnIndex >= 3) return undefined
    return {
      rowspan: record.__caseRowSpan,
      colspan: record.__caseRowSpan > 0 ? 1 : 0,
    }
  }

  function formatDateTime(timestamp: number | string) {
    if (!timestamp) return ''
    const date = new Date(timestamp)
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
  }

  function statusColor(status: number | string) {
    if (Number(status) === 4) return 'orange'
    return props.enumStore?.status_colors?.[status] || 'gray'
  }

  function statusText(status: number | string) {
    if (Number(status) === 4) return '警告'
    return props.enumStore?.task_status?.[status]?.title || '未知'
  }

  function buildWarningRows(item: any) {
    const rows = Array.isArray(item?.children) && item.children.length > 0 ? item.children : [item]
    const writtenWarningCount = rows.filter((row: any) => Number(row?.status) === 4).length
    const warningCount = Math.max(Number(item?.warning || 0) - writtenWarningCount, 0)
    if (warningCount <= 0) return []
    const fallbackName = '未执行步骤'
    return Array.from({ length: warningCount }, (_, index) => ({
      id: `warning-${item?.id || item?.case_id || 'case'}-${index}`,
      name: fallbackName,
      status: 4,
      error_message: '该用例前置步骤失败，未被执行',
      __isWarningRow: true,
    }))
  }
</script>

<style scoped lang="less">
  @import './case-table.less';
</style>
