<template>
  <a-modal v-model:visible="visible" title="调试结果" :width="760" :footer="false" @cancel="close">
    <a-space v-if="result" direction="vertical" fill>
      <a-alert v-if="result.execution_no" type="success"
        >执行编号：{{ result.execution_no }}</a-alert
      >
      <JsonDisplay :data="result.context || result" />
      <a-button
        v-if="result.execution_id != null"
        status="danger"
        :loading="cleanupLoading"
        @click="cleanup"
        >清理调试数据</a-button
      >
    </a-space>
  </a-modal>
</template>
<script setup lang="ts">
  import { ref, shallowRef, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { Message } from '@arco-design/web-vue'
  import {
    postDataFactoryTemplateDebugRun,
    postDataFactoryTemplateDebugCleanup,
  } from '@/api/data-factory'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import { useTemplateScope } from '../../composables/useTemplateScope'
  import { clone } from '../form'
  import type { Id, Overrides, DebugResult } from '../types'
  const emit = defineEmits<{ (event: 'busy-change', pending: boolean): void }>()
  const visible = ref(false),
    running = ref(false),
    cleanupLoading = ref(false),
    result = shallowRef<DebugResult | null>(null)
  let session = 0
  const scope = useTemplateScope(close),
    route = useRoute()
  watch(() => [route.query.template_id, route.query.test_env], close, { flush: 'sync' })
  function close() {
    ++session
    visible.value = false
    result.value = null
  }
  async function run(id: Id, overrides: Overrides, environment: Id | null): Promise<boolean> {
    if (!scope.isActive() || running.value || cleanupLoading.value) return false
    close()
    const current = session,
      version = scope.snapshot(),
      payload = { template_id: id, overrides: clone(overrides), test_env: environment }
    running.value = true
    emit('busy-change', true)
    try {
      const response = await postDataFactoryTemplateDebugRun(payload)
      if (current !== session || !scope.current(version)) return false
      result.value = response.data ?? null
      visible.value = true
      return true
    } catch {
      return false
    } finally {
      running.value = false
      emit('busy-change', false)
    }
  }
  async function cleanup(): Promise<boolean> {
    const id = result.value?.execution_id
    if (!visible.value || !scope.isActive() || id == null || cleanupLoading.value || running.value)
      return false
    const current = session,
      version = scope.snapshot()
    cleanupLoading.value = true
    emit('busy-change', true)
    try {
      const response = await postDataFactoryTemplateDebugCleanup({ execution_id: id })
      if (current !== session || !scope.current(version)) return false
      Message.success(response.msg)
      return true
    } catch {
      return false
    } finally {
      cleanupLoading.value = false
      emit('busy-change', false)
    }
  }
  defineExpose({ run, close })
</script>
