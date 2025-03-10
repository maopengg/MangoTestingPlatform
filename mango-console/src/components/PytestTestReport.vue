<template>
  <a-tabs default-active-key="1">
    <a-tab-pane key="1" title="执行过程">
      <a-collapse
        :default-active-key="['1']"
        v-for="(attachments, index) of resultData.attachments"
        :key="index"
        :bordered="false"
        accordion
        destroy-on-hide
      >
        <a-collapse-item :header="attachments.name" :key="index">
          <div>{{ attachments.source }}</div>
        </a-collapse-item>
      </a-collapse>
    </a-tab-pane>
    <a-tab-pane key="2" title="完整数据">
      <pre>{{ resultData }}</pre>
    </a-tab-pane>
  </a-tabs>
</template>

<script setup lang="ts">
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
