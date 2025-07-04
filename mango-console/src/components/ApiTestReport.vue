<template>
  <a-tabs default-active-key="1">
    <template #extra>
      <a-tag v-if="resultData?.test_time">执行时间：{{ resultData?.test_time }}</a-tag>
    </template>
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
    <a-tab-pane key="12" title="断言数据">
      <JsonDisplay :data="resultData?.ass" />
    </a-tab-pane>
  </a-tabs>
</template>

<script lang="ts" setup>
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
