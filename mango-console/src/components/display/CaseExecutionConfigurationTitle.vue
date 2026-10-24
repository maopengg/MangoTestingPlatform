<template>
  <a-space :size="4">
    <span>执行配置</span>
    <a-tooltip :trigger="['hover', 'focus']" :content="prepublished ? '按用例发布状态展示配置；本次审核用例均为预发布，展示预发布配置。' : '按用例发布状态展示配置：未发布展示编辑态，预发布展示预发布修订，已发布展示已发布版本。'">
      <IconQuestionCircle tabindex="0" aria-label="执行配置来源说明" />
    </a-tooltip>
  </a-space>
</template>

<script setup lang="ts">
  import { IconQuestionCircle } from '@arco-design/web-vue/es/icon'

  defineProps<{ prepublished?: boolean }>()
</script>
