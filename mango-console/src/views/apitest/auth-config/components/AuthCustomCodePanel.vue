<template>
  <BaseSidePanel
    v-model:visible="customCodePanel.visible"
    :title="customCodePanel.title"
    :width="1000"
    :show-footer="false"
  >
    <div v-if="customCodePanel.visible" class="mango-auth-custom-code-panel">
      <CodeEditor
        :model-value="customCodePanel.code"
        language="python"
        readonly
        placeholder="暂无自定义授权代码"
        :code-style="{ height: '100%' }"
      />
      <section class="mango-auth-custom-code-result">
        <div class="mango-auth-custom-code-result-header">
          <span>执行结果</span>
          <a-button
            type="primary"
            size="small"
            :loading="customCodeRunningIds.has(customCodePanel.id)"
            @click="onRunCustomCode"
            >刷新/执行</a-button
          >
        </div>
        <MangoPanelSpin
          :loading="customCodeRunningIds.has(customCodePanel.id)"
          class="mango-auth-custom-code-result-body"
        >
          <MangoRequestFeedback v-if="customCodePanel.error" :message="(customCodePanel.error)" />
          <JsonDisplay
            v-else-if="customCodePanel.result !== null"
            :data="customCodePanel.result"
            :show-toolbar="false"
          />
          <div v-else class="mango-empty-state">点击“刷新/执行”刷新授权，结果将在此展示。</div>
        </MangoPanelSpin>
      </section>
    </div>
  </BaseSidePanel>
</template>
<script setup lang="ts">
import { requestFailureMessage } from '@/utils/load-error'

  import { reactive, onBeforeUnmount, onDeactivated } from 'vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import CodeEditor from '@/components/editors/CodeEditor.vue'
  import JsonDisplay from '@/components/display/JsonDisplay.vue'
  import MangoPanelSpin from '@/components/feedback/MangoPanelSpin.vue'
  import { postApiAuthConfigRefresh } from '@/api/apitest/auth-config'
  import type { AuthRecord } from '../types'
  const emit = defineEmits<{ (event: 'refreshed'): void }>()
  const customCodePanel = reactive({
    visible: false,
    title: '自定义代码',
    code: '',
    id: 0,
    result: null as Record<string, unknown> | null,
    error: '',
    version: 0,
  })
  const customCodeRunningIds = reactive(new Set<number>())

  function onViewCustomCode(record: AuthRecord) {
    if (record.auth_type !== 1) return
    customCodePanel.version += 1
    customCodePanel.id = record.id
    customCodePanel.result = null
    customCodePanel.error = ''
    customCodePanel.title = `自定义代码 / ${record.name}`
    customCodePanel.code = record.custom_code || ''
    customCodePanel.visible = true
  }

  async function onRunCustomCode() {
    const { id, version } = customCodePanel
    if (!customCodePanel.visible || !id || customCodeRunningIds.has(id)) return
    customCodeRunningIds.add(id)
    customCodePanel.result = null
    customCodePanel.error = ''
    const isCurrent = () =>
      customCodePanel.visible && customCodePanel.id === id && customCodePanel.version === version
    try {
      const response = await postApiAuthConfigRefresh(id)
      if (isCurrent()) customCodePanel.result = response.data
    } catch (error) {
      if (isCurrent())
        customCodePanel.error = requestFailureMessage(error, error instanceof Error ? error.message : '授权刷新失败，请稍后重试')
    } finally {
      customCodeRunningIds.delete(id)
      emit('refreshed')
    }
  }

  function closePanel() {
    customCodePanel.visible = false
    customCodePanel.version++
  }
  onBeforeUnmount(closePanel)
  onDeactivated(closePanel)
  defineExpose({ open: onViewCustomCode })
</script>
<style scoped>
  .mango-auth-custom-code-panel {
    display: grid;
    grid-template-rows: minmax(0, 7fr) minmax(0, 3fr);
    gap: var(--m-page-gap);
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .mango-auth-custom-code-result {
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
  }

  .mango-auth-custom-code-result-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--m-page-gap);
    padding-bottom: var(--m-page-gap);
    color: var(--m-text);
    font-weight: 500;
  }

  .mango-auth-custom-code-result-body {
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .mango-auth-custom-code-result-body :deep(> .mango-panel-spin__content) {
    height: 100%;
    overflow: auto;
  }
</style>
