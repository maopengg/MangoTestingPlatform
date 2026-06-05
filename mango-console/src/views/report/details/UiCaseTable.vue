<template>
  <a-table
    :bordered="false"
    :data="flatRows"
    :loading="loading"
    :pagination="false"
    :scroll="{ x: 1520 }"
    :span-method="spanMethod"
    class="case-summary-table"
    row-key="__rowKey"
  >
    <template #columns>
      <a-table-column
        v-for="itemRow of uiColumns"
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
        <template v-else-if="itemRow.key === 'actions'" #cell="{ record }">
          <div class="action-cell">
            <a-button
              v-if="!record.children"
              type="text"
              size="mini"
              @click="$emit('show-details', record.__detailRecord || record)"
            >
              查看详细报告
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
  import { uiColumns } from './config'

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
      const rowSpan = rows.length
      const caseId = item?.case_id || item?.id || '-'
      const caseName = item?.case_name || item?.name || '未命名用例'
      const detailRecord = {
        ...item,
        case_type: 0,
        name: caseName,
        status: item?.status ?? rows.find((row: any) => row?.status === 0)?.status ?? rows[0]?.status,
        test_time: item?.test_time || rows[0]?.test_time,
        test_object: item?.test_object || rows[0]?.test_object,
        video_path: item?.video_path || rows.find((row: any) => row?.video_path)?.video_path,
        error_message: item?.error_message || rows.find((row: any) => row?.error_message)?.error_message,
        element_result_list: rows,
        children: rows,
      }
      return rows.map((row: any, index: number) => ({
        ...row,
        case_type: row?.case_type ?? 0,
        name: row?.name || item?.case_name || item?.name,
        __rowKey: `${item?.id || caseId}-${row?.id || index}-${index}`,
        __caseId: caseId,
        __caseName: caseName,
        __caseCount: Number(item?.case_sum || rows.length || 0),
        __caseRowSpan: index === 0 ? rowSpan : 0,
        __caseSourceId: item?.id,
        __isFirstCaseRow: index === 0,
        __detailRecord: detailRecord,
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

  function statusColor(status: number) {
    return props.enumStore?.status_colors?.[status] || 'gray'
  }

  function statusText(status: number) {
    return props.enumStore?.task_status?.[status]?.title || '未知'
  }
</script>

<style scoped lang="less">
  @import './case-table.less';
</style>
