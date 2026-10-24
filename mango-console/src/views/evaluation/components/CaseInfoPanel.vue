<template>
  <aside class="mango-case-info" aria-label="用例信息">
    <h2 class="mango-case-info__heading">用例信息</h2>
    <div class="mango-case-info__body mango-native-scrollbar" tabindex="0" aria-label="用例基本信息">
      <dl class="mango-case-info__fields">
        <div v-for="field in fields" :key="field.label" class="mango-case-info__row">
          <dt>{{ field.label }}</dt>
          <dd v-if="field.label === '状态'"><a-tag size="small" :color="statusColor(record.status)">{{ enumTitle('evaluation_case_status', record.status) }}</a-tag></dd>
          <dd v-else>{{ field.value }}</dd>
        </div>
      </dl>
      <section class="mango-case-info__description" aria-label="场景描述">
        <h3>场景描述</h3>
        <p>{{ record.description || '暂无描述' }}</p>
      </section>
    </div>
  </aside>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { formatModulePath } from '@/utils/business-format'
  import { formatEvaluationDate, formatVersion } from './presentation'
  import { useEvaluationEnums } from './useEvaluationEnums'

  const props = defineProps<{ record: Record<string, any> }>()
  const { title: enumTitle, color: statusColor } = useEvaluationEnums()
  const fields = computed(() => [
    { label: '用例 ID', value: props.record.id ?? '—' },
    { label: '用例名称', value: props.record.name || '—' },
    { label: '状态', value: props.record.status },
    { label: '项目/产品', value: props.record.project_product_data?.name || '—' },
    { label: '所属模块', value: formatModulePath(props.record.module_data) },
    { label: '负责人', value: props.record.owner_name || '—' },
    { label: '数据集', value: props.record.dataset_name || '—' },
    { label: '发布版本', value: formatVersion(props.record.dataset_version_no) },
    { label: '创建时间', value: formatEvaluationDate(props.record.create_time) },
    { label: '更新时间', value: formatEvaluationDate(props.record.update_time) },
  ])
</script>

<style scoped>
  .mango-case-info {
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    background: var(--m-surface-soft);
    border-radius: var(--m-radius-md);
  }
  .mango-case-info__heading {
    margin: 0;
    padding: var(--m-space-md);
    border-bottom: 1px solid var(--m-border);
    color: var(--m-text);
    font-size: var(--m-font-body);
    font-weight: 600;
  }
  .mango-case-info__body {
    min-height: 0;
    overflow: auto;
    padding: var(--m-space-md);
  }
  .mango-case-info__fields { margin: 0; }
  .mango-case-info__row {
    display: grid;
    grid-template-columns: 72px minmax(0, 1fr);
    gap: var(--m-space-sm);
    padding-bottom: var(--m-space-md);
    line-height: 1.6;
  }
  .mango-case-info__row dt { color: var(--m-muted); }
  .mango-case-info__row dd {
    margin: 0;
    min-width: 0;
    color: var(--m-text);
    overflow-wrap: anywhere;
  }
  .mango-case-info__description {
    border-top: 1px solid var(--m-border);
    padding-top: var(--m-space-md);
  }
  .mango-case-info__description h3 {
    margin: 0 0 var(--m-space-sm);
    font-size: inherit;
    font-weight: 500;
    color: var(--m-muted);
  }
  .mango-case-info__description p {
    margin: 0;
    line-height: 1.7;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    color: var(--m-text);
  }
</style>
