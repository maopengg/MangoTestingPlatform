<template>
  <a-tabs default-active-key="1">
    <template #extra>
      <a-tag v-if="resultData?.start">
        执行时间：{{
          (() => {
            const d = new Date(Number(resultData.start))
            return `${d.getFullYear()}年${(d.getMonth() + 1).toString().padStart(2, '0')}月${d
              .getDate()
              .toString()
              .padStart(2, '0')}日 ${d.getHours().toString().padStart(2, '0')}时${d
              .getMinutes()
              .toString()
              .padStart(2, '0')}分${d.getSeconds().toString().padStart(2, '0')}秒`
          })()
        }}</a-tag
      >
    </template>
    <a-tab-pane key="1" title="执行过程">
      <a-collapse
        v-for="(attachments, index) of resultData.attachments"
        :key="index"
        :bordered="false"
        :default-active-key="['1']"
        destroy-on-hide
      >
        <a-collapse-item :key="index" :header="attachments.name">
          <div>{{ attachments.source }}</div>
        </a-collapse-item>
      </a-collapse>
    </a-tab-pane>
    <a-tab-pane key="2" title="完整数据">
      <pre>{{ resultData }}</pre>
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
