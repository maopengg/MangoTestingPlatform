<template>
  <a-modal
    modal-class="mango-simple-form-modal"
    v-model:visible="visible"
    title="绑定已有 ApiCase"
    :width="560"
    :ok-loading="saving"
    :on-before-ok="save"
    :mask-closable="!saving"
    :closable="!saving"
    :esc-to-close="!saving"
    :cancel-button-props="{ disabled: saving }"
  >
    <template v-if="failed"><a-button size="small" :loading="optionsLoading" @click="loadOptions">重新加载</a-button></template>
    <a-form auto-label-width class="mango-simple-form" layout="horizontal" :model="form">
      <a-form-item class="mango-simple-form-item" label="ApiCase" required>
        <a-select
          v-model="form.apiCaseId"
          :loading="optionsLoading"
          :disabled="saving || optionsLoading || failed"
          allow-search
          :options="options"
          :field-names="{ value: 'key', label: 'title' }"
        />
      </a-form-item>
    </a-form>
  </a-modal>
</template>
<script setup lang="ts">
import { reportLoadError } from '@/utils/load-error'

  import { reactive, ref } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { getApiCaseName } from '@/api/apitest/case'
  import { bindCoverageApiCase } from '@/api/apitest/module-coverage'
  import { useCoveragePanelScope } from '../composables/useCoveragePanelScope'
  import type { CoverageRecord } from '../types'
  const emit = defineEmits<{ (event: 'saved'): void }>()
  const visible = ref(false),
    saving = ref(false),
    optionsLoading = ref(false),
    failed = ref(false)
  const form = reactive<{ coverageCaseId: number; moduleId?: number; apiCaseId?: number }>({
    coverageCaseId: 0,
  })
  const options = ref<Array<{ key: number; title: string }>>([])
  let session = 0
  const { begin, current, close } = useCoveragePanelScope(visible, () => {
    optionsLoading.value = false
  })
  async function loadOptions() {
    if (!visible.value) return
    const token = (session = begin()),
      moduleId = form.moduleId
    optionsLoading.value = true
    failed.value = false
    try {
      const response = await getApiCaseName(moduleId ?? '')
      if (current(token)) options.value = response.data || []
    } catch (loadFailure0) {
      if (current(token)) (reportLoadError(loadFailure0, "加载失败，请重试", false), failed.value = true)
    } finally {
      if (current(token)) optionsLoading.value = false
    }
  }
  function open(row: CoverageRecord) {
    if (saving.value) return
    Object.assign(form, {
      coverageCaseId: row.id,
      moduleId: row.module?.id,
      apiCaseId: row.api_case ?? undefined,
    })
    options.value = []
    visible.value = true
    return loadOptions()
  }
  async function save() {
    if (!visible.value || saving.value || optionsLoading.value || failed.value) return false
    if (!form.apiCaseId) {
      Message.warning('请选择 ApiCase')
      return false
    }
    const token = session,
      id = form.coverageCaseId,
      apiCaseId = form.apiCaseId
    saving.value = true
    try {
      await bindCoverageApiCase(id, apiCaseId)
      if (!current(token)) return false
      Message.success('绑定成功')
      emit('saved')
      visible.value = false
      return true
    } catch {
      return false
    } finally {
      saving.value = false
    }
  }
  defineExpose({ open, close })
</script>
