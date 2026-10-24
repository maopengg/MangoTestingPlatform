<template>
  <section class="mango-workflow-result">
    <h3 class="mango-section-title">执行流程</h3>
    <a-table class="mango-native-scroll-table" :data="records" :columns="columns" :pagination="false" :scroll="{ x: 760, y: '100%' }" size="small">
      <template #stage="{ record }">{{ label(record.stage, 'evaluation_workflow_stage') }}</template>
      <template #scope="{ record }">{{ label(record.scope, 'evaluation_workflow_scope') }}</template>
      <template #status="{ record }"><a-tag size="small" :color="record.status === 'success' ? 'green' : record.status === 'failed' ? 'red' : 'blue'">{{ label(record.status, 'evaluation_item_execution_status') }}</a-tag></template>
      <template #actions="{ record }"><MangoTableActions :actions="[{ label: '详情', permission: 'evaluation.case:detail', onClick: () => selected = record }]" /></template>
    </a-table>
    <div v-if="selected" class="mango-soft-panel"><strong>{{ selected.name }}</strong><p v-if="selected.error_message" role="alert">{{ selected.error_message }}</p><JsonDisplay :data="selected.output" :show-drawer-button="false" /></div>
  </section>
</template>
<script setup lang="ts">
  import { ref, watch } from 'vue'
  import { useEnum } from '@/store/modules/get-enum'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  const props = defineProps<{ records: any[] }>()
  const selected = ref<any>(), enums = useEnum()
  watch(() => props.records, () => { selected.value = undefined })
  const label = (value: string, key: string) => ((enums as any)[key] || []).find((item: any) => item.key === value)?.title || value
  const columns = [{ title: '步骤', dataIndex: 'name', width: 180, ellipsis: true, tooltip: true }, { title: '阶段', slotName: 'stage', width: 130 }, { title: '范围', slotName: 'scope', width: 150 }, { title: '状态', slotName: 'status', width: 90 }, { title: '耗时（ms）', dataIndex: 'duration_ms', width: 110 }, { title: '操作', slotName: 'actions', width: 160, align: 'center', fixed: 'right' }]
</script>
<style scoped>
  .mango-workflow-result { min-width: 0; max-height: 420px; display: flex; flex-direction: column; gap: var(--m-page-gap); }
  .mango-workflow-result > .arco-table { min-height: 0; flex: 1; }
  .mango-workflow-result .mango-soft-panel { overflow: auto; padding: var(--m-card-padding); }
</style>
