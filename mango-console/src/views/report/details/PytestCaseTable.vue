<template>
  <a-table
    :bordered="false"
    :data="flatRows"
    :loading="loading"
    :pagination="false"
    :scroll="{ x: 1480 }"
    :span-method="spanMethod"
    class="mango-case-summary-table"
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
          <span class="mango-case-count">共 {{ record.__caseCount }} 条</span>
        </template>
        <template v-else-if="itemRow.key === '__caseId'" #cell="{ record }"><span>{{ record.__caseId ?? '-' }}</span></template>
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
        loading: retryingIds?.includes(String(record.__caseSourceId)),
        hidden: !(canRetry && record.__isFirstCaseRow && record.__caseSourceId !== null),
        onClick: () => retry(record), },
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
  import { pytestColumns } from './config'
  import { flattenReportCases, reportStatusText, reportStatusColor, formatReportDateTime, type ReportCaseRow, type ReportStatusOption } from './report-rows'

  const props = defineProps<{
    cases: unknown[]
    statusOptions?: ReportStatusOption[]
    statusColors?: Record<string, string>

    canRetry?: boolean
    retryingIds?: string[]
    loading?: boolean
  }>()
  const emit = defineEmits<{

    (event: 'show-details', record: unknown): void

    (event: 'retry', id: string): void
    (event: 'disposition-saved'): void
  }>()
  const flatRows = computed(() => flattenReportCases(props.cases, 2))
  function spanMethod({ record, columnIndex }: { record: ReportCaseRow; columnIndex: number }) {
    if (!pytestColumns[columnIndex]?.mergeCell) return undefined
    return { rowspan: record.__caseRowSpan, colspan: record.__caseRowSpan > 0 ? 1 : 0 }
  }
  function statusText(status: unknown) { return reportStatusText(status, props.statusOptions) }
  function statusColor(status: unknown) { return reportStatusColor(status, props.statusColors) }
  function retry(record: ReportCaseRow) {
    if (!props.canRetry || !record.__isFirstCaseRow || record.__caseSourceId === null || props.retryingIds?.includes(record.__caseSourceId)) return
    emit('retry', record.__caseSourceId)
  }

  const formatDateTime = formatReportDateTime
</script>

<style scoped lang="less">
  @import './case-table.less';
</style>
