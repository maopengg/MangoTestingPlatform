<template>
  <BaseSidePanel
    :visible="state.visible"
    title="接口管理详情"
    width="calc(92vw - 150px)"
    mode="page"
    @update:visible="state.visible = $event"
    @cancel="state.visible = false"
  >
    <div class="mango-api-case-api-info-panel">
      <ApiInfoDetails
        v-if="state.visible && state.apiInfoId"
        :key="state.apiInfoId"
        embedded
        :api-info-id="state.apiInfoId"
        @close="state.visible = false"
      />
    </div>
  </BaseSidePanel>
</template>

<script setup lang="ts">
  import { reactive, onBeforeUnmount, onDeactivated } from 'vue'
  import BaseSidePanel from '@/components/overlays/BaseSidePanel.vue'
  import ApiInfoDetails from '@/views/apitest/info/details/index.vue'

  const state = reactive({
    visible: false,
    apiInfoId: '',
  })

  function open(apiInfoId: string | number) {
    state.apiInfoId = String(apiInfoId)
    state.visible = true
  }

  function close() {
    state.visible = false
  }
  onBeforeUnmount(close)
  onDeactivated(close)
  defineExpose({ open, close })
</script>

<style scoped>
  .mango-api-case-api-info-panel {
    height: 100%;
    min-height: 0;
  }

  .mango-api-case-api-info-panel :deep(.mango-detail-workbench-page) {
    height: 100%;
    min-height: 0;
  }
</style>
