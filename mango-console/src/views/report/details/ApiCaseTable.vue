<template>
  <a-table
    :bordered="false"
    :data="flatRows"
    :loading="loading"
    :pagination="false"
    :scroll="{ x: 2000 }"
    :span-method="spanMethod"
    class="case-summary-table"
    row-key="__rowKey"
  >
    <template #columns>
      <a-table-column
        v-for="itemRow of apiColumns"
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
        <template v-else-if="itemRow.key === 'name'" #cell="{ record }">
          <a-tag v-if="record.is_recovery" size="small">恢复</a-tag>
          <span>{{ record.name }}</span>
        </template>
        <template v-else-if="itemRow.key === 'status'" #cell="{ record }">
          <a-tag :color="statusColor(record.status)" size="small">{{
            statusText(record.status)
          }}</a-tag>
        </template>
        <template v-else-if="itemRow.key === 'response_time'" #cell="{ record }">
          <span>{{ formatDuration(record?.response_time ?? record?.response?.time) }}</span>
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
        label: '重试',
        hidden: !(canRetry && record.__isFirstCaseRow),
        onClick: () => $emit('retry', record.__caseSourceId), },
    {
        label: '历史报告',
        hidden: !(record.__isFirstCaseRow && record.__caseId && record.__caseId !== '-'),
        onClick: () => $emit('show-history', record), },
    {
        label: '用例详情',
        hidden: !(canRetry && record.__isFirstCaseRow && record.__caseId && record.__caseId !== '-'),
        onClick: () => $emit('open-case-detail', record), },
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
  import { apiColumns } from './config'

  const props = defineProps<{
    cases: any[]
    enumStore: any
    canRetry?: boolean
    loading?: boolean
  }>()

  defineEmits<{
    (event: 'open-case-detail', record: any): void
    (event: 'show-details', record: any): void
    (event: 'show-history', record: any): void
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
      const apiInfoName =
        item?.api_info_name || rows.find((row: any) => row?.api_info_name)?.api_info_name
      const snapshotCurrentStep = item?.snapshot_current_step || {}
      const snapshotParameterId = snapshotCurrentStep?.parameter_id
      return displayRows.map((row: any, index: number) => ({
        ...row,
        status: isSnapshotRow(item, row, index, displayRows.length) ? 3 : row?.status,
        error_message: isSnapshotRow(item, row, index, displayRows.length)
          ? snapshotMessage(item, row)
          : row?.error_message,
        case_type: row?.case_type ?? 1,
        name: row?.name || item?.case_name || item?.name,
        __rowKey: `${item?.id || caseId}-${row?.id || index}-${index}`,
        __detailId: item?.id || '-',
        __caseId: caseId,
        __caseName: caseName,
        __apiInfoName: row?.api_info_name || apiInfoName || '-',
        __caseCount: Number(item?.case_sum || displayRows.length || 0),
        __caseRowSpan: index === 0 ? rowSpan : 0,
        __caseSourceId: item?.id,
        __isFirstCaseRow: index === 0,
        __sourceRecord: item,
        __isWarningRow: row?.__isWarningRow,
        __isSnapshotRow: isSnapshotRow(item, row, index, displayRows.length),
        __snapshotParameterId: snapshotParameterId,
        __detailRecord: {
          ...row,
          __caseId: caseId,
          __caseName: caseName,
          test_suite_detail_id: item?.id,
          __caseSourceId: item?.id,
          status: isSnapshotRow(item, row, index, displayRows.length) ? 3 : row?.status,
          error_message: isSnapshotRow(item, row, index, displayRows.length)
            ? snapshotMessage(item, row)
            : row?.error_message,
          case_type: row?.case_type ?? 1,
          name: row?.name || item?.case_name || item?.name,
          result_mode: item?.result_mode,
          snapshot_progress: item?.snapshot_progress,
          snapshot_retry: item?.snapshot_retry,
          snapshot_updated_at: item?.snapshot_updated_at,
        },
      }))
    })
  )

  function spanMethod({ record, columnIndex }: any) {
    if (!apiColumns[columnIndex]?.mergeCell) return undefined
    return {
      rowspan: record.__caseRowSpan,
      colspan: record.__caseRowSpan > 0 ? 1 : 0,
    }
  }

  function formatDuration(value: number | string) {
    if (value === undefined || value === null || value === '') return ''
    const duration = Number(value)
    if (Number.isNaN(duration)) return `${value} 秒`
    return `${duration.toFixed(2)} 秒`
  }

  function statusColor(status: number | string) {
    if (Number(status) === 4) return 'orange'
    return props.enumStore?.status_colors?.[status] || 'gray'
  }

  function statusText(status: number | string) {
    if (Number(status) === 4) return '警告'
    return props.enumStore?.task_status?.[status]?.title || '未知'
  }

  function isSnapshotRow(item: any, row: any, index: number, total: number) {
    if (item?.result_mode !== 'snapshot') return false
    const currentStep = item?.snapshot_current_step || {}
    if (currentStep?.parameter_id && row?.parameter_id) {
      return String(currentStep.parameter_id) === String(row.parameter_id)
    }
    return index === total - 1
  }

  function snapshotMessage(item: any, row: any) {
    const retry = item?.snapshot_retry || {}
    const progress = item?.snapshot_progress || {}
    const parts = ['执行中快照']
    if (retry.current || retry.max) {
      parts.push(`重试 ${retry.current || 0}/${retry.max || '-'}`)
    }
    if (progress.done || progress.total) {
      parts.push(`进度 ${progress.done || 0}/${progress.total || '-'}`)
    }
    if (row?.error_message || retry.reason) {
      parts.push(row?.error_message || retry.reason)
    }
    if (item?.snapshot_updated_at) {
      parts.push(`更新于 ${item.snapshot_updated_at}`)
    }
    return parts.join('，')
  }

  function buildWarningRows(item: any) {
    const rows = Array.isArray(item?.children) && item.children.length > 0 ? item.children : [item]
    const writtenWarningCount = rows.filter((row: any) => Number(row?.status) === 4).length
    const warningCount = Math.max(Number(item?.warning || 0) - writtenWarningCount, 0)
    if (warningCount <= 0) return []
    const fallbackName =
      item?.api_info_name ||
      rows.find((row: any) => row?.api_info_name)?.api_info_name ||
      '未执行步骤'
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
