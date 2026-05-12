<template>
  <a-tabs default-active-key="1">
    <template #extra>
      <a-tag v-if="resultData?.test_time">执行时间：{{ resultData?.test_time }}</a-tag>
    </template>
    <a-tab-pane key="1" title="基础信息">
      <section class="api-summary">
        <div class="summary-header">
          <div>
            <span class="summary-label">接口ID</span>
            <h1>{{ resultData?.id || '-' }}</h1>
          </div>
          <a-tag :color="statusTagColor" size="large">{{ statusText }}</a-tag>
        </div>

        <div class="summary-grid">
          <div class="summary-item">
            <span class="item-label">接口名称</span>
            <span class="item-value">{{ resultData?.name || '-' }}</span>
          </div>
          <div class="summary-item">
            <span class="item-label">Method</span>
            <a-tag color="arcoblue">{{ resultData?.request?.method || '-' }}</a-tag>
          </div>
          <div class="summary-item summary-item-wide">
            <span class="item-label">URL</span>
            <span class="item-value url-text">{{ resultData?.request?.url || '-' }}</span>
          </div>
          <div class="summary-item">
            <span class="item-label">Status Code</span>
            <span class="item-value">{{ resultData?.response?.code || '-' }}</span>
          </div>
          <div class="summary-item">
            <span class="item-label">响应时间</span>
            <span class="item-value">{{ resultData?.response?.time || '-' }}</span>
          </div>
        </div>

        <div v-if="resultData?.status === 0" class="error-block">
          <span class="error-title">错误提示语</span>
          <span class="error-content">{{ resultData?.error_message || '-' }}</span>
        </div>
      </section>
    </a-tab-pane>
    <a-tab-pane key="2" title="请求信息">
      <a-tabs default-active-key="21" position="left" size="small">
        <a-tab-pane key="21" title="请求头">
          <JsonDisplay :data="resultData?.request?.headers" />
        </a-tab-pane>
        <a-tab-pane key="22" title="参数">
          <JsonDisplay :data="resultData?.request?.params" />
        </a-tab-pane>
        <a-tab-pane key="23" title="表单">
          <JsonDisplay :data="resultData?.request?.data" />
        </a-tab-pane>
        <a-tab-pane key="24" title="JSON">
          <JsonDisplay :data="resultData?.request?.json" />
        </a-tab-pane>
        <a-tab-pane key="25" title="文件">
          <JsonDisplay :data="resultData?.request?.file" />
        </a-tab-pane>
      </a-tabs>
    </a-tab-pane>
    <a-tab-pane key="3" title="响应信息">
      <a-tabs default-active-key="31" position="left" size="small">
        <a-tab-pane key="31" title="响应头">
          <JsonDisplay :data="resultData?.response?.headers" />
        </a-tab-pane>

        <a-tab-pane key="33" title="JSON">
          <JsonDisplay :data="resultData?.response?.json" />
        </a-tab-pane>
        <a-tab-pane key="32" title="文本">
          <JsonDisplay :data="resultData?.response?.text" />
        </a-tab-pane>
      </a-tabs>
    </a-tab-pane>

    <a-tab-pane key="11" title="缓存数据">
      <JsonDisplay :data="resultData?.cache_data" />
    </a-tab-pane>
    <a-tab-pane key="13" title="数据工厂">
      <JsonDisplay :data="resultData?.data_factory_cache_data" />
    </a-tab-pane>
    <a-tab-pane key="12" title="断言数据">
      <AssertionResult :data="resultData?.ass" />
    </a-tab-pane>
  </a-tabs>
</template>

<script lang="ts" setup>
  import { computed } from 'vue'
  import AssertionResult from '@/components/AssertionResult.vue' // 引入断言结果组件

  const props = defineProps({
    resultData: {
      type: Object as () => any,
      required: true,
    },
  })

  const statusText = computed(() => {
    if (props.resultData?.status === 1) return '测试通过'
    if (props.resultData?.status === 0) return '测试失败'
    return '未测试'
  })

  const statusTagColor = computed(() => {
    if (props.resultData?.status === 1) return 'green'
    if (props.resultData?.status === 0) return 'red'
    return 'gray'
  })
</script>

<style scoped>
  .api-summary {
    padding: 18px;
    border: 1px solid var(--color-border-2);
    border-radius: 6px;
    background: linear-gradient(180deg, var(--color-fill-1), var(--color-bg-2));
  }

  .summary-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--color-border-2);
  }

  .summary-label,
  .item-label,
  .error-title {
    color: var(--color-text-3);
    font-size: 13px;
    line-height: 20px;
  }

  .summary-header h1 {
    margin: 4px 0 0;
    color: var(--color-text-1);
    font-size: 24px;
    font-weight: 600;
    line-height: 32px;
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px 20px;
    padding-top: 16px;
  }

  .summary-item {
    min-width: 0;
    padding: 12px;
    border-radius: 6px;
    background: var(--color-bg-1);
  }

  .summary-item-wide {
    grid-column: 1 / -1;
  }

  .item-label {
    display: block;
    margin-bottom: 6px;
  }

  .item-value {
    color: var(--color-text-1);
    font-size: 14px;
    font-weight: 500;
    line-height: 22px;
  }

  .url-text {
    display: block;
    word-break: break-all;
  }

  .error-block {
    display: flex;
    gap: 12px;
    margin-top: 16px;
    padding: 12px;
    border: 1px solid rgb(var(--red-2));
    border-radius: 6px;
    background: rgb(var(--red-1));
  }

  .error-title {
    flex: 0 0 76px;
    color: rgb(var(--red-6));
    font-weight: 500;
  }

  .error-content {
    min-width: 0;
    color: var(--color-text-1);
    line-height: 22px;
    word-break: break-word;
  }

  pre {
    background-color: #f5f5f5;
    padding: 10px;
    border-radius: 4px;
    overflow-x: auto;
  }

  @media (max-width: 768px) {
    .api-summary {
      padding: 14px;
    }

    .summary-header {
      flex-direction: column;
      align-items: stretch;
    }

    .summary-grid {
      grid-template-columns: 1fr;
    }

    .error-block {
      flex-direction: column;
      gap: 6px;
    }
  }
</style>
