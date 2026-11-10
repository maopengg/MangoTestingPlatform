<template>
  <span class="mango-variable-reference-trigger">
    <a-button
      size="small"
      :aria-expanded="visible"
      :aria-controls="panelId"
      @click="visible = true" data-testid="qa-components-business-variablereferencepanel-button-随机测试数据"
    >
      随机测试数据
    </a-button>
    <BaseSidePanel
      v-model:visible="visible"
      title="随机测试数据"
      width="68%"
      mode="page"
    >
      <div :id="panelId" class="mango-variable-reference-panel">
        <VariableReferencePage embedded />
      </div>
    </BaseSidePanel>
  </span>
</template>

<script lang="ts" setup>
  import { getCurrentInstance, onDeactivated, ref } from 'vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import VariableReferencePage from '@/views/help/variable/index.vue'

  const visible = ref(false)
  onDeactivated(() => { visible.value = false })
  const panelId = `mango-variable-reference-panel-${getCurrentInstance()?.uid ?? 'default'}`
</script>

<style scoped>
  .mango-variable-reference-trigger {
    display: inline-flex;
  }

  .mango-variable-reference-panel {
    height: 100%;
    min-height: 0;
    padding: 0;
    background: var(--m-bg);
  }
</style>
