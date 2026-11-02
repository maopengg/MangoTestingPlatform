<template>
  <a-table
    :bordered="false"
    :data="flatRows"
    :loading="loading"
    :pagination="false"
    :scroll="{ x: 1720 }"
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
        <template v-else-if="itemRow.key === 'disposition'" #cell="{ record }">
          <ReportDispositionStatus :record="record.__sourceRecord" />
        </template>
        <template v-else-if="itemRow.key === 'actions'" #cell="{ record }">
          <ReportDisposition :record="record.__sourceRecord"
            :editable="canRetry && record.__isFirstCaseRow" @saved="$emit('disposition-saved')">
            <template #default="{ open, eligible }">
          <MangoTableActions
            :actions="[
    { label: '排查与排除', hidden: !eligible, overflow: true, priority: 100, onClick: open },
    {
        label: '详细报告',
        hidden: !!record.children,
        onClick: () => $emit('show-details', record.__detailRecord || record), },
    {
        label: '用例详情',
        hidden: !(canRetry && record.__isFirstCaseRow && record.__caseId && record.__caseId !== '-'),
        onClick: () => $emit('open-case-detail', record), },
    {
        label: '重试',
        hidden: !(canRetry && record.__isFirstCaseRow),
        onClick: () => $emit('retry', record.__caseSourceId), },
]"
          />
            </template>
          </ReportDisposition>
        </template>
      </a-table-column>
    </template>
  </a-table>
</template>

<script lang="ts" setup>
  import { computed } from 'vue'
  import MangoTableActions from '@/components/table/MangoTableActions.vue'
  import ReportDisposition from './ReportDisposition.vue'
  import ReportDispositionStatus from './ReportDispositionStatus.vue'
  import { uiColumns } from './config'

  const props = defineProps<{
    cases: any[]
    enumStore: any
    canRetry?: boolean
    loading?: boolean
  }>()

  defineEmits<{
    (event: 'open-case-detail', record: any): void
    (event: 'show-details', record: any): void
    (event: 'retry', id: any): void
    (event: 'disposition-saved'): void
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
        case_type: row?.case_type ?? 0,
        name: row?.name || item?.case_name || item?.name,
        __rowKey: `${item?.id || caseId}-${row?.id || index}-${index}`,
        __detailId: item?.id || '-',
        __caseId: caseId,
        __caseName: caseName,
        __caseCount: Number(item?.case_sum || displayRows.length || 0),
        __caseRowSpan: index === 0 ? rowSpan : 0,
        __caseSourceId: item?.id,
        __isFirstCaseRow: index === 0,
        __sourceRecord: item,
        __isWarningRow: row?.__isWarningRow,
        __detailRecord: {
          ...row,
          test_suite_detail_id: item?.id,
          __caseSourceId: item?.id,
          case_type: row?.case_type ?? 0,
          name: row?.name || caseName,
          status: row?.status,
          test_time: row?.test_time || item?.test_time,
          test_object: row?.test_object || item?.test_object,
          video_path: row?.video_path || item?.video_path,
          error_message: row?.error_message || item?.error_message,
          cache_data: row?.cache_data || item?.cache_data,
          data_factory_cache_data: row?.data_factory_cache_data || item?.data_factory_cache_data,
          element_result_list: [row],
          children: [row],
        },
      }))
    })
  )

  function spanMethod({ record, columnIndex }: any) {
    if (!uiColumns[columnIndex]?.mergeCell) return undefined
    return {
      rowspan: record.__caseRowSpan,
      colspan: record.__caseRowSpan > 0 ? 1 : 0,
    }
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
