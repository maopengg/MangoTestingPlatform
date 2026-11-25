<template>
  <a-space :size="4">
    <span>结果</span>
    <a-tooltip :trigger="['hover', 'focus']">
      <IconQuestionCircle tabindex="0" aria-label="用例结果说明" />
      <template #content>
        <div class="mango-case-result-help">
          <div>按展示版本取跨环境最近一次已完成结果：未发布取编辑态，预发布取候选修订，已发布取发布版本。右上角环境仅用于执行。</div>
          <div>新执行排队、进行中或自动恢复中，仍保留上次完成结果；该版本没有完成记录时显示待测试。</div>
          <div>通过 / 失败：执行和断言结论；警告：执行存在警告；已停止：执行已停止。</div>
          <div>悬停按发布状态、执行环境逐行查看最近完成结果，点击已有结果查看执行详情。当前执行进度请查看执行报告，修改配置不会清除已有结果。</div>
        </div>
      </template>
    </a-tooltip>
  </a-space>
</template>

<script setup lang="ts">
  import { IconQuestionCircle } from '@arco-design/web-vue/es/icon'
</script>

<style scoped>
  .mango-case-result-help {
    max-width: 360px;
    display: flex;
    flex-direction: column;
    gap: var(--m-page-gap);
  }
</style>
