<template>
  <BaseSidePanel v-model:visible="visible" :title="`执行结果 / ${selectedId ?? '-'}`"
    width="50%" cancel-button-text="关闭" @cancel="close">
    <MangoPanelSpin :loading="loading" class="mango-execution-result-json">
      <JsonDisplay v-if="result?.state === 'available'" :data="result.value"
        :default-expanded="false" :show-drawer-button="false" />
      <div v-else-if="!loading && result" class="mango-empty-state">
        {{ result.state === 'cleaned' ? '完整结果已按保留策略清理，执行记录仍保留。' : '本次执行尚未保存完整结果。' }}
      </div>
      <MangoRequestFeedback v-else-if="failed">
        <a-button size="small" :loading="loading" @click="loadResult">重新读取</a-button>
      </MangoRequestFeedback>
    </MangoPanelSpin>
  </BaseSidePanel>
</template>

<script setup lang="ts">
  import { onBeforeUnmount, onDeactivated, ref, shallowRef, watch } from 'vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import MangoRequestFeedback from '@/components/feedback/MangoRequestFeedback.vue'
  import { getExecutionResultDetailResolved } from '@/api/system/execution_result'
  import { reportLoadError } from '@/utils/load-error'
  import { parseExecutionResultJson } from '../execution-admin'
  import type { ExecutionAdminId, ExecutionResultJson } from '../execution-admin'

  const props = defineProps<{ contextKey: string }>()
  const visible = ref(false), loading = ref(false), failed = ref(false)
  const selectedId = ref<ExecutionAdminId | null>(null)
  const result = shallowRef<ExecutionResultJson | null>(null)
  let version = 0

  function close() {
    version++
    visible.value = false
    selectedId.value = null
    result.value = null
    loading.value = false
    failed.value = false
  }

  async function loadResult() {
    if (!visible.value || selectedId.value === null || loading.value) return
    const id = selectedId.value, context = props.contextKey, currentVersion = ++version
    const current = () => visible.value && currentVersion === version && context === props.contextKey
    loading.value = true
    failed.value = false
    result.value = null
    try {
      const response = await getExecutionResultDetailResolved(id)
      if (current()) result.value = parseExecutionResultJson(response, id)
    } catch (error) {
      if (current()) {
        failed.value = true
        reportLoadError(error, '完整结果读取失败，请重新读取；若文件已被删除，请检查存储服务。')
      }
    } finally {
      if (current()) loading.value = false
    }
  }

  function open(id: ExecutionAdminId) {
    if (visible.value && String(selectedId.value) === String(id) && loading.value) return
    close()
    selectedId.value = id
    visible.value = true
    return loadResult()
  }
  watch(visible, value => { if (!value) close() }, { flush: 'sync' })
  watch(() => props.contextKey, close, { flush: 'sync' })
  onDeactivated(close)
  onBeforeUnmount(close)
  defineExpose({ open, close, loading, selectedId })
</script>

<style scoped>
  .mango-execution-result-json {
    display: block;
    width: 100%;
    min-height: 160px;
  }
</style>
