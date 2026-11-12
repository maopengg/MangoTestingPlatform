<template>
  <ParametrizeDrawer :key="session" v-model:initial-data="draft" :visible="visible" :saving="saving" show-environment @ok="save" @cancel="close">
    <template #feedback><MangoRequestFeedback v-if="error" :message="(error)" /></template>
  </ParametrizeDrawer>
</template>
<script setup lang="ts">
import { requestFailureMessage } from '@/utils/load-error'

  import { ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import ParametrizeDrawer from '@/components/forms/ParametrizeDrawer.vue'
  import { putUiCase } from '@/api/uitest/case'
  import { uiCaseAssetResponse } from '@/components/business/ui-case-step-create'
  import { cloneLosslessJson } from '@/utils/lossless-json'
  import { useCaseListScope } from '../composables/useCaseListScope'
  import { readCaseSuites, type CaseSuite, type UiCaseRow, type CaseId } from '../case-list-records'
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const visible = ref(false), saving = ref(false), error = ref(''), session = ref(0), caseId = ref<CaseId | null>(null), draft = ref<CaseSuite[]>([])
  function close() { session.value++; visible.value = false; error.value = '' }
  const scope = useCaseListScope({ invalidate: close })
  function open(row: UiCaseRow) {
    if (saving.value || !scope.available()) return
    close(); caseId.value = row.id; draft.value = readCaseSuites(row.parametrize)
    if (!draft.value.length) draft.value = [{ name: '', parametrize: [{ key: '', value: '', test_envs: [] }] }]
    visible.value = true
  }
  async function save(value: unknown): Promise<boolean> {
    if (saving.value || !visible.value || caseId.value === null || !scope.available()) return false
    const valid = scope.capture(), version = session.value, current = () => valid() && version === session.value && visible.value, id = caseId.value
    let suites: CaseSuite[]
    try { suites = readCaseSuites(value); draft.value = cloneLosslessJson(suites) } catch (requestFailure) { error.value = requestFailureMessage(requestFailure, '套件数据格式有误，请检查后重试'); return false }
    const hasData = suites.some(suite => suite.name || suite.parametrize.some(item => item.key || item.value))
    saving.value = true; error.value = ''
    try {
      uiCaseAssetResponse(await putUiCase({ id, parametrize: hasData ? suites : [] }))
      if (!current()) return false
      Message.success('套件保存成功'); emit('saved'); close(); return true
    } catch (requestFailure) { if (current()) error.value = requestFailureMessage(requestFailure, '套件保存失败，草稿已保留，请重试'); return false }
    finally { saving.value = false }
  }
  defineExpose({ open, close })
</script>
