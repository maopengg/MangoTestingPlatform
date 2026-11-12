<template>
  <section class="api-case-panel api-case-left" :class="{ 'api-case-edit-locked': editLocked }">
    <div class="api-case-panel-head">
      <div>
        <div class="api-case-panel-title">用例编排</div>
        <div class="api-case-panel-subtitle">前置准备、执行编排和后置清理配置</div>
      </div>
      <a-tag size="small" color="arcoblue">{{ stepCount }} 个步骤</a-tag>
    </div>
    <mango-panel-spin :loading="loading" tip="配置加载中..." class="api-case-panel-loading">
      <div class="api-case-panel-body">
        <a-tabs class="mango-api-case-orchestration-tabs" :active-key="activeKey" @tab-click="$emit('change', String($event))">
          <template #extra>
            <a-space v-if="showAdd && !editLocked">
              <a-button
                size="small"
                type="primary"
                data-testid="qa-views-apitest-case-details-button-增加"
                @click="$emit('add')"
              >
                增加
              </a-button>
            </a-space>
          </template>
          <a-tab-pane
            key="1"
            title="前置准备"
            data-testid="qa-views-apitest-case-details-tab-pane-前置准备"
          >
            <slot name="preparation"></slot>
          </a-tab-pane>
          <a-tab-pane
            key="2"
            title="执行编排"
            data-testid="qa-views-apitest-case-details-tab-pane-执行编排"
          >
            <slot name="steps"></slot>
          </a-tab-pane>
          <a-tab-pane
            key="3"
            title="后置清理"
            data-testid="qa-views-apitest-case-details-tab-pane-后置清理"
          >
            <slot name="cleanup"></slot>
          </a-tab-pane>
        </a-tabs>
      </div>
    </mango-panel-spin>
  </section>
</template>

<script setup lang="ts">
  defineProps<{
    activeKey: string
    stepCount: number
    editLocked: boolean
    showAdd: boolean
    loading: boolean
  }>()

  defineEmits<{
    (event: 'change', value: string): void
    (event: 'add'): void
  }>()
</script>

<style scoped>
  .api-case-panel {
    display: flex;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    flex-direction: column;
    border: 1px solid var(--m-border);
    border-radius: var(--m-radius-md);
    background: var(--m-surface);
  }

  .api-case-panel-head {
    display: flex;
    min-height: 58px;
    padding: 10px 12px;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    border-bottom: 1px solid var(--m-border);
    background: var(--m-surface);
  }

  .api-case-panel-head > div:first-child {
    min-width: 0;
    flex: 1;
  }

  .api-case-panel-title {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 8px;
    color: var(--m-text);
    font-size: 15px;
    font-weight: 600;
    line-height: 22px;
  }

  .api-case-panel-subtitle {
    overflow: hidden;
    max-width: 680px;
    color: var(--m-muted);
    font-size: 12px;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .api-case-panel-body {
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    flex: 1;
    padding: var(--m-page-gap);
  }

  .api-case-panel-loading {
    min-height: 0;
    overflow: hidden;
    flex: 1;
  }

  .api-case-panel-loading :deep(> .mango-panel-spin__content) {
    display: flex;
    height: 100%;
    min-height: 0;
    flex-direction: column;
  }
  .mango-api-case-orchestration-tabs { display: flex; flex: 1; flex-direction: column; height: 100%; min-height: 0; overflow: hidden; }
  .mango-api-case-orchestration-tabs :deep(> .arco-tabs-nav) { flex: none; }
  .mango-api-case-orchestration-tabs :deep(> .arco-tabs-content) { display: flex; flex-direction: column; flex: 1; min-width: 0; min-height: 0; overflow: hidden; padding-top: 1px; }
  .mango-api-case-orchestration-tabs :deep(> .arco-tabs-content > .arco-tabs-content-list) { flex: 1; width: 100%; height: 100%; min-width: 0; min-height: 0; }
  .mango-api-case-orchestration-tabs :deep(> .arco-tabs-content > .arco-tabs-content-list > .arco-tabs-content-item) { height: 100%; min-height: 0; overflow: hidden; }
  .mango-api-case-orchestration-tabs :deep(> .arco-tabs-content > .arco-tabs-content-list > .arco-tabs-content-item > .arco-tabs-pane) { height: 100%; min-height: 0; overflow: auto; overscroll-behavior: contain; }
</style>
