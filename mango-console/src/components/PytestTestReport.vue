<template>
  <a-tabs default-active-key="1">
    <a-tab-pane key="1" title="执行过程">
      <a-collapse v-for="item of resultData" :bordered="false" :key="item.uuid" destroy-on-hide>
        <a-collapse-item :header="item.name" :style="customStyle" :key="item.uuid">
          <a-descriptions :column="{ xs: 1, md: 3, lg: 4 }">
            <a-descriptions-item
              v-for="attachments of item.attachments"
              :key="attachments.name"
              :label="attachments.name"
            >
              <a-tag>{{ attachments.source }}</a-tag>
            </a-descriptions-item>
          </a-descriptions>
        </a-collapse-item>
      </a-collapse>
    </a-tab-pane>
  </a-tabs>
</template>

<script setup lang="ts">
  import { defineProps, reactive } from 'vue'
  import { strJson } from '@/utils/tools'
  const customStyle = reactive({
    borderRadius: '6px',
    marginBottom: '2px',
    border: 'none',
    overflow: 'hidden',
  })
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
