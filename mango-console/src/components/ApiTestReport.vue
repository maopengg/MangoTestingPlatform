<template>
  <a-tabs default-active-key="1">
    <a-tab-pane key="1" title="基础信息">
      <a-space direction="vertical">
        <h1>接口ID：{{ resultData?.id }}</h1>
        <p>接口名称：{{ resultData?.name }}</p>
        <p>Method：{{ resultData?.request?.method }}</p>
        <p>URL：{{ resultData?.request?.url }}</p>
        <p>Status Code：{{ resultData?.response?.code }}</p>
        <p>响应时间：{{ resultData?.response?.time }}</p>
        <p :style="{ color: resultData?.status === 0 ? 'red' : 'inherit' }">
          测试结果：{{ resultData?.status === 1 ? '通过' : resultData?.status === 0 ? '失败' : '' }}
        </p>
        <p v-if="resultData?.status === 0">错误提示语：{{ resultData?.error_message }}</p>
      </a-space>
    </a-tab-pane>
    <a-tab-pane key="2" title="请求信息">
      <a-tabs default-active-key="21" size="small" position="left">
        <a-tab-pane key="21" title="请求头">
          <pre>{{ strJson(resultData?.request?.headers) }}</pre>
        </a-tab-pane>
        <a-tab-pane key="22" title="参数">
          <pre>{{ strJson(resultData?.request?.params) }}</pre>
        </a-tab-pane>
        <a-tab-pane key="23" title="data">
          <pre>{{ strJson(resultData?.request?.data) }}</pre>
        </a-tab-pane>
        <a-tab-pane key="24" title="json">
          <pre>{{ strJson(resultData?.request?.json) }}</pre>
        </a-tab-pane>
        <a-tab-pane key="25" title="文件">
          <pre>{{ strJson(resultData?.request?.file) }}</pre>
        </a-tab-pane>
      </a-tabs>
    </a-tab-pane>
    <a-tab-pane key="3" title="响应信息">
      <a-tabs default-active-key="31" size="small" position="left">
        <a-tab-pane key="31" title="响应头">
          <pre>{{ strJson(resultData?.response?.headers) }}</pre>
        </a-tab-pane>
        <a-tab-pane key="32" title="文本">
          <pre>{{ strJson(resultData?.response?.text) }}</pre>
        </a-tab-pane>
        <a-tab-pane key="33" title="JSON">
          <pre>{{ strJson(resultData?.response?.json) }}</pre>
        </a-tab-pane>
      </a-tabs>
    </a-tab-pane>

    <a-tab-pane key="11" title="缓存数据">
      <pre>{{ strJson(resultData?.cache_data) }}</pre>
    </a-tab-pane>
    <a-tab-pane key="12" title="断言数据">
      <pre>{{ strJson(resultData?.ass) }}</pre>
    </a-tab-pane>
  </a-tabs>
</template>

<script setup lang="ts">
  import { defineProps } from 'vue'
  import { strJson } from '@/utils/tools'

  defineProps({
    resultData: {
      type: Object as () => any,
      required: true,
    },
  })
</script>

<style scoped>
  /* 样式 */
  pre {
    background-color: #f5f5f5;
    padding: 10px;
    border-radius: 4px;
    overflow-x: auto;
  }
</style>
