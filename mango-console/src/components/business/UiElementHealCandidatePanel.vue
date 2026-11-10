<template>
  <div class="mango-ui-heal-candidates">
    <a-alert
      v-if="successText"
      type="success"
      class="mango-ui-heal-candidates__result"
    >
      {{ successText }}
    </a-alert>
    <a-alert
      v-else-if="rows.length"
      type="warning"
      class="mango-ui-heal-candidates__result"
    >
      自愈未找到验证通过的候选，请展开诊断过程查看失败原因。
    </a-alert>
    <a-alert v-else type="info">{{ emptyText }}</a-alert>

    <UiElementHealCandidateTable
      v-if="verifiedRows.length"
      :rows="verifiedRows"
      :applying-key="applyingKey"
      @apply="forwardApply"
    />

    <a-collapse v-if="failedRows.length" :bordered="false" class="mango-ui-heal-candidates__diagnostics">
      <a-collapse-item :header="`诊断过程（${failedRows.length} 个未通过候选）`">
        <UiElementHealCandidateTable :rows="failedRows" :applying-key="applyingKey" diagnostic />
      </a-collapse-item>
    </a-collapse>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import UiElementHealCandidateTable from '@/components/business/UiElementHealCandidateTable.vue'
  import type { AiCandidate } from './ui-element-ai'

  const props = defineProps<{
    rows: AiCandidate[]
    applyingKey?: string
    emptyText: string
  }>()
  const emit = defineEmits<{
    (event: 'apply', record: AiCandidate, rowIndex: number, slot: number): void
  }>()

  const normalizedRows = computed(() => (props.rows || []).map((item, index) => ({
    ...item,
    _candidateRowIndex: item.candidate_index ?? index,
  })))
  const verifiedRows = computed(() => normalizedRows.value.filter((item) => Boolean(item.verified)))
  const failedRows = computed(() => normalizedRows.value.filter((item) => !item.verified))
  const verifiedAiCount = computed(() => verifiedRows.value.filter(
    (item) => ['ai_accessibility', 'visual_agent'].includes(item.source || '')
  ).length)
  const successText = computed(() => {
    if (verifiedAiCount.value) return `自愈成功：AI候选匹配${verifiedAiCount.value}个`
    if (verifiedRows.value.length) return `自愈成功：找到${verifiedRows.value.length}个可用候选`
    return ''
  })
  function forwardApply(record: AiCandidate, rowIndex: number, slot: number) {
    emit('apply', record, rowIndex, slot)
  }

</script>

<style scoped>
  .mango-ui-heal-candidates {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-width: 0;
  }
  .mango-ui-heal-candidates__result { margin-bottom: 0; }
  .mango-ui-heal-candidates__diagnostics { background: var(--m-surface-soft); border-radius: var(--m-radius-md); }
</style>
