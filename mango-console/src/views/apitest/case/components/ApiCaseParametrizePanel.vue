<template>
  <ParametrizeDrawer
    :key="session"
    v-model:initial-data="draft"
    :visible="visible"
    :saving="saving"
    show-environment
    @ok="save"
    @cancel="close"
  />
</template>
<script setup lang="ts">
  import { ref, onBeforeUnmount, onDeactivated } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import ParametrizeDrawer from '@/components/forms/ParametrizeDrawer.vue'
  import { putApiCase } from '@/api/apitest/case'
  import { cloneLosslessJson } from '@/utils/lossless-json'
  import type { CaseListRow, CaseParametrizeSuite } from '../types'
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const visible = ref(false),
    saving = ref(false),
    session = ref(0),
    caseId = ref<number | null>(null)
  const draft = ref<CaseParametrizeSuite[]>([])
  function close() {
    session.value++
    visible.value = false
  }
  function open(record: CaseListRow) {
    if (saving.value) return
    session.value++
    caseId.value = record.id
    draft.value = cloneLosslessJson(record.parametrize || [])
    visible.value = true
  }
  async function save(value: CaseParametrizeSuite[]) {
    if (saving.value || caseId.value === null || !visible.value) return
    const token = session.value,
      id = caseId.value,
      suites = cloneLosslessJson(value)
    const hasData = suites.some(
      (item) => item.name || item.parametrize.some((variable) => variable.key)
    )
    saving.value = true
    try {
      const response = await putApiCase({ id, parametrize: hasData ? suites : [] })
      if (token !== session.value) return
      Message.success(response.msg)
      emit('saved')
      close()
    } catch {
      /* 保留抽屉和草稿，允许重试。 */
    } finally {
      saving.value = false
    }
  }
  onBeforeUnmount(close)
  onDeactivated(close)
  defineExpose({ open, close })
</script>
