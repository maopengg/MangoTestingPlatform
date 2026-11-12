<template>
  <div class="mango-evaluation-report-list">
    <section v-for="record in rows" :key="record.key" class="mango-section-card">
      <div class="mango-section-title">{{ record.name }} · {{ record.executionNo }}</div>
      <a-descriptions :column="2" size="small">
        <a-descriptions-item label="数据版本">数据集 #{{ record.datasetId }} · V{{ record.datasetVersion }}</a-descriptions-item>
        <a-descriptions-item label="被测对象">{{ record.targetText }}</a-descriptions-item>
        <a-descriptions-item label="执行结论"><a-tag size="small" :color="statusColor(record.status)">{{ statusText(record.status) }}</a-tag></a-descriptions-item>
        <a-descriptions-item label="有效 / 总测次">{{ record.valid ?? '—' }} / {{ record.total ?? '—' }}</a-descriptions-item>
        <a-descriptions-item label="平均分">{{ record.averageScore ?? '—' }}</a-descriptions-item>
        <a-descriptions-item label="有效率">{{ record.validRate }}</a-descriptions-item>
        <a-descriptions-item label="有效题通过率">{{ record.effectPassRate }}</a-descriptions-item>
        <a-descriptions-item label="无效条目">{{ record.invalid ?? '—' }}</a-descriptions-item>
      </a-descriptions>
        <a-alert data-feedback-kind="execution-result" v-if="record.errorMessage" type="error">{{ record.errorMessage }}</a-alert>
      <a-descriptions v-if="record.memory" :column="3" size="small" title="记忆问答能力">
        <a-descriptions-item label="正确率">{{ record.memory.correct }}</a-descriptions-item>
        <a-descriptions-item label="幻觉率">{{ record.memory.hallucination }}</a-descriptions-item>
        <a-descriptions-item label="遗漏率">{{ record.memory.omission }}</a-descriptions-item>
      </a-descriptions>
      <a-table :columns="evaluationMetricColumns" :data="record.metrics" :pagination="false" :bordered="false" :scroll="{ x: 600 }" row-key="key" size="small" />
      <section v-if="record.aiSummary" class="mango-soft-panel">
        <div class="mango-section-title">AI 总结</div>
        <template v-if="record.aiSummary.status === 'completed'">
          <p>{{ record.aiSummary.overview }}</p>
          <p v-for="(finding, index) in record.aiSummary.findings" :key="index">{{ finding }}</p>
          <p v-for="(tip, index) in record.aiSummary.recommendations" :key="index">{{ tip }}</p>
        </template>
        <a-alert v-else type="warning">总结生成失败，不影响评分结果。{{ record.aiSummary.error_message }}</a-alert>
      </section>
      <div class="mango-evaluation-report-note">统计来自本次执行冻结的数据和评分配置；无效条目不计入能力指标。未配置的能力不作统计。</div>
    </section>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { evaluationMetricColumns } from './config'
  import { evaluationReportRows } from './evaluation-report'
  import { reportStatusText, reportStatusColor, type ReportStatusOption } from './report-rows'
  const props = defineProps<{ cases: unknown[]; statusOptions?: ReportStatusOption[]; statusColors?: Record<string, string> }>()
  const rows = computed(() => evaluationReportRows(props.cases))
  function statusText(value: unknown) { return reportStatusText(value, props.statusOptions, '未评测') }
  function statusColor(value: unknown) { return reportStatusColor(value, props.statusColors) }
</script>

<style scoped>
  .mango-evaluation-report-list { display: grid; gap: var(--m-page-gap); min-width: 0; }
  .mango-section-card { padding: var(--m-card-padding); min-width: 0; }
  .mango-evaluation-report-note { color: var(--m-muted); margin-top: var(--m-page-gap); font-size: 12px; }
</style>
