<template>
  <a-drawer
    v-model:visible="visible"
    class="mango-case-diff-drawer"
    title="Case扫描差异"
    width="min(1440px, max(1040px, 56vw))"
    unmount-on-close
  >
    <mango-panel-spin :loading="loading" class="mango-case-diff__spin">
      <template v-if="failed"><a-button size="small" :loading="loading" @click="loadDiff">重新加载</a-button></template>
      <div class="mango-case-diff__grid">
        <section>
          <h4>上一扫描版本</h4>
          <pre class="mango-code-panel">{{ pretty(diff.previous?.payload) }}</pre>
        </section>
        <section>
          <h4>当前扫描版本</h4>
          <pre class="mango-code-panel">{{ pretty(diff.current?.payload) }}</pre>
        </section>
      </div>
    </mango-panel-spin>
  </a-drawer>
</template>

<script lang="ts" setup>
import { reportLoadError } from '@/utils/load-error'

  import { ref } from 'vue'
  import { getCoverageCaseDiff } from '@/api/apitest/module-coverage'
  import { useCoveragePanelScope } from '../composables/useCoveragePanelScope'
  import type { CoverageDiff } from '../types'
  const visible = ref(false),
    loading = ref(false),
    failed = ref(false),
    diff = ref<CoverageDiff>({}),
    selectedId = ref<number>()
  const { begin, current, close } = useCoveragePanelScope(visible, () => {
    loading.value = false
  })
  const pretty = (value: unknown) => (value == null ? '暂无数据' : JSON.stringify(value, null, 2))
  async function loadDiff() {
    if (!visible.value || !selectedId.value) return
    const token = begin(),
      id = selectedId.value
    loading.value = true
    failed.value = false
    try {
      const response = await getCoverageCaseDiff(id)
      if (current(token)) diff.value = response.data || {}
    } catch (loadFailure0) {
      if (current(token)) (reportLoadError(loadFailure0, "加载失败，请重试", false), failed.value = true)
    } finally {
      if (current(token)) loading.value = false
    }
  }
  function open(id: number) {
    selectedId.value = id
    diff.value = {}
    visible.value = true
    return loadDiff()
  }
  defineExpose({ open, close })
</script>
<style lang="less" scoped>
  :global(.mango-case-diff-drawer .arco-drawer-body) {
    display: flex;
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
  }
  .mango-case-diff__spin {
    display: block;
    flex: 1;
    min-height: 0;
    width: 100%;
  }
  :deep(.mango-case-diff__spin > .arco-spin),
  :deep(.mango-case-diff__spin > .mango-panel-spin__content) {
    height: 100%;
    min-height: 0;
  }
  .mango-case-diff__grid {
    display: grid;
    height: 100%;
    min-height: 0;
    grid-template-columns: repeat(2, minmax(480px, 1fr));
    gap: var(--m-page-gap);
    overflow-x: auto;
  }
  .mango-case-diff__grid section {
    display: flex;
    min-width: 480px;
    min-height: 0;
    flex-direction: column;
  }
  .mango-case-diff__grid h4 {
    flex: none;
    margin: 0 0 var(--m-page-gap);
    color: var(--m-text-1);
  }
  .mango-case-diff__grid pre {
    flex: 1;
    min-height: 0;
    margin: 0;
    overflow: auto;
    white-space: pre-wrap;
  }
</style>
