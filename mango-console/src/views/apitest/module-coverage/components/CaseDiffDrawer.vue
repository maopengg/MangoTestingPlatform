<template>
  <a-drawer
    v-model:visible="visible"
    class="mango-case-diff-drawer"
    title="Case扫描差异"
    width="min(1440px, max(1040px, 56vw))"
    unmount-on-close
  >
    <mango-panel-spin :loading="loading" class="mango-case-diff__spin">
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
  import { reactive, ref } from 'vue'
  import { getCoverageCaseDiff } from '@/api/apitest/module-coverage'

  const visible = ref(false)
  const loading = ref(false)
  const diff = reactive<any>({})
  const pretty = (value: any) => (value ? JSON.stringify(value, null, 2) : '暂无数据')

  async function open(id: number) {
    visible.value = true
    loading.value = true
    try {
      Object.assign(diff, (await getCoverageCaseDiff(id)).data || {})
    } finally {
      loading.value = false
    }
  }

  defineExpose({ open })
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
